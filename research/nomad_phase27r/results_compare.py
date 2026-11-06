"""Read-only Phase26/27-R comparison, using the frozen report and 27-F accounting.

No simulation, controller invocation, inference or planner solve. The registered
report/decision functions and all frozen source hashes are left unchanged.
"""
import argparse,csv,json,subprocess
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.config import METHODS,PRIMARY,SCENES
from nomad_phase26.decisions import classify,exclusions
from .config import OUT,RUN_ROOT,HERE,verify,check_run_root
from .report import generate as frozen_generate,DOC

STATES=['DRIVING','ALIGN_ROTATE','ALIGN_BRAKE','SP_LOW','FILTER_NO_CANDIDATE','DETOUR_COMPUTE_WAIT','RECOVER_ROTATE','FIRST_INFERENCE_WAIT','OTHER_STOP']
LABELS=['주행','정렬 회전','정렬 감속','SP 저속','필터 후보 없음','우회/수리 대기','RECOVER_ROTATE','첫 추론 대기','기타 정지']
SHORT=dict(zip(METHODS,['B0','SAFE_TE','SAFE_RTC','SAFE_ROTATE','ASTAR','C0']))

def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s] if Path(p).exists() else []
def csv_read(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
def csv_write(p,rows):
    with Path(p).open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def med(values):
    a=[x for x in values if x is not None and np.isfinite(x)];return float(np.median(a)) if a else None
def hold(times,values,mid,default):
    if not len(times):return np.full(len(mid),default)
    assert np.all(np.diff(times)>=0)
    i=np.searchsorted(times,mid+1e-10,side='right')-1
    out=np.asarray(values)[np.maximum(i,0)].copy();out[i<0]=default;return out
def table(rows):
    keys=list(rows[0]);fmt=lambda v:'—' if v is None else f'{v:.3f}' if isinstance(v,float) else str(v).replace('|','/')
    return '\n'.join(['| '+' | '.join(keys)+' |','|'+'|'.join(['---']*len(keys))+'|']+['| '+' | '.join(fmt(r[k]) for k in keys)+' |' for r in rows])
def fmt(v,places=2):return '—' if v is None else f'{v:.{places}f}' if isinstance(v,float) else str(v)
def arrow(a,b,places=2):return fmt(a,places)+' → '+fmt(b,places)

def time_budget(run,phase,hashes):
    """Exact non-G branch of the published Phase27-F measurement rules."""
    root=Path(run['output']);trace=csv_read(root/'agent_trajectory.csv')
    t=np.array([float(r['simulation_time_s']) for r in trace]);v=np.array([float(r['v_m_s']) for r in trace]);dt=np.r_[0.,np.diff(t)];mid=t-dt/2
    assert t[0]==0 and np.allclose(dt[1:],1/72,rtol=0,atol=1e-10) and v.min()>=0
    stopped=abs(v)<.02;cmd=lines(root/'phase20_commands.jsonl');ctime=[r['time_s'] for r in cmd]
    src=hold(ctime,[q.get('source','G_'+q.get('mode','UNKNOWN')) for q in cmd],mid,'UNKNOWN')
    mode=hold(ctime,[(q.get('SP') or {}).get('mode','UNKNOWN') for q in cmd],mid,'UNKNOWN')
    target=hold(ctime,[(q.get('SP') or {}).get('target',np.nan) for q in cmd],mid,np.nan).astype(float)
    recovery=hold(ctime,[q.get('recovery','NORMAL') for q in cmd],mid,'NORMAL')=='RECOVER_ROTATE'
    rotation=(mode=='ROTATE')|(src=='ALIGN_ROTATE');braking=(mode=='BRAKE')|(src=='ALIGN_BRAKE')
    for r in lines(root/'recovery_72hz.jsonl'):
        if r['state']=='RECOVER_ROTATE':recovery[int(r['tick'])]=True
        elif r['state']=='WAIT_FRESH':src[int(r['tick'])]='WAIT_FRESH';rotation[int(r['tick'])]=False;braking[int(r['tick'])]=False
    recovery|=src=='RECOVER_ROTATE';rotation&=~recovery;braking&=~recovery
    waiting=np.isin(src,['REPAIR_WAIT','DETOUR_WAIT'])
    native=lines(root/'events.jsonl');filt=[r for r in native if r.get('application_sim_s') is not None and (r.get('phase16') or {}).get('selection') is not None]
    unsafe=hold([r['application_sim_s'] for r in filt],[r['phase16']['selection']['all_unsafe'] for r in filt],mid,False).astype(bool)
    filter_stop=(src=='STOP_WAIT')&unsafe;sp_low=(mode=='GO')&(target<.3-1e-9)&~stopped
    first=min((r['application_sim_s'] for r in native if r.get('application_sim_s') is not None),default=float(t[-1]));firstwait=(mid<first)&stopped
    state=np.full(len(t),8,np.int8)
    for key,mask in [('DRIVING',~stopped),('SP_LOW',sp_low),('FILTER_NO_CANDIDATE',filter_stop),('DETOUR_COMPUTE_WAIT',waiting),('ALIGN_BRAKE',braking),('ALIGN_ROTATE',rotation),('RECOVER_ROTATE',recovery),('FIRST_INFERENCE_WAIT',firstwait)]:state[mask]=STATES.index(key)
    state[0]=8;rot=state==1;brake=state==2
    times={k+'_s':float(dt[state==i].sum()) for i,k in enumerate(STATES)}
    assert abs(sum(times.values())-t[-1])<1e-8 and abs(run['duration_s']-t[-1])<1e-8
    stop_s=float(dt[stopped].sum());align_s=times['ALIGN_ROTATE_s']+times['ALIGN_BRAKE_s'];stationary=float(dt[(rot|brake)&stopped].sum())
    uid=f"{phase}_{run['scene']}_{run['index']}_{run['method']}"
    outcome='SUCCESS' if run['success'] else 'TIMEOUT' if run['termination'] in ('simulation_timeout','navigation_wall_timeout') else 'OTHER_FAILURE'
    record=dict(run_id=uid,phase=phase,scene=run['scene'],method=run['method'],index=run['index'],outcome=outcome,duration_s=float(t[-1]),physical_stop_s=stop_s,
        physical_moving_s=float(dt[~stopped].sum()),alignment_total_s=align_s,alignment_stationary_s=stationary,
        alignment_over_stop=align_s/stop_s if stop_s else None,stationary_alignment_over_stop=stationary/stop_s if stop_s else None,
        rotate_fraction=times['ALIGN_ROTATE_s']/t[-1],brake_fraction=times['ALIGN_BRAKE_s']/t[-1],**times)
    np.savez_compressed(OUT/'time_steps'/f'{uid}.npz',t=t,dt=dt,v=v,state=state,physical_stop=stopped)
    for name in ('agent_trajectory.csv','phase20_commands.jsonl','recovery_72hz.jsonl','events.jsonl','summary.json','provenance.json'):
        p=root/name
        if p.exists():hashes[str(p)]=sha256_file(p)
    return record,state

def aggregate_budget(rows,**identity):
    assert rows
    total=sum(r['duration_s'] for r in rows);stop=sum(r['physical_stop_s'] for r in rows);stationary=sum(r['alignment_stationary_s'] for r in rows)
    r=dict(**identity,runs=len(rows),duration_s=total,physical_stop_s=stop,physical_stop_fraction=stop/total,alignment_stationary_s=stationary,
        stationary_alignment_over_stop=stationary/stop if stop else None)
    for key in STATES:
        r[key+'_s']=sum(x[key+'_s'] for x in rows);r[key+'_mean_s']=r[key+'_s']/len(rows);r[key+'_fraction']=r[key+'_s']/total
    r['alignment_over_stop']=(r['ALIGN_ROTATE_s']+r['ALIGN_BRAKE_s'])/stop if stop else None
    r['alignment_label']='ALIGNMENT_DOMINANT' if r['alignment_over_stop'] is not None and r['alignment_over_stop']>=.5 else 'NOT_DOMINANT'
    return r

def summary_rows(rows,phase):
    excluded=exclusions(rows);eligible=[r for r in rows if r['technical_validation']=='PASS' and (r['method'] not in PRIMARY or (r['scene'],r['index']) not in excluded)]
    output=[]
    for group in (*SCENES,'SUDDEN','STATIC','ALL'):
        scenes=SCENES[2:] if group=='SUDDEN' else SCENES[:2] if group=='STATIC' else SCENES if group=='ALL' else (group,)
        for method in METHODS:
            q=[r for r in eligible if r['scene'] in scenes and r['method']==method]
            speeds=[r['distance_m']/r['duration_s'] for r in q]
            output.append(dict(phase=phase,group=group,method=method,n=len(q),goal=sum(r['success'] for r in q),collision=sum(r['collision'] for r in q),
                box_collision=sum(r['obstacle_collision'] for r in q),wall_collision=sum(r['wall_overlap'] for r in q),corridor=sum(r['corridor'] for r in q),
                passage=sum(r['box_passage'] for r in q) if group not in ('SLW','LC','STATIC') else None,
                passage_eligible_n=sum(r['scene'] in SCENES[2:] for r in q),
                passage_time_median_s=med([r.get('box_passage_from_spawn_s') for r in q]),goal_time_median_s=med([r.get('goal_time_s') for r in q]),
                mean_speed_m_s=float(np.mean(speeds)) if speeds else None,stop_fraction_median=med([r['stopped_fraction'] for r in q]),
                stop_fraction_mean=float(np.mean([r['stopped_fraction'] for r in q])) if q else None))
    return output

def extend(root):
    verify();root=check_run_root(root)
    protected=[ROOT/'research/results/phase26',ROOT/'research/results/phase27f',OUT/'preparation']
    protected_hashes={str(f):sha256_file(f) for p in protected for f in p.rglob('*') if f.is_file()}
    original_decision=read(ROOT/'research/results/phase26/decision.json')
    existing_auto=read(OUT/'decision.json') if (OUT/'decision.json').exists() else None
    result=frozen_generate(root)
    if existing_auto is not None:assert result==existing_auto,'Regenerated frozen decision differs from campaign report'
    baseline=read(ROOT/'research/results/phase26/runs.json');current=read(OUT/'runs.json');assert len(baseline)==len(current)==60
    assert all(r['technical_validation']=='PASS' for r in baseline+current)
    assert {(r['scene'],r['index'],r['method']) for r in baseline}=={(r['scene'],r['index'],r['method']) for r in current}
    phases={'phase26':baseline,'phase27r':current};summary=[r for phase,rows in phases.items() for r in summary_rows(rows,phase)]
    # Reapply exactly the original classifier; no altered thresholds or tie rules.
    decisions={}
    for phase,rr in phases.items():
        d=classify([r for r in summary if r['phase']==phase]);d['excluded_scene_seed']=exclusions(rr);decisions[phase]=d
    assert decisions['phase26']==original_decision and decisions['phase27r']==result
    csv_write(OUT/'before_after_summary.csv',summary);save(OUT/'before_after_decisions.json',decisions)
    lookup={(r['phase'],r['group'],r['method']):r for r in summary}
    paired=[]
    for before in baseline:
        after=next(r for r in current if all(r[k]==before[k] for k in ('scene','index','method')))
        paired.append(dict(scene=before['scene'],index=before['index'],method=before['method'],
            before_goal=before['success'],after_goal=after['success'],before_collision=before['collision'],after_collision=after['collision'],
            before_passage=before['box_passage'],after_passage=after['box_passage'],before_passage_s=before.get('box_passage_from_spawn_s'),after_passage_s=after.get('box_passage_from_spawn_s'),
            before_mean_speed=before['distance_m']/before['duration_s'],after_mean_speed=after['distance_m']/after['duration_s'],
            before_stop_fraction=before['stopped_fraction'],after_stop_fraction=after['stopped_fraction']))
    csv_write(OUT/'before_after_seed_pairs.csv',paired)

    hashes={};budgets=[];regression=[];(OUT/'time_steps').mkdir(exist_ok=True)
    prior={r['run_id']:r for r in csv_read(ROOT/'research/results/phase27f/time_budget_runs.csv') if r['phase']=='phase26'}
    for phase,rr in phases.items():
        for run in rr:
            b,state=time_budget(run,phase,hashes);budgets.append(b)
            if phase=='phase26':
                expected=prior[b['run_id']];keys=[s+'_s' for s in STATES]+['duration_s','physical_stop_s','physical_moving_s','alignment_total_s','alignment_stationary_s','alignment_over_stop']
                err=max(abs(b[k]-float(expected[k])) for k in keys)
                with np.load(ROOT/'research/results/phase27f/time_steps'/f"{b['run_id']}.npz") as z:same=np.array_equal(state,z['state'])
                assert err<1e-8 and same,(b['run_id'],err,same)
                regression.append(dict(run_id=b['run_id'],max_numeric_error=err,identical_72hz_states=bool(same)))
        print('[time budget]',phase,len(rr),'done',flush=True)
    csv_write(OUT/'time_budget_runs.csv',budgets);csv_write(OUT/'time_budget_regression.csv',regression)
    budget_summary=[]
    for phase in phases:
        for scene in (*SCENES,'ALL'):
            for method in (*METHODS,'ALL'):
                rows=[b for b in budgets if b['phase']==phase and (scene=='ALL' or b['scene']==scene) and (method=='ALL' or b['method']==method)]
                for outcome in ('ALL','SUCCESS','TIMEOUT','OTHER_FAILURE'):
                    q=[r for r in rows if outcome=='ALL' or r['outcome']==outcome]
                    if q:budget_summary.append(aggregate_budget(q,phase=phase,scene=scene,method=method,outcome=outcome))
    csv_write(OUT/'time_budget_summary.csv',budget_summary)
    get_budget=lambda phase,method='ALL',scene='ALL',outcome='ALL':next(r for r in budget_summary if (r['phase'],r['method'],r['scene'],r['outcome'])==(phase,method,scene,outcome))
    totals={phase:get_budget(phase) for phase in phases}
    ranking=[]
    for group in (*SCENES,'SUDDEN','STATIC','ALL'):
        scenes=SCENES[2:] if group=='SUDDEN' else SCENES[:2] if group=='STATIC' else SCENES if group=='ALL' else (group,)
        for phase,rr in phases.items():
            c=lookup[phase,group,'C0'];a=lookup[phase,group,'B4_ASTAR'];wins=losses=ties=0
            for scene in scenes:
                for seed in (201,202):
                    cr=next(r for r in rr if (r['scene'],r['index'],r['method'])==(scene,seed,'C0'));ar=next(r for r in rr if (r['scene'],r['index'],r['method'])==(scene,seed,'B4_ASTAR'))
                    wins+=cr['success']>ar['success'];losses+=cr['success']<ar['success'];ties+=cr['success']==ar['success']
            goal_rank='C0 > ASTAR' if c['goal']>a['goal'] else 'C0 < ASTAR' if c['goal']<a['goal'] else 'TIED_GOALS'
            ranking.append(dict(phase=phase,group=group,n=c['n'],C0_goal=c['goal'],ASTAR_goal=a['goal'],goal_rank=goal_rank,
                C0_collision=c['collision'],ASTAR_collision=a['collision'],C0_passage=c['passage'],ASTAR_passage=a['passage'],
                C0_passage_median_s=c['passage_time_median_s'],ASTAR_passage_median_s=a['passage_time_median_s'],
                C0_wins=wins,ASTAR_wins=losses,ties=ties,registered_label=decisions[phase]['C0_vs_ASTAR'] if group=='SUDDEN' else 'DESCRIPTIVE_ONLY'))
    csv_write(OUT/'c0_astar_ranking.csv',ranking)
    measurement=read(ROOT/'research/results/phase27f/measurement_rules.json')
    save(OUT/'time_budget_rules.json',dict(source='Phase27-F non-G branch; baseline60 bitwise state regression',time_budget=measurement,
        result_speed='distance_m/duration_s per run, including stops; equal-run mean per method/scene',
        result_stop='frozen Phase26 stopped_fraction: abs(v)<.01, median across runs',budget_stop='Phase27-F abs(v)<.02, duration-weighted',
        current_run_count=60,baseline_run_count=60,no_rollout=True))
    # Provenance checks all final attempts, without reading RGB/depth payloads.
    execution_shas=Counter();source_hashes=Counter()
    for run in current:
        provenance=read(Path(run['output'])/'provenance.json');execution_shas[provenance['git_sha']]+=1
        patch=provenance['phase27r_registration']['allowed_source_change'];source_hashes[patch['after_sha256']]+=1
    provenance=dict(execution_sha_counts=dict(execution_shas),patched_execution_sha256_counts=dict(source_hashes),input_sha256=hashes,
        phase26_frozen_results_sha256=protected_hashes,analysis_script_sha256=sha256_file(Path(__file__)),
        no_new_navigation=True,no_inference=True,no_solve=True,no_frozen_source_changes=True)
    save(OUT/'comparison_provenance.json',provenance)
    make_figures(summary,budget_summary)

    def comparison_table(groups):
        rr=[]
        for group in groups:
            for method in METHODS:
                a=lookup['phase26',group,method];b=lookup['phase27r',group,method]
                rr.append(dict(장면=group,방법=method,n=arrow(a['n'],b['n']),도착=arrow(a['goal'],b['goal']),충돌=arrow(a['collision'],b['collision']),통과=arrow(a['passage'],b['passage']),
                    통과시간_s=arrow(a['passage_time_median_s'],b['passage_time_median_s']),평균속도_m_s=arrow(a['mean_speed_m_s'],b['mean_speed_m_s'],3),정지_pct=arrow(100*a['stop_fraction_median'],100*b['stop_fraction_median'])))
        return table(rr)
    before=totals['phase26'];after=totals['phase27r']
    heading=f'''# Phase27-R 결과 — Phase26 대비 정렬 prefix 수정

**기존 Phase26 판정 함수를 그대로 재적용한 결과: `{result['label']}`.** 수정 전은 `{original_decision['label']}`였다. 두 실험 모두60/60 final run이 기술 검증 PASS이며 scene×seed 제외는 없다. 새 주행·추론·계획 재풀이 없이 기존 report를 재생성하고 저장 로그의 비교·시간 회계만 추가했다. 원래 Phase26 결과와 Phase27-R 준비 자료는 보존했다.

## 수정 전후 핵심 비교

같은6방법·5장면·seed201/202, 같은 등록 판정이다. 변경된 주행 동작은 SP 출발 정렬 목표의 prefix→B 투영 이후 suffix 수정 하나다. 서로 다른 실행 시점의 두 폐루프 실험이므로 수정 전후 NoMaD 입력·경로·우회 발동 시점은 같지 않다. 이 표는 같은 seed 짝의 관측 비교이며 저장 경로 하나의 반사실이 아니다.

총 도착은 **{sum(r['success'] for r in baseline)}/60→{sum(r['success'] for r in current)}/60**, 충돌은 **{sum(r['collision'] for r in baseline)}→{sum(r['collision'] for r in current)}**다. 주행시간 중 정렬 회전은 **{before['ALIGN_ROTATE_fraction']*100:.2f}%→{after['ALIGN_ROTATE_fraction']*100:.2f}%**, 정렬 감속은 **{before['ALIGN_BRAKE_fraction']*100:.2f}%→{after['ALIGN_BRAKE_fraction']*100:.2f}%**. 정렬 감소가 C0의 등록 우위를 유지한다는 결과는 나오지 않았다.

## 1. 방법×장면 나란히 비교

모든 셀은 **Phase26 → Phase27-R**. 도착·충돌·통과는 run 수다. 정적 SLW/LC의 상자 통과는 해당 없음(—). ALL행의 n=10은 전체 run 수이며 상자 통과 대상은 그중 돌발6run이다(CSV의 passage_eligible_n에 별도 기록). 충돌은 원래 평가기의 실제 box/wall overlap이며, margin-only corridor 종료는 별도로 원래 결과 표/CSV에 남긴다. H2 통과는 두 상자 모두 통과해야1건이고, 통과시간은 첫 상자 생성부터 두 번째 상자 통과까지다. 미통과 시간은 대체하지 않으므로 통과시간 중앙값은 통과 run에 조건부이며 분모 변화에 주의한다.

평균속도는 run별 `distance_m/duration_s`(정지 포함)를 방법×장면 안에서 산술평균한다. 정지비율은 원래 Phase26 정의 `|v|<0.01`의 run별 비율 중앙값이다. 아래 시간 예산은 Phase27F의0.02기준·시간가중치이므로 두 비율을 섞지 않는다. 도착시간·box/wall 충돌 분리와 다른 원래 지표도 아래 frozen report 및 [before_after_summary.csv](../research/results/phase27r/before_after_summary.csv)에 있다.

{comparison_table(SCENES)}

### 돌발·정적·전체 합산

{comparison_table(('SUDDEN','STATIC','ALL'))}

![장면별 도착 비교](../research/results/phase27r/before_after_goal.png)

## 2. Phase27F 방식72Hz 시간 예산 재계산

원본 궤적의72Hz dt와9Hz 명령/회복 로그를 대응시켰다. 우선순위는 첫 추론 대기→RECOVER_ROTATE→정렬 회전/감속→수리/우회 계산 대기→ALL_UNSAFE STOP_WAIT→SP 저속→잔여 주행→기타 정지다. 각 tick은 한 상태에만 포함된다. SP 저속은 GO 목표속도<0.3이며 실제속도≥0.02인 구간이다. B0도 공통 SP 정렬을 사용한다.

기존 Phase26의60run을 동일 코드로 다시 계산했을 때 **Phase27F의 저장72Hz 상태 배열과 전부 일치**, 모든 시간 합의 최대 차이는 {max(x['max_numeric_error'] for x in regression):.3g}s였다. 새 run도 각 상태 시간 합=실제 지속시간이다. method×scene×성공/timeout/기타실패별 표는 [time_budget_summary.csv](../research/results/phase27r/time_budget_summary.csv)에 보존했다.

{table([dict(상태=LABELS[i],전_초=before[s+'_s'],후_초=after[s+'_s'],전_주행시간_pct=100*before[s+'_fraction'],후_주행시간_pct=100*after[s+'_fraction']) for i,s in enumerate(STATES)])}

### 남은 정렬 회전·감속(방법별)

%는 해당 방법의 총 기록시간을 분모로 한다. 실제 정지 시간(|v|<0.02) 중 정렬 상태가 차지한 비율도 병기한다. 감속 중 실제 이동은 마지막 열의 분자에서 제외한다.

{table([dict(방법=m,회전_s=arrow(get_budget('phase26',m)['ALIGN_ROTATE_s'],get_budget('phase27r',m)['ALIGN_ROTATE_s']),회전_pct=arrow(100*get_budget('phase26',m)['ALIGN_ROTATE_fraction'],100*get_budget('phase27r',m)['ALIGN_ROTATE_fraction']),감속_s=arrow(get_budget('phase26',m)['ALIGN_BRAKE_s'],get_budget('phase27r',m)['ALIGN_BRAKE_s']),감속_pct=arrow(100*get_budget('phase26',m)['ALIGN_BRAKE_fraction'],100*get_budget('phase27r',m)['ALIGN_BRAKE_fraction']),물리정지_pct=arrow(100*get_budget('phase26',m)['physical_stop_fraction'],100*get_budget('phase27r',m)['physical_stop_fraction']),정지중정렬_pct=arrow(100*get_budget('phase26',m)['stationary_alignment_over_stop'],100*get_budget('phase27r',m)['stationary_alignment_over_stop'])) for m in (*METHODS,'ALL')])}

Phase27F의 문자 그대로의 `(정렬회전 전체+정렬감속 전체)/물리적 정지시간`은 {before['alignment_over_stop']*100:.2f}%→{after['alignment_over_stop']*100:.2f}%이며, 감속 중 이동까지 포함하여100%를 넘을 수 있다. 실제 정지 tick에 한정하면 **{before['stationary_alignment_over_stop']*100:.2f}%→{after['stationary_alignment_over_stop']*100:.2f}%**다. 이 시간 진단은 Phase26 성능 판정과 별개다.

![시간 예산 비교](../research/results/phase27r/before_after_time_budget.png)

## 3. 동결 판정과 C0 대 B4 순위 변화

{table([dict(항목=k,Phase26=str(original_decision[k]),Phase27R=str(result[k])) for k in ('label','C0_BETTER_vs','C0_vs_ASTAR','STATIC_OK','satisfied','unsatisfied')])}

순위는 우선 도착 수만으로 비교하고 충돌을 별도 표시한다. SUDDEN행에만 원래 C0_vs_ASTAR 등록 라벨을 적용하며, scene/전체 행은 서술용이다. 임의의 종합 점수나 새 tie-break를 만들지 않았다.

{table([dict(장면=group,C0도착=arrow(lookup['phase26',group,'C0']['goal'],lookup['phase27r',group,'C0']['goal']),B4도착=arrow(lookup['phase26',group,'B4_ASTAR']['goal'],lookup['phase27r',group,'B4_ASTAR']['goal']),도착순위=arrow(next(r['goal_rank'] for r in ranking if r['phase']=='phase26' and r['group']==group),next(r['goal_rank'] for r in ranking if r['phase']=='phase27r' and r['group']==group)),C0충돌=arrow(lookup['phase26',group,'C0']['collision'],lookup['phase27r',group,'C0']['collision']),B4충돌=arrow(lookup['phase26',group,'B4_ASTAR']['collision'],lookup['phase27r',group,'B4_ASTAR']['collision'])) for group in (*SCENES,'SUDDEN','STATIC','ALL')])}

돌발 합산에서 C0/B4 도착은 **5/6 vs3/6 → 4/6 vs4/6**으로 C0 우위에서 동률로 바뀌었다. 동시에 충돌이 **0 vs0 → 1 vs0**이 되어 C0의 안전 비열등 조건이 깨졌다. 따라서 등록 C0_vs_ASTAR는 **BETTER→WORSE**이며, 도착 수가 A*보다 작아졌기 때문이라는 해석은 틀리다. H1의 C0 도착2→1·충돌0→1, H2의 B4 도착0→1이 이 차이에 기여했다. 전체10run 도착은 C0/B4 **6 vs5 → 6 vs6**이다. 돌발 상자 통과는 C0/B4 **6 vs4 → 4 vs6**으로 바뀌었다.

각 scene×seed에서 C0가 이긴/진/동률인 수와 통과시간은 [c0_astar_ranking.csv](../research/results/phase27r/c0_astar_ranking.csv), 방법별 수정 전후 같은 seed 결과는 [before_after_seed_pairs.csv](../research/results/phase27r/before_after_seed_pairs.csv)에 있다. 표본이 작고 수정으로 폐루프 궤적·관측이 바뀌었으므로 시간 감소만으로 충돌 원인이나 우회 성능 기여를 확정하지 않는다.

## 4. 재현·검증

실행 SHA별 run 수: `{dict(execution_shas)}`. 수정 SP 파일 SHA256은60run 모두 `{next(iter(source_hashes))}`로 일치한다. 기존 campaign report의 판정과 이번 재생성 판정이 일치하고, Phase26의 판정 함수와 원래 결정 파일도 일치한다. source/입력 hash와 보존 결과 hash는 `comparison_provenance.json`, 검사 결과는 `comparison_validation.json`에 기록했다.

재생성 명령(저장 로그만): `PYTHONPATH=research /usr/bin/python3 -m nomad_phase27r.results_compare --run-root ../artifacts/isaac6/phase27r_pilot_01`. 이는 기존 `nomad_phase27r.report.generate`를 먼저 호출한 뒤 비교표·시간 예산을 추가한다. 기존 frozen report·판정·주행 코드는 수정하지 않았다. venv 설치 없음.

---

## 기존 report 전체(동결 판정·지표)

'''
    original_text=DOC.read_text();DOC.write_text(heading+original_text.replace('# Phase27-R — Phase26 suffix-alignment bug-fix rerun','### Registered report',1))
    assert all(sha256_file(Path(p))==h for p,h in protected_hashes.items()),'Pre-existing baseline/preparation artifact changed'
    assert all(sha256_file(Path(p))==h for p,h in hashes.items()),'Raw input changed'
    validation=dict(runs_per_phase={p:len(r) for p,r in phases.items()},source_verify_passed=True,baseline_72hz_bitwise_matches=len(regression),
        baseline_max_numeric_error=max(x['max_numeric_error'] for x in regression),phase26_label_unchanged=True,campaign_label_unchanged=True,
        raw_inputs_unchanged=True,baseline_and_preparation_unchanged=True,no_navigation=True,no_rollout=True)
    save(OUT/'comparison_validation.json',validation)
    print(json.dumps(dict(label=result['label'],before_label=original_decision['label'],time_totals=totals,validation=validation),ensure_ascii=False))
    return result

def make_figures(summary,budget):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,5,figsize=(16,4),sharey=True);x=np.arange(len(METHODS))
    for ax,scene in zip(axs,SCENES):
        for offset,phase,color in [(-.18,'phase26','#999999'),(.18,'phase27r','#2274a5')]:
            q={r['method']:r for r in summary if r['phase']==phase and r['group']==scene}
            ax.bar(x+offset,[q[m]['goal'] for m in METHODS],.36,color=color,label=phase)
        ax.set_title(scene);ax.set_xticks(x,[SHORT[m] for m in METHODS],rotation=70,ha='right');ax.set_ylim(0,2.5);ax.set_yticks([0,1,2])
    axs[0].set_ylabel('Goal successes /2');axs[-1].legend(fontsize=8);fig.suptitle('Phase26 -> Phase27-R: matched seeds, unchanged pilot rules');fig.tight_layout();fig.savefig(OUT/'before_after_goal.png',dpi=150);plt.close(fig)
    colors=['#4c956c','#e76f51','#f4a261','#8ab17d','#b39ddb','#779ecb','#c77dff','#c2b280','#b7b7b7']
    fig,axs=plt.subplots(1,2,figsize=(14,5),sharey=True)
    for ax,phase in zip(axs,['phase26','phase27r']):
        q={r['method']:r for r in budget if r['phase']==phase and r['scene']=='ALL' and r['outcome']=='ALL'};bottom=np.zeros(len(METHODS))
        for s,col in zip(STATES,colors):
            v=np.array([100*q[m][s+'_fraction'] for m in METHODS]);ax.bar(x,v,bottom=bottom,label=s,color=col);bottom+=v
        ax.set_xticks(x,[SHORT[m] for m in METHODS],rotation=40,ha='right');ax.set_title(phase);ax.set_ylim(0,100);ax.set_ylabel('% recorded driving-clock time')
    axs[-1].legend(loc='upper left',bbox_to_anchor=(1,1),fontsize=8);fig.tight_layout();fig.savefig(OUT/'before_after_time_budget.png',dpi=150);plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,default=RUN_ROOT);a=ap.parse_args();extend(a.run_root)

if __name__=='__main__':main()
