"""Immutable map transport and nonblocking latest-output reads."""
import json,os,subprocess,threading,time,queue
from pathlib import Path
from nomad_isaac.common import ROOT
from nomad_phase19r.evaluate import clean
import numpy as np

class Worker:
    def __init__(self,out):
        self.out=Path(out);self.folder=self.out/'g_jobs';self.folder.mkdir();self.lock=threading.Lock();self.write_lock=threading.Lock();self.latest={};self.deadlines={};self.error=None;self.ready=queue.Queue();self.threads=[]
        self.log=(self.out/'g_pool.log').open('x');self.records=(self.out/'g_pool.jsonl').open('x')
        env=os.environ.copy()
        for key in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(key,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.process=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase24r.online_pool'],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        def read():
            try:
                for line in self.process.stdout:
                    r=json.loads(line)
                    if r['kind']=='READY':self.ready.put(r);continue
                    if r['kind']=='ERROR':self.error=RuntimeError(r['error']);self.records.write(json.dumps(r)+'\n');self.records.flush();continue
                    r['parent_received_ns']=time.monotonic_ns()
                    with self.lock:
                        if r['parent_received_ns']<=self.deadlines[r['job_id']]:self.latest.setdefault(r['job_id'],[]).append(r)
                    if r['kind']=='FINAL':
                        (self.folder/f"result_{r['job_id']:04d}.json").write_text(json.dumps(r));self.records.write(json.dumps(dict(job_id=r['job_id'],kind='FINAL',parent_received_ns=r['parent_received_ns'],compute_s=r['result']['compute_s'],output_type=r['result']['output_type']))+'\n');self.records.flush()
            except BaseException as exc:self.error=exc
        self.reader=threading.Thread(target=read,daemon=True);self.reader.start();ready=self.ready.get(timeout=90);assert len(set(ready['pids']))==4
        (self.out/'g_pool_environment.json').write_text(json.dumps(ready,indent=2))
    def submit(self,job,field):
        with self.lock:self.deadlines[job['job_id']]=job['dispatch_ns']+500_000_000
        def work():
            try:
                file=self.folder/f"snapshot_{job['job_id']:04d}.npz"
                # Base and last-free evidence are preserved; the coordinator builds
                # the same strict EDT as C0 R3 once per job.
                np.savez(file,values=field.values,occupied=field.occupied,observed=field.observed,origin=field.origin,h=field.h,radius=field.radius,last_free_tick=field.last_free_tick,metadata=json.dumps(dict(field.metadata)))
                payload=clean(job);payload['case']['snapshot_file']=str(file)
                (self.folder/f"input_{job['job_id']:04d}.json").write_text(json.dumps(payload))
                with self.write_lock:self.process.stdin.write(json.dumps(payload)+'\n');self.process.stdin.flush()
            except BaseException as exc:self.error=exc
        thread=threading.Thread(target=work,daemon=True);thread.start();self.threads.append(thread)
    def result(self,identifier,cutoff_ns):
        if self.error:raise RuntimeError('G worker failed') from self.error
        if self.process.poll() is not None:raise RuntimeError('G coordinator exited')
        with self.lock:
            return next((r for r in reversed(self.latest.get(identifier,[])) if r['parent_received_ns']<=cutoff_ns),None)
    def close(self):
        for t in self.threads:t.join(10)
        if self.process.poll() is None:self.process.stdin.write('null\n');self.process.stdin.flush();self.process.wait(timeout=30)
        self.reader.join(5);self.process.stdin.close();self.process.stdout.close();self.records.close();self.log.close()
        if self.error:raise RuntimeError('G worker failed') from self.error
