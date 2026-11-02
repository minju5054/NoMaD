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

def stop_rollout(B,v0):
    pose=np.array(B,dtype=float);poses=[pose.copy()];vs=[];ws=[];v=float(v0)
    while v>1e-12:
        if len(vs)%8==0:v=max(0.,v-.5/9)
        pose=integrate_se2(pose,v,0.,1/72);poses.append(pose.copy());vs.append(v);ws.append(0.)
    return dict(poses=np.array(poses),speeds=vs,omegas=ws,duration_s=len(vs)/72,completion_time_s=None,completed=False,termination='NO_PLAN_STOP',omega_saturation_fraction=0.,distance_m=sum(vs)/72,commands=[])

def unified_simulate(case,plan,policy):
    assert policy['rotation_policy']=='graph_rotation','Execution rule must be explicitly registered'
    if not plan['accepted']:return stop_rollout(case['B'],case['previous_vw'][0])
    q=np.array(plan['poses']);dt=np.array(plan['dt']);lengths=np.linalg.norm(np.diff(q[:,:2],axis=0),axis=1);s=np.r_[0.,np.cumsum(lengths)]
    if s[-1]<1e-10:return stop_rollout(case['B'],case['previous_vw'][0])
    poly=XYPath(q[:,:2]);follower=PurePursuit(q[:,:2],follower_protocol()['follower'])
    pose=np.array(case['B']);poses=[pose.copy()];vs=[];ws=[];commands=[];previous=float(case['previous_vw'][0]);progress=0.;rotation_time=0.;done=set();tick=0
    while True:
        progress=max(progress,poly.project(pose[:2])[0]);reason=stop_reason(pose,poly.points[-1],progress,float(s[-1]),tick/72,rotation_time)
        if reason:break
        if tick%8==0:
            rotations=[i for i in range(10) if lengths[i]<=1e-8 and i not in done and progress>=s[i]-1e-8]
            mode='PP_GRAPH_SPEED'
            if rotations:
                i=rotations[0];error=float((q[i+1,2]-pose[2]+np.pi)%(2*np.pi)-np.pi)
                if previous>.01:v=max(0.,previous-.5/9);w=0.;mode='GRAPH_ROTATION_BRAKE'
                elif abs(error)>.001:
                    planned=abs(float((q[i+1,2]-q[i,2]+np.pi)%(2*np.pi)-np.pi))/dt[i]
                    v=0.;w=float(np.clip(error*9,-min(.4,planned),min(.4,planned)));mode='GRAPH_ROTATION'
                else:done.add(i);v=0.;w=0.;mode='GRAPH_ROTATION_END'
            else:
                i=min(9,int(np.searchsorted(s,progress,side='right')-1));target=lengths[i]/dt[i];v=float(np.clip(target,max(0.,previous-.5/9),min(.3,previous+.5/9)))
                _,diag=follower.control(pose);x,y=diag['target_local_x_m'],diag['target_local_y_m'];k=2*y/max(x*x+y*y,1e-24);w=float(np.clip(v*k,-.4,.4))
            previous=v;commands.append(dict(tick=tick,v=v,w=w,mode=mode))
        pose=integrate_se2(pose,v,w,1/72);poses.append(pose.copy());vs.append(v);ws.append(w);rotation_time+=(mode.startswith('GRAPH_ROTATION'))/72;tick+=1
        if tick>72*(s[-1]/.05+40):raise RuntimeError('Unexpected rotation/time guard')
    return dict(poses=np.array(poses),speeds=vs,omegas=ws,commands=commands,completed=True,duration_s=tick/72,completion_time_s=tick/72,termination=reason,TIMEOUT=reason=='TIMEOUT',rotation_time_s=rotation_time,
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
