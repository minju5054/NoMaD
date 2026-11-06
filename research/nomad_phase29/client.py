import hashlib,json,os,secrets,subprocess,sys,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from multiprocessing.connection import Client
from multiprocessing import shared_memory
import numpy as np
import scipy
from nomad_isaac.common import ROOT
from nomad_phase28.telemetry import builtin

class Worker:
    def __init__(self,out):
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='phase29-transport');self.socket='/tmp/nomad29-'+hashlib.sha1(str(out).encode()).hexdigest()[:12]+'.sock'
        assert len(self.socket.encode())<100 and not Path(self.socket).exists()
        token=secrets.token_bytes(32);env=os.environ.copy();env['NOMAD_PHASE29_AUTH']=token.hex()
        roots=[str(ROOT/'research'),str(Path(np.__file__).parent.parent),str(Path(scipy.__file__).parent.parent),*sys.path]
        env['PYTHONPATH']=os.pathsep.join(dict.fromkeys(p for p in roots if p and os.path.isdir(p)));env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(out/'phase29_worker.log').open('x')
        self.process=subprocess.Popen([sys.executable,'-u','-m','nomad_phase29.worker','--socket',self.socket,'--cpu','7','--provenance',str(out/'phase29_worker_provenance.json')],cwd=ROOT,env=env,stdout=self.log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+30
        while not Path(self.socket).exists():
            if self.process.poll() is not None:raise RuntimeError('Phase29 numerical worker startup failed')
            if time.monotonic()>deadline:raise TimeoutError('Phase29 worker readiness')
            time.sleep(.01)
        self.connection=Client(self.socket,family='AF_UNIX',authkey=token)
        assert self.connection.poll(30);self.info=json.loads(self.connection.recv_bytes())
        assert self.info['numpy']==np.__version__ and self.info['scipy']==scipy.__version__ and self.info['affinity']['actual']==[7]
    def submit(self,job,field):return self.pool.submit(self.compute,job,field)
    def compute(self,job,field):
        blocks=[]
        try:
            arrays={}
            for name in ('values','occupied','observed'):
                a=np.ascontiguousarray(getattr(field,name));b=shared_memory.SharedMemory(create=True,size=a.nbytes);blocks.append(b);np.ndarray(a.shape,dtype=a.dtype,buffer=b.buf)[:]=a
                arrays[name]=dict(name=b.name,shape=list(a.shape),dtype=a.dtype.str)
            payload=dict(job=job,arrays=arrays,field=dict(origin=field.origin.tolist(),h=field.h,radius=field.radius,error_bound=field.error_bound,metadata=dict(field.metadata)))
            self.connection.send_bytes(json.dumps(builtin(payload)).encode())
            if not self.connection.poll(30):raise TimeoutError('Phase29 numerical worker response')
            r=json.loads(self.connection.recv_bytes())
            if r.get('technical_error'):raise RuntimeError(r['technical_error'])
            assert r['job_id']==job['job_id'];r['result_received_ns']=time.monotonic_ns();return r
        finally:
            for b in blocks:b.close();b.unlink()
    def close(self):
        self.pool.shutdown(wait=True)
        try:
            if self.process.poll() is None:self.connection.send_bytes(b'{"shutdown":true}');self.process.wait(timeout=15)
        finally:
            if self.process.poll() is None:self.process.terminate();self.process.wait(timeout=10)
            self.connection.close();self.log.close();Path(self.socket).unlink(missing_ok=True)
