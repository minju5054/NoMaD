"""Five-method wiring. J0 noEC and native sample0 executors remain reused."""
import json
import time
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase0.pure_pursuit import PurePursuit,XYPath
from nomad_phase4c.execution import AccelExecution
from nomad_phase12.gf_worker import CONTROL_CONFIG,numeric_job
from nomad_phase15b.depth import evaluate_samples
from nomad_phase17.worker import Client
from nomad_phase3_stage2.execution import decision
from nomad_phase16.execution import stop_command
from nomad_phase18raw.execution import RawExecution as FrozenRaw
from nomad_phase28.telemetry import builtin
from .execution import Execution as FrozenNoEC,install as common_install,run_without_oracle
from .ec import certify

class RawExecution(FrozenRaw):
    """Only the shared ENDPOINT latch is added to the exact sample0 executor."""
    def __init__(self,out):super().__init__(out);self.endpoint_latched=False
    def apply(self,core,refresh,switch):
        if switch is not None:self.endpoint_latched=False
        super().apply(core,refresh,switch)
        self.endpoint_latched=bool(self.endpoint_latched or refresh['pure_pursuit'].get('endpoint_stop'))
        if self.endpoint_latched:
            core.v=core.w=0.;self.last_command=[0.,0.]
            refresh.update(commanded_v_m_s=0.,commanded_w_rad_s=0.,applied_v_m_s=0.,applied_command_source='ENDPOINT')
            refresh['pure_pursuit']['stop_reason']='ENDPOINT'
        refresh['j_execution']=dict(method='NOMAD_RAW',endpoint_latched=self.endpoint_latched,recovery=False,stop_wait_special=False,EC=False)
        if switch is not None:switch.update({k:refresh[k] for k in ('j_execution','pure_pursuit','commanded_v_m_s','commanded_w_rad_s','applied_command_source')})

