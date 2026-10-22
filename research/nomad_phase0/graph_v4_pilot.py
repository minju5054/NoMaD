"""Frozen v4 campaign on saved 59 cases, one solve per registered start/method."""
import argparse
import copy
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy

from nomad_isaac.common import ROOT, local_to_world, sha256_file, write_json
from nomad_isaac.clearance import configured_obstacles, obstacle_bounds, single_obstacle_config, swept_clearance
from nomad_isaac.handoff_audit import path_safety
from .graph_v2_pilot import distribution, git, write_csv
from .graph_v3 import FLAGS
from .graph_v3_pilot import evaluate
from .graph_v4 import GraphV4, SignedDistanceField, selection_score
from .pure_pursuit import PurePursuit

PROTOCOL = Path(__file__).with_name('graph_v4_protocol.json')
V3 = ROOT.parent/'artifacts/graph_v3/offline_pilot_01'
V3_RESULTS = ROOT/'research/results/graph_v3_offline_pilot_20261022'
METHODS = ['RAW', 'RAW+Speed', 'RAW+Rate limit', 'RIGID', 'Sample selection only',
           'Graph v3', 'Graph v4 single', 'Graph v4 multi']
NEW = ['Sample selection only', 'Graph v4 single', 'Graph v4 multi']


def initial_clearance(case):
    config = case['evaluation_config']
    return min(swept_clearance(case['boundary'], 0, 0, 0,
        *obstacle_bounds(single_obstacle_config(config, box)), config['agent_radius_m'])['lower_m']
        for box in configured_obstacles(config))


def preflight(out):
    assert not out.exists(), 'Never overwrite an existing campaign'
    p = json.loads(PROTOCOL.read_text()); selection = json.loads((V3/'selection.json').read_text())
    verification = json.loads((V3_RESULTS/'verification.json').read_text())
    assert len(selection['cases']) == 59
    hashes = dict(selection['input_sha256'])
    for name in ['summary.json', 'selection.json', 'protocol.json', 'execution.json']:
        hashes[str(V3/name)] = sha256_file(V3/name)
    raw_max = 0.; shapes = []; unsafe = []
    for case in selection['cases']:
        saved = V3/'cases'/(case['case_id']+'.json')
        assert sha256_file(saved) == verification['case_outputs_sha256'][saved.name]
        hashes[str(saved)] = sha256_file(saved)
        derived = Path(case['source_run'])/'model/derived'/f"{case['fresh_id']:04d}.npz"
        hashes[str(derived)] = sha256_file(derived)
        with np.load(derived, allow_pickle=False) as data:
            samples = data['metric'].copy()
        assert samples.shape == (8, 8, 2) and np.isfinite(samples).all()
        worlds = np.array([local_to_world(sample, case['observation_pose']) for sample in samples])
        np.testing.assert_allclose(worlds[0], case['fresh_world_xy'], atol=1e-12, rtol=0)
        config = case['public_config']; c = config['corridor']
        lower = np.array([c['xmin']-p['sdf_padding_m'], -c['half_width']-p['sdf_padding_m']])
        upper = np.array([c['xmax']+p['sdf_padding_m'], c['half_width']+p['sdf_padding_m']])
        assert (worlds.min(axis=(0,1))-p['xy_trust_region_m'] > lower).all()
        assert (worlds.max(axis=(0,1))+p['xy_trust_region_m'] < upper).all()
        pp, _ = PurePursuit(worlds[0], json.loads((V3/'protocol.json').read_text())['follower']).control(case['boundary'])
        saved_raw = json.loads(saved.read_text())['methods']['RAW']['H_switch']['first_command_vw']
        raw_max = max(raw_max, float(np.max(abs(np.array(pp)-saved_raw))))
        assert raw_max < 1e-10
        clearance = initial_clearance(case)
        if clearance < .02: unsafe.append({'case_id':case['case_id'], 'dataset':case['dataset'], 'clearance_m':clearance})
        shapes.append({'case_id':case['case_id'], 'samples':8, 'initial_clearance_m':clearance})
    assert {c['case_id'] for c in unsafe} == {'old_rollout_obstacle_01_F0052', 'topomap_sudden_01_F0053', 'early_raw_01_F0064'}
    for f in [PROTOCOL, Path(__file__), PROTOCOL.with_name('graph_v4.py'),
              ROOT/'research/tests/test_graph_v4.py']:
        hashes[str(f.resolve())] = sha256_file(f)
    assert all(sha256_file(Path(f)) == h for f, h in hashes.items())
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/'protocol.json', p)
    write_json(out/'inputs.json', {'cases':selection['cases'], 'input_sha256':hashes,
        'v3_source':str(V3), 'v3_case_count':59, 'maximum_solve_count':531,
        'raw_max_first_command_error':raw_max, 'initial_unsafe':unsafe, 'samples':shapes,
        'optimization_runs_so_far':0, 'base_contains_plot_only_descendants':git('rev-parse', 'HEAD')})
    print(json.dumps({'preflight':'PASS', 'cases':59, 'saved_samples':472, 'raw_max_error':raw_max,
                      'protected_hashes':len(hashes), 'initial_unsafe':unsafe}), flush=True)


