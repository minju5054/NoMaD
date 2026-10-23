"""Phase4 applied-command wrapper, unchanged PP geometry and waypoint timing."""
import json
import os
import queue
import subprocess
import threading
import time
import numpy as np
from nomad_isaac.common import ROOT, integrate_se2
from nomad_phase0.chunk_execution import ChunkExecution
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase3_stage2.execution import Stage2Execution, SerialGraphClient


def predict_boundary(pose, command):
    return integrate_se2(np.asarray(pose),*command,2/9)


def command_policy(method,kappa,previous_v,profile=None,projected_s=0.):
    if profile is not None:
        target=float(np.interp(projected_s,profile['s_m'],profile['v_m_s']))
        v=float(np.clip(target,.05,.3))
    elif method=='RAW':target=v=.3
    else:
        target=float(np.clip(.4/abs(kappa),.05,.3)) if kappa else .3
        v=float(np.clip(target,max(.05,previous_v-.5/9),min(.3,previous_v+.5/9)))
    w=float(np.clip(v*kappa,-.4,.4))
    return (v,w),{'v_target_m_s':target,'CURVATURE_SATURATED':bool(abs(kappa)>8),
        'ACCEL_LIMITED':bool(abs(v-target)>1e-12),'OMEGA_CLIPPED':bool(abs(w-v*kappa)>1e-12),
        'temporal_acceleration_exceeds_limit':bool(abs(v-previous_v)>.5/9+1e-12),
        'profile_projected_s_m':float(projected_s) if profile is not None else None}


def decision(result,latest_id,valid,pose,predicted):
    duration=(result['worker_end_ns']-result['worker_start_ns'])/1e9;stale=duration>.3
    if result['id']!=latest_id:status='SUPERSEDED'
    elif stale:status='STALE'
    elif not valid:status='WAYPOINT_EXPIRED'
    elif result.get('initialization_rejected'):status='INITIALIZATION_REJECTED'
    elif result.get('error'):status='SOLVER_ERROR'
    elif not result['solver']['success']:status='NONCONVERGED'
    elif not result['accepted']:status='CONSTRAINT_FAILED'
    elif np.linalg.norm(np.asarray(pose)[:2]-np.asarray(predicted)[:2])>.02:status='APP_MISMATCH'
    else:status='ACCEPTED'
    return status,stale,duration


class V5Client(SerialGraphClient):
    def __init__(self,out):
        self.out=out;self.jobs=queue.Queue(512);self.results=queue.Queue(512)
        self.ready=threading.Event();self.error=None;self.busy=False
        env=os.environ.copy()
        for key in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(key,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(out/'graph_worker.log').open('x')
        self.proc=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase4.worker'],cwd=ROOT,env=env,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        self.thread=threading.Thread(target=self.run,name='graph-v5-ipc',daemon=True);self.thread.start()
        if not self.ready.wait(30) or self.error:raise RuntimeError(f'Graph worker startup failed: {self.error}')


class Phase4Execution(Stage2Execution):
    def __init__(self,config,out,client=None):
        ChunkExecution.__init__(self)
        self.config=config;self.method=config['phase4_method']
        self.client=(client or V5Client(out)) if self.method=='GRAPH-v5' else None
        self.log=(out/'stage2_graph.jsonl').open('x')
        self.pending={};self.ready_results=[];self.previous_accepted=None
        self.corrected=False;self.profile=None;self.fresh_switch_s=None;self.next_job=0

    def apply(self, core, refresh, switch):
        before = list(self.last_command)
        graph_applied = None
        if switch is not None:
            self.fresh_switch_s = refresh['simulation_time_s']
            self.corrected = False
            self.profile = None
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
                status, stale, duration = decision(result, core.latest['id'] if core.latest else -1, refresh['valid'], core.pose, job['boundary'])
                record = {**result, 'event':'RESULT', 'disposition':status, 'stale_flag':stale,
                    'processing_wall_s':duration, 'queue_wait_s':(result['worker_start_ns']-job['dispatch_ns'])/1e9,
                    'evaluated_sim_s':refresh['simulation_time_s'], 'evaluated_monotonic_ns':refresh['monotonic_ns'],
                    'boundary':job['boundary'], 'dispatch_pose':job['dispatch_pose'], 'pose_at_result':core.pose.tolist(),
                    'app_mismatch_m':float(np.linalg.norm(core.pose[:2]-np.asarray(job['boundary'])[:2])),
                    'app_yaw_mismatch_rad':float((core.pose[2]-job['boundary'][2]+np.pi)%(2*np.pi)-np.pi),
                    'movement_since_dispatch_m':job['distance_m'],
                    'yaw_since_dispatch_rad':float((core.pose[2]-job['dispatch_pose'][2]+np.pi)%(2*np.pi)-np.pi)}
                if status == 'ACCEPTED':
                    assert switch is None and core.applied_id == result['id']
                    xy = np.asarray(result['poses'])[:,:2]
                    self.follower = PurePursuit(xy, self.settings['follower'])
                    self.previous_accepted = xy.tolist()
                    self.profile = result['speed_profile']
                    self.corrected = True
                    graph_applied = result['job_id']
                    record.update(applied_world_xy=xy.tolist(), speed_profile=self.profile, applied_tick=round(refresh['simulation_time_s']*72),
                        edit_rms_m=float(np.sqrt(np.mean(np.sum((xy-np.asarray(job['world_xy']))**2,axis=1)))))
                self.record(record)
        # Reuse unchanged chunk switch diagnostics, progression, endpoint and timeout semantics.
        ChunkExecution.apply(self, core, refresh, switch)
        diag = refresh['pure_pursuit']
        flags = {'CURVATURE_SATURATED':False, 'ACCEL_LIMITED':False, 'OMEGA_CLIPPED':False}
        kappa = None
        if diag['stop_reason'] is None:
            x,y = diag['target_local_x_m'], diag['target_local_y_m']
            kappa = 2*y/(x*x+y*y) if x*x+y*y > 1e-24 else 0.
            projected=self.follower.path.project(core.pose[:2])[0]
            command,flags=command_policy(self.method,kappa,before[0],self.profile,projected)
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
                    'boundary':predict_boundary(core.pose,self.last_command).tolist(),'dispatch_pose':core.pose.tolist(),'previous_command':self.last_command,'public_config':self.config,
                    'previous_xy':self.previous_accepted,'dispatch_ns':time.monotonic_ns(),
                    'switch_monotonic_ns':refresh['monotonic_ns'],'switch_sim_s':refresh['simulation_time_s'],
                    'observation_pose':switch['observation_pose'],'observation_sim_s':switch['observation_sim_s'],
                    'distance_m':0.}
                self.next_job += 1
                self.pending[job['job_id']] = job
                self.record({'event':'SUBMIT',**job})
                self.client.submit(dict(job))

