"""Freeze, diagnose, recheck and report R1 using saved inputs only."""
import argparse,csv,json,time,subprocess
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase20d.recent import RecentSnapshot
from .config import HERE,PARAMETERS,verify as original_verify
from .offline import previous_controller
from .graph import HandoffGraph
from .graph_r1 import R1Graph,R1Follower,SCALE,solve,violations
from .tracking import predict,na_duration

OLD=ROOT/'research/results/phase28';OUT=ROOT/'research/results/phase28_r1';PROTOCOL=HERE/'protocol_r1.json'
MODES={'Inequality constraints incompatible':4,'Positive directional derivative for linesearch':8,'Iteration limit reached':9,'More than 3*n iterations in LSQ subproblem':3}
def read(p):return json.loads(Path(p).read_text())
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s]
def csv_write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def table(rows):
    if not rows:return '없음'
    keys=list(rows[0]);fmt=lambda x:'—' if x is None else f'{x:.5g}' if isinstance(x,float) else str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])
def quant(rows,k,q=.5):
    a=[r[k] for r in rows if r.get(k) is not None];return float(np.quantile(a,q)) if a else None
def key(c):return f"{c['scene']}_{c['index']}_{c['source_method']}_{c['native_id']}"

def freeze():
    original_verify();assert not PROTOCOL.exists(),'R1 already frozen'
    old=read(OLD/'preparation/sample_manifest.json');catalog=read(OLD/'preparation/input_inventory.json')['cases'];old_ids={c['event_key'] for c in old['cases']}
    cache={};available=[];missing=0
    for c in catalog:
        if key(c) in old_ids:continue
        if not Path(c['snapshot']['file']).exists():missing+=1;continue
        if c['output'] not in cache:cache[c['output']]=[r for r in lines(Path(c['output'])/'repair.jsonl') if r['event']=='PATH_APPLIED']
        aligned=bool(cache[c['output']][c['application_index']]['alignment']);available.append(dict(c,event_key=key(c),original_alignment=aligned))
    rng=np.random.default_rng(20261107);c0=[i for i,c in enumerate(available) if c['source_method']=='C0'];first=rng.choice(c0,100,replace=False).tolist()
    aligned=[i for i,c in enumerate(available) if c['original_alignment'] and i not in first];second=rng.choice(aligned,100,replace=False).tolist();cases=[]
    for stratum,ids in [('C0_SAFE_RANDOM',first),('ACTUAL_ALIGNMENT',second)]:
        for i in ids:cases.append(dict(available[i],stratum=stratum,snapshot_sha256=sha256_file(Path(available[i]['snapshot']['file']))))
    assert len({c['event_key'] for c in cases})==200 and not ({c['event_key'] for c in cases}&old_ids)
    manifest=dict(seed=20261107,cases=cases,scope=old['scope'],old_sample_excluded=True,overlap_old=0,missing_snapshot_excluded=missing,c0_pool=len(c0),alignment_pool=len(aligned))
    save(OUT/'sample_new.json',manifest);save(OUT/'sample_same.json',old)
    protected={str(f):sha256_file(f) for folder in [OLD] for f in folder.rglob('*') if f.is_file()}
    protected[str(ROOT/'docs/PHASE28_PREP.md')]=sha256_file(ROOT/'docs/PHASE28_PREP.md')
    source_files=[HERE/n for n in ('graph_r1.py','r1.py','test_r1.py')]
    p=dict(revision='Phase28 PREP R1',status='FROZEN_BEFORE_RECHECK',base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        original_protocol_sha256=sha256_file(HERE/'protocol.json'),parameters=PARAMETERS,source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in source_files},
        same_manifest_sha256=sha256_file(OUT/'sample_same.json'),new_manifest_sha256=sha256_file(OUT/'sample_new.json'),
        changes=dict(initialization='C0-NA at predicted B, exact72Hz integration; sample11poses including B at unchanged original cold/previous-dt knot times. At reached endpoint hold the reached pose without snapping; no future FRESH.',
            warm_start='Previous accepted dt schedules retained; previous poses replaced by NA initialization as requested.',
            horizon='Sum of frozen original H.initial(warm) dt values, bounded1..10s; no new horizon constant.',
            boundary='Remove first constant-twist equality; x0 fixed. Add initial acceleration (v_first-v0)/(dt0/2), angular analogous, as hard bounds; interior bounds unchanged.',
            scaling=SCALE.tolist(),scaling_reason='Position=.3m, heading=.4rad from frozen one-second speed limits, interval=1s; optimize z=x/scale and chain-rule Jacobians; costs unchanged.',
            output='OPTIMIZED on convergence+all constraints+certificate+deadline; otherwise INIT_ONLY if prechecked NA initial satisfies all constraints/certificate and returns within deadline; otherwise FALLBACK.',
            timeout='Original hard deadline retained: no accepted output after0.15s. TIMEOUT remains FALLBACK even if a prior initial certificate passed.',
            tracking='For R1, add the explicit initial v/w time anchor before segment-midpoint interpolation; feedback, clipping and90deg rule unchanged.'),
        diagnostics=dict(original_last_iterates='Not saved. Replay original SOLVER_FAILURE once per event, preserving original accepted warm history; original status remains authoritative and replay parity is reported.',
            dominant_violation='max normalized overshoot; SDF/.025,v/.3,w/.4,a/.5,angular/alpha,dt_lower/.1,dt_upper/1,equality_position/.05,equality_yaw/.4; physical units also saved.'),
        timing='Entire solve call including prediction, NA initialization, checks, solver, certificates and diagnostic bookkeeping; npz loading and JSON writing excluded; planning-only time also retained.',
        gate=dict(per_sample_set_n=200,optimized_min=.70,accepted_min=.90,p95_max_s=.15,require_both_sets=True),
        preserved_inputs_sha256=protected,existing_code_and_NA_unchanged=True,new_navigation=False)
    save(PROTOCOL,p);print(json.dumps(dict(protocol_sha256=sha256_file(PROTOCOL),same=200,new=200,overlap=0,pools=[len(c0),len(aligned)])))

