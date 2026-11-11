"""Synchronous system-Python RPC with persistent four-process 11-start pool."""
import json,os,select,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT
from nomad_phase28.telemetry import builtin
FIELD=None;FIELD_FILE=None

def start_one(payload):
    global FIELD,FIELD_FILE
    from nomad_phase15b.depth import Snapshot
    from nomad_phase33p.storage import load_snapshot
    from .graph import Graph,solve_start
    job,index=payload
    if FIELD_FILE!=job['snapshot_file']:
        FIELD=load_snapshot(Snapshot,job['snapshot_file']);FIELD_FILE=job['snapshot_file']
    g=Graph(job['initial'],job['omega'],job['samples_world'],FIELD,job['previous'],job['simulation_time_s'])
    return builtin(solve_start(g,index))

def solve(job,pool):
    begin=time.perf_counter()
    results=list(pool.map(start_one,[(job,k) for k in range(11)]))
    return builtin(dict(results=results,solve_s=time.perf_counter()-begin))

class Client:
    def __init__(self,out):
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(out/'ugraph_worker.log').open('x')
        self.proc=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase55p.worker'],cwd=ROOT,env=env,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        assert self.read()['kind']=='ready'
    def read(self):
        if not select.select([self.proc.stdout],[],[],300)[0]:raise TimeoutError('U-Graph RPC technical watchdog; no numerical output')
        line=self.proc.stdout.readline()
        if not line:raise RuntimeError('U-Graph worker exited; see ugraph_worker.log')
        r=json.loads(line)
        if r.get('kind')=='error':raise RuntimeError(r['error'])
        return r
    def solve(self,job):
        begin=time.perf_counter();self.proc.stdin.write(json.dumps(builtin(job),allow_nan=False)+'\n');self.proc.stdin.flush()
        r=self.read();r['rpc_s']=time.perf_counter()-begin;return r
    def close(self):
        try:
            if self.proc.poll() is None:
                self.proc.stdin.write('{"kind":"stop"}\n');self.proc.stdin.flush();self.proc.wait(timeout=10)
        finally:
            if self.proc.poll() is None:self.proc.kill();self.proc.wait()
            self.proc.stdin.close();self.proc.stdout.close();self.log.close()

def main():
    import sys,traceback,multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(4,mp_context=multiprocessing.get_context('spawn')) as pool:
        print(json.dumps(dict(kind='ready',workers=4,starts=11)),flush=True)
        for line in sys.stdin:
            job=json.loads(line)
            if job.get('kind')=='stop':return
            try:r=solve(job,pool)
            except Exception as exc:traceback.print_exc();r=dict(kind='error',error=repr(exc))
            print(json.dumps(builtin(r),allow_nan=False),flush=True)
if __name__=='__main__':main()
