"""Generate the offline preparation report; never launches navigation."""
import csv,json,hashlib
from collections import defaultdict
from pathlib import Path
from nomad_isaac.common import ROOT
from nomad_phase31p.report import table
from .evaluate import OUT,HERE,verify

def read(p):return json.loads(Path(p).read_text())
def csvread(p):
    with Path(p).open() as f:return list(csv.DictReader(f))

def main():
    protocol=verify();decision=read(OUT/'decision.json');topo=read(OUT/'topo_decision.json');audit=read(OUT/'preparation/input_audit.json')
    availability=csvread(OUT/'availability.csv');groups=defaultdict(lambda:dict(runs=0,all_control_ticks=0,map_available_ticks=0,map_missing_ticks=0,eligible_ticks=0,common_eligible_ticks=0,eligible_map_missing_ticks=0))
    for row in availability:
        key=(row['phase'],row['scene'],row['method']);g=groups[key];g['runs']+=1
        for name in list(g):
            if name!='runs':g[name]+=int(row.get(name) or 0)
    aa=[]
    for (phase,scene,method),g in sorted(groups.items()):
        aa.append(dict(phase=phase,scene=scene,method=method,**g,map_availability=g['map_available_ticks']/g['all_control_ticks'],eligible_availability=g['common_eligible_ticks']/g['eligible_ticks'] if g['eligible_ticks'] else None))
    labels=csvread(OUT/'trigger_summary.csv');new=csvread(OUT/'new_static_triggers.csv');static=[]
    for scene in ('SLW','LC'):
        rr=[r for r in new if r['scene']==scene]
        static.append(dict(scene=scene,new_TRIG_original_off=len(rr),**{k:sum(r['TRIG_label']==k for r in rr) for k in ('BOX_AHEAD','STATIC_AHEAD','PASSED_BOX','NOTHING_AHEAD')}))
    checks=[dict(condition=k,passed=v) for k,v in decision['checks'].items()]
    digest=hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest()
    text=f'''# Phase37 준비 — TRIG / TOPO-H 오프라인 확인

**{decision['label']}**. TOPO-H: **{topo['label']}**. 새 시뮬레이션·렌더·NoMaD 추론은 실행하지 않았다. Protocol `FROZEN_OFFLINE`, SHA256 `{digest}`.

Phase32 C0-NA+EC15 run과 Phase35 OURS15 run, 총30 run(정적6, 돌발24)을 사용했다. 기존 코드·raw·결과는 보존했다. 이전의 ‘개입하지 않았을 때5초 진전’ 정의는 사용자 지시에 따라 폐기하고, 아래 oracle 기하 분류만 게이트에 사용했다.

## 고정한 TRIG 정의

- 앞쪽1.0×0.40m 직사각형 안의 `observed & occupied` 셀이5개 이상. unknown과 observed free는 세지 않는다. 다섯 셀의 연결성은 추가 조건으로 요구하지 않는다.
- t_ref는 관측 점유 셀이 전방 직사각형에 처음 들어온 관측 시각이다. snapshot의 `first_occupied_tick`은 과거 점유 관측을 직접 증명하므로, 그 시각의 pose·기본3초 방향에서 해당 셀이 전방에 있었을 때만 그 시각으로 복원한다. 그렇지 않으면 공통 보존 관측 범위의 첫 전방 진입 시각을 사용한다. 누락된 지도 자체를 복원하거나 과거 지도를 최신으로 대체하지 않는다.
- 현재 관측 점유 셀의4-연결 덩어리는 참조 시각·거리 측정의 대상 연결에만 사용한다. 각 덩어리의 가장 이른 t_ref를 사용하고, 여러 대상은 기존처럼 이른 시각 우선(동률 격자순)이다. 전방5셀 문턱은 전체 직사각형에서 센다.
- 기본 u_ref는 t_ref 직전3초 변위 방향, 변위<0.3m이면 t_ref heading이다. 같은 t_ref에서 끝나는10초 변위가≥0.3m이고 두 방향 차가>90°이면10초 방향으로 교체한다. 현재 시점3초 방향을 계속 갱신하지 않는다. 불충분한10초 이력·정의 불가 변위는 기존 방향을 유지한다.
- 현재3초 진전<0.20m OR 장애물 거리 감소<0.10m이면 NO_PROGRESS. 거리 감소는 현재 관측된 해당 덩어리의 같은 점 집합을3초 전/현재 pose에 적용한다. 이미 완전히 지난 덩어리의 제외는 기존 `passed`를 재사용한다.
- 오프라인은 두 규칙에 **같은 기록된 busy/회전/정렬/R2 대기/3초 cooldown 상태**를 적용한9Hz 결정 기회 비교다. 새 트리거가 실제로 만들 우회·대기·이후 궤적은 생성하지 않는다. 연속 true 결정 기회를 임의의 새 episode 문턱으로 합치지 않았다. 트리거A·R2/R3·EC·유지/넘김을 바꾸지 않았다.

## 기하 분류와 gate 분모

oracle은 아래 분석에만 썼으며 TRIG/TOPO-H 입력에는 쓰지 않았다. 각 규칙의 u_ref 기준 전방 직사각형과 실제 상자/벽 polygon의 교차를 검사한다. 상자는 기록된 spawn 이후에만 존재하고, 기존 평가기의 passage 시각으로 이미 통과한 상자를 구분한다.

1. BOX_AHEAD: 아직 통과하지 않은 돌발 상자가 직사각형과 교차.
2. STATIC_AHEAD: BOX_AHEAD가 아니고 고정 장애물/실제 벽이 교차.
3. PASSED_BOX: 앞의 두 분류가 아니며 이미 통과했거나 뒤/옆에만 있는 상자들. 통과 후 다시 돌아보는 경우도 이전 passage를 취소하지 않고 이 분류다.
4. NOTHING_AHEAD: 그 외. 아직 먼 전방에만 있는 상자는 전방 직사각형의 장애물이 아니므로 이 분류다.

95% 보존율의 분모는 **공통 결정 기회에서 원래 규칙이 발동한 BOX_AHEAD**이며, 분자는 그 같은 tick에서 TRIG도 발동한 수다. ±시간 window나 미래 개입은 사용하지 않는다. 오발동은 각 규칙의 PASSED_BOX+NOTHING_AHEAD 발동 수다. 방향 오류는 Topomap 촬영 pose를 이은 기준 경로의 최근접 투영 segment tangent와 u_ref 차이>90°이다. STATIC_AHEAD는 **모든 gate 분모에서 제외**하고 따로 보고한다. BOX_AHEAD 표본이 없거나 방향 비율 분모가 없으면 통과를 주장하지 않는다.

## TRIG 결과

{table([dict(original_BOX_AHEAD=decision['original_BOX_AHEAD'],TRIG_recalled=decision['TRIG_fired_at_same_BOX_AHEAD_opportunity'],recall=decision['box_recall'],original_false=decision['false_trigger_counts']['original'],TRIG_false=decision['false_trigger_counts']['TRIG'])])}

{table([dict(rule=k,**v) for k,v in decision['direction'].items()])}

{table(checks)}

{table(labels)}

## 정적 장면의 새 발동 — 판정 미사용

{table(static)}

`new_static_triggers.csv`에는 원래 off/TRIG on인 각 시점의 pose 참조, 방향, t_ref, 진행량, 거리 감소, 기하 분류와 snapshot을 기록했다.

## 지도 가용률과 미측정

{table(aa)}

전체 run별 표는 `availability.csv`. 조건 로그에 저장된 실제 check snapshot을 우선 사용하고, 그 외 시점은 같은 제어 tick에 기록된 snapshot을 사용했다. 발행 시점의 모든 지도는 보존되지 않았으므로 **결과는 동일한 보존 지도와 기록된 상태 범위에 한정된다**. 최초 전방 관측도 이 보존 범위와 명시적 first-occupied 이력에 의존한다. 최종 효과 확인은 새 seed 주행 실험에서 해야 한다.

원래 로그의 eligible 조건 중 지도 확인 가능 {audit['totals']['exact_condition_checks']}건은 {audit['totals']['reproduced_condition_checks']}건 모두 원 조건·component·u_ref·진전량과 일치했다. 원 B 트리거162건 중161건의 check map이 남아 있다. 미보존 시점은 새 지도나 오래된 지도 proxy로 대체하지 않았다.

## TOPO-H 정의와 오프라인 결과

`candidate_range(H, goal_node, radius=4)`의 원 구현(오른쪽 radius+1과 inclusive slice 포함), close_threshold3을 그대로 쓴다. r≥H이면 H=r,c=0; r<H이면 c+=1, c≥3에서만 H=r,c=0. subgoal=min(H+int(dist[H]<3),goal_node), H≥goal_node−1이면 goal_node다. oracle·pose는 이 선택 함수 입력이 아니다.

질의의 원 RGB 관측 pose를 기준 경로에 투영하고, 선택 subgoal의 호길이가 로봇보다0.2m 초과 뒤인지, 선택 subgoal index가 실제 최근접 촬영 node보다2 초과 앞서는지 측정했다. 원래 raw closest/subgoal은 모든 저장 거리값으로 먼저 회귀 확인했다.

H가 원 closest와 달라지면 요구 window 일부의 거리값이 기록에 없을 수 있다. 누락 점수를 추정하거나 새 추론을 하지 않았다. 가능한 H/c/subgoal 상태 집합을 보수적으로 전파해 비율의 하한·상한을 보고한다. 상한으로도 조건을 만족해야 TOPO_OK, 하한에서도 실패하면 TOPO_FAIL, 나머지는 미측정 점수로 미확정이다. 이는 분석의 불확실성 처리이며 온라인 규칙에 추가하는 조건이 아니다.

{table(topo['groups'])}

{table([dict(condition=k,passes_using_upper_bound=v) for k,v in topo['checks_using_upper_bounds'].items()])}

## 검증 및 다음 단계

21개 단위테스트: observed/occupied5셀·unknown 제외·직사각형 변환, t_ref 고정과 전방 돌발 출현 시 기존 t_new 일치, t_ref 기준 방향 guard(짧은3초 변위의 heading 대체 포함), TOPO-H3회 후퇴·거리/goal 분기·원 window 유지·누락 점수 상태 범위, 기하 분류와 gate 경계를 확인했다. frozen 코드는 수정하지 않았다.

게이트 계산 전 구현 검토에서,3초 변위<0.3m인 경우 raw 변위 방향이 아니라 최종 기본 u_ref(heading 대체값)를10초 방향과 비교해야 하는 오류를 수정했다. 첫 부분 평가 출력과 당시 protocol은 `technical_archive/guard_comparison_attempt1/`에 보존했으며 판정에 사용하지 않았다. 숫자·gate·데이터셋은 변경하지 않았고 결과를 이용한 튜닝도 하지 않았다.

TRIG={decision['label']}, TOPO-H={topo['label']}. TRIG 통과 시에만 선택 방법 `{decision['planned_new_method']}`의20회 준비로 진행한다. 이 보고서 생성 자체는 campaign·Isaac·NoMaD를 실행하지 않는다.
'''
    if decision['label']!='OFFLINE_OK':text+='\n**주행 준비 없이 중단한다.** 실행용 protocol·20개 조합 dry-run·nohup 명령·새 run-root는 만들지 않았다.\n'
    else:text+='\n오프라인 gate를 통과했으며 온라인 준비 단계의 검증·동결은 별도 기록이 필요하다. 아직 실행 명령을 제시하지 않는다.\n'
    (ROOT/'docs/PHASE37_PREP.md').write_text(text)

if __name__=='__main__':main()
