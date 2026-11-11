"""One new selector; frozen Phase53 fallback/Graph/EC and a common endpoint latch."""
import numpy as np
from nomad_phase40p.launch import bind
from nomad_phase28.telemetry import builtin
from nomad_phase28.runtime import installer
from nomad_phase32.policy import CappedNA,normal_choice
from nomad_phase38.ec_normal import RTCWithEC
from nomad_phase53p.runtime import Execution as Handoff
from nomad_phase47c.runtime import install as frozen_install,run_without_oracle
from nomad_phase0.pure_pursuit import XYPath

class LatchedProfile(CappedNA):
    def replace_path(self,*args,**kw):
        super().replace_path(*args,**kw);self.endpoint_latched=False
    def control(self,pose,actual_v):
        if self.endpoint_latched:return (0.,0.),dict(completed=True,mode='ENDPOINT',target=0.,kappa=None,endpoint_latched=True,ec_speed_cap_m_s=self.speed_cap)
        command,diag=super().control(pose,actual_v)
        if diag['completed']:self.endpoint_latched=True
        return command,builtin(dict(diag,endpoint_latched=self.endpoint_latched))

def select_cons(primary,options,check,retained_cap=None,primary_rejected=False):
    """Rank only depth-safe candidates, then run the frozen full/slow/stop tiers.

    The heading constraint is relative to the same reference as the score.
    A full-speed passing backward option is considered only after every
    <=90degree full-speed option failed; the identical rule holds in slow tier.
    """
    B=np.asarray(primary['_cons_B']);endpoint=primary['_cons_reference_endpoint']
    ref=np.asarray(endpoint)-B[:2] if endpoint is not None else np.array([np.cos(B[2]),np.sin(B[2])])
    ref_yaw=float(np.arctan2(ref[1],ref[0])) if np.linalg.norm(ref)>1e-12 else float(B[2])
    ranked=[]
    for item in options:
        delta=np.asarray(item['path'])[-1]-B[:2]
        yaw=float(np.arctan2(delta[1],delta[0])) if np.linalg.norm(delta)>1e-12 else float(B[2])
        angle=abs(float(np.arctan2(np.sin(yaw-ref_yaw),np.cos(yaw-ref_yaw))))
        path=XYPath(item['path']);s,_=path.project(B[:2]);remaining=float(path.s[-1]-s)
        ranked.append((angle,-remaining,item['index'],item))
    ordered=[x[-1] for x in sorted(ranked,key=lambda x:x[:3])]
    if not ordered:return dict(item=None,cap=None,route='STOP_WAIT')
    # Preserve rejection of an already-failed active path at the current cap,
    # without accidentally excluding the new angular-primary candidate.
    def checked(item,cap):
        if primary_rejected and item['key']==primary['key'] and cap==retained_cap:return dict(passed=False)
        return check(item,cap)
    return normal_choice(ordered[0],ordered,checked,retained_cap,False)

class Execution(Handoff):
    def __init__(self,method,out,worker=None):
        super().__init__('CUT',out);self.cons_method=method;self.cons_endpoint=None
        if method=='CONS+G18':
            from nomad_night20261111.worker import Client
            self.ho_method='GRAPH-HO';self.ho_worker=worker if worker is not None else Client(out)
    def ec_options(self,*args,**kw):
        primary,options=super().ec_options(*args,**kw)
        # Frozen signature: primary,source_id,kind,pose,field,...
        primary['_cons_B']=np.asarray(args[3]).copy();primary['_cons_reference_endpoint']=self.cons_endpoint
        return primary,options
    def ec_install(self,*args,**kw):
        fn=Handoff.ec_install if self.cons_method=='CUT' else bind(Handoff.ec_install,normal_choice=select_cons)
        return fn(self,*args,**kw)
    def ec_check(self,pose,vw,path,field,t,state,scope,cap,controller=None):
        if controller is None:
            controller=LatchedProfile();controller.replace_path(path,pose,vw[0]);controller.speed_cap=cap
        return super().ec_check(pose,vw,path,field,t,state,scope,cap,controller)
    def record(self,event,**kw):
        if event=='INSTALL':
            kw.update(selection_method=self.cons_method,reference_endpoint_before=self.cons_endpoint,endpoint_latch=True)
            # Update from the actually installed endpoint, including Graph
            # corrections and EC fallback replacements; STOP does not update it.
            self.cons_endpoint=np.asarray(kw['path_world'])[-1].tolist()
            kw['reference_endpoint_after']=self.cons_endpoint
        return super().record(event,**kw)

class ProfileBridge(RTCWithEC):
    commit_path=installer(LatchedProfile)
class ConsExecution(Execution,ProfileBridge):pass

def install(config):
    frozen_install(config)
    from nomad_phase24.retention import retained_apply
    import nomad_phase15b.execution as factory
    import nomad_phase8.execution as overnight
    def make(c,out):return retained_apply(ConsExecution(c['phase58p_method'],out))
    factory.make_execution=make;overnight.OvernightExecution=make
    if config.get('h1v2'):
        from nomad_h1v2.scene import install_environment
        install_environment(config)
