"""One frozen offline campaign; no renderer, policy, navigation, or retries."""
import argparse
import copy
import csv
import json
import subprocess
import time
from collections import Counter
from pathlib import Path

import numpy as np
from nomad_isaac.common import ROOT, local_to_world, sha256_file
from nomad_isaac.handoff_audit import path_safety
from nomad_phase0.chunk_report import trace
from nomad_phase0.graph_v4 import menger
from nomad_phase0.graph_v2 import fixed_entry
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase12.graph_gf import GraphGF, graph_protocol
from nomad_phase15.evaluate import suffix, sample_path, oracle_clearance
from nomad_phase15b.depth import Snapshot
from nomad_phase15b.graph import DepthGraph

OUT = ROOT/'research/results/phase15c'
DEPTH = 'FRESHEST-SAFE+GRAPH-depth'
GF = 'FRESHEST-SAFE+GRAPH-GF'
VARIANTS = ('NEITHER', 'CERT_ONLY', 'CONSTRAINT_ONLY', 'FULL')
SIGMAS = {f'{group}_x{factor:g}': {group:factor}
          for group in ('prior', 'relative', 'boundary') for factor in (.5, 2.)}
SIGMAS.update({f'all_x{factor:g}': {g:factor for g in ('prior','relative','boundary')} for factor in (.5,2.)})
RULES = dict(expected_jobs={DEPTH:209, GF:460}, safety_m=.025, path_match_m=1e-6,
    variants=VARIANTS, sigma_variants=SIGMAS, sigma_path_statistic='median of per-job median point distances; all pairs with finite returned iterates, including rejected iterates; accepted-only also reported',
    sigma_acceptance='absolute change in fraction accepted; all 209 jobs including initialization rejections',
    certificate_tolerance_m=1e-8,
    regression='A FULL/NEITHER baseline solve reused for depth/GF regression; stored scheduling dispositions retained separately; no new wall-time deadline imposed offline',
    ablation_label_priority=['NO_DANGEROUS_CORRECTIONS (<5)', 'CONSTRAINT_MATTERS', 'CERTIFICATE_SUFFICES', 'MIXED'],
    wall_scope='last three FRESH switches, all replacement applications within them, and final active application; full and B-suffix path metrics; exact stop-site wall cell plus 2-cell neighborhood diagnostics',
    wall_site_band_m=.10, wall_unknown_rule='exact nearest wall cell in latest snapshot published by stop timestamp; neighborhood status also reported',
    detour_window_s=5., detour_rule='first x < running_max_x - .30; otherwise first cumulative absolute unwrapped yaw change > 2pi; no interpolation',
    dispersion='population std (ddof=0); scalar is RMS of x/y std, comparable to per-coordinate sigma=.10; radial std and per-axis std also retained',
    oracle='posthoc evaluation only; never passed into any solver', navigation=0, inference=0, render=0,
    retries=0, tuning=0, scope='Offline path-level counterfactuals, not closed-loop or causal performance evidence')


def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def write_csv(path, rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('x', newline='') as f:
        w=csv.DictWriter(f, keys); w.writeheader()
        for r in rows:
            w.writerow({k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()})


def jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l]


def finite(v):
    return float(v) if np.isfinite(v) else None


class ConstraintsOnly(DepthGraph):
    def certificate(self, poses):
        return {'status':'DISABLED_FOR_OFFLINE_ABLATION'}, True


def solve_once(job, field, variant, sigma=None):
    """Only numeric job data + frozen depth; oracle config intentionally absent."""
    started=time.perf_counter()
    args=(job['world_xy'],job['boundary'],job['previous_command'])
    try:
        if variant in ('NEITHER','CERT_ONLY'):
            graph=GraphGF(*args,graph_protocol(),job['previous_xy'])
        else:
            graph=(ConstraintsOnly if variant=='CONSTRAINT_ONLY' else DepthGraph)(*args,field,job['previous_xy'])
        # Sigma changes affect only residual scales; unchanged native initialization,
        # fixed entry, constraints, bounds, and analytic solver are reused.
        graph.p=copy.deepcopy(graph.p)
        for group,factor in (sigma or {}).items():
            for tail in ('xy_m','yaw_deg'):
                graph.p[f'{group}_sigma_{tail}']*=factor
        poses,solver=graph.solve()
        if variant=='CERT_ONLY':
            ok=field.exact_clearance(poses[:,:2])>=.025-1e-8
            solver['exact_certificate_pass']=bool(ok)
            solver['feasible']=bool(solver['feasible'] and ok)
        status='NONCONVERGED' if not solver['success'] else 'CONSTRAINT_FAILED' if not solver['feasible'] else 'ACCEPTED'
        return dict(disposition=status,accepted=bool(solver['feasible']),poses=poses.tolist(),solver=solver,
                    solve_wall_s=time.perf_counter()-started)
    except ValueError as e:
        return dict(disposition='INITIALIZATION_REJECTED',accepted=False,poses=None,error=str(e),solve_wall_s=time.perf_counter()-started)


