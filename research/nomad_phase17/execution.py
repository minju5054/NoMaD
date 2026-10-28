"""Opt-in recovery wrapper; inherited SAFE selection, fallback and Graph clocks."""
import json,time
import numpy as np
from nomad_phase16.execution import SafeExecution as Base,stop_command
from nomad_phase12.execution import BaselineExecution
from .recovery import Recovery,OMEGA
from .config import METHODS,SAFE


class SafeExecution(Base):
    def __init__(self,method,out):
        client=None
        if method==METHODS[5]:
            from .worker import Client
            client=Client(out,True)
        super().__init__(method,out,client)
        self.recovery=Recovery();self.recovery_start=None
        self.recovery_log=(out/'recovery.jsonl').open('x')
        self.recovery_steps=(out/'recovery_72hz.jsonl').open('x')
        self.base_integrate=self.plant.integrate
        self.plant.integrate=self.integrate

    def recovery_record(self,event,**data):
        self.recovery_log.write(json.dumps(dict(event=event,recovery_id=self.recovery.count,**data))+'\n');self.recovery_log.flush()

    def integrate(self,core,tick):
        state=self.recovery.state
        if state not in ('RECOVER_ROTATE','WAIT_FRESH'):return self.base_integrate(core,tick)
        commanded=[core.v,core.w];before=core.pose.copy()
        core.v,core.w=self.recovery.interval_command()
        actual=self.base_integrate(core,tick)
        core.v,core.w=commanded
        self.recovery_steps.write(json.dumps(dict(tick=tick,state=state,recovery_id=self.recovery.count,
            nominal_controller_vw=commanded,actual_vw=list(actual),pose=core.pose.tolist()))+'\n');self.recovery_steps.flush()
        assert np.array_equal(core.pose[:2],before[:2]),'In-place recovery must preserve circle center'
        if state=='RECOVER_ROTATE' and self.recovery.integrated(actual[1]):
            self.recovery_record('END',tick=tick,simulation_time_s=tick/72,pose=core.pose.tolist(),
                duration_s=tick/72-self.recovery_start['simulation_time_s'],angle_rad=float((core.pose[2]-self.recovery_start['pose'][2]+np.pi)%(2*np.pi)-np.pi))
        return actual

    def discard_results(self,refresh):
        if not self.client:return
        while True:
            result=self.client.poll()
            if result is None:break
            self.ready_results.append(result)
        ready=[r for r in self.ready_results if r['result_received_ns']<=refresh['monotonic_ns']]
        self.ready_results=[r for r in self.ready_results if r['result_received_ns']>refresh['monotonic_ns']]
        for result in ready:
            job=self.pending.pop(result['job_id'])
            self.record({**result,'event':'RESULT','disposition':'RECOVERY_DISCARDED',
                'evaluated_sim_s':refresh['simulation_time_s'],'movement_since_dispatch_m':job['distance_m'],
                'processing_wall_s':(result['worker_end_ns']-result['worker_start_ns'])/1e9})

    def override(self,core,refresh,switch):
        rotating=self.recovery.state=='RECOVER_ROTATE';command=[0.,self.recovery.sign*OMEGA if rotating else 0.]
        core.v,core.w=command;self.last_command=command
        refresh.update(commanded_v_m_s=core.v,commanded_w_rad_s=core.w,applied_v_m_s=core.v,
            applied_w_rad_s=self.plant.actual_w,applied_command_source=self.recovery.state,
            phase17_recovery=dict(state=self.recovery.state,count=self.recovery.count,remaining_rad=self.recovery.remaining),
            phase16_fallback_mode=self.recovery.state,
            pure_pursuit=dict(active_chunk_id=self.active_id,path_valid=False,stop_reason=self.recovery.state,
                             endpoint_clamped=None,v_clipped=False,w_clipped=False),
            stage2=dict(method=self.method,kappa_pp=None,corrected_path_active=False,graph_applied_job=None,
                        CURVATURE_SATURATED=False,ACCEL_LIMITED=False,OMEGA_CLIPPED=False,v_target_m_s=0.))
        if switch is not None:
            switch.update({k:v for k,v in refresh.items() if k in ('commanded_v_m_s','commanded_w_rad_s','applied_v_m_s','applied_w_rad_s','applied_command_source','phase17_recovery','phase16_fallback_mode','pure_pursuit','stage2')})

    def apply(self,core,refresh,switch):
        state=self.recovery.state
        if state=='WAIT_FRESH' and switch is not None:
            self.recovery.state='NORMAL';self.mode='STOP_WAIT'
        elif state in ('RECOVER_ROTATE','WAIT_FRESH'):
            self.discard_results(refresh)
            if switch is not None:
                self.active_id=switch['id'];switch['phase17_selection_deferred']=True
                self.recovery_record('FRESH_DEFERRED',id=switch['id'],simulation_time_s=refresh['simulation_time_s'])
            self.override(core,refresh,switch);return
        actual_v=self.last_command[0]
        super().apply(core,refresh,switch)
        if switch is not None:
            self.recovery.decision(self.mode)
            if self.recovery.awaiting_outcome:
                safe_count=sum(x['safe'] for x in switch['phase16']['selection']['candidates'])
                self.recovery_record('FIRST_FRESH',id=switch['id'],simulation_time_s=refresh['simulation_time_s'],safe_sample_count=safe_count)
                self.recovery.awaiting_outcome=False
        if self.recovery.eligible(actual_v):
            # Latest immutable depth, no oracle. Stopping from <.01 is within
            # the existing 0.5m/s^2 per-controller-tick acceleration allowance.
            snapshot=self.depth_maps.snapshot();rays=self.recovery.start(snapshot,core.pose)
            self.recovery_start=dict(simulation_time_s=refresh['simulation_time_s'],pose=core.pose.tolist())
            self.recovery_record('START',**self.recovery_start,tick=round(refresh['simulation_time_s']*72),
                id=self.active_id,sign=self.recovery.sign,rays_m=rays,snapshot=dict(snapshot.metadata),
                stop_wait_streak=self.recovery.streak,previous_actual_v_m_s=actual_v)
            self.follower=None;self.path_source_id=None;self.corrected=False
            self.discard_results(refresh);self.override(core,refresh,switch)
        else:refresh['phase17_recovery']=dict(state='NORMAL',count=self.recovery.count,stop_wait_streak=self.recovery.streak)

    def close(self):
        self.recovery_log.close();self.recovery_steps.close();super().close()


def make_execution(config,out):
    assert config.get('phase17');m=config['phase15b_method'];assert m in METHODS
    if m in SAFE:return SafeExecution(m,out)
    return BaselineExecution(dict(phase12_method=m,phase4c_method='CURV',plant_alpha='inf'),out)


def install_runtime_adapters():
    from nomad_phase16.execution import install_runtime_adapters as base
    base()
    import nomad_phase15b.execution as runtime
    runtime.make_execution=make_execution
