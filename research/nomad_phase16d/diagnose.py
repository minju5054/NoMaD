"""No simulator, inference, rendering, optimization, or kinematic rollout."""
import argparse,csv,json,subprocess
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,local_to_world,sha256_file
from nomad_phase0.chunk_report import trace
from nomad_phase15.evaluate import suffix,sample_path
from nomad_phase15b.depth import Snapshot,evaluate_samples
from nomad_phase16.geometry import path_safety

OUT=ROOT/'research/results/phase16d'
DEPTH='FRESHEST-SAFE+GRAPH-depth';GF='FRESHEST-SAFE+GRAPH-GF';SAFE='FRESHEST-SAFE'
RULES=dict(base_commit='18de5fa',main_inventory=72,gate_inventory=6,stop_fraction_strict_min=.20,
    always_include_gates=['SL_901_GRAPH-depth','SL_902_GRAPH-depth'],target_clearance_m=.025,
    depth_path='unchanged suffix/evaluate_samples: sampled SDF minimum - h/sqrt(2) - max sample spacing/2',
    depth_B='SDF.query(B) - h/sqrt(2); nominal and exact occupied-site distance also reported; no segment spacing penalty at a single point',
    oracle='exact inherited polyline footprint clearance, minimum over static boxes AND outer rectangle; evaluation only',
    best_sample_for_A='maximum oracle clearance among all eight; depth-best oracle clearance is an additional field',
    sample_change='mean world XY distance over 8x8 same-index points, descriptive array change; sample indices are not physical correspondences',
    near_start_radius_m=.30,risk_location='Euclidean radius from actual B; query points use the same conservative spacing allowance as the native selector; near/far can both be unsafe',
    consecutive='consecutive applied FRESH decisions, broken by NORMAL or KEEP_ACTIVE; median change during consecutive STOP_WAIT pairs, plus all-STOP-pair statistic',
    B_neighborhood_m=.30,B_matching='first entry recorded; GRAPH_APPROACH_CLOSER compares point oracle clearance at B with SAFE closest recorded pose inside radius; prior active lineage must be corrected',
    B_certificate='sole exact certificate rejection: solver success + constraints_satisfied + exact_certificate_pass false + actual CONSTRAINT_FAILED; nonconvergence/stale alone is not certificate rejection',
    B_different_route='either SAFE or GF never enters the 0.30m neighborhood; tested after first two label conditions',
    E1='threshold=min(.025,c_B-.005), with no clamp at zero; eligible longest remaining suffix, then lower index',
    E2='threshold=.010; eligible longest remaining suffix, then lower index',
    E3='maximum depth clearance, then lower index (same Phase15B implementation)',
    tie_order=['E1','E2','E3','E0'],speed_cap_m_s=.10,
    selection='pooled A STOP_WAIT events including D0 SL gates; retain candidates with zero oracle-negative selected paths, maximize escape fraction, require >=.50; descriptive main/gate strata also reported',
    figure_event='middle event of the earliest longest consecutive STOP_WAIT chain; never selected by escape-rule outcomes',
    figure_scope='all main STUCK runs plus the two SL gates; runs outside A are explicitly plot-only and use their last FRESH if no STOP_WAIT chain exists',
    scope='Offline same-data path selection, not execution safety, intervention causality, or navigation success. Nonpenetration is weaker than the 2.5cm margin. New-seed closed-loop validation required.',
    navigation=0,inference=0,render=0,graph_solves=0,rollouts=0)

def dump(path,data):
    with Path(path).open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')
