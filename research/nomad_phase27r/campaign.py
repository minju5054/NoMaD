"""Reuse Phase26 locking/order/retry/disk logic; route only launch/report modules."""
import argparse
import json
import subprocess
from pathlib import Path
from nomad_phase26 import campaign as base
from .config import protocol,verify,check_run_root

ROUTES={'nomad_phase26.launch':'nomad_phase27r.launch','nomad_phase26.report':'nomad_phase27r.report'}

def routed(argv):
    if not isinstance(argv,(list,tuple)):return argv
    result=list(argv)
    if '-m' in result:
        i=result.index('-m')+1
        if i<len(result):result[i]=ROUTES.get(result[i],result[i])
    return result

class ProcessRoutes:
    """Local proxy; does not patch the global subprocess module or any controller."""
    def __getattr__(self,name):return getattr(subprocess,name)
    def Popen(self,argv,*a,**kw):return subprocess.Popen(routed(argv),*a,**kw)
    def run(self,argv,*a,**kw):return subprocess.run(routed(argv),*a,**kw)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-root',type=Path,required=True)
    parser.add_argument('--status',action='store_true');parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args();root=check_run_root(args.run_root)
    if args.status:print(json.dumps(base.status(root)));return
    base.verify=verify;base.protocol=protocol;base.subprocess=ProcessRoutes()
    if args.dry_run:
        p=verify();plan=base.jobs(root)
        print(json.dumps(dict(planned=len(plan),indices=p['indices'],disk=base.capacity(root,plan),navigation_started=0)))
        return
    # Phase26 main retains its exclusive lock, atomic state, retry, socket,
    # frozen-preflight and per-attempt capacity guards. No smoke is added.
    base.main()

if __name__=='__main__':main()