def verify():
    original_verify();p=read(PROTOCOL);assert p['parameters']==PARAMETERS
    for f,h in p['source_sha256'].items():assert sha256_file(ROOT/f)==h,f
    assert sha256_file(HERE/'protocol.json')==p['original_protocol_sha256']
    assert sha256_file(OUT/'sample_same.json')==p['same_manifest_sha256'];assert sha256_file(OUT/'sample_new.json')==p['new_manifest_sha256']
    return p

def diagnose():
    verify();dest=OUT/'diagnosis';dest.mkdir(exist_ok=True);assert not (dest/'events.json').exists()
    original={r['event_key']:r for r in read(OLD/'offline/events.json')};cases=sorted(read(OUT/'sample_same.json')['cases'],key=lambda c:(c['output'],c['time_s']));warm={};rows=[]
    for i,c in enumerate(cases):
        saved=original[c['event_key']];field=RecentSnapshot.load(c['snapshot']['file']);B=saved['prediction']['pose'];vw=saved['prediction']['vw'];prior=warm.get(c['output'])
        g=HandoffGraph(B,vw,c['selected_path'],field,saved['alpha']);initial=g.initial(prior)
        r=dict(event_key=c['event_key'],stratum=c['stratum'],original_disposition=saved['disposition'],original_message=saved.get('message'),original_exit_mode=MODES.get(saved.get('message')),
            initial_x=initial.tolist(),initial_violation=violations(g,initial,'ORIGINAL'),warm_start=prior is not None,last_iterate_source='NOT_AVAILABLE_IN_ORIGINAL_RECORD')
        if saved['disposition']=='SOLVER_FAILURE':
            start=time.perf_counter();h=HandoffGraph(B,vw,c['selected_path'],field,saved['alpha'],start+.15);last=initial.copy();kind='INITIAL_NO_MAJOR_ITERATE';res=None
            def observe(x):
                nonlocal last,kind
                last=np.array(x).copy();kind='REPLAY_LAST_MAJOR_ITERATE';h.observe(x)
            try:
                x=h.initial(prior)
                res=minimize(h.objective,x,jac=True,method='SLSQP',bounds=h.bounds,constraints=[dict(type='ineq',fun=lambda x:h.constraints(x)[0],jac=lambda x:h.constraints(x)[1]),dict(type='eq',fun=lambda x:h.boundary(x)[0],jac=lambda x:h.boundary(x)[1])],callback=observe,options=dict(maxiter=100,ftol=1e-8))
                last=res.x.copy();kind='REPLAY_RETURNED_FINAL_ITERATE';h.check();r.update(replay_exit_mode=int(res.status),replay_message=str(res.message),replay_success=bool(res.success))
            except TimeoutError:r.update(replay_exit_mode=None,replay_message='TIMEOUT',replay_success=False)
            r.update(replay_wall_s=time.perf_counter()-start,replay_matches_original_message=r['replay_message']==saved['message'],last_iterate_source=kind,last_x=last.tolist(),last_violation=violations(h,last,'ORIGINAL'))
        if saved['accepted']:warm[c['output']]=saved
        rows.append(r);save(dest/(c['event_key']+'.json'),r)
        if (i+1)%50==0:print('[original diagnosis]',i+1,'/200',flush=True)
    save(dest/'events.json',rows)