def run_start(sample, xy, case, p, field, previous):
    start = time.perf_counter()
    result = {'sample_index':sample, 'native_world_xy_m':xy.tolist(),
              'solve_attempted':False, 'previous_prior_id':previous['id'] if previous else None}
    try:
        graph = GraphV4(xy, case['boundary'], case['previous_actual_vw'], case['public_config'], p, field,
                        previous_xy=previous['xy'] if previous else None)
        result['initialization_wall_s'] = time.perf_counter()-start
        result.update(entry=graph.entry, heading_chords=graph.chords,
                      previous_prior_targets=graph.previous_target.tolist() if graph.previous_target is not None else None)
        result['solve_attempted'] = True
        poses, solver = graph.solve()
        result.update(world_xy_m=poses[:, :2].tolist(), auxiliary_headings_rad=poses[:, 2].tolist(), solver=solver)
    except (ValueError, FloatingPointError) as error:
        result['error'] = str(error)
    result['total_wall_s'] = time.perf_counter()-start
    return result


def candidate_feasible(result):
    return bool(result.get('solver', {}).get('feasible', False))


def count_distribution(values):
    d = distribution(values)
    for threshold in [.02, .1]:
        label = f'over_{round(threshold*1000)}ms'
        d[label+'_count'] = sum(v > threshold for v in values)
        d[label+'_ratio'] = d[label+'_count']/len(values) if values else None
    return d


