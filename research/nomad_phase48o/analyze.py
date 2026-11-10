"""Saved-log replay only:argmin,HMM,zero-error graph upper bound,+one2% arm."""
import argparse,json,time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import multiprocessing as mp
import numpy as np
from nomad_phase42l.filter import WindowHMM
from nomad_phase42l.analyze import read,sha,save,csvout,table
from .data import ROOT,PHASES,NOISE_SEED,load_run
from .graph import FixedLag,NOISE_FRACTION,LAG_S,REVERSE_ALLOWANCE_M

OUT=ROOT/'research/results/phase48o';DOC=ROOT/'docs/PHASE48O.md'
MODELS=('ARGMIN','HMM_FORWARD','FG_HARD_0ERR_UPPER_BOUND','FG_2PCT_ONE_DRAW')
RULES=dict(primary_title='주 결과:오도메트리 오차0의 시뮬레이터 이상조건 상한; 실제 시스템 성능 보장이 아님',
    inputs='Final recorded attempts in Phase43-P,44-P,45-P,46-P,47-C,all stored HMM and original-localization runs',
    reference='Topomap node world-pose XY polyline; continuous cumulative arclength; duplicate-node ties use smaller index',
    argmin='Minimum logged distance in the logged candidate window,not HMM-run logged closest_node',
    hmm='Frozen42-L/43 forward filter,logged candidate window; logged cumulative odometry when present,otherwise saved72Hz path length',
    main_motion='On-reference edge:s[k]-s[k-1]=project(p[k])-project(p[k-1]) exactly by variable elimination',
    off_path='Any72Hz pose between inference observations at distance>=0.5m from reference => no signed increment;only abs(delta_s)<=recorded travel length',
    noise_seed=NOISE_SEED,noise='One standard-normal draw per inference interval,stable run hash substream; no tuning/repeated draws',
    noisy_on_path='measured delta=projected delta+N(0,(0.02*abs(delta))²),Gaussian factor with exactly that sigma;zero sigma stays exact',
    noisy_off_path='no direction:measured upper bound=max(0,travel+N(0,(0.02*travel)²));one-sided Gaussian excess factor with that sigma;zero travel stays exact',
    noise_scope='User-specified2% sensitivity model,not empirically calibrated wheel-odometry covariance;reference/ground-truth evaluation remains clean',
    visual='Mixture over logged node positions:weights softmax(-distance),Gaussian position kernel sigma=median positive node spacing/sqrt(12)',
    robust='Cauchy scale1 on sqrt(2 negative-log-mixture-likelihood);objective log(1+2*NLL),fixed before results',
    monotonic=f'Weak prior:max(0,-delta_s-{REVERSE_ALLOWANCE_M})/median_node_spacing,squared;hard odometry takes priority',
    lag=f'{LAG_S}s causal rolling factor window;expired factors dropped,no extra boundary prior or future observations;previous states warm-start only',
    solver='SLSQP analytical objective gradient,linear constraints,maxiter100,ftol1e-8;starts=warm solution plus each current logged-node-aligned trajectory',
    acceptance='Solver success and constraint violation<=1e-7m;failures remain missing,not silently replaced by another estimator',
    node='Latest optimized s chooses nearest node arclength;truth is nearest node XY at image observation pose',
    jump='abs(delta estimated node)>=3 per consecutive inference;first/missing predecessor excluded',
    virtual_stop='Estimated node==goal at an actually delivered inference;false if recorded latch-pose goal distance>0.5m',
    virtual_counts='Candidate false events plus first-virtual-stop per run;after virtual stop remaining data are diagnostics,not a new closed-loop run',
    virtual_missing='Missing prior estimates make a first-stop outcome unknown;post-termination drained results ineligible,actual declaration result eligible',
    limitations='Logged windows only:unobserved node distances not generated.Graph kernel tails/odometry can extrapolate outside current window;count separately',
    ideal_limit='Projected increments/off-reference flags use exact simulator poses and reference geometry:upper bound.Exact on-path increments make monotonic factor constant there',
    no_driving_claim='No rerender,NoMaD inference,controller rollout,or new driving.Original windows and trajectories were produced by their original policies',
    reporting='All available estimates plus paired-common subsets;H2 and SLW explicit;Phase44 changed appearance identified separately')


