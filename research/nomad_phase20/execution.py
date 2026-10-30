"""SP plus departure alignment only; geometry input, no obstacle/controller oracle."""
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.chunk_execution import protocol as follower_protocol
from nomad_phase18d.speed_profile import make_profile
from nomad_phase19s.srg import wrap,evaluate


class SPAlignment:
    def __init__(self):self.plan_generation=0

    def replace_path(self,xy,B,actual_v):
        self.follower=PurePursuit(xy,follower_protocol()['follower']);self.plan=make_profile(xy)
        self.plan_generation+=1;self.mode='GO';self.target_yaw=None;self.trigger_S=False
        B=np.asarray(B,dtype=float)
        first=next((q for q in self.follower.path.points if np.linalg.norm(q-B[:2])>=.05),None)
        if actual_v<.01 and first is not None:
            target=float(np.arctan2(*(first-B[:2])[::-1]))
            if abs(wrap(target-B[2]))>=np.deg2rad(20)-1e-12:
                self.trigger_S=True;self.target_yaw=target;self.mode='BRAKE'

    def control(self,pose,actual_v):
        if self.mode=='ROTATE' and abs(wrap(self.target_yaw-pose[2]))<1e-10:self.mode='GO'
        _,diag=self.follower.control(pose)
        if self.mode=='GO' and diag['endpoint_stop']:return (0.,0.),dict(completed=True,mode='ENDPOINT',target=0.,kappa=None)
        if self.mode=='BRAKE' and actual_v<=1e-12:self.mode='ROTATE'
        if self.mode=='ROTATE':v=0.;w=float(np.clip(wrap(self.target_yaw-pose[2])*9,-.4,.4));target=0.;k=None
        else:
            x,y=diag['target_local_x_m'],diag['target_local_y_m'];k=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
            s,_=self.follower.path.project(pose[:2]);target=float(np.interp(s,self.plan['s_m'],self.plan['v_m_s']))
            floor=0. if self.mode=='BRAKE' else .05;target=0. if self.mode=='BRAKE' else float(np.clip(target,.05,.3))
            v=float(np.clip(target,max(floor,actual_v-.5/9),min(.3,actual_v+.5/9)));w=float(np.clip(v*k,-.4,.4))
        return (v,w),dict(completed=False,mode=self.mode,target=target,kappa=k,progress=self.follower.progress,plan_generation=self.plan_generation)


def rollout(B,xy,previous_v,config,ticks=108):
    assert 0<=ticks<=108
    controller=SPAlignment();controller.replace_path(xy,B,previous_v)
    pose=np.asarray(B,dtype=float).copy();poses=[pose.copy()];commands=[];speeds=[];omegas=[];phases=[]
    actual_v=float(previous_v);v=w=0.;completed=False;distance=0.;max_cte=controller.follower.path.project(pose[:2])[1]
    for tick in range(ticks):
        if tick%8==0:
            (v,w),diag=controller.control(pose,actual_v)
            if diag['completed']:completed=True;break
            commands.append(dict(tick=tick,v=v,w=w,**diag));actual_v=v
        pose=integrate_se2(pose,v,w,1/72);poses.append(pose.copy());speeds.append(v);omegas.append(w);phases.append(controller.mode)
        distance+=abs(v)/72;max_cte=max(max_cte,controller.follower.path.project(pose[:2])[1])
    if not completed and controller.mode=='GO' and np.linalg.norm(pose[:2]-controller.follower.path.points[-1])<=.01:completed=True
    result=dict(poses=np.array(poses),commands=commands,speeds=speeds,omegas=omegas,phases=phases,trigger_S=controller.trigger_S,trigger_P=0,
        rotation_time_s=sum(p=='ROTATE' for p in phases)/72,distance_m=distance,arclength_progress_m=float(controller.follower.path.project(pose[:2])[0]),
        max_cross_track_m=max_cte,duration_s=len(speeds)/72,completed=completed,termination='ENDPOINT' if completed else 'HORIZON',
        omega_saturation_fraction=float(np.mean(np.abs(omegas)>=.399)) if omegas else 0.)
    return evaluate(result,config)