def case_rows(case, methods, metadata):
    result = []; raw = methods['RAW']
    unsafe_B = initial_clearance(case) < .02
    for name in METHODS:
        m = methods.get(name); meta = metadata[name]
        for h in ['H_switch', 'H_chunk']:
            base = raw[h]; row = {'case_id':case['case_id'], 'dataset':case['dataset'], 'method':name,
                'horizon':h, 'initial_unsafe_B':unsafe_B, 'initial_clearance_m':initial_clearance(case),
                'available':m is not None, 'accepted_path':meta['accepted'], 'status':meta['status'],
                'sample_index':meta.get('sample_index'), 'previous_prior_id':meta.get('previous_prior_id'),
                'method_wall_s':meta.get('method_wall_s'), 'cold_inclusive_wall_s':meta.get('cold_inclusive_wall_s'),
                'raw_unsafe':not(raw['native_full']['safe'] and base['safe']),
                'native_safe':False, 'rollout_safe':False, 'complete':False, 'safe_complete':False,
                'safe_complete_progress':False, 'raw_unsafe_to_safe':False,
                'overlap':None, 'corridor_intrusion':None, 'native_clearance_m':None, 'rollout_clearance_m':None,
                'duration_s':None, 'distance_m':None, 'H_switch_motion_ratio_RAW':None, 'progress_pass':False,
                'switch_abs_dw':None, 'sign_reversal':None, 'xy_rms_from_RAW0_m':None,
                'control_ticks':0, 'integration_intervals':0, 'chunk_timeout':None, 'endpoint_reached':None}
            for f in FLAGS: row[f+'_control_ticks'] = 0; row[f+'_intervals'] = 0
            if m is not None:
                r = m[h]; short = m['H_switch']
                completed = r['endpoint_reached'] if h == 'H_chunk' else r['executed_ticks'] == r['requested_ticks']
                progress = not short['stop_or_truncated'] and short['distance_m'] >= .7*raw['H_switch']['distance_m']
                safe = m['native_full']['safe'] and r['safe'] and completed and meta['accepted']
                row.update(native_safe=m['native_full']['safe'], rollout_safe=r['safe'], complete=completed,
                    safe_complete=safe, safe_complete_progress=safe and progress,
                    raw_unsafe_to_safe=row['raw_unsafe'] and safe, overlap=r['geometric_overlap'],
                    corridor_intrusion=r['corridor_intrusion'], native_clearance_m=m['native_full']['obstacle_clearance_m'],
                    rollout_clearance_m=r['minimum_clearance_m'], duration_s=r['duration_s'], distance_m=r['distance_m'],
                    H_switch_motion_ratio_RAW=short['distance_m']/raw['H_switch']['distance_m'], progress_pass=progress,
                    switch_abs_dw=m['switch_abs_delta_w_rad_s'], sign_reversal=m['switch_sign_reversal'],
                    xy_rms_from_RAW0_m=m['xy_rms_m'], control_ticks=r['control_ticks'],
                    integration_intervals=r['executed_ticks'], chunk_timeout=r['chunk_timeout'], endpoint_reached=r['endpoint_reached'])
                for f in FLAGS:
                    row[f+'_control_ticks'] = r['flag_control_ticks'][f]
                    row[f+'_intervals'] = r['flag_integration_intervals'][f]
            result.append(row)
    return result


def start_rows(case, branch, starts):
    result = []
    for start in starts:
        s = start.get('solver', {})
        result.append({'case_id':case['case_id'], 'dataset':case['dataset'], 'branch':branch,
            'sample_index':start['sample_index'], 'previous_prior_id':start['previous_prior_id'],
            'solve_attempted':start['solve_attempted'], 'converged':s.get('success', False),
            'constraint_feasible':s.get('feasible', False), 'status':s.get('status'),
            'message':start.get('error') or s.get('message'), 'iterations':s.get('iterations'),
            'solver_wall_s':s.get('solver_wall_s'), 'total_wall_s':start['total_wall_s'],
            'objective':s.get('objective'), 'selection_score':s.get('selection_score', {}).get('total'),
            'maximum_node_curvature':s.get('maximum_node_curvature_m_inv'),
            'minimum_scaled_inequality':s.get('minimum_scaled_inequality'),
            'entry_curvature':s.get('entry_curvature_m_inv'), 'previous_curvature':s.get('previous_curvature_m_inv'),
            'native_exact_clearance':s.get('exact_path_certificate', {}).get('obstacle_clearance_m'),
            'world_xy_m':json.dumps(start.get('world_xy_m'))})
    return result


