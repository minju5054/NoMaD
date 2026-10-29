"""Fixed-path 9/72Hz counterfactual, not a closed-loop navigation simulator."""
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_isaac.clearance import obstacle_bounds,single_obstacle_config,point_clearance,swept_clearance
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from nomad_phase0.chunk_execution import protocol
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase4.execution import command_policy
from nomad_phase16.geometry import centered,shifted
from .speed_profile import make_profile

class Evaluator:
    """Passive oracle evaluation; never passed to PP or speed planning."""
    def __init__(self,config):
        self.c=config;self.radius=config['agent_radius_m'];self.cc,self.offset=centered(config)
        self.boxes=[obstacle_bounds(single_obstacle_config(config,b)) for b in config['obstacles']]
    def interval(self,pose,v,w,dt):
        if dt:
            gaps=[swept_clearance(pose,v,w,dt,lo,hi,self.radius,threshold=.025) for lo,hi in self.boxes]
            low=min(x['lower_m'] for x in gaps);upper=min(x['upper_m'] for x in gaps)
        else:low=upper=min(point_clearance(np.asarray(pose)[:2],lo,hi,self.radius) for lo,hi in self.boxes)
        wall=corridor_arc_minimum(shifted(pose,self.offset),v,w,dt,self.cc['corridor'],self.radius)
        return min(low,wall),low,wall,min(upper,wall)

def rollout(B,xy,previous_v,rule,config,ticks=108,initial_progress=0.):
    assert rule in ('CURV','SP') and 0<=ticks<=108
    follower=PurePursuit(xy,protocol()['follower']);follower.progress=initial_progress
    plan=make_profile(xy) if rule=='SP' else None
    evaluator=Evaluator(config);pose=np.asarray(B,dtype=float).copy();poses=[pose.copy()];commands=[];speeds=[];omegas=[]
    minimum,obstacle,wall,witness=evaluator.interval(pose,0.,0.,0.)
    overlap=minimum<0;reason='INITIAL_OVERLAP' if overlap else 'HORIZON'
    max_cte=follower.path.project(pose[:2])[1];distance=0.;v_prev=float(previous_v);v=w=0.;clipped=0
    for tick in range(0 if overlap else ticks):
        if tick%8==0:
            _,diag=follower.control(pose)
            if diag['endpoint_stop']:reason='ENDPOINT';break
            x,y=diag['target_local_x_m'],diag['target_local_y_m'];kappa=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
            if rule=='CURV':(v,w),flags=command_policy('CURV-SPEED',kappa,v_prev);target=flags['v_target_m_s']
            else:
                s,_=follower.path.project(pose[:2]);target=float(np.clip(np.interp(s,plan['s_m'],plan['v_m_s']),.05,.3))
                v=float(np.clip(target,max(.05,v_prev-.5/9),min(.3,v_prev+.5/9)));w=float(np.clip(v*kappa,-.4,.4))
            commands.append(dict(tick=tick,v=v,w=w,target=target,kappa=kappa,progress=follower.progress));v_prev=v
        gap,boxgap,wallgap,upper=evaluator.interval(pose,v,w,1/72)
        nxt=integrate_se2(pose,v,w,1/72);distance+=abs(v)/72;pose=nxt;poses.append(pose.copy());speeds.append(v);omegas.append(w)
        minimum=min(minimum,gap);obstacle=min(obstacle,boxgap);wall=min(wall,wallgap);witness=min(witness,upper)
        max_cte=max(max_cte,follower.path.project(pose[:2])[1]);clipped+=abs(w)>=.399
        if gap<0:overlap=True;reason='ORACLE_OVERLAP_BOUND';break
    duration=len(speeds)/72
    return dict(minimum_clearance_m=float(minimum),minimum_obstacle_clearance_m=float(obstacle),minimum_wall_clearance_m=float(wall),
        overlap=bool(overlap),geometric_negative_witness=bool(witness<0),conservative_only_negative=bool(overlap and witness>=0),margin_violation=minimum<.025,
        average_speed_m_s=distance/duration if duration else 0.,distance_m=distance,omega_saturation_fraction=clipped/len(speeds) if speeds else 0.,
        max_cross_track_m=max_cte,duration_s=duration,termination=reason,endpoint_stop=reason=='ENDPOINT',end_pose=pose.tolist(),
        poses=np.array(poses),commands=commands,speeds=speeds,omegas=omegas,profile=plan)
