"""SO opt-in executor: shared SAFE/SP/alignment/recovery, repair only on ALL_UNSAFE."""
import ast,inspect,json,time
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase15b.depth import evaluate_samples
from nomad_phase16.execution import fallback,stop_command
from nomad_phase17.execution import SafeExecution as RecoveryBase
from nomad_phase17.recovery import OMEGA
from nomad_phase19r.evaluate import clean
from .execution import SPAlignment
from .worker import RepairWorker,disposition


class Execution(RecoveryBase):
    def __init__(self,method,out):
        super().__init__('FRESHEST-SAFE',out)
        self.named_method=method;self.sp=None;self.path_kind=None;self.repair_worker=RepairWorker() if method=='M2_REPAIR' else None
        self.repair_pending=None;self.next_repair=0;self.repair_active=False;self.await_repair_fresh=False
        self.repair_log=(out/'repair.jsonl').open('x');self.command_log=(out/'phase20_commands.jsonl').open('x')
        self.jobs_dir=out/'repair_jobs';self.jobs_dir.mkdir();self.out=out

    def rlog(self,event,**data):
        self.repair_log.write(json.dumps(clean(dict(event=event,**data)),allow_nan=False)+'\n');self.repair_log.flush()

    def new_path(self,path,core,refresh,source_id,kind):
        self.sp=SPAlignment();self.sp.replace_path(path,core.pose,self.last_command[0]);self.follower=self.sp.follower
        self.path_source_id=source_id;self.path_kind=kind;self.mode='NORMAL';self.last_application_ns=refresh['monotonic_ns']
        self.repair_active=kind=='REPAIR'
        self.rlog('PATH_APPLIED',kind=kind,id=source_id,tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],
                  pose=core.pose.tolist(),previous_vw=self.last_command,path_world=self.follower.path.points.tolist(),alignment=self.sp.trigger_S,
                  heading_error_deg=self.sp.initial_heading_error_deg,threshold_deg=self.sp.alignment_threshold_deg,plan=self.sp.plan)

    def use_fallback(self,core,refresh):
        self.snapshot=self.depth_maps.snapshot()
        self.mode,detail=fallback(self.follower.path.points if self.follower else None,core.pose,self.snapshot)
        self.repair_active=False
        self.fallback_log.write(json.dumps(dict(id=self.active_id,simulation_time_s=refresh['simulation_time_s'],mode=self.mode,
            path_source_id=self.path_source_id,**detail))+'\n');self.fallback_log.flush()
        self.recovery.decision(self.mode)
        return detail

    def collect_repair(self,core,refresh,switch):
        if not self.repair_worker:return None
        delivered=[]
        while True:
            result=self.repair_worker.poll()
            if result is None:break
            delivered.append(result)
        found=None
        for result in delivered:
            if self.repair_pending and result['job_id']==self.repair_pending['job_id']:found=result
            else:self.rlog('LATE_RESULT',**result)
        if self.repair_pending is None:return None
        job=self.repair_pending;now=time.monotonic_ns()
        status=disposition(found,job['dispatch_ns'],now)
        if switch is not None:status='SUPERSEDED'
        if status=='WAIT':return None
        self.repair_pending=None
        if status=='ACCEPTED' and not refresh['valid']:status='WAYPOINT_TIMEOUT'
        if status=='ACCEPTED':
            chosen=found['results'][found['selected_sample']]
            self.new_path(chosen['path'],core,refresh,job['id'],'REPAIR');self.await_repair_fresh=True;self.recovery.decision('NORMAL')
        elif switch is None:self.use_fallback(core,refresh)
        self.rlog('RESULT',job_id=job['job_id'],id=job['id'],disposition=status,simulation_time_s=refresh['simulation_time_s'],
            wait_s=(now-job['dispatch_ns'])/1e9,pose_at_dispatch=job['B'],pose_at_result=core.pose.tolist(),
            movement_m=float(np.linalg.norm(core.pose[:2]-np.array(job['B'])[:2])),numeric_result=found)
        return status

    def apply(self,core,refresh,switch):
        before=list(self.last_command);nominal=[core.v,core.w];state=self.recovery.state
        if state=='WAIT_FRESH' and switch is not None:self.recovery.state='NORMAL';self.mode='STOP_WAIT'
        elif state in ('RECOVER_ROTATE','WAIT_FRESH'):
            if switch is not None:self.active_id=switch['id'];switch['phase17_selection_deferred']=True
            self.override(core,refresh,switch);self.write_command(core,refresh,switch,before,nominal,state,{})
            return
        repair_status=self.collect_repair(core,refresh,switch);decision=None;detail=None
        if switch is not None:
            self.active_id=switch['id'];self.fresh_switch_s=refresh['simulation_time_s'];self.repair_active=False
            self.snapshot=self.depth_maps.snapshot();switch['phase16_selection_ns']=time.monotonic_ns()
            worlds=np.array([local_to_world(np.array(x),switch['observation_pose']) for x in switch['overnight_metric_samples']])
            selected,detail=evaluate_samples(worlds,core.pose,self.snapshot);self.active_sample=detail['selected_sample']
            if self.await_repair_fresh:
                self.rlog('FIRST_FRESH_AFTER_REPAIR',id=switch['id'],simulation_time_s=refresh['simulation_time_s'],safe_sample_count=sum(c['safe'] for c in detail['candidates']))
                self.await_repair_fresh=False
            if self.recovery.awaiting_outcome:
                self.recovery_record('FIRST_FRESH',id=switch['id'],simulation_time_s=refresh['simulation_time_s'],safe_sample_count=sum(c['safe'] for c in detail['candidates']))
                self.recovery.awaiting_outcome=False
            if not detail['all_unsafe']:
                self.new_path(selected,core,refresh,switch['id'],'SAFE');self.recovery.decision('NORMAL')
            elif self.repair_worker is not None and not self.repair_worker.busy():
                job=dict(job_id=self.next_repair,id=switch['id'],B=core.pose.tolist(),samples_world=worlds.tolist(),
                    previous_vw=before,observation_pose=switch['observation_pose'],observation_sim_s=switch['observation_sim_s'],
                    depth_snapshot=dict(self.snapshot.metadata),dispatch_ns=time.monotonic_ns(),simulation_time_s=refresh['simulation_time_s'])
                self.next_repair+=1;self.repair_pending=job;self.mode='REPAIR_WAIT'
                (self.jobs_dir/f"{job['job_id']:04d}.json").write_text(json.dumps(clean(job)))
                self.rlog('SUBMIT',**job);self.repair_worker.submit(job,self.snapshot)
            else:
                if self.repair_worker is not None:self.rlog('WORKER_BUSY_FALLBACK',id=switch['id'],simulation_time_s=refresh['simulation_time_s'])
                decision=self.use_fallback(core,refresh)
            switch['phase16']=dict(method=self.named_method,selection=detail,fallback_mode=self.mode,fallback=decision,path_source_id=self.path_source_id,oracle_used=False)
        if self.repair_pending is None and self.recovery.eligible(before[0]):
            self.snapshot=self.depth_maps.snapshot();rays=self.recovery.start(self.snapshot,core.pose)
            self.recovery_start=dict(simulation_time_s=refresh['simulation_time_s'],pose=core.pose.tolist())
            self.recovery_record('START',**self.recovery_start,tick=round(refresh['simulation_time_s']*72),id=self.active_id,
                sign=self.recovery.sign,rays_m=rays,snapshot=dict(self.snapshot.metadata),stop_wait_streak=self.recovery.streak,previous_actual_v_m_s=before[0])
            self.follower=None;self.sp=None;self.path_source_id=None;self.repair_active=False
            self.override(core,refresh,switch);self.write_command(core,refresh,switch,before,nominal,'RECOVER_ROTATE',{})
            return
        diag={};source=self.mode
        if not refresh['valid']:
            command=stop_command(before[0]);source='WAYPOINT_TIMEOUT'
        elif self.mode in ('REPAIR_WAIT','STOP_WAIT') or self.sp is None:
            command=stop_command(before[0])
        else:
            command,diag=self.sp.control(core.pose,before[0])
            if diag['completed']:command=stop_command(before[0]);source='ENDPOINT'
            elif diag['mode'] in ('BRAKE','ROTATE'):source='ALIGN_'+diag['mode']
            elif self.repair_active:source='REPAIR'
        core.v,core.w=command;self.last_command=list(command)
        assert abs(core.v-before[0])<=.5/9+1e-12 and abs(core.w)<=.4+1e-12
        self.write_command(core,refresh,switch,before,nominal,source,diag)
        if switch is not None or repair_status=='ACCEPTED':
            self.apps.write(json.dumps(dict(tick=round(refresh['simulation_time_s']*72),simulation_time_s=refresh['simulation_time_s'],
                id=self.active_id,path_source_id=self.path_source_id,kind=self.path_kind,pose=core.pose.tolist(),selected_sample=self.active_sample,
                world_xy=self.follower.path.points.tolist() if self.follower else None,depth_snapshot=dict(self.snapshot.metadata),
                before_vw=before,after_vw=list(command),fallback_mode=self.mode))+'\n');self.apps.flush()

    def write_command(self,core,refresh,switch,before,nominal,source,diag):
        refresh.update(commanded_v_m_s=core.v,commanded_w_rad_s=core.w,applied_v_m_s=core.v,applied_w_rad_s=self.plant.actual_w,
            applied_command_source=source,phase16_fallback_mode=self.mode,phase17_recovery=dict(state=self.recovery.state,count=self.recovery.count,stop_wait_streak=self.recovery.streak),
            phase20=dict(method=self.named_method,source=source,repair_active=self.repair_active,pending_job=self.repair_pending['job_id'] if self.repair_pending else None,
                path_source_id=self.path_source_id,nominal_PD=nominal,SP=diag),
            pure_pursuit=dict(active_chunk_id=self.path_source_id,path_valid=self.follower is not None,stop_reason=source if source in ('STOP_WAIT','REPAIR_WAIT','WAYPOINT_TIMEOUT','ENDPOINT') else None),
            stage2=dict(method=self.named_method,kappa_pp=diag.get('kappa'),corrected_path_active=self.repair_active,graph_applied_job=None))
        self.command_log.write(json.dumps(clean(dict(tick=round(refresh['simulation_time_s']*72),time_s=refresh['simulation_time_s'],
            pose=core.pose.tolist(),before_vw=before,command=[core.v,core.w],**refresh['phase20'])))+'\n');self.command_log.flush()
        if switch is not None:switch.update({k:refresh[k] for k in ('commanded_v_m_s','commanded_w_rad_s','applied_v_m_s','applied_w_rad_s','phase20','phase17_recovery','phase16_fallback_mode','pure_pursuit')})

    def close(self):
        if self.repair_worker:
            self.repair_worker.close()
            if self.repair_pending:self.rlog('TERMINAL_UNAPPLIED',job_id=self.repair_pending['job_id'])
        self.repair_log.close();self.command_log.close();super().close()


def install():
    from nomad_phase16.execution import install_runtime_adapters
    install_runtime_adapters()
    import nomad_phase15b.execution as factory
    import nomad_phase15b.depth as depth
    from .depth import DepthMapThread
    factory.make_execution=lambda c,out:Execution(c['phase20_method'],out)
    depth.DepthMapThread=DepthMapThread


def run_without_oracle(*args,**kwargs):
    """Clone only the RGB/depth driver function; delete its oracle publication gate."""
    import nomad_isaac.async_runtime as original
    tree=ast.parse(inspect.getsource(original.run_async));changed=0
    fn=tree.body[0]
    for i,node in enumerate(fn.body):
        if isinstance(node,ast.If) and ast.unparse(node.test)=='s1 and engine.dynamic is not None':
            fn.body[i]=ast.Assign(targets=[ast.Name(id='oracle_gate',ctx=ast.Store())],value=ast.Constant(value=None));changed+=1
    assert changed==1
    ns=dict(original.__dict__);exec(compile(ast.fix_missing_locations(tree),original.__file__,'exec'),ns)
    return ns['run_async'](*args,**kwargs)
