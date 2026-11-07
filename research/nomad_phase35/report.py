"""Registered arrival/collision predicates; descriptive metrics never gate."""
import argparse,csv,json,math,subprocess
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,verify

def read(p):return json.loads(Path(p).read_text())
def exact_mcnemar(wins,losses):
    n=wins+losses
    return min(1.,2*sum(math.comb(n,k) for k in range(min(wins,losses)+1))/2**n) if n else 1.

def decide(rows):
    keys={(s,i,m) for s in SCENES for i in INDICES for m in METHODS}
    valid=len(rows)==75 and {(r['scene'],r['index'],r['method']) for r in rows}==keys and all(r.get('technical_validation')=='PASS' and r.get('collision') is not None for r in rows)
    counts={m:dict(n=sum(r['method']==m for r in rows),valid=sum(r['method']==m and r.get('technical_validation')=='PASS' for r in rows),
        goal=sum(r['method']==m and r.get('technical_validation')=='PASS' and bool(r.get('success')) for r in rows),
        collision=sum(r['method']==m and r.get('technical_validation')=='PASS' and bool(r.get('collision')) for r in rows)) for m in METHODS}
    pairs=[]
    for s in SCENES:
        for i in INDICES:
            block={r['method']:r for r in rows if (r['scene'],r['index'])==(s,i) and r.get('technical_validation')=='PASS'}
            if 'OURS' not in block:continue
            o=block['OURS']
            for m in METHODS[1:]:
                if m not in block:continue
                x=block[m]
                pairs.append(dict(scene=s,index=i,comparison='OURS - '+m,baseline=m,ours_goal=o['success'],other_goal=x['success'],
                    ours_collision=o['collision'],other_collision=x['collision'],
                    goal_difference=int(o['success'])-int(x['success']),
                    goal_time_difference_s=o['goal_time_s']-x['goal_time_s'] if o['success'] and x['success'] else None))
    comparison=[]
    for m in METHODS[1:]:
        pp=[r for r in pairs if r['baseline']==m];wins=sum(r['goal_difference']>0 for r in pp);losses=sum(r['goal_difference']<0 for r in pp)
        comparison.append(dict(baseline=m,n=len(pp),wins=wins,losses=losses,ties=len(pp)-wins-losses,
            both_arrived=sum(r['goal_time_difference_s'] is not None for r in pp),
            goal_time_delta_median_s=median([r['goal_time_difference_s'] for r in pp if r['goal_time_difference_s'] is not None]),mcnemar_exact_p=exact_mcnemar(wins,losses)))
    o=counts['OURS'];a=counts['ASTAR+EC'];dt=comparison[0]['goal_time_delta_median_s']
    better=o['goal']>=a['goal'] and o['collision']<=a['collision'] and (o['goal']>a['goal'] or (dt is not None and dt<0))
    equal=abs(o['goal']-a['goal'])<=1 and o['collision']==a['collision']
    graph='GRAPH_BETTER' if better else 'GRAPH_EQUAL' if equal else 'GRAPH_WORSE'
    beats={m:o['goal']>counts[m]['goal'] and o['collision']<=counts[m]['collision'] for m in METHODS[2:]}
    return dict(label=graph if valid else 'PENDING_INCOMPLETE_EVIDENCE',evidence_valid=valid,counts=counts,
        BEATS=beats if valid else {m:None for m in beats},GRAPH=graph if valid else None,
        provisional_predicates=dict(BEATS=beats,GRAPH=graph),comparisons=comparison,pairs=pairs,
        statistical_p_used_for_decision=False,planned_pairs=15)

