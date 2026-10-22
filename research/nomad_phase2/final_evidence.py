"""Read-only final evidence audit; does not run navigation, inference or Graph."""
from collections import Counter, defaultdict
import csv, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image
from nomad_isaac.async_report import rows, stats
from nomad_isaac.common import sha256_file, write_json
from nomad_isaac.old_rollout_placement import magenta_mask
from nomad_phase2.aggregate import boot, csvwrite

def supplement(root,out):
    assert (root/'complete.json').exists(), 'Campaign must finish first'
    out.mkdir(exist_ok=False)
    amendments={p.stem:json.loads(p.read_text()) for p in (root/'audit_amendments').glob('*.json')}
    records=[json.loads(p.read_text()) for p in sorted((root/'metrics').glob('*.json'))]
    records=[amendments.get(r['key'],r) for r in records]
    journal=rows(root/'journal.jsonl');starts=[r for r in journal if r.get('event')=='START']
    assert len(starts)==len({r['key'] for r in starts})==len(records)
    detail=[];graph_results=[];terminal_graph=[];visibility_frames=0
    pacing=[];switch_changes=defaultdict(list)
    for m in records:
        run=Path(m['output']);controls=rows(run/'controller.jsonl');events=rows(run/'events.jsonl')
        observations=[r for r in rows(run/'observations.jsonl') if 'observation_id' in r]
        results=[r for r in rows(run/'phase2_graph.jsonl') if r.get('kind')=='result']
        submit=[r for r in rows(run/'phase2_graph.jsonl') if r.get('event')=='SUBMIT']
        for o in observations:
            d=o.get('dynamic')
            if not d:continue
            mask=magenta_mask(np.array(Image.open(run/o['rgb_file'])))
            assert int(mask.sum())==d['magenta_pixels']
            assert hashlib.sha256(mask.tobytes()).hexdigest()==d['mask_sha256']
            assert d['visible']==bool(d['active'] and mask.sum()>=20)
            if not d['active']:assert not o['oracle_information']['geometry_available']
            visibility_frames+=1
        for e in events:
            intervened=e['phase2']['selected_sample']!=0 or e['phase2']['graph_applied']
            assert e['phase2']['variable_speed']==intervened
        with (run/'agent_trajectory.csv').open() as f:trace=list(csv.DictReader(f))
        endpoint=trace[-1]
        pacing.extend(abs(float(t['pacing_error_s'])) for t in trace)
        if m['stage'] in ('s2a','s2b'):
            switch_changes[m['method']].extend(abs(e['actual_command_delta'][1]) for e in events[1:])
        nominal_pp=[c for c in controls if c['applied_command_source'] in ('original_pp','variable_speed_pp')]
        flags={name:sum(c['pure_pursuit'].get(name,False) for c in nominal_pp) for name in ('CURVATURE_SATURATED','ACCEL_LIMITED','OMEGA_CLIPPED')}
        flags.update(evaluated_ticks=len(nominal_pp),all_ticks=len(controls))
        wait=sum(min(1/9,max(0,m['duration_s']-c['simulation_time_s'])) for c in controls if c['graph_wait'])
        epoch=json.loads((run/'summary.json').read_text())['epoch_monotonic_ns']
        for r in results:
            s=next(j for j in submit if j['job_id']==r['job_id'])
            graph_results.append({'run':m['key'],'stage':m['stage'],'fresh_id':r['id'],'job_id':r['job_id'],
                'status':r['status'],'solver_success':r.get('solver',{}).get('success'),
                'path_feasible':r.get('accepted',False),'actually_applied':r.get('applied',False),
                'expired_before_apply':r.get('expired_before_apply',False),'stale':r['stale'],
                'solver_wall_s':r.get('solver',{}).get('solver_wall_s'),'dispatch_to_result_s':r['elapsed_s'],
                'old_distance_m':r['movement_since_dispatch_m'],'old_yaw_rad':r['yaw_change_rad'],
                'boundary':r['boundary'],'returned_pose':r['returned_pose'],
                'trajectory_rms_change_m':float(np.sqrt(np.mean(np.sum((np.array(r['poses'])[:,:2]-np.array(s['world_xy']))**2,axis=1)))) if 'poses' in r else None,
                'error':r.get('error')})
        for g in submit:
            if not any(r['job_id']==g['job_id'] for r in results):
                terminal_graph.append({'run':m['key'],'id':g['id'],'job_id':g['job_id'],'dispatch_ns':g['dispatch_ns'],'boundary':g['boundary'],'terminal_pose':[float(endpoint[k]) for k in ('x_m','y_m','yaw_rad')],'status':'TERMINAL_UNAPPLIED','termination_reason':m['termination_reason']})
        before_spawn=[e for e in events if m.get('spawn') and e['application_sim_s']<m['spawn']['simulation_time_s']]
        detail.append({'key':m['key'],'stage':m['stage'],'method':m['method'],'D_s':m['D_s'],'d_m':m['d_m'],'index':m['index'],
            'classification':m['classification'],'sample0_unsafe_count':m['sample0_unsafe_count'],'strict_margin_success':m['success'] and m['margin_violation_s']==0,
            'margin_violation':m['margin_violation_s']>0,'geometric_overlap':m['geometric_overlap'],
            'corridor_intrusion':m['corridor_intrusion'],'conservative_contact_stop':m['conservative_contact_stop'],
            'duration_s':m['duration_s'],'stop_s':m['stop_s'],'distance_m':m['distance_m'],
            'min_clearance_m':m['minimum_clearance_m'],'margin_violation_s':m['margin_violation_s'],
            'terminal_pose':[float(endpoint[k]) for k in ('x_m','y_m','yaw_rad')],
            'first_visible_fresh_status':m.get('first_fresh',{}).get('status') if m.get('first_fresh') else None,
            'flags':flags,'graph_wait_s':wait,'waypoint_timeouts':m['waypoint_timeouts'],
            'actual_replacement_count':m['actual_replacement_count'],
            'passage':m['passage'],
            'switch_sign_reversals':sum(e['actual_command_before'][1]*e['actual_command_after'][1]<-1e-12 for e in events[1:]),
            'dynamic_geometry_decision_count':sum(d.get('geometry_available',False) for d in rows(run/'phase2_decisions.jsonl')),
            'interventions_before_spawn':sum(e['phase2']['selected_sample']!=0 or e['phase2']['graph_applied'] for e in before_spawn),
            'graph':m['graph'],'feasibility_status':{state:{m2:v.get('status') for m2,v in methods.items() if isinstance(v,dict)} for state,methods in m.get('feasibility',{}).items() if isinstance(methods,dict)}})
    grouped=defaultdict(list)
    for r in detail:grouped[(r['stage'] in ('s2a','s2b'),r['method'])].append(r)
    aggregates=[]
    for (main,method),rr in grouped.items():
        if not main:continue
        flags={k:sum(r['flags'][k] for r in rr) for k in rr[0]['flags']}
        aggregates.append({'method':method,'n':len(rr),'strict_margin_success':sum(r['strict_margin_success'] for r in rr),
            'switch_abs_dw_rad_s':stats(switch_changes[method]),
            'switch_definition':'Every successive actual FRESH switch except the first; includes STOP-to-motion transitions',
            'switch_sign_reversals':sum(r['switch_sign_reversals'] for r in rr),
            'margin_violating_runs':sum(r['margin_violation'] for r in rr),'overlap_runs':sum(r['geometric_overlap'] for r in rr),
            'corridor_runs':sum(r['corridor_intrusion'] for r in rr),'unsafe_execution_without_native_unsafe_trigger':sum(r['classification']=='SAFETY_FAILURE' and r['sample0_unsafe_count']==0 for r in rr),'flags':flags,
            'flag_ratios':{k:flags[k]/flags['evaluated_ticks'] if flags['evaluated_ticks'] else None for k in ('CURVATURE_SATURATED','ACCEL_LIMITED','OMEGA_CLIPPED')},
            **{k:boot([r[k] for r in rr if r[k] is not None]) for k in ('stop_s','distance_m','min_clearance_m','margin_violation_s','graph_wait_s')}})
    main_graph=[r for r in graph_results if r['stage']=='s2b']
    result={'scope':'Exploratory N4, oracle geometry, SE2 kinematic Isaac RGB; no causal/Graph necessity proof',
        'attempts':len(records),'unique_start_attempts':len(starts),'visibility_frames_recomputed':visibility_frames,
        'all_conditional_speed_branches_validated':True,'method_aggregates':aggregates,
        'absolute_pacing_error_s':stats(pacing),
        'validation_max_errors':{k:max(m['validation'][k] for m in records) for k in ('pose_error','pp_command_error','command_trace_error','max_pacing_error_s')},
        'graph_solver_wall_s':stats([r['solver_wall_s'] for r in main_graph if r['solver_wall_s'] is not None]),
        'graph_dispatch_to_result_s':stats([r['dispatch_to_result_s'] for r in main_graph]),
        'graph_old_motion_m':stats([r['old_distance_m'] for r in main_graph]),
        'graph_result_statuses':dict(Counter(r['status'] for r in main_graph)),
        'terminal_unapplied_graph':terminal_graph,
        'legacy_visibility_flag_note':'Capture-layer used_for_control=false is inherited Phase1 metadata. Actual Phase2 geometry use is recorded by phase2_decisions.geometry_available/public_obstacle_ids and phase2_oracle publication; do not infer absence of oracle use from this legacy flag.',
        'execution_git_shas':sorted({m['execution_git_sha'] for m in records}),
        'source_record_sha256':{p.name:sha256_file(p) for p in (root/'metrics').glob('*.json')},
        'amendment_sha256':{p.name:sha256_file(p) for p in (root/'audit_amendments').glob('*.json')}}
    write_json(out/'evidence.json',result);write_json(out/'run_evidence.json',detail);csvwrite(out/'graph_results.csv',graph_results)
    print(json.dumps({k:result[k] for k in ('attempts','visibility_frames_recomputed','validation_max_errors','graph_solver_wall_s','graph_result_statuses')}))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();supplement(a.root,a.output)
