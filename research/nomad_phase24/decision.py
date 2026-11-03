"""Re-evaluate the unchanged20F observable trigger on recorded histories."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from nomad_phase0.chunk_report import trace
from nomad_phase15b.depth import Snapshot
from nomad_phase20f.history import HistorySnapshot
from nomad_phase20f.trigger import NewObstacleNoProgress,choose_ahead
from nomad_phase20c.detour_known import radial_reference


def available_history(case):
    run=Path(case['run']);needed=[run/'agent_trajectory.csv',Path(case['snapshot_file'])]
    missing=[str(f) for f in needed if not f.exists()]
    if missing:return False,missing
    with np.load(case['snapshot_file']) as z:complete='first_free_tick' in z.files
    if complete:return True,[]
    for f in (run/'scenario.json',run/'depth/updates.jsonl'):
        if not f.exists():missing.append(str(f))
    if missing:return False,missing
    frame=int(Snapshot.load(case['snapshot_file']).metadata['frame_id'])
    for line in (run/'depth/updates.jsonl').read_text().splitlines():
        update=json.loads(line)
        if update['frame_id']<=frame:
            file=run/f"depth/depth_{update['frame_id']:04d}.npz"
            if not file.exists():missing.append(str(file))
    return not missing,missing


def pose_history(case):
    file=Path(case['run'])/'agent_trajectory.csv'
    if file.exists():
        _,poses=trace(Path(case['run']));return poses[:case['tick']+1].copy()
    # Public robot initial condition, not obstacle/goal oracle input.
    start=json.loads((Path(case['run'])/'scenario.json').read_text())['start_pose']
    return np.asarray([start,case['B']],float)


def resolve_direction(case,history_file,poses=None,tick=None):
    poses=pose_history(case) if poses is None else np.asarray(poses)
    tick=len(poses)-1 if tick is None else tick
    if history_file is not None:
        field=HistorySnapshot.load(history_file);chosen,detail=choose_ahead(field,poses,tick,{})
        if chosen is not None:return chosen['u_ref'],dict(source='20F_COMPONENT_PREAPPEARANCE',component=chosen,**detail)
        component_status='NO_COMPONENT_AHEAD'
    else:detail={};component_status='HISTORY_UNAVAILABLE'
    u,info=radial_reference(poses,tick)
    return u.tolist(),dict(source='20F_A_FALLBACK',component_status=component_status,fallback=info,**detail)


def recompute_trigger(poses,tick,field):
    """Fixed-snapshot predicate: no invented preceding G busy/cooldown state."""
    events=[];owner=SimpleNamespace(depth_maps=SimpleNamespace(snapshot=lambda:field),suppress_trigger_tick=-1,drecord=lambda event,**kw:events.append(dict(event=event,**kw)))
    detector=NewObstacleNoProgress(owner);old_u,_=radial_reference(poses,tick)
    fired,progress,reason=detector.check(poses,tick,old_u,blocked=False)
    return bool(fired),dict(reason=reason,progress_3s_m=progress,gate=detector.last_gate,events=events,
        transient_guards=dict(busy=False,cooldown_until=None,blocked=False,suppress_trigger_tick=-1),
        guard_note='Snapshot-only counterfactual: no prior G execution exists, so only the requested observable trigger predicate is reconstructed; no source-method busy state is imputed as G state.')


def choose_mode(case,history_file,missing):
    if history_file is not None:
        poses=pose_history(case);assert len(poses)>case['tick'];field=HistorySnapshot.load(history_file)
        fired,info=recompute_trigger(poses,case['tick'],field);mode='DETOUR' if fired else 'NORMAL';source='MODE_RECOMPUTED'
    elif Path(case['c0_record']).exists():
        record=json.loads(Path(case['c0_record']).read_text());plan=record['methods']['C0']['plan'];attempted=any(s['kind']=='R3' for s in plan.get('stages',[]))
        mode='DETOUR' if attempted else 'NORMAL';source='MODE_FROM_C0';info=dict(missing_history=missing,c0_disposition=plan['disposition'],c0_attempted_R3=attempted)
    else:mode='NORMAL';source='MODE_FALLBACK';info=dict(missing_history=missing,reason='NO_HISTORY_OR_C0_DECISION')
    u,reference=resolve_direction(case,history_file)
    return dict(mode=mode,mode_source=source,trigger=info,u_ref=u,direction=reference,history_file=history_file)


def advanced_case(case,prediction):
    """At the first failed output, the executor starts its registered braking."""
    c=dict(case,B=prediction['B_pred'],previous_vw=prediction['previous_vw'],tick=case['tick']+len(prediction['speeds']),executing_path=None,executing_graph=None)
    poses=np.vstack([pose_history(case),np.asarray(prediction['poses'])[1:]])
    return c,poses
