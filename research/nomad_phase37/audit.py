"""Read-only input availability and frozen-trigger replay, before gate labels."""
import csv,hashlib,json,time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase24r.trigger import choose_ahead,component_sets,approach_progress
from nomad_phase20c.detour_known import radial_reference
from nomad_phase32o.evaluate import save,csvout

OUT=ROOT/'research/results/phase37/preparation'
HASHES={}

def register(p):
    p=Path(p).resolve()
    if str(p) not in HASHES:HASHES[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    return p

def read(p):return json.loads(register(p).read_text())
def lines(p):return [json.loads(x) for x in register(p).read_text().splitlines() if x] if Path(p).exists() else []

def metadata(p):
    with np.load(p) as z:
        m=json.loads(str(z['metadata']))
    return json.loads(m['_sdf_storage_v2']['original_metadata_json']) if '_sdf_storage_v2' in m else m

def history_map(p):
    # Trigger predicates do not query SDF values. Restore exactly the saved
    # observation/history arrays without any reconstruction or map inference.
    register(p)
    with np.load(p) as z:
        data={k:z[k].copy() for k in ('observed','occupied','new_component_ids','origin','first_occupied_tick')}
        data.update(h=float(z['h']),radius=float(z['radius']),
            component_births={int(k):int(v) for k,v in json.loads(str(z['component_births'])).items()},metadata=metadata(p))
    return SimpleNamespace(**data)


def run():
    runs=[dict(r,source_phase='32') for r in read(ROOT/'research/results/phase32/runs.json') if r['method']=='C0-NA+EC']
    runs+=[dict(r,source_phase='35') for r in read(ROOT/'research/results/phase35/runs.json') if r['method']=='OURS']
    assert len(runs)==30 and len({r['output'] for r in runs})==30
    audit=[];replay=[];events=[];missing=[];started=time.monotonic()
    for r in runs:
        root=Path(r['output']);cfg=read(root/'scenario.json');trace=register(root/'agent_trajectory.csv')
        with trace.open() as f:tr=list(csv.DictReader(f))
        poses=np.array([[float(x[k]) for k in ('x_m','y_m','yaw_rad')] for x in tr]);times=np.array([float(x['simulation_time_s']) for x in tr])
        np.testing.assert_allclose(times,np.arange(len(times))/72,atol=1e-9,rtol=0)
        controls=lines(root/'controller.jsonl');logs=lines(root/'detour.jsonl');updates=lines(root/'depth/updates.jsonl')
        byframe={int(u['frame_id']):u for u in updates};copies={}
        for file in sorted((root/'repair_jobs').glob('input_*.npz')):
            m=metadata(file);copies[(m['frame_id'],m['sim_s'])]=file
        def resolve(m):
            f=Path(m['file'])
            if f.exists():return f
            return copies.get((m['frame_id'],m['sim_s']))
        retained={f:resolve(u) for f,u in byframe.items()}
        cc=[c for c in controls if c['simulation_time_s']>=3]
        known=sum(retained.get(c.get('phase20d',{}).get('depth_frame')) is not None for c in cc)
        conditions=[e for e in logs if e['event']=='NEW_OBSTACLE_CONDITION']
        triggers=[e for e in logs if e['event']=='TRIGGER' and e.get('trigger')=='B']
        resolved_conditions=0;matched=0;last_file=None;field=None
        # This is the exact predicate at recorded eligible checks, not a
        # claim that every unlogged counterfactual check is reconstructible.
        for e in conditions:
            f=resolve(e['snapshot']);item=dict(phase=r['source_phase'],scene=r['scene'],index=r['index'],tick=e['tick'],
                simulation_s=e['simulation_time_s'],recorded_reason=e['reason'],map_available=f is not None)
            if f is None:
                replay.append(item);continue
            resolved_conditions+=1
            if f!=last_file:field=history_map(f);last_file=f
            tick=e['tick'];chosen,detail=choose_ahead(field,poses,tick,{})
            u=np.array(chosen['u_ref']) if chosen else radial_reference(poses,tick)[0]
            forward=float((poses[tick,:2]-poses[tick-216,:2])@u)
            drop=approach_progress(component_sets(field)[chosen['component_id']],poses[tick-216],poses[tick])[0] if chosen else None
            fire=bool(chosen and (forward<.2 or (drop is not None and drop<.1)))
            reason='NO_PROGRESS' if fire else 'NO_NEW_OBSTACLE_AHEAD' if chosen is None else 'PROGRESS'
            same_component=(chosen is None)==(e['component'] is None) and (chosen is None or chosen['component_id']==e['component']['component_id'])
            match=reason==e['reason'] and same_component and np.max(abs(u-np.asarray(e['u_ref'])))<1e-12 and abs(forward-e['progress_3s_m'])<1e-9
            matched+=match
            item.update(reason_recomputed=reason,fire_recomputed=fire,component_matches=same_component,matches=bool(match),snapshot_file=str(f))
            replay.append(item)
        context_counts=Counter();trigger_exact=0
        for e in triggers:
            gate=e['new_obstacle_condition'];f=resolve(gate['snapshot']);trigger_exact+=f is not None
            t=e['simulation_time_s'];window=[c for c in controls if t<=c['simulation_time_s']<t+5-1e-9]
            partial=t+5>times[-1]+1e-9
            interventions=sorted({c.get('applied_command_source','UNKNOWN') for c in window
                if c.get('phase20d',{}).get('detour_state') in ('WAIT','ACTIVE')
                or c.get('phase20',{}).get('repair_active') or c.get('phase20',{}).get('pending_job') is not None
                or c.get('phase17_recovery',{}).get('state')!='NORMAL'})
            status='TRUNCATED' if partial else 'INTERVENED' if interventions else 'NOMAD_ONLY_OBSERVED'
            context_counts[status]+=1
            events.append(dict(phase=r['source_phase'],scene=r['scene'],index=r['index'],job_id=e['job_id'],
                time_s=t,exact_check_snapshot_available=f is not None,future_5s_status=status,
                future_5s_intervention_sources=interventions,output=r['output']))
        for frame,u in byframe.items():
            if retained[frame] is None:missing.append(dict(phase=r['source_phase'],scene=r['scene'],index=r['index'],frame=frame,capture_s=u['sim_s'],file=u['file']))
        reference=cfg.get('reference_file');reference_path=Path(reference) if reference else None
        if reference_path and not reference_path.is_absolute():reference_path=ROOT/reference_path
        row=dict(phase=r['source_phase'],scene=r['scene'],index=r['index'],duration_s=r['duration_s'],
            published_maps=len(updates),available_map_frames=sum(f is not None for f in retained.values()),
            control_ticks_after_3s=len(cc),command_snapshot_available_ticks=known,
            logged_condition_checks=len(conditions),exact_condition_checks=resolved_conditions,
            reproduced_condition_checks=int(matched),logged_B_triggers=len(triggers),exact_B_trigger_maps=trigger_exact,
            B_future_full_nomad_only=context_counts['NOMAD_ONLY_OBSERVED'],B_future_intervened=context_counts['INTERVENED'],
            B_future_truncated=context_counts['TRUNCATED'],reference_file=str(reference_path) if reference_path else None,
            reference_available=bool(reference_path and reference_path.exists()),output=r['output'])
        audit.append(row);print('[audit]',len(audit),'/30',r['source_phase'],r['scene'],r['index'],flush=True)
    numeric=('published_maps','available_map_frames','control_ticks_after_3s','command_snapshot_available_ticks',
        'logged_condition_checks','exact_condition_checks','reproduced_condition_checks','logged_B_triggers','exact_B_trigger_maps',
        'B_future_full_nomad_only','B_future_intervened','B_future_truncated')
    totals={k:sum(r[k] for r in audit) for k in numeric}
    summary=dict(status='AWAITING_MEASUREMENT_DEFINITIONS',gate_evaluated=False,simulation_started=False,
        runs=30,static_runs=6,sudden_runs=24,totals=totals,phase36_found=False,primitive_tests_passed=6,elapsed_s=time.monotonic()-started,
        missing_reasons=['Phase36 TOPO-H definition absent from local and fetched remote history',
            'Default u_ref definition ambiguous: retain component-born direction vs rolling three-second direction',
            'Five-second original-NoMaD outcome cannot be read directly after intervention; progress threshold and episode matching need preregistration',
            'Compact archives omit some published snapshots; exact-check cohort vs missing-data policy must be stated'])
    OUT.mkdir(parents=True,exist_ok=True);save(OUT/'input_audit.json',summary);save(OUT/'input_hashes.json',HASHES)
    csvout(OUT/'availability.csv',audit);csvout(OUT/'original_trigger_replay.csv',replay);csvout(OUT/'original_B_events.csv',events);csvout(OUT/'missing_frames.csv',missing)
    save(OUT/'cohort.json',[{k:r[k] for k in ('source_phase','scene','index','method','output','duration_s')} for r in runs])
    print(json.dumps(summary))

if __name__=='__main__':run()
