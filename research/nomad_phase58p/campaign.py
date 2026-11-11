"""Same serial/resumable campaign and one technical retry; no smoke."""
import argparse,inspect,json,subprocess
from nomad_phase55p import campaign as previous
from nomad_phase26 import campaign as base
from nomad_phase40p.launch import bind
from nomad_phase40p.campaign import capacity
from nomad_phase0.s0_batch import exclusive_batch
from .config import ROOT,HERE,OUT,RUN_ROOT,protocol,verify
class Routes(previous.Routes):
    def Popen(self,args,*a,**kw):
        return subprocess.Popen(['nomad_phase58p.launch' if x=='nomad_phase26.launch' else x for x in args],*a,**kw)
def jobs(root=RUN_ROOT):return bind(base.jobs,protocol=protocol)(root,False)
source=inspect.getsource(previous.run).replace('planned=24','planned=18').replace('nomad_phase55p.report','nomad_phase58p.report')
ns=dict(previous.run.__globals__,__package__=__package__,ROOT=ROOT,HERE=HERE,OUT=OUT,RUN_ROOT=RUN_ROOT,verify=verify,jobs=jobs,Routes=Routes)
exec(compile(source,__file__,'exec'),ns);run=ns['run']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    if a.status:print(json.dumps(dict(base.status(RUN_ROOT),planned=18)));return
    verify()
    if a.dry_run:
        plan=jobs();print(json.dumps(dict(planned=len(plan),jobs=plan,disk=capacity(RUN_ROOT,plan),simulations_started=0)));return
    with exclusive_batch():run()
if __name__=='__main__':main()
