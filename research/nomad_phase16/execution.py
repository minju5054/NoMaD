"""Phase16-only fallback wrapper; original PP, CURV, Graph and timeout core unchanged."""
import json,time
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase4c.execution import AccelExecution
from nomad_phase12.execution import BaselineExecution
from nomad_phase12.methods import TransitionState
from nomad_phase4c.plant import control_command
from nomad_phase12.gf_worker import numeric_job,CONTROL_CONFIG
from nomad_phase15.evaluate import suffix,sample_path
from nomad_phase15b.depth import evaluate_samples
from nomad_phase15b.worker import Client
from .config import METHODS,SAFE

def fallback(active_xy,pose,field):
    if active_xy is not None:
        path,length=suffix(np.array(active_xy),pose);q,ds=sample_path(path)
        gap=float(field.query(q)[0].min()-field.error_bound-ds/2)
        if gap>=.025 and length>=.25:return 'KEEP_ACTIVE',dict(clearance_m=gap,remaining_length_m=length)
        return 'STOP_WAIT',dict(clearance_m=gap,remaining_length_m=length)
    return 'STOP_WAIT',dict(clearance_m=None,remaining_length_m=0.)

def stop_command(previous_v):
    return [max(0.,previous_v-.5/9),0.]

def filter_ensemble(ensemble,pose,field,now_ns):
    """Only called on ALL_UNSAFE: expire, inspect each suffix, keep survivors."""
    expired=[];removed=[];kept=[];checks=[]
    for chunk in ensemble.chunks:
        if not 0<=now_ns-chunk['received_ns']<1_000_000_000:
            expired.append(chunk['id']);continue
        mode,detail=fallback(chunk['follower'].path.points,pose,field)
        checks.append(dict(id=chunk['id'],keep=mode=='KEEP_ACTIVE',**detail))
        (kept if mode=='KEEP_ACTIVE' else removed).append(chunk)
    ensemble.chunks=kept
    # TemporalTargets.control retains order and recomputes exp(-.5k) weights;
    # no waypoint timing, chunk reception time, or progress is reset here.
    return ('KEEP_ACTIVE' if kept else 'STOP_WAIT'),dict(kept_chunk_ids=[x['id'] for x in kept],
        removed_chunk_ids=[x['id'] for x in removed],removed_chunk_count=len(removed),
        expired_chunk_ids=expired,expired_chunk_count=len(expired),total_removed_chunk_count=len(removed)+len(expired),checks=checks)