def csv_write(path,records):
    keys=list(dict.fromkeys(k for r in records for k in r))
    with Path(path).open('x',newline='') as f:
        w=csv.DictWriter(f,keys);w.writeheader()
        for r in records:w.writerow({k:json.dumps(v,allow_nan=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
def rows(path):return [json.loads(l) for l in Path(path).read_text().splitlines() if l]
def median(values):
    v=[x for x in values if x is not None];return float(np.median(v)) if v else None
def clearance(xy,config):
    s=path_safety(np.array(xy),config);return min(s['obstacle_clearance_m'],s['corridor_clearance_m'])
def point_clearance(p,config):return clearance(np.repeat(np.asarray(p)[None,:2],2,axis=0),config)
def is_stop(e):return e.get('phase16',{}).get('fallback_mode')=='STOP_WAIT'
def classify_A(marginal,blocked,near,n):
    if not n:return 'OTHER'
    if marginal/n>=.7:return 'MARGINAL_DEADLOCK'
    if blocked/n>=.7:return 'TRUE_BLOCK'
    if near/n>=.7:return 'NEAR_START_POSE'
    return 'OTHER'
def choose_escape(depth,lengths,c_B):
    """No oracle argument: selected index depends only on available depth/length."""
    depth=np.asarray(depth);lengths=np.asarray(lengths)
    def pick(threshold):
        ids=np.flatnonzero(depth>=threshold)
        return int(min(ids,key=lambda i:(-lengths[i],int(i)))) if len(ids) else None
    return {'E0':None,'E1':pick(min(.025,c_B-.005)),'E2':pick(.010),
            'E3':int(min(range(len(depth)),key=lambda i:(-depth[i],i)))}
def select_rule(summary):
    eligible=[r for r in summary if r['penetrating_selections']==0]
    chosen=min(eligible,key=lambda r:(-r['escape_fraction'],RULES['tie_order'].index(r['candidate'])))
    return dict(candidate=chosen['candidate'],escape_fraction=chosen['escape_fraction'],penetrating_selections=chosen['penetrating_selections'],
                label='INSUFFICIENT' if chosen['escape_fraction']<.5 else 'OFFLINE_SELECTED',eligible=[r['candidate'] for r in eligible],
                next_step='Consider in-place-rotation recovery in a new study' if chosen['escape_fraction']<.5 else 'Validate this rule in a new-seed closed-loop study',scope=RULES['scope'])

class Inputs:
    def __init__(self):self.hashes={}
    def track(self,path,expected=None):
        path=Path(path);key=str(path.resolve())
        if key not in self.hashes:self.hashes[key]=sha256_file(path)
        if expected is not None:assert self.hashes[key]==expected,path
        return path
    def field(self,path):return Snapshot.load(self.track(path))

def load_run(record,inputs):
    run=Path(record['output']);data=dict(record=record,run=run)
    for file,h in record.get('input_sha256',{}).items():inputs.track(run/file,h)
    data['config']=json.loads(inputs.track(run/'scenario.json').read_text())
    for key,file in (('events','events.jsonl'),('controllers','controller.jsonl'),('fallbacks','fallback.jsonl'),('apps','phase16_applications.jsonl'),('graphs','stage2_graph.jsonl'),('gaps','clearance.jsonl'),('updates','depth/updates.jsonl')):
        p=run/file;data[key]=rows(inputs.track(p)) if p.exists() else []
    inputs.track(run/'agent_trajectory.csv');data['trace'],data['poses']=trace(run)
    data['distance']=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(data['poses'][:,:2],axis=0),axis=1))]
    data['jobs']={r['id']:r for r in data['graphs'] if r['event']=='SUBMIT'}
    data['results']={r['job_id']:r for r in data['graphs'] if r['event'] in ('RESULT','TERMINAL_UNAPPLIED')}
    duration=record['duration_s'];times=np.array([c['simulation_time_s'] for c in data['controllers']]);dt=np.maximum(0,np.r_[times[1:],duration]-times)
    frac=float(sum(t for t,c in zip(dt,data['controllers']) if c.get('phase16_fallback_mode')=='STOP_WAIT')/duration)
    assert abs(frac-record['fallback_time_fraction']['STOP_WAIT'])<1e-12
    assert {e['id'] for e in data['events'] if is_stop(e)}=={e['id'] for e in data['fallbacks'] if e['mode']=='STOP_WAIT'}
    # Keep the distinction between an original path, corrected path, and a
    # KEEP_ACTIVE reuse. STOP_WAIT is braking/waiting, not path following.
    lineage='NONE'
    for app in data['apps']:
        if app['kind']=='GRAPH':lineage='CORRECTED'
        elif app['kind']=='NORMAL':lineage='ORIGINAL'
        app['_lineage']=lineage
    return data

