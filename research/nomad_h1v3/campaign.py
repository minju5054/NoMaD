"""Four J0-equivalent runs, zero delay first; resume/locks/report unchanged."""
import argparse
import json
from pathlib import Path
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from nomad_j0 import campaign as frozen
from .config import ROOT,HERE,RUN_ROOT,verify,order,bind

def jobs(root):
    rows=[]
    for j in order():
        key=f"H1-v3_D{round(j['delay']*1000):03d}_{j['index']}_{j['method']}"
        out=Path(root)/'main'/key/'attempt1'
        argv=['/usr/bin/python3','-u','-m','nomad_h1v3.launch','--scene','H1-v3','--index',str(j['index']),
              '--delay',str(j['delay']),'--method',j['method'],'--output',str(out)]
        rows.append(dict(j,key=key,output=str(out),argv=argv,socket_bytes=validate_socket_path(socket_path_for_run(out))))
    assert len(rows)==4
    return rows

execute=bind(frozen.execute,verify=verify,HERE=HERE,jobs=jobs,__package__=__package__)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT)
    ap.add_argument('--dry-run',action='store_true');ap.add_argument('--status',action='store_true');a=ap.parse_args();root=a.run_root.resolve()
    if a.status:
        s=frozen.status(root)
        if s['status']=='NOT_STARTED':s['planned']=4
        print(json.dumps(s));return
    verify();plan=jobs(root)
    if a.dry_run:print(json.dumps(dict(planned=4,simulations_started=0,jobs=plan)));return
    execute(root,plan,report_argv=['/usr/bin/python3','-m','nomad_h1v3.report','--run-root',str(root),'--publish'])

if __name__=='__main__':main()
