"""FRESHEST selection + oracle-free v4; inherits the existing online scheduler."""
import json
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase4c.execution import AccelExecution
from .methods import GF,freshest
from .gf_worker import Client,CONTROL_CONFIG,numeric_job

class GFExecution(AccelExecution):
    def __init__(self,config,out,client=None):
        assert config['phase12_method']==GF and config['phase4c_method']=='GRAPH' and config['plant_alpha']=='inf'
        # Whitelist before entering the controller or any optimizer dispatch.
        super().__init__(dict(CONTROL_CONFIG),out,client or Client(out))
        self.last_application_ns=None;self.active_sample=0
        self.applications=(out/'phase6_applications.jsonl').open('x')
        self.oracle=(out/'overnight_oracle.jsonl').open('x')
    def record(self,row):
        if row['event']=='SUBMIT':row={'event':'SUBMIT',**numeric_job({k:v for k,v in row.items() if k!='event'})}
        super().record(row)
    def apply(self,core,refresh,switch):
        before=list(self.last_command);original=None;detail=None
        if switch is not None:
            original=switch['chunk']
            samples=np.array([local_to_world(np.asarray(x),np.asarray(switch['observation_pose'])) for x in switch['overnight_metric_samples']])
            xy,detail=freshest(samples,core.pose);self.active_sample=detail['selected_sample']
            try:XYPath(xy);valid=True
            except ValueError:valid=False
            switch['chunk']={**original,'world_xy_m':xy.tolist(),'path_valid':valid}
            switch['phase12']=dict(method=GF,detail=detail,applied_initial_world_xy=xy.tolist(),oracle_used=False)
        try:super().apply(core,refresh,switch)
        finally:
            if original is not None:switch['chunk']=original
        refresh['phase12_method']=GF;graph_job=refresh['stage2']['graph_applied_job']
        if switch is not None or graph_job is not None:
            path=self.follower.path if self.follower is not None else None;s,d=path.project(core.pose[:2]) if path else (None,None)
            row=dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],monotonic_ns=refresh['monotonic_ns'],
                id=self.active_id,pose=core.pose.tolist(),kind='GRAPH-GF' if graph_job is not None else 'FRESHEST',graph_job_id=graph_job,
                selected_sample=self.active_sample,world_xy=path.points.tolist() if path else None,path_length_m=float(path.s[-1]) if path else None,
                projected_arclength_m=s,projection_distance_m=d,staleness=float(s/path.s[-1]) if path else None,
                before_vw=before,after_vw=list(self.last_command),abs_dw=abs(self.last_command[1]-before[1]),oracle_used=False)
            self.applications.write(json.dumps(row)+'\n');self.applications.flush();self.last_application_ns=refresh['monotonic_ns']
    def close(self):
        self.oracle.close();self.applications.close();super().close()
