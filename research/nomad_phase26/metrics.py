"""Technical audit independent of navigation outcomes; multi-box evaluation."""
import json
from pathlib import Path
import numpy as np
from nomad_phase24r.online_metrics import base_audit,rows

def audit(run):
    run=Path(run);r=base_audit(run);s=json.loads((run/'summary.json').read_text());cfg=s['scenario']
    assert cfg['phase26'] and cfg['goal_tolerance_m']==.3
    geometry=json.loads((run/'geometry_check.json').read_text());assert geometry['status']=='PASS'
    assert (run/'phase26_complete.json').exists()
    assert not (run/'oracle_information.json').exists()
    assert cfg['depth_camera']==(cfg['phase26_method']!='B0_NOMAD_RAW')
    if cfg['depth_camera']:
        updates=rows(run/'depth/updates.jsonl');assert updates
    else:assert not (run/'depth').exists()
    for q in rows(run/'repair_pool_jobs.jsonl'):assert not q.get('error'),q.get('error')
    detours=rows(run/'detour.jsonl');triggers={e['job_id']:e for e in detours if e['event']=='TRIGGER'}
    applies=[e for e in detours if e['event']=='APPLIED'];results=[e for e in detours if e['event']=='RESULT']
    latency=[e['simulation_time_s']-triggers[e['job_id']]['simulation_time_s'] for e in applies]
    costs=[e['numeric_result']['dispatch_to_complete_s'] for e in results if e.get('numeric_result') and 'dispatch_to_complete_s' in e['numeric_result']]
    dynamic=s.get('dynamic_obstacle') or {};boxes=dynamic.get('boxes')
    if boxes is None:boxes=[dynamic] if dynamic.get('spawn') else []
    passage=[]
    for i,box in enumerate(boxes):
        spawn=box['spawn'];ev=box.get('evaluation') or {};passed=ev.get('passage')
        passage.append(dict(box_number=i+1,spawn_time_s=spawn['simulation_time_s'],passed=bool(passed),
            passage_time_s=passed['simulation_time_s']-spawn['simulation_time_s'] if passed else None,
            passage_at_s=passed['simulation_time_s'] if passed else None,side=passed.get('side') if passed else None,
            min_clearance_m=ev.get('minimum_swept_clearance_lower_m'),collision=bool(ev.get('geometric_overlap'))))
        file=run/f"dynamic_render_{spawn['obstacle']['id']}.json";assert file.exists()
        assert json.loads(file.read_text())['obstacle']==spawn['obstacle']
    expected=2 if r['scene']=='H2' else 1 if r['scene'] in ('L2','H1') else 0
    all_passed=bool(expected and len(passage)==expected and all(v['passed'] for v in passage))
    r.update(method=cfg['phase26_method'],box_passage=all_passed,boxes=passage,expected_boxes=expected,
        box_passage_from_spawn_s=passage[-1]['passage_at_s']-passage[0]['spawn_time_s'] if all_passed else None,
        detour_trigger_count=len(triggers),detour_applied_count=len(applies),detour_latency_s=latency,
        detour_latency_median_s=float(np.median(latency)) if latency else None,
        detour_compute_p95_s=float(np.quantile(costs,.95)) if costs else None,
        certificate_rejection_count=sum(e.get('disposition')=='APPLICATION_UNSAFE' for e in results),
        recovery_count=sum(e['event']=='START' for e in rows(run/'recovery.jsonl')),
        launcher_wall_s=json.loads((run/'launch_complete.json').read_text())['launcher_wall_s'],
        wall_geometry_error_m=geometry['max_error_m'])
    return r
