"""Actual-command wrapper; original PP, NoMaD timing, Graph v4 remain untouched."""
import json
import queue
import time
import numpy as np
from nomad_phase0.chunk_execution import ChunkExecution
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase2.execution import GraphClient, speed_command


def horizon_command(kappa, previous_v, remaining, elapsed):
    time_remaining = max(.998-elapsed, .1)
    target = float(np.clip(remaining/time_remaining, .05, .2))
    v = float(np.clip(target, max(.05, previous_v-.5/9), min(.2, previous_v+.5/9)))
    w = float(np.clip(v*kappa, -.4, .4))
    return (v,w), {'v_target_m_s': target, 'T_rem_s': time_remaining,
        'CURVATURE_SATURATED': bool(abs(kappa)>8), 'ACCEL_LIMITED': bool(abs(v-target)>1e-12),
        'OMEGA_CLIPPED': bool(abs(w-v*kappa)>1e-12)}


class SerialGraphClient(GraphClient):
    """Same external worker; FIFO jobs, one CPU solve at a time, every switched FRESH.

    Max 361 captures at 4 Hz/90 s bounds the queue. Superseded outputs are logged,
    never applied; no cancellation/restart of a solve and no execution-thread wait.
    """
    def __init__(self, out):
        super().__init__(out)
        # Parent thread may already wait on the original jobs queue: keep it.
        self.jobs.maxsize = 512
        self.results.maxsize = 512

    def submit(self, job):
        self.busy = True
        self.jobs.put_nowait(job)


def decision(result, latest_id, valid):
    processing_s = (result['worker_end_ns']-result['worker_start_ns'])/1e9
    stale = processing_s > .5
    if result['id'] != latest_id: status = 'SUPERSEDED'
    elif stale: status = 'STALE'
    elif not valid: status = 'WAYPOINT_EXPIRED'
    elif result.get('initialization_rejected'): status = 'INITIALIZATION_REJECTED'
    elif not result['solver']['success']: status = 'NONCONVERGED'
    elif not result['accepted']: status = 'CONSTRAINT_FAILED'
    else: status = 'ACCEPTED'
    return status, stale, processing_s


