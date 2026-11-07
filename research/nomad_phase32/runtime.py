"""New EC adapter; frozen C0 decision/R2/R3/normal G18 numerical code reused."""
import hashlib,json,time
from types import SimpleNamespace
import numpy as np
from nomad_phase29.runtime import PathExecution
from nomad_phase28.runtime import NAExecution,installer
from nomad_phase28.telemetry import builtin
from nomad_phase3_stage2.execution import decision
from nomad_phase20b.worker import disposition
from nomad_phase20c.detour import select_detour
from nomad_phase15b.depth import evaluate_samples
from nomad_isaac.common import local_to_world
from nomad_phase32o.exec_cert import certify
from .policy import CappedNA,normal_choice,continuation_certificate,PERIOD_TICKS

RAW_INSTALL=installer(CappedNA)

def path_key(path):return hashlib.sha256(np.asarray(path,dtype=np.float64).tobytes()).hexdigest()

class RecoveryGate:
    def __init__(self,base,owner):object.__setattr__(self,'base',base);object.__setattr__(self,'owner',owner)
    def __getattr__(self,key):return getattr(self.base,key)
    def __setattr__(self,key,value):setattr(self.base,key,value)
    def decision(self,mode):
        # The inherited caller assumes new_path always succeeds. EC STOP must
        # not be reset by its unconditional NORMAL notification.
        if mode=='NORMAL' and self.owner.ec_blocked:return
        return self.base.decision(mode)

class WorkerGate:
    def __init__(self,base,owner):self.base=base;self.owner=owner
    def __getattr__(self,key):return getattr(self.base,key)
    def poll(self):
        result=self.base.poll()
        if result is None:return None
        o=self.owner;job=o.detour if o.detour is not None else o.repair_pending
        if not job or result.get('job_id')!=job['job_id']:return result
        if disposition(result,job['dispatch_ns'],time.monotonic_ns())!='ACCEPTED':return result
        core,refresh=o.ec_context;state='R3' if o.detour is not None else 'R2';field=o.depth_maps.snapshot();checks=[];filtered=[]
        candidates=range(len(result['results'])) if state=='R3' else [result['selected_sample']]
        allowed=[]
        for i in candidates:
            candidate=result['results'][i]
            if not candidate.get('accepted'):continue
            r=o.ec_check(core.pose,o.actual_vw(),candidate['path'],field,refresh['simulation_time_s'],state,'INSTALL_CANDIDATE',o.ec_cap)
            checks.append(dict(index=i,check_id=r['check_id'],passed=r['passed']))
            if r['passed']:
                allowed.append(i);o.ec_tokens.add((round(refresh['simulation_time_s']*72),path_key(candidate['path'])))
        if state=='R3':
            for i,c in enumerate(result['results']):filtered.append(dict(c,accepted=bool(c.get('accepted') and i in allowed)))
            chosen=select_detour(filtered)
        else:chosen=result['selected_sample'] if allowed else None
        if chosen is None:o.ec_blocked=True
        o.ec_log('SOLVER_FILTER',state=state,job_id=job['job_id'],simulation_time_s=refresh['simulation_time_s'],original_selected=result['selected_sample'],selected=chosen,checks=checks,route='R2_TO_R3' if state=='R2' and chosen is None else 'R3_FAILURE' if chosen is None else 'SOLVER_EC_PASS')
        # Preserve all original numerical outcomes; only the installed choice
        # is gated. No solver success flag/cost/deadline is altered.
        out=dict(result,selected_sample=chosen,ec_original_selected_sample=result['selected_sample'],ec_checks=checks)
        if state=='R3':out.update(selected_initialization=chosen,ec_original_selected_initialization=result.get('selected_initialization'))
        return out

class ECInstaller(NAExecution):
    def new_path(self,path,core,refresh,source_id,kind):return self.ec_install(path,core,refresh,source_id,kind)

