"""Frozen20F controller, fixed-path72Hz rollout; oracle is passive evaluation."""
import numpy as np
from nomad_phase20.execution import SPAlignment
from nomad_isaac.common import integrate_se2
from nomad_phase18d.rollout import Evaluator
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from nomad_phase16.geometry import shifted

class OracleEvaluator(Evaluator):
    def interval(self,pose,v,w,dt):
        if self.boxes:return super().interval(pose,v,w,dt)
        wall=corridor_arc_minimum(shifted(pose,self.offset),v,w,dt,self.cc['corridor'],self.radius);return wall,float('inf'),wall,wall

def simulate(B,path,previous_v,ticks=4320):
    ctl=SPAlignment();ctl.replace_path(path,B,previous_v);pose=np.asarray(B,dtype=float).copy();poses=[pose.copy()];commands=[];vel=[];omega=[];previous=float(previous_v);completed=False;errors=[]
    for tick in range(ticks):
        if tick%8==0:
            (v,w),diag=ctl.control(pose,previous)
            if diag['completed']:completed=True;break
            previous=v;commands.append(dict(tick=tick,v=v,w=w,mode=diag['mode']))
        pose=integrate_se2(pose,v,w,1/72);poses.append(pose.copy());vel.append(v);omega.append(w);errors.append(ctl.follower.path.project(pose[:2])[1])
    if not completed and ctl.mode=='GO' and np.linalg.norm(pose[:2]-np.asarray(path)[-1])<=.01:completed=True
    ww=np.array([r['w'] for r in commands]);jerk=np.diff(ww,n=2)*81
    return dict(poses=np.array(poses),commands=commands,speeds=vel,omegas=omega,completed=completed,completion_time_s=len(vel)/72 if completed else None,duration_s=len(vel)/72,
        jerk_rms=float(np.sqrt(np.mean(jerk**2))) if len(jerk) else 0.,omega_saturation_fraction=float(np.mean(np.abs(omega)>=.399)) if omega else 0.,
        tracking_rms=float(np.sqrt(np.mean(np.square(errors)))) if errors else 0.,tracking_max=max(errors,default=0.),distance_m=float(np.sum(np.abs(vel))/72),termination='ENDPOINT' if completed else 'TIME_LIMIT',alignment=ctl.trigger_S)

def evaluate(result,config):
    ev=OracleEvaluator(config);low,box,wall,upper=ev.interval(result['poses'][0],0,0,0);first=0 if low<0 else None
    for i,(v,w) in enumerate(zip(result['speeds'],result['omegas'])):
        a,b,c,d=ev.interval(result['poses'][i],v,w,1/72);low=min(low,a);box=min(box,b);wall=min(wall,c);upper=min(upper,d)
        if a<0 and first is None:first=i+1
    return {**result,'oracle_minimum_clearance_m':low,'oracle_box_clearance_m':box,'oracle_wall_clearance_m':wall,'oracle_collision':upper<0,
        'oracle_conservative_negative':low<0 and upper>=0,'first_overlap_tick':first,'safe_completion':result['completed'] and upper>=0}
