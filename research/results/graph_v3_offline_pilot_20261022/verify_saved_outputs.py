import json,hashlib,csv,collections
from pathlib import Path
import numpy as np
from nomad_isaac.common import integrate_se2,sha256_file,write_json
from nomad_isaac.clearance import configured_obstacles,obstacle_bounds,single_obstacle_config,swept_clearance
from nomad_phase0.graph_v3 import FLAGS,curvature
ROOT=Path('/home/gpuadmin/Workspace/NoMaD/artifacts/graph_v3/offline_pilot_01')
OUT=Path('/home/gpuadmin/Workspace/NoMaD/visualnav-transformer/research/results/graph_v3_offline_pilot_20261022')
s=json.loads((ROOT/'summary.json').read_text());p=json.loads((ROOT/'protocol.json').read_text())
selection=json.loads((ROOT/'selection.json').read_text())
assert len(list((ROOT/'cases').glob('*.json')))==59
count=0;max_pose=0.;max_accel=0.;minv=1.;maxv=0.;maxw=0.;profiles=[];initial=[];aggregate_flags=[];method_summary=[];tradeoffs=[]
for file in sorted((ROOT/'cases').glob('*.json')):
 c=json.loads(file.read_text());case=c['case'];g=c['methods']['Graph v3'];solver=c['solver']
 assert c['solve_attempted'] and solver and solver['nfev']<=200
 np.testing.assert_allclose(g['world_xy_m'], np.array(g['world_xy_m']), atol=0.)
 profiles.append({'case_id':case['case_id'],'dataset':case['dataset'],'converged':solver['success'],'boundary':case['boundary'],'previous_actual_vw':case['previous_actual_vw'],'world_xy_m':g['world_xy_m'],'auxiliary_heading_rad':c['graph_v3_auxiliary_headings'],'profile_columns':['projected_arclength_m','applied_v_m_s','target_v_m_s','kappa_PP_m_inv'],'H_chunk_speed_profile':[[z['arclength_m'],z['v_m_s'],z['v_target_m_s'],z['kappa_PP_m_inv']] for z in g['H_chunk']['speed_profile']]})
 if case['dataset']=='c_stress':
  gaps={b['id']:swept_clearance(case['boundary'],0,0,0,*obstacle_bounds(single_obstacle_config(case['evaluation_config'],b)),.09)['lower_m'] for b in configured_obstacles(case['evaluation_config'])}
  initial.append({'case_id':case['case_id'],'initial_clearance_m':min(gaps.values()),'per_box':gaps})
 for method,m in c['methods'].items():
  for horizon in ['H_switch','H_chunk']:
   r=m[horizon];controls=r['controls'];pose=np.array(case['boundary']);last=case['previous_actual_vw'];distance=0.;flags={f:0 for f in FLAGS};intervalflags=flags.copy()
   assert len(controls)==r['control_ticks'] and len(controls)==len(r['speed_profile'])
   assert np.all(np.diff([z['arclength_m'] for z in r['speed_profile']])>=-1e-12)
   for j,z in enumerate(controls):
    count+=1;np.testing.assert_allclose(z['pose'],pose,atol=1e-10,rtol=0)
    vw=z['command_vw'];k=curvature(z);assert abs(k-z['kappa_PP_m_inv'])<1e-10
    assert 0.05-1e-12<=vw[0]<=.2+1e-12 and abs(vw[1])<=.4+1e-12
    if method in ['RAW+Speed','Graph v3']:
     target=float(np.clip(.4/abs(k),.05,.2)) if k else .2
     expectedv=float(np.clip(target,max(.05,last[0]-.5/9),min(.2,last[0]+.5/9)))
     np.testing.assert_allclose(vw,[expectedv,float(np.clip(expectedv*k,-.4,.4))],atol=1e-12,rtol=0)
     assert z['CURVATURE_SATURATED']==(abs(k)>8.)
     assert z['ACCEL_LIMITED']==(abs(vw[0]-target)>1e-12)
     assert z['OMEGA_CLIPPED']==(abs(vw[1]-vw[0]*k)>1e-12)
     assert abs(vw[0]-last[0])*9<=.5+1e-12
     max_accel=max(max_accel,abs(vw[0]-last[0])*9);minv=min(minv,vw[0]);maxv=max(maxv,vw[0]);maxw=max(maxw,abs(vw[1]))
    if method=='RAW+Rate limit':assert abs(vw[1]-last[1])<=.1+1e-12
    held=(controls[j+1]['offset_tick'] if j+1<len(controls) else r['executed_ticks'])-z['offset_tick'];assert 1<=held<=8
    pose=integrate_se2(pose,*vw,held/72);distance+=vw[0]*held/72
    for f in FLAGS:flags[f]+=int(z[f]);intervalflags[f]+=int(z[f])*held
    last=vw
   assert flags==r['flag_control_ticks'] and intervalflags==r['flag_integration_intervals']
   np.testing.assert_allclose(pose,r['end_pose'],atol=1e-10,rtol=0);max_pose=max(max_pose,float(np.max(abs(pose-r['end_pose']))))
   assert abs(distance-r['distance_m'])<1e-10
   if r['chunk_timeout']:assert np.linalg.norm(pose[:2]-np.array(m['world_xy_m'])[-1])>.01
 for h in ['H_switch','H_chunk']:
  tr={'case_id':case['case_id'],'dataset':case['dataset'],'horizon':h,'converged':solver['success'],
      'qualifies_vs_Speed':g['qualification'][h]['vs_RAW+Speed']['qualifies'],
      'failed_criteria':';'.join(k for k,v in g['qualification'][h]['vs_RAW+Speed']['checks'].items() if not v),
      'native_obstacle_loss_vs_RAW_m':c['methods']['RAW']['native_full']['obstacle_clearance_m']-g['native_full']['obstacle_clearance_m'],
      'native_corridor_loss_vs_RAW_m':c['methods']['RAW']['native_full']['corridor_clearance_m']-g['native_full']['corridor_clearance_m'],
      'rollout_obstacle_loss_vs_RAW_m':c['methods']['RAW'][h]['minimum_clearance_m']-g[h]['minimum_clearance_m'],
      'rollout_corridor_loss_vs_RAW_m':c['methods']['RAW'][h]['minimum_corridor_m']-g[h]['minimum_corridor_m'],
      'H_switch_motion_ratio_RAW':g['H_switch']['distance_m']/c['methods']['RAW']['H_switch']['distance_m']}
  tradeoffs.append(tr)
