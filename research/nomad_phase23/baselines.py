"""Frozen comparator solvers with measured, deadline-capped output delivery."""
import json,time,tempfile,shutil,threading
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase15b.depth import Snapshot,evaluate_samples
from nomad_phase15.evaluate import suffix
from nomad_phase20d.pool import evaluate_job as graph_job
from nomad_phase21.pool import evaluate_job as astar_job


class DeadlinePool:
    """Same stage solver calls; parent never applies results delivered after1s."""
    def __init__(self,pool,deadline_ns):self.pool=pool;self.deadline_ns=deadline_ns;self.futures=[]
    def map(self,fn,items):
        if time.monotonic_ns()>=self.deadline_ns:raise TimeoutError('Comparator deadline')
        futures=[self.pool.submit(fn,item) for item in items];self.futures.extend(futures)
        result=[]
        for future in futures:
            result.append(future.result(timeout=max(0.,(self.deadline_ns-time.monotonic_ns())/1e9)))
            if time.monotonic_ns()>self.deadline_ns:raise TimeoutError('Comparator late result discarded')
        return result
    def release(self,directory):
        # A late worker may still need its saved cache; remove it only after all
        # calls finish/cancel. This callback does not delay path application.
        from .anytime import _late_errors
        count=[len(self.futures)];lock=threading.Lock()
        if not count[0]:shutil.rmtree(directory);return
        def done(f):
            if not f.cancelled() and f.exception() is not None:_late_errors.put(repr(f.exception()))
            with lock:count[0]-=1;last=count[0]==0
            if last:shutil.rmtree(directory,ignore_errors=True)
        for f in self.futures:f.add_done_callback(done)
        for f in self.futures:f.cancel()


def plan(pool,c,method,recent_file):
    field=Snapshot.load(c['snapshot_file']);started=time.monotonic_ns();deadline=started+1_000_000_000
    selected,detail=evaluate_samples(np.asarray(c['samples_world']),c['B'],field)
    if c.get('trigger')!='B' and not detail['all_unsafe']:
        return dict(accepted=True,path=selected.tolist(),disposition='SAFE_SAMPLE',compute_s=(time.monotonic_ns()-started)/1e9,
            selection=detail,application_delay_s=0.,application_rule='Original FRESHEST switch B; no R2/R3 job')
    old=c.get('baseline_old_path',c.get('old_path'));keep=False
    if old is not None:
        tail,length=suffix(old,c['B']);_,check=evaluate_samples(np.repeat(np.asarray(old)[None],8,axis=0),c['B'],field)
        keep=not check['all_unsafe'] and length>=.25
    fallback=dict(accepted=keep,path=old if keep else None,disposition='KEEP_ACTIVE' if keep else 'STOP_WAIT_NO_FIXED_PATH',recovery_replanning_not_simulated=True)
    settings=json.loads((ROOT/'research/nomad_phase21/protocol.json').read_text())['astar']['selected'];stages=[];timed=DeadlinePool(pool,deadline)
    directory=tempfile.mkdtemp(prefix='phase23-baseline-')
    try:
        for kind in (['R3'] if c.get('trigger')=='B' else ['R2','R3']):
            begin=time.monotonic_ns()
            if begin>=deadline:break
            job=dict(kind=kind,job_id=0,B=c['B'],u_ref=c['baseline_u_ref'],previous_vw=c['previous_vw'],samples_world=c['samples_world'],snapshot_file=recent_file,evaluation_tick=c['tick'],cache_file=str(Path(directory)/(kind+'.npz')),dispatch_ns=started)
            try:r=graph_job(timed,job) if method=='C0' else astar_job(timed,job,settings['lambda'],settings['smoothing_iterations'])
            except TimeoutError:
                stages.append(dict(kind=kind,disposition='TIMEOUT',measured_wall_s=(time.monotonic_ns()-begin)/1e9));break
            r['measured_wall_s']=(time.monotonic_ns()-begin)/1e9;stages.append(r);index=r['selected_sample'];ready=time.monotonic_ns()
            if index is not None and ready<=deadline:
                return dict(accepted=True,path=r['results'][index]['path'],disposition=kind,compute_s=(ready-started)/1e9,
                    application_delay_s=(ready-started)/1e9,stages=stages,selection=detail,deadline_s=1.,late_results_used=False)
        elapsed=(time.monotonic_ns()-started)/1e9
        return dict(fallback,compute_s=elapsed,application_delay_s=min(elapsed,1.),stages=stages,selection=detail,deadline_s=1.,late_results_used=False)
    finally:timed.release(directory)
