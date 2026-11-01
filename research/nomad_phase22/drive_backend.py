"""Frozen A*/Graph stage functions and explicit one-budget refinement branches."""
import json,os,sys,time,multiprocessing as mp,threading,queue,subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from nomad_isaac.common import ROOT
from nomad_phase19r.evaluate import clean
from nomad_phase20d.recent import load_cache
from nomad_phase20c.detour import select_detour
from nomad_phase20d.pool import solve_one as graph_one
from nomad_phase21.pool import evaluate_job as astar_job,initialize,ping
from .refine import graph_refine
from .drive_config import protocol


def select_final(astar,refined,graph,deadline_ns,now_ns):
    """Branch unit: a cached predeadline A* result remains usable after refine timeout."""
    good=lambda r:r is not None and r.get('selected_sample') is not None and r['end_ns']<=deadline_ns
    if good(astar):
        if good(refined):return 'REFINED',refined
        return 'A*_RAW',astar
    if good(graph):return 'GRAPH_FALLBACK',graph
    return 'NONE',None


def composite(pool,job,send,settings,astar_settings):
    start=time.monotonic_ns();deadline=job['dispatch_ns']+1_000_000_000
    a=astar_job(pool,job,astar_settings['lambda'],astar_settings['smoothing_iterations']);send(dict(message='ASTAR_READY',result=a))
    selected=a['selected_sample'];refined=graph=None
    if selected is not None and a['end_ns']<=deadline:
        base,strict=load_cache(job['cache_file'])
        r=graph_refine(job['B'],job['u_ref'],base,strict,a['results'][selected]['path'],job['anchor_xy'],settings,deadline)
        ended=time.monotonic_ns();refined=dict(job_id=job['job_id'],kind='R3',start_ns=start,end_ns=ended,results=[r],selected_sample=0 if r['accepted'] else None,
            pool_wall_s=(ended-start)/1e9,dispatch_to_complete_s=(ended-job['dispatch_ns'])/1e9,sample_solve_s=[r['refinement_wall_s']],cache=a['cache'])
    elif time.monotonic_ns()<deadline:
        results=list(pool.map(graph_one,[('R3',i,job,job['cache_file']) for i in range(7)]));ended=time.monotonic_ns();which=select_detour(results)
        graph=dict(job_id=job['job_id'],kind='R3',start_ns=start,end_ns=ended,results=results,selected_sample=which,pool_wall_s=(ended-start)/1e9,dispatch_to_complete_s=(ended-job['dispatch_ns'])/1e9,
            sample_solve_s=[r['total_attempt_s'] for r in results],cache=a['cache'])
    branch,result=select_final(a,refined,graph,deadline,time.monotonic_ns());ended=time.monotonic_ns()
    if result is None:result=dict(job_id=job['job_id'],kind='R3',start_ns=start,end_ns=ended,results=[],selected_sample=None,pool_wall_s=(ended-start)/1e9,dispatch_to_complete_s=(ended-job['dispatch_ns'])/1e9,sample_solve_s=[],cache=a['cache'])
    return dict(**result,branch=branch,backend_end_ns=ended,decision_ns=ended,decision_wall_s=(ended-job['dispatch_ns'])/1e9,deadline_ns=deadline,stage_results=dict(astar=a,refine=refined,graph=graph))


def server():
    p=protocol();settings=p['refine_settings'];astar_settings=p['astar_settings'];ctx=mp.get_context('spawn');q=ctx.Queue()
    with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
        tasks=[pool.submit(ping) for _ in range(4)];pids=[q.get(timeout=90) for _ in range(4)]
        for f in tasks:f.result()
        print(json.dumps(dict(message='READY',workers=4,pids=pids)),flush=True)
        for line in sys.stdin:
            job=json.loads(line)
            if job is None:break
            try:
                if job['kind']=='R2':r=astar_job(pool,job,astar_settings['lambda'],astar_settings['smoothing_iterations'])
                else:r=composite(pool,job,lambda x:print(json.dumps(clean(x)),flush=True),settings,astar_settings)
            except BaseException as exc:r=dict(job_id=job['job_id'],kind=job['kind'],start_ns=time.monotonic_ns(),end_ns=time.monotonic_ns(),results=[],selected_sample=None,error=repr(exc),branch='NONE')
            print(json.dumps(clean(dict(message='FINAL',result=r))),flush=True)


