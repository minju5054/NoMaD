"""One persistent numerical process; immutable SDF arrays cross via shared memory."""
import hashlib,json,os,secrets,subprocess,sys,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,Future
from multiprocessing.connection import Client
from multiprocessing import shared_memory
import numpy as np
import scipy
from nomad_isaac.common import ROOT
from .timing import LOCAL,BUDGET_S

class ProcessWorker:
    def __init__(self,out,cpu=None):
        self.out=Path(out);self.cpu=cpu;self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='h-sdf-transport');self.process=None;self.connection=None;self.failed=None;self.next_request=0
        self.socket='/tmp/nomad28t-'+hashlib.sha1(str(self.out).encode()).hexdigest()[:12]+'.sock';assert len(self.socket.encode())<100 and not Path(self.socket).exists()
        env=os.environ.copy();token=secrets.token_bytes(32);env['NOMAD_PHASE28T_AUTH']=token.hex()
        # Preserve the running simulator's numerical modules, not a different venv.
        roots=[str(ROOT/'research'),str(Path(np.__file__).parent.parent),str(Path(scipy.__file__).parent.parent),*sys.path]
        env['PYTHONPATH']=os.pathsep.join(dict.fromkeys(str(p) for p in roots if p and os.path.isdir(p)));env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        args=[sys.executable,'-u','-m','nomad_phase28t.worker','--socket',self.socket,'--provenance',str(self.out/'phase28t_worker_provenance.json')]
        if cpu is not None:args+=['--cpu',str(cpu)]
        self.log=(self.out/'phase28t_worker.log').open('x');self.process=subprocess.Popen(args,cwd=ROOT,env=env,stdout=self.log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+30
        try:
            while not Path(self.socket).exists():
                if self.process.poll() is not None:
                    detail='\n'.join((self.out/'phase28t_worker.log').read_text().splitlines()[-8:])
                    raise RuntimeError('Numerical worker failed before readiness: '+detail)
                if time.monotonic()>deadline:raise TimeoutError('Numerical worker readiness')
                time.sleep(.01)
            self.connection=Client(self.socket,family='AF_UNIX',authkey=token)
            if not self.connection.poll(30):raise TimeoutError('Numerical worker handshake')
            self.info=json.loads(self.connection.recv_bytes());assert self.info['numpy']==np.__version__ and self.info['scipy']==scipy.__version__
            assert self.info['numpy_file']==str(Path(np.__file__).resolve()) and self.info['scipy_file']==str(Path(scipy.__file__).resolve())
        except BaseException:
            self.process.terminate();self.process.wait(timeout=15);self.log.close()
            if Path(self.socket).exists():Path(self.socket).unlink()
            raise
    def submit(self,fn,B,vw,path,field,alpha,warm,started):
        if self.failed is not None:
            f=Future();f.set_result(dict(accepted=False,output_type='FALLBACK',disposition='WORKER_UNAVAILABLE',error=self.failed,wall_s=time.perf_counter()-started,timing={}));return f
        submitted=time.perf_counter_ns();prediction=dict(getattr(LOCAL,'prediction',{}))
        request=self.next_request;self.next_request+=1
        return self.pool.submit(self.compute,B,vw,path,field,alpha,warm,started,submitted,prediction,request)
    def compute(self,B,vw,path,field,alpha,warm,started,submitted,prediction,request):
        begin=time.perf_counter_ns();blocks=[];copy_start=time.perf_counter_ns()
        try:
            arrays={}
            for name in ('values','occupied','observed'):
                a=np.ascontiguousarray(getattr(field,name));block=shared_memory.SharedMemory(create=True,size=a.nbytes);blocks.append(block)
                np.ndarray(a.shape,dtype=a.dtype,buffer=block.buf)[:]=a
                arrays[name]=dict(name=block.name,shape=list(a.shape),dtype=a.dtype.str)
            copied=time.perf_counter_ns()
            payload=dict(request_id=request,B=B,vw=vw,path=path,alpha=alpha,warm=warm,started=started,arrays=arrays,
                field=dict(origin=field.origin.tolist(),h=field.h,radius=field.radius,error_bound=field.error_bound,metadata=dict(field.metadata)))
            send=time.perf_counter_ns();self.connection.send_bytes(json.dumps(payload).encode());sent=time.perf_counter_ns()
            if not self.connection.poll(2.):raise TimeoutError('Worker response missing')
            raw=self.connection.recv_bytes();received=time.perf_counter_ns();r=json.loads(raw);decoded=time.perf_counter_ns()
            if r.get('request_id')!=request:raise RuntimeError('Mismatched worker response; refuse stale result')
        except Exception as exc:
            r=dict(accepted=False,output_type='FALLBACK',disposition='TRANSPORT_ERROR',error=repr(exc),wall_s=time.perf_counter()-started,timing={});send=sent=received=decoded=None;copied=time.perf_counter_ns()
            self.failed=repr(exc)
            if self.process.poll() is None:self.process.terminate();self.process.wait(timeout=10)
            self.connection.close()
        finally:
            for block in blocks:
                block.close()
                try:block.unlink()
                except FileNotFoundError:pass
        ready=time.perf_counter_ns();timing=r.setdefault('timing',{})
        timing.update(request_id=request,dispatch_start_ns=round(started*1e9),B_prediction_start_ns=prediction.get('start_ns'),B_prediction_end_ns=prediction.get('end_ns'),
            submit_ns=submitted,transport_thread_start_ns=begin,sdf_copy_start_ns=copy_start,sdf_copy_end_ns=copied,parent_send_start_ns=send,parent_send_end_ns=sent,
            parent_receive_ns=received,parent_decode_end_ns=decoded,future_ready_ns=ready,shared_memory_bytes=sum(getattr(field,k).nbytes for k in ('values','occupied','observed')))
        r['worker_inclusive_wall_s']=r['wall_s'];r['worker_output_type']=r['output_type'];r['worker_disposition']=r.get('disposition');r['wall_s']=ready/1e9-started;r['over_deadline']=r['wall_s']>BUDGET_S
        if r['over_deadline']:
            timing['client_deadline_exceeded_ns']=ready
            r.update(accepted=False,output_type='FALLBACK',disposition='TRANSPORT_TIMEOUT' if r.get('disposition')!='TIMEOUT' else 'TIMEOUT')
        return r
    def shutdown(self,wait=True,cancel_futures=True):
        self.pool.shutdown(wait=wait,cancel_futures=cancel_futures)
        try:
            if self.process.poll() is None:
                self.connection.send_bytes(json.dumps(dict(shutdown=True)).encode());self.process.wait(timeout=10)
        finally:
            if self.process.poll() is None:self.process.terminate();self.process.wait(timeout=10)
            if self.connection is not None:self.connection.close()
            self.log.close()
            if Path(self.socket).exists():Path(self.socket).unlink()
