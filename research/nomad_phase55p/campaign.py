"""24 sequential runs, resumable, one technical retry, no preparation smoke."""
import argparse,json,os,signal,subprocess
from pathlib import Path
from nomad_phase26 import campaign as base
from nomad_phase26.launch import environment
from nomad_phase40p.campaign import capacity
from nomad_phase40p.launch import bind
from nomad_phase0.s0_batch import exclusive_batch
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,protocol,verify
class Routes:
    def __getattr__(self,key):return getattr(subprocess,key)
    def Popen(self,args,*a,**kw):
        return subprocess.Popen(['nomad_phase55p.launch' if x=='nomad_phase26.launch' else x for x in args],*a,**kw)
def jobs(root=RUN_ROOT):return bind(base.jobs,protocol=protocol)(root,False)
def run():
    p=verify();root=RUN_ROOT;plan=jobs();ready=base.read(OUT/'preparation/validation.json',{})
    assert ready.get('passed') and ready['protocol_sha256']==sha256_file(HERE/'protocol.json'),'Frozen dry-run required'
    assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip(),'Commit sources before main'
    root.mkdir(parents=True,exist_ok=True)
    if base.read(root/'complete.json',{}).get('complete'):print('[complete] no repeats',flush=True);return
    saved=base.read(root/'plan.json')
    if saved:assert saved['protocol']==p
    else:base.write(root/'plan.json',dict(protocol=p,jobs=plan))
    state=base.load_state(root) or {};state.update(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],planned=24)
    def stop(*_):raise KeyboardInterrupt('Campaign interrupted')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    from .metrics import audit
    import nomad_phase26.metrics as metric_module
    metric_module.audit=audit
    runner=bind(base.run_job,subprocess=Routes(),capacity=capacity,jobs=lambda r:plan)
    try:
        for job in plan:
            if (root/'metrics'/f"{job['key']}.json").exists():continue
            disk=capacity(root,plan);base.write(root/'capacity.json',disk)
            if not disk['enough']:state.update(status='LOW_DISK_STOP');return
            base.ensure_reserve(root);print('[main]',job['key'],'start',flush=True)
            result=runner(root,job,state,False)
            if result is None:return
            print('[audit]',job['key'],result['technical_validation'],flush=True)
        state['current']='report';base.write(root/'state.json',state)
        with (root/'report.log').open('a') as log:
            subprocess.run(['/usr/bin/python3','-u','-m','nomad_phase55p.report','--publish'],cwd=ROOT,env=environment(),stdout=log,stderr=subprocess.STDOUT,check=True)
        state.update(status='COMPLETE',current=None);base.write(root/'complete.json',dict(complete=True))
    except BaseException as exc:
        state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));raise
    finally:state.update(pid=None);base.write(root/'state.json',state)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(dict(base.status(RUN_ROOT),planned=24)));return
    verify()
    if a.dry_run:
        plan=jobs();print(json.dumps(dict(planned=len(plan),jobs=plan,disk=capacity(RUN_ROOT,plan),simulations_started=0)));return
    with exclusive_batch():run()
if __name__=='__main__':main()
