"""Deterministic computation-window motion, using no future observations."""
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.chunk_execution import protocol as follower_protocol

def prefix(case,duration_s,mode):
    pose=np.asarray(case['B'],dtype=float).copy();v,w=map(float,case['previous_vw']);poses=[pose.copy()];vs=[];ws=[];dts=[];commands=[]
    path=case.get('executing_path',case.get('baseline_old_path',case.get('old_path')))
    follower=PurePursuit(path,follower_protocol()['follower']) if path is not None else None
    elapsed=0.;step=0;command_v=v;command_w=w
    while elapsed<duration_s-1e-12:
        # Preserve the already applied command until the next9Hz control tick.
        if (int(case.get('tick',0))+step)%8==0:
            if mode=='continue_current_v_pp' and follower is not None and v>0:
                _,diag=follower.control(pose);x,y=diag['target_local_x_m'],diag['target_local_y_m'];command_v=v;command_w=float(np.clip(v*2*y/max(x*x+y*y,1e-24),-.4,.4))
            elif mode=='brake_wait':command_v=max(0.,command_v-.5/9);command_w=0.
            elif mode not in ('continue_current_v_pp','brake_wait','constant_twist'):raise ValueError(mode)
            commands.append(dict(tick=step,time_s=elapsed,v=command_v,w=command_w,mode='BASELINE_COMPUTATION_BRAKE' if mode=='brake_wait' else 'COMPUTATION_OLD_PATH'))
        dt=min(1/72,duration_s-elapsed);pose=integrate_se2(pose,command_v,command_w,dt)
        poses.append(pose.copy());vs.append(command_v);ws.append(command_w);dts.append(dt);elapsed+=dt;step+=1
    return dict(poses=np.array(poses),speeds=vs,omegas=ws,step_dt_s=dts,duration_s=duration_s,distance_m=float(np.sum(np.array(vs)*dts)),
        B_pred=pose.tolist(),previous_vw=[command_v,command_w],mode=mode,path_available=path is not None,oracle_used=False,future_log_used=False,commands=commands)

def concatenate(waiting,result):
    n=len(waiting['speeds']);dts=result.get('step_dt_s',[1/72]*len(result['speeds']));duration=waiting['duration_s']+result['duration_s']
    commands=list(waiting.get('commands',[]))+[dict(c,tick=c['tick']+n,time_s=waiting['duration_s']+c.get('time_s',c['tick']/72)) for c in result.get('commands',[])]
    return dict(result,poses=np.vstack([waiting['poses'][:-1],result['poses']]),speeds=waiting['speeds']+list(result['speeds']),omegas=waiting['omegas']+list(result['omegas']),commands=commands,
        step_dt_s=waiting['step_dt_s']+list(dts),duration_s=duration,completion_time_s=duration if result['completed'] else None,distance_m=waiting['distance_m']+result['distance_m'],
        computation_prefix_ticks=n,computation_prefix_s=waiting['duration_s'],computation_prefix_distance_m=waiting['distance_m'],
        tick_cap=n+result.get('tick_cap',len(result['speeds'])),
        omega_saturation_fraction=float(np.mean(np.abs(waiting['omegas']+list(result['omegas']))>=.399)) if duration else 0.)
