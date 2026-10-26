"""Depth-only selection and isolated immutable Graph dispatch, unchanged scheduler."""
import json
import time
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase4c.execution import AccelExecution
from nomad_phase13.execution import FreshestExecution
from nomad_phase12.execution import BaselineExecution
from nomad_phase8.execution import OvernightExecution
from nomad_phase12.gf_worker import CONTROL_CONFIG,numeric_job
from .config import SAFE
from .depth import evaluate_samples
from .worker import Client

def make_execution(config,out):
    m=config['phase15b_method'];control=dict(phase12_method=m,phase4c_method='CURV',plant_alpha='inf')
    if m=='FRESHEST':return FreshestExecution(control,out)
    if m=='TEMPORAL-ENSEMBLE':return BaselineExecution(control,out)
    if m=='SELECT+GRAPH':return OvernightExecution({**config,'overnight_method':'SELECT+GRAPH'},out)
    return SafeExecution(m,out)

def capped_command(kappa,previous_v):
    target=min(.10,float(np.clip(.4/abs(kappa),.05,.3)) if kappa else .3)
    v=float(np.clip(target,max(.05,previous_v-.5/9),min(.3,previous_v+.5/9)))
    return [v,float(np.clip(v*kappa,-.4,.4))],target

class SafeExecution(AccelExecution):
    def __init__(self,method,out,client=None):
        assert method in SAFE
        graph='GRAPH' in method
        super().__init__(dict(CONTROL_CONFIG) if graph else dict(phase4c_method='CURV',plant_alpha='inf'),out,(client or Client(out,method==SAFE[2])) if graph else None)
        self.last_application_ns=None
        self.named_method=method;self.depth_maps=None;self.cap=False;self.snapshot=None;self.active_sample=0
        self.applications=(out/'phase6_applications.jsonl').open('x');self.oracle=(out/'overnight_oracle.jsonl').open('x')
    def record(self,row):
        if row['event']=='SUBMIT':
            row={'event':'SUBMIT',**numeric_job({k:v for k,v in row.items() if k!='event'})}
            row['depth_snapshot']=dict(self.snapshot.metadata)
        if row['event']=='APPLIED_COMMAND':
            self.override_cap(self._core,self._refresh,None,self._before)
            row={**row,'after_vw':list(self.last_command),'all_unsafe_cap':self.cap}
        super().record(row)
    def override_cap(self,core,refresh,switch,before):
        if self.cap and refresh['pure_pursuit']['stop_reason'] is None:
            k=refresh['stage2']['kappa_pp'];command,target=capped_command(k,before[0]);core.v,core.w=command;self.last_command=command
            refresh.update(commanded_v_m_s=core.v,commanded_w_rad_s=core.w,applied_v_m_s=core.v)
            refresh['stage2'].update(v_target_m_s=target,ACCEL_LIMITED=abs(target-core.v)>1e-12,OMEGA_CLIPPED=abs(core.w-core.v*k)>1e-12)
        refresh['depth_fallback_cap_active']=self.cap
        if switch is not None:
            for k in ('commanded_v_m_s','commanded_w_rad_s','applied_v_m_s','stage2','depth_fallback_cap_active'):switch[k]=refresh[k]
            switch['chunk_transition'].update(command_after=list(self.last_command),command_delta=(np.array(self.last_command)-before).tolist())
    def apply(self,core,refresh,switch):
        before=list(self.last_command);self._core=core;self._refresh=refresh;self._before=before
        original=None;detail=None
        if switch is not None:
            self.snapshot=self.depth_maps.snapshot()
            switch["phase15b_selection_monotonic_ns"]=time.monotonic_ns()
            samples=np.array([local_to_world(np.asarray(x),np.asarray(switch['observation_pose'])) for x in switch['overnight_metric_samples']])
            xy,detail=evaluate_samples(samples,core.pose,self.snapshot)
            self.active_sample=detail['selected_sample'];self.cap=detail['all_unsafe']
            if self.client:self.client.snapshot_file=self.snapshot.metadata['file']
            original=switch['chunk']
            try:XYPath(xy);valid=True
            except ValueError:valid=False
            switch['chunk']={**original,'world_xy_m':xy.tolist(),'path_valid':valid}
            switch['phase15b']=dict(method=self.named_method,detail=detail,applied_initial_world_xy=xy.tolist(),oracle_used=False)
        try:super().apply(core,refresh,switch)
        finally:
            if original is not None:switch['chunk']=original
        self.override_cap(core,refresh,switch,before)
        graph_job=refresh['stage2']['graph_applied_job']
        if switch is not None or graph_job is not None:
            path=self.follower.path if self.follower else None;s,d=path.project(core.pose[:2]) if path else (None,None)
            row=dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],monotonic_ns=refresh['monotonic_ns'],id=self.active_id,pose=core.pose.tolist(),kind='GRAPH' if graph_job is not None else 'FRESHEST-SAFE',graph_job_id=graph_job,selected_sample=self.active_sample,world_xy=path.points.tolist() if path else None,path_length_m=float(path.s[-1]) if path else None,projected_arclength_m=s,projection_distance_m=d,staleness=float(s/path.s[-1]) if path else None,before_vw=before,after_vw=list(self.last_command),abs_dw=abs(self.last_command[1]-before[1]),oracle_used=False,all_unsafe=self.cap,depth_snapshot=dict(self.snapshot.metadata))
            self.applications.write(json.dumps(row)+'\n');self.applications.flush();self.last_application_ns=refresh['monotonic_ns']
    def close(self):
        self.applications.close();self.oracle.close();super().close()
