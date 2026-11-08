"""Only new method adapters; the five Phase35 methods retain their factory."""
import json
import numpy as np
from nomad_phase35 import runtime as frozen
from nomad_phase24.retention import retained_apply
from nomad_phase28.alignment import NoAlignment
from nomad_phase28.telemetry import builtin
from .ec_normal import RTCWithEC,TEWithEC
from .care import correct,SAFE_FOV
from .care_depth import CareFrames
from . import scenes

run_without_oracle=frozen.run_without_oracle

class CareProfile(NoAlignment):
    def control(self,pose,actual_v):
        if self.care_waypoint is not None:
            delta=self.care_waypoint-np.asarray(pose)[:2];target=float(np.arctan2(delta[1],delta[0]))
            error=float((target-pose[2]+np.pi)%(2*np.pi)-np.pi)
            # The explicitly specified CARE gate commands v=0 immediately.
            # The >90deg NA departure rule is replaced only for a CARE path.
            self.mode='GO';self.target_yaw=None
            if abs(error)>SAFE_FOV:
                return (0.,float(np.clip(9*error,-.4,.4))),dict(completed=False,mode='ROTATE',
                    target=0.,kappa=None,care_safe_fov_active=True,care_heading_error_rad=error)
        result,diag=super().control(pose,actual_v)
        return result,builtin(dict(diag,care_safe_fov_active=False))

class CareExecution(frozen.RawNA):
    def __init__(self,out):super().__init__(out);self.care_log=(out/'care.jsonl').open('x')
    def new_path(self,path,core,refresh,source_id,kind):
        frame=self.depth_maps.snapshot();updated,detail=correct(path,core.pose,frame.points_world)
        super().new_path(updated,core,refresh,source_id,kind)
        profile=object.__new__(CareProfile);profile.__dict__.update(self.sp.__dict__)
        profile.care_waypoint=np.asarray(updated[detail['selected_waypoint']]) if detail['selected_waypoint'] is not None else None
        if detail['obstacles']:profile.mode='GO';profile.target_yaw=None
        self.sp=profile
        self.care_log.write(json.dumps(builtin(dict(event='CORRECTION',id=source_id,tick=round(refresh['simulation_time_s']*72),
            sample=0,original_path=np.asarray(path).tolist(),corrected_path=updated.tolist(),depth_frame=dict(frame.metadata),**detail)),allow_nan=False)+'\n');self.care_log.flush()
    def write_command(self,core,refresh,switch,before,nominal,source,diag):
        super().write_command(core,refresh,switch,before,nominal,source,diag)
        if switch is not None:switch['phase38_care']=dict(sample=0,depth_for_care_only=True,depth_filter=False,freshest_selection=False,recovery=False,ec=False,detour=False)
        if diag.get('care_safe_fov_active'):
            self.care_log.write(json.dumps(builtin(dict(event='SAFE_FOV',tick=round(refresh['simulation_time_s']*72),mode=diag['mode'],command=[core.v,core.w])),allow_nan=False)+'\n');self.care_log.flush()
    def close(self):
        try:super().close()
        finally:self.care_log.close()

def make_execution(config,out):
    method=config['phase38_method']
    if method in ('NOMAD_RAW','TE','RTC','ASTAR+EC','OURS'):return frozen.make_execution(config,out)
    if method=='CARE':execution=CareExecution(out)
    elif method=='TE+EC':execution=TEWithEC(out);execution.ec_te_mode=config['phase38_ec']['te_rollout']
    elif method in ('RTC+EC','OURS-DETOUR'):execution=RTCWithEC(out)
    else:raise ValueError(method)
    return retained_apply(execution)

def install(config):
    frozen.install(config);scenes.install(config)
    import nomad_phase15b.execution as factory
    import nomad_phase8.execution as overnight
    factory.make_execution=make_execution
    previous=overnight.OvernightExecution
    overnight.OvernightExecution=lambda c,out:make_execution(c,out) if c.get('phase38') else previous(c,out)
    if config['phase38_method']=='CARE':
        import nomad_phase15b.depth as depth
        depth.DepthMapThread=CareFrames