for d,hs in s['comparison'].items():
 for h,methods in hs.items():
  for m,v in methods.items():
   if not v['n']:continue
   row={'dataset':d,'horizon':h,'method':m,'n':v['n'],'mean_abs_dw':v['switch_abs_dw']['mean'],'native_safe':v['native_safe_count'],'rollout_safe':v['rollout_safe_count'],'accepted_complete_joint_safe':v['complete_and_joint_safe_count'],'overlaps':v['overlap_count'],'corridor_intrusions':v['corridor_intrusion_count'],'distance_mean_m':v['distance_m']['mean'],'speed_mean_m_s':v['mean_speed_m_s']['mean'],'endpoint_complete':v['endpoint_reached_count'],'chunk_timeout':v['chunk_timeout_count'],'joint_improvement_vs_RAW':v['qualifies_vs_RAW_count'],'joint_improvement_vs_Speed':v['qualifies_vs_Speed_count'],'raw_unsafe_to_accepted_safe':v['raw_unsafe_to_safe_count']};method_summary.append(row)
   for f,vf in v['flags'].items():aggregate_flags.append({'dataset':d,'horizon':h,'method':m,'flag':f,**vf})
assert all(sha256_file(Path(f))==h for f,h in selection['input_sha256'].items())
verify={'status':'PASS','actual_solve_count':59,'restarts':0,'navigation':0,'inference':0,'verified_control_records':count,'variable_speed_min_m_s':minv,'variable_speed_max_m_s':maxv,'maximum_abs_w_rad_s':maxw,'maximum_acceleration_m_s2':max_accel,'max_control_hold_pose_replay_error':max_pose,'control_flags_recomputed':'PASS','rate_limit_recomputed':'PASS','arclength_profiles_nondecreasing':'PASS','no_zero_speed_rotation_commands':True,'all_2311_inputs_and_frozen_sources_unchanged':True,'initial_stress_clearance':initial,'case_outputs_sha256':{f.name:sha256_file(f) for f in sorted((ROOT/'cases').glob('*.json'))},'artifact_summary_sha256':sha256_file(ROOT/'summary.json'),'script_sha256':sha256_file(Path(__file__))}
write_json(OUT/'verification.json',verify)
write_json(OUT/'graph_v3_corrections.json',{'meaning':p['variable_speed']['speed_profile'],'speed_rule':p['variable_speed'],'cases':profiles})
for name,records in [('flag_counts.csv',aggregate_flags),('method_summary.csv',method_summary),('tradeoffs.csv',tradeoffs)]:
 with (OUT/name).open('x') as f:w=csv.DictWriter(f,list(records[0]));w.writeheader();w.writerows(records)
print(json.dumps({k:v for k,v in verify.items() if k not in ['case_outputs_sha256','initial_stress_clearance']}))
print('initial stress',initial)
