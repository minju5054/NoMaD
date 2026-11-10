"""Saved-data braking EC and execution-graph feasibility reports."""
import json
from collections import Counter,defaultdict
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase31p.report import table,median
from nomad_phase32o.evaluate import save,csvout
from .evaluate import OUT


def quantile(values,q):return float(np.quantile(values,q)) if values else None

def braking_summary(records,fields):
    groups=defaultdict(list)
    for r in records:groups[tuple(r[k] for k in fields)].append(r)
    result=[]
    for key,group in sorted(groups.items()):
        valid=[e for e in group if e.get('status')=='ASSESSED'];matched=[e for e in valid if e.get('replay_match')];flip=[e for e in matched if e['pass_to_reject']]
        result.append(dict(zip(fields,key),recorded=len(group),assessed=len(valid),missing_maps=sum(e['status']=='MISSING_EXACT_MAP' for e in group),
            other_excluded=len(group)-len(valid)-sum(e['status']=='MISSING_EXACT_MAP' for e in group),replay_matches=len(matched),replay_mismatches=len(valid)-len(matched),
            logged_pass=sum(e['logged_passed'] for e in group),confirmed_pass_to_reject=len(flip),
            fraction_of_reproduced_pass=len(flip)/sum(e['logged_passed'] for e in matched) if any(e['logged_passed'] for e in matched) else None,
            endpoint_flips=sum(e['stop_reason']=='ENDPOINT' for e in flip),horizon_flips=sum(e['stop_reason']=='HORIZON' for e in flip),
            flipped_speed_median_m_s=median([e['actual_v_m_s'] for e in flip]),flipped_remaining_median_m=median([e['remaining_length_m'] for e in flip])))
    return result

def graph_summary(jobs,results,fields):
    groups=defaultdict(list);by={r['event_id']:r for r in results};output=[]
    for j in jobs:groups[tuple(j[k] for k in fields)].append(j)
    for key,jj in sorted(groups.items()):
        eligible=[j for j in jj if j['graph_eligible']];rr=[by[j['event_id']] for j in eligible if j['event_id'] in by];good=[r for r in rr if r['found']]
        chosen=[r['results'][r['selected']] for r in good];all_initial_reject=[r for r in rr if r['all_original_reject']]
        t=[r['eight_start_s'] for r in rr];candidate_t=[c['wall_s'] for r in rr for c in r['results'] if c.get('solver_started')]
        solve_totals=[sum(c['wall_s'] for c in r['results']) for r in rr if any(c.get('solver_started') for c in r['results'])]
        output.append(dict(zip(fields,key),raw_reject_checks=sum(j['raw_record_count'] for j in jj),unique_full_speed_inputs=len(jj),eligible=len(eligible),completed=len(rr),
            missing_map=sum(j['graph_exclusion']=='MISSING_EXACT_MAP' for j in jj),other_excluded=sum(not j['graph_eligible'] and j['graph_exclusion']!='MISSING_EXACT_MAP' for j in jj),
            found=len(good),found_fraction=len(good)/len(rr) if rr else None,
            displacement_mean_median_m=median([c['mean_displacement_m'] for c in chosen]),displacement_max_median_m=median([c['max_displacement_m'] for c in chosen]),
            displacement_max_overall_m=max((c['max_displacement_m'] for c in chosen),default=None),
            eight_start_p50_s=median(t),eight_start_p95_s=quantile(t,.95),per_start_p50_s=median(candidate_t),per_start_p95_s=quantile(candidate_t,.95),
            timed_solver_events=len(solve_totals),solve_verify_sum_p50_s=median(solve_totals),solve_verify_sum_p95_s=quantile(solve_totals,.95),
            initial_state_infeasible=sum(not r['initial_state_pass'] for r in rr),original_any_tail_pass=sum(r['original_any_tail_pass'] for r in rr),
            all_original_reject=len(all_initial_reject),found_when_all_original_reject=sum(r['found'] for r in all_initial_reject),
            resampling_only_rescue=sum(r['found'] and r['results'][r['selected']]['max_displacement_m']<=1e-6 for r in all_initial_reject),
            optimized_rescue=sum(r['found'] and r['results'][r['selected']]['max_displacement_m']>1e-6 for r in all_initial_reject),
            selected_under_1um_modification=sum(c['max_displacement_m']<=1e-6 for c in chosen),
            mean_edit_p95_m=quantile([c['mean_displacement_m'] for c in chosen],.95),
            optimized_mean_edit_median_m=median([c['mean_displacement_m'] for c in chosen if c['max_displacement_m']>1e-6]),
            optimized_max_edit_median_m=median([c['max_displacement_m'] for c in chosen if c['max_displacement_m']>1e-6]),
            selected_displacement_from_B_le_5cm=sum(c['displacement_from_B_m']<=.05 for c in chosen),
            selected_travel_median_m=median([c['travel_m'] for c in chosen]),independent_ec_rejected_numerically_feasible=sum(c.get('independent_ec_pass') is False for r in rr for c in r['results'])))
    return output