def numerical_disposition(saved):
    if saved is None or 'accepted' not in saved: return None
    if saved.get('initialization_rejected'): return 'INITIALIZATION_REJECTED'
    if not saved['solver']['success']: return 'NONCONVERGED'
    return 'ACCEPTED' if saved['accepted'] else 'CONSTRAINT_FAILED'


def regression(result, saved):
    status=numerical_disposition(saved)
    if status is None:
        return dict(regression_comparable=False,regression_match=None,regression_reason='TERMINAL_UNAPPLIED: no saved worker result',saved_disposition=saved.get('event') if saved else None)
    a,b=result.get('poses'),saved.get('poses')
    error=float(np.linalg.norm(np.array(a)[:,:2]-np.array(b)[:,:2],axis=1).max()) if a is not None and b is not None else None
    yaw_error=float(np.max(np.abs((np.array(a)[:,2]-np.array(b)[:,2]+np.pi)%(2*np.pi)-np.pi))) if a is not None and b is not None else None
    presence=(a is None)==(b is None)
    match=status==result['disposition'] and presence and (error is None or error<=1e-6)
    logged=saved['disposition']
    effective=logged if logged in ('SUPERSEDED','STALE','WAYPOINT_EXPIRED') else result['disposition']
    return dict(regression_comparable=True,regression_match=bool(match),regression_path_max_error_m=error,
        regression_yaw_max_error_rad=yaw_error,saved_disposition=logged,saved_numerical_disposition=status,
        replay_with_saved_schedule_disposition=effective,regression_schedule_match=effective==logged,
        regression_reason='MATCH' if match else 'NUMERICAL_REPLAY_MISMATCH; identical saved inputs, no tuning or retry; inspect solver status/iterations')


def path_metrics(result, job, field, config):
    p=result.get('poses')
    if p is None:return {}
    xy=np.array(p)[:,:2]; original=np.array(job['world_xy']); b=np.array(job['boundary'])
    forward=np.array([np.cos(b[2]),np.sin(b[2])]); e=fixed_entry(original,b)
    i,j,frac=e['a'],e['b'],e['fraction'];entry=(1-frac)*xy[i]+frac*xy[j]
    # Match frozen graph entry interpolation, including its auxiliary heading.
    heading=(1-frac)*np.array(p)[i,2]+frac*np.array(p)[j,2]
    return dict(depth_clearance_m=finite(field.exact_clearance(xy)),oracle_clearance_m=oracle_clearance(xy,config),
        mean_edit_cm=float(np.linalg.norm(xy-original,axis=1).mean()*100),max_abs_kappa=float(np.abs(menger(xy)[0]).max()),
        endpoint_progress_m=float((xy[-1]-b[:2])@forward),boundary_position_error_m=float(np.linalg.norm(entry-b[:2])),
        boundary_heading_error_deg=float(abs((heading-b[2]+np.pi)%(2*np.pi)-np.pi)*180/np.pi))


def ablation_label(n, recovered, rejected):
    if n<5:return 'NO_DANGEROUS_CORRECTIONS'
    if recovered/n>=.5:return 'CONSTRAINT_MATTERS'
    if rejected/n>=.8:return 'CERTIFICATE_SUFFICES'
    return 'MIXED'


