"""Phase38(all methods)+Phase41 localization audit from saved logs only."""
import argparse,csv,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from .filter import WindowHMM

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'research/results/phase42l'
DOCUMENT=ROOT/'docs/PHASE42L.md'
RULES=dict(primary_pose='Image observation_pose at observation_sim_s; nearest Topomap node in XY, smaller node id on ties',
    auxiliary_pose='Inference completion and controller latch: nearest preceding saved72Hz pose; no extrapolation beyond trajectory',
    node_error='estimated index minus nearest physical node index; absolute error in nodes',
    jump='abs(current closest - preceding inference closest)>=3; first/missing predecessor excluded',
    last10='Failed runs only; observations in[max(0,termination_sim_s-10),termination_sim_s]',
    failure_mapping='Existing primary_cause; POST_PASSAGE_TIMEOUT=>POST_PASSAGE, STATIC_NARROW_STUCK=>STATIC_NARROW; successes override stale cause; others retained',
    cohorts='Final recorded attempt per report row, Phase38 180 + Phase41 15; technical failures listed separately',
    hmm='Forward only, no Viterbi/backward pass, no future observations or nearest-node truth input',
    transition='Uniform over global-map index neighbors |j-i|<=K; K=min(N-1,max(1,ceil(odometry_path_distance/median_positive_adjacent_node_spacing)))',
    distance='Integrated recorded72Hz XY travel between successive valid observation times; no displacement cancellation',
    emission='exp(-logged_NoMaD_distance), unit temperature, uncalibrated energy; no fitting or variants',
    missing_window='Only logged candidate_ids receive emissions; all other posterior entries zero, no distance synthesis',
    reset='If logged window has zero reachable prior mass, uniform prior in that window, count reset explicitly',
    limitations='Observed raw-policy windows are fixed; this is not a counterfactual full online localization policy or driving outcome',
    reporting='Event-weighted error plus equal-run mean MAE; paired raw/HMM errors use identical valid rows; no significance tests or causal claims')


def read(path):return json.loads(Path(path).read_text())
def lines(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()] if Path(path).exists() else []
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,x):path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def csvout(path,rows):
    path=Path(path)
    if not rows:path.write_text('');return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader()
        w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)


