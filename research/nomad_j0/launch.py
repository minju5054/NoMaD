"""One frozen-method launch; --dry-run validates the actual command path only."""
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from nomad_isaac.socket_path import socket_path_for_run, validate_socket_path
from nomad_isaac.common import sha256_file
from nomad_phase26.launch import environment
from nomad_phase26.storage import atomic_json
from .config import ROOT, HERE, METHOD, SCENES, INDICES, DELAYS, verify

def build(args):
    p=verify()
    assert args.scene in SCENES and args.index in INDICES and args.delay in DELAYS and args.method==METHOD
    out=args.output.resolve();sock=socket_path_for_run(out)
    assert validate_socket_path(sock)<100
    topomap=p['scenes'][args.scene]['topomap']
    worker=[str(ROOT.parent/'.venv/bin/python'),'-u','-m','nomad_isaac.worker','--socket',str(sock),
            '--output',str(out/'model'),'--checkpoint',str(ROOT.parent/'artifacts/checkpoints/nomad.pth'),
            '--topomap',topomap]
    sim=['/home/gpuadmin/isaacsim/python.sh',str(HERE/'simulator.py'),'--level',args.scene,'--method',args.method,
         '--index',str(args.index),'--delay',str(args.delay),'--output',str(out),'--socket',str(sock),
         '--timeout','90','--topomap',topomap,'--portable-root',str(out/'portable')]
    return dict(output=str(out),socket=str(sock),socket_bytes=validate_socket_path(sock),worker=worker,simulator=sim,
                protocol_sha256=sha256_file(HERE/'protocol.json'),simulations_started=0)

def parser():
    p=argparse.ArgumentParser()
    p.add_argument('--scene',choices=SCENES,required=True)
    p.add_argument('--index',type=int,choices=INDICES,required=True)
    p.add_argument('--delay',type=float,choices=DELAYS,required=True)
    p.add_argument('--method',choices=[METHOD],default=METHOD)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--dry-run',action='store_true')
    return p

def main():
    a=parser().parse_args();plan=build(a)
    if a.dry_run:
        print(json.dumps(plan));return
    out=Path(plan['output']);sock=Path(plan['socket'])
    assert not sock.exists();out.mkdir(parents=True,exist_ok=False)
    p=verify();start=time.monotonic();worker=sim=None
    atomic_json(out/'provenance.json',dict(phase='J0',plan=plan,protocol=p,
        git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
    def interrupted(*_):raise KeyboardInterrupt('J0 launch interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    env=environment()
    env.update(PYTHONPYCACHEPREFIX=str(out/'pycache'),XDG_CACHE_HOME=str(out/'cache'),NOMAD_PHASE24_FULL_FRAMES='1')
    try:
        with (out/'worker.log').open('x') as wl,(out/'simulator.log').open('x') as sl:
            worker=subprocess.Popen(plan['worker'],cwd=ROOT,env=env,stdout=wl,stderr=subprocess.STDOUT,start_new_session=True)
            deadline=time.monotonic()+90
            while not sock.exists():
                if worker.poll() is not None:raise RuntimeError('NoMaD worker startup failed')
                if time.monotonic()>deadline:raise TimeoutError('NoMaD socket startup')
                time.sleep(.05)
            sim=subprocess.Popen(plan['simulator'],cwd=ROOT,env=env,stdout=sl,stderr=subprocess.STDOUT,start_new_session=True)
            code=sim.wait(timeout=600)
            if code or not (out/'summary.json').exists() or (out/'FAILED.json').exists():
                raise RuntimeError(f'Isaac stage incomplete exit={code}')
            assert worker.wait(timeout=15)==0
            atomic_json(out/'launch_complete.json',dict(exit_code=0,launcher_wall_s=time.monotonic()-start))
    except BaseException as e:
        atomic_json(out/'launch_failure.json',dict(error=repr(e)));raise
    finally:
        for proc in (sim,worker):
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        if sock.exists():sock.unlink()

if __name__=='__main__':main()
