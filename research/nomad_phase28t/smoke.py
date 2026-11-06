"""User-only one-run entry; no retry and no main campaign invocation."""
import argparse,json,subprocess
from pathlib import Path
from nomad_isaac.common import ROOT
from nomad_phase26.launch import environment
from .config import SMOKE_ROOT,verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=SMOKE_ROOT);ap.add_argument('--dry-run',action='store_true');a=ap.parse_args();out=a.output.resolve()
    assert out==SMOKE_ROOT.resolve();verify()
    cmd=['/usr/bin/python3','-u','-m','nomad_phase28t.launch','--scene','H1','--method','C0-H','--index','201','--output',str(out)]
    if a.dry_run:print(json.dumps(dict(runs=1,scene='H1',method='C0-H',seed=201,navigation_started=0,command=cmd)));return
    if out.exists():raise RuntimeError('Existing smoke preserved; no automatic repeat/retry')
    result=subprocess.run(cmd,cwd=ROOT,env=environment(),check=False)
    if out.exists():subprocess.run(['/usr/bin/python3','-u','-m','nomad_phase28t.report','--smoke-root',str(out)],cwd=ROOT,env=environment(),check=True)
    if result.returncode:raise SystemExit(result.returncode)

if __name__=='__main__':main()