def analyze_run(item):
    phase,row=item;hashes={};records,node_s,spacing,coverage=load_run(row,phase,hashes)
    hmm=WindowHMM(len(node_s),spacing);hard=FixedLag(node_s,spacing);noisy=FixedLag(node_s,spacing,noisy=True)
    results=[];intervals=[];first={m:None for m in MODELS};unknown_before={m:False for m in MODELS}
    previous={};previous_total=None;hmm_checks=0
    for record in records:
        ids=record['candidate_ids'];dist=record['distances'];raw=int(ids[int(np.argmin(dist))])
        if record['logged_raw_argmin'] is not None:assert raw==record['logged_raw_argmin']
        if not record['has_logged_hmm']:assert raw==record['logged_closest']
        delta=0. if previous_total is None else max(0.,record['odometry_total_m']-previous_total)
        h,hd=hmm.step(ids,dist,delta);previous_total=record['odometry_total_m']
        if record['has_logged_hmm']:assert h==record['logged_closest'];hmm_checks+=1
        gh,dh=hard.step(record);gn,dn=noisy.step(record)
        e=record['edge']
        if e['has_predecessor']:
            sigma=NOISE_FRACTION*(e['travel_m'] if e['off_path'] else abs(e['projected_delta_m']))
            intervals.append(dict(run=record['run'],phase=phase,scene=record['scene'],seed=record['seed'],method=record['method'],inference_id=record['id'],
                time_s=record['time_s'],off_path=e['off_path'],off_path_episode=e['off_path_episode'],travel_m=e['travel_m'],
                projected_delta_m=e['projected_delta_m'],noise_z=e['noise_z'],sigma_m=sigma,
                noisy_measurement_m=max(0.,e['travel_m']+sigma*e['noise_z']) if e['off_path'] else e['projected_delta_m']+sigma*e['noise_z']))
        for model,node,detail in ((MODELS[0],raw,{}),(MODELS[1],h,hd),(MODELS[2],gh,dh),(MODELS[3],gn,dn)):
            valid=node is not None;prev=previous.get(model)
            event=dict(run=record['run'],phase=phase,scene=record['scene'],seed=record['seed'],method=record['method'],source_localization=record['source_localization'],
                appearance=record['appearance'],model=model,inference_id=record['id'],observation_s=record['time_s'],estimated_node=node,true_node=record['true_node'],
                signed_error=node-record['true_node'] if valid else None,abs_error=abs(node-record['true_node']) if valid else None,
                jump=bool(abs(node-prev[1])>=3) if valid and prev is not None and prev[1] is not None and prev[0]+1==record['id'] else None,
                true_node_outside_window=record['true_node'] not in ids,estimated_outside_window=node not in ids if valid else None,
                eligible_virtual_stop=record['virtual_stop_eligible'],delivery_s=record['delivery_s'],delivery_distance_m=record['delivery_distance_m'],
                observation_goal_distance_m=record['goal_distance_observation_m'],estimated_goal=bool(node==record['goal_node']) if valid else None,
                virtual_false_event=bool(node==record['goal_node'] and record['delivery_distance_m']>.5) if valid and record['virtual_stop_eligible'] else None,
                off_path_interval=e['off_path'],solve_success=detail.get('success',True),s_m=detail.get('s_m'),solve_s=detail.get('solve_s'),
                window_n=detail.get('window_n'),starts=detail.get('starts'),hmm_window_reset=detail.get('window_reset'),
                max_hard_equality_error_m=detail.get('max_hard_equality_error_m'),max_original_travel_bound_excess_m=detail.get('max_original_travel_bound_excess_m'),
                solve_attempts=detail.get('attempts'))
            if record['virtual_stop_eligible'] and first[model] is None:
                if not valid:unknown_before[model]=True
                elif event['estimated_goal']:
                    first[model]=dict(inference_id=record['id'],delivery_s=record['delivery_s'],distance_m=record['delivery_distance_m'],
                        false_stop=record['delivery_distance_m']>.5,reliable_first=not unknown_before[model])
            previous[model]=(record['id'],node);results.append(event)
    stops=[]
    for model in MODELS:
        stop=first[model]
        stops.append(dict(run=coverage['run'],phase=phase,scene=row['scene'],seed=row['index'],method=row['method'],model=model,
            first_virtual_goal=stop is not None,first_outcome_known=(stop['reliable_first'] if stop else not unknown_before[model]),
            first_virtual_wrong=stop['false_stop'] if stop and stop['reliable_first'] else None,
            first_stop_inference_id=stop['inference_id'] if stop else None,stop_distance_m=stop['distance_m'] if stop else None,
            first_stop_s=stop['delivery_s'] if stop else None))
    # Replay of the recorded source estimator must reproduce its declaration.
    actual_model=MODELS[1] if records and records[0]['has_logged_hmm'] else MODELS[0]
    actual=first[actual_model]
    if row.get('declared_arrival'):
        assert actual is not None and actual['inference_id']==row['stop_inference_id']
        assert abs(actual['distance_m']-row['stop_distance_m'])<1e-9
    coverage.update(hmm_logged_checks=hmm_checks,source_localization=records[0]['source_localization'] if records else None,
        virtual_eligible_inferences=sum(r['virtual_stop_eligible'] for r in records),window_limited=sum(len(r['candidate_ids'])<len(node_s) for r in records))
    return results,intervals,stops,coverage,hashes