def world_samples(data,e,inputs):
    p=inputs.track(data['run']/f"model/derived/{e['id']:04d}.npz")
    with np.load(p) as z:local=z['metric'].copy()
    assert local.shape==(8,8,2)
    np.testing.assert_array_equal(local,np.array(e['overnight_metric_samples']))
    return np.array([local_to_world(x,e['observation_pose']) for x in local])
def event_field(e,inputs):
    meta=e.get('phase16',{}).get('selection',{}).get('snapshot',e['depth_snapshot'])
    assert meta['publication_monotonic_ns']<=e.get('phase16_selection_ns',e.get('phase15b_selection_monotonic_ns',e['application_monotonic_ns']))
    return inputs.field(meta['file']),meta

def measure_event(data,e,inputs,previous=None,previous_world=None,consecutive=False):
    r=data['record'];B=np.array(e['agent_pose_at_switch']);field,meta=event_field(e,inputs)
    worlds=world_samples(data,e,inputs);_,decision=evaluate_samples(worlds,B,field)
    logged=e['phase16']['selection'];assert decision['all_unsafe'] and logged['all_unsafe']
    np.testing.assert_allclose([r['clearance_m'] for r in decision['candidates']],[r['clearance_m'] for r in logged['candidates']],atol=1e-12,rtol=0)
    oracle=[];depth=[];lengths=[];locations=[];argmin_distance=[];deficits=[];near_gap=[];far_gap=[]
    for sample,candidate in zip(worlds,decision['candidates']):
        path,length=suffix(sample,B);q,ds=sample_path(path);values=field.query(q)[0]-field.error_bound-ds/2
        d=np.linalg.norm(q-B[:2],axis=1);near=d<=.30;unsafe=values<.025
        near_unsafe=bool(np.any(unsafe & near));far_unsafe=bool(np.any(unsafe & ~near))
        locations.append('NEAR_AND_FAR' if near_unsafe and far_unsafe else 'NEAR_ONLY' if near_unsafe else 'FAR_ONLY' if far_unsafe else 'NONE')
        oracle.append(clearance(path,data['config']));depth.append(candidate['clearance_m']);lengths.append(length);deficits.append(max(0.,.025-candidate['clearance_m']))
        argmin_distance.append(float(d[np.argmin(values)]));near_gap.append(float(values[near].min()) if near.any() else None);far_gap.append(float(values[~near].min()) if (~near).any() else None)
    nominal=float(field.query(B[None,:2])[0][0]);cB=nominal-field.error_bound;bOracle=point_clearance(B,data['config'])
    best_oracle=max(oracle);best_depth=int(min(range(8),key=lambda i:(-depth[i],i)))
    tick=round(e['application_sim_s']*72);change=move=displacement=elapsed=None
    if previous is not None:
        old_tick=round(previous['application_sim_s']*72);change=float(np.linalg.norm(worlds-previous_world,axis=2).mean())
        move=float(data['distance'][tick]-data['distance'][old_tick]);displacement=float(np.linalg.norm(B[:2]-np.array(previous['agent_pose_at_switch'])[:2]));elapsed=e['application_sim_s']-previous['application_sim_s']
    f=e['phase16'].get('fallback') or {};row=dict(run=r['key'],split=r['split'],scene=r['scene'],method=r['method'],index=r['index'],id=e['id'],time_s=e['application_sim_s'],tick=tick,
        observation_pose=e['observation_pose'],B=B.tolist(),snapshot_file=meta['file'],snapshot_time_s=meta['sim_s'],snapshot_age_s=e['application_sim_s']-meta['sim_s'],
        B_depth_clearance_m=cB,B_depth_nominal_m=nominal,B_depth_exact_sites_m=field.exact_clearance(np.repeat(B[None,:2],2,axis=0)),B_oracle_clearance_m=bOracle,
        B_unknown=bool(field.unknown_fraction(B[None,:2])),depth_clearances_m=depth,oracle_clearances_m=oracle,remaining_lengths_m=lengths,
        depth_max_m=max(depth),depth_median_m=float(np.median(depth)),depth_best_deficit_m=max(0.,.025-max(depth)),depth_median_deficit_m=max(0.,.025-float(np.median(depth))),sample_deficits_m=deficits,
        unsafe_locations=locations,minimum_location_distance_to_B_m=argmin_distance,near_clearance_m=near_gap,far_clearance_m=far_gap,
        oracle_categories=['PENETRATING' if v<0 else 'NEAR' if v<.025 else 'MARGIN_MET' for v in oracle],oracle_best_m=best_oracle,oracle_best_sample=int(np.argmax(oracle)),
        depth_best_sample=best_depth,depth_best_sample_oracle_m=oracle[best_depth],oracle_nonpenetrating_samples=sum(v>=0 for v in oracle),oracle_margin_samples=sum(v>=.025 for v in oracle),
        marginal_event=0<=best_oracle<.025,true_block_event=all(v<0 for v in oracle),near_start_event=cB<.025,
        previous_stop_id=previous['id'] if previous else None,consecutive_stop_pair=consecutive,sample_change_mean_m=change,robot_arclength_since_previous_stop_m=move,
        robot_displacement_since_previous_stop_m=displacement,elapsed_since_previous_stop_s=elapsed,actual_v_at_B=float(data['trace'][tick]['v_m_s']),
        active_path_clearance_m=f.get('clearance_m'),active_path_remaining_length_m=f.get('remaining_length_m'),te_component_checks=f.get('checks'),
        keep_rejected_for_short_remaining=f.get('remaining_length_m') is not None and f['remaining_length_m']<.25,
        graph_dispatched_for_stop=e['id'] in data['jobs'])
    return row,worlds