def evaluate(sample):
    verify();dest=OUT/sample;dest.mkdir(exist_ok=True);assert not (dest/'events.json').exists(),'No automatic re-solves'
    cases=sorted(read(OUT/f'sample_{sample}.json')['cases'],key=lambda c:(c['output'],c['time_s']));old={r['event_key']:r for r in read(OLD/'offline/events.json')};cache={};warm={};rows=[]
    for i,c in enumerate(cases):
        assert sha256_file(Path(c['snapshot']['file']))==c['snapshot_sha256'];field=RecentSnapshot.load(c['snapshot']['file']);cfg=read(Path(c['output'])/'scenario.json')
        alpha=float(cfg['plant_alpha']);alpha=alpha if np.isfinite(alpha) else 2.
        controller=previous_controller(c,cache);start=time.perf_counter();prediction=predict(c['B'],c['previous_vw'],controller,c['tick'],float(cfg['plant_alpha']))
        result=solve(prediction['pose'],prediction['vw'],c['selected_path'],field,alpha,warm.get(c['output']),start)
        if sample=='same':
            np.testing.assert_allclose(prediction['pose'],old[c['event_key']]['prediction']['pose'],atol=1e-12,rtol=0)
            np.testing.assert_allclose(prediction['vw'],old[c['event_key']]['prediction']['vw'],atol=1e-12,rtol=0)
        if result['accepted']:warm[c['output']]=result
        na=na_duration(c['selected_path'],prediction['pose'],prediction['vw'][0]);result.update(sample=sample,event_key=c['event_key'],stratum=c['stratum'],source_method=c['source_method'],scene=c['scene'],index=c['index'],alpha=alpha,prediction=prediction,na_expected=na)
        result['optimized_time_difference_s']=result['trajectory_time_s']-na['total_s'] if result['output_type']=='OPTIMIZED' else None
        if result['accepted']:
            follower=R1Follower(result,0,alpha);cmd,diag=follower.control(prediction['pose'],prediction['vw'][0])
            result['first_command_delta_v']=cmd[0]-prediction['vw'][0];result['first_command_delta_w']=cmd[1]-prediction['vw'][1]
        rows.append(result);save(dest/(c['event_key']+'.json'),result)
        if (i+1)%25==0:print('[R1]',sample,i+1,'/200',flush=True)
    save(dest/'events.json',rows)

def gate(rows):
    n=len(rows);optimized=sum(r['output_type']=='OPTIMIZED' for r in rows);accepted=sum(r['output_type']!='FALLBACK' for r in rows);p95=quant(rows,'wall_s',.95)
    flags=dict(optimized=optimized/n>=.7,accepted=accepted/n>=.9,timing=p95<=.15)
    return dict(n=n,optimized=optimized,accepted=accepted,optimized_fraction=optimized/n,accepted_fraction=accepted/n,p95_s=p95,checks=flags,passed=all(flags.values()))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--diagnose',action='store_true');ap.add_argument('--evaluate',choices=['same','new']);ap.add_argument('--report',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    elif a.diagnose:diagnose()
    elif a.evaluate:evaluate(a.evaluate)
    elif a.report:report()
    else:ap.error('Choose a stage')

