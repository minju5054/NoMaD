"""Serialized renderer preparation and immutable generated-map seals."""
import json,os,signal,subprocess,shutil
from pathlib import Path
from nomad_phase26.storage import atomic_json
from nomad_phase26.launch import environment
from nomad_phase28.storage import cleanup
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,RUN_ROOT,SCENES,verify


def status():
    file=RUN_ROOT/'topomap_state.json'
    if not file.exists():return dict(status='NOT_STARTED')
    state=json.loads(file.read_text())
    if state.get('status')=='RUNNING' and state.get('pid'):
        try:live=Path(f"/proc/{state['pid']}/stat").read_text().split()[21]==state.get('process_token')
        except FileNotFoundError:live=False
        if not live:state.update(status='ABNORMAL_EXIT',pid=None)
    return state


def ensure():
    p=verify();seal=RUN_ROOT/'topomaps_sealed.json'
    if seal.exists():verify(require_maps=True);return
    RUN_ROOT.mkdir(parents=True,exist_ok=True);statefile=RUN_ROOT/'topomap_state.json'
    state=dict(status='RUNNING',pid=os.getpid(),process_token=Path('/proc/self/stat').read_text().split()[21],current=None)
    def interrupted(*_):raise KeyboardInterrupt('Topomap preparation interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    records={}
    try:
        for scene in SCENES:
            folder=RUN_ROOT/'topomap'/scene;complete=folder/'render_complete.json'
            state['current']=scene;atomic_json(statefile,state)
            if not complete.exists():
                assert not folder.exists(),'Incomplete render preserved; inspect before retry: '+str(folder)
                assert shutil.disk_usage(ROOT).free>=30_000_000_000,'Disk below30GB; no render started'
                folder.mkdir(parents=True)
                log=RUN_ROOT/f'topomap_{scene}.log'
                env=environment();env.update(PYTHONPYCACHEPREFIX=str(folder/'pycache'),XDG_CACHE_HOME=str(folder/'cache'))
                # Kit output mkdir must happen in the script, not through an
                # automatic pycache prefix inside that still-uncreated folder.
                env['PYTHONPYCACHEPREFIX']=str(RUN_ROOT/'topomap_pycache'/scene)
                with log.open('x') as stream:
                    cmd=['/home/gpuadmin/isaacsim/python.sh',str(HERE/'render_topomap.py'),'--scene',scene,'--output',str(folder),'--portable-root',str(folder/'portable')]
                    proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                    state['child_pid']=proc.pid;atomic_json(statefile,state)
                    try:code=proc.wait(timeout=900)
                    finally:
                        if proc.poll() is None:
                            os.killpg(proc.pid,signal.SIGTERM)
                            try:proc.wait(timeout=30)
                            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                        state.pop('child_pid',None)
                        if folder.exists():cleanup(folder,True,True)
                        cache=RUN_ROOT/'topomap_pycache'/scene
                        if cache.exists():shutil.rmtree(cache)
                    assert code==0 and complete.exists(),'Topomap renderer failed; no main run started'
            item=json.loads(complete.read_text());assert item['passed'] and item['protocol_sha256']==sha256_file(HERE/'protocol.json')
            records[scene]=dict(manifest_sha256=item['manifest_sha256'],render_complete_sha256=sha256_file(complete))
            print(f'[topomap] {scene} done ({item["node_count"]} original poses)',flush=True)
        atomic_json(seal,dict(protocol_sha256=sha256_file(HERE/'protocol.json'),scenes=records))
        verify(require_maps=True);state['status']='COMPLETE'
    except BaseException as exc:
        state.update(status='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',error=repr(exc));raise
    finally:
        state.update(pid=None,current=None);atomic_json(statefile,state)
