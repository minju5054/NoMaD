"""Phase20 process launcher, with no modification to the existing launcher/worker."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
from .config import verify_sources,METHODS

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scene',required=True,choices=['SO']);ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--mode',choices=['navigation'],required=True);ap.add_argument('--topomap',type=Path);ap.add_argument('--method',choices=METHODS)
    ap.add_argument('--index',type=int);ap.add_argument('--delay',type=float,choices=[0.,.75]);ap.add_argument('--timeout',type=float,default=90.)
    ap.add_argument('--smoke',action='store_true');ap.add_argument('--start-pose',type=float,nargs=3);a=ap.parse_args();p=verify_sources();out=a.output.resolve()
    assert p['status']=='FROZEN','Awaiting explicit user choices and frozen protocol'
    if a.mode=='navigation':
        assert a.topomap and a.method and a.index is not None and a.delay is not None
        assert (a.smoke and a.timeout==30) or (not a.smoke and a.timeout==90)
        assert sha256_file(a.topomap)==p['SO']['topomap_sha256']
        assert (a.smoke and a.index==901 and a.method=='M2_REPAIR' and a.delay==0.) or (not a.smoke and 74<=a.index<=79 and a.delay==.75)
    assert a.start_pose is None
    socket_path=socket_path_for_run(out);assert not socket_path.exists();out.mkdir(parents=True,exist_ok=False)
    scenario=ROOT/p['SO']['source_scenario']
    write_json(out/'provenance.json',dict(phase=20,mode=a.mode,smoke_excluded=a.smoke,git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        smoke_start_pose=a.start_pose,source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in Path(__file__).parent.glob('*') if f.is_file()},scenario_sha256=sha256_file(scenario),protocol=p,
        socket_path=str(socket_path),socket_path_bytes=validate_socket_path(socket_path),checkpoint_sha256=p['checkpoint_sha256']))
    worker=sim=None
    def interrupted(*_):raise KeyboardInterrupt('Campaign interruption')
    signal.signal(signal.SIGTERM,interrupted)
    env=os.environ.copy()
    for k in ('LD_LIBRARY_PATH','LD_PRELOAD','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
    env.update(PYTHONPATH=':'.join(str(ROOT/x) for x in ('research','train','external/diffusion_policy')),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    try:
        with (out/'worker.log').open('x') as wl,(out/'simulator.log').open('x') as sl:
            if a.mode=='navigation':
                worker_module='nomad_isaac.worker'
                worker_extra=[]
                worker=subprocess.Popen([str(ROOT.parent/'.venv/bin/python'),'-u','-m',worker_module,'--socket',str(socket_path),'--output',str(out/'model'),'--checkpoint',str(ROOT.parent/'artifacts/checkpoints/nomad.pth'),'--topomap',str(a.topomap.resolve()),*worker_extra],cwd=ROOT,env=env,stdout=wl,stderr=subprocess.STDOUT,start_new_session=True)
                deadline=time.monotonic()+90
                while not socket_path.exists():
                    if worker.poll() is not None:raise RuntimeError('NoMaD worker startup failed')
                    if time.monotonic()>deadline:raise TimeoutError('NoMaD socket startup')
                    time.sleep(.05)
            cmd=['/home/gpuadmin/isaacsim/python.sh',str(ROOT/'research/nomad_phase20/simulator.py'),'--output',str(out),'--timeout',str(a.timeout),'--portable-root',str(out/'portable')]
            if a.mode=='navigation':cmd+=['--topomap',str(a.topomap.resolve()),'--method',a.method,'--index',str(a.index),'--delay',str(a.delay),'--socket',str(socket_path)]
            if a.start_pose is not None:cmd+=['--start-pose',*[str(v) for v in a.start_pose]]
            env.update(PYTHONPYCACHEPREFIX=str(out/'pycache'),XDG_CACHE_HOME=str(out/'cache'))
            sim=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=sl,stderr=subprocess.STDOUT,start_new_session=True)
            code=sim.wait(timeout=600)
            expected=out/('summary.json' if a.mode=='navigation' else 'topomap/manifest.json' if a.mode=='reference' else 'inspection.json')
            if code or not expected.exists() or (out/'FAILED.json').exists():raise RuntimeError(f'Isaac stage incomplete exit={code}')
            if worker is not None:assert worker.wait(timeout=15)==0
            write_json(out/'launch_complete.json',dict(exit_code=0,mode=a.mode))
    except BaseException as e:
        write_json(out/'launch_failure.json',dict(error=repr(e)));raise
    finally:
        for proc in (sim,worker):
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        if worker is not None and socket_path.exists():socket_path.unlink()
if __name__=='__main__':main()
