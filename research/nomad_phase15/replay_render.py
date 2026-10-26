"""Opt-in depth-only Isaac replay. No navigation, inference or physics stepping.

The host driver records immutable inputs before launching the existing isolated
Isaac process. The simulator imports render_isaac only on the depth replay gate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np
from nomad_isaac.common import ROOT, sha256_file, write_json

HERE = Path(__file__).parent
DEFAULT_ROOT = ROOT.parent/'artifacts/isaac6/phase15a_depth_01'


def jsonl(path):
    with Path(path).open() as f: return [json.loads(line) for line in f if line.strip()]


def git_sha():
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def collect_sources():
    import csv
    p = json.loads((HERE/'protocol.json').read_text())
    source = ROOT/p['source_runs']; old_hash_path = source.with_name('input_hashes.json')
    old_hashes = json.loads(old_hash_path.read_text())
    records = [r for r in json.loads(source.read_text()) if r['method'] in p['methods']]
    assert len(records)==p['expected_runs'] and len({r['key'] for r in records})==24
    assert all(sorted(r['index'] for r in records if r['method']==m)==p['indices'] for m in p['methods'])
    hashes = {str(source):sha256_file(source),str(old_hash_path):sha256_file(old_hash_path)}
    plans=[]
    for record in sorted(records,key=lambda r:(r['index'],r['method'])):
        run = Path(record['output']); old = old_hashes[record['key']]
        for name in ('scenario.json','observations.jsonl','events.jsonl','agent_trajectory.csv','provenance.json'):
            path=run/name; digest=sha256_file(path)
            if name in old: assert old[name]==digest, f'Changed source {path}'
            hashes[str(path)]=digest
        if record['method']=='FRESHEST+GRAPH-GF' and record['index'] in (39,45):
            path=run/'phase6_applications.jsonl';digest=sha256_file(path)
            assert old[path.name]==digest
            hashes[str(path)]=digest
        config=json.loads((run/'scenario.json').read_text())
        assert 'dynamic_obstacle' not in config and config['agent_radius_m']==.09
        assert config['camera']['horizontal_fov_deg']==90
        assert config['camera']['height_m']==.5
        provenance=json.loads((run/'provenance.json').read_text())
        assert provenance['git_sha']==record['execution_git_sha']
        with (run/'agent_trajectory.csv').open() as f: trace={int(r['tick']):r for r in csv.DictReader(f)}
        observations=jsonl(run/'observations.jsonl')
        frames=[]
        for obs in observations:
            if 'observation_id' not in obs: continue
            tick=round(obs['observation_sim_s']*72); row=trace[tick]
            pose=[float(row[k]) for k in ('x_m','y_m','yaw_rad')]
            assert np.max(np.abs(np.array(pose)-obs['observation_pose']))<1e-10
            assert abs(float(row['simulation_time_s'])-obs['observation_sim_s'])<1e-9
            assert obs['capture_end_monotonic_ns']>=obs['observation_monotonic_ns']
            frames.append(dict(observation_id=obs['observation_id'],tick=tick,pose=pose,
                sim_s=obs['observation_sim_s'],capture_end_monotonic_ns=obs['capture_end_monotonic_ns'],
                observation_monotonic_ns=obs['observation_monotonic_ns'],source_rgb_sha256=obs['frame_sha256']))
        assert frames and all(b['capture_end_monotonic_ns']>=a['capture_end_monotonic_ns'] for a,b in zip(frames,frames[1:]))
        events=jsonl(run/'events.jsonl')
        for event in events:
            derived=run/f"model/derived/{event['id']:04d}.npz"
            hashes[str(derived)]=sha256_file(derived)
            assert 'application_monotonic_ns' in event and not event['terminal_unapplied']
        plans.append(dict(key=record['key'],method=record['method'],index=record['index'],output=str(run),
            scenario=config,frames=frames,original_execution_sha=provenance['git_sha']))
    return dict(runs=plans,input_hashes=hashes,protocol=p,protocol_sha256=sha256_file(HERE/'protocol.json'),
                execution_git_sha=git_sha(),source_manifest=str(source))


def render_isaac(args, build_scene, app, rep, usd, Gf, UsdGeom):
    """Called inside simulator, after SimulationApp is initialized, never main()."""
    # No scipy import in the Isaac environment.
    plan=json.loads(args.depth_replay_manifest.read_text()); out=args.output.resolve()
    rep.orchestrator.set_capture_on_play(False)
    stage=usd.get_context().get_stage()
    if stage is None: usd.get_context().new_stage()
    scene=build_scene(plan['runs'][0]['scenario'])
    stage,agent,translate,rotate,camera,annotator,product=scene
    import omni.timeline
    timeline=omni.timeline.get_timeline_interface(); timeline.stop()
    config=plan['runs'][0]['scenario']; cam=config['camera']
    k=[320*cam['focal_length_mm']/cam['horizontal_aperture_mm'],
       240*cam['focal_length_mm']/cam['vertical_aperture_mm'],160.,120.]
    camera_data=dict(intrinsics=k,resolution=[320,240],annotator='distance_to_image_plane',
                     usd_camera_path=str(camera.GetPath()),source_camera=cam)
    write_json(out/'camera.json',camera_data)
    for _ in range(10): app.update()
    results=[]
    initialized=False
    for run in plan['runs']:
        # All 24 runs used the same static S0 geometry/camera; per-run seeds and
        # controller settings are irrelevant to this render-only branch.
        for key in ('obstacles','corridor','camera'):
            assert run['scenario'][key]==config[key],f'Scene mismatch: {key}'
        dest=out/run['key']; dest.mkdir()
        frames=[]; metadata=[]; transforms=[]
        for item in run['frames']:
            pose=item['pose']; translate.Set(Gf.Vec3d(pose[0],pose[1],0.))
            rotate.Set(float(np.degrees(pose[2])))
            timeline.set_current_time(item['sim_s'])
            begin=time.perf_counter()
            # Match existing capture startup handling. Only renderer readiness
            # retries at the identical first pose, never another navigation.
            for _ in range(1 if initialized else 20):
                rep.orchestrator.step(rt_subframes=4,delta_time=0.,pause_timeline=True)
                depth=np.asarray(annotator.get_data())
                if depth.shape==(240,320) and np.any(np.isfinite(depth)&(depth>0)):break
            if depth.shape!=(240,320) or not np.any(np.isfinite(depth)&(depth>0)):
                raise RuntimeError(f'Invalid depth {run["key"]} observation {item["observation_id"]}: {depth.shape}')
            initialized=True
            matrix=UsdGeom.Xformable(camera).ComputeLocalToWorldTransform(0)
            # Gf uses row vectors; save explicit column-vector transform.
            transform=np.eye(4)
            transform[:3,3]=np.asarray(matrix.ExtractTranslation())
            for j in range(3):
                axis=[0.,0.,0.];axis[j]=1.
                transform[:3,j]=np.asarray(matrix.TransformDir(Gf.Vec3d(*axis)))
            yaw=pose[2]; c,s=np.cos(yaw),np.sin(yaw)
            expected=np.array([[s,0,-c,pose[0]],[-c,0,-s,pose[1]],[0,1,0,.5],[0,0,0,1.]])
            # Agent translation op is float32 in existing scene; preserve it
            # and record the actual USD matrix, never assume exact rendering pose.
            assert np.max(np.abs(transform-expected))<1e-6
            stored=depth.astype(np.float16)
            frames.append(stored);transforms.append(transform)
            metadata.append(dict(**item,render_wall_ms=(time.perf_counter()-begin)*1000,
                depth_sha256=hashlib.sha256(stored.tobytes()).hexdigest(),
                usd_pose_error_max=float(np.max(np.abs(transform-expected)))))
        archive=dest/'depth.npz'
        np.savez_compressed(archive,depth=np.stack(frames),camera_to_world=np.stack(transforms))
        write_json(dest/'frames.json',metadata)
        result=dict(key=run['key'],frames=len(frames),archive=str(archive),sha256=sha256_file(archive),
                    metadata_sha256=sha256_file(dest/'frames.json'))
        results.append(result)
        with (out/'progress.jsonl').open('a') as f: f.write(json.dumps(result)+'\n')
        print(f"DEPTH_REPLAY {len(results)}/24 {run['key']} frames={len(frames)}",flush=True)
    write_json(out/'render_complete.json',dict(runs=results,execution_git_sha=plan['execution_git_sha'],
        frames=sum(r['frames'] for r in results),physics_steps=0,inference_requests=0,
        camera_sha256=sha256_file(out/'camera.json'),plan_sha256=sha256_file(args.depth_replay_manifest)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root',type=Path,default=DEFAULT_ROOT)
    parser.add_argument('--depth-camera',action='store_true',required=True)
    parser.add_argument('--isaac-root',type=Path,default=Path('/home/gpuadmin/isaacsim'))
    args=parser.parse_args(); out=args.run_root.resolve()
    if out.exists(): raise FileExistsError(f'Refusing overwrite/resume: {out}')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():
        raise RuntimeError('Commit tracked code/protocol changes before rendering')
    plan=collect_sources()
    plan['producer_hashes']={str(path.relative_to(ROOT)):sha256_file(path) for path in
        [*sorted(HERE.glob('*.py')),HERE/'protocol.json',ROOT/'research/nomad_isaac/simulator.py',
         ROOT/'research/nomad_isaac/clearance.py',ROOT/'research/nomad_phase0/graph_v4.py']}
    out.mkdir(parents=True); write_json(out/'plan.json',plan)
    env=os.environ.copy()
    for key in ('PYTHONPATH','VIRTUAL_ENV','PYTHONHOME','LD_LIBRARY_PATH','LD_PRELOAD'): env.pop(key,None)
    env['PYTHONPATH']=str(ROOT/'research')
    for key,name in [('XDG_CACHE_HOME','cache'),('XDG_CONFIG_HOME','config'),('CUDA_CACHE_PATH','cuda_cache'),
                     ('__GL_SHADER_DISK_CACHE_PATH','gl_cache'),('PYTHONPYCACHEPREFIX','isaac_pycache')]:
        env[key]=str(out/name); (out/name).mkdir()
    command=[str(args.isaac_root/'python.sh'),str(ROOT/'research/nomad_isaac/simulator.py'),
        '--output',str(out),'--portable-root',str(out/'portable'),'--depth-camera',
        '--depth-replay-manifest',str(out/'plan.json')]
    write_json(out/'launch.json',dict(command=command,execution_git_sha=git_sha(),isaac_version=(args.isaac_root/'VERSION').read_text().strip()))
    with (out/'isaac_stdout.log').open('x') as log:
        code=subprocess.call(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    if code or not (out/'render_complete.json').exists():
        raise RuntimeError(f'Depth replay failed ({code}); preserved {out}/isaac_stdout.log; no automatic retry')
    print(f'DEPTH_REPLAY_COMPLETE {out}',flush=True)


if __name__=='__main__': main()