def aggregate(events,stops,group_fields):
    groups=defaultdict(list);stopgroups=defaultdict(list)
    for e in events:groups[tuple(e[k] for k in group_fields)+(e['model'],)].append(e)
    for s in stops:stopgroups[tuple(s[k] for k in group_fields)+(s['model'],)].append(s)
    rows=[]
    for key,group in sorted(groups.items()):
        valid=[e for e in group if e['abs_error'] is not None];errors=[e['abs_error'] for e in valid];jumps=[e['jump'] for e in group if e['jump'] is not None]
        virtual=[e for e in valid if e['virtual_false_event'] is not None];run_stops=stopgroups.get(key,[])
        timing=[e['solve_s'] for e in group if e['solve_s'] is not None]
        rows.append(dict(zip((*group_fields,'model'),key),runs=len({e['run'] for e in group}),inferences=len(group),valid=len(valid),
            missing=len(group)-len(valid),mae=float(np.mean(errors)) if errors else None,p95_nodes=float(np.quantile(errors,.95)) if errors else None,
            jumps=sum(jumps),jump_denominator=len(jumps),jump_rate=sum(jumps)/len(jumps) if jumps else None,
            virtual_stop_eligible=len(virtual),false_goal_events=sum(e['virtual_false_event'] for e in virtual),
            first_virtual_stop_runs=sum(s['first_virtual_goal'] for s in run_stops),first_virtual_wrong_runs=sum(s['first_virtual_wrong'] is True for s in run_stops),
            first_outcome_unknown_runs=sum(not s['first_outcome_known'] for s in run_stops),
            estimates_outside_logged_window=sum(e['estimated_outside_window'] for e in valid),truth_outside_window=sum(e['true_node_outside_window'] for e in group),
            solve_p50_s=float(np.median(timing)) if timing else None,solve_p95_s=float(np.quantile(timing,.95)) if timing else None))
    return rows


