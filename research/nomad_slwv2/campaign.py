import argparse
import json
import shutil
import subprocess
from pathlib import Path
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_j0 import campaign as frozen
from .config import ROOT,HERE,RUN_ROOT,verify,order,bind

def jobs(root):
    result=[]
    for j in order():
        key=f"SLW-v2_D{round(j['delay']*1000):03d}_{j['index']}_{j['method']}";out=Path(root)/'main'/key/'attempt1'
        argv=['/usr/bin/python3','-u','-m','nomad_slwv2.launch','--scene','SLW-v2','--index',str(j['index']),
              '--delay',str(j['delay']),'--method',j['method'],'--output',str(out)]
        result.append(dict(j,key=key,output=str(out),argv=argv,socket_bytes=validate_socket_path(socket_path_for_run(out))))
    assert len(result)==4
    return result

execute=bind(frozen.execute,verify=verify,HERE=HERE,jobs=jobs,__package__=__package__)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args()
    if a.status:
        s=frozen.status(RUN_ROOT);s['planned']=4
        f=RUN_ROOT/'reference_state.json';s['reference']=json.loads(f.read_text()) if f.exists() else {'status':'NOT_STARTED'}
        print(json.dumps(s));return
    verify()
    from . import reference
    if a.dry_run:print(json.dumps(dict(reference=reference.plan(),planned=4,simulations_started=0,jobs=jobs(RUN_ROOT))));return
    if shutil.disk_usage(ROOT).free<30_000_000_000:raise OSError('Disk reserve below30GB; no preparation/run started')
    try:reference.execute()
    except Exception:
        subprocess.run(['/usr/bin/python3','-m','nomad_slwv2.report','--publish'],cwd=ROOT,check=True);raise
    verify(require_assets=True)
    execute(RUN_ROOT,jobs(RUN_ROOT),report_argv=['/usr/bin/python3','-m','nomad_slwv2.report','--publish'])

if __name__=='__main__':main()
