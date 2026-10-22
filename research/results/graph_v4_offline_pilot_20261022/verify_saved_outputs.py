"""Read-only post-execution verification; no minimize/solve/navigation/inference."""
import csv, json, hashlib
from pathlib import Path
import numpy as np
from nomad_isaac.common import integrate_se2, sha256_file, write_json
from nomad_isaac.handoff_audit import path_safety
from nomad_phase0.graph_v3 import FLAGS, curvature, speed_command
from nomad_phase0.graph_v4 import GraphV4, SignedDistanceField, menger, previous_stencil, selection_score
R=Path('/home/gpuadmin/Workspace/NoMaD/artifacts/graph_v4/offline_pilot_01')
V3=Path('/home/gpuadmin/Workspace/NoMaD/artifacts/graph_v3/offline_pilot_01')
OUT=Path('/home/gpuadmin/Workspace/NoMaD/visualnav-transformer/research/results/graph_v4_offline_pilot_20261022')
p=json.loads((R/'protocol.json').read_text());sp=json.loads((V3/'protocol.json').read_text())
inputs=json.loads((R/'inputs.json').read_text());summary=json.loads((R/'summary.json').read_text())
assert summary['solve_attempt_count']==531 and summary['converged_starts']==403 and summary['nonconverged_starts']==128
cases={f.stem:json.loads(f.read_text()) for f in sorted((R/'cases').glob('*.json'))}
assert len(cases)==59
fields={};native_min=100.;maxk=0.;maxboundaryk=0.;maxpose=0.;controls=0;verified_starts=0;previous_count=0;selected=[]
for identifier, item in cases.items():
 case=item['case'];config=case['public_config'];key=item['sdf_key']
 if key not in fields:
  fields[key]=SignedDistanceField(config,p['sdf_resolution_m'],p['sdf_padding_m'])
  assert hashlib.sha256(fields[key].values.tobytes()).hexdigest()==summary['sdf_fields'][key]['values_sha256']
 baseline=json.loads((V3/'cases'/(identifier+'.json')).read_text())
 for method in ['RAW','RAW+Speed','RAW+Rate limit','RIGID','Graph v3']:
  assert item['methods'][method]==baseline['methods'][method],(identifier,method)
 for branch in ['single','multi']:
  candidates=item['starts'][branch];assert len(candidates)==(1 if branch=='single' else 8)
  for candidate in candidates:
   verified_starts+=1;s=candidate['solver'];xy=np.array(candidate['world_xy_m']);original=np.array(candidate['native_world_xy_m'])
   graph=GraphV4(original,case['boundary'],case['previous_actual_vw'],config,p,fields[key])
   x=np.column_stack([xy,candidate['auxiliary_headings_rad']]).ravel()
   g,_,e,_=graph.constraints(x)
   assert abs(g.min()-s['minimum_scaled_inequality'])<1e-10
   assert abs(abs(e[0])-s['scaled_equality_error'])<1e-10
   cert=path_safety(xy,config)
   assert cert==s['exact_path_certificate']
   assert selection_score(xy,original,case['boundary'],p)==s['selection_score']
   if s['feasible']:
    assert s['success'] and g.min()>=-p['constraint_tolerance'] and abs(e[0])<=p['constraint_tolerance']
    assert cert['obstacle_clearance_m']>=.025-1e-8 and cert['corridor_clearance_m']>=.005-1e-8
    k=float(np.max(abs(menger(xy)[0])));assert k<=8*(1+p['constraint_tolerance'])
    maxk=max(maxk,k);native_min=min(native_min,cert['obstacle_clearance_m'])
    d=graph.weights@xy-np.array(case['boundary'])[:2]
    kb=2*(d@graph.left)/(d@d);error=abs(kb-graph.kappa_before)
    assert error<=p['entry_curvature_tolerance_m_inv'];maxboundaryk=max(maxboundaryk,error)
   prev_id=candidate['previous_prior_id']
   if prev_id:
    assert case['dataset']=='b_S1_P0' and cases[prev_id]['case']['fresh_id']==case['fresh_id']-1
    old=cases[prev_id]['methods']['Graph v4 '+branch]['world_xy_m']
    target=previous_stencil(old,case['boundary'],original)
    np.testing.assert_allclose(candidate['previous_prior_targets'],target,rtol=0,atol=1e-12);previous_count+=1
  feasible=[c for c in candidates if c['solver']['feasible']]
  expected=min(feasible,key=lambda x:(x['solver']['selection_score']['total'],x['sample_index'])) if feasible else None
  meta=item['metadata']['Graph v4 '+branch]
  assert meta['accepted']==(expected is not None)
  if expected:assert meta['sample_index']==expected['sample_index']
 eligible=[c for c in item['sample_checks'] if c['public_native']['safe']]
 expected=min(eligible,key=lambda x:(x['score']['total'],x['sample_index'])) if eligible else None
 assert item['metadata']['Sample selection only']['sample_index']==(expected['sample_index'] if expected else None)
 for name in ['Sample selection only','Graph v4 single','Graph v4 multi']:
  if name not in item['methods']:continue
  m=item['methods'][name]
  selected.append({'case_id':identifier,'dataset':case['dataset'],'method':name,'metadata':item['metadata'][name],
     'world_xy_m':m['world_xy_m'],'native_full':m['native_full'],
     'H_switch':{k:m['H_switch'][k] for k in ['minimum_clearance_m','safe','distance_m','end_pose']},
     'H_chunk':{k:m['H_chunk'][k] for k in ['minimum_clearance_m','safe','distance_m','end_pose','endpoint_reached','chunk_timeout']}})
  for horizon in ['H_switch','H_chunk']:
   r=m[horizon];last=case['previous_actual_vw'];pose=np.array(case['boundary']);distance=0
   flags={k:0 for k in FLAGS};ints=flags.copy()
   for i,c in enumerate(r['controls']):
    controls+=1;maxpose=max(maxpose,float(np.max(abs(pose-c['pose']))));np.testing.assert_allclose(pose,c['pose'],atol=1e-10,rtol=0)
    vw,expected_flags=speed_command(curvature(c),last[0],sp['variable_speed'])
    np.testing.assert_allclose(c['command_vw'],vw,atol=1e-12,rtol=0)
    for flag in FLAGS:assert c[flag]==expected_flags[flag]
    assert .05<=vw[0]<=.2 and abs(vw[1])<=.4 and abs(vw[0]-last[0])*9<=.5+1e-12
    end=r['controls'][i+1]['offset_tick'] if i+1<len(r['controls']) else r['executed_ticks']
    held=end-c['offset_tick'];assert 0<held<=8
    pose=integrate_se2(pose,*vw,held/72);distance+=vw[0]*held/72
    for flag in FLAGS:flags[flag]+=int(c[flag]);ints[flag]+=int(c[flag])*held
    last=vw
   np.testing.assert_allclose(pose,r['end_pose'],atol=1e-10,rtol=0)
   assert abs(distance-r['distance_m'])<1e-10 and flags==r['flag_control_ticks'] and ints==r['flag_integration_intervals']
assert verified_starts==531
assert all(sha256_file(Path(f))==h for f,h in inputs['input_sha256'].items())
result={'status':'PASS','starts_verified':verified_starts,'feasible_paths_exactly_verified':403,
 'minimum_feasible_native_clearance_m':native_min,'maximum_feasible_node_curvature_m_inv':maxk,
 'maximum_boundary_curvature_error_m_inv':maxboundaryk,'control_records_verified':controls,
 'maximum_held_command_pose_error':maxpose,'previous_prior_stencils_verified':previous_count,
 'all_saved_baselines_identical':True,'selection_rule_recomputed':True,'source_and_input_hashes_unchanged':2378,
 'no_new_solve':True,'no_navigation':True,'no_inference':True,
 'case_sha256':{f.name:sha256_file(f) for f in sorted((R/'cases').glob('*.json'))},
 'script_sha256':sha256_file(Path(__file__))}
write_json(OUT/'verification.json',result)
write_json(OUT/'selected_paths.json',{'meaning':'Offline evaluated paths; rejected single iterates explicitly labelled, no selected multi path when none feasible','paths':selected})
print(json.dumps({k:v for k,v in result.items() if k!='case_sha256'},indent=2))