def paired_rows(events):
    groups=defaultdict(dict)
    for e in events:groups[(e['run'],e['inference_id'])][e['model']]=e
    pairs=[]
    for scene in ('ALL','H2','SLW','L2','LC','H1'):
        for target,reference in ((MODELS[1],MODELS[0]),(MODELS[2],MODELS[0]),(MODELS[2],MODELS[1]),(MODELS[3],MODELS[2])):
            rows=[g for g in groups.values() if (scene=='ALL' or g[target]['scene']==scene) and g[target]['abs_error'] is not None and g[reference]['abs_error'] is not None]
            diff=[g[target]['abs_error']-g[reference]['abs_error'] for g in rows]
            pairs.append(dict(scene=scene,target=target,reference=reference,paired_n=len(rows),
                target_mae=float(np.mean([g[target]['abs_error'] for g in rows])) if rows else None,
                reference_mae=float(np.mean([g[reference]['abs_error'] for g in rows])) if rows else None,
                mae_difference=float(np.mean(diff)) if diff else None,better_events=sum(x<0 for x in diff),worse_events=sum(x>0 for x in diff)))
    return pairs


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=OUT);ap.add_argument('--document',type=Path,default=DOC);ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
    assert 1<=a.workers<=4;a.output.mkdir(parents=True,exist_ok=True)
    rules=a.output/'rules.json'
    if rules.exists():assert read(rules)==RULES,'Refuse unregistered analysis change'
    else:save(rules,RULES)
    hashes={};inputs=[]
    for phase in PHASES:
        file=ROOT/f'research/results/{phase}/runs.json';hashes[str(file)]=sha(file)
        inputs.extend((phase,r) for r in read(file))
    assert len(inputs)==111
    start=time.perf_counter();events=[];intervals=[];stops=[];coverage=[]
    iterator=map(analyze_run,inputs) if a.workers==1 else None
    pool=None
    if a.workers>1:
        pool=ProcessPoolExecutor(max_workers=a.workers,mp_context=mp.get_context('spawn'));iterator=pool.map(analyze_run,inputs)
    try:
        for i,(ev,edge,st,cov,hh) in enumerate(iterator,1):
            events.extend(ev);intervals.extend(edge);stops.extend(st);coverage.append(cov);hashes.update(hh)
            if i%5==0 or i==len(inputs):print(f'[saved-log] {i}/{len(inputs)} runs; {time.perf_counter()-start:.1f}s',flush=True)
    finally:
        if pool:pool.shutdown(wait=True,cancel_futures=True)
    overall=aggregate(events,stops,());scenes=aggregate(events,stops,('scene',));cohorts=aggregate(events,stops,('phase','method','scene'))
    paired=paired_rows(events);main=[r for r in overall if r['model']!=MODELS[3]];aux=[r for r in overall if r['model'] in MODELS[2:]]
    for name,data in [('inferences',events),('odometry_intervals',intervals),('first_virtual_stops',stops),('coverage',coverage),
        ('summary',overall),('scene_summary',scenes),('cohort_summary',cohorts),('paired_common',paired)]:csvout(a.output/(name+'.csv'),data)
    save(a.output/'input_hashes.json',hashes)
    result=dict(saved_runs=len(inputs),inferences=len(events)//4,elapsed_s=time.perf_counter()-start,workers=a.workers,
        simulations_started=0,new_nomad_inferences=0,noise_realizations=1,noise_seed=NOISE_SEED,rules_sha256=sha(rules),
        source_sha256={str(f.relative_to(ROOT)):sha(f) for f in Path(__file__).parent.glob('*.py')})
    save(a.output/'analysis.json',result)
    sections=[('주 결과 — 오도메트리 오차0 이상조건 상한',main),('보조 — 사전 고정2% 잡음1회;실측 covariance 아님',aux),
        ('측정 정의와 상한 해석의 한계',[dict(item=k,value=v) for k,v in RULES.items()]),
        ('장면별(H2·SLW 포함) — HARD는0오차 상한',scenes),('동일 측정가능 입력의 짝 비교',paired),
        ('HMM/원래 위치추정·외관별 원 run 코호트',cohorts),('이탈 구간 수와 로그 가용 범위',coverage),
        ('첫 가상 정지 run별 결과',stops),('실행 정보',[result])]
    a.document.write_text('\n\n'.join(table([dict(table=name)])+'\n\n'+table(data) for name,data in sections)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