class SafeExecution(AccelExecution):
    def __init__(self,method,out,client=None):
        self.method_name=method;self.use_ec=method in ('OURS','OURS-noGRAPH');self.has_graph=method=='OURS'
        super().__init__(dict(CONTROL_CONFIG) if self.has_graph else dict(phase4c_method='CURV',plant_alpha='inf'),out,
                         (client if client is not None else Client(out,True)) if self.has_graph else None)
        self.depth_maps=None;self.snapshot=None;self.last_application_ns=None;self.path_received_ns=None;self.path_source_id=None
        self.active_sample=None;self.endpoint_latched=False;self.job_receipts={};self.graph_installed=None
        self.apps=(out/'j_applications.jsonl').open('x')
        self.ec_file=(out/'exec_cert.jsonl').open('x') if self.use_ec else None
        self.ec_due=None;self.ec_pending=None;self.ec_blocked=False;self.ec_generation=0;self.ec_sequence=0
    def record(self,row):super().record(builtin(row))
    def ec_log(self,event,**data):
        if self.ec_file:self.ec_file.write(json.dumps(builtin(dict(event=event,**data)),allow_nan=False)+'\n');self.ec_file.flush()
    def ec_check(self,path,pose,tick,scope,follower=None):
        field=self.depth_maps.snapshot();start=time.monotonic_ns()
        r=certify(pose,[self.last_command[0],self.plant.actual_w],path,field,tick,follower,
                  self.endpoint_latched if follower is not None else False)
        ident=self.ec_sequence;self.ec_sequence+=1
        row=dict(check_id=ident,scope=scope,generation=self.ec_generation,check_tick=tick,simulation_time_s=tick/72,
                 check_started_ns=start,check_finished_ns=time.monotonic_ns(),pose=np.asarray(pose).tolist(),
                 actual_vw=[self.last_command[0],self.plant.actual_w],snapshot=dict(field.metadata),path=np.asarray(path).tolist(),**r)
        self.ec_log('CHECK',**row);return row
    def install_notice(self,refresh,source,receipt,kind):
        self.path_source_id=source;self.path_received_ns=receipt;self.endpoint_latched=False
        self.last_application_ns=refresh['monotonic_ns']
        if self.use_ec:
            self.ec_generation+=1;self.ec_due=round(refresh['simulation_time_s']*72)+36
            self.ec_pending=None;self.ec_blocked=False
            self.ec_log('INSTALL',id=source,kind=kind,apply_tick=round(refresh['simulation_time_s']*72),generation=self.ec_generation)
    def application(self,core,refresh,kind,before,job=None):
        row=dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],id=self.active_id,
            path_source_id=self.path_source_id,kind=kind,graph_job_id=job,selected_sample=self.active_sample,pose=core.pose.tolist(),
            world_xy=self.follower.path.points.tolist(),before_vw=before,after_vw=self.last_command,depth_snapshot=dict(self.snapshot.metadata))
        self.apps.write(json.dumps(builtin(row),allow_nan=False)+'\n');self.apps.flush()
    def integrate_record(self,before,after):
        super().integrate_record(before,after)
        tick=self.plant.last_tick
        if self.use_ec and self.ec_due is not None and tick>=self.ec_due:
            self.ec_due+=36
            if self.follower is not None and not self.ec_blocked and self.ec_pending is None:
                r=self.ec_check(self.follower.path.points,after,tick,'PERIODIC',self.follower)
                if not r['passed']:self.ec_pending=r
    def collect(self,core,refresh,switch):
        if not self.client:return
        while True:
            r=self.client.poll()
            if r is None:break
            self.ready_results.append(r)
        eligible=[r for r in self.ready_results if r['result_received_ns']<=refresh['monotonic_ns']]
        self.ready_results=[r for r in self.ready_results if r['result_received_ns']>refresh['monotonic_ns']]
        for result in eligible:
            job=self.pending.pop(result['job_id']);receipt=self.job_receipts.pop(result['job_id'])
            status,stale,seconds=decision(result,core.latest['id'] if core.latest else -1,refresh['valid'])
            if status=='ACCEPTED' and switch is not None:status='SUPERSEDED'
            if status=='ACCEPTED':
                check=self.ec_check(np.asarray(result['poses'])[:,:2],core.pose,round(refresh['simulation_time_s']*72),'GRAPH_INSTALL')
                result=dict(result,ec_check_id=check['check_id'])
                if not check['passed']:status='EXEC_CERT_REJECT'
            row=dict(result,event='RESULT',disposition=status,stale_flag=stale,processing_wall_s=seconds,
                evaluated_sim_s=refresh['simulation_time_s'],boundary=job['boundary'],pose_at_result=core.pose.tolist(),
                movement_since_dispatch_m=job['distance_m'])
            if status=='ACCEPTED':
                xy=np.asarray(result['poses'])[:,:2];self.follower=PurePursuit(xy,self.settings['follower'])
                self.previous_accepted=xy.tolist();self.corrected=True;self.active_id=core.applied_id
                self.install_notice(refresh,result['id'],receipt,'GRAPH');self.graph_installed=result['job_id']
                row.update(applied_world_xy=xy.tolist(),applied_tick=round(refresh['simulation_time_s']*72))
            self.record(row)
    def dispatch(self,core,refresh,switch,selected,before):
        if not self.client:return
        job=dict(job_id=self.next_job,id=switch['id'],world_xy=selected.tolist(),boundary=core.pose.tolist(),
            previous_command=[before[0],self.plant.actual_w],previous_commanded_vw=before,previous_xy=self.previous_accepted,
            observation_pose=switch['observation_pose'],observation_sim_s=switch['observation_sim_s'],dispatch_ns=time.monotonic_ns(),
            switch_monotonic_ns=refresh['monotonic_ns'],switch_sim_s=refresh['simulation_time_s'],distance_m=0.)
        numeric_job(job);self.next_job+=1;self.pending[job['job_id']]=job;self.job_receipts[job['job_id']]=switch['received_monotonic_ns']
        self.record(dict(event='SUBMIT',**job,depth_snapshot=dict(self.snapshot.metadata)))
        self.client.snapshot_file=self.snapshot.metadata['file'];self.client.submit(dict(job))
    def apply(self,core,refresh,switch):
        tick=round(refresh['simulation_time_s']*72);before=list(self.last_command);self.graph_installed=None
        if self.ec_pending is not None:
            pending=self.ec_pending;self.ec_pending=None;delay=tick-pending['check_tick'];assert 0<=delay<=4
            if pending['generation']==self.ec_generation:self.ec_blocked=True
            self.ec_log('PERIODIC_APPLY',check_id=pending['check_id'],check_tick=pending['check_tick'],apply_tick=tick,
                delay_ticks=delay,delay_ms=delay/72*1000,action='BRAKE_KEEP_PATH')
        self.collect(core,refresh,switch)
        selected=None;safe=False;install=False;original=None
        if switch is not None:
            self.snapshot=self.depth_maps.snapshot();switch['j_selection_ns']=time.monotonic_ns()
            worlds=np.array([local_to_world(np.asarray(x),switch['observation_pose']) for x in switch['overnight_metric_samples']])
            selected,detail=evaluate_samples(worlds,core.pose,self.snapshot);safe=not detail['all_unsafe']
            if safe:
                try:XYPath(selected)
                except ValueError:safe=False
            install=safe
            if safe and self.use_ec:install=self.ec_check(selected,core.pose,tick,'SAFE_INSTALL')['passed']
            switch['j_selection']=dict(detail,installed=bool(install),disposition='SAFE_SELECTED' if install else 'EC_REJECT_KEEP_CURRENT' if safe else 'NO_SAFE_KEEP_CURRENT',oracle_used=False)
            if install:
                original=switch['chunk'];switch['chunk']=dict(original,world_xy_m=selected.tolist(),path_valid=True)
                self.active_sample=detail['selected_sample'];self.install_notice(refresh,switch['id'],switch['received_monotonic_ns'],'SAFE')
            else:self.active_id=switch['id']
        refresh['j_latest_chunk_valid']=refresh['valid']
        if self.path_received_ns is not None and refresh['monotonic_ns']-self.path_received_ns>=1_000_000_000:refresh.update(valid=False,status='expired')
        # The protected Phase18 controller/plant, without a second Graph poll or
        # dispatch. Numerical jobs use the exact frozen worker below.
        client=self.client;self.client=None
        try:super().apply(core,refresh,switch if install else None)
        finally:
            self.client=client
            if original is not None:switch['chunk']=original
        self.endpoint_latched=bool(self.endpoint_latched or refresh['pure_pursuit'].get('endpoint_stop'))
        if self.ec_blocked:
            core.v,core.w=stop_command(before[0]);self.last_command=[core.v,core.w]
            refresh['pure_pursuit']['stop_reason']='EC_BRAKE'
            refresh.update(commanded_v_m_s=core.v,commanded_w_rad_s=core.w,applied_v_m_s=core.v,applied_command_source='EC_BRAKE')
        elif self.endpoint_latched:
            core.v=core.w=0.;self.last_command=[0.,0.]
            refresh['pure_pursuit']['stop_reason']='ENDPOINT'
            refresh.update(commanded_v_m_s=0.,commanded_w_rad_s=0.,applied_v_m_s=0.,applied_command_source='ENDPOINT')
        refresh['stage2']['graph_applied_job']=self.graph_installed
        refresh['j_execution']=dict(method=self.method_name,endpoint_latched=self.endpoint_latched,path_source_id=self.path_source_id,
            path_received_ns=self.path_received_ns,recovery=False,stop_wait_special=False,EC=self.use_ec,ec_blocked=self.ec_blocked)
        if switch is not None:switch.update({k:refresh[k] for k in ('commanded_v_m_s','commanded_w_rad_s','applied_v_m_s','applied_command_source','pure_pursuit','stage2','j_execution')})
        if install or self.graph_installed is not None:self.application(core,refresh,'GRAPH' if self.graph_installed is not None else 'SAFE',before,self.graph_installed)
        # A rejected raw interim path does not suppress the safe candidate's
        # Graph attempt. Its output still needs frozen acceptance + fresh EC.
        if switch is not None and safe:self.dispatch(core,refresh,switch,selected,before)
    def close(self):
        try:super().close()
        finally:
            self.apps.close()
            if self.ec_file:self.ec_file.close()

def install(c):
    common_install(c)
    import nomad_phase15b.execution as factory
    def make(config,out):
        m=config['j_method']
        if m=='OURS-noEC':return FrozenNoEC(out)
        if m=='NOMAD_RAW':return RawExecution(out)
        return SafeExecution(m,out)
    factory.make_execution=make
