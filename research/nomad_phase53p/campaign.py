"""Serial resume/retry engine. One separately registered smoke, never a main preflight drive."""
import argparse,json,os,signal,subprocess,sys
from pathlib import Path
from nomad_phase26 import campaign as base
from nomad_phase26.launch import environment
from nomad_phase40p.campaign import capacity
from nomad_phase40p.launch import bind
from nomad_phase0.s0_batch import exclusive_batch
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,SMOKE_ROOT,protocol,verify

class Routes:
    def __getattr__(self,key):return getattr(subprocess,key)
    def Popen(self,args,*a,**kw):
        args=['nomad_phase53p.launch' if x=='nomad_phase26.launch' else x for x in args]
        if str(SMOKE_ROOT) in ' '.join(map(str,args)) and '--smoke' not in args:args.append('--smoke')
        return subprocess.Popen(args,*a,**kw)

def jobs(root=RUN_ROOT):return bind(base.jobs,protocol=protocol)(root,False)
def smoke_job():
    j=dict(scene='LC_D075',index=95,method='GRAPH-HO',key='LC_D075_095_GRAPH-HO')
    j['outputs']=[str(SMOKE_ROOT/'main'/j['key']/'attempt1')];return j

def run(root,smoke=False):
    p=verify();plan=[smoke_job()] if smoke else jobs(root)
    if smoke:assert not root.exists(),'Only one smoke; preserve any existing output'
    else:
        ready=base.read(OUT/'preparation/smoke.json',{})
        assert ready.get('technical_validation')=='PASS' and ready['protocol_sha256']==sha256_file(HERE/'protocol.json'),'Registered smoke audit must PASS'
        assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip(),'Commit frozen sources before main'
    root.mkdir(parents=True,exist_ok=True)
    if base.read(root/'complete.json',{}).get('complete'):print('[complete] no repeats',flush=True);return
    saved=base.read(root/'plan.json')
    if saved:assert saved['protocol']==p
    else:base.write(root/'plan.json',dict(protocol=p,jobs=plan))
    state=base.load_state(root) or {}
    if state:print('[resume]',state.get('current'),flush=True)
    state.update(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],planned=len(plan),smoke=smoke)
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
            base.ensure_reserve(root)
            print('[smoke]' if smoke else '[main]',job['key'],'start',flush=True)
            result=runner(root,job,state,False) # smoke is routed below, single output prevents retry
            if result is None:return
            print('[audit]',job['key'],result['technical_validation'],flush=True)
            if smoke:
                result=dict(result,protocol_sha256=sha256_file(HERE/'protocol.json'),excluded_from_main=True)
                base.write(OUT/'preparation/smoke.json',result)
                assert result['technical_validation']=='PASS',result.get('error')
        if not smoke:
            state['current']='report';base.write(root/'state.json',state)
            with (root/'report.log').open('a') as log:
                subprocess.run(['/usr/bin/python3','-u','-m','nomad_phase53p.report','--publish'],cwd=ROOT,env=environment(),stdout=log,stderr=subprocess.STDOUT,check=True)
        state.update(status='COMPLETE',current=None);base.write(root/'complete.json',dict(complete=True,smoke=smoke))
    except BaseException as exc:
        state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));raise
    finally:state.update(pid=None);base.write(root/'state.json',state)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');ap.add_argument('--smoke',action='store_true');a=ap.parse_args()
    root=SMOKE_ROOT if a.smoke else RUN_ROOT
    if a.status:print(json.dumps(dict(base.status(root),planned=1 if a.smoke else 40)));return
    verify()
    if a.dry_run:
        plan=jobs();print(json.dumps(dict(planned=len(plan),jobs=plan,disk=capacity(root,plan),simulations_started=0)));return
    with exclusive_batch():run(root,a.smoke)
if __name__=='__main__':main()