# report() is below so the registered module remains the single staged entry point.
def summarize(rows,sample,stratum):
    accepted=[r for r in rows if r['accepted']];optimized=[r for r in rows if r['output_type']=='OPTIMIZED'];counts=Counter(r['output_type'] for r in rows)
    return dict(sample=sample,stratum=stratum,n=len(rows),optimized=counts['OPTIMIZED'],init_only=counts['INIT_ONLY'],fallback=counts['FALLBACK'],
        optimized_fraction=counts['OPTIMIZED']/len(rows),accepted_fraction=len(accepted)/len(rows),p50_s=quant(rows,'wall_s'),p95_s=quant(rows,'wall_s',.95),
        over_015_fraction=sum(r['over_deadline'] for r in rows)/len(rows),accepted=len(accepted),
        max_w=max((r['max_abs_w'] for r in accepted),default=None),max_a=max((r['max_abs_a'] for r in accepted),default=None),
        max_angular_acceleration=max((r['max_abs_angular_acceleration'] for r in accepted),default=None),
        max_start_pose_error=max((r['start_pose_error'] for r in accepted),default=None),
        max_start_time_v_error=max((r['initial_time_anchor_speed_error'] for r in accepted),default=None),max_start_time_w_error=max((r['initial_time_anchor_omega_error'] for r in accepted),default=None),
        max_first_midpoint_dv=max((abs(r['first_midpoint_speed_delta']) for r in accepted),default=None),max_first_midpoint_dw=max((abs(r['first_midpoint_omega_delta']) for r in accepted),default=None),
        max_first_command_dv=max((abs(r['first_command_delta_v']) for r in accepted),default=None),max_first_command_dw=max((abs(r['first_command_delta_w']) for r in accepted),default=None),
        optimized_delta_time_median_s=quant(optimized,'optimized_time_difference_s'),optimized_delta_time_p95_s=quant(optimized,'optimized_time_difference_s',.95),
        initial_valid=sum(r['initial_valid'] for r in rows))

def violation_table(rows,stage,label):
    available=[r[stage] for r in rows if r.get(stage)];names=sorted({k for r in available for k in r['groups']});result=[]
    for name in names:
        q=[r['groups'][name] for r in available if name in r['groups']];numbers=[x['maximum'] for x in q if x['maximum'] is not None]
        result.append(dict(cohort=label,stage=stage,constraint=name,n=len(available),violated_events=sum(x['count']>0 for x in q),
            dominant_events=sum(r['dominant']==name for r in available),maximum=max(numbers) if numbers else None,
            p50=float(np.median(numbers)) if numbers else None,p95=float(np.quantile(numbers,.95)) if numbers else None,unit=q[0]['unit']))
    return result