def summary(rows):
    result=[]
    for m in METHODS:
        for s in (*SCENES,'ALL'):
            rr=[r for r in rows if r['method']==m and (s=='ALL' or r['scene']==s)];v=[r for r in rr if r.get('technical_validation')=='PASS']
            result.append(dict(method=m,scene=s,n=len(rr),valid=len(v),goal=sum(r['success'] for r in v),collision=sum(r['collision'] for r in v),
                goal_time_median_s=median([r['goal_time_s'] for r in v if r['success']]),mean_speed_m_s=median([r['mean_speed_m_s'] for r in v]),
                stopped_fraction=median([r['stopped_fraction'] for r in v]),minimum_clearance_m=median([r['minimum_clearance_m'] for r in v if r['minimum_clearance_m'] is not None]),
                omega_saturation_fraction=median([r['omega_saturation_fraction'] for r in v])))
    return result

def generate(stage):
    p=verify();rows=[read(f) for f in sorted((RUN_ROOT/'metrics').glob('*.json'))];d=decide(rows)
    state=read(RUN_ROOT/'state.json') if (RUN_ROOT/'state.json').exists() else dict(status='PREPARATION',reason='Implementation and tests')
    d.update(campaign_status=state['status'],stopped_stage=state.get('stage',stage),stop_reason=state.get('reason'),report_stage=stage,
        protocol_sha256=__import__('hashlib').sha256((HERE/'protocol.json').read_bytes()).hexdigest())
    if state['status'] in ('PARTIAL','STOP_BLOCKED','AWAITING_TECHNICAL_FIX'):d['label']=state['status']
    stats=summary(rows);mechanism=[];rtc=[];failures=[]
    for m in METHODS:
        rr=[r for r in rows if r['method']==m and r.get('technical_validation')=='PASS'];costs=[v for r in rr for v in r.get('compute_times_s',[])]
        states={s:dict(checks=sum(r.get('ec_by_state',{}).get(s,{}).get('checks',0) for r in rr),rejects=sum(r.get('ec_by_state',{}).get(s,{}).get('rejects',0) for r in rr)) for s in ('NORMAL','R2','R3')}
        for v in states.values():v['reject_fraction']=v['rejects']/v['checks'] if v['checks'] else None
        routes=Counter()
        for r in rr:routes.update(r.get('ec_fallback_routes',{}))
        mechanism.append(dict(method=m,n=len(rr),detour_triggers=sum(r.get('detour_trigger_count',0) for r in rr),detour_applied=sum(r.get('detour_applied_count',0) for r in rr),
            detour_path_total_m=sum(r.get('detour_path_total_m',0) for r in rr),detour_execution_s=sum(r.get('detour_execution_s',0) for r in rr),
            compute_n=len(costs),compute_p50_s=median(costs),compute_p95_s=float(np.quantile(costs,.95)) if costs else None,ec_by_state=states,fallback_routes=dict(routes)))
        for r in rr:
            if not r['success']:failures.append({k:r.get(k) for k in ('scene','index','method','primary_cause','minimum_goal_distance_m','last10_goal_progress_m','maximum_start_displacement_m','structural_contact','output')})
            if m=='SAFE_RTC':rtc.append({k:r.get(k) for k in ('scene','index','chunk_delay_p50_s','chunk_delay_p95_s','inference_p50_s','inference_p95_s','stopped_fraction','command_state_seconds')})
    smoke=[read(f) for f in sorted((RUN_ROOT/'smoke_metrics').glob('*.json'))]
    smoke_info=[{k:r.get(k) for k in ('scene','index','method','technical_validation','launcher_wall_s','attempt_count','output')} for r in smoke]
    smoke_errors=[{k:r.get(k) for k in ('scene','index','method','attempt','error','output')} for f in sorted((RUN_ROOT/'attempt_metrics').glob('smoke_*.json')) if (r:=read(f)).get('technical_validation')!='PASS']
    technical=[{k:r.get(k) for k in ('scene','index','method','attempt_count','error','output')} for r in rows if r.get('technical_validation')!='PASS']
    OUT.mkdir(parents=True,exist_ok=True)
    save(OUT/'runs.json',rows);save(OUT/'decision.json',d);csvout(OUT/'summary.csv',stats);csvout(OUT/'paired.csv',d['pairs']);csvout(OUT/'comparisons.csv',d['comparisons'])
    save(OUT/'mechanism.json',mechanism);save(OUT/'rtc.json',rtc);csvout(OUT/'failures.csv',failures);save(OUT/'technical_failures.json',technical);save(OUT/'smoke.json',smoke_info)
    save(OUT/'smoke_technical_failures.json',smoke_errors)
    count_text=' / '.join(f"{m} {d['counts'][m]['goal']}/{d['counts'][m]['valid']}" for m in METHODS)
    collision_text=' / '.join(f"{m} {d['counts'][m]['collision']}" for m in METHODS)
    dt=d['comparisons'][0]['goal_time_delta_median_s']
    morning=[f"1. 라벨: **{d['label']}**; BEATS: {d['BEATS']}.",f"2. 도착(유효 run): {count_text}.",f"3. 충돌: {collision_text}.",
        f"4. OURS−ASTAR+EC 도착시간 짝차이 중앙값: {dt if dt is not None else '미측정'}s; 완료 {len(rows)}/75.",
        f"5. 멈춘 단계/상태: {d['stopped_stage']} / {state['status']}; 이유: {state.get('reason') or '진행 중, 중단 없음'}. 본 실행은 재개 가능."]
    text='\n'.join(morning)+'\n\n# Phase35 주요 baseline 비교\n\n'
    text+=f"Protocol FROZEN SHA256 `{d['protocol_sha256']}`. 실험 시작 예산 기준 UTC epoch {p['budget_start_unix']}, 최대6.5시간. oracle은 원 평가기에만 사용한다. 기존 결과/방법 파일을 수정하지 않는다.\n\n"
    text+='## 동결 방법\n\n'+table(p['method_definitions'])+'\n\n'
    text+='공통 실행기는 Phase32 C0-NA PP/SP(lookahead0.25, v≤0.3, |ω|≤0.4, a≤0.5, B 이후 suffix 방향 >90°일 때만 정렬)이다. SAFE_TE의 기존 ensemble target 조향·K/가중치/만료/KEEP는 그대로이며 속도와 출발 정렬은 최신 chunk 기준이다. NOMAD_RAW는 sample0, depth/filter/fallback/RECOVER 없음. SAFE_RTC는 동결 RTC-hard 생성/SAFE/handoff와 RECOVER를 유지한다. OURS·ASTAR+EC는 동일한 Phase32 EC·24-R 결정/보수적 지도/certificate/넘김을 사용하며 A*는 Phase21 B4처럼 R2와 R3 양쪽 자리를 대체한다(λ4, smoothing0).\n\n'
    text+='저장 v2: snapshot/repair input의 values 생략, savez_compressed, STORAGE_RETROFIT 복원. 라이브 지도 계산은 그대로다. 기존 raw retention을 유지하고 run 종료 뒤 portable/cache·pycache를 정리한다. 지연D750·90초·goal0.3m·장면·평가기·seed는 동결이다.\n\n'
    text+='## 사전 판정\n\nBEATS_X: OURS 도착>X 도착 AND 충돌≤X. Graph 판정은 순서대로 GRAPH_BETTER(도착≥A*, 충돌≤A*, 그리고 도착>A* 또는 둘 다 성공한 짝 시간차 median<0), GRAPH_EQUAL(도착 차이±1 이내·충돌 같음), 나머지 GRAPH_WORSE다. 도착시간 차이는 OURS−비교법, 둘 다 성공한 짝만 사용한다. 75회 미완료/기술 무효가 남으면 모르는 충돌을 0으로 간주하지 않고 주 판정 보류, 관측된 수치와 임시 predicate만 저장한다. McNemar exact p는 참고이며 판정에 쓰지 않는다.\n\n'
    text+=table(d['comparisons'])+'\n\nBEATS 결과: `'+str(d['BEATS'])+'`; Graph: `'+str(d['GRAPH'])+'`.\n\n'
    text+='## 방법×장면\n\n'+table(stats)+'\n\n도착시간은 성공 run만의 중앙값, 속도/정지/여유/포화는 run별 값의 중앙값이다. 최소여유는 참고이며 주 판정에 사용하지 않는다.\n\n'
    text+='## 15개 scene×seed 짝\n\n'+table(d['pairs'])+'\n\n'
    text+='## 우회·EC·계산시간\n\n'+table(mechanism)+'\n\n우회 경로 길이는 실제 설치된 DETOUR polyline 길이 합, 실행시간은 APPLIED→END(종료 시 활성 구간 포함) 합이다. 계산시간은 R2/R3 4-process pool 전체 job 시간이며 inference/EC 시간과 다르다. EC는 상태별 CHECK 수/REJECT 수를 보고한다. 미사용 방법은 해당 없음이며 거절률0으로 해석하지 않는다.\n\n'
    text+='## SAFE_RTC chunk 이어받기 지연·정지\n\n'+table(rtc)+'\n\nChunk 지연=application_sim_s−observation_sim_s(D750·추론 포함); received→apply 원자료도 runs.json에 기록했다. 정지는 실제72Hz |v|<0.01 비율, command_state_seconds는9Hz 명령 유지시간 합이다.\n\n'
    text+='## 실패 분해(Phase31-D 그대로)\n\n우선순위: 기술 실패 OTHER(성능 통계 제외); box contact→BOX_COLLISION(InnerCorner 등 구조벽은 WALL); 외곽 overlap/corridor stop→WALL_COLLISION; 목표≤0.6m→NEAR_GOAL_HOVER; 모든 돌발 상자 통과→POST_PASSAGE_TIMEOUT; SLW/LC 마지막10초 목표거리 감소<0.2m→STATIC_NARROW_STUCK; 상자 출현·미통과→DETOUR_FAIL; 미출현 또는 시작 최대변위<0.5m→EARLY_STUCK; 나머지OTHER. WALL_COLLISION 분해에는 margin 정지도 포함되나 주 판정 충돌은 원 evaluator 실제 overlap 값 그대로다.\n\n'+table(failures)+'\n\n'
    text+='## Smoke와 기술 실패\n\nSmoke는 기술검증 전용이며 본 결과에서 제외하고 성능 해석하지 않는다.\n\n'+table(smoke_info)+'\n\n'+(table(technical) if technical else '본 결과 기술 실패 없음(아직 미완료인 run을 성공으로 세지 않음).')+'\n\n'
    if smoke_errors:text+='보존한 smoke 기술 실패:\n\n'+table(smoke_errors)+'\n\nNOMAD_RAW 첫 시도는 depth 없는 원 factory를 통해 이전20°/45° 실행기로 연결되어90° 기술 검사를 통과하지 못했다. 본 실행 전 Phase35의 RGB-only factory 연결만 수정했다. 방법 수치·판정·기존 파일은 변경하지 않았으며 첫 시도를 본 결과에서 제외하고 한 번만 재시도했다.\n\n'
    text+='순차 실행, 기술실패1회 재시도, smoke 같은 오류2회면 STOP_BLOCKED. 매 attempt 전30GB 미만이면 STOP_BLOCKED;6.5시간 만료 시 진행 중 run만 끝내고 PARTIAL. 완료 블록5개마다 중간 보고서를 commit·push하며 매 단계 동일하게 보존한다.\n\n'
    text+='재개: `env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase35.campaign --stage main`\n\n상태: `PYTHONPATH=research /usr/bin/python3 -m nomad_phase35.campaign --status`\n'
    doc=ROOT/'docs/PHASE35_REPORT.md';doc.write_text(text)
    return doc

def publish(doc,stage):
    paths=[str(doc.relative_to(ROOT)),str(OUT.relative_to(ROOT))]
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only','--',*paths],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m',f'Phase35 report checkpoint: {stage}','--',*paths],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',default='manual');ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    doc=generate(a.stage)
    if a.publish:publish(doc,a.stage)
if __name__=='__main__':main()
