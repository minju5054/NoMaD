"""Read-only inputs; one preregistered offline analysis with preserved journals."""
import argparse,csv,json,subprocess,time
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,local_to_world
from nomad_phase0.chunk_report import trace
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase15b.depth import Snapshot
from nomad_phase16.geometry import path_safety
from nomad_phase12.methods import hermite_splice
from .speed_profile import curvature_after
from .rollout import rollout
from .graph_k import solve

HERE=ROOT/'research/nomad_phase18d';OUT=ROOT/'research/results/phase18d'
SAFE='FRESHEST-SAFE';HERMITE=SAFE+'+HERMITE';DEPTH=SAFE+'+GRAPH-depth';CLR=DEPTH+'-CLR'
PATHS=('FRESHEST-SAFE','HERMITE','CLR','K','KP');SPEEDS=('CURV','SP')

def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,np.generic):return clean(x.item())
    if isinstance(x,float) and not np.isfinite(x):return None
    return x
def dump(path,x):
    with Path(path).open('x') as f:json.dump(clean(x),f,indent=2,allow_nan=False);f.write('\n')
def csv_write(path,records):
    keys=list(dict.fromkeys(k for r in records for k in r))
    with Path(path).open('x',newline='') as f:
        w=csv.DictWriter(f,keys);w.writeheader()
        for r in records:w.writerow({k:json.dumps(clean(v)) if isinstance(v,(dict,list,tuple)) else clean(v) for k,v in r.items()})
def rows(path):return [json.loads(l) for l in Path(path).read_text().splitlines() if l] if Path(path).exists() else []
def stats(x):
    x=[v for v in x if v is not None and np.isfinite(v)]
    return dict(n=len(x),median=float(np.median(x)) if x else None,p10=float(np.quantile(x,.1)) if x else None,p90=float(np.quantile(x,.9)) if x else None,p95=float(np.quantile(x,.95)) if x else None)
def gap(path,c):
    s=path_safety(np.asarray(path),c)
    return min(s['obstacle_clearance_m'],s['corridor_clearance_m']),s['corridor_clearance_m']
def curve_ratio(raw,path,B):
    a=curvature_after(raw,B);b=curvature_after(path,B)
    return dict(native_kappa_max=a['max_abs'],path_kappa_max=b['max_abs'],turn=a['turn'],
        curvature_ratio=b['max_abs']/a['max_abs'] if a['max_abs'] is not None and a['max_abs']>1e-12 and b['max_abs'] is not None else None,
        dominant_sign_agrees=a['dominant_sign']==b['dominant_sign'] if a['dominant_sign'] is not None and b['dominant_sign'] is not None else None)

class Inputs:
    def __init__(self):self.hashes={};self.cache={}
    def track(self,path,expected=None):
        p=Path(path).resolve();key=str(p)
        if key not in self.hashes:self.hashes[key]=sha256_file(p)
        if expected:assert self.hashes[key]==expected,p
        return p
    def field(self,path):return Snapshot.load(self.track(path))
    def load(self,r):
        if r['key'] in self.cache:return self.cache[r['key']]
        run=Path(r['output']);d=dict(record=r,run=run)
        for name,h in r.get('input_sha256',{}).items():self.track(run/name,h)
        d['config']=json.loads(self.track(run/'scenario.json').read_text())
        for name,file in [('events','events.jsonl'),('controls','controller.jsonl'),('apps','phase16_applications.jsonl'),('graphs','stage2_graph.jsonl'),('gaps','clearance.jsonl')]:d[name]=rows(self.track(run/file))
        self.track(run/'agent_trajectory.csv');d['trace'],d['poses']=trace(run)
        d['events_by_id']={e['id']:e for e in d['events']}
        d['jobs']={j['job_id']:j for j in d['graphs'] if j['event']=='SUBMIT'}
        d['jobs_by_id']={j['id']:j for j in d['jobs'].values()}
        d['results']={j['job_id']:j for j in d['graphs'] if j['event']=='RESULT'}
        d['v']=np.array([float(x['v_m_s']) for x in d['trace']]);d['w']=np.array([float(x['w_rad_s']) for x in d['trace']])
        self.cache[r['key']]=d;return d
    def native(self,d,e):
        file=self.track(d['run']/f"model/derived/{e['id']:04d}.npz")
        with np.load(file) as z:metric=z['metric'].copy()
        np.testing.assert_array_equal(metric,e['overnight_metric_samples'])
        selection=e.get('phase16',{}).get('selection')
        if selection is None:return None
        return local_to_world(metric[selection['selected_sample']],e['observation_pose'])

