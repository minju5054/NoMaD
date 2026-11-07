"""All saved PATH_APPLIED events; offline forward integration only."""
import argparse,csv,hashlib,json,os,time
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,local_to_world
from nomad_phase15b.depth import Snapshot,evaluate_samples
from .exec_cert import certify

OUT=ROOT/'research/results/phase32o'
MANIFEST={}
def register(p):
 p=Path(p).resolve()
 if str(p) not in MANIFEST:MANIFEST[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 return p

def read(p):return json.loads(register(p).read_text())
def lines(p):return [json.loads(x) for x in register(p).read_text().splitlines() if x] if Path(p).exists() else []
def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 if isinstance(x,np.ndarray):return clean(x.tolist())
 if isinstance(x,np.generic):return clean(x.item())
 if isinstance(x,float) and not np.isfinite(x):return None
 return x

def save(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(clean(obj),ensure_ascii=False,allow_nan=False,indent=2)+'\n');os.replace(tmp,p)
def csvout(p,rows):
 if not rows:return
 with Path(p).open('w',newline='') as f:
  fields=list(dict.fromkeys(k for r in rows for k in r));w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader()
  for r in rows:w.writerow({k:json.dumps(clean(v)) if isinstance(v,(dict,list)) else clean(v) for k,v in r.items()})

def array_trace(root):
 with register(root/'agent_trajectory.csv').open() as f:r=list(csv.DictReader(f))
 return dict(t=np.array([float(x['simulation_time_s']) for x in r]),pose=np.array([[float(x[k]) for k in ('x_m','y_m','yaw_rad')] for x in r]),vw=np.array([[float(x[k]) for k in ('v_m_s','w_rad_s')] for x in r]))

def restored_maps(root):
 restored={}
 for f in (root/'repair_jobs').glob('input_*.npz'):
  register(f)
  with np.load(f) as z:
   if not {'metadata','values','occupied','observed'}.issubset(z.files):continue
   m=json.loads(str(z['metadata']));restored[(m.get('frame_id'),m.get('sim_s'))]=str(f)
 return restored

def stored_r3_alternatives(root,detours,app,now,field):
 """Only already available same-boundary saved R3 outcomes. No new solver.

 The original job map may predate the application map; every candidate is
 recertified with the current EXEC-CERT input. Absent saved R3 is UNASSESSED.
 """
 candidates=[];jobs=0
 submits={x['job_id']:x for x in detours if x['event'] in ('TRIGGER','SUBMIT')}
 for r in detours:
  if r['event']!='RESULT' or r.get('numeric_result') is None or r['simulation_time_s']>now+1e-9:continue
  job=submits.get(r['job_id'],{});B=job.get('B',r.get('pose_at_result'))
  if B is None or np.linalg.norm(np.array(B[:2])-np.array(app['pose'][:2]))>1e-6:continue
  if abs((B[2]-app['pose'][2]+np.pi)%(2*np.pi)-np.pi)>1e-6:continue
  if now-r['simulation_time_s']>1/9+1e-9:continue
  jobs+=1
  for c in r['numeric_result'].get('results',[]):
   if c.get('accepted') and c.get('path') is not None:
    path=np.asarray(c['path'])
    if path.shape==np.asarray(app['path_world']).shape and np.allclose(path,app['path_world'],atol=1e-8):continue
    candidates.append(path)
 return jobs,candidates

def run_one(r):
 root=Path(r['output']);tr=array_trace(root);repair=lines(root/'repair.jsonl');apps=[x for x in repair if x['event']=='PATH_APPLIED'];commands=lines(root/'phase20_commands.jsonl');controls=lines(root/'controller.jsonl');updates=lines(root/'depth/updates.jsonl');events=lines(root/'events.jsonl');detours=lines(root/'detour.jsonl')
 ctrl={round(x['simulation_time_s']*72):x for x in controls};evt={e['id']:e for e in events if e.get('overnight_metric_samples') is not None};pub=np.array([u['publication_monotonic_ns'] for u in updates]);bycopy=restored_maps(root)
 box_positive=r['primary_cause']=='BOX_COLLISION';rows=[];alt=[];errors=[];same_errors=[];examples=[];last_file=None;field=None;availability=[]
 for u in updates:
  f=u['file'] if Path(u['file']).exists() else bycopy.get((u['frame_id'],u['sim_s']));availability.append(f)
 for k,a in enumerate(apps):
  tick=int(a['tick']);now=tick/72;ci=ctrl[tick];np.testing.assert_allclose(tr['pose'][tick],a['pose'],atol=1e-9,rtol=0)
  vw=tr['vw'][tick];i=int(np.searchsorted(pub,ci['monotonic_ns'],side='right'))-1;assert i>=0
  j=i
  while j>=0 and availability[j] is None:j-=1
  assert j>=0;file=availability[j];exact=i==j
  if file!=last_file:register(file);field=Snapshot.load(file);last_file=file
  tload=time.perf_counter();result=certify(a['pose'],vw,a['path_world'],field,return_trace=True);trajectory=result.pop('trajectory',None)
  valid_path=trajectory is not None
  if trajectory is None:
   # A timed H rotation may have zero XY length. Frozen NA cannot construct
   # that path: retain explicit INVALID_INPUT rejection and no model samples.
   trajectory=dict(poses=np.asarray([a['pose']]),commands=np.empty((0,2)))
   result.update(duration_s=0.,endpoint_reached=False,alignment=False,clearance_m=None)

  exposed_end=apps[k+1]['simulation_time_s'] if k+1<len(apps) else float(tr['t'][-1]);limit=min(exposed_end,float(tr['t'][-1]),now+result['duration_s'])
  # Fixed-path executor validation stops at the first external intervention.
  # C0's20/45deg policy and H timed follower remain in the inclusive population
  # and are separately identified, never silently forced to match NA.
  boundary_reason='NEXT_PATH_OR_RUN_END_OR_HORIZON'
  for c in commands:
   if c['time_s']<now-1e-8 or c['time_s']>=limit-1e-9:continue
   if c['source'] not in ('NORMAL','REPAIR','DETOUR','ALIGN_BRAKE','ALIGN_ROTATE'):
    limit=c['time_s'];boundary_reason=c['source'];break
  n=max(0,min(len(trajectory['poses'])-1,int(round((limit-now)*72))))
  pe=np.linalg.norm(trajectory['poses'][1:n+1,:2]-tr['pose'][tick+1:tick+n+1,:2],axis=1)
  identical=r['method']!='C0' and a['kind']!='HANDOFF'
  errors.extend(pe.tolist())
  if identical:same_errors.extend(pe.tolist())
  state='R2' if a['kind']=='REPAIR' else 'R3' if a['kind']=='DETOUR' else 'NORMAL'
  collision_event=bool(r['collision'] and k==len(apps)-1)
  row=dict(uid=r['uid'],event_index=k,event_key=f"{r['uid']}:{k}",method=r['method'],variant=r['variant'],scene=r['scene'],index=r['index'],state=state,kind=a['kind'],install_s=now,id=a['id'],
   pose=a['pose'],actual_vw=vw.tolist(),source_logged_previous_vw=a['previous_vw'],collision_event=collision_event,box_positive=box_positive and collision_event,
   exact_install_map=exact,map_scope='LATEST_PUBLISHED' if exact else 'OLDER_ARCHIVE_PROXY',requested_frame=updates[i]['frame_id'],used_frame=updates[j]['frame_id'],snapshot_file=file,
   snapshot_age_s=now-updates[j]['sim_s'],extra_archive_staleness_s=updates[i]['sim_s']-updates[j]['sim_s'],latest_update_s=updates[i]['sim_s'],
   valid_na_input_path=valid_path,disposition=('PASS' if result['passed'] else 'REJECT') if exact else 'MISSING_LATEST_MAP',proxy_disposition='PASS' if result['passed'] else 'REJECT',**result,
   valid_actual_ticks=n,compared_actual_s=n/72,comparison_end_reason=boundary_reason,same_executor=identical,
   position_error_p50_m=float(np.median(pe)) if n else None,position_error_p95_m=float(np.quantile(pe,.95)) if n else None,position_error_max_m=float(pe.max()) if n else None,
   observation_exposure_s=exposed_end-now,collision_delay_s=float(tr['t'][-1])-now if collision_event else None,output=str(root))
  rows.append(row)
  if (row['box_positive'] or (not result['passed'] and len(examples)<2)):
   examples.append(dict(event_key=row['event_key'],path=a['path_world'],predicted_poses=trajectory['poses'],actual_poses=tr['pose'][tick:tick+n+1].tolist(),actual_times=tr['t'][tick:tick+n+1].tolist(),input_field=file))
  if exact and not collision_event and not result['passed']:
   slow=certify(a['pose'],vw,a['path_world'],field,speed_cap=.1);e=evt.get(a['id']);safe_tests=[];safe_count=0
   if e is not None:
    worlds=np.array([local_to_world(p,e['observation_pose']) for p in e['overnight_metric_samples']]);_,selection=evaluate_samples(worlds,a['pose'],field)
    original_selected=e.get('phase16',{}).get('selection',{}).get('selected_sample')
    for c in selection['candidates']:
     if c['safe'] and c['index']!=original_selected:
      safe_count+=1;cr=certify(a['pose'],vw,worlds[c['index']],field);safe_tests.append(dict(index=c['index'],**cr))
   jobs,paths=stored_r3_alternatives(root,detours,a,now,field);r3_tests=[certify(a['pose'],vw,path,field) for path in paths]
   ar=dict(event_key=row['event_key'],uid=r['uid'],method=r['method'],state=state,other_safe_available_input=e is not None,other_safe_candidate_count=safe_count,
    other_safe_pass=any(c['passed'] for c in safe_tests),slowdown_pass=slow['passed'],slowdown_clearance_m=slow.get('clearance_m'),
    r3_status='ASSESSED_STORED_SAME_BOUNDARY' if jobs else 'UNASSESSED_NO_STORED_JOB',r3_job_count=jobs,r3_other_accepted_paths=len(paths),r3_pass=any(c['passed'] for c in r3_tests) if jobs else None,
    any_measured_alternative_pass=slow['passed'] or any(c['passed'] for c in safe_tests+r3_tests),safe_results=safe_tests,r3_results=r3_tests)
   alt.append(ar)
 save(OUT/'per_run'/f"{r['uid']}.json",dict(events=rows,alternatives=alt,examples=examples))
 np.savez_compressed(OUT/'per_run'/f"{r['uid']}_errors.npz",all_errors=np.array(errors),same_executor_errors=np.array(same_errors))
 return len(rows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--limit-runs',type=int);a=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True);(OUT/'per_run').mkdir(exist_ok=True)
 protocol=read(Path(__file__).with_name('protocol.json'))
 for f,h in protocol['source_hashes'].items():assert hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,f
 runs=read(ROOT/'research/results/phase31d/runs.json');assert len(runs)==160
 if a.limit_runs:runs=runs[:a.limit_runs]
 started=time.time();done=0
 # Warm import and NumPy dispatch on a synthetic map; no research input tuned.
 from .test_exec_cert import field
 for _ in range(10):certify([0,0,0],[0,0],[[0,0],[1,0]],field([.5,.5]))
 for ri,r in enumerate(runs):
  file=OUT/'per_run'/f"{r['uid']}.json"
  if file.exists():
   cached=json.loads(file.read_text());n=len(cached['events']);root=Path(r['output'])
   for filename in ['agent_trajectory.csv','repair.jsonl','phase20_commands.jsonl','controller.jsonl','depth/updates.jsonl','events.jsonl','detour.jsonl']:
    if (root/filename).exists():register(root/filename)
   for event in cached['events']:register(event['snapshot_file'])
   restored_maps(root)
  else:
   try:n=run_one(r)
   except BaseException as exc:
    save(OUT/'status.json',dict(status='FAILED',last=r['uid'],error=repr(exc),runs_done=ri,elapsed_s=time.time()-started))
    save(OUT/'input_manifest.json',[dict(file=f,sha256=h) for f,h in sorted(MANIFEST.items())]);raise
  done+=n;save(OUT/'status.json',dict(status='RUNNING',runs_done=ri+1,runs_total=len(runs),events=done,elapsed_s=time.time()-started,last=r['uid']))
  print(f'[{ri+1}/{len(runs)}] {r["uid"]} {n} events; elapsed {time.time()-started:.1f}s',flush=True)
 previous=OUT/'input_manifest.json';old={x['file']:x['sha256'] for x in json.loads(previous.read_text())} if previous.exists() else {};old.update(MANIFEST)
 save(previous,[dict(file=f,sha256=h) for f,h in sorted(old.items())]);save(OUT/'status.json',dict(status='COMPLETE' if len(runs)==160 else 'PARTIAL',runs_done=len(runs),events=done,elapsed_s=time.time()-started))
if __name__=='__main__':main()