class Execution(PathExecution,ECInstaller):
    def __init__(self,method,out):
        self.ec_method=method;self.ec_blocked=False;self.ec_cap=None;self.ec_generation=0;self.ec_due=None;self.ec_pending=None;self.ec_context=None;self.ec_tokens=set();self.ec_sequence=0;self.ec_check_sequence=0;self.ec_samples={};self.ec_switch=None
        self.ec_file=(out/'exec_cert.jsonl').open('x');self.ec_ticks=(out/'exec_cert_72hz.jsonl').open('x')
        super().__init__('G18' if method=='G18+EC' else 'C0-NA',out)
        self.recovery=RecoveryGate(self.recovery,self)
        self.repair_worker=WorkerGate(self.repair_worker,self)
    def ec_log(self,event,**kw):self.ec_file.write(json.dumps(builtin(dict(event=event,**kw)),allow_nan=False)+'\n');self.ec_file.flush()
    def actual_vw(self):return [float(self.last_command[0]),float(self.plant.actual_w)]
    def ec_check(self,pose,vw,path,field,t,state,scope,cap,controller=None):
        tick=round(t*72);check_started_ns=time.monotonic_ns()
        if hasattr(self.depth_maps,'archive_queue') and not getattr(self.depth_maps,'full_frames',True):self.depth_maps.archive_queue.put_nowait((field,None,None))
        r=continuation_certificate(controller,pose,vw,field,tick) if controller is not None else certify(pose,vw,path,field,speed_cap=cap)
        check_finished_ns=time.monotonic_ns();ident=self.ec_check_sequence;self.ec_check_sequence+=1
        self.ec_log('CHECK',check_id=ident,generation=self.ec_generation,state=state,scope=scope,check_tick=tick,check_started_ns=check_started_ns,check_finished_ns=check_finished_ns,simulation_time_s=t,pose=np.asarray(pose).tolist(),actual_vw=vw,speed_cap_m_s=cap,snapshot=dict(field.metadata),path_sha256=path_key(path),**r)
        return dict(r,check_id=ident,check_tick=tick,check_started_ns=check_started_ns,check_finished_ns=check_finished_ns)
    def ec_stop(self,refresh,reason):
        self.ec_blocked=True;self.ec_due=None;self.follower=None;self.sp=None;self.path_source_id=None;self.path_kind=None;self.repair_active=False;self.mode='STOP_WAIT'
        if self.ec_switch is not None:self.recovery.decision('STOP_WAIT')
        self.ec_log('FALLBACK',route='STOP_WAIT',reason=reason,simulation_time_s=refresh['simulation_time_s'],apply_tick=round(refresh['simulation_time_s']*72))
    def ec_options(self,primary,source_id,kind,pose,field,reference_sample=None,native_options=False):
        sample=self.ec_samples.get(source_id);options=[];selected=self.active_sample if reference_sample is None else reference_sample
        if sample is not None:
            worlds=sample['worlds'];_,detail=evaluate_samples(worlds,pose,field)
            safe=sorted([c for c in detail['candidates'] if c['safe']],key=lambda c:(-c['remaining_length_m'],c['index']))
            for rank,c in enumerate(safe,1):
                i=c['index'];p=np.asarray(primary) if i==selected and not native_options else worlds[i]
                options.append(dict(key=path_key(p),path=p,index=i,rank=rank,kind=kind if i==selected and not native_options else 'SAFE'))
        initial=dict(key=path_key(primary),path=np.asarray(primary),index=selected,rank=next((x['rank'] for x in options if x['index']==selected),None),kind=kind)
        return initial,options
    def ec_install(self,path,core,refresh,source_id,kind,periodic_rejected=False,reference_sample=None):
        tick=round(refresh['simulation_time_s']*72);state='R2' if kind=='REPAIR' else 'R3' if kind=='DETOUR' else 'NORMAL';field=self.depth_maps.snapshot()
        if periodic_rejected and self.ec_samples:source_id=max(self.ec_samples)
        fresh=kind=='SAFE' and self.ec_switch is not None and self.ec_switch['id']==source_id
        if state=='NORMAL':
            initial,options=self.ec_options(path,source_id,kind,core.pose,field,reference_sample,native_options=periodic_rejected)
            def check(item,cap):return self.ec_check(core.pose,self.actual_vw(),item['path'],field,tick/72,state,'INSTALL',cap)
            chosen=normal_choice(initial,options,check,None if fresh else self.ec_cap,primary_rejected=periodic_rejected)
            if chosen['item'] is None:self.ec_stop(refresh,'NORMAL_NO_EC_SAFE_CANDIDATE');return dict(installed=False,**chosen)
            item=chosen['item'];path=item['path'];kind=item['kind'];self.active_sample=item['index'];cap=chosen['cap'];rank=item['rank'];route=chosen['route']
        else:
            token=(tick,path_key(path));assert token in self.ec_tokens,'R2/R3 must pass WorkerGate before installation'
            self.ec_tokens.discard(token);cap=None;rank=None;route=state+'_EC_PASS'
        # A pre-existing cap survives non-FRESH replacements (including R2/R3)
        # until a FRESH installs at full speed, as preregistered.
        if self.ec_cap is not None and not fresh:cap=.1
        RAW_INSTALL(self,path,core,refresh,source_id,kind);self.sp.speed_cap=cap
        self.ec_generation+=1;self.ec_due=tick+36;self.ec_pending=None;self.ec_blocked=False;oldcap=self.ec_cap;self.ec_cap=cap
        self.ec_log('INSTALL',generation=self.ec_generation,id=source_id,kind=kind,state=state,apply_tick=tick,simulation_time_s=tick/72,route=route,speed_cap_m_s=cap,fresh=fresh,freshest_rank=rank,selected_sample=self.active_sample,cap_released=oldcap is not None and cap is None,cap_activated=oldcap is None and cap is not None)
        return dict(installed=True,kind=kind,cap=cap,rank=rank,route=route)
    def new_path(self,path,core,refresh,source_id,kind):
        if self.ec_method=='G18+EC':return PathExecution.new_path(self,path,core,refresh,source_id,kind)
        return self.ec_install(path,core,refresh,source_id,kind)
    def collect_paths(self,core,refresh,switch):
        # Same frozen job disposition/stale/superseded rules; EC is the last
        # installation guard. Prior is updated only for an installed Graph XY.
        for job_id,(job,future,started) in list(self.path_jobs.items()):
            if not future.done():continue
            result=future.result()
            if result['result_received_ns']>refresh['monotonic_ns']:continue
            del self.path_jobs[job_id];status,stale,seconds=decision(result,core.latest['id'] if core.latest else -1,refresh['valid'])
            if status=='ACCEPTED' and (switch is not None or core.applied_id!=job['id']):status='SUPERSEDED'
            if status=='ACCEPTED' and (self.detour is not None or self.detour_active or self.repair_pending is not None or self.mode!='NORMAL' or self.recovery.state!='NORMAL'):status='NON_NORMAL_MODE'
            if status=='ACCEPTED':
                path=np.asarray(result['poses'])[:,:2]
                bank=self.ec_samples.get(job['id'],{}).get('worlds',[])
                original=np.asarray(job['path']);reference=next((i for i,p in enumerate(bank) if p.shape==original.shape and np.allclose(p,original,atol=1e-10,rtol=0)),self.active_sample)
                outcome=self.ec_install(path,core,refresh,job['id'],'GRAPH18',reference_sample=reference)
                if outcome['installed'] and outcome.get('kind')=='GRAPH18':self.path_prior=path.tolist()
                else:status='EXEC_CERT_REJECT'
            self.path_record('RESULT',**result,simulation_time_s=refresh['simulation_time_s'],disposition=status,stale_flag=stale,applied=status=='ACCEPTED',wall_s=seconds,dispatch_to_result_s=(result['result_received_ns']-started)/1e9)
    def integrate_record(self,before,after):
        super().integrate_record(before,after);tick=self.plant.last_tick
        if self.ec_due is not None and tick>=self.ec_due:
            self.ec_due+=36
            if self.sp is not None and self.mode not in ('STOP_WAIT','REPAIR_WAIT') and self.recovery.state=='NORMAL' and self.ec_pending is None:
                field=self.depth_maps.snapshot();state='R3' if self.detour_active else 'R2' if self.repair_active else 'NORMAL'
                r=self.ec_check(after,self.actual_vw(),self.follower.path.points,field,tick/72,state,'PERIODIC',self.ec_cap,self.sp)
                if not r['passed']:self.ec_pending=dict(generation=self.ec_generation,state=state,path=self.follower.path.points.copy(),source_id=self.path_source_id,check_tick=tick,check_id=r['check_id'],check_started_ns=r['check_started_ns'],check_finished_ns=r['check_finished_ns'])
        self.ec_ticks.write(json.dumps(builtin(dict(tick=tick,simulation_time_s=tick/72,speed_cap_active=self.ec_cap is not None,ec_reject_latched=self.ec_blocked,physical_stop=abs(self.last_command[0])<.01,mode=self.mode,recovery_state=self.recovery.state,periodic_pending=self.ec_pending is not None)))+'\n')
    def apply(self,core,refresh,switch):
        tick=round(refresh['simulation_time_s']*72);self.ec_context=(core,refresh);self.ec_switch=switch;self.ec_tokens={x for x in self.ec_tokens if x[0]==tick}
        if switch is not None:
            self.ec_samples[switch['id']]=dict(worlds=np.array([local_to_world(np.asarray(x),switch['observation_pose']) for x in switch['overnight_metric_samples']]))
            self.ec_samples={k:v for k,v in self.ec_samples.items() if k>=switch['id']-2}
        pending=self.ec_pending
        if pending is not None:
            self.ec_pending=None;delay=tick-pending['check_tick'];assert 0<=delay<=4
            if pending['generation']!=self.ec_generation:action='SUPERSEDED_PATH'
            elif pending['state']=='R2':
                self.ec_blocked=True;self.repair_active=False;self.start_detour(core,refresh,'A',None);action='R2_TO_R3'
            elif pending['state']=='R3':
                self.ec_blocked=True;self.end_detour(core,refresh,'EXEC_CERT_REJECT');action='R3_FAILURE'
            else:
                self.ec_install(pending['path'],core,refresh,pending['source_id'],self.path_kind,periodic_rejected=True);action='NORMAL_FALLBACK'
            self.ec_log('PERIODIC_APPLY',check_id=pending['check_id'],check_tick=pending['check_tick'],apply_tick=tick,delay_ticks=delay,delay_ms=delay/72*1000,apply_monotonic_ns=time.monotonic_ns(),delay_wall_ms=(time.monotonic_ns()-pending['check_started_ns'])/1e6 if pending.get('check_started_ns') is not None else None,action=action,state=pending['state'])
        super().apply(core,refresh,switch)
        refresh['exec_cert']=builtin(dict(speed_cap_m_s=self.ec_cap,blocked=self.ec_blocked,generation=self.ec_generation))
        if switch is not None:switch['exec_cert']=refresh['exec_cert']
        self.ec_switch=None
    def close(self):
        try:super().close()
        finally:self.ec_file.close();self.ec_ticks.close()


def install(config):
    from nomad_phase26.execution import install as frozen
    from nomad_phase24.retention import retained_apply
    frozen(config)
    import nomad_phase15b.execution as factory
    factory.make_execution=lambda c,out:retained_apply(Execution(c['phase32_method'],out))

from nomad_phase26.execution import run_without_oracle
