"""Reuse Phase53 serial/retry/resume engine; no smoke, four fixed main runs."""
import argparse,inspect,json,subprocess
from nomad_phase53p import campaign as frozen
from nomad_phase40p.launch import bind
from nomad_phase0.s0_batch import exclusive_batch
from .config import ROOT,HERE,OUT,RUN_ROOT,protocol,verify

class Routes:
    def __getattr__(self,key):return getattr(subprocess,key)
    def Popen(self,args,*a,**kw):
        return subprocess.Popen(['nomad_h1v2_trial.launch' if x=='nomad_phase26.launch' else x for x in args],*a,**kw)

def jobs(root=RUN_ROOT):return bind(frozen.base.jobs,protocol=protocol)(root,False)

def run(root):
    source=inspect.getsource(frozen.run)
    old="""ready=base.read(OUT/'preparation/smoke.json',{})
        assert ready.get('technical_validation')=='PASS' and ready['protocol_sha256']==sha256_file(HERE/'protocol.json'),'Registered smoke audit must PASS'"""
    new="""ready=base.read(OUT/'preparation/validation.json',{})
        assert ready.get('passed') and ready['protocol_sha256']==sha256_file(HERE/'protocol.json'),'Four-case dry-run preparation must PASS'"""
    assert source.count(old)==1
    source=source.replace(old,new).replace('from .metrics import audit','from nomad_h1v2_trial.metrics import audit').replace("'nomad_phase53p.report'","'nomad_h1v2_trial.report'")
    ns=dict(frozen.run.__globals__,ROOT=ROOT,HERE=HERE,OUT=OUT,RUN_ROOT=RUN_ROOT,protocol=protocol,verify=verify,jobs=jobs,Routes=Routes)
    exec(compile(source,__file__,'exec'),ns);return ns['run'](root,False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--status',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(dict(frozen.base.status(RUN_ROOT),planned=4)));return
    verify()
    if a.dry_run:
        plan=jobs();print(json.dumps(dict(planned=len(plan),jobs=plan,disk=frozen.capacity(RUN_ROOT,plan),smoke=False,simulations_started=0)));return
    with exclusive_batch():run(RUN_ROOT)
if __name__=='__main__':main()
