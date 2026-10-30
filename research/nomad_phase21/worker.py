"""Nonblocking job bridge; in-memory published snapshot copied to private job input."""
import json,os,queue,subprocess,threading,time
from pathlib import Path
from nomad_isaac.common import ROOT

class Worker:
    def __init__(self,out):
        self.out=Path(out);self.thread=None;self.results=queue.SimpleQueue();self.messages=queue.Queue()
        self.jobs=(self.out/'repair_pool_jobs.jsonl').open('x');self.log=(self.out/'repair_pool.log').open('x')
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.process=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase21.pool'],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        def read():
            try:
                for line in self.process.stdout:self.messages.put(json.loads(line))
            finally:self.messages.put(dict(kind='CLOSED'))
        self.reader=threading.Thread(target=read,daemon=True);self.reader.start()
        ready=self.messages.get(timeout=90);assert ready['kind']=='READY' and len(set(ready['pids']))==4
        (self.out/'repair_pool_environment.json').write_text(json.dumps(ready,indent=2))
    def busy(self):return self.thread is not None and self.thread.is_alive()
    def submit(self,job,field):
        assert not self.busy()
        kind=job.get('kind','R2');identifier=job['job_id'];folder=self.out/'repair_jobs';folder.mkdir(exist_ok=True)
        def work():
            try:
                source=folder/f'input_{identifier:04d}.npz';field.save(source,compressed=False)
                payload=dict(job,kind=kind,snapshot_file=str(source),cache_file=str(folder/f'cache_{identifier:04d}.npz'))
                (folder/f'transport_{identifier:04d}.json').write_text(json.dumps(payload))
                self.process.stdin.write(json.dumps(payload)+'\n');self.process.stdin.flush();r=self.messages.get(timeout=30)
                assert r.get('job_id')==identifier and r.get('kind')==kind,r
                r['parent_received_ns']=time.monotonic_ns()
            except BaseException as exc:r=dict(job_id=identifier,kind=kind,start_ns=time.monotonic_ns(),end_ns=time.monotonic_ns(),selected_sample=None,results=[],error=repr(exc))
            self.jobs.write(json.dumps(r)+'\n');self.jobs.flush();self.results.put(r)
        self.thread=threading.Thread(target=work,daemon=True,name='R2-R3-job-bridge');self.thread.start()
    def poll(self):
        try:return self.results.get_nowait()
        except queue.Empty:return None
    def close(self):
        if self.thread:self.thread.join(35)
        if self.process.poll() is None:self.process.stdin.write('null\n');self.process.stdin.flush();self.process.wait(timeout=20)
        self.process.stdin.close();self.process.stdout.close();self.jobs.close();self.log.close()
