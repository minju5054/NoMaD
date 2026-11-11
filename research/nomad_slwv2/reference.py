"""Deferred original SLW reference procedure, executed only by user campaign."""
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from nomad_phase26.launch import environment
from .config import ROOT,HERE,RUN_ROOT,REFERENCE_ROOT,TOPOMAP,verify,build_scene,verify_assets

def define():
    # This numerical reference rollout is deliberately NOT called by prepare.
    from nomad_phase16.geometry import reference_path,reference_rollout
    verify();folder=RUN_ROOT/'reference_definition';folder.mkdir(parents=True,exist_ok=False)
    c=build_scene();xy,geometry=reference_path(c);_,_,result=reference_rollout(c,xy)
    assert result['goal'],result
    file=folder/'reference.json'
    atomic_json(file,dict(world_xy=xy.tolist(),geometry=geometry,offline_pp=result,
                         definition_protocol_sha256=sha256_file(HERE/'protocol.json')))
    c.update(reference_file=str(file),reference_sha256=sha256_file(file),reference_length_m=geometry['reference_length_m'],
             reference_preparation=geometry,reference_offline_pp_check=result)
    atomic_json(folder/'scenario.json',c)

def plan():
    return dict(definition_argv=['/usr/bin/python3','-u','-m','nomad_slwv2.reference','--define'],
        render_argv=['/home/gpuadmin/isaacsim/python.sh',str(HERE/'reference_simulator.py'),'--scene','SLW-v2',
            '--mode','reference','--output',str(REFERENCE_ROOT),'--timeout','90','--portable-root',str(REFERENCE_ROOT/'portable')],
        definition=str(RUN_ROOT/'reference_definition/reference.json'),topomap=str(TOPOMAP),NoMaD_inference=False,
        reference_procedure='frozen Phase16 reference_path + reference_rollout + Phase17 reference renderer',
        spacing_sim_s=2.,navigation_runs=0)

def resolve():
    from nomad_isaac.topomap import load_map
    images,_=load_map(TOPOMAP);m=json.loads(TOPOMAP.read_text());assert m['spacing_sim_s']==2. and len(images)==m['node_count']
    files=[RUN_ROOT/'reference_definition/reference.json',RUN_ROOT/'reference_definition/scenario.json',TOPOMAP,REFERENCE_ROOT/'reference_status.json']
    files.extend(TOPOMAP.parent/n['rgb_file'] for n in m['nodes'])
    result=dict(protocol_sha256=sha256_file(HERE/'protocol.json'),topomap_manifest=str(TOPOMAP),spacing_sim_s=2.,
        node_count=m['node_count'],sha256={str(f):sha256_file(f) for f in files},reference_result=m['reference_result'])
    assert result['reference_result']['goal']
    atomic_json(RUN_ROOT/'resolved_assets.json',result);return result

def execute():
    from nomad_phase0.s0_batch import exclusive_batch
    from nomad_j0.campaign import cleanup
    verify();RUN_ROOT.mkdir(parents=True,exist_ok=True)
    if (RUN_ROOT/'resolved_assets.json').exists():return verify_assets()
    # Same global exclusion as J0: no reference renderer overlaps navigation.
    with exclusive_batch():
        if (RUN_ROOT/'resolved_assets.json').exists():return verify_assets()
        log=RUN_ROOT/'reference_launcher.log';state=dict(status='RUNNING',stage='DEFINITION',protocol_sha256=sha256_file(HERE/'protocol.json'))
        atomic_json(RUN_ROOT/'reference_state.json',state);proc=None
        def interrupted(*_):raise KeyboardInterrupt('Reference interrupted; partial files preserved')
        previous=signal.signal(signal.SIGTERM,interrupted)
        env=environment()
        try:
            with log.open('a') as stream:
                definition=RUN_ROOT/'reference_definition/reference.json'
                if not definition.exists():
                    assert not definition.parent.exists(),'Incomplete reference definition preserved; no automatic retry'
                    proc=subprocess.Popen(plan()['definition_argv'],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                    assert proc.wait()==0,'Reference definition failed';proc=None
                definition_data=json.loads(definition.read_text());assert definition_data['definition_protocol_sha256']==state['protocol_sha256']
                if not (REFERENCE_ROOT/'launch_complete.json').exists():
                    assert not REFERENCE_ROOT.exists(),'Incomplete reference rendering preserved; no automatic retry'
                    REFERENCE_ROOT.mkdir();state['stage']='REFERENCE_RENDER';atomic_json(RUN_ROOT/'reference_state.json',state)
                    atomic_json(REFERENCE_ROOT/'provenance.json',dict(git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                        protocol_sha256=state['protocol_sha256'],mode='reference',navigation_excluded=True))
                    env.update(PYTHONPYCACHEPREFIX=str(REFERENCE_ROOT/'pycache'),XDG_CACHE_HOME=str(REFERENCE_ROOT/'cache'))
                    started=time.monotonic();proc=subprocess.Popen(plan()['render_argv'],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                    assert proc.wait(timeout=900)==0 and TOPOMAP.exists(),'Reference renderer failed';proc=None
                    assert not (REFERENCE_ROOT/'FAILED.json').exists()
                    atomic_json(REFERENCE_ROOT/'launch_complete.json',dict(exit_code=0,launcher_wall_s=time.monotonic()-started,mode='reference'))
            result=resolve();cleanup(REFERENCE_ROOT);state.update(status='COMPLETE',stage='DONE',node_count=result['node_count']);return result
        except BaseException as e:
            state.update(status='FAILED',error=repr(e))
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=30)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            raise
        finally:
            atomic_json(RUN_ROOT/'reference_state.json',state);signal.signal(signal.SIGTERM,previous)

def main():
    p=argparse.ArgumentParser();p.add_argument('--define',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    if a.dry_run:print(json.dumps(plan()));return
    if a.define:define();return
    raise ValueError('Reference execution is only invoked as the campaign preparation stage')

if __name__=='__main__':main()