class SafeExecution(AccelExecution):
    def __init__(self,method,out,client=None):
        graph='GRAPH' in method
        super().__init__(dict(CONTROL_CONFIG) if graph else dict(phase4c_method='CURV',plant_alpha='inf'),out,
                         (client or Client(out,method=='FRESHEST-SAFE+GRAPH-depth')) if graph else None)
        self.named_method=method;self.depth_maps=None;self.last_application_ns=None
        self.snapshot=None;self.active_sample=0;self.path_source_id=None;self.mode='NORMAL'
        adaptation={'FRESHEST-SAFE+HERMITE':'HERMITE-SPLICE','FRESHEST-SAFE+TEMPORAL-ENSEMBLE':'TEMPORAL-ENSEMBLE'}.get(method)
        self.transition=TransitionState(adaptation) if adaptation else None
        self.apps=(out/'phase16_applications.jsonl').open('x');self.fallback_log=(out/'fallback.jsonl').open('x')
    def record(self,row):
        if row['event']=='SUBMIT':
            row={'event':'SUBMIT',**numeric_job({k:v for k,v in row.items() if k!='event'}),'depth_snapshot':dict(self.snapshot.metadata)}
        super().record(row)
    def apply(self,core,refresh,switch):
        before=list(self.last_command);original=None;detail=None;decision=None;keep=switch is not None
        if switch is not None:
            self.snapshot=self.depth_maps.snapshot();switch['phase16_selection_ns']=time.monotonic_ns()
            worlds=np.array([local_to_world(np.array(x),switch['observation_pose']) for x in switch['overnight_metric_samples']])
            selected,detail=evaluate_samples(worlds,core.pose,self.snapshot)
            original=switch['chunk'];self.active_sample=detail['selected_sample']
            if detail['all_unsafe']:
                if self.transition and self.transition.method=='TEMPORAL-ENSEMBLE':
                    self.mode,decision=filter_ensemble(self.transition.ensemble,core.pose,self.snapshot,refresh['monotonic_ns'])
                    if self.transition.ensemble.chunks:
                        retained=self.transition.ensemble.chunks[-1]
                        self.follower=retained['follower'];self.path_source_id=retained['id']
                    else:self.follower=None;self.path_source_id=None
                else:
                    old=self.follower.path.points if self.follower else None
                    self.mode,decision=fallback(old,core.pose,self.snapshot)
                # Keep the active geometric path AND its progress, but not an old
                # prediction's validity clock. The unchanged timing core consumes
                # this actual FRESH; KEEP_ACTIVE is logged as an explicit override.
                self.active_id=switch['id'];keep=False
                self.fresh_switch_s=refresh['simulation_time_s']
                self.fallback_log.write(json.dumps(dict(id=switch['id'],simulation_time_s=refresh['simulation_time_s'],mode=self.mode,path_source_id=self.path_source_id,**decision))+'\n');self.fallback_log.flush()
            else:
                self.mode='NORMAL';self.path_source_id=switch['id']
                if self.transition:
                    selected,adaptation=self.transition.switch(np.repeat(selected[None],8,axis=0),core.pose,switch['id'],switch['received_monotonic_ns'],refresh['monotonic_ns'])
                    switch['phase16_transition']=adaptation
                try:XYPath(selected);valid=True
                except ValueError:valid=False
                switch['chunk']={**original,'world_xy_m':selected.tolist(),'path_valid':valid}
                if self.client:self.client.snapshot_file=self.snapshot.metadata['file']
            switch['phase16']=dict(method=self.named_method,selection=detail,fallback_mode=self.mode,fallback=decision,path_source_id=self.path_source_id,oracle_used=False)
        try:super().apply(core,refresh,switch if keep else None)
        finally:
            if original is not None:switch['chunk']=original
        if self.transition and self.transition.method=='TEMPORAL-ENSEMBLE':
            diag,ensemble=self.transition.ensemble.control(core.pose,refresh['monotonic_ns'])
            pp=refresh['pure_pursuit'];reason=refresh['status'] if not refresh['valid'] else 'no_valid_chunk' if diag is None else 'endpoint' if diag['endpoint_stop'] else None
            command=(0.,0.);kappa=None;flags={}
            if diag is not None:pp.update(diag)
            pp.update(stop_reason=reason,path_valid=diag is not None)
            if reason is None:
                x,y=diag['target_local_x_m'],diag['target_local_y_m'];kappa=2*y/(x*x+y*y) if x*x+y*y>1e-24 else 0.
                command,flags=control_command('CURV',kappa,before[0],self.plant.actual_w,self.plant.alpha)
            core.v,core.w=command;self.last_command=list(command)
            refresh.update(commanded_v_m_s=core.v,commanded_w_rad_s=core.w,applied_v_m_s=core.v,applied_command_source=self.named_method if reason is None else reason,phase16_ensemble=ensemble)
            refresh['stage2'].update(**flags,kappa_pp=kappa)
        if self.mode=='STOP_WAIT' and refresh['valid']:
            core.v,core.w=stop_command(before[0]);self.last_command=[core.v,core.w]
            refresh.update(commanded_v_m_s=core.v,commanded_w_rad_s=core.w,applied_v_m_s=core.v,applied_command_source='STOP_WAIT')
            refresh['stage2'].update(v_target_m_s=0.,ACCEL_LIMITED=core.v>0.)
        refresh['phase16_fallback_mode']=self.mode
        if switch is not None:
            switch.update({k:v for k,v in refresh.items() if k in ('pure_pursuit','stage2','commanded_v_m_s','commanded_w_rad_s','applied_v_m_s','applied_w_rad_s','phase16_fallback_mode')})
        job=refresh['stage2']['graph_applied_job']
        if switch is not None or job is not None:
            path=self.follower.path if self.follower else None
            row=dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],monotonic_ns=refresh['monotonic_ns'],id=self.active_id,
                path_source_id=self.path_source_id,kind='GRAPH' if job is not None else self.mode,graph_job_id=job,pose=core.pose.tolist(),selected_sample=self.active_sample,
                world_xy=path.points.tolist() if path else None,depth_snapshot=dict(self.snapshot.metadata),before_vw=before,after_vw=list(self.last_command),fallback_mode=self.mode)
            if 'phase16_ensemble' in refresh:row.update(ensemble_components=refresh['phase16_ensemble']['components'],world_xy_role='latest selected chunk only; ensemble has no single path')
            self.apps.write(json.dumps(row)+'\n');self.apps.flush();self.last_application_ns=refresh['monotonic_ns']
    def close(self):
        self.apps.close();self.fallback_log.close();super().close()

def make_execution(config,out):
    m=config['phase15b_method'];assert config['phase16'] and m in METHODS
    if m in SAFE:return SafeExecution(m,out)
    if m=='TEMPORAL-ENSEMBLE':return BaselineExecution(dict(phase12_method=m,phase4c_method='CURV',plant_alpha='inf'),out)
    raise ValueError(f'Unsupported Phase16 method: {m}')

def install_runtime_adapters():
    """Process-local dependency injection only; never edits an imported source file."""
    import nomad_phase15b.execution as old
    import nomad_phase15b.depth as olddepth
    import nomad_isaac.clearance as clearance
    from .depth import DepthMapThread
    from .geometry import corridor_clearance
    old.make_execution=make_execution;olddepth.DepthMapThread=DepthMapThread
    clearance.corridor_clearance=corridor_clearance