def regression(records,inputs):
    candidates=[]
    for record in sorted(records,key=lambda r:r['key']):
        if record['technical_validation']!='PASS' or 'TEMPORAL-ENSEMBLE' in record['method']:continue
        d=inputs.load(record);terminal=len(d['poses'])-1
        for i,a in enumerate(d['apps']):
            if a['kind'] not in ('NORMAL','GRAPH') or not a.get('world_xy'):continue
            start=a['tick'];end=min(start+108,terminal,d['apps'][i+1]['tick'] if i+1<len(d['apps']) else terminal)
            if end-start<8:continue
            for tick in range(start,end,8):
                c=d['controls'][tick//8]
                if not c['valid'] or c['pure_pursuit']['stop_reason'] is not None or c.get('phase16_fallback_mode') not in ('NORMAL','KEEP_ACTIVE'):
                    end=tick;break
            if end-start>=8:candidates.append((record['key'],i,start,end))
    assert len(candidates)>=20
    selected=np.random.default_rng(20261031).choice(len(candidates),20,replace=False);out=[]
    for n in selected:
        key,i,start,end=candidates[n];d=inputs.cache[key];a=d['apps'][i]
        result=rollout(a['pose'],a['world_xy'],a['before_vw'][0],'CURV',d['config'],ticks=end-start)
        count=min(len(result['poses']),end-start+1)
        error=float(np.linalg.norm(result['poses'][:count,:2]-d['poses'][start:start+count,:2],axis=1).max())
        yaw=float(np.max(np.abs((result['poses'][:count,2]-d['poses'][start:start+count,2]+np.pi)%(2*np.pi)-np.pi)))
        out.append(dict(run=key,application_index=i,start_tick=start,end_tick=end,kind=a['kind'],actual_ticks=end-start,rollout_ticks=len(result['poses'])-1,
                        maximum_position_error_m=error,maximum_yaw_error_rad=yaw,complete_comparison=count==end-start+1,termination=result['termination']))
    return out,dict(candidate_segments=len(candidates),sample_seed=20261031,segments=20,
        maximum_position_error_m=max(r['maximum_position_error_m'] for r in out),
        complete_segments=sum(r['complete_comparison'] for r in out),
        label='ROLLOUT_VALID' if max(r['maximum_position_error_m'] for r in out)<=.01 and all(r['complete_comparison'] for r in out) else 'ROLLOUT_APPROXIMATE')

def execution_metrics(d,start,end):
    end=min(end,len(d['poses'])-1);idx=np.arange(start+1,end+1);ctes=[];apps=d['apps'];app_ticks=[a['tick'] for a in apps]
    for tick in idx:
        control=d['controls'][(tick-1)//8]
        if control.get('phase16_fallback_mode') not in ('NORMAL','KEEP_ACTIVE'):continue
        j=np.searchsorted(app_ticks,tick-1,side='right')-1
        if j>=0 and apps[j].get('world_xy'):ctes.append(XYPath(apps[j]['world_xy']).project(d['poses'][tick,:2])[1])
    gs=d['gaps'][start+1:end+1];k=[abs(c['stage2']['kappa_pp']) for c in d['controls'][start//8:(end+7)//8] if c.get('stage2',{}).get('kappa_pp') is not None]
    return dict(mean_speed_m_s=float(np.mean(d['v'][idx])) if len(idx) else 0.,omega_saturation_fraction=float(np.mean(np.abs(d['w'][idx])>=.399)) if len(idx) else 0.,
        max_cross_track_m=max(ctes,default=None),minimum_obstacle_clearance_m=min((g['lower_m'] for g in gs),default=None),
        minimum_wall_clearance_m=min((g['corridor_lower_m'] for g in gs),default=None),pp_curvature_median=float(np.median(k)) if k else None,
        duration_s=(end-start)/72)

def active_path(d,tick):
    control=d['controls'][min((tick-1)//8,len(d['controls'])-1)]
    if control.get('phase16_fallback_mode') not in ('NORMAL','KEEP_ACTIVE'):return None
    return next((a for a in reversed(d['apps']) if a['tick']<tick and a.get('world_xy')),None)

def cause(r):
    ratio=r.get('curvature_ratio')
    if r.get('turn') and ratio is not None and ratio<.8:return 'UNDERTURN_PATH'
    if r.get('turn') and ratio is not None and ratio>=.8 and r.get('omega_saturation_fraction',0)>=.5 and r.get('mean_speed_m_s',0)>.4/r['native_kappa_max']:return 'UNDERTURN_EXECUTION'
    if r.get('clearance_push_evidence'):return 'CLEARANCE_PUSH'
    return 'OTHER'

def same_box_safe(d,record,inputs,records,x):
    boxes=d['config']['obstacles'];box=min(boxes,key=lambda b:abs(x-b['center_xy_m'][0]));lo=box['center_xy_m'][0]-box['size_xyz_m'][0]/2-.30;hi=box['center_xy_m'][0]+box['size_xyz_m'][0]/2+.30
    match=next(r for r in records if r['scene']=='SLW' and r['index']==record['index'] and r['method']==SAFE);other=inputs.load(match)
    ticks=np.flatnonzero((other['poses'][:,0]>=lo)&(other['poses'][:,0]<=hi))
    detail=dict(box=box['id'],x_band_m=[lo,hi],safe_run=match['key'])
    if not len(ticks):return {**detail,'available':False}
    first=ticks[0];stop=next((t for t in range(first+1,len(other['poses'])) if not lo<=other['poses'][t,0]<=hi),len(other['poses'])-1)
    return dict(**detail,available=True,start_s=first/72,end_s=stop/72,**execution_metrics(other,int(first),int(stop)))

def compact_rollout(r):return {k:v for k,v in r.items() if k not in ('poses','commands','speeds','omegas','profile')}

def attribution(records,inputs,journal):
    output=[];lookup={}
    for record in sorted(records,key=lambda r:r['key']):
        if record['scene']!='SLW' or record['method'] not in (DEPTH,CLR) or record['success']:continue
        d=inputs.load(record)
        if not d['jobs']:continue
        job=max(d['jobs'].values(),key=lambda j:j['switch_sim_s']);field=inputs.field(job['depth_snapshot']['file'])
        assert field.metadata['publication_monotonic_ns']<=job['dispatch_ns']
        assert field.metadata['sim_s']<=job['switch_sim_s']
        saved=d['results'].get(job['job_id']);case=[]
        for variant in ('CLR','NO_PROGRESS','NO_CLEARANCE','NO_BOTH'):
            result=solve(job,field,variant);journal.write(json.dumps(clean(dict(section='A',run=record['key'],job_id=job['job_id'],variant=variant,**result)))+'\n');journal.flush()
            row=dict(run=record['key'],source_method=record['method'],index=record['index'],job_id=job['job_id'],fresh_id=job['id'],variant=variant,
                disposition=result['disposition'],accepted=result['accepted'],solve_wall_s=result['solve_wall_s'],B=job['boundary'],selected_path=job['world_xy'])
            row['factor_costs']=result.get('solver',{}).get('factor_costs')
            if result['poses'] is not None:
                path=np.array(result['poses'])[:,:2];g,w=gap(path,d['config'])
                row.update(**curve_ratio(job['world_xy'],path,job['boundary']),path_oracle_clearance_m=g,path_wall_clearance_m=w,path=path.tolist())
            if result['accepted']:
                r=rollout(job['boundary'],path,job['previous_command'][0],'CURV',d['config'])
                row.update({'rollout_'+k:v for k,v in compact_rollout(r).items()})
            if variant=='CLR' and record['method']==CLR:
                comparable=saved is not None and saved.get('poses') is not None and result['poses'] is not None
                row['stored_regression_available']=comparable
                row['stored_regression_path_error_m']=float(np.max(np.linalg.norm(np.array(saved['poses'])[:,:2]-np.array(result['poses'])[:,:2],axis=1))) if comparable else None
                row['stored_regression_acceptance_match']=saved['accepted']==result['accepted'] if saved else None
            output.append(row);case.append(row)
        lookup[record['key']]=case
    return output,lookup

def analyze_A(records,inputs,terms):
    output=[];run_rows=[]
    for record in sorted(records,key=lambda r:r['key']):
        if record['scene']!='SLW' or record['method'] not in (SAFE,HERMITE,DEPTH,CLR) or record['success']:continue
        d=inputs.load(record);terminal=len(d['poses'])-1
        for e in d['events'][-3:]:
            start=round(e['application_sim_s']*72);following=[round(x['application_sim_s']*72) for x in d['events'] if x['application_sim_s']>e['application_sim_s']];end=min(following,default=terminal)
            a=active_path(d,end);raw=None;path=None;source=None
            if a:
                source=d['events_by_id'].get(a.get('path_source_id',a['id']));raw=inputs.native(d,source) if source else None
                path=a['world_xy']
            row=dict(row_type='FRESH',run=record['key'],method=record['method'],index=record['index'],classification=record['classification'],termination=record['termination_reason'],
                id=e['id'],start_s=start/72,end_s=end/72,B=e['agent_pose_at_switch'],fallback=e.get('phase16',{}).get('fallback_mode','RECOVERY_DEFERRED'),
                path_kind=a['kind'] if a else 'NO_PATH_TRACKING',active_graph_job=a.get('graph_job_id') if a else None,
                raw=raw.tolist() if raw is not None else None,path=path,**execution_metrics(d,start,end),
                safe_same_box=same_box_safe(d,record,inputs,records,e['agent_pose_at_switch'][0]))
            if raw is not None and path is not None:row.update(curve_ratio(raw,path,source['agent_pose_at_switch']))
            output.append(row)
        a=active_path(d,terminal)
        final=dict(row_type='FINAL_CAUSE',run=record['key'],method=record['method'],index=record['index'],classification=record['classification'],termination=record['termination_reason'],
            final_pose=d['poses'][-1].tolist(),path_kind=a['kind'] if a else 'NO_PATH_TRACKING',clearance_push_evidence=False)
        if a:
            source=d['events_by_id'].get(a.get('path_source_id',a['id']));raw=inputs.native(d,source) if source else None
            if raw is not None:
                final.update(**curve_ratio(raw,a['world_xy'],source['agent_pose_at_switch']),**execution_metrics(d,a['tick'],terminal),
                    B=source['agent_pose_at_switch'],raw=raw.tolist(),path=a['world_xy'],active_graph_job=a.get('graph_job_id'),source_id=source['id'])
                off=next((x for x in terms.get(record['key'],[]) if x['variant']=='NO_CLEARANCE'),None)
                if record['method']==CLR and a['kind']=='GRAPH' and off and off['job_id']==a['graph_job_id'] and off['accepted']:
                    wall=gap(a['world_xy'],d['config'])[1];final['clearance_off_wall_gain_m']=off['path_wall_clearance_m']-wall
                    final['clearance_push_evidence']=final['clearance_off_wall_gain_m']>=.02
        final['label']=cause(final);run_rows.append(final);output.append(final)
    return output,run_rows

def combinations(records,inputs,journal,out):
    data=[];solves=[];plot_data=None;count=0
    target=[r for r in records if r['scene'] in ('SLW','CL') and r['method']==CLR]
    for record in sorted(target,key=lambda r:r['key']):
        d=inputs.load(record)
        for event in d['events']:
            B=np.array(event['agent_pose_at_switch']);job=d['jobs_by_id'].get(event['id']);mode=event.get('phase16',{}).get('fallback_mode','RECOVERY_DEFERRED')
            identity=dict(run=record['key'],scene=record['scene'],index=record['index'],fresh_id=event['id'],B=B.tolist(),mode=mode)
            paths={};status={};gresults={};raw=inputs.native(d,event)
            if job is not None:
                assert mode=='NORMAL' and raw is not None
                np.testing.assert_allclose(raw,job['world_xy'],atol=1e-12,rtol=0);np.testing.assert_array_equal(B,job['boundary'])
                paths['FRESHEST-SAFE']=raw;status['FRESHEST-SAFE']='AVAILABLE'
                try:paths['HERMITE']=hermite_splice(raw,B)[0];status['HERMITE']='AVAILABLE'
                except ValueError as exc:status['HERMITE']='DEGENERATE_HERMITE: '+str(exc)
                saved=d['results'].get(job['job_id'])
                if saved is not None:
                    gresults['CLR']=dict(accepted=bool(saved.get('accepted')),disposition=saved['disposition'],poses=saved.get('poses'),
                        solve_wall_s=saved.get('solver',{}).get('solve_and_certificate_wall_s'),solver=saved.get('solver'))
                else:gresults['CLR']=dict(accepted=None,disposition='MISSING_STORED_WORKER_RESULT',poses=None,solve_wall_s=None)
                field=inputs.field(job['depth_snapshot']['file'])
                assert field.metadata['publication_monotonic_ns']<=job['dispatch_ns']
                assert field.metadata['sim_s']<=job['switch_sim_s']
                for variant in ('K','KP'):
                    result=solve(job,field,variant);gresults[variant]=result
                    journal.write(json.dumps(clean(dict(section='B',**identity,job_id=job['job_id'],variant=variant,**result)))+'\n');journal.flush()
                for variant,result in gresults.items():
                    if result['accepted'] and result['poses'] is not None:paths[variant]=np.array(result['poses'])[:,:2];status[variant]='AVAILABLE'
                    else:status[variant]=result['disposition']
                    solves.append(dict(**identity,variant=variant,job_id=job['job_id'],accepted=result['accepted'],disposition=result['disposition'],
                        solve_wall_s=result['solve_wall_s'],solver_started=result.get('solver') is not None,progress_removed=result.get('progress_removed')))
                previous_v=job['previous_command'][0]
            else:
                previous_v=None
                status={name:'NO_GRAPH_INPUT_'+mode for name in PATHS}
            common=all(name in paths for name in PATHS)
            case_results={}
            for name in PATHS:
                for speed in SPEEDS:
                    row={**identity,'path_type':name,'speed':speed,'common_eligible':common,'available':name in paths,'availability':status.get(name,'MISSING'),
                         'accepted':gresults[name]['accepted'] if name in gresults else None}
                    if name in paths:
                        result=rollout(B,paths[name],previous_v,speed,d['config']);case_results[name,speed]=result
                        row.update(compact_rollout(result),**curve_ratio(raw,paths[name],B))
                    data.append(row)
            if plot_data is None and record['scene']=='SLW' and common and curvature_after(raw,B)['turn']:
                # Prespecified first eligible turning event; independent of outcomes.
                plot_data=dict(**identity,path=paths['CLR'].tolist(),CURV=clean(case_results['CLR','CURV']),SP=clean(case_results['CLR','SP']))
            count+=1
            if count%40==0:print(f'[offline] {count}/569 FRESH recorded',flush=True)
    if plot_data is not None:dump(out/'speed_example.json',plot_data)
    return data,solves

def summarize_combos(data,solves,rule):
    primary=[];available=[]
    for scene in ('SLW','CL'):
        for path in PATHS:
            for speed in SPEEDS:
                for common,destination in ((True,primary),(False,available)):
                    rr=[r for r in data if r['scene']==scene and r['path_type']==path and r['speed']==speed and r['available'] and (r['common_eligible'] or not common)]
                    destination.append(dict(scene=scene,path_type=path,speed=speed,n=len(rr),scope='ALL_PATHS_COMMON_VALID' if common else 'METHOD_AVAILABLE_DESCRIPTIVE',
                        overlap=sum(r['overlap'] for r in rr),negative_witness=sum(r['geometric_negative_witness'] for r in rr),conservative_only_negative=sum(r['conservative_only_negative'] for r in rr),
                        margin_violation=sum(r['margin_violation'] for r in rr),mean_progress_m=float(np.mean([r['distance_m'] for r in rr])) if rr else None,
                        mean_speed_m_s=float(np.mean([r['average_speed_m_s'] for r in rr])) if rr else None,
                        omega_saturation_fraction=float(np.mean([r['omega_saturation_fraction'] for r in rr])) if rr else None,
                        maximum_cross_track_m=max((r['max_cross_track_m'] for r in rr),default=None),endpoint_stops=sum(r['endpoint_stop'] for r in rr),
                        curvature_ratio=stats([r.get('curvature_ratio') for r in rr if r.get('turn')]),minimum_clearance_m=min((r['minimum_clearance_m'] for r in rr),default=None)))
    graph=[]
    for variant in ('CLR','K','KP'):
        rr=[r for r in solves if r['variant']==variant];known=[r for r in rr if r['accepted'] is not None];accept=sum(bool(r['accepted']) for r in known)
        graph.append(dict(variant=variant,attempts=len(rr),known=len(known),accepted=accept,acceptance_lower=accept/len(rr),acceptance_upper=(accept+len(rr)-len(known))/len(rr),
            solve_time_s=stats([r['solve_wall_s'] for r in rr]),started_solve_time_s=stats([r['solve_wall_s'] for r in rr if r['solver_started']]),
            dispositions=dict(Counter(r['disposition'] for r in rr))))
    lookup={(r['scene'],r['path_type'],r['speed']):r for r in primary};gs={r['variant']:r for r in graph};base=lookup['SLW','FRESHEST-SAFE','CURV']
    eligible=[];checks=[]
    names=('CLR','K','KP') if rule['candidate_scope']=='GRAPH_ONLY' else PATHS
    for name in names:
        for speed in SPEEDS:
            a,b=lookup['SLW',name,speed],lookup['CL',name,speed]
            safety=a['n']>0 and a['overlap']<=base['overlap'];timing=acceptance=True
            if name in gs:
                q=gs[name];p95=q['started_solve_time_s']['p95']
                timing=p95 is not None and p95<=.20
                acceptance=name=='CLR' or gs['CLR']['acceptance_upper']-q['acceptance_lower']<.10
            row=dict(path_type=name,speed=speed,safety_pass=safety,timing_pass=timing,acceptance_pass=acceptance,slw_overlap=a['overlap'],slw_n=a['n'],cl_progress_m=b['mean_progress_m'],cl_n=b['n'])
            checks.append(row)
            if safety and timing and acceptance and b['n']>0:eligible.append(row)
    order={'KP':4,'K':3,'CLR':2,'HERMITE':1,'FRESHEST-SAFE':0}
    chosen=max(eligible,key=lambda r:(r['cl_progress_m'],order[r['path_type']],r['speed']=='SP')) if eligible else None
    selection=dict(label=f"CANDIDATE_{chosen['path_type']}_{chosen['speed']}" if chosen else 'NO_CANDIDATE',chosen=chosen,checks=checks,
        reference_slw_overlap=base['overlap'],reference_slw_n=base['n'],SP_FAIRNESS=[lookup[sc,name,'SP'] for name in ('FRESHEST-SAFE','HERMITE') for sc in ('SLW','CL')],
        same_data_selection=True,closed_loop_claim=False,acceptance_missing_baseline='conservative upper bound',scope='Common accepted-path intersection; unavailable/rejected events retained and acceptance rates use all submitted jobs')
    return primary+available,graph,selection

def run(out):
    assert not out.exists(),'Existing offline attempt preserved; do not restart solves'
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).strip(),'Commit code/protocol before execution'
    protocol=json.loads((HERE/'protocol.json').read_text());inputs=Inputs()
    source=inputs.track(ROOT/'research/results/phase18/runs.json');records=json.loads(source.read_text())
    assert len(records)==144 and all(Path(r['output']).parent==ROOT.parent/'artifacts/isaac6/phase18_confirm_01/main' for r in records)
    for file,h in protocol['protected_sha256'].items():inputs.track(ROOT/file,h)
    for file in HERE.glob('*.py'):inputs.track(file)
    inputs.track(HERE/'protocol.json');sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    out.mkdir(parents=True);dump(out/'protocol.json',protocol)
    regression_rows,reg=regression(records,inputs);csv_write(out/'rollout_regression.csv',regression_rows)
    print(f"[regression] {reg['label']}: max position error {reg['maximum_position_error_m']:.9g} m; {reg['complete_segments']}/20 complete",flush=True)
    with (out/'solve_results.jsonl').open('x') as journal:
        terms,term_lookup=attribution(records,inputs,journal)
        print(f'[attribution] {len(terms)} fixed attempts',flush=True)
        failures,final=analyze_A(records,inputs,term_lookup)
        combos,solves=combinations(records,inputs,journal,out)
    combo_summary,graph_summary,selection=summarize_combos(combos,solves,protocol['selection'])
    coverage=[]
    for sc in ('SLW','CL'):
        event_rows=[r for r in combos if r['scene']==sc and r['path_type']=='CLR' and r['speed']=='CURV']
        coverage.append(dict(scene=sc,all_fresh=len(event_rows),common_valid=sum(r['common_eligible'] for r in event_rows),availability=dict(Counter(r['availability'] for r in event_rows))))
    assert sum(r['all_fresh'] for r in coverage)==569
    contributions=[]
    for variant in ('NO_PROGRESS','NO_CLEARANCE','NO_BOTH'):
        pairs=[]
        for run,rr in term_lookup.items():
            a=next(x for x in rr if x['variant']=='CLR');b=next(x for x in rr if x['variant']==variant)
            if a['accepted'] and b['accepted'] and a.get('turn') and a.get('curvature_ratio') is not None and b.get('curvature_ratio') is not None:
                pairs.append(dict(run=run,ratio_change=b['curvature_ratio']-a['curvature_ratio'],overlap_change=int(b['rollout_overlap'])-int(a['rollout_overlap'])))
        contributions.append(dict(variant=variant,paired_n=len(pairs),ratio_change=stats([r['ratio_change'] for r in pairs]),overlap_change=sum(r['overlap_change'] for r in pairs)))
    summary=dict(git_sha=sha,protocol=protocol,regression=reg,regression_rows=regression_rows,A_labels=dict(Counter(r['label'] for r in final)),
        A_by_method={m:dict(Counter(r['label'] for r in final if r['method']==m)) for m in (SAFE,HERMITE,DEPTH,CLR)},
        term_contributions=contributions,coverage=coverage,graph_summary=graph_summary,selection=selection,
        approximation=reg['label']!='ROLLOUT_VALID',scope='Offline fixed-path same-data selection, not closed-loop navigation improvement')
    for name,data in [('slw_failures',failures),('term_attribution',terms),('combos',combos),('combo_summary',combo_summary),('graph_summary',graph_summary),('graph_jobs',solves)]:csv_write(out/f'{name}.csv',data)
    dump(out/'selection.json',selection);dump(out/'summary.json',summary);dump(out/'input_manifest.json',dict(git_sha=sha,sha256=inputs.hashes))
    from .report import render
    render(out,summary,inputs,failures,terms,combo_summary,selection)
    for file,h in inputs.hashes.items():assert sha256_file(file)==h,file
    dump(out/'complete.json',dict(completed=True,graph_attempts=len(terms)+sum(r['variant'] in ('K','KP') for r in solves),input_hashes_unchanged=True,Isaac_navigation=0,NoMaD_inference=0,render=0))
    print(json.dumps(dict(regression=reg['label'],A=summary['A_labels'],candidate=selection['label'])),flush=True)

def publish(out):
    assert (out/'complete.json').exists()
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    paths=['research/nomad_phase18d',str(out.relative_to(ROOT)),'docs/PHASE18D_CURVATURE.md']
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    png=list(out.glob('*.png'))
    if png:subprocess.run(['git','add','-f','--',*[str(p.relative_to(ROOT)) for p in png]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase18D fixed-path curvature and speed-plan diagnosis'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--publish',action='store_true');a=p.parse_args()
    if OUT.exists():assert (OUT/'complete.json').exists(),'Partial result preserved; no automatic restart'
    else:run(OUT)
    if a.publish:publish(OUT)

if __name__=='__main__':main()