def stop_chains(events):
    chains=[];chain=[]
    for e in events:
        if is_stop(e):chain.append(e['id'])
        elif chain:chains.append(chain);chain=[]
    if chain:chains.append(chain)
    return chains
def analyze_A(data,inputs):
    records=[];previous=world=None;was_stop=False
    for e in data['events']:
        if is_stop(e):
            row,new_world=measure_event(data,e,inputs,previous,world,was_stop);records.append(row);previous=e;world=new_world
        was_stop=is_stop(e)
    n=len(records);m=sum(r['marginal_event'] for r in records);b=sum(r['true_block_event'] for r in records);near=sum(r['near_start_event'] for r in records)
    label=classify_A(m,b,near,n);chains=stop_chains(data['events']);longest=max(chains,key=len) if chains else []
    by_id={r['id']:r for r in records};representative=longest[len(longest)//2] if longest else None
    r=data['record'];summary=dict(run=r['key'],split=r['split'],scene=r['scene'],method=r['method'],index=r['index'],classification=r['classification'],STOP_WAIT_fraction=r['fallback_time_fraction']['STOP_WAIT'],
        stop_events=n,cause=label,marginal_fraction=m/n if n else None,true_block_fraction=b/n if n else None,near_start_fraction=near/n if n else None,
        oracle_margin_available_fraction=sum(x['oracle_margin_samples']>0 for x in records)/n if n else None,
        depth_false_close_fraction=sum(x['B_depth_clearance_m']<.025<=x['B_oracle_clearance_m'] for x in records)/n if n else None,
        active_path_short_rejections=sum(x['keep_rejected_for_short_remaining'] for x in records),max_consecutive_STOP_WAIT=len(longest),
        longest_chain_first_id=longest[0] if longest else None,longest_chain_last_id=longest[-1] if longest else None,
        longest_chain_event_span_s=by_id[longest[-1]]['time_s']-by_id[longest[0]]['time_s'] if longest else 0.,
        sample_change_consecutive_median_m=median([x['sample_change_mean_m'] for x in records if x['consecutive_stop_pair']]),
        sample_change_all_stop_pairs_median_m=median([x['sample_change_mean_m'] for x in records]),
        sample_change_stationary_pairs_median_m=median([x['sample_change_mean_m'] for x in records if x['consecutive_stop_pair'] and x['robot_arclength_since_previous_stop_m']<=.001]),
        robot_movement_consecutive_median_m=median([x['robot_arclength_since_previous_stop_m'] for x in records if x['consecutive_stop_pair']]),
        graph_dispatches_during_stop=sum(x['graph_dispatched_for_stop'] for x in records),representative_id=representative)
    return records,summary

def candidates_for_event(row):
    picks=choose_escape(row['depth_clearances_m'],row['remaining_lengths_m'],row['B_depth_clearance_m']);output=[]
    for name,index in picks.items():
        oracle=row['oracle_clearances_m'][index] if index is not None else None
        output.append(dict(run=row['run'],split=row['split'],scene=row['scene'],method=row['method'],index=row['index'],id=row['id'],time_s=row['time_s'],candidate=name,
            selected_sample=index,escape=index is not None,depth_threshold_m=min(.025,row['B_depth_clearance_m']-.005) if name=='E1' else .010 if name=='E2' else None,
            speed_cap_hypothetical_m_s=.10 if index is not None else None,selected_depth_clearance_m=row['depth_clearances_m'][index] if index is not None else None,
            selected_oracle_clearance_m=oracle,penetrating=oracle is not None and oracle<0,near=oracle is not None and 0<=oracle<.025,
            oracle_margin_met=oracle is not None and oracle>=.025,executed=False))
    return output
def escape_summary(rows):
    output=[]
    for split in ('ALL','main','gate'):
        for name in ('E0','E1','E2','E3'):
            rr=[r for r in rows if r['candidate']==name and (split=='ALL' or r['split']==split)];n=len(rr)
            output.append(dict(split=split,candidate=name,events=n,selected=sum(r['escape'] for r in rr),escape_fraction=sum(r['escape'] for r in rr)/n if n else 0.,
                penetrating_selections=sum(r['penetrating'] for r in rr),near_selections=sum(r['near'] for r in rr),margin_met_selections=sum(r['oracle_margin_met'] for r in rr)))
    return output

def snapshot_at(data,ns,inputs):
    available=[r for r in data['updates'] if r['publication_monotonic_ns']<=ns]
    return inputs.field(available[-1]['file'] if available else data['run']/'depth/snapshot_initial.npz')
def comparison_at(data,B,inputs):
    distances=np.linalg.norm(data['poses'][:,:2]-np.array(B)[:2],axis=1);inside=np.flatnonzero(distances<=.30)
    out=dict(comparator_run=data['record']['key'],comparator_method=data['record']['method'],comparator_result=data['record']['classification'],entered_radius=bool(len(inside)),minimum_distance_to_B_m=float(distances.min()))
    if not len(inside):return out
    first=int(inside[0]);closest=int(inside[np.argmin(distances[inside])])
    for name,tick in (('entry',first),('closest',closest)):
        p=data['poses'][tick];field=snapshot_at(data,int(data['trace'][tick]['monotonic_ns']),inputs)
        out.update({f'{name}_time_s':tick/72,f'{name}_pose':p.tolist(),f'{name}_heading_deg':float(np.degrees(p[2])),
            f'{name}_distance_to_B_m':float(distances[tick]),f'{name}_oracle_clearance_m':point_clearance(p,data['config']),
            f'{name}_depth_clearance_m':float(field.query(p[None,:2])[0][0]-field.error_bound)})
    out['minimum_oracle_within_radius_m']=min(point_clearance(data['poses'][k],data['config']) for k in inside)
    return out
def solely_certificate_rejected(result):
    s=result.get('solver',{})
    return bool(result.get('disposition')=='CONSTRAINT_FAILED' and s.get('success') and s.get('constraints_satisfied') and s.get('exact_certificate_pass') is False)
def B_label(corrected_active,safe,graph_clearance,certificate_revert,comparisons):
    if corrected_active and safe.get('entered_radius') and safe['closest_oracle_clearance_m']-graph_clearance>=.02:return 'GRAPH_APPROACH_CLOSER'
    if certificate_revert:return 'CERTIFICATE_REVERT'
    if any(not x['entered_radius'] for x in comparisons):return 'DIFFERENT_ROUTE'
    return 'OTHER'

def analyze_B(data,safe,gf,inputs):
    first=next(e for e in data['events'] if is_stop(e));B=np.array(first['agent_pose_at_switch']);tick=round(first['application_sim_s']*72)
    previous=[e for e in data['events'] if e['application_sim_s']<first['application_sim_s']][-3:]
    applications=[r for r in data['apps'] if r['tick']<tick];last=applications[-1] if applications else None
    comparisons=[comparison_at(d,B,inputs) for d in (safe,gf)]
    first_field,_=event_field(first,inputs);B_oracle=point_clearance(B,data['config']);switches=[]
    for j,e in enumerate(previous):
        worlds=world_samples(data,e,inputs);selected=e['phase16']['selection']['selected_sample'];raw=worlds[selected];field,_=event_field(e,inputs)
        job=data['jobs'].get(e['id']);result=data['results'].get(job['job_id'],{}) if job else {};b=e['agent_pose_at_switch'];raw_suffix,_=suffix(raw,b)
        raw_oracle=clearance(raw_suffix,data['config']);raw_obstacle=path_safety(raw_suffix,data['config'])['obstacle_clearance_m']
        corrected=np.array(result['poses'])[:,:2] if 'poses' in result else None;corrected_suffix=suffix(corrected,b)[0] if corrected is not None else None
        start=round(e['application_sim_s']*72);next_event=next((x for x in data['events'] if x['application_sim_s']>e['application_sim_s']),first);end=min(tick,round(next_event['application_sim_s']*72))
        local_apps=[a for a in data['apps'] if start<=a['tick']<end];corrected_tick=result.get('applied_tick')
        intervals=data['gaps'][corrected_tick+1:end+1] if corrected_tick is not None and corrected_tick<end else []
        corr_oracle=clearance(corrected_suffix,data['config']) if corrected_suffix is not None else None
        switches.append(dict(row_type='preceding_switch',index=data['record']['index'],run=data['record']['key'],id=e['id'],switch_time_s=e['application_sim_s'],
            selected_sample=selected,fallback_mode=e['phase16']['fallback_mode'],actual_path_kinds=[a['_lineage'] for a in local_apps],
            graph_disposition=result.get('disposition',result.get('event','NO_JOB')),corrected_actually_applied=corrected_tick is not None,
            raw_suffix_oracle_clearance_m=raw_oracle,raw_suffix_obstacle_clearance_m=raw_obstacle,
            raw_full_oracle_clearance_m=clearance(raw,data['config']),raw_depth_clearance_m=float(field.exact_clearance(raw_suffix)),
            corrected_suffix_oracle_clearance_m=corr_oracle,corrected_full_oracle_clearance_m=clearance(corrected,data['config']) if corrected is not None else None,
            corrected_depth_clearance_m=float(field.exact_clearance(corrected_suffix)) if corrected_suffix is not None else None,
            delta_oracle_clearance_m=corr_oracle-raw_oracle if corr_oracle is not None else None,
            delta_obstacle_clearance_m=path_safety(corrected_suffix,data['config'])['obstacle_clearance_m']-raw_obstacle if corrected_suffix is not None else None,
            corrected_execution_min_oracle_clearance_m=min(min(g['lower_m'],g['corridor_lower_m']) for g in intervals) if intervals else None,
            corrected_execution_min_obstacle_clearance_m=min(g['lower_m'] for g in intervals) if intervals else None,
            exact_certificate_pass=result.get('solver',{}).get('exact_certificate_pass'),sole_certificate_rejection=solely_certificate_rejected(result)))
    active_id=last.get('path_source_id') if last else None
    active_job=data['jobs'].get(active_id);active_result=data['results'].get(active_job['job_id'],{}) if active_job else {}
    cert=bool(last and last['_lineage']=='ORIGINAL' and solely_certificate_rejected(active_result))
    corrected_active=bool(last and last['_lineage']=='CORRECTED')
    label=B_label(corrected_active,comparisons[0],B_oracle,cert,comparisons)
    summary=dict(row_type='run_summary',index=data['record']['index'],run=data['record']['key'],cause=label,first_stop_id=first['id'],first_stop_time_s=first['application_sim_s'],B=B.tolist(),
        B_oracle_clearance_m=B_oracle,B_depth_clearance_m=float(first_field.query(B[None,:2])[0][0]-first_field.error_bound),
        prior_active_path_kind=last['_lineage'] if last else None,prior_application_tick=last['tick'] if last else None,prior_path_source_id=active_id,
        safe_closest_minus_graph_B_m=comparisons[0]['closest_oracle_clearance_m']-B_oracle if comparisons[0]['entered_radius'] else None,
        safe_entry_minus_graph_B_m=comparisons[0]['entry_oracle_clearance_m']-B_oracle if comparisons[0]['entered_radius'] else None,certificate_revert=cert,
        comparisons=comparisons)
    flat=[summary,*[dict(row_type='comparator',index=data['record']['index'],cause=label,**x) for x in comparisons],*switches]
    return summary,flat

def run_campaign(root,out):
    out.mkdir(parents=True,exist_ok=False);dump(out/'protocol.json',RULES);inputs=Inputs()
    source=inputs.track(ROOT/'research/results/phase16/runs.json');main=json.loads(source.read_text())
    gates=[]
    for f in sorted((root/'metrics').glob('gate_*.json')):gates.append(json.loads(inputs.track(f).read_text()))
    assert len(main)==72 and len(gates)==6
    for r in main:r['split']='main'
    for r in gates:r['split']='gate'
    all_records=main+gates
    assert all(Path(r['output']).is_relative_to(root) for r in all_records)
    chosen=[r for r in all_records if (r['split']=='main' and r.get('fallback_time_fraction',{}).get('STOP_WAIT',0)>.20) or (r['split']=='gate' and r['scene']=='SL')]
    assert all(r['technical_validation']=='PASS' for r in chosen)
    inventory=[dict(run=r['key'],split=r['split'],scene=r['scene'],index=r['index'],method=r['method'],classification=r['classification'],STOP_WAIT_fraction=r.get('fallback_time_fraction',{}).get('STOP_WAIT',0),selected_for_A=r in chosen) for r in all_records]
    data={};stop_rows=[];run_rows=[];escapes=[]
    def get(r):
        key=r['split'],r['scene'],r['index'],r['method']
        if key not in data:data[key]=load_run(r,inputs)
        return data[key]
    for r in chosen:
        d=get(r);events,summary=analyze_A(d,inputs);stop_rows+=events;run_rows.append(summary)
        for e in events:escapes+=candidates_for_event(e)
        print(f"[A] {r['key']}: {len(events)} STOP_WAIT events",flush=True)
    b=[];brows=[]
    targets=[r for r in main if r['scene']=='CL' and r['method']==DEPTH and r['classification']=='STUCK'];assert len(targets)==4
    for r in targets:
        match=lambda method:next(x for x in main if x['scene']=='CL' and x['index']==r['index'] and x['method']==method)
        summary,rr=analyze_B(get(r),get(match(SAFE)),get(match(GF)),inputs);b.append(summary);brows+=rr
    gate_rows=[]
    for r in run_rows:
        if r['split']!='gate':continue
        label='GATE_DEADLOCK' if r['cause'] in ('MARGINAL_DEADLOCK','NEAR_START_POSE') else 'NOMAD_BLOCKED' if r['cause']=='TRUE_BLOCK' else 'OTHER'
        rr=[x for x in stop_rows if x['run']==r['run'] and x['split']=='gate']
        gate_rows.append(dict(**r,gate_cause=label,nonpenetrating_sample_available_events=sum(x['oracle_nonpenetrating_samples']>0 for x in rr),
            nonpenetrating_sample_available_fraction=sum(x['oracle_nonpenetrating_samples']>0 for x in rr)/len(rr) if rr else None))
    summaries=escape_summary(escapes);selection=select_rule([s for s in summaries if s['split']=='ALL'])
    summary=dict(A=dict(Counter(r['cause'] for r in run_rows)),B={str(r['index']):r['cause'] for r in b},C={str(r['index']):r['gate_cause'] for r in gate_rows},
        selected_runs=len(chosen),main_selected=sum(r['split']=='main' for r in chosen),gate_selected=sum(r['split']=='gate' for r in chosen),stop_events=len(stop_rows),selection=selection,B_details=b)
    plot_records=[]
    for r in all_records:
        if r['classification']!='STUCK' or not (r['split']=='main' or r['scene']=='SL'):continue
        d=get(r);chains=stop_chains(d['events']);chain=max(chains,key=len) if chains else []
        eid=chain[len(chain)//2] if chain else d['events'][-1]['id'];e=next(x for x in d['events'] if x['id']==eid)
        world_samples(d,e,inputs);event_field(e,inputs)
        plot_records.append(dict(run=r['key'],split=r['split'],scene=r['scene'],method=r['method'],index=r['index'],representative_id=eid,in_A=r in chosen))
    summary['plot_records']=plot_records
    for name,rr in [('inventory',inventory),('stop_events',stop_rows),('runs',run_rows),('graph_vs_safe',brows),('sl_gate',gate_rows),('escape_candidates',escapes),('escape_summary',summaries)]:csv_write(out/f'{name}.csv',rr)
    dump(out/'selection.json',selection);dump(out/'summary.json',summary)
    source_files=[*Path(__file__).parent.glob('*.py'),ROOT/'research/nomad_phase16/geometry.py',ROOT/'research/nomad_phase16/execution.py',ROOT/'research/nomad_phase15b/depth.py',ROOT/'research/nomad_phase15/evaluate.py']
    dump(out/'input_manifest.json',dict(execution_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),input_sha256=inputs.hashes,
        source_sha256={str(p.relative_to(ROOT)):sha256_file(p) for p in source_files}))
    from .report import render
    render(out,summary,run_rows,stop_rows,brows,gate_rows,summaries,data)
    for name,h in inputs.hashes.items():assert sha256_file(name)==h,name
    dump(out/'complete.json',dict(complete=True,inputs_unchanged=True,events=len(stop_rows),navigation=0,inference=0,render=0,graph_solves=0,rollouts=0))
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,default=ROOT.parent/'artifacts/isaac6/phase16_multiscene_01');p.add_argument('--publish',action='store_true');a=p.parse_args()
    if OUT.exists():assert (OUT/'complete.json').exists(),'Partial output preserved; inspect before continuing';summary=json.loads((OUT/'summary.json').read_text())
    else:summary=run_campaign(a.run_root.resolve(),OUT)
    if a.publish:
        from .report import publish
        publish()
    print(json.dumps({k:summary[k] for k in ('A','B','C','selection')}))
if __name__=='__main__':main()
