"""Offline PP execution with frozen22-O2 stop criteria; no fresh/replanning."""
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase0.pure_pursuit import XYPath,PurePursuit
from nomad_phase0.chunk_execution import protocol as follower_protocol
from nomad_phase22.reeval import stop_reason,simulate as baseline_simulate
from nomad_phase22.drive_geometry import swept_gap,bounds
from nomad_isaac.clearance import configured_obstacles
from nomad_phase0.s0_batch_metrics import corridor_arc_minimum
from nomad_phase16.geometry import centered,shifted

def angle_delta(a):return float((a+np.pi)%(2*np.pi)-np.pi)

class GraphFollower:
    """PP direction + arclength-interpolated graph speed; no start-alignment rule."""
    def __init__(self,poses,dt):
        self.q=np.asarray(poses,dtype=float);self.dt=np.asarray(dt,dtype=float)
        self.lengths=np.linalg.norm(np.diff(self.q[:,:2],axis=0),axis=1)
        self.s=np.r_[0.,np.cumsum(self.lengths)];self.v=self.lengths/self.dt
        self.w=np.array([angle_delta(a) for a in np.diff(self.q[:,2])])/self.dt
        self.rotations=self.v<.01;self.done=set();self.progress=0.;self.rotation=None;self.failure=None
        moving=~self.rotations;centers=(self.s[:-1]+self.s[1:])/2
        self.speed_s=centers[moving];self.speed_v=self.v[moving]
        self.poly=XYPath(self.q[:,:2]) if self.s[-1]>1e-10 else None
        self.pp=PurePursuit(self.q[:,:2],follower_protocol()['follower']) if self.poly is not None else None
    def speed_at(self,s):
        return float(np.clip(np.interp(s,self.speed_s,self.speed_v),0,.3)) if len(self.speed_s) else 0.
    def control(self,pose,previous_v):
        if self.poly is not None:self.progress=max(self.progress,self.poly.project(np.asarray(pose)[:2])[0])
        eligible=[i for i in range(len(self.dt)) if self.rotations[i] and i not in self.done and self.progress>=self.s[i]-1e-8]
        while eligible:
            i=eligible[0];error=angle_delta(self.q[i+1,2]-pose[2]);omega=float(np.clip(self.w[i],-.4,.4))
            if abs(error)<=.001:
                self.done.add(i);self.progress=max(self.progress,float(self.s[i+1]));eligible=eligible[1:];continue
            if previous_v>1e-12:
                return (max(0.,previous_v-.5/9),0.),dict(mode='GRAPH_ROTATION_BRAKE',segment=i,target_v=0.)
            if abs(omega)<1e-12:
                self.failure='ROTATION_ZERO_OMEGA_MISMATCH'
                return (0.,0.),dict(mode=self.failure,segment=i,target_v=0.)
            sign=np.sign(omega);remaining=float((sign*(self.q[i+1,2]-pose[2]))%(2*np.pi))
            # Preserve planned sign and magnitude; shorten only the final9Hz
            # angular step to land exactly on the requested heading.
            return (0.,float(sign*min(abs(omega),remaining*9))),dict(mode='GRAPH_ROTATION',segment=i,planned_w=omega,target_v=0.)
        if self.pp is None:return (max(0.,previous_v-.5/9),0.),dict(mode='ENDPOINT',target_v=0.)
        self.pp.progress=max(self.pp.progress,self.progress)
        target=self.speed_at(self.progress);v=float(np.clip(target,max(0.,previous_v-.5/9),min(.3,previous_v+.5/9)))
        _,diag=self.pp.control(pose);x,y=diag['target_local_x_m'],diag['target_local_y_m'];k=2*y/max(x*x+y*y,1e-24)
        return (v,float(np.clip(v*k,-.4,.4))),dict(mode='PP_GRAPH_SPEED',target_v=target,progress_m=self.progress,kappa_pp=k)