def summarize_ablation(rows):
    output=[]
    for method in ('ALL',DEPTH,GF):
        rr=[r for r in rows if method=='ALL' or r['source_method']==method]
        lookup={(r['run'],r['job_id'],r['variant']):r for r in rr}
        dangerous=[r for r in rr if r['variant']=='NEITHER' and r['accepted'] and r['oracle_clearance_m']<.025]
        counts=Counter()
        for r in dangerous:
            for v in ('CERT_ONLY','CONSTRAINT_ONLY','FULL'):
                x=lookup[r['run'],r['job_id'],v]
                counts[v+'_rejected']+=not x['accepted']
                counts[v+'_safe']+=bool(x['accepted'] and x['oracle_clearance_m']>=.025)
                counts[v+'_unsafe_accepted']+=bool(x['accepted'] and x['oracle_clearance_m']<.025)
        label=ablation_label(len(dangerous),counts['CONSTRAINT_ONLY_safe'],counts['CERT_ONLY_rejected'])
        for v in VARIANTS:
            vv=[r for r in rr if r['variant']==v]
            output.append(dict(source_method=method,variant=v,jobs=len(vv),accepted=sum(r['accepted'] for r in vv),
                oracle_unsafe_accepted=sum(r['accepted'] and r.get('oracle_clearance_m',1)<.025 for r in vv),
                dangerous_neither=len(dangerous),**dict(counts),label=label,
                solve_median_s=float(np.median([r['solve_wall_s'] for r in vv]))))
    return output


def detour_start(poses):
    back=np.flatnonzero(poses[:,0]<np.maximum.accumulate(poses[:,0])-.30)
    if len(back):return int(back[0]),'X_BACKTRACK_0.30M'
    yaw=np.r_[0.,np.cumsum(np.abs(np.diff(np.unwrap(poses[:,2]))))]
    turn=np.flatnonzero(yaw>2*np.pi)
    return (int(turn[0]),'ABS_HEADING_2PI') if len(turn) else (None,'NO_EVENT')


def consecutive(values):
    return any(a and b for a,b in zip(values,values[1:]))


def detour_label(rows):
    if any(r['all_unsafe'] for r in rows):return 'FALLBACK_SLOWDOWN'
    if consecutive([r['remaining_length_m']<.25 for r in rows]):return 'SHORT_REMAINING'
    if consecutive([r['disposition']!='ACCEPTED' for r in rows]):return 'GRAPH_REJECTED'
    if any(r['disposition']=='ACCEPTED' and (r.get('endpoint_direction_change_deg') or 0)>45 for r in rows):return 'CORRECTION_DIVERGES'
    return 'OTHER'


def wall_label(unknown, depth, oracle, execution, stop_margin=0.):
    if unknown:return 'UNOBSERVED_WALL'
    if depth>=.025 and stop_margin>.025 and oracle>=0:return 'MARGIN_MISMATCH'
    if depth>=.025 and oracle>=.025 and execution<=0:return 'EXECUTION'
    if depth-oracle>.02:return 'DEPTH_ERROR'
    return 'OTHER'


def observed_wall(field, point):
    cells,ok=field.cells(np.asarray(point)[None])
    if not ok[0]:return dict(wall_observed=False,wall_neighborhood_observed=False,wall_occupied=False)
    x,y=cells[0]; sl=np.s_[max(0,y-2):y+3,max(0,x-2):x+3]
    return dict(wall_observed=bool(field.observed[y,x]),wall_neighborhood_observed=bool(field.observed[sl].any()),wall_occupied=bool(field.occupied[y,x]))


def prepare_run(r):
    run=Path(r['output']); data=dict(record=r,run=run,config=json.loads((run/'scenario.json').read_text()))
    for key,file in (('apps','phase6_applications.jsonl'),('events','events.jsonl'),('ctrl','controller.jsonl'),('graphs','stage2_graph.jsonl'),('updates','depth/updates.jsonl'),('gaps','clearance.jsonl')):
        data[key]=jsonl(run/file)
    rec,poses=trace(run); data.update(rec=rec,poses=poses)
    data['jobs']={x['id']:x for x in data['graphs'] if x['event']=='SUBMIT'}
    data['results']={x['job_id']:x for x in data['graphs'] if x['event'] in ('RESULT','TERMINAL_UNAPPLIED')}
    by_id={e['id']:e for e in data['events']}
    for job in data['jobs'].values():
        e=by_id[job['id']];s=e['phase15b']['detail']['selected_sample']
        world=local_to_world(np.array(e['overnight_metric_samples'][s]),e['observation_pose'])
        np.testing.assert_allclose(world,job['world_xy'],atol=1e-12,rtol=0)
        np.testing.assert_allclose(job['boundary'],e['agent_pose_at_switch'],atol=1e-12,rtol=0)
    return data


