"""Actual J1 launch path; same worker/bootstrap/short sockets as J0."""
import argparse
import sys
from pathlib import Path
from nomad_j0 import launch as old
from nomad_isaac.common import sha256_file
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from .config import ROOT,HERE,METHODS,SCENES,INDICES,verify,bind

def parser():
    p=argparse.ArgumentParser();p.add_argument('--scene',choices=SCENES,required=True);p.add_argument('--method',choices=METHODS,required=True)
    p.add_argument('--index',type=int,required=True);p.add_argument('--delay',type=float,choices=[.75],default=.75)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--smoke',action='store_true');p.add_argument('--dry-run',action='store_true');return p

def build(a):
    p=verify();assert (a.smoke and a.index==95 and a.scene=='LC' and a.method=='OURS') or (not a.smoke and a.index in INDICES)
    out=a.output.resolve();sock=socket_path_for_run(out);validate_socket_path(sock);top=p['scenes'][a.scene]['topomap']
    worker=['/home/gpuadmin/Workspace/NoMaD/.venv/bin/python','-u','-m','nomad_phase8.worker' if a.method=='RTC-hard' else 'nomad_isaac.worker',
            '--socket',str(sock),'--output',str(out/'model'),'--checkpoint',str(ROOT.parent/'artifacts/checkpoints/nomad.pth'),'--topomap',top]
    if a.method=='RTC-hard':worker+=['--rtc-mode','hard']
    sim=['/home/gpuadmin/isaacsim/python.sh',str(HERE/'simulator.py'),'--level',a.scene,'--method',a.method,'--index',str(a.index),
         '--delay','.75','--output',str(out),'--socket',str(sock),'--timeout','30' if a.smoke else '90',
         '--topomap',top,'--portable-root',str(out/'portable')]
    return dict(output=str(out),socket=str(sock),socket_bytes=validate_socket_path(sock),worker=worker,simulator=sim,
                protocol_sha256=sha256_file(HERE/'protocol.json'),simulations_started=0,smoke_excluded=a.smoke)

def write(path,value):
    if path.name=='provenance.json':value=dict(value,phase='J1',smoke_excluded='--smoke' in sys.argv)
    old.atomic_json(path,value)

main=bind(old.main,parser=parser,build=build,verify=verify,atomic_json=write)
if __name__=='__main__':main()
