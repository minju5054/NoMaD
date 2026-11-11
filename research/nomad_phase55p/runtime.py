"""Frozen CUT+HOLD plumbing; U-Graph attempts at arrivals and 36-tick checks."""
import json,time
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase28.telemetry import builtin
from nomad_phase32.runtime import Execution as OriginalEC
from nomad_night20261111.runtime import HoldExecution
from nomad_phase53p.runtime import frozen_install,run_without_oracle
from nomad_phase52p.runtime import HoldCore
from nomad_ugraph.certificate import StationaryEndpoint

class Execution(HoldExecution):
    def __init__(self,out,worker=None):
        super().__init__('CUT-HOLD',out)
        from .worker import Client
        self.u_worker=worker if worker is not None else Client(out)
        self.u_file=(out/'ugraph.jsonl').open('x');self.u_dir=out/'ugraph_jobs';self.u_dir.mkdir()
        self.u_count=0;self.u_prior=None;self.u_next=None;self.u_due=None;self.u_cycle=None
    def record(self,event,**kw):
        if event=='INSTALL' and getattr(self,'u_installing',False):kw['path_type']='UGRAPH'
        return super().record(event,**kw)
    def ulog(self,event,**kw):
        self.u_file.write(json.dumps(builtin(dict(event=event,**kw)),allow_nan=False)+'\n');self.u_file.flush()
    def prepare_solution(self,core,refresh,switch,check_tick):
        t=refresh['simulation_time_s'];tick=round(t*72)
        if switch is not None:
            source_id=switch['id'];worlds=np.array([local_to_world(np.asarray(x),switch['observation_pose']) for x in switch['overnight_metric_samples']])
        elif self.ec_samples:
            source_id=max(self.ec_samples);worlds=self.ec_samples[source_id]['worlds']
        else:return None
        self.u_count+=1;field=self.depth_maps.snapshot();file=self.u_dir/f'input_{self.u_count:05d}.npz';field.save(file)
        vw=self.actual_vw();job=dict(sequence=self.u_count,id=source_id,initial=[*core.pose,float(vw[0])],omega=vw[1],
            samples_world=worlds,previous=self.u_prior,snapshot_file=str(file),simulation_time_s=t,tick=tick,
            trigger='CHUNK_AND_PERIODIC' if switch is not None and check_tick is not None else 'CHUNK' if switch is not None else 'PERIODIC',
            periodic_check_tick=check_tick,snapshot=dict(field.metadata))
        (self.u_dir/f'job_{self.u_count:05d}.json').write_text(json.dumps(builtin(job),allow_nan=False)+'\n')
        start=time.perf_counter();result=self.u_worker.solve(job);chosen=None;checks=[]
        cap=None if switch is not None else self.ec_cap
        for candidate in sorted([x for x in result['results'] if x['hard_feasible']],key=lambda x:(x['objective'],x['start_index'])):
            xy=np.asarray(candidate['states'])[:,:2]
            stationary=bool(np.max(np.linalg.norm(xy-xy[0],axis=1))<=1e-9)
            controller=StationaryEndpoint() if stationary else None
            check=self.ec_check(core.pose,self.actual_vw(),xy,self.depth_maps.snapshot(),t,'NORMAL','UGRAPH_INSTALL',cap,controller)
            checks.append(dict(start_index=candidate['start_index'],check_id=check['check_id'],passed=check['passed']))
            if check['passed']:chosen=dict(candidate,stationary=stationary);break
        return dict(job=job,numeric=result,chosen=chosen,checks=checks,cap=cap,applied=False,
            reason='EC_TAIL_PASS' if chosen else 'EC_TAIL_REJECT' if checks else 'NO_HARD_FEASIBLE_SOLUTION',total_s=time.perf_counter()-start)
    def adopt(self,core,refresh):
        cycle=self.u_cycle
        if cycle is None or cycle['chosen'] is None:return False
        if cycle['applied']:
            self.active_sample=cycle['chosen']['active_candidate'];return True
        c=cycle['chosen'];job=cycle['job'];t=refresh['simulation_time_s'];tick=round(t*72);xy=np.asarray(c['states'])[:,:2]
        self.active_sample=c['active_candidate']
        if c['stationary']:
            # PP has no direction on a zero-length XY path. Adopt its stationary
            # endpoint as STOP through frozen stop_command, never invent a path.
            OriginalEC.ec_stop(self,refresh,'UGRAPH_STATIONARY_XY');self.set_hold(False,t,'UGRAPH_STATIONARY_XY')
        else:
            self.u_installing=True
            try:self.install_certified(xy,core,refresh,job['id'],'UGRAPH',cycle['cap'])
            finally:self.u_installing=False
            self.sp.speed_cap=cycle['cap'];self.ec_blocked=False;self.recovery.decision('NORMAL')
        oldcap=self.ec_cap;self.ec_cap=cycle['cap'];self.ec_generation+=1;self.ec_due=tick+36;self.ec_pending=None
        self.u_prior=dict(time_s=t,states=c['states']);cycle['applied']=True
        self.ec_log('INSTALL',generation=self.ec_generation,id=job['id'],kind='UGRAPH_STOP' if c['stationary'] else 'UGRAPH',state='NORMAL',
            apply_tick=tick,simulation_time_s=t,route='UGRAPH_EC_PASS',speed_cap_m_s=self.ec_cap,fresh=job['trigger']!='PERIODIC',
            selected_sample=self.active_sample,cap_released=oldcap is not None and self.ec_cap is None,cap_activated=False)
        self.ulog('INSTALL',id=job['id'],sequence=job['sequence'],tick=tick,simulation_time_s=t,pose=core.pose,path_world=xy,
            states=c['states'],start_index=c['start_index'],active_candidate=c['active_candidate'],stationary_xy=c['stationary'],graph_velocity_executed=False)
        return True
    def ec_install(self,path,core,refresh,source_id,kind,**kw):
        if self.adopt(core,refresh):return dict(installed=True,kind='UGRAPH',route='UGRAPH_EC_PASS',cap=self.ec_cap)
        return super().ec_install(path,core,refresh,source_id,kind,**kw)
    def use_fallback(self,core,refresh):
        if self.adopt(core,refresh):return dict(reason='UGRAPH_EC_PASS')
        return super().use_fallback(core,refresh)
    def apply(self,core,refresh,switch):
        tick=round(refresh['simulation_time_s']*72);self.ec_context=(core,refresh)
        check_tick=self.u_due;self.u_due=None
        if switch is not None and self.u_next is None:self.u_next=tick+36
        self.u_cycle=self.prepare_solution(core,refresh,switch,check_tick) if switch is not None or check_tick is not None else None
        # Periodic installation happens on the first9Hz tick after the check.
        # Recovery state is frozen: no installed path interrupts its rotation.
        if switch is None and self.recovery.state=='NORMAL':self.adopt(core,refresh)
        super().apply(core,refresh,switch)
        if self.u_cycle is not None:
            c=self.u_cycle
            if c['chosen'] is not None and not c['applied']:c['reason']='RECOVERY_DEFERRED'
            self.ulog('SOLVE',sequence=c['job']['sequence'],id=c['job']['id'],tick=tick,simulation_time_s=refresh['simulation_time_s'],
                trigger=c['job']['trigger'],periodic_check_tick=check_tick,periodic_delay_ticks=None if check_tick is None else tick-check_tick,
                applied=c['applied'],reason=c['reason'],solve_s=c['numeric']['solve_s'],rpc_s=c['numeric']['rpc_s'],total_s=c['total_s'],
                checks=c['checks'],chosen_start=None if c['chosen'] is None else c['chosen']['start_index'],results=c['numeric']['results'])
        self.u_cycle=None
    def integrate_record(self,before,after):
        super().integrate_record(before,after);tick=self.plant.last_tick
        if self.u_next is not None and tick>=self.u_next:
            self.u_due=self.u_next;self.u_next+=36
    def close(self):
        try:self.u_worker.close();super().close()
        finally:self.u_file.close()

def install(c):
    frozen_install(c)
    from nomad_phase24.retention import retained_apply
    import nomad_phase15b.execution as factory
    import nomad_phase8.execution as overnight
    import nomad_isaac.async_runtime as engine
    engine.WaypointExecution=HoldCore
    def make(config,out):return retained_apply(Execution(out))
    factory.make_execution=make;overnight.OvernightExecution=make
    if c.get('h1v2'):
        from nomad_h1v2.scene import install_environment
        install_environment(c)