def report():
    p=verify();diag=read(OUT/'diagnosis/events.json');data={s:read(OUT/s/'events.json') for s in ('same','new')};summary=[]
    status=[]
    for stratum in ('ALL','C0_SAFE_RANDOM','ACTUAL_ALIGNMENT'):
        q=[r for r in diag if r['original_disposition']=='SOLVER_FAILURE' and (stratum=='ALL' or r['stratum']==stratum)]
        for (mode,message),count in Counter((r['original_exit_mode'],r['original_message']) for r in q).items():status.append(dict(stratum=stratum,exit_mode=mode,message=message,count=count))
    csv_write(OUT/'original_solver_failures.csv',status)
    failures=[r for r in diag if r['original_disposition']=='SOLVER_FAILURE']
    vtable=violation_table(diag,'initial_violation','ORIGINAL_ALL200')+violation_table(failures,'initial_violation','ORIGINAL_FAILURE172')+violation_table(failures,'last_violation','ORIGINAL_FAILURE172_REPLAY')
    csv_write(OUT/'original_constraint_violations.csv',vtable)
    replay=Counter((r['original_exit_mode'],r.get('replay_exit_mode'),r.get('replay_message')) for r in failures)
    replay_rows=[dict(original_mode=k[0],replay_mode=k[1],replay_message=k[2],count=v) for k,v in replay.items()];csv_write(OUT/'original_replay_status.csv',replay_rows)
    for sample,rows in data.items():
        assert len(rows)==200 and len({r['event_key'] for r in rows})==200
        for stratum in ('ALL','C0_SAFE_RANDOM','ACTUAL_ALIGNMENT'):
            q=[r for r in rows if stratum=='ALL' or r['stratum']==stratum];summary.append(summarize(q,sample,stratum))
    csv_write(OUT/'summary.csv',summary)
    flat=[];r1v=[]
    for sample,rows in data.items():
        for r in rows:
            flat.append({k:r.get(k) for k in ('sample','event_key','stratum','source_method','scene','index','output_type','disposition','solver_success','exit_mode','wall_s','planning_wall_s','diagnostic_wall_s','over_deadline','initial_valid','max_abs_w','max_abs_a','max_abs_angular_acceleration','start_pose_error','first_midpoint_speed_delta','first_midpoint_omega_delta','first_command_delta_v','first_command_delta_w','optimized_time_difference_s')})
            if r['accepted']:
                assert r['max_abs_w']<=.4+1e-7 and r['max_abs_a']<=.5+1e-7 and r['max_abs_angular_acceleration']<=r['alpha']+1e-7
                assert not r['over_deadline']
        r1v+=violation_table(rows,'initial_violation',sample+'_R1_ALL')+violation_table([r for r in rows if r['output_type']=='FALLBACK'],'last_violation',sample+'_R1_FALLBACK')
    csv_write(OUT/'events.csv',flat);csv_write(OUT/'r1_constraint_violations.csv',r1v)
    gates={sample:gate(rows) for sample,rows in data.items()};passed=all(r['passed'] for r in gates.values());label='GATE_PASS' if passed else 'GATE_FAIL'
    reasons=[sample+':'+k for sample,g in gates.items() for k,ok in g['checks'].items() if not ok]
    save(OUT/'gate.json',dict(label=label,sets=gates,failed_checks=reasons,criteria=p['gate']))
    fallback=[]
    for sample,rows in data.items():
        for reason,count in Counter(r['disposition'] for r in rows if r['output_type']=='FALLBACK').items():fallback.append(dict(sample=sample,reason=reason,count=count))
    csv_write(OUT/'fallback_reasons.csv',fallback)
    preserve=all(sha256_file(Path(f))==h for f,h in p['preserved_inputs_sha256'].items());assert preserve
    same_ids={r['event_key'] for r in data['same']};new_ids={r['event_key'] for r in data['new']};assert not same_ids&new_ids
    matches=sum(r.get('replay_matches_original_message',False) for r in failures)
    performance=[{k:r[k] for k in ('sample','stratum','n','optimized','init_only','fallback','optimized_fraction','accepted_fraction','p50_s','p95_s','over_015_fraction')} for r in summary]
    limits=[{k:r[k] for k in ('sample','stratum','accepted','max_w','max_a','max_angular_acceleration','max_start_pose_error','max_start_time_v_error','max_start_time_w_error','max_first_midpoint_dv','max_first_midpoint_dw','max_first_command_dv','max_first_command_dw')} for r in summary if r['stratum']!='ALL']
    times=[{k:r[k] for k in ('sample','stratum','optimized','optimized_delta_time_median_s','optimized_delta_time_p95_s')} for r in summary if r['stratum']!='ALL']
    tests=read(OUT/'tests.json')
    text=f'''# Phase28 준비 R1 — 실패 진단과 정식화 재검사

**{label}**. 실패 조건: `{reasons}`. 기존 주행·Phase28 오프라인 결과·C0-NA 정의·원 protocol은 보존했다. Isaac·본 주행·NoMaD 추론·새 렌더는 실행하지 않았다. 요청한 초기화용 C0-NA72Hz 수치 전방 적분과 저장 입력 SLSQP만 수행했다. 새 튜닝·상수 변경·결과를 본 뒤 재풀이 없음.

R1 protocol SHA256 `{sha256_file(PROTOCOL)}`. 원 protocol SHA256 `{p['original_protocol_sha256']}`. 표본·초기화 시계·scaling·경계식·fallback/시간 규칙을 평가 전에 고정했다. 단위테스트 {tests['tests_run']}개 통과.

## 1. 기존200개 실패 진단

원래 결과: 수락26, SOLVER_FAILURE172, TIMEOUT2. 원 파일에는 exit message와 반복 수만 있고 실패한 x0/x_final은 없다. 아래 exit mode는 설치된 SciPy SLSQP의 message→mode 대응(3/4/8/9)을 적용한 것으로, 원 숫자 status가 저장되어 있었다고 주장하지 않는다.

{table(status)}

초기값은 원 B 예측값·snapshot·직전 **원래 수락 해**를 사용해200건 모두 결정적으로 복원했다. 마지막 반복은 원 SOLVER_FAILURE172건에 한해 원 정식화·상수·SLSQP 옵션·0.15s 한도로 한 번씩 **진단용 재풀이**했다. 원 message와 일치한 재풀이는 {matches}/172건이다. CPU deadline 차이 때문에 재풀이 status가 달라질 수 있으므로, 실패율은 원 로그 기준으로 보존한다. 아래 final 수치는 원래 저장 iterate가 아니라 재풀이의 returned x 또는 timeout 직전 major callback x다. 첫 major iteration도 없으면 초기값임을 개별 JSON에 표시했다.

{table(replay_rows)}

### 초기 제약 위반(원200개)

{table([r for r in vtable if r['cohort']=='ORIGINAL_ALL200'])}

### 원 실패172개: 초기값과 재풀이 마지막 반복

{table([r for r in vtable if r['cohort']!='ORIGINAL_ALL200'])}

`violated_events`는 해당 제약을 하나라도1e−7보다 더 위반한 사건 수다. maximum/p50/p95는 표에 적힌 물리 단위다. dominant_events는 사건마다 정규화 위반이 가장 큰 제약 한 종류를 센다(SDF/.025, v/.3, ω/.4, a/.5, 각가속도/α, dt하한/.1·상한/1, 첫 위치 equality/.05, 첫 yaw equality/.4). 다른 단위를 raw 값으로 직접 비교하지 않는다. 모든 값이 허용오차 안이면 NONE_FEASIBLE로 별도 집계되므로 dominant 합이 전체 수보다 작을 수 있다. 원 실패군의 초기값과 마지막 상태는 별도 CSV/JSON으로 보존했다.

## 2. 승인된 개정만 적용

- 초기화: B 예측 상태에서 동결 C0-NA를72Hz 적분한다. 10개 미래 pose와 dt의 시계는 원 H cold 초기값의 dt 또는 직전 수락 해의 dt 그대로다. 따라서 지평선은 기존Σdt(1–10s)이며 새 상수는 없다. 이전 해의 공간 초기값만 NA 궤적으로 대체하고 시간 warm start는 유지한다. 경로 끝에 도달하면 도달 pose에서 정지해 남은 시계를 채운다(끝점으로 순간이동하지 않음). 이 endpoint padding은 가속도 위반을 만들 수 있으므로 INIT_ONLY 전에 전부 검사한다.
- 첫 구간 integrate_se2 equality를 제거했다. x0=B pose는 계속 고정이다. 첫 구간 대표 속도는 그 구간 중심에 있으므로 초기 가속도는 `(v_first−v0)/(dt0/2)`, 각가속도도 같은 식으로 hard 제한한다. 내부 구간 rate는 원 식 그대로다. 실행 시간 보간에는 t=0의 v0/ω0 anchor만 추가한다. feedback gain·최종 clip·90° 규칙은 변경하지 않는다.
- scaling: `x=S·z`, S는 위치0.3m·각도0.4rad·dt1s(기존1초 속도 한계에서 정한 값). 목적·제약 Jacobian과 bounds에 같은 chain rule을 적용한다. **목적함수 자체와 원래 제약 행은 수치적으로 동일함을 테스트**했다.
- 출력: 수렴·제약·certificate·0.15s를 모두 만족하면 OPTIMIZED. 수렴/제약/certificate 실패 시, 미리 계산한 NA 초기값이 모든 제약·bounds·같은 certificate를 만족하고 시간 안에 반환되면 INIT_ONLY. 아니면 FALLBACK. 원래 시간 제한 정책은 유지하여 TIMEOUT은 INIT_ONLY로 늦게 수락하지 않는다.

원래 추종σ0.05, 비홀로노믹σ0.03, smoothingσ0.03, 여유0.15/0.05, 시간0.1Σdt, v0.3·ω0.4·a0.5·각가속도2.0, dt0.1–1.0, SLSQP100/1e−8,0.15s 한도는 그대로다. R2/R3·지도·필터·평가·C0-NA 파일은 수정하지 않았다.

## 3. 같은200개와 새200개 재검사

same은 원 manifest의 정확히 같은200개다. 예측B·속도를 원 저장값과1e−12 이내로 검산했다. new는 seed20261107, 동일한 C0 SAFE 무작위100/실제 정렬 SAFE FRESH100 규칙이며 **원200개를 제외한 풀에서** 뽑았다. 표본 내부·두 표본 사이 중복은0이다. RAW B0는 depth가 없어 두 번째 층에서도 제외하며 기존 층화 정의와 동일하다. 각 표본의 시간순·run별로 직전 수락 해의 dt만 이어간다. 선택되지 않은 사건은 풀지 않았다.

{table(performance)}

p50/p95·0.15s 초과 비율은 각 층100개 전체를 분모로 한다. 시간은 B 예측, NA 초기 적분, solver, 제약·certificate, 진단 bookkeeping까지 포함한 전체 호출이다. npz 로딩과 JSON 저장은 제외한다. planning-only와 bookkeeping 시간도 사건별로 남겼다. 지연 초과로 수락을 허용하거나 계산시간을0.15로 잘라 보고하지 않았다.

### 수락 해의 제한·시작 상태

{table(limits)}

`max_start_time_*`는 시간 보간 궤적의 t=0 anchor 오차다. 새 경계식은 첫 구간 평균속도가 v0와 같도록 요구하지 않으므로 `max_first_midpoint_dv/dw`를 별도로 보고한다. 이를 순간적인 t=0 jump와 혼동하지 않는다. 실제 첫9Hz 명령의 변화 `max_first_command_dv/dw`도 병기한다. 이는 동결 feedback·clip·기존 각속도의 감속을 포함하며, 연속시간 곡선 anchor 오차와는 다른 지표다. 최대a·각가속도에는 새 초기 boundary rate도 포함한다.

### OPTIMIZED만: 같은 사건의 C0-NA 대비 예상 시간

{table(times)}

차이는 H Σdt − C0-NA의 동결 SP 일정 적분(+필요 시 이상적 출발 정렬/감속시간)이다. 같은 B 기준이며 계산 대기·미래 FRESH·PP 추종 오차·goal 성공을 포함하지 않는다. INIT_ONLY를 이 비교에 섞지 않았다. 실제 주행 도착 시간으로 해석하지 않는다.

### R1 FALLBACK 이유

{table(fallback)}

R1 초기·마지막 위반 상세는 `r1_constraint_violations.csv`, 개별 x0/last_x와 certificate는 `same/`, `new/`에 있다. 원 실패 진단은 `diagnosis/`에 분리해 원 결과를 덮어쓰지 않았다.

## 4. 주행 준비 게이트

각 **200개 표본 전체**에서 OPTIMIZED≥70%, OPTIMIZED+INIT_ONLY≥90%, p95≤0.15s를 모두 만족해야 한다. 두 층은 각각 보고하되 요청한 게이트 분모는200이다.

{table([dict(sample=s,n=g['n'],optimized=g['optimized'],accepted=g['accepted'],optimized_fraction=g['optimized_fraction'],accepted_fraction=g['accepted_fraction'],p95_s=g['p95_s'],optimized_ok=g['checks']['optimized'],accepted_ok=g['checks']['accepted'],timing_ok=g['checks']['timing'],passed=g['passed']) for s,g in gates.items()])}

최종: **{label}**. {'두 표본 모두 기준 충족. 온라인 R1 연결 검증 후 동일20회 명령을 유지한다.' if passed else '미충족 항목: '+', '.join(reasons)+'. 주행 명령을 제공하지 않고 중단한다. 수치나 구조를 추가 조정하지 않았다.'}

재현: `/usr/bin/python3`, `PYTHONPATH=research`. 저장 입력 기반 오프라인 계산만 수행했고 venv에 패키지를 설치하지 않았다. 기존 결과·원 protocol·C0-NA hash 보존을 확인했다.
'''
    (ROOT/'docs/PHASE28_PREP_R1.md').write_text(text)
    save(OUT/'verification.json',dict(original_results_preserved=preserve,original_source_verified=True,same_inputs=200,new_inputs=200,cross_set_overlap=0,
        accepted_limits_verified=True,original_failure_replays=172,original_replay_message_matches=matches,source_hashes_frozen_before_recheck=True,new_navigation=False,gate=label))
    print(json.dumps(dict(label=label,gates=gates,failed_checks=reasons,original_replay_message_matches=matches)))
    return passed

if __name__=='__main__':main()
