"""Standard-library process launcher; frozen NoMaD and short socket selection."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from .online_config import METHODS,SCENES,verify

def environment():
    env=os.environ.copy()
    for key in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(key,None)
    env.update(PYTHONPATH=':'.join(str(ROOT/p) for p in ('research','train','external/diffusion_policy')),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    return env

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scene',choices=SCENES,required=True);ap.add_argument('--method',choices=METHODS,required=True);ap.add_argument('--index',type=int,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--smoke',action='store_true');a=ap.parse_args();p=verify();out=a.output.resolve()
    assert (a.smoke and a.scene=='L2' and a.index==95) or (not a.smoke and p['status']=='FROZEN' and a.index in p['indices'])
    if a.method=='G':assert p['application_policy'] is not None,'Resolve the0.5s/9Hz application definition'
    sock=socket_path_for_run(out);assert validate_socket_path(sock)<100 and not sock.exists();out.mkdir(parents=True,exist_ok=False)
    write_json(out/'provenance.json',dict(phase='24-online',smoke_excluded=a.smoke,git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),protocol=p,method=a.method,scene=a.scene,index=a.index,seed_offset=a.index*10000,
        socket_path=str(sock),socket_path_bytes=validate_socket_path(sock),source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in Path(__file__).parent.glob('*.py')},checkpoint_sha256=p['checkpoint_sha256']))
    worker=sim=None;launch_start=time.monotonic()
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
    env=environment()
    try:
        with (out/'worker.log').open('x') as wl,(out/'simulator.log').open('x') as sl:
            worker=subprocess.Popen([str(ROOT.parent/'.venv/bin/python'),'-u','-m','nomad_isaac.worker','--socket',str(sock),'--output',str(out/'model'),'--checkpoint',str(ROOT.parent/'artifacts/checkpoints/nomad.pth'),'--topomap',p['scenes'][a.scene]['topomap']],cwd=ROOT,env=env,stdout=wl,stderr=subprocess.STDOUT,start_new_session=True)
            deadline=time.monotonic()+90
            while not sock.exists():
                if worker.poll() is not None:raise RuntimeError('NoMaD worker startup failed')
                if time.monotonic()>deadline:raise TimeoutError('NoMaD socket startup')
                time.sleep(.05)
            env.update(PYTHONPYCACHEPREFIX=str(out/'pycache'),XDG_CACHE_HOME=str(out/'cache'))
            cmd=['/home/gpuadmin/isaacsim/python.sh',str(ROOT/'research/nomad_phase24/online_simulator.py'),'--level',a.scene,'--output',str(out),'--method',a.method,'--index',str(a.index),'--delay','.75','--socket',str(sock),'--timeout','90','--topomap',p['scenes'][a.scene]['topomap'],'--portable-root',str(out/'portable')]
            sim=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=sl,stderr=subprocess.STDOUT,start_new_session=True);code=sim.wait(timeout=600)
            if code or not (out/'summary.json').exists() or (out/'FAILED.json').exists():raise RuntimeError(f'Isaac stage incomplete exit={code}')
            assert worker.wait(timeout=15)==0;write_json(out/'launch_complete.json',dict(exit_code=0,smoke_excluded=a.smoke,launcher_wall_s=time.monotonic()-launch_start))
    except BaseException as exc:write_json(out/'launch_failure.json',dict(error=repr(exc)));raise
    finally:
        for proc in (sim,worker):
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        if sock.exists():sock.unlink()
if __name__=='__main__':main()
