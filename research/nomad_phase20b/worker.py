"""Isaac-side nonblocking facade; pool lives in a clean /usr/bin/python3 broker."""
import json,os,queue,subprocess,threading,time
from pathlib import Path
from nomad_isaac.common import ROOT

def disposition(result,dispatch_ns,now_ns):
    if result is None:return 'TIMEOUT' if now_ns-dispatch_ns>1_000_000_000 else 'WAIT'
    if result['end_ns']-dispatch_ns>1_000_000_000:return 'TIMEOUT'
    if result.get('error'):return 'ERROR'
    return 'ACCEPTED' if result['selected_sample'] is not None else 'REJECTED'


class RepairWorker:
    def __init__(self,out):
        self.thread=None;self.results=queue.SimpleQueue();self.messages=queue.Queue();self.error=None
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(Path(out)/'repair_pool.log').open('x')
        self.jobs_log=(Path(out)/'repair_pool_jobs.jsonl').open('x')
        self.process=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase20b.pool_server'],cwd=ROOT,env=env,
                                      stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        def read():
            try:
                for line in self.process.stdout:self.messages.put(json.loads(line))
            except BaseException as exc:self.error=repr(exc)
            self.messages.put(dict(kind='BROKER_CLOSED',error=self.error))
        self.reader=threading.Thread(target=read,daemon=True);self.reader.start()
        try:
            ready=self.messages.get(timeout=90);assert ready.get('kind')=='READY' and ready['workers']==4,ready
        except BaseException:
            self.process.terminate();self.process.wait(timeout=15);self.log.close();self.jobs_log.close();raise
        (Path(out)/'repair_pool_environment.json').write_text(json.dumps(ready,indent=2))

    def busy(self):return self.thread is not None and self.thread.is_alive()
    def submit(self,job,field):
        assert not self.busy()
        payload=dict(job_id=job['job_id'],B=job['B'],samples_world=job['samples_world'],dispatch_ns=job['dispatch_ns'],snapshot_file=field.metadata['file'])
        def bridge():
            try:
                self.process.stdin.write(json.dumps(payload)+'\n');self.process.stdin.flush()
                result=self.messages.get(timeout=30)
                assert result.get('kind')=='RESULT' and result['job_id']==job['job_id'],result
                result['parent_received_ns']=time.monotonic_ns()
            except BaseException as exc:result=dict(job_id=job['job_id'],start_ns=time.monotonic_ns(),end_ns=time.monotonic_ns(),error=repr(exc),selected_sample=None,results=[])
            self.jobs_log.write(json.dumps(result,allow_nan=False)+'\n');self.jobs_log.flush();self.results.put(result)
        self.thread=threading.Thread(target=bridge,name='repair-pool-delivery',daemon=True);self.thread.start()
    def poll(self):
        try:return self.results.get_nowait()
        except queue.Empty:return None
    def close(self):
        if self.thread:self.thread.join(35)
        try:
            if self.process.poll() is None:self.process.stdin.write('null\n');self.process.stdin.flush();self.process.wait(timeout=20)
        finally:
            if self.process.poll() is None:self.process.terminate();self.process.wait(timeout=15)
            self.log.close();self.jobs_log.close()
