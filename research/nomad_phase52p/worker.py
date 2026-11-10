"""Queued nonblocking transport to a fixed four-process R2 broker."""
import json,os,queue,subprocess,threading,time
from pathlib import Path
from nomad_isaac.common import ROOT
from nomad_phase28.telemetry import builtin

class Worker:
    def __init__(self,out):
        self.out=Path(out);self.queue=queue.Queue();self.results=queue.SimpleQueue();self.ready=queue.Queue();self.error=None
        self.folder=self.out/'reconstruction_jobs';self.folder.mkdir();self.log=(self.out/'reconstruction_pool.log').open('x')
        self.records=(self.out/'reconstruction_pool.jsonl').open('x')
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.process=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase52p.pool'],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        self.reader=threading.Thread(target=self.read,daemon=True);self.reader.start()
        try:ready=self.ready.get(timeout=90);assert ready.get('kind')=='READY' and ready['workers']==4,ready
        except BaseException:
            self.process.terminate();self.process.wait(timeout=15);raise
        (self.out/'reconstruction_environment.json').write_text(json.dumps(ready))
        self.writer=threading.Thread(target=self.write,daemon=True);self.writer.start()
    def read(self):
        try:
            for line in self.process.stdout:
                row=json.loads(line)
                if row.get('kind')=='READY':self.ready.put(row);continue
                row['parent_received_ns']=time.monotonic_ns();self.records.write(json.dumps(builtin(row),allow_nan=False)+'\n');self.records.flush();self.results.put(row)
        except BaseException as e:self.error=repr(e);self.ready.put(dict(error=self.error))
    def write(self):
        try:
            while True:
                item=self.queue.get()
                if item is None:self.process.stdin.write('null\n');self.process.stdin.flush();return
                job,field=item;file=self.folder/f"input_{job['job_id']:04d}.npz";field.save(file)
                job=dict(job,snapshot_file=str(file));(self.folder/f"job_{job['job_id']:04d}.json").write_text(json.dumps(builtin(job),allow_nan=False))
                self.process.stdin.write(json.dumps(builtin(job),allow_nan=False)+'\n');self.process.stdin.flush()
        except BaseException as e:self.error=repr(e)
    def submit(self,job,field):
        if self.error:raise RuntimeError(self.error)
        self.queue.put_nowait((dict(job),field))
    def poll(self):
        if self.error:raise RuntimeError(self.error)
        if self.process.poll() is not None:raise RuntimeError('Reconstruction broker exited during navigation')
        try:return self.results.get_nowait()
        except queue.Empty:return None
    def close(self):
        self.queue.put(None);self.writer.join(35)
        try:
            if self.writer.is_alive():raise TimeoutError('Reconstruction archive/send drain')
            self.process.wait(timeout=60);self.reader.join(5)
            if self.process.returncode or self.error:raise RuntimeError(self.error or f'Broker exit{self.process.returncode}')
        finally:
            if self.process.poll() is None:self.process.terminate();self.process.wait(timeout=15)
            self.process.stdin.close();self.process.stdout.close();self.log.close();self.records.close()