def aggregate(rows, starts, records, fields, execution, inputs):
    summary = {'scope':'Oracle geometry, fixed-B offline mechanism validation; no new navigation or inference',
        'execution':execution, 'cases':59, 'initial_unsafe':inputs['initial_unsafe'], 'comparison':{},
        'timing':{}, 'sdf_fields':fields, 'solve_attempt_count':sum(s['solve_attempted'] for s in starts),
        'converged_starts':sum(s['converged'] for s in starts), 'feasible_starts':sum(s['constraint_feasible'] for s in starts),
        'nonconverged_starts':sum(s['solve_attempted'] and not s['converged'] for s in starts),
        'initialization_rejections':sum(not s['solve_attempted'] for s in starts)}
    for dataset in ['a_S0', 'b_S1_P0', 'c_stress']:
        summary['comparison'][dataset] = {}
        for population in ['all', 'initially_safe_B']:
            summary['comparison'][dataset][population] = {}
            for horizon in ['H_switch', 'H_chunk']:
                dest = summary['comparison'][dataset][population][horizon] = {}
                for method in METHODS:
                    r = [r for r in rows if r['dataset']==dataset and r['horizon']==horizon and r['method']==method
                         and (population=='all' or not r['initial_unsafe_B'])]
                    v = {'denominator':len(r), 'evaluated_n':sum(x['available'] for x in r),
                         'accepted_path_n':sum(x['accepted_path'] for x in r),
                         'no_selected_path_n':sum(not x['available'] for x in r)}
                    for key in ['native_safe','rollout_safe','complete','safe_complete','safe_complete_progress','raw_unsafe_to_safe',
                                'overlap','corridor_intrusion','progress_pass','sign_reversal','chunk_timeout','endpoint_reached']:
                        v[key+'_count'] = sum(bool(x[key]) for x in r)
                    for key in ['overlap','corridor_intrusion']:
                        v['accepted_'+key+'_count'] = sum(bool(x[key]) and x['accepted_path'] for x in r)
                    for key in ['switch_abs_dw','H_switch_motion_ratio_RAW','distance_m','rollout_clearance_m','xy_rms_from_RAW0_m']:
                        v[key] = distribution([x[key] for x in r if x[key] is not None])
                        v['accepted_'+key] = distribution([x[key] for x in r if x[key] is not None and x['accepted_path']])
                    v['flags'] = {}
                    for flag in FLAGS:
                        for accepted in [False, True]:
                            subset = [x for x in r if x['available'] and (not accepted or x['accepted_path'])]
                            count = sum(x[flag+'_control_ticks'] for x in subset); total = sum(x['control_ticks'] for x in subset)
                            v['flags'][('accepted_' if accepted else '')+flag] = {'ticks':count, 'total':total, 'ratio':count/total if total else None}
                    dest[method] = v
    for branch in ['single', 'multi']:
        subset = [s for s in starts if s['branch']==branch]
        summary['timing'][branch+'_per_start_solver_s'] = count_distribution([s['solver_wall_s'] for s in subset if s['solver_wall_s'] is not None])
        summary['timing'][branch+'_per_start_total_s'] = count_distribution([s['total_wall_s'] for s in subset])
        summary[branch+'_nonconverged_starts'] = sum(s['solve_attempted'] and not s['converged'] for s in subset)
        summary[branch+'_feasible_starts'] = sum(s['constraint_feasible'] for s in subset)
    for method in NEW:
        subset = [r['metadata'][method] for r in records]
        summary['timing'][method+'_method_s'] = count_distribution([m['method_wall_s'] for m in subset])
        if method != 'Sample selection only':
            summary['timing'][method+'_cold_inclusive_s'] = count_distribution([m['cold_inclusive_wall_s'] for m in subset])
    summary['timing']['Graph v3_cached_solver_s'] = count_distribution([r['v3_solver_wall_s'] for r in records])
    summary['limitations'] = [
        'Discrete Menger path curvature and boundary-circle equality do not bound actual PP curvature or certify PP rollout.',
        'SDF certification covers all seven native segments, not B-to-entry connection. PP safety is post-hoc only.',
        'No feasible multi/sample solution is NO_SELECTION, not a safe stop or a new fallback policy.',
        'Single-start failed final iterates are diagnostic; accepted and all-evaluated denominators are separate.',
        'S1 weak previous prior uses immediately previous accepted geometric output, with actual saved B/OLD command; not a new closed-loop state.',
        'Sample selection only uses same variable-speed executor as v4; its geometry is unmodified.',
        'H_chunk is an unexecuted frozen continuation capped at60s, including recorded mathematical overlap; no future FRESH or1s expiry.',
        'Three initially unsafe stress cases cannot satisfy full-interval2cm; all six preserved, salvageable denominator3.',
        '20ms is an online target only; no solver-time boundary motion is modelled.'
    ]
    return summary


