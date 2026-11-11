"""Phase42-L clock/truth alignment; finalized run metrics only, no live log scan."""
import csv,json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase42l.analyze import read,lines,sha,nearest
HERE=Path(__file__).parent;OUT=ROOT/'research/results/hmm_replay';RUN_ROOT=ROOT.parent/'artifacts/isaac6/hmm_replay_01'
SOURCES=(
 ('Phase53-P','research/nomad_phase53p/protocol.json','phase53p_01'),
 ('NIGHT_E1','research/nomad_night20261111/protocol_E1.json','night_queue_20261111_01/E1'),
 ('Phase57-P','research/nomad_phase57p/protocol.json','phase57p_01'),
 ('Phase58-P','research/nomad_phase58p/protocol.json','phase58p_01'))

def discover():
    available=[];coverage=[]
    for phase,protocol,root in SOURCES:
        p=read(ROOT/protocol);root=ROOT.parent/'artifacts/isaac6'/root
        for job in p['main_order']:
            scene=job['scene'];method=job['method']
            if scene.endswith('_D150') or method=='NOMAD_RAW':continue
            key=f"{scene}_{job['index']:03d}_{method}";metric=root/'metrics'/(key+'.json');uid=phase+'/'+key
            record=dict(phase=phase,key=key,uid=uid,scene=scene.removesuffix('_D075'),seed=job['index'],method=method)
            if not metric.exists():coverage.append(dict(record,status='NOT_FINALIZED_OR_NOT_RUN'));continue
            row=read(metric);folder=Path(row['output'])
            required=[folder/x for x in ('scenario.json','summary.json','model/inference.jsonl','agent_trajectory.csv','received.jsonl')]
            missing=[str(f) for f in required if not f.exists()]
            if missing:coverage.append(dict(record,status='MISSING_SAVED_INPUT',missing=missing));continue
            cfg=read(required[0]);summary=read(required[1]);manifest=Path(cfg['topomap_manifest'])
            if summary['delivery_delay']['configured_additional_s']!=.75:coverage.append(dict(record,status='NOT_D075'));continue
            if not cfg.get('phase43p'):coverage.append(dict(record,status='NOT_HMM'));continue
            if not manifest.exists():coverage.append(dict(record,status='MISSING_TOPOMAP_MANIFEST'));continue
            files=[metric,*required,manifest]
            declaration=folder/'declared_arrival.json'
            if declaration.exists():files.append(declaration)
            hashes={str(f):sha(f) for f in files}
            available.append(dict(record,row=row,folder=str(folder),metric=str(metric),input_sha256=hashes))
            coverage.append(dict(record,status='AVAILABLE',technical_validation=row['technical_validation'],attempt=row.get('attempt'),output=str(folder)))
    return available,coverage

def load(item):
    folder=Path(item['folder']);row=item['row'];cfg=read(folder/'scenario.json');nodes=read(cfg['topomap_manifest'])['nodes']
    assert [n['node_id'] for n in nodes]==list(range(len(nodes)))
    xy=np.asarray([n['world_pose'] for n in nodes],float);intervals=np.linalg.norm(np.diff(xy[:,:2],axis=0),axis=1)
    positive=intervals[intervals>1e-12];assert len(positive);spacing=float(np.median(positive))
    with (folder/'agent_trajectory.csv').open() as stream:tr=list(csv.DictReader(stream))
    times=np.array([float(r['simulation_time_s']) for r in tr]);poses=np.array([[float(r[k]) for k in ('x_m','y_m','yaw_rad')] for r in tr]);assert len(times) and np.all(np.diff(times)>0)
    received={r['id']:r for r in lines(folder/'received.jsonl')}
    saved_truth={r['inference_id']:r for r in row.get('node_errors',[])}
    stop=read(folder/'declared_arrival.json') if (folder/'declared_arrival.json').exists() else None
    events=[];missing=[]
    for event in sorted(lines(folder/'model/inference.jsonl'),key=lambda x:x['id']):
        m=event.get('topomap');t=event.get('observation_sim_s');pose=event.get('observation_pose')
        if not m or 'hmm' not in m or t is None or pose is None:
            missing.append(dict(id=event.get('id'),reason='MISSING_HMM_OR_OBSERVATION'));continue
        if not times[0]-1e-9<=t<=times[-1]+1e-9:
            missing.append(dict(id=event['id'],reason='OBSERVATION_OUTSIDE_SAVED_TRAJECTORY'));continue
        tick=int(np.argmin(abs(times-t)));assert abs(times[tick]-t)<=1/72+1e-9
        np.testing.assert_allclose(poses[tick,:2],np.asarray(pose)[:2],atol=1e-6,rtol=0)
        truth=nearest(xy,pose);truth_source='Phase42-L nearest(saved observation pose)'
        if event['id'] in saved_truth:
            assert saved_truth[event['id']]['true_node']==truth
            truth=int(saved_truth[event['id']]['true_node']);truth_source='saved node_errors'
        ids=m.get('candidate_ids',[]);distances=m.get('distances',[])
        if not ids or len(ids)!=len(distances) or len(set(ids))!=len(ids) or not np.isfinite(distances).all() or min(ids)<0 or max(ids)>=len(nodes):
            missing.append(dict(id=event['id'],reason='INVALID_LOGGED_WINDOW'));continue
        total=event.get('hmm_odometry_total_m')
        if total is None:
            missing.append(dict(id=event['id'],reason='MISSING_LOGGED_ODOMETRY'));continue
        assert event['hmm_odometry_tick']==round(t*72);assert m['goal_node']==len(nodes)-1
        delivery=received.get(event['id']);declared=stop is not None and stop['id']==event['id']
        terminal=bool(delivery and delivery.get('terminal_unapplied')) and not declared
        events.append(dict(id=event['id'],time_s=float(t),odometry_xy=list(pose[:2]),odometry_total_m=float(total),true_node=truth,truth_source=truth_source,
            ids=m['candidate_ids'],distances=m['distances'],logged_map=int(m['closest_node']),logged_width=m['hmm']['transition_half_width'],
            goal_node=len(nodes)-1,truth_outside_window=truth not in m['candidate_ids'],terminal_drained=terminal,declared_stop_inference=declared,
            valid_delivery=bool(delivery and not terminal),observed_pose_source='logged observation pose = exact simulator odometry'))
    return events,len(nodes),spacing,stop,missing