def latest_snapshot(data, ns):
    updates=[u for u in data['updates'] if u['publication_monotonic_ns']<=ns]
    return Snapshot.load(updates[-1]['file']) if updates else Snapshot.load(data['run']/'depth/snapshot_initial.npz')


def route_comparison(records, index, point, time_s):
    rows=[]
    for r in records:
        if r['index']!=index or r.get('technical_validation')!='PASS':continue
        _,p=trace(Path(r['output']));k=int(np.argmin(np.linalg.norm(p[:,:2]-point,axis=1)))
        rows.append(dict(index=index,method=r['method'],classification=r['classification'],
            nearest_time_s=k/72,nearest_pose=p[k].tolist(),distance_to_diagnostic_location_m=float(np.linalg.norm(p[k,:2]-point)),
            pose_at_same_elapsed_time=p[min(round(time_s*72),len(p)-1)].tolist(),minimum_corridor_clearance_m=r['minimum_corridor_clearance_m']))
    return rows


def wall_diagnostics(data):
    r=data['record'];c=data['config'];poses=data['poses'];apps=data['apps'];last=apps[-1]
    stop=poses[-1]; wall_y=np.sign(stop[1])*c['corridor']['half_width'];wall_point=[stop[0],wall_y]
    stop_ns=int(data['rec'][-1]['monotonic_ns']);stop_field=latest_snapshot(data,stop_ns)
    site=observed_wall(stop_field,wall_point)
    first_tick=round(data['events'][-3]['application_sim_s']*72)
    chosen=[a for a in apps if a['tick']>=first_tick]
    if last not in chosen:chosen.append(last)
    rows=[]
    for a in chosen:
        xy=np.array(a['world_xy']);remain,_=suffix(xy,a['pose']);field=Snapshot.load(a['depth_snapshot']['file']);q,_=sample_path(remain)
        ix=apps.index(a);end=apps[ix+1]['tick'] if ix+1<len(apps) else len(poses)-1
        gaps=data['gaps'][a['tick']+1:end+1]
        execution=min((g['corridor_lower_m'] for g in gaps),default=path_safety(poses[a['tick']:a['tick']+1].repeat(2,axis=0)[:,:2],c)['corridor_clearance_m'])
        safety=path_safety(remain,c);depth=field.exact_clearance(remain)
        # Oracle location is used solely to attribute depth points to a wall.
        ys=field.origin[1]+np.arange(field.occupied.shape[0])*field.h
        band=np.abs(ys-wall_y)<=RULES['wall_site_band_m']
        wall_field=copy.copy(field);wall_field.occupied=field.occupied & band[:,None]
        wall_depth=finite(wall_field.exact_clearance(remain)) if wall_field.occupied.any() else None
        path=XYPath(xy);cte=[path.project(p[:2])[1] for p in poses[a['tick']:end+1]]
        row=dict(index=r['index'],id=a['id'],application_tick=a['tick'],application_time_s=a['simulation_time_s'],kind=a['kind'],
            is_final_active=a is last,graph_job_id=a['graph_job_id'],all_unsafe=a['all_unsafe'],
            depth_clearance_m=depth,depth_wall_sites_clearance_m=wall_depth,oracle_wall_clearance_m=safety['corridor_clearance_m'],
            oracle_obstacle_clearance_m=safety['obstacle_clearance_m'],full_path_depth_clearance_m=field.exact_clearance(xy),
            path_unknown_fraction=field.unknown_fraction(q),actual_corridor_lower_m=execution,
            path_minus_actual_wall_clearance_m=safety['corridor_clearance_m']-execution,max_cross_track_m=max(cte),
            snapshot_capture_s=field.metadata['sim_s'],stop_time_s=(len(poses)-1)/72,stop_pose=stop.tolist(),
            stop_wall_cell_at_application=observed_wall(field,wall_point),**site,
            stop_latest_snapshot_s=stop_field.metadata['sim_s'],stop_margin_m=0.,
            raw_world_xy=xy.tolist(),snapshot_file=a['depth_snapshot']['file'])
        rows.append(row)
    active=next(x for x in rows if x['is_final_active'])
    label=wall_label(not site['wall_observed'],active['depth_clearance_m'],active['oracle_wall_clearance_m'],active['actual_corridor_lower_m'])
    for row in rows:row['run_cause']=label
    return rows