class Stage2Execution(ChunkExecution):
    def __init__(self, config, out, client=None):
        super().__init__()
        self.config = config
        self.method = config['s0_stage2_method']
        self.client = (client or SerialGraphClient(out)) if self.method == 'GRAPH' else None
        self.log = (out/'stage2_graph.jsonl').open('x')
        self.pending = {}
        self.ready_results = []
        self.previous_accepted = None
        self.corrected = False
        self.fresh_switch_s = None
        self.next_job = 0

    def record(self, row):
        self.log.write(json.dumps(row)+'\n'); self.log.flush()

    def integrate_record(self, before, after):
        distance = float(np.linalg.norm(np.asarray(after)[:2]-np.asarray(before)[:2]))
        for item in self.pending.values(): item['distance_m'] += distance

    def apply(self, core, refresh, switch):
        before = list(self.last_command)
        graph_applied = None
        if switch is not None:
            self.fresh_switch_s = refresh['simulation_time_s']
            self.corrected = False
        # Raw FRESH wins over any older result arriving at the same controller tick.
        if self.client:
            while True:
                result = self.client.poll()
                if result is None: break
                self.ready_results.append(result)
            eligible = [r for r in self.ready_results if r['result_received_ns'] <= refresh['monotonic_ns']]
            self.ready_results = [r for r in self.ready_results if r['result_received_ns'] > refresh['monotonic_ns']]
            for result in eligible:
                job = self.pending.pop(result['job_id'])
                status, stale, duration = decision(result, core.latest['id'] if core.latest else -1, refresh['valid'])
                record = {**result, 'event':'RESULT', 'disposition':status, 'stale_flag':stale,
                    'processing_wall_s':duration, 'queue_wait_s':(result['worker_start_ns']-job['dispatch_ns'])/1e9,
                    'evaluated_sim_s':refresh['simulation_time_s'], 'evaluated_monotonic_ns':refresh['monotonic_ns'],
                    'boundary':job['boundary'], 'pose_at_result':core.pose.tolist(),
                    'movement_since_dispatch_m':job['distance_m'],
                    'yaw_since_dispatch_rad':float((core.pose[2]-job['boundary'][2]+np.pi)%(2*np.pi)-np.pi)}
                if status == 'ACCEPTED':
                    assert switch is None and core.applied_id == result['id']
                    xy = np.asarray(result['poses'])[:,:2]
                    self.follower = PurePursuit(xy, self.settings['follower'])
                    self.previous_accepted = xy.tolist()
                    self.corrected = True
                    graph_applied = result['job_id']
                    record.update(applied_world_xy=xy.tolist(), applied_tick=round(refresh['simulation_time_s']*72),
                        edit_rms_m=float(np.sqrt(np.mean(np.sum((xy-np.asarray(job['world_xy']))**2,axis=1)))))
                self.record(record)
        # Reuse unchanged chunk switch diagnostics, progression, endpoint and timeout semantics.
        super().apply(core, refresh, switch)
        diag = refresh['pure_pursuit']
        flags = {'CURVATURE_SATURATED':False, 'ACCEL_LIMITED':False, 'OMEGA_CLIPPED':False}
        kappa = None
        if diag['stop_reason'] is None:
            x,y = diag['target_local_x_m'], diag['target_local_y_m']
            kappa = 2*y/(x*x+y*y) if x*x+y*y > 1e-24 else 0.
            if self.method == 'HORIZON-SPEED':
                # Use literal nearest projection, not the monotonic tracking progress.
                remaining = float(self.follower.path.s[-1]-self.follower.path.project(core.pose[:2])[0])
                command, flags = horizon_command(kappa,before[0],remaining,refresh['simulation_time_s']-self.fresh_switch_s)
                flags['projected_remaining_m'] = remaining
            else:
                command, flags = speed_command(kappa,before[0])
            core.v,core.w = command
        self.last_command = [core.v,core.w]
        actual = {'applied_v_m_s':core.v,'applied_w_rad_s':core.w,
            'applied_command_source':self.method+('_GRAPH' if self.corrected else '_RAW') if diag['stop_reason'] is None else diag['stop_reason'],
            'stage2':{**flags,'method':self.method,'kappa_pp':kappa,'corrected_path_active':self.corrected,
                'graph_applied_job':graph_applied,'fresh_switch_sim_s':self.fresh_switch_s,
                'elapsed_since_fresh_switch_s':None if self.fresh_switch_s is None else refresh['simulation_time_s']-self.fresh_switch_s}}
        refresh.update(actual)
        if graph_applied is not None:
            self.record({'event':'APPLIED_COMMAND','job_id':graph_applied,'id':self.active_id,
                'simulation_time_s':refresh['simulation_time_s'],'monotonic_ns':refresh['monotonic_ns'],
                'pose':core.pose.tolist(),'before_vw':before,'after_vw':self.last_command})
        if switch is not None:
            switch.update(actual)
            switch['chunk_transition'].update(actual_command_after=self.last_command,
                actual_command_delta=(np.asarray(self.last_command)-before).tolist())
            if self.client:
                job = {'job_id':self.next_job,'id':switch['id'],'world_xy':switch['chunk']['world_xy_m'],
                    'boundary':core.pose.tolist(),'previous_command':before,'public_config':self.config,
                    'previous_xy':self.previous_accepted,'dispatch_ns':time.monotonic_ns(),
                    'switch_monotonic_ns':refresh['monotonic_ns'],'switch_sim_s':refresh['simulation_time_s'],
                    'observation_pose':switch['observation_pose'],'observation_sim_s':switch['observation_sim_s'],
                    'distance_m':0.}
                self.next_job += 1
                self.pending[job['job_id']] = job
                self.record({'event':'SUBMIT',**job})
                self.client.submit(dict(job))

    def close(self):
        if self.client:
            for job in self.pending.values():
                self.record({'event':'TERMINAL_UNAPPLIED','job_id':job['job_id'],'id':job['id'],
                    'movement_since_dispatch_m':job['distance_m']})
            self.client.close()
        self.log.close()
