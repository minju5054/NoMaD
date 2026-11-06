"""Time feedforward, small pose feedback, and final command saturation."""
import copy,math
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.chunk_execution import protocol as pp_protocol
from nomad_phase18d.speed_profile import make_profile
from nomad_phase16.execution import stop_command
from .graph import wrap
from .telemetry import builtin

def clip_command(raw,previous,alpha,dt=1/9):
    v=float(np.clip(raw[0],max(0.,previous[0]-.5*dt),min(.3,previous[0]+.5*dt)))
    w=float(np.clip(raw[1],max(-.4,previous[1]-alpha*dt),min(.4,previous[1]+alpha*dt)))
    return (v,w),builtin(dict(v_clipped=abs(v-raw[0])>1e-12,w_clipped=abs(w-raw[1])>1e-12,any_clipped=abs(v-raw[0])>1e-12 or abs(w-raw[1])>1e-12))

class TimedFollower:
    def __init__(self,result,start_s,alpha):
        self.result=result;self.q=np.array(result['poses']);self.dt=np.array(result['dt']);self.times=np.r_[0.,np.cumsum(self.dt)];self.mid=(self.times[:-1]+self.times[1:])/2
        self.start_s=start_s;self.now_s=start_s;self.alpha=alpha;self.previous_w=result['omega'][0]
        self.follower=PurePursuit(self.q[:,:2],pp_protocol()['follower']);self.plan=make_profile(self.q[:,:2]);self.mode='GO';self.trigger_S=False;self.target_yaw=None
    def control(self,pose,actual_v):
        t=float(np.clip(self.now_s-self.start_s,0,self.times[-1]));pose=np.asarray(pose)
        target=np.array([np.interp(t,self.times,self.q[:,i]) for i in (0,1)]);heading=float(np.interp(t,self.times,np.unwrap(self.q[:,2])))
        vf=float(np.interp(t,self.mid,self.result['speed']));wf=float(np.interp(t,self.mid,self.result['omega']))
        delta=target-pose[:2];c,s=np.cos(pose[2]),np.sin(pose[2]);ex=c*delta[0]+s*delta[1];ey=-s*delta[0]+c*delta[1];eh=float(wrap(heading-pose[2]))
        raw=[vf+.5*ex,wf+ey+.5*eh];suppressed=False
        if raw[0]<=1e-12 and not self.result['allow_rotation']:raw[1]=0.;suppressed=True
        finished=self.now_s-self.start_s>=self.times[-1]-1e-12
        if finished:raw=[0.,0.]
        command,flags=clip_command(raw,[actual_v,self.previous_w],self.alpha)
        self.mode='ROTATE' if command[0]<.01 and abs(command[1])>1e-8 and self.result['allow_rotation'] else 'GO'
        done=finished and max(abs(command[0]),abs(command[1]))<1e-12
        return command,builtin(dict(completed=done,mode=self.mode,phase28_timed=True,elapsed_s=t,target=vf,kappa=None,
            feedforward=[vf,wf],feedback=[.5*ex,ey+.5*eh],raw_command=raw,rotation_suppressed=suppressed,**flags))

def apply_tick(dispatch_tick):return int(math.ceil((int(dispatch_tick)+.15*72)/8)*8)

def predict(pose,vw,controller,dispatch_tick,alpha=float('inf')):
    """Same controller + exact72Hz unicycle integrator; no new observation/solve."""
    control=copy.deepcopy(controller);q=np.asarray(pose,float).copy();v,w=map(float,vw);target=apply_tick(dispatch_tick)
    for tick in range(int(dispatch_tick),target):
        if tick%8==0:
            if control is None:v,w=stop_command(v)
            else:
                if hasattr(control,'prediction_epoch_ns'):control.now_ns=control.prediction_epoch_ns+round((tick-control.prediction_epoch_tick)/72*1e9)
                if isinstance(control,TimedFollower):control.now_s=tick/72;control.previous_w=w
                (nv,nw),diag=control.control(q,v)
                if diag['completed']:nv,nw=stop_command(v)
                v=float(nv);requested_w=float(nw)
                w=requested_w if math.isinf(alpha) else float(np.clip(requested_w,w-alpha/72,w+alpha/72))
        elif control is not None and not math.isinf(alpha):w=float(np.clip(requested_w,w-alpha/72,w+alpha/72))
        q=integrate_se2(q,v,w,1/72)
    return dict(pose=q.tolist(),vw=[v,w],dispatch_tick=int(dispatch_tick),apply_tick=target,delay_s=(target-dispatch_tick)/72)

def na_duration(path,B,previous_v):
    """SP arclength-time integral; ideal schedule, not a rollout or goal forecast."""
    from nomad_phase0.pure_pursuit import XYPath
    from .graph import backward
    p=XYPath(path);s,_=p.project(np.asarray(B)[:2]);profile=make_profile(path)
    sample=np.r_[s,p.s[p.s>s]];vel=np.maximum(.05,np.interp(sample,profile['s_m'],profile['v_m_s']))
    moving=0.
    for ds,a,b in zip(np.diff(sample),vel[:-1],vel[1:]):
        moving+=float(ds/a if abs(b-a)<1e-12 else ds*np.log(b/a)/(b-a))
    turning=braking=0.
    if backward(path,B):
        i=np.flatnonzero(p.s>=s+.05)[0];d=p.points[i]-np.asarray(B)[:2];turning=abs(float(wrap(np.arctan2(d[1],d[0])-B[2])))/.4;braking=max(0.,previous_v)/.5
    return dict(sp_time_s=moving,alignment_time_s=turning,alignment_brake_time_s=braking,total_s=moving+turning+braking,
        limitation='SP profile integral and ideal departure stop/rotation only; no PP rollout, tracking error, future FRESH or success prediction')