def detour_diagnostics(data, other):
    r=data['record'];tick,rule=detour_start(data['poses']);rows=[]
    if tick is None:raise ValueError(f'No detour event for {r["key"]}')
    t=tick/72
    for e in data['events']:
        if not t-5<=e['application_sim_s']<=t+5:continue
        job=data['jobs'].get(e['id']);result=data['results'].get(job['job_id'],{}) if job else {}
        detail=e['phase15b']['detail'];select=detail['selected_sample'];candidate=detail['candidates'][select]
        xy=np.array(e['phase15b']['applied_initial_world_xy']);b=np.array(e['agent_pose_at_switch']);field=Snapshot.load(e['depth_snapshot']['file'])
        corrected=np.array(result['poses'])[:,:2] if 'poses' in result else None
        cmds=[c for c in data['ctrl'] if c['waypoint_id']==e['id']]
        angle=None
        if corrected is not None:
            u,v=xy[-1]-b[:2],corrected[-1]-b[:2]
            if min(np.linalg.norm(u),np.linalg.norm(v))>1e-12:
                angle=float(np.degrees(np.arccos(np.clip(u@v/np.linalg.norm(u)/np.linalg.norm(v),-1,1))))
        applied=result.get('disposition')=='ACCEPTED'
        rows.append(dict(index=r['index'],id=e['id'],switch_time_s=e['application_sim_s'],detour_start_s=t,detour_rule=rule,
            disposition=result.get('disposition',result.get('event','NO_JOB')),previous_v=job['previous_command'][0] if job else None,
            initialization_error=result.get('error'),all_unsafe=detail['all_unsafe'],remaining_length_m=candidate['remaining_length_m'],
            endpoint_clamp_fraction=float(np.mean([bool(c['pure_pursuit'].get('endpoint_clamped')) for c in cmds])) if cmds else None,
            corrected_actually_applied=applied,corrected_depth_clearance_m=field.exact_clearance(corrected) if corrected is not None else None,
            corrected_oracle_clearance_m=oracle_clearance(corrected,data['config']) if corrected is not None else None,
            endpoint_direction_change_deg=angle,selected_sample=select))
    label=detour_label(rows)
    for row in rows:row['run_cause']=label
    point=data['poses'][tick,:2];other_poses=other['poses'];near=int(np.argmin(np.linalg.norm(other_poses[:,:2]-point,axis=1)))
    compare=dict(index=r['index'],detour_start_s=t,detour_rule=rule,cause=label,gf_distance_m=r['distance_m'],
        depth_result=other['record']['classification'],depth_distance_m=other['record']['distance_m'],
        depth_nearest_time_s=near/72,depth_nearest_pose=other_poses[near].tolist(),depth_nearest_distance_m=float(np.linalg.norm(other_poses[near,:2]-point)),
        depth_same_elapsed_pose=other_poses[min(tick,len(other_poses)-1)].tolist())
    return rows,compare


def summarize_sigma(rows):
    out=[]
    base=[r for r in rows if r['sigma']=='baseline'];base_rate=np.mean([r['accepted'] for r in base])
    for name in ('baseline',*SIGMAS):
        rr=[r for r in rows if r['sigma']==name];d=[r['path_difference_median_m'] for r in rr if r.get('path_difference_median_m') is not None]
        accepted_d=[r['path_difference_median_m'] for r in rr if r.get('path_difference_median_m') is not None and r['accepted'] and r['baseline_accepted']]
        delta=float(np.mean([r['accepted'] for r in rr])-base_rate);median=float(np.median(d)) if d else None
        out.append(dict(sigma=name,jobs=len(rr),accepted=sum(r['accepted'] for r in rr),acceptance_change_pp=100*delta,
            changed_acceptance=sum(r['accepted']!=r['baseline_accepted'] for r in rr),path_pairs=len(d),
            path_difference_median_m=median,path_difference_max_m=max((r.get('path_difference_max_m') or 0 for r in rr),default=0),
            accepted_pairs=len(accepted_d),accepted_pair_path_median_m=float(np.median(accepted_d)) if accepted_d else None,
            within_threshold=abs(delta)<=.05+1e-12 and median is not None and median<=.02+1e-12))
    return out


