"""Synchronous system-Python RPC; original ClearanceGraph numerical code unchanged."""
import json,os,select,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT
from nomad_phase28.telemetry import builtin

def solve(job):
    from nomad_phase17.graph import ClearanceGraph
    from nomad_phase15b.depth import Snapshot
    from nomad_phase33p.storage import load_snapshot
    start=time.perf_counter()
    try:
        graph=ClearanceGraph(job['world_xy'],job['boundary'],job['previous_command'],load_snapshot(Snapshot,job['snapshot_file']),job['previous_xy'])
    except ValueError as exc:
        return dict(accepted=False,reason='INITIALIZATION_REJECTED',error=str(exc),solve_s=time.perf_counter()-start)
    poses,solver=graph.solve()
    return builtin(dict(accepted=bool(solver['feasible']),reason='ACCEPTED' if solver['feasible'] else 'SOLVER_OR_CERTIFICATE_REJECT',
                        poses=poses,solver=solver,solve_s=time.perf_counter()-start))

class Client:
    def __init__(self,out):
        env=os.environ.copy()
        for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
        env.update(PYTHONPATH=str(ROOT/'research'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        self.log=(out/'graph_ho_worker.log').open('x')
        self.proc=subprocess.Popen(['/usr/bin/python3','-u','-m','nomad_phase53p.worker'],cwd=ROOT,env=env,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        assert self.read()['kind']=='ready'
    def read(self):
        if not select.select([self.proc.stdout],[],[],30)[0]:raise TimeoutError('Graph RPC technical watchdog (not solver option)')
        line=self.proc.stdout.readline()
        if not line:raise RuntimeError('Graph RPC terminated; see graph_ho_worker.log')
        result=json.loads(line)
        if result.get('kind')=='error':raise RuntimeError(result['error'])
        return result
    def solve(self,job):
        start=time.perf_counter();self.proc.stdin.write(json.dumps(builtin(job),allow_nan=False)+'\n');self.proc.stdin.flush()
        r=self.read();r['rpc_s']=time.perf_counter()-start;return r
    def close(self):
        try:
            if self.proc.poll() is None:
                self.proc.stdin.write('{"kind":"stop"}\n');self.proc.stdin.flush();self.proc.wait(timeout=10)
        finally:
            if self.proc.poll() is None:self.proc.kill();self.proc.wait()
            self.proc.stdin.close();self.proc.stdout.close();self.log.close()

def main():
    from nomad_phase17.graph import ClearanceGraph
    print(json.dumps(dict(kind='ready')),flush=True)
    import sys,traceback
    for line in sys.stdin:
        job=json.loads(line)
        if job.get('kind')=='stop':return
        try:r=solve(job)
        except Exception as exc:traceback.print_exc();r=dict(kind='error',error=repr(exc))
        print(json.dumps(builtin(r),allow_nan=False),flush=True)
if __name__=='__main__':main()
