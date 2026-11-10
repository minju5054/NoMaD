"""Read immutable logs; build projected increments and off-reference bounds."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase42l.analyze import read,lines,sha,nearest

ROOT=Path(__file__).resolve().parents[2]
PHASES=('phase43p','phase44p','phase45p','phase46p','phase47c')
NOISE_SEED=20261112


def load_run(row,phase,hashes):
    root=Path(row['output']);key=f"{phase}/{row['scene']}/{row['index']}/{row['method']}"
    files=[root/name for name in ('scenario.json','agent_trajectory.csv','model/inference.jsonl','received.jsonl')]
    for f in files:
        if not f.exists():raise FileNotFoundError(f)
        hashes[str(f)]=sha(f)
    config=read(files[0]);manifest=Path(config['topomap_manifest']);hashes[str(manifest)]=sha(manifest)
    nodes=read(manifest)['nodes'];assert [n['node_id'] for n in nodes]==list(range(len(nodes)))
    xy=np.asarray([n['world_pose'] for n in nodes],float);reference=XYPath(xy[:,:2])
    lengths=np.linalg.norm(np.diff(xy[:,:2],axis=0),axis=1);node_s=np.r_[0.,np.cumsum(lengths)]
    spacing=float(np.median(lengths[lengths>1e-12]))
    with files[1].open() as stream:tr=list(csv.DictReader(stream))
    ts=np.array([float(r['simulation_time_s']) for r in tr]);poses=np.array([[float(r[k]) for k in ('x_m','y_m','yaw_rad')] for r in tr])
    cumulative=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1))]
    projections=np.asarray([reference.project(q[:2]) for q in poses])
    received={r['id']:r for r in lines(files[3])};declaration=root/'declared_arrival.json'
    stop=read(declaration) if declaration.exists() else None
    if stop is not None:hashes[str(declaration)]=sha(declaration)
    seed_word=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)
    rng=np.random.default_rng(np.random.SeedSequence([NOISE_SEED,seed_word]))
    previous=None;records=[];off_episode=0;previous_off=False
    for e in sorted(lines(files[2]),key=lambda x:x['id']):
        m=e['topomap'];t=float(e['observation_sim_s']);tick=int(np.argmin(abs(ts-t)))
        assert abs(ts[tick]-t)<1e-9
        np.testing.assert_allclose(poses[tick],e['observation_pose'],atol=1e-9,rtol=0)
        ids=m['candidate_ids'];distances=m['distances'];assert len(ids)==len(distances)>0 and np.isfinite(distances).all()
        travel=0. if previous is None else float(cumulative[tick]-cumulative[previous['tick']])
        projected_delta=0. if previous is None else float(projections[tick,0]-projections[previous['tick'],0])
        off=False if previous is None else bool(np.max(projections[previous['tick']:tick+1,1])>=.5)
        if off and not previous_off:off_episode+=1
        edge=dict(travel_m=travel,projected_delta_m=projected_delta,off_path=off,
            noise_z=0. if previous is None else float(rng.standard_normal()),
            off_path_episode=off_episode if off else None,has_predecessor=previous is not None)
        previous_off=off
        delivery=received.get(e['id']);declared=stop is not None and stop['id']==e['id']
        valid_delivery=delivery is not None and (not delivery.get('terminal_unapplied') or declared)
        delivery_distance=None;delivery_s=None
        if valid_delivery:
            delivery_s=float(delivery['latched_sim_s']);index=int(np.argmin(abs(ts-delivery_s)))
            assert abs(ts[index]-delivery_s)<1e-9
            delivery_distance=float(np.linalg.norm(poses[index,:2]-np.asarray(config['goal_pose'])[:2]))
        logged_total=e.get('hmm_odometry_total_m')
        observed_total=float(cumulative[tick]) if logged_total is None else float(logged_total)
        record=dict(run=key,phase=phase,scene=row['scene'],seed=row['index'],method=row['method'],
            source_localization='HMM' if 'hmm' in m else 'ARGMIN',appearance='DIVERSE' if phase=='phase44p' else 'ORIGINAL',
            id=e['id'],time_s=t,tick=tick,candidate_ids=ids,distances=distances,node_s=node_s[ids].tolist(),
            true_node=nearest(xy,poses[tick]),true_projected_s_m=float(projections[tick,0]),cross_track_m=float(projections[tick,1]),
            goal_node=len(nodes)-1,goal_distance_observation_m=float(np.linalg.norm(poses[tick,:2]-np.asarray(config['goal_pose'])[:2])),
            delivery_s=delivery_s,delivery_distance_m=delivery_distance,virtual_stop_eligible=valid_delivery,
            logged_closest=int(m['closest_node']),logged_raw_argmin=m.get('raw_argmin_node'),
            odometry_total_m=observed_total,edge=edge,has_logged_hmm='hmm' in m)
        records.append(record);previous=record
    return records,node_s,spacing,dict(run=key,phase=phase,scene=row['scene'],seed=row['index'],method=row['method'],
        records=len(records),off_path_intervals=sum(r['edge']['off_path'] for r in records),off_path_episodes=off_episode,
        projected_intervals=sum(r['edge']['has_predecessor'] and not r['edge']['off_path'] for r in records),
        projection_abs_delta_exceeds_travel=sum(r['edge']['has_predecessor'] and not r['edge']['off_path'] and abs(r['edge']['projected_delta_m'])>r['edge']['travel_m']+1e-6 for r in records),
        median_node_spacing_m=spacing,noise_base_seed=NOISE_SEED,noise_run_word=seed_word)
