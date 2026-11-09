"""Oracle association after run termination; never imported by runtime."""
import json
from pathlib import Path
import numpy as np
from nomad_phase32.report import lines


def box_distance(points,box):
    points=np.asarray(points,float);delta=points-np.asarray(box['center_xy_m'],float)
    angle=np.deg2rad(float(box.get('yaw_deg',0.)));c,s=np.cos(angle),np.sin(angle)
    local=delta@np.array([[c,-s],[s,c]])
    outside=np.maximum(np.abs(local)-np.asarray(box['size_xyz_m'][:2])/2,0.)
    return float(np.linalg.norm(outside,axis=1).min())


def classify(points,boxes,t):
    active=[b for b in boxes if b['time_s']<=t+1e-12]
    if not active:return dict(classification='NON_BOX',minimum_box_distance_m=None,matched_box_ids=[],reason='NO_SPAWNED_SUDDEN_BOX')
    if points is None or not len(points):return dict(classification='UNMEASURED',minimum_box_distance_m=None,matched_box_ids=[],reason='MISSING_EXACT_TRIGGER_COMPONENT')
    distances=[(box_distance(points,b['box']),b['box']['id']) for b in active]
    matched=[identity for d,identity in distances if d<=.3+1e-12]
    return dict(classification='BOX' if matched else 'NON_BOX',minimum_box_distance_m=min(d for d,_ in distances),matched_box_ids=matched,reason='CELL_CENTER_TO_BOX_FOOTPRINT')


def component_points(root,event):
    evidence=event.get('trigger_component_evidence')
    if evidence is not None:return evidence['cell_centers_world'],'LIVE_EXACT_COMPONENT'
    # Historical45-P may not retain every published field. Use only exactly
    # matching frame IDs; never substitute an older/later snapshot.
    gate=event.get('new_obstacle_condition') or {};component=gate.get('component') or event.get('component') or {}
    source=gate.get('snapshot') or {};identity=component.get('component_id')
    if identity is None:return None,'NO_COMPONENT_ID'
    candidates=[]
    if source.get('file'):candidates.append(Path(source['file']))
    candidates.append(root/'repair_jobs'/f"input_{event['job_id']:04d}.npz")
    from nomad_phase33p.storage import load_snapshot
    from nomad_phase20f.history import HistorySnapshot
    from nomad_phase24r.trigger import component_sets
    for file in candidates:
        if not file.exists():continue
        field=load_snapshot(HistorySnapshot,file)
        if field.metadata.get('frame_id')!=source.get('frame_id'):continue
        if not hasattr(field,'new_component_ids'):continue
        points=component_sets(field).get(identity)
        if points is not None:return points.tolist(),'ARCHIVED_EXACT_FRAME'
    return None,'EXACT_TRIGGER_MAP_NOT_RETAINED'


def evaluate(root,row):
    root=Path(root);summary=json.loads((root/'summary.json').read_text());dynamic=summary.get('dynamic_obstacle') or {}
    records=dynamic.get('boxes')
    if records is None:records=[dynamic] if dynamic.get('spawn') else []
    boxes=[dict(time_s=b['spawn']['simulation_time_s'],box=b['spawn']['obstacle']) for b in records if b.get('spawn')]
    events=lines(root/'detour.jsonl');out=[]
    for event in events:
        if event['event']!='TRIGGER' or event.get('trigger')!='B':continue
        points,source=component_points(root,event)
        job=event['job_id'];applied=[e for e in events if e['event']=='APPLIED' and e['job_id']==job]
        results=[e for e in events if e['event']=='RESULT' and e['job_id']==job]
        ended=[e for e in events if e['event']=='END' and e['job_id']==job]
        out.append(dict(job_id=job,trigger_s=event['simulation_time_s'],component_id=(event.get('component') or {}).get('component_id'),
            component_source=source,component_cells=len(points) if points is not None else None,
            **classify(points,boxes,event['simulation_time_s']),r3_installed=bool(applied),
            r3_disposition=results[-1]['disposition'] if results else 'UNRESOLVED_AT_TERMINATION',
            r3_end_reason=ended[-1]['reason'] if ended else 'RUN_TERMINATED_ACTIVE' if applied else None,
            run_success=bool(row.get('success')),run_collision=bool(row.get('collision')),run_termination=row.get('termination')))
    return out