def main():
    protocol=json.loads((OUT/'protocol.json').read_text());runs=[json.loads(p.read_text()) for p in sorted((OUT/'replay').glob('*.json'))]
    records=[e for r in runs for e in r['records']];jobs=json.loads((OUT/'graph_inputs.json').read_text());slow=json.loads((OUT/'slow_inputs_count_only.json').read_text())
    results=[json.loads(p.read_text()) for p in sorted((OUT/'graph').glob('*.json'))]
    bs=braking_summary(records,('phase','scene'))+braking_summary(records,('phase',))+braking_summary(records,())
    for r in bs:r.setdefault('phase','ALL');r.setdefault('scene','ALL')
    flips=[{k:e.get(k) for k in ('uid','phase','scene','method','seed','condition','check_id','tick','time_s','scope','actual_v_m_s','speed_cap_m_s',
        'remaining_length_m','logged_clearance_m','new_clearance_m','stop_reason','brake_start_s','braking_s','control_rounding_ticks','map_frame','path_hash')} for e in records if e.get('pass_to_reject')]
    mismatch=[e for e in records if e.get('status')!='ASSESSED' or not e.get('replay_match')]
    csvout(OUT/'braking_summary.csv',bs);csvout(OUT/'braking_flips.csv',flips);save(OUT/'replay_exclusions_or_mismatches.json',mismatch)
    exclusions=Counter(e['status'] for e in records);coverage=[]
    for phase in ('phase47c','phase52p'):
        rr=[r for r in runs if r['uid'].startswith(phase+'/')];coverage.append(dict(phase=phase,runs=len(rr),runs_with_ec=sum(bool(r['records']) for r in rr),runs_without_ec=sum(not r['records'] for r in rr)))
    defs=[dict(item='규칙',value='경로 끝 또는2s 중 먼저 제동을 요청하고 frozen stop_command(v=max(0,v-0.5/9),omega=0)를9Hz마다 반복하여v=0까지72Hz 적분/연속 swept footprint 검사. 주행 코드 수정 없음'),
        dict(item='시간 격자',value='주기 EC는9Hz 중간4tick 위상일 수 있음.2s 제동 요청은 정확히 기록하고 다음 실제9Hz 제어 tick에서 적용(0/4tick 추가),이 구간도 검사. 새 경로 Graph 검증은 원 INSTALL EC처럼t=0에서 첫 제어'),
        dict(item='원 EC 재현',value='설치 경로는 새 frozen NA profile,continuation은 저장된 generation/실제 제어 호출로 mode·target·progress 복원. 원 PASS·끝점·시간·최소여유1e-6 일치한 검사만 확정 PASS→REJECT로 집계'),
        dict(item='입력 보존',value='정확한 검사 snapshot을 STORAGE_RETROFIT로 복원. 없는 지도는 제외,오래된 지도 대체 없음. NoMaD world 좌표의 플랫폼별 fused multiply-add 차이는 저장 path SHA256과 비트일치하는 경우만 복원'),
        dict(item='한계',value='정적 저장 지도 위 오프라인 재판정. 새 NoMaD/지도갱신/주행 없음. v=0까지 제동을 유지하는 분석 규칙이므로 향후 온라인에서도 같은 종료 동작이 필요')]
    compact_flips=[{k:e[k] for k in ('phase','scene','method','seed','condition','check_id','time_s','scope','actual_v_m_s','remaining_length_m','logged_clearance_m','new_clearance_m','stop_reason')} for e in flips]
    doc='# EC 제동 꼬리: Phase47-C·Phase52-P 저장 검사 재판정\n\n'+table(coverage)+'\n\n'+table(bs)+'\n\n'+table(defs)+'\n\n## PASS → REJECT 검사\n\n'+table(compact_flips or [dict(n=0)])+'\n\n변경 검사: [braking_flips.csv](../research/results/phase52ec/braking_flips.csv). 전체 검사 `research/results/phase52ec/ec_checks.csv`는 로컬 archive로 보존한다. 불일치/제외: [목록](../research/results/phase52ec/replay_exclusions_or_mismatches.json).\n'
    (ROOT/'docs/PHASE52P_EC_BRAKING_TAIL.md').write_text(doc)
    gs=graph_summary(jobs,results,('phase','scene'))+graph_summary(jobs,results,('phase',))+graph_summary(jobs,results,())
    for r in gs:r.setdefault('phase','ALL');r.setdefault('scene','ALL')
    csvout(OUT/'graph_summary.csv',gs)
    slow_summary=[]
    for phase in ('phase47c','phase52p'):
        for scene in ('SLW','LC','L2','H1','H2'):
            gg=[j for j in slow if j['phase']==phase and j['scene']==scene];slow_summary.append(dict(phase=phase,scene=scene,slow_reject_records=sum(j['raw_record_count'] for j in gg),slow_unique_not_solved=len(gg)))
    statuses=Counter((r['phase'],r['scene'],str(c.get('solver_status')),c['solver_message']) for r in results for c in r['results'])
    status_rows=[dict(phase=p,scene=s,status=k,message=m,starts=n) for (p,s,k,m),n in sorted(statuses.items())];csvout(OUT/'solver_status.csv',status_rows)
    selections=[]
    for r in results:
        c=r['results'][r['selected']] if r['found'] else {}
        selections.append(dict(event_id=r['event_id'],uid=r['uid'],scene=r['scene'],time_s=r['time_s'],found=r['found'],selected=r['selected'],
            mean_displacement_m=c.get('mean_displacement_m'),max_displacement_m=c.get('max_displacement_m'),clearance_m=c.get('independent_clearance_m'),
            eight_start_s=r['eight_start_s'],original_any_tail_pass=r['original_any_tail_pass'],initial_state_pass=r['initial_state_pass'],travel_m=c.get('travel_m')))
    csvout(OUT/'graph_selections.csv',selections)
    rules=[dict(item=k,value=v) for k,v in protocol['rules'].items()]
    feasible=[{k:r[k] for k in ('phase','scene','raw_reject_checks','unique_full_speed_inputs','missing_map','completed','found','found_fraction','initial_state_infeasible')} for r in gs]
    edits=[{k:r[k] for k in ('phase','scene','displacement_mean_median_m','displacement_max_median_m','mean_edit_p95_m','displacement_max_overall_m','timed_solver_events','solve_verify_sum_p50_s','solve_verify_sum_p95_s')} for r in gs]
    mechanism=[{k:r[k] for k in ('phase','scene','original_any_tail_pass','all_original_reject','resampling_only_rescue','optimized_rescue','optimized_mean_edit_median_m','optimized_max_edit_median_m','selected_displacement_from_B_le_5cm')} for r in gs]
    doc='# 실행 궤적 제약 Graph: 저장 EC REJECT 입력의 오프라인 가능성\n\n'+table(feasible)+'\n\n## 채택 해 변위와 계산시간\n\n'+table(edits)+'\n\n## 기존 대안·재표집·최적화 구분\n\n'+table(mechanism)+'\n\n## 0.1m/s 입력: 집계만, 재풀이 없음\n\n'+table(slow_summary)+'\n\n## 정식화와 사전 고정 정의\n\n'+table(rules)+'\n\n'
    doc+='변수는 후보별 B+7개 XY점이다. SE(2) 상태 x_j=(x,y,theta)는 PP/SP 명령과 72Hz integrate_se2 등식으로 결정되어 최적화에서 소거된다. 독립 yaw·시간변수나 새로운 조향기는 사용하지 않는다. 목적은 sum_i ||p_i-q_ki||² 하나이고, 제약은 제동 꼬리 포함 실행 궤적의 최소 footprint depth clearance>=0.025m와 최종v=omega=0이다. 목표/진전/길이 항은 추가하지 않아 짧게 멈추거나 회전만 하는 해도 가능하며 별도로 표시한다.\n\n'
    doc+='목적 gradient는 해석적, 실행 제약 gradient는 2점 유한차분(eps=1e-6m)이다. 최적화 내부 산술 커널과 별개로 동결 Python 제어기·적분·exact swept 검사로 다시 PASS한 해만 해 찾음으로 센다. 원 후보가 이미 새 EC를 통과한 경우와 모든 원 후보가 거절됐는데 보정이 통과한 경우를 분리한다. Graph 계산시간은 `solve_verify_sum_p50/p95_s`: 입력1개에서 기록한8개 초기화 solve+독립 검증 시간을 합산한 값이며 solver가 실제 시작한 입력만 포함한다. `eight_start_p50/p95_s`는 원 후보8개의 비교용 EC 검사와 초기상태 검사까지 포함한 분석 호출 전체 wall time이다. 지도 디스크 로드·프로세스 시작은 두 값에서 제외한다. 초기 B 불가능으로 solver를 생략한 입력 수를 별도 표시하며, 그 초기검사 시간만은 따로 계측되지 않았다.\n\n## Solver 상태\n\n'+table(status_rows)+'\n\n사건별 결과: [graph_selections.csv](../research/results/phase52ec/graph_selections.csv). 후보별 status·경로·재검증 결과: `research/results/phase52ec/graph/`.\n'
    doc+='\n변위는 선택된 원 후보의 B 이후 suffix를 B+7점으로 재표집한 기준과의 점별 거리(고정 B 포함8점)다. 1μm 이하 변경은 수치적으로 초기값 그대로인 해로 따로 세었다. `resampling_only_rescue`는 원 후보8개가 모두 꼬리 EC에 실패했지만 재표집 초기값이 통과한 경우, `optimized_rescue`는 그 집합에서1μm 넘게 수정한 해가 통과한 경우다. 이 분해는 결과 해석용이며 solver·채택 규칙은 바꾸지 않았다.\n\n안전성은 저장된 **depth 지도상 2초 또는 끝점+제동 꼬리**에만 해당한다. unknown=free인 동결 EC 지도 규칙을 유지했으며 oracle 안전·전체 경로·목표 도착을 보장하지 않는다. 짧은 정지/회전만으로도 목적이 만족될 수 있어 실제 순변위5cm 이하 해를 함께 보고했다.\n'
    (ROOT/'docs/PHASE52P_EXEC_GRAPH.md').write_text(doc)
    summary=dict(recorded_ec_checks=len(records),confirmed_pass_to_reject=len(flips),replay_exclusions_or_mismatches=len(mismatch),
        raw_full_speed_reject_checks=sum(j['raw_record_count'] for j in jobs),unique_full_speed_inputs=len(jobs),
        unique_slow_inputs_not_solved=len(slow),graph_solved_inputs=len(results),graph_found=sum(r['found'] for r in results),
        graph_found_when_all_original_rejected=sum(r['found'] and r['all_original_reject'] for r in results))
    save(OUT/'summary.json',summary);print(json.dumps(summary))

if __name__=='__main__':main()