def run_campaign(run_root,out):
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'protocol.json',RULES)
    records=json.loads((ROOT/'research/results/phase15b/runs.json').read_text())
    assert all(Path(r['output']).parent==run_root for r in records)
    selected=[r for r in records if r['method'] in (DEPTH,GF)]
    assert len(selected)==16 and all(r['technical_validation']=='PASS' for r in selected)
    inputs={};data={}
    source_results=ROOT/'research/results/phase15b/runs.json'
    inputs[str(source_results)]=sha256_file(source_results)
    for r in records:
        if r.get('technical_validation')=='PASS':
            f=Path(r['output'])/'agent_trajectory.csv';h=sha256_file(f)
            assert h==r['input_log_sha256']['agent_trajectory.csv'];inputs[str(f)]=h
    for r in selected:
        for name,h in r['input_log_sha256'].items():
            # Only inputs consumed by this analysis, not RGB/raw network tensors.
            if name in ('stage2_graph.jsonl','events.jsonl','phase6_applications.jsonl','controller.jsonl','clearance.jsonl','agent_trajectory.csv','scenario.json','depth/updates.jsonl') or name.startswith('depth/snapshot_') or name.startswith('model/derived/'):
                f=Path(r['output'])/name;actual=sha256_file(f);assert actual==h,f;inputs[str(f)]=actual
        data[r['method'],r['index']]=prepare_run(r)
    counts={m:sum(len(d['jobs']) for (method,_),d in data.items() if method==m) for m in (DEPTH,GF)}
    assert counts==RULES['expected_jobs'],counts
    dump(out/'input_manifest.json',dict(git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        input_sha256=inputs,source_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in [Path(__file__),Path(__file__).with_name('report.py'),Path(__file__).with_name('test_diagnose.py'),ROOT/'research/nomad_phase12/graph_gf.py',ROOT/'research/nomad_phase15b/graph.py',ROOT/'research/nomad_phase0/graph_v4.py',ROOT/'research/nomad_phase0/graph_v4_protocol.json']}))
    ablation=[];sensitivity=[];regressions=[];dispersions=[];attempts=0
    with (out/'solve_results.jsonl').open('x') as journal:
        for (method,index),d in sorted(data.items()):
            for e in d['events']:
                world=np.array([local_to_world(np.array(x),e['observation_pose']) for x in e['overnight_metric_samples']]);std=world.std(axis=0)
                for i,s in enumerate(std):
                    dispersions.append(dict(source_method=method,index=index,fresh_id=e['id'],waypoint=i,std_x_m=float(s[0]),std_y_m=float(s[1]),rms_axis_std_m=float(np.sqrt(np.mean(s*s))),radial_std_m=float(np.linalg.norm(s)),fixed_prior_sigma_m=.10))
            for job in d['jobs'].values():
                field=Snapshot.load(job['depth_snapshot']['file']);saved=d['results'].get(job['job_id']);results={}
                identity=dict(run=d['record']['key'],source_method=method,index=index,job_id=job['job_id'],fresh_id=job['id'])
                for v in VARIANTS:
                    result=solve_once(job,field,v);attempts+=1;results[v]=result
                    row={**identity,'variant':v,**{k:x for k,x in result.items() if k not in ('poses','solver')},**path_metrics(result,job,field,d['config'])}
                    row['accepted_depth_clearance_m']=row.get('depth_clearance_m') if row['accepted'] else None
                    row['accepted_oracle_clearance_m']=row.get('oracle_clearance_m') if row['accepted'] else None
                    ablation.append(row);journal.write(json.dumps({**identity,'variant':v,**result},allow_nan=False)+'\n');journal.flush()
                reg={**identity,**regression(results['FULL' if method==DEPTH else 'NEITHER'],saved)};regressions.append(reg)
                for row in ablation[-4:]:row.update({k:v for k,v in reg.items() if k.startswith('regression')})
                if method==DEPTH:
                    base=results['FULL']
                    for name,scales in [('baseline',{}),*SIGMAS.items()]:
                        result=base if name=='baseline' else solve_once(job,field,'FULL',scales)
                        if name!='baseline':
                            attempts+=1;journal.write(json.dumps({**identity,'sigma':name,**result},allow_nan=False)+'\n');journal.flush()
                        difference=np.linalg.norm(np.array(result['poses'])[:,:2]-np.array(base['poses'])[:,:2],axis=1) if result['poses'] is not None and base['poses'] is not None else None
                        sensitivity.append({**identity,'sigma':name,'baseline_accepted':base['accepted'],
                            **{k:x for k,x in result.items() if k not in ('poses','solver')},**path_metrics(result,job,field,d['config']),
                            'path_difference_median_m':float(np.median(difference)) if difference is not None else None,
                            'path_difference_max_m':float(np.max(difference)) if difference is not None else None,
                            'regression_match':reg['regression_match']})
            print(f'Completed {method} seed {index}: {len(d["jobs"])} jobs, total solve attempts {attempts}',flush=True)
    walls=[];wall_comparisons=[];detours=[];detour_comparisons=[]
    for index in (47,49):
        d=data[DEPTH,index];walls+=wall_diagnostics(d)
        wall_comparisons+=route_comparison(records,index,d['poses'][-1,:2],(len(d['poses'])-1)/72)
    for r in selected:
        if r['method']==GF and r['success'] and r['distance_m']>8:
            rows,compare=detour_diagnostics(data[GF,r['index']],data[DEPTH,r['index']]);detours+=rows;detour_comparisons.append(compare)
    assert len(detour_comparisons)==5
    asum=summarize_ablation(ablation);ssum=summarize_sigma(sensitivity)
    neither={(r['run'],r['job_id']):r for r in ablation if r['variant']=='NEITHER'}
    for row in ablation:
        base=neither[row['run'],row['job_id']]
        row['dangerous_neither']=bool(base['accepted'] and base.get('oracle_clearance_m',1)<.025)
        row['dangerous_transfer_outcome']=('REJECTED' if not row['accepted'] else 'SAFE_ACCEPTED' if row['oracle_clearance_m']>=.025 else 'UNSAFE_ACCEPTED') if row['dangerous_neither'] else None
    single=[r for r in ssum if r['sigma']!='baseline' and not r['sigma'].startswith('all_')]
    summary=dict(A=asum[0]['label'],B={str(i):next(r['run_cause'] for r in walls if r['index']==i) for i in (47,49)},
        C={str(r['index']):r['cause'] for r in detour_comparisons},D='ROBUST' if all(r['within_threshold'] for r in single) else 'SENSITIVE',
        sigma_exceeded=[r['sigma'] for r in single if not r['within_threshold']],solve_attempts=attempts,
        regression_comparable=sum(r['regression_comparable'] for r in regressions),regression_mismatches=sum(r.get('regression_match') is False for r in regressions),
        regression_unavailable=sum(not r['regression_comparable'] for r in regressions),ablation_summary=asum,sigma_summary=ssum,
        wall_comparisons=wall_comparisons,detour_comparisons=detour_comparisons)
    for name,rows in [('ablation_jobs',ablation),('ablation_summary',asum),('regression',regressions),('wall_failures',walls),('wall_comparisons',wall_comparisons),('gf_detours',detours),('sigma_sensitivity',sensitivity),('sigma_summary',ssum),('sample_dispersion',dispersions)]:
        write_csv(out/f'{name}.csv',rows)
    dump(out/'summary.json',summary)
    # A mismatched replay is retained and flagged in every comparison, never silently discarded.
    from .report import render
    render(out,data,summary,ablation,sensitivity,dispersions,walls,detours)
    for name,h in inputs.items():assert sha256_file(name)==h,name
    dump(out/'complete.json',dict(solve_attempts=attempts,raw_hashes_unchanged=True,labels={k:summary[k] for k in ('A','B','C','D')}))
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,default=ROOT.parent/'artifacts/isaac6/phase15b_depth_02');p.add_argument('--publish',action='store_true');a=p.parse_args()
    if OUT.exists():
        assert (OUT/'complete.json').exists(),'Partial campaign preserved; do not rerun solves'
        summary=json.loads((OUT/'summary.json').read_text())
    else:summary=run_campaign(a.run_root.resolve(),OUT)
    if a.publish:
        from .report import publish
        publish()
    print(json.dumps({k:summary[k] for k in ('A','B','C','D')}))


if __name__=='__main__':main()