class Worker:
    def __init__(self,out,anchor_provider):
        self.out=Path(out);self.anchor_provider=anchor_provider;self.thread=None;self.results=queue.SimpleQueue();self.messages=queue.Queue();self.partial=None;self.pending=None;self.delivered_ids=set();self.lock=threading.Lock();self.event_lock=threading.Lock()
        self.jobs=(self.out/'repair_pool_jobs.jsonl').open('x');self.log=(self.out/'repair_pool.log').open('x');self.events=(self.out/'refinement_branches.jsonl').open('x')
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.process=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase22.drive_backend'],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        def read():
            for line in self.process.stdout:self.messages.put(json.loads(line))
            self.messages.put(dict(message='CLOSED'))
        threading.Thread(target=read,daemon=True).start();ready=self.messages.get(timeout=90);assert ready['message']=='READY' and len(set(ready['pids']))==4
        (self.out/'repair_pool_environment.json').write_text(json.dumps(ready,indent=2))
    def event(self,name,**kw):
        with self.event_lock:self.events.write(json.dumps(clean(dict(event=name,**kw)))+'\n');self.events.flush()
    def busy(self):return self.thread is not None and self.thread.is_alive()
    def submit(self,job,field):
        assert not self.busy();payload=dict(job,kind=job.get('kind','R2'));payload.update(self.anchor_provider(job));folder=self.out/'repair_jobs';folder.mkdir(exist_ok=True)
        with self.lock:self.pending=payload;self.partial=None
        def work():
            try:
                source=folder/f"input_{job['job_id']:04d}.npz";field.save(source,compressed=False);payload.update(snapshot_file=str(source),cache_file=str(folder/f"cache_{job['job_id']:04d}.npz"))
                (folder/f"transport_{job['job_id']:04d}.json").write_text(json.dumps(clean(payload)));self.process.stdin.write(json.dumps(clean(payload))+'\n');self.process.stdin.flush()
                while True:
                    message=self.messages.get(timeout=30)
                    if message['message']=='ASTAR_READY':
                        with self.lock:self.partial=message['result']
                        self.event('ASTAR_READY',job_id=job['job_id'],ready_ns=self.partial['end_ns'],accepted=self.partial['selected_sample'] is not None)
                    elif message['message']=='FINAL':r=message['result'];break
                    else:raise RuntimeError(message)
                r['parent_received_ns']=time.monotonic_ns()
            except BaseException as exc:r=dict(job_id=job['job_id'],kind=payload['kind'],start_ns=time.monotonic_ns(),end_ns=time.monotonic_ns(),results=[],selected_sample=None,error=repr(exc),branch='NONE')
            self.jobs.write(json.dumps(clean(r))+'\n');self.jobs.flush()
            with self.lock:
                if job['job_id'] not in self.delivered_ids:self.results.put(r)
                else:self.event('LATE_BACKEND_RESULT',job_id=job['job_id'],backend_result=r)
        self.thread=threading.Thread(target=work,daemon=True);self.thread.start()
    def poll(self):
        with self.lock:
            try:r=self.results.get_nowait()
            except queue.Empty:r=None
            if r is not None:
                self.delivered_ids.add(r['job_id']);self.event('DELIVERED',job_id=r['job_id'],branch=r.get('branch','R2'),decision_ns=time.monotonic_ns(),plan_ready_ns=r['end_ns']);return r
            if self.pending and self.pending['job_id'] not in self.delivered_ids and self.pending['kind']=='R3' and time.monotonic_ns()>=self.pending['dispatch_ns']+1_000_000_000:
                deadline=self.pending['dispatch_ns']+1_000_000_000
                if self.partial and self.partial['selected_sample'] is not None and self.partial['end_ns']<=deadline:
                    r={**self.partial,'branch':'A*_RAW','decision_ns':time.monotonic_ns(),'deadline_ns':deadline,'fallback_reason':'REFINEMENT_TIMEOUT_CACHED_ASTAR'};self.delivered_ids.add(r['job_id'])
                    self.event('DELIVERED',job_id=r['job_id'],branch=r['branch'],decision_ns=r['decision_ns'],plan_ready_ns=r['end_ns']);return r
        return None
    def close(self):
        if self.thread:self.thread.join(35)
        if self.process.poll() is None:self.process.stdin.write('null\n');self.process.stdin.flush();self.process.wait(timeout=20)
        self.process.stdin.close();self.process.stdout.close();self.jobs.close();self.log.close();self.events.close()
if __name__=='__main__':server()
