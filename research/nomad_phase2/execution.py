"""Phase2 optional actual-command layer, isolated from original PP/PD/timing code."""
from collections import deque
import copy
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import numpy as np
from nomad_isaac.common import ROOT, local_to_world
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.chunk_execution import protocol as chunk_protocol, describe_chunk
from .config import select, protocol


def speed_command(kappa,previous_v):
    # Exact v3 formula, isolated here so Isaac imports no SciPy/Graph dependencies.
    target=float(np.clip(.4/abs(kappa),.05,.2)) if kappa else .2
    v=float(np.clip(target,max(.05,previous_v-.5/9),min(.2,previous_v+.5/9)))
    w=float(np.clip(v*kappa,-.4,.4))
    return (v,w),{'v_target_m_s':target,'CURVATURE_SATURATED':bool(abs(kappa)>8),
        'ACCEL_LIMITED':bool(abs(v-target)>1e-12),'OMEGA_CLIPPED':bool(abs(w-v*kappa)>1e-12)}


class GraphClient:
    def __init__(self,out):
        self.out=out; self.jobs=queue.Queue(maxsize=1);self.results=queue.Queue(maxsize=1)
        self.ready=threading.Event();self.error=None;self.busy=False
        env=os.environ.copy()
        for key in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):
            env.pop(key,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(out/'graph_worker.log').open('x')
        self.proc=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase2.graph_worker'],
            cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        self.thread=threading.Thread(target=self.run,name='graph-ipc',daemon=True);self.thread.start()
        if not self.ready.wait(30) or self.error:raise RuntimeError(f'Graph worker startup failed: {self.error}')
    def run(self):
        try:
            assert json.loads(self.proc.stdout.readline())['kind']=='ready';self.ready.set()
            while True:
                job=self.jobs.get()
                if job is None:
                    self.proc.stdin.write('{"kind":"stop"}\n');self.proc.stdin.flush();return
                self.proc.stdin.write(json.dumps(job)+'\n');self.proc.stdin.flush()
                result=json.loads(self.proc.stdout.readline());result['result_received_ns']=time.monotonic_ns()
                self.results.put(result)
        except BaseException as e:self.error=e;self.ready.set()
    def submit(self,job):
        assert not self.busy;self.busy=True;self.jobs.put_nowait(job)
    def poll(self):
        if self.error:raise RuntimeError('Graph IPC failed') from self.error
        try:r=self.results.get_nowait()
        except queue.Empty:return None
        self.busy=False;return r
    def close(self):
        if self.busy:
            self.thread.join(.01)
        self.proc.terminate()
        try:self.proc.wait(10)
        except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait()
        self.log.close()


class Phase2Execution:
    def __init__(self,config,out):
        self.config=config;self.out=out;self.method=config['phase2_method'];self.settings=chunk_protocol()
        self.follower=None;self.active=None;self.active_id=-1;self.variable=False
        self.last_command=[0.,0.];self.queue=deque();self.pending=None;self.next_job=0
        self.client=GraphClient(out) if self.method=='M5' else None
        self.public=None;self.public_lock=threading.Lock();self.previous_corrected=None
        self.decisions=(out/'phase2_decisions.jsonl').open('x');self.graph_log=(out/'phase2_graph.jsonl').open('x')
        self.oracle_log=(out/'phase2_oracle.jsonl').open('x');self.closed=False
    def emit(self,stream,data):stream.write(json.dumps(data)+'\n');stream.flush()
    def publish(self,gate,box):
        if gate['geometry_available'] and box is not None:
            with self.public_lock:
                if self.public is None:
                    self.public={'obstacle':copy.deepcopy(box),'gate':copy.deepcopy(gate)}
                    self.emit(self.oracle_log,{'event':'PUBLIC','publication_monotonic_ns':time.monotonic_ns(),**self.public})
    def accept(self,row,metric):
        self.queue.append((copy.deepcopy(row),metric.copy()))
    def public_config(self):
        c=copy.deepcopy(self.config);c['obstacles']=list(c['obstacles'])
        with self.public_lock: p=copy.deepcopy(self.public)
        if p:c['obstacles'].append(p['obstacle'])
        c.pop('dynamic_obstacle',None)
        return c,p
    def activate(self,item,core,now,tick,graph_result=None):
        row,metric,decision=item
        i=decision['selected_sample'];world=local_to_world(metric[i],np.array(row['observation_pose']))
        corrected=bool(graph_result and graph_result.get('accepted') and not graph_result['stale'])
        if corrected:world=np.array(graph_result['poses'])[:,:2]
        self.variable=corrected or i!=0
        self.active={**row,'phase2':{**decision,'graph_applied':corrected,'variable_speed':self.variable,
            'world_xy_m':world.tolist(),'graph_job_id':graph_result['job_id'] if graph_result else None}}
        self.active_id=row['id'];core.applied_id=self.active_id
        try:self.follower=PurePursuit(world,self.settings['follower'])
        except ValueError:self.follower=None
        self.previous_corrected=world.copy() if corrected else None
        return {**self.active,'application_sim_s':tick/72,'application_monotonic_ns':now,
            'agent_pose_at_switch':core.pose.tolist(),'chunk':{**describe_chunk(metric[i],row['observation_pose']),
            'world_xy_m':world.tolist(),'anchor':'observation_pose_then_explicit_graph_correction' if corrected else 'observation_pose'},
            'actual_command_before':list(self.last_command)}
    def control(self,core,tick,now):
        if tick%8:return None,None
        before=list(self.last_command);switch=None;hold=False
        if self.pending:
            result=self.client.poll()
            if result is not None:
                pending=self.pending;self.pending=None
                result.update(dispatch_ns=pending['dispatch_ns'],boundary=pending['boundary'],
                    returned_pose=core.pose.tolist(),returned_tick=tick,
                    elapsed_s=(result['result_received_ns']-pending['dispatch_ns'])/1e9,
                    movement_since_dispatch_m=pending['distance_m'],
                    yaw_change_rad=float((core.pose[2]-pending['boundary'][2]+np.pi)%(2*np.pi)-np.pi))
                result['stale']=result['elapsed_s']>.5
                result['status']='GRAPH_STALE' if result['stale'] else 'ACCEPTED' if result['accepted'] else 'REJECTED'
                row=pending['item'][0]
                age=(now-row['received_monotonic_ns'])/1e9
                result['fresh_age_at_return_s']=age
                if age<1.:
                    switch=self.activate(pending['item'],core,now,tick,result)
                    result['applied']=switch['phase2']['graph_applied']
                    result['application_monotonic_ns']=now
                else:result['applied']=False;result['expired_before_apply']=True
                self.emit(self.graph_log,result)
            else:hold=True
        if not self.pending and switch is None and self.queue:
            row,metric=self.queue.popleft()
            age=(now-row['received_monotonic_ns'])/1e9
            if age>=1.:
                self.emit(self.decisions,{'id':row['id'],'status':'EXPIRED_BEFORE_DECISION','age_s':age})
            else:
                samples=np.array([local_to_world(x,np.array(row['observation_pose'])) for x in metric])
                public,gate=self.public_config();decision=select(samples,core.pose,public)
                if self.method=='M0':decision['selected_sample']=0
                decision.update(id=row['id'],decision_tick=tick,decision_ns=now,boundary=core.pose.tolist(),
                    geometry_available=gate is not None,public_obstacle_ids=[b['id'] for b in public['obstacles']],
                    selection_intervened=decision['selected_sample']!=0,method=self.method)
                item=(row,metric,decision)
                if self.method=='M5' and decision['sample0_unsafe']:
                    job={'job_id':self.next_job,'id':row['id'],'world_xy':samples[decision['selected_sample']].tolist(),
                         'boundary':core.pose.tolist(),'previous_command':before,'public_config':public,
                         'previous_xy':self.previous_corrected.tolist() if self.previous_corrected is not None else None,
                         'dispatch_ns':now}
                    self.next_job+=1;self.client.submit(job)
                    self.pending={'item':item,'dispatch_ns':now,'boundary':core.pose.tolist(),'distance_m':0.}
                    self.emit(self.graph_log,{'event':'SUBMIT',**job});hold=True
                    decision['graph_submitted']=True
                else:
                    decision['graph_submitted']=False
                    switch=self.activate(item,core,now,tick)
                self.emit(self.decisions,decision)
        age=None if self.active is None else (now-self.active['received_monotonic_ns'])/1e9
        valid=age is not None and age<1.;status='valid' if valid else 'missing' if age is None else 'expired'
        new_timeout=status=='expired' and self.active_id not in core.expired_ids
        if new_timeout:core.expired_ids.add(self.active_id)
        diag={'endpoint_stop':False,'CURVATURE_SATURATED':False,'ACCEL_LIMITED':False,'OMEGA_CLIPPED':False}
        if not valid:command=(0.,0.);source=status
        elif hold:command=tuple(before);source='graph_wait_hold_old'
        elif self.follower is None:command=(0.,0.);source='invalid_chunk'
        else:
            command,diag0=self.follower.control(core.pose);diag.update(diag0)
            x,y=diag0['target_local_x_m'],diag0['target_local_y_m'];k=2*y/(x*x+y*y) if x*x+y*y>=1e-24 else 0.
            diag.update(kappa_PP_m_inv=k,CURVATURE_SATURATED=abs(k)>8,OMEGA_CLIPPED=diag0['w_clipped'])
            if self.variable and not diag0['endpoint_stop']:
                command,flags=speed_command(k,before[0]);diag.update(flags)
            source='endpoint' if diag0['endpoint_stop'] else 'variable_speed_pp' if self.variable else 'original_pp'
        nominal=list(map(float,core.controller(self.active['selected_waypoint_m']))) if valid else [0.,0.]
        core.v,core.w=command;core.applied_id=self.active_id;core.command_valid=valid
        self.last_command=list(command)
        refresh={'simulation_time_s':tick/72,'monotonic_ns':now,'waypoint_id':self.active_id,
            'latest_received_id':core.latest['id'] if core.latest else -1,'waypoint_age_wall_s':age,
            'valid':valid,'status':status,'new_timeout':new_timeout,'v_m_s':nominal[0],'w_rad_s':nominal[1],
            'applied_v_m_s':float(command[0]),'applied_w_rad_s':float(command[1]),'applied_command_source':source,
            'phase2_method':self.method,'variable_speed':self.variable,'graph_wait':hold,'pure_pursuit':diag}
        if switch:
            switch.update(v_m_s=nominal[0],w_rad_s=nominal[1],applied_v_m_s=float(command[0]),
                applied_w_rad_s=float(command[1]),applied_command_source=source,pure_pursuit=diag,
                actual_command_after=list(command),actual_command_delta=(np.array(command)-before).tolist())
        return refresh,switch
    def integrate_record(self,old_pose,new_pose):
        if self.pending:self.pending['distance_m']+=float(np.linalg.norm(new_pose[:2]-old_pose[:2]))
    def close(self):
        if self.closed:return
        if self.pending:self.emit(self.graph_log,{'event':'TERMINAL_UNAPPLIED','id':self.pending['item'][0]['id']})
        if self.client:self.client.close()
        for stream in (self.decisions,self.graph_log,self.oracle_log):stream.close()
        self.closed=True
