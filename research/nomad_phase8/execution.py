"""Subclass hook: unchanged CURV/Graph scheduling and explicit selected/spliced paths."""
import copy
import json
import threading
import time
import numpy as np
from nomad_phase4c.execution import AccelExecution
from nomad_phase0.chunk_execution import describe_chunk
from nomad_phase6.selection import select as original_select
from nomad_phase2.config import native_safety
from nomad_isaac.common import local_to_world
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase9.intent import intention,splice

def select(samples,observation_pose,boundary,config):
    if config['obstacles']:return original_select(samples,observation_pose,boundary,config)
    # Same rule in the obstacle-free domain, where legacy min(empty) is undefined.
    worlds=[local_to_world(np.asarray(x),np.asarray(observation_pose)) for x in samples];candidates=[]
    for i,xy in enumerate(worlds):
        safety=native_safety(xy,config)
        try:
            path=XYPath(xy);s,d=path.project(np.asarray(boundary)[:2]);remaining=float(path.s[-1]-s)
        except ValueError:s=d=remaining=None
        candidates.append(dict(index=i,**safety,path_valid=remaining is not None,projected_arclength_m=s,projection_distance_m=d,remaining_length_m=remaining))
    safe=[x for x in candidates if x['safe'] and x['path_valid']]
    index=min(safe,key=lambda x:(-x['remaining_length_m'],x['index']))['index'] if safe else 0
    return worlds[index],dict(selected_sample=index,all_unsafe=not bool(safe),candidates=candidates,anchor='observation_pose',selection_boundary=np.asarray(boundary).tolist())

class OvernightExecution(AccelExecution):
    def __init__(self,config,out,client=None):
        if config['overnight_method']=='GRAPH-v6' and client is None:
            from nomad_phase9.worker import Client
            client=Client(out)
        super().__init__(config,out,client)
        self.original_config=config;self.named_method=config['overnight_method']
        self.public=None;self.public_lock=threading.Lock()
        self.oracle=(out/'overnight_oracle.jsonl').open('x')
        self.applications=(out/'phase6_applications.jsonl').open('x')
        self.active_sample=0;self.last_application_ns=None
    def publish(self,gate,box):
        if not gate['geometry_available'] or box is None:return
        with self.public_lock:
            if self.public is None:
                import time
                self.public={'obstacle':copy.deepcopy(box),'gate':copy.deepcopy(gate),'publication_monotonic_ns':time.monotonic_ns(),'consumer':self.named_method,'control_usage':'SELECT/intent/Graph only; CURV ignores oracle'}
                self.oracle.write(json.dumps(self.public)+'\n');self.oracle.flush()
    def public_config(self):
        c=copy.deepcopy(self.original_config);c.pop('dynamic_obstacle',None)
        with self.public_lock:
            p=copy.deepcopy(self.public);snapshot_ns=time.monotonic_ns()
        if p:c['obstacles'].append(p['obstacle'])
        return c,p,snapshot_ns
    def apply(self,core,refresh,switch):
        before=list(self.last_command);original=None;detail=None
        public,gate,geometry_ns=self.public_config();intent=intention(public,core.pose) if self.original_config['overnight_phase']==9 else None
        public['public_intent']=intent;public['geometry_snapshot_monotonic_ns']=geometry_ns;self.config=public
        if switch is not None:
            original=switch['chunk'];xy=np.asarray(original['world_xy_m']);self.active_sample=0
            if self.named_method in ('SELECT','SELECT+GRAPH'):
                xy,detail=select(switch['overnight_metric_samples'],switch['observation_pose'],core.pose,public)
                self.active_sample=detail['selected_sample']
            elif self.named_method=='INTENT-SPLICE' and intent:
                xy=splice(core.pose,intent)
            try:XYPath(xy);path_valid=True
            except ValueError:path_valid=False
            switch['chunk']={**original,'world_xy_m':xy.tolist(),'path_valid':path_valid}
            switch['overnight']=dict(method=self.named_method,selection=detail,intent=intent,
                public_obstacle_ids=[b['id'] for b in public['obstacles']],oracle_gate=gate,geometry_snapshot_monotonic_ns=geometry_ns,
                applied_initial_world_xy=xy.tolist(),selected_sample=self.active_sample)
        try:super().apply(core,refresh,switch)
        finally:
            self.config=self.original_config
            if original is not None:switch['chunk']=original
        refresh['overnight_method']=self.named_method
        graph_job=refresh['stage2']['graph_applied_job']
        if switch is not None or graph_job is not None:
            path=self.follower.path if self.follower is not None else None
            s,d=path.project(core.pose[:2]) if path else (None,None)
            row=dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],monotonic_ns=refresh['monotonic_ns'],id=self.active_id,pose=core.pose.tolist(),
                kind='GRAPH' if graph_job is not None else 'SELECT' if detail is not None else 'INTENT-SPLICE' if self.named_method=='INTENT-SPLICE' and intent else 'RAW',
                graph_job_id=graph_job,selected_sample=self.active_sample,world_xy=path.points.tolist() if path else None,path_length_m=float(path.s[-1]) if path else None,
                projected_arclength_m=s,projection_distance_m=d,staleness=float(s/path.s[-1]) if path else None,before_vw=before,after_vw=list(self.last_command),abs_dw=abs(self.last_command[1]-before[1]))
            self.last_application_ns=refresh['monotonic_ns']
            self.applications.write(json.dumps(row)+'\n');self.applications.flush()
    def close(self):
        self.applications.close();self.oracle.close();super().close()
