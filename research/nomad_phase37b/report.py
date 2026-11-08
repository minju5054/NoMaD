"""Read-only provenance comparison report. Never starts a campaign."""
import csv,json
from pathlib import Path
from collections import Counter
from nomad_isaac.common import ROOT
from nomad_phase31p.report import table
from .evaluate import OUT,HERE,verify

def read(p):return json.loads(Path(p).read_text())
def csvread(p):
    with Path(p).open() as f:return list(csv.DictReader(f))

def main():
    protocol=verify();d=read(OUT/'decision.json');summaries=csvread(OUT/'summary.csv');history=read(OUT/'evidence_summary.json');verification=read(OUT/'verification.json');misses=csvread(OUT/'missed_BOX_AHEAD.csv')
    static=[r for r in summaries if r['scene'] in ('SLW','LC')];old_total=rows_total=0
    totals={k:sum(r[k] for r in history) for k in ('candidate_cell_union','confirmed_published_free_cells','unmeasured_history_cells','no_published_free_with_complete_history_cells','first_free_frame_observed_false','first_free_frame_unavailable')}
    per_scene=[]
    for scene in ('SLW','LC','L2','H1','H2'):
        group=[r for r in history if r['scene']==scene]
        per_scene.append(dict(scene=scene,runs=len(group),**{k:sum(r[k] for r in group) for k in ('candidate_cell_union','confirmed_published_free_cells','unmeasured_history_cells','no_published_free_with_complete_history_cells')}))
    import hashlib
    digest=hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest()
    text=f'''# Phase37-B — 原 B / PROV 관측 이력 비교

**{d['label']}**. Phase37과 동일한30 run·4,915개 공통 결정 시점을 사용했다. 새 시뮬레이션·NoMaD 추론·주행 준비는 하지 않았다. 기존 코드·결과·raw는 변경하지 않았다. Protocol SHA256 `{digest}`.

## 원래 규칙과의 실제 차이

원래 코드도 `first_free_tick ≥ 0` 및 `first_free_tick < first_occupied_tick`을 요구한다. 이 timestamp는 `RecentMap`의 실제 ray-clearing mask(`_free & ~_hits`)에서만 나온다. 따라서 PROV를 **ray clearing 이력 자체만 다시 요구하는 뜻**으로 해석하면 원래 규칙과 동일하여 발동·게이트도 변하지 않는다.

요청의 `observed=True이며 free`는 **해당 frame의 최종 발행 상태**로 해석했다. 같은 frame의 shadow 처리가 음수 log-odds 칸을 unknown으로 돌려 `observed=False`로 만들 수 있는데, 기존 `last_free_tick`/`first_free_tick`은 그 경우에도 남는다. PROV에는 최초 occupied보다 앞선 시점에 아래 증거가 한 번 이상 확인된 칸만 남긴다.

`last_free_tick == frame_tick AND observed == True AND occupied == False AND frame_tick < first_occupied_tick`

최초 ray-free가 shadow에 의해 무효여도, 그 뒤 최초 occupied 전에 유효한 free 관측이 한 번이라도 있으면 인정한다. 음수 log-odds 등 별도 문턱을 추가하지 않았다. Snapshot에는 log-odds가 없으며, 저장 이력 밖의 관측을 추정하지 않았다.

필터링한 셀 mask만 원래 `component_sets`에 추가한다. 덩어리≥5, 원래4-연결성·identity·t_new·u_ref·1.0×0.4m 사각형·진전 없음·passed 판정·선택 순서는 그대로다.10초 방향 보정과 Phase37 TRIG는 사용하지 않는다. R2/R3·EC·유지/넘김·실행기는 수정하거나 실행하지 않았다.

## 이력 가용성

{table([totals])}

{table(per_scene)}

셀 수는 각 run 안의 고유 기존 후보 셀을 센 후 합산한 값이다. 원래 후보 셀 전부에 ray-clearing timestamp가 있음을 확인했다. 과거 발행 지도에서 free가 확인되면 CONFIRMED, 최초 free~occupied 사이의 모든 발행 이력이 남아 있고 확인 관측이 없으면 NO_VALID_PUBLISHED_FREE, 일부 이력이 없으면 UNMEASURED다. 과거 지도를 누락 시점에 대신 넣지 않는다.

이력 누락을 모두 ‘유효 free가 없었음’으로 간주하면 효과를 과장할 수 있다. 따라서 표에는 **보존 이력으로 증명된 셀만 사용한 재평가**와, 미측정 이력이 허용할 수 있는 결과 범위를 함께 제시한다. 셀 추가가 덩어리 선택·u_ref·거리 감소를 바꿀 수 있어 단순히 두 mask 실행을 상한/하한으로 부르지 않고, 가능한 선택 덩어리와 거리 감소 범위를 보수적으로 계산했다. 분류별 범위는 서로 다른 가능성에서 나올 수 있으며 gate는 비-BOX 합산 범위를 직접 쓴다.

## 네 분류별·장면별 발동

분류와 9Hz 공통 평가 기회는 Phase37 그대로다. oracle은 BOX_AHEAD / STATIC_AHEAD / PASSED_BOX / NOTHING_AHEAD 분석에만 사용했다. 기록된 우회·회복·정렬·R2 대기·cooldown 상태는 두 규칙에 동일하게 적용했다. 새 규칙이 만든 이후 주행을 재현한 결과는 아니다.

{table(summaries)}

원 규칙의 공통 시점 발동·분류·방향은 Phase37 결과와 {verification['original_regression_exact']}/{verification['common_opportunities']} 시점에서 일치했다. 자료 범위는 동일한 보존 지도와 확인 가능한 과거 이력에 한정된다.

## 정적 장면 SLW·LC

{table(static)}

이 단계에서는 STATIC_AHEAD도 다른 비-BOX 분류와 함께50% 감소 조건에 포함한다. Phase37의 STATIC 제외 gate를 가져오지 않았다.

## 놓친 BOX_AHEAD 사건

원래 BOX_AHEAD인 시점에서 증명된 이력만 사용한 PROV가 off인 사건을 전부 열거한다. DEFINITE_MISS는 누락 이력을 가장 유리하게 보더라도 미발동이며, UNMEASURED_HISTORY_SENSITIVE는 실제 PROV가 놓쳤다고 확정할 수 없다.

{table(misses)}

각 사건의 셀별 표는 `research/results/phase37b/missed_box_cell_history.csv`다. 실제 상자 footprint와 교차하는 현재 observed occupied 격자 칸(격자 사각형 면적 기준)과 원래 선택 덩어리의 칸을 함께 기록했다. `box_ids`와 `selected_component_cell`로 구분하며, 원래 발동 대상이 옆의 정적 물체였는지도 드러난다. 최초 ray-free·최초 확인된 observed-free·최초 occupied의 tick과 초, 첫 free frame의 observed 상태, 누락 이력 수를 제공한다. 확인할 수 없는 시각은 빈 값으로 남긴다.

## 사전 gate

{table([dict(original_BOX_AHEAD=d['BOX_AHEAD_original'],retained_confirmed_history=d['BOX_retained_confirmed_history'],retained_lower=d['BOX_retained_lower'],retained_upper=d['BOX_retained_upper'],recall_confirmed_history=d['recall_confirmed_history'],recall_lower=d['recall_lower'],recall_upper=d['recall_upper'])])}

{table([dict(original_nonbox=d['nonbox_original'],PROV_confirmed_history=d['nonbox_confirmed_history'],PROV_lower=d['nonbox_lower'],PROV_upper=d['nonbox_upper'],required_max=d['nonbox_original']*.5)])}

{table([dict(condition=k,passed=v) for k,v in d['checks'].items()])}

PROV_OK는 BOX_AHEAD 보존율 하한≥95% 및 (STATIC_AHEAD+PASSED_BOX+NOTHING_AHEAD) 발동 상한≤원래의50%를 모두 만족할 때만 부여한다. 가장 유리한 해석에서도 조건을 못 채우면 PROV_FAIL, 누락 이력 때문에 결론이 달라질 수 있으면 PROV_NOT_ESTABLISHED_MISSING_HISTORY다. 수치 기준은 변경하지 않았다.

**{d['label']}**. 결과와 무관하게 주행 준비·실행 명령은 만들지 않는다. 원래 관측 이력만 다시 요구하는 해석은 추가적인 규칙이 아니며, 최종 published observed 상태까지 요구한 해석의 효과를 위와 같이 구분했다.

실행: `PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_phase37b.report`
'''
    (ROOT/'docs/PHASE37B_PROV.md').write_text(text)

if __name__=='__main__':main()