def table(rows):
    if not rows:return '| n |\n|---|\n| 0 |'
    keys=list(dict.fromkeys(k for r in rows for k in r))
    def fmt(x):
        if x is None:return '—'
        if isinstance(x,float):return f'{x:.4g}'
        return str(x).replace('|','/').replace('\n',' ')
    return '| '+' | '.join(keys)+' |\n|'+'|'.join('---' for _ in keys)+'|\n'+'\n'.join('| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows)


def cause(row):
    if row.get('technical_validation')!='PASS':return 'TECHNICAL_FAILURE'
    if row['success']:return 'SUCCESS'
    value=row.get('primary_cause') or ('WRONG_STOP' if row.get('wrong_stop') else 'OTHER')
    return {'POST_PASSAGE_TIMEOUT':'POST_PASSAGE','STATIC_NARROW_STUCK':'STATIC_NARROW'}.get(value,value)


def nearest(nodes,pose):return int(np.argmin(np.linalg.norm(nodes[:,:2]-np.asarray(pose)[:2],axis=1)))


def summary(rows):
    n=len(rows);result=dict(inferences=n,runs=len({r['run'] for r in rows}))
    for tag in ('raw','hmm'):
        values=[r[tag+'_abs_error'] for r in rows if r.get(tag+'_abs_error') is not None]
        jumps=[r[tag+'_jump'] for r in rows if r.get(tag+'_jump') is not None]
        per_run=defaultdict(list)
        for r in rows:
            if r.get(tag+'_abs_error') is not None:per_run[r['run']].append(r[tag+'_abs_error'])
        result.update({tag+'_n':len(values),tag+'_mae':float(np.mean(values)) if values else None,
            tag+'_abs_p50':float(np.median(values)) if values else None,tag+'_abs_p95':float(np.quantile(values,.95)) if values else None,
            tag+'_signed_mean':float(np.mean([r[tag+'_signed_error'] for r in rows if r.get(tag+'_signed_error') is not None])) if values else None,
            tag+'_run_mean_mae':float(np.mean([np.mean(v) for v in per_run.values()])) if per_run else None,
            tag+'_jump_n':sum(jumps),tag+'_jump_denominator':len(jumps),tag+'_jump_rate':sum(jumps)/len(jumps) if jumps else None})
    common=[r for r in rows if r.get('hmm_abs_error') is not None and r.get('raw_abs_error') is not None]
    result.update(paired_n=len(common),paired_raw_mae=float(np.mean([r['raw_abs_error'] for r in common])) if common else None,
        hmm_minus_raw_mae=float(np.mean([r['hmm_abs_error']-r['raw_abs_error'] for r in common])) if common else None,
        truth_outside_window=sum(r['truth_outside_window'] for r in rows),hmm_window_resets=sum(r.get('window_reset',False) for r in rows))
    return result


def group_summary(events,fields,windows=('ALL','FAIL_LAST10')):
    result=[]
    for window in windows:
        groups=defaultdict(list)
        for r in events:
            if window=='FAIL_LAST10' and not r['failure_last10']:continue
            groups[tuple(r[k] for k in fields)].append(r)
        for key,rows in sorted(groups.items()):result.append(dict(zip(fields,key),window=window,**summary(rows)))
    return result


def run_analysis(row,phase,hashes):
    folder=Path(row['output']);ident=f"{phase}/{row['scene']}_{row['index']}_{row['method']}"
    files=[folder/name for name in ('scenario.json','agent_trajectory.csv','model/inference.jsonl','received.jsonl')]
    missing=[str(f) for f in files if not f.exists()]
    for f in files:
        if f.exists():hashes[str(f)]=sha(f)
    if any(not f.exists() for f in files[:3]):
        return [],dict(phase=phase,run=ident,method=row['method'],scene=row['scene'],status='MISSING_INPUT',missing=missing),None
    cfg=read(files[0]);manifest=Path(cfg['topomap_manifest']);hashes[str(manifest)]=sha(manifest)
    node_rows=sorted(read(manifest)['nodes'],key=lambda n:n['node_id'])
    assert [n['node_id'] for n in node_rows]==list(range(len(node_rows)))
    nodes=np.asarray([n['world_pose'] for n in node_rows],float)
    spacing=np.linalg.norm(np.diff(nodes[:,:2],axis=0),axis=1);positive=spacing[spacing>1e-12]
    if not len(positive):raise ValueError(f'No positive Topomap spacing: {manifest}')
    node_spacing=float(np.median(positive));hmm=WindowHMM(len(nodes),node_spacing)
    with files[1].open() as f:trajectory=list(csv.DictReader(f))
    poses=np.array([[float(r[k]) for k in ('x_m','y_m','yaw_rad')] for r in trajectory])
    ts=np.array([float(r['simulation_time_s']) for r in trajectory]);clock=np.array([int(r['monotonic_ns']) for r in trajectory],np.int64)
    travel=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1))]
    assert len(ts) and np.all(np.diff(ts)>0) and np.all(np.diff(clock)>=0)
    duration=float(row.get('duration_s',ts[-1]));received={r['id']:r for r in lines(files[3])}
    declaration_file=folder/'declared_arrival.json'
    declaration=read(declaration_file) if declaration_file.exists() else None
    if declaration is not None:hashes[str(declaration_file)]=sha(declaration_file)
    inference=lines(files[2]);events=[];counts=Counter();previous_raw=None;previous_hmm=None;last_travel=None
    end=ts[-1];failure=cause(row);outcome='SUCCESS' if row.get('success') else 'FAILURE' if row.get('technical_validation')=='PASS' else 'TECHNICAL_FAILURE'
    for event in sorted(inference,key=lambda x:x['id']):
        m=event.get('topomap');t=event.get('observation_sim_s');pose=event.get('observation_pose')
        if not m or t is None or pose is None:counts['missing_topomap_or_pose']+=1;continue
        if not (ts[0]-1e-9<=t<=end+1e-9):counts['observation_outside_saved_trajectory']+=1;continue
        tick=int(np.argmin(np.abs(ts-t)))
        if abs(ts[tick]-t)>1/72+1e-9:counts['pose_time_unmatched']+=1;continue
        # Stored observation is the actual renderer pose, not a planner B or
        # predicted pose; confirm it against the source72Hz trajectory.
        mismatch=float(np.linalg.norm(np.asarray(pose)[:2]-poses[tick,:2]))
        if mismatch>1e-6:raise ValueError(f'Observation/trajectory pose mismatch: {ident}/{event["id"]}: {mismatch}')
        truth=nearest(nodes,pose);raw=int(m['closest_node']);ids=m.get('candidate_ids',[]);dist=m.get('distances',[])
        if int(m['goal_node'])!=len(nodes)-1:raise ValueError('Topomap node count mismatch')
        r=dict(phase=phase,run=ident,method=row['method'],scene=row['scene'],seed=row['index'],outcome=outcome,cause=failure,
            inference_id=event['id'],observation_s=float(t),observation_pose=list(pose),true_node=truth,raw_node=raw,
            raw_signed_error=raw-truth,raw_abs_error=abs(raw-truth),
            raw_jump=abs(raw-previous_raw[1])>=3 if previous_raw is not None and event['id']==previous_raw[0]+1 else None,
            failure_last10=outcome=='FAILURE' and max(0.,duration-10)-1e-9<=t<=duration+1e-9,
            candidate_ids=ids,predicted_distances=dist,total_nodes=len(nodes),truth_outside_window=truth not in ids,
            node_spacing_m=node_spacing,zero_spacing_edges=int(np.count_nonzero(spacing<=1e-12)),
            completion_true_node=None,raw_completion_error=None,hmm_completion_error=None,
            delivery_true_node=None,raw_delivery_error=None,hmm_delivery_error=None)
        previous_raw=(event['id'],raw)
        cumulative=float(np.interp(t,ts,travel));delta=0. if last_travel is None else max(0.,cumulative-last_travel)
        try:
            filtered,detail=hmm.step(ids,dist,delta)
            argmin=int(ids[int(np.argmin(dist))]);counts['raw_argmin_mismatch']+=int(argmin!=raw)
            r.update(hmm_node=filtered,hmm_signed_error=filtered-truth,hmm_abs_error=abs(filtered-truth),
                hmm_jump=abs(filtered-previous_hmm[1])>=3 if previous_hmm is not None and event['id']==previous_hmm[0]+1 else None,
                odometry_travel_m=delta,raw_argmin_node=argmin,**detail)
            previous_hmm=(event['id'],filtered);last_travel=cumulative
        except ValueError as exc:
            counts['hmm_invalid_window']+=1;r.update(hmm_node=None,hmm_abs_error=None,hmm_signed_error=None,hmm_jump=None,hmm_error=str(exc))
        completed=event.get('inference_end_monotonic_ns')
        if completed is not None and clock[0]<=completed<=clock[-1]:
            k=max(0,int(np.searchsorted(clock,completed,side='right')-1));n=nearest(nodes,poses[k])
            r.update(completion_true_node=n,raw_completion_error=abs(raw-n),
                hmm_completion_error=abs(r['hmm_node']-n) if r['hmm_node'] is not None else None,
                completion_pose_age_ms=(completed-int(clock[k]))/1e6)
        delivery=received.get(event['id']);r['terminal_unapplied']=bool(delivery and delivery.get('terminal_unapplied'))
        # Phase41 marks the declaration's waypoint terminal_unapplied because
        # that path is not installed. The inference DID control the stop; it
        # is distinct from a leftover inference drained after termination.
        r['declared_stop_inference']=bool(declaration is not None and declaration['id']==event['id'])
        r['terminal_drained_inference']=r['terminal_unapplied'] and not r['declared_stop_inference']
        if delivery is not None:
            t_recv=delivery.get('latched_sim_s')
            if t_recv is not None and not r['terminal_drained_inference'] and ts[0]<=t_recv<=end+1e-9:
                k=max(0,int(np.searchsorted(ts,t_recv,side='right')-1));n=nearest(nodes,poses[k])
                r.update(delivery_s=t_recv,delivery_true_node=n,raw_delivery_error=abs(raw-n),
                    hmm_delivery_error=abs(r['hmm_node']-n) if r['hmm_node'] is not None else None)
        events.append(r)
    coverage=dict(phase=phase,run=ident,method=row['method'],scene=row['scene'],seed=row['index'],outcome=outcome,cause=failure,
        status='OK',inference_logged=len(inference),measured=len(events),hmm_measured=sum(r['hmm_node'] is not None for r in events),
        terminal_unapplied=sum(r['terminal_unapplied'] for r in events),window_limited=sum(len(r['candidate_ids'])<len(nodes) for r in events),
        declared_stop_inferences=sum(r['declared_stop_inference'] for r in events),terminal_drained_inferences=sum(r['terminal_drained_inference'] for r in events),
        truth_outside_window=sum(r['truth_outside_window'] for r in events),node_count=len(nodes),median_node_spacing_m=node_spacing,
        source_missing_files=missing,**counts)
    wrong=None
    if phase=='Phase41' and row.get('wrong_stop'):
        stop=declaration;assert stop is not None
        e=next((r for r in events if r['inference_id']==stop['id']),None)
        truth=nearest(nodes,stop['pose']);estimated=int(stop['closest_node'])
        wrong=dict(scene=row['scene'],seed=row['index'],run=ident,stop_s=stop['simulation_time_s'],goal_distance_m=row['stop_distance_m'],
            inference_id=stop['id'],estimated_node=estimated,true_node_at_stop=truth,node_error_at_stop=estimated-truth,
            true_node_at_observation=e['true_node'] if e else None,hmm_node=e['hmm_node'] if e else None,
            hmm_error_at_stop=e['hmm_node']-truth if e and e['hmm_node'] is not None else None,
            observation_to_stop_s=stop['simulation_time_s']-e['observation_s'] if e else None,
            goal_node=stop['goal_node'],raw_jump=e['raw_jump'] if e else None)
    return events,coverage,wrong


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=OUT);ap.add_argument('--document',type=Path,default=DOCUMENT);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    # Freeze the only filter specification before reading any error/outcome
    # measurements; reruns refuse a silent change of the analysis definition.
    rules_file=a.output/'rules.json'
    if rules_file.exists():assert read(rules_file)==RULES,'Analysis rules changed'
    else:save(rules_file,RULES)
    sources=[('Phase38',ROOT/'research/results/phase38/runs.json'),('Phase41',ROOT/'research/results/phase41/runs.json')]
    hashes={str(f):sha(f) for _,f in sources};events=[];coverage=[];stops=[]
    for phase,file in sources:
        rows=read(file)
        assert len(rows)==(180 if phase=='Phase38' else 15)
        for i,row in enumerate(rows,1):
            ev,c,wrong=run_analysis(row,phase,hashes);events.extend(ev);coverage.append(c)
            if wrong:stops.append(wrong)
            if i%30==0 or i==len(rows):print(f'[{phase}] {i}/{len(rows)} saved runs',flush=True)
    cohorts=group_summary(events,('phase','method','outcome'))
    failures=group_summary([r for r in events if r['outcome']!='SUCCESS'],('phase','cause'))
    method_failures=group_summary([r for r in events if r['outcome']!='SUCCESS'],('phase','method','cause'))
    scenes=group_summary(events,('phase','method','scene','outcome'),('ALL',))
    runs=group_summary(events,('phase','run','method','scene','outcome','cause'))
    clocks=[]
    for (phase,outcome),group in sorted(_groups(events,('phase','outcome')).items()):
        for clock in ('completion','delivery'):
            rows=[r for r in group if r['raw_'+clock+'_error'] is not None]
            common=[r for r in rows if r['hmm_'+clock+'_error'] is not None]
            clocks.append(dict(phase=phase,outcome=outcome,pose_clock=clock,available=len(rows),missing=len(group)-len(rows),
                raw_mae=float(np.mean([r['raw_'+clock+'_error'] for r in rows])) if rows else None,
                hmm_paired_mae=float(np.mean([r['hmm_'+clock+'_error'] for r in common])) if common else None))
    cov=[]
    for key,group in sorted(_groups(coverage,('phase','method','scene')).items()):
        cov.append(dict(zip(('phase','method','scene'),key),runs=len(group),missing_input_runs=sum(r['status']!='OK' for r in group),
            logged=sum(r.get('inference_logged',0) for r in group),measured=sum(r.get('measured',0) for r in group),
            hmm_measured=sum(r.get('hmm_measured',0) for r in group),window_limited=sum(r.get('window_limited',0) for r in group),
            declared_stop_inferences=sum(r.get('declared_stop_inferences',0) for r in group),terminal_drained_inferences=sum(r.get('terminal_drained_inferences',0) for r in group),
            truth_outside_window=sum(r.get('truth_outside_window',0) for r in group),raw_argmin_mismatch=sum(r.get('raw_argmin_mismatch',0) for r in group)))
    for name,rows in [('inferences',events),('coverage',coverage),('coverage_summary',cov),('cohorts',cohorts),('failure_types',failures),
        ('method_failure_types',method_failures),('scene_outcomes',scenes),('runs',runs),('wrong_stops',stops),('clock_comparison',clocks)]:csvout(a.output/(name+'.csv'),rows)
    save(a.output/'input_hashes.json',hashes)
    save(a.output/'analysis.json',dict(saved_runs=len(coverage),measured_inferences=len(events),wrong_stops=len(stops),simulations_started=0,new_nomad_inferences=0,
        filter_variants=1,source_sha256={str(f.relative_to(ROOT)):sha(f) for f in Path(__file__).parent.glob('*.py')},rules_sha256=sha(rules_file)))
    sections=[('측정 규칙',[dict(item=k,definition=v) for k,v in RULES.items()]),('지도·로그 가용 범위',cov),('성공/실패 전체 및 실패 전10초',cohorts),
        ('실패 유형',failures),('방법×실패 유형',method_failures),('장면×방법×결과',scenes),('추론 완료/전달 시점 보조 오차',clocks),
        ('Phase41 잘못된 정지',stops),('run별 전체·실패 전10초',runs)]
    a.document.write_text('\n\n'.join(table([{'table':name}])+'\n\n'+table(rows) for name,rows in sections)+'\n')
    print(json.dumps(dict(saved_runs=len(coverage),inferences=len(events),document=str(a.document),simulations_started=0)),flush=True)


def _groups(rows,keys):
    groups=defaultdict(list)
    for r in rows:groups[tuple(r[k] for k in keys)].append(r)
    return groups


if __name__=='__main__':main()