def execute(out):
    assert not git('status', '--porcelain'), 'Commit protocol/code and run from clean checkout'
    p = json.loads(PROTOCOL.read_text()); assert p == json.loads((out/'protocol.json').read_text())
    inputs = json.loads((out/'inputs.json').read_text())
    assert all(sha256_file(Path(f)) == h for f,h in inputs['input_sha256'].items())
    (out/'cases').mkdir(exist_ok=False)
    execution = {'git_sha':git('rev-parse','HEAD'), 'clean_checkout':True, 'python':sys.version,
                 'numpy':np.__version__, 'scipy':scipy.__version__, 'platform':platform.platform(),
                 'protocol_sha256':sha256_file(PROTOCOL), 'new_navigation':0, 'new_inference':0, 'restarts':0}
    write_json(out/'execution.json', execution)
    evaluation_protocol = json.loads((V3/'protocol.json').read_text())
    histories = {'single':None, 'multi':None}; cache = {}; fields = {}; records = []; all_rows = []; all_starts = []
    for case in inputs['cases']:
        case_start = time.perf_counter()
        saved = json.loads((V3/'cases'/(case['case_id']+'.json')).read_text())
        methods = {m:copy.deepcopy(saved['methods'][m]) for m in ['RAW','RAW+Speed','RAW+Rate limit','RIGID','Graph v3']}
        metadata = {m:{'accepted':m!='Graph v3' or saved['solver']['success'], 'status':'CACHED_V3' if m=='Graph v3' else 'CACHED_BASELINE',
                       'sample_index':0} for m in methods}
        with np.load(Path(case['source_run'])/'model/derived'/f"{case['fresh_id']:04d}.npz", allow_pickle=False) as data:
            samples = np.array([local_to_world(s, case['observation_pose']) for s in data['metric']])
        config = case['public_config']
        geometry = {'obstacles':configured_obstacles(config), 'corridor':config['corridor'], 'radius':config['agent_radius_m']}
        key = hashlib.sha256(json.dumps(geometry,sort_keys=True).encode()).hexdigest()
        if key not in cache:
            field = SignedDistanceField(config, p['sdf_resolution_m'], p['sdf_padding_m']); cache[key] = field
            fields[key] = {'geometry':geometry, 'shape':list(field.values.shape), 'resolution_m':field.h,
                'bilinear_error_bound_m':field.error_bound, 'build_wall_s':field.build_wall_s,
                'values_sha256':hashlib.sha256(field.values.tobytes()).hexdigest()}
        field = cache[key]
        # Original safe sample selection uses public native geometry only.
        selection_start = time.perf_counter(); sample_checks = []
        for i, xy in enumerate(samples):
            check = path_safety(xy, config)
            sample_checks.append({'sample_index':i, 'public_native':check, 'score':selection_score(xy,xy,case['boundary'],p)})
        eligible = [r for r in sample_checks if r['public_native']['safe']]
        selected = min(eligible,key=lambda r:(r['score']['total'],r['sample_index'])) if eligible else None
        metadata['Sample selection only'] = {'accepted':selected is not None, 'status':'SELECTED_UNMODIFIED' if selected else 'NO_SELECTION',
            'sample_index':selected['sample_index'] if selected else None, 'method_wall_s':time.perf_counter()-selection_start}
        # Both v4 methods are solved before PP validation; no rollout outcome can affect selection/history.
        branch_results = {}; selected_paths = {}
        for branch, indices in [('single',[0]), ('multi',range(8))]:
            name = 'Graph v4 '+branch
            previous = histories[branch] if case['dataset']=='b_S1_P0' else None
            if previous is not None: assert previous['fresh_id']==case['fresh_id']-1
            start_time = time.perf_counter()
            starts = [run_start(i,samples[i],case,p,field,previous) for i in indices]
            eligible = [r for r in starts if candidate_feasible(r)]
            chosen = min(eligible,key=lambda r:(r['solver']['selection_score']['total'],r['sample_index'])) if eligible else None
            elapsed = time.perf_counter()-start_time
            branch_results[branch] = starts
            metadata[name] = {'accepted':chosen is not None, 'status':'CONSTRAINT_FEASIBLE_SELECTED' if chosen else 'NO_FEASIBLE_SOLUTION',
                'sample_index':chosen['sample_index'] if chosen else None, 'method_wall_s':elapsed,
                'cold_inclusive_wall_s':elapsed+field.build_wall_s,
                'previous_prior_id':previous['id'] if previous else None}
            if chosen:
                selected_paths[name] = np.array(chosen['world_xy_m'])
            elif branch=='single' and 'world_xy_m' in starts[0]:
                selected_paths[name] = np.array(starts[0]['world_xy_m'])
                metadata[name]['status'] = 'REJECTED_FINAL_ITERATE_DIAGNOSTIC'
                metadata[name]['sample_index'] = 0
            if case['dataset']=='b_S1_P0':
                histories[branch] = {'id':case['case_id'], 'fresh_id':case['fresh_id'], 'xy':chosen['world_xy_m']} if chosen else None
        if selected: selected_paths['Sample selection only'] = samples[selected['sample_index']]
        for name, xy in selected_paths.items():
            try:
                methods[name] = evaluate(xy, case, evaluation_protocol, 'speed')
                for h in ['H_switch','H_chunk']: methods[name][h].pop('poses',None)
            except (ValueError, FloatingPointError) as error:
                metadata[name]['evaluation_error'] = str(error); metadata[name]['status'] += '_EVALUATION_FAILED'
                metadata[name]['accepted'] = False
        result = {'case':case, 'methods':methods, 'metadata':metadata, 'sample_checks':sample_checks,
                  'starts':branch_results, 'sdf_key':key}
        write_json(out/'cases'/(case['case_id']+'.json'), result)
        all_rows.extend(case_rows(case, methods, metadata))
        for branch, starts in branch_results.items(): all_starts.extend(start_rows(case,branch,starts))
        records.append({'case_id':case['case_id'], 'metadata':metadata, 'v3_solver_wall_s':saved['solver']['wall_s']})
        print(json.dumps({'case':case['case_id'], 'completed':len(records), 'single_accepted':metadata['Graph v4 single']['accepted'],
            'multi_sample':metadata['Graph v4 multi']['sample_index'], 'feasible_multi':sum(candidate_feasible(s) for s in branch_results['multi']),
            'single_wall_s':metadata['Graph v4 single']['method_wall_s'], 'multi_wall_s':metadata['Graph v4 multi']['method_wall_s'],
            'case_total_s':time.perf_counter()-case_start}),flush=True)
    write_csv(out/'comparison.csv',all_rows); write_csv(out/'starts.csv',all_starts)
    summary = aggregate(all_rows,all_starts,records,fields,execution,inputs)
    assert all(sha256_file(Path(f)) == h for f,h in inputs['input_sha256'].items())
    summary['all_input_hashes_unchanged'] = True
    write_json(out/'summary.json',summary)
    write_json(out/'records.json',records)
    print(json.dumps({'finished':True, 'cases':len(records), 'solves':summary['solve_attempt_count'],
                      'converged':summary['converged_starts'], 'feasible':summary['feasible_starts']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['preflight','execute']); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); (preflight if args.mode=='preflight' else execute)(args.output.resolve())