def stop_rollout(B,v0):
    pose=np.array(B,dtype=float);poses=[pose.copy()];vs=[];ws=[];commands=[];v=float(v0)
    while v>1e-12:
        if len(vs)%8==0:
            v=max(0.,v-.5/9);commands.append(dict(tick=len(vs),v=v,w=0.,mode='NO_PLAN_BRAKE'))
        pose=integrate_se2(pose,v,0.,1/72);poses.append(pose.copy());vs.append(v);ws.append(0.)
    return dict(poses=np.array(poses),speeds=vs,omegas=ws,duration_s=len(vs)/72,completion_time_s=None,completed=False,termination='NO_PLAN_STOP',omega_saturation_fraction=0.,distance_m=sum(vs)/72,commands=commands)


def unified_simulate(case,plan,policy):
    assert policy['rotation_policy']=='graph_rotation','Execution rule must be explicitly registered'
    if not plan['accepted']:return stop_rollout(case['B'],case['previous_vw'][0])
    ctl=GraphFollower(plan['poses'],plan['dt']);pose=np.array(case['B'],dtype=float);poses=[pose.copy()];vs=[];ws=[];commands=[]
    previous=float(case['previous_vw'][0]);rotation_time=0.;brake_time=0.;tick=0;progress=0.;complete=True
    while True:
        if ctl.poly is not None:progress=max(progress,ctl.poly.project(pose[:2])[0],ctl.progress)
        # Frozen22-O2 positional stopping, with no heuristic alignment exemption.
        reason=stop_reason(pose,ctl.q[-1,:2],progress,float(ctl.s[-1]),tick/72,0.)
        if reason:break
        if tick%8==0:
            (v,w),diag=ctl.control(pose,previous);mode=diag['mode'];previous=v
            commands.append(dict(tick=tick,v=v,w=w,**diag))
            if ctl.failure:reason=ctl.failure;complete=False;break
        pose=integrate_se2(pose,v,w,1/72);poses.append(pose.copy());vs.append(v);ws.append(w)
        rotation_time+=(mode=='GRAPH_ROTATION')/72;brake_time+=(mode=='GRAPH_ROTATION_BRAKE')/72;tick+=1
    return dict(poses=np.array(poses),speeds=vs,omegas=ws,commands=commands,completed=complete,duration_s=tick/72,completion_time_s=tick/72 if complete else None,termination=reason,TIMEOUT=reason=='TIMEOUT',rotation_time_s=rotation_time,rotation_braking_s=brake_time,
        omega_saturation_fraction=float(np.mean(np.abs(ws)>=.399)) if ws else 0.,distance_m=sum(vs)/72)


def evaluate(result,case):
    config=case['oracle_config'];cc,offset=centered(config);boxes=configured_obstacles(config);minimum=float('inf');collision=False
    for i in range(len(result['poses'])):
        if i==0:p=result['poses'][0];v=w=duration=0.
        else:p=result['poses'][i-1];v=result['speeds'][i-1];w=result['omegas'][i-1];duration=1/72
        wall=corridor_arc_minimum(shifted(p,offset),v,w,duration,cc['corridor'],cc['agent_radius_m']);minimum=min(minimum,wall);collision|=wall<0
        for box in boxes:
            gap=swept_gap(p,v,w,duration,box,config['agent_radius_m']);minimum=min(minimum,gap['lower_m']);collision|=gap['upper_m']<0
    delta=result['poses'][-1,:2]-np.array(case['B'])[:2];progress=float(delta@np.array(case['evaluation_direction']))
    passage=False;side=None;wide=None
    if case['group']=='sudden' and case.get('spawn'):
        box=case['spawn']['obstacle'];lo,hi=bounds(box);passage=bool(np.any(result['poses'][:,0]-config['agent_radius_m']>hi[0]))
        if passage:
            i=np.flatnonzero(result['poses'][:,0]-config['agent_radius_m']>hi[0])[0];side='+Y' if result['poses'][i,1]>box['center_xy_m'][1] else '-Y'
            positive=config['corridor']['half_width']-hi[1];negative=lo[1]+config['corridor']['half_width'];wide=side==('+Y' if positive>negative else '-Y') if abs(positive-negative)>1e-9 else None
        progress=float(passage)
    return dict(oracle_collision=bool(collision),oracle_minimum_clearance_m=minimum,progress=progress,box_passage=passage,side=side,wide_gap=wide,
        execution_time_s=result['duration_s'],omega_saturation_fraction=result['omega_saturation_fraction'],completed=result['completed'],termination=result['termination'])
