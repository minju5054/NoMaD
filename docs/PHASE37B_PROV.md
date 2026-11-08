# Phase37-B — 원래 B / PROV 관측 이력 비교

**PROV_NOT_ESTABLISHED_MISSING_HISTORY**. Phase37과 동일한30 run·4,915개 공통 결정 시점을 사용했다. 새 시뮬레이션·NoMaD 추론·주행 준비는 하지 않았다. 기존 코드·결과·raw는 변경하지 않았다. Protocol SHA256 `664fa32a4981ff84ea06e4387b739bf336e6e7edef8c2f3ef3f7259a792eefff`.

## 원래 규칙과의 실제 차이

원래 코드도 `first_free_tick ≥ 0` 및 `first_free_tick < first_occupied_tick`을 요구한다. 이 timestamp는 `RecentMap`의 실제 ray-clearing mask(`_free & ~_hits`)에서만 나온다. 따라서 PROV를 **ray clearing 이력 자체만 다시 요구하는 뜻**으로 해석하면 원래 규칙과 동일하여 발동·게이트도 변하지 않는다.

요청의 `observed=True이며 free`는 **해당 frame의 최종 발행 상태**로 해석했다. 같은 frame의 shadow 처리가 음수 log-odds 칸을 unknown으로 돌려 `observed=False`로 만들 수 있는데, 기존 `last_free_tick`/`first_free_tick`은 그 경우에도 남는다. PROV에는 최초 occupied보다 앞선 시점에 아래 증거가 한 번 이상 확인된 칸만 남긴다.

`last_free_tick == frame_tick AND observed == True AND occupied == False AND frame_tick < first_occupied_tick`

최초 ray-free가 shadow에 의해 무효여도, 그 뒤 최초 occupied 전에 유효한 free 관측이 한 번이라도 있으면 인정한다. 음수 log-odds 등 별도 문턱을 추가하지 않았다. Snapshot에는 log-odds가 없으며, 저장 이력 밖의 관측을 추정하지 않았다.

필터링한 셀 mask만 원래 `component_sets`에 추가한다. 덩어리≥5, 원래4-연결성·identity·t_new·u_ref·1.0×0.4m 사각형·진전 없음·passed 판정·선택 순서는 그대로다.10초 방향 보정과 Phase37 TRIG는 사용하지 않는다. R2/R3·EC·유지/넘김·실행기는 수정하거나 실행하지 않았다.

## 이력 가용성

| candidate_cell_union | confirmed_published_free_cells | unmeasured_history_cells | no_published_free_with_complete_history_cells | first_free_frame_observed_false | first_free_frame_unavailable |
|---|---|---|---|---|---|
| 344859 | 213170 | 102126 | 29563 | 130369 | 98223 |

| scene | runs | candidate_cell_union | confirmed_published_free_cells | unmeasured_history_cells | no_published_free_with_complete_history_cells |
|---|---|---|---|---|---|
| SLW | 3 | 7627 | 3292 | 4151 | 184 |
| LC | 3 | 31136 | 17840 | 10860 | 2436 |
| L2 | 8 | 107935 | 67870 | 29040 | 11025 |
| H1 | 8 | 77267 | 47122 | 23350 | 6795 |
| H2 | 8 | 120894 | 77046 | 34725 | 9123 |

셀 수는 각 run 안의 고유 기존 후보 셀을 센 후 합산한 값이다. 원래 후보 셀 전부에 ray-clearing timestamp가 있음을 확인했다. 과거 발행 지도에서 free가 확인되면 CONFIRMED, 최초 free~occupied 사이의 모든 발행 이력이 남아 있고 확인 관측이 없으면 NO_VALID_PUBLISHED_FREE, 일부 이력이 없으면 UNMEASURED다. 과거 지도를 누락 시점에 대신 넣지 않는다.

이력 누락을 모두 ‘유효 free가 없었음’으로 간주하면 효과를 과장할 수 있다. 따라서 표에는 **보존 이력으로 증명된 셀만 사용한 재평가**와, 미측정 이력이 허용할 수 있는 결과 범위를 함께 제시한다. 셀 추가가 덩어리 선택·u_ref·거리 감소를 바꿀 수 있어 단순히 두 mask 실행을 상한/하한으로 부르지 않고, 가능한 선택 덩어리와 거리 감소 범위를 보수적으로 계산했다. 분류별 범위는 서로 다른 가능성에서 나올 수 있으며 gate는 비-BOX 합산 범위를 직접 쓴다.

## 네 분류별·장면별 발동

분류와 9Hz 공통 평가 기회는 Phase37 그대로다. oracle은 BOX_AHEAD / STATIC_AHEAD / PASSED_BOX / NOTHING_AHEAD 분석에만 사용했다. 기록된 우회·회복·정렬·R2 대기·cooldown 상태는 두 규칙에 동일하게 적용했다. 새 규칙이 만든 이후 주행을 재현한 결과는 아니다.

| scene | label | original | PROV_confirmed_history | PROV_lower | PROV_upper |
|---|---|---|---|---|---|
| SLW | BOX_AHEAD | 0 | 0 | 0 | 0 |
| SLW | STATIC_AHEAD | 38 | 10 | 10 | 53 |
| SLW | PASSED_BOX | 0 | 0 | 0 | 0 |
| SLW | NOTHING_AHEAD | 0 | 0 | 0 | 0 |
| LC | BOX_AHEAD | 0 | 0 | 0 | 0 |
| LC | STATIC_AHEAD | 0 | 0 | 0 | 2 |
| LC | PASSED_BOX | 0 | 0 | 0 | 0 |
| LC | NOTHING_AHEAD | 3 | 1 | 1 | 3 |
| L2 | BOX_AHEAD | 11 | 11 | 11 | 11 |
| L2 | STATIC_AHEAD | 25 | 17 | 16 | 25 |
| L2 | PASSED_BOX | 3 | 2 | 2 | 2 |
| L2 | NOTHING_AHEAD | 0 | 0 | 0 | 0 |
| H1 | BOX_AHEAD | 4 | 1 | 1 | 3 |
| H1 | STATIC_AHEAD | 5 | 4 | 4 | 5 |
| H1 | PASSED_BOX | 7 | 2 | 2 | 5 |
| H1 | NOTHING_AHEAD | 0 | 0 | 0 | 0 |
| H2 | BOX_AHEAD | 30 | 30 | 30 | 30 |
| H2 | STATIC_AHEAD | 32 | 21 | 21 | 30 |
| H2 | PASSED_BOX | 3 | 2 | 2 | 3 |
| H2 | NOTHING_AHEAD | 0 | 0 | 0 | 0 |
| ALL | BOX_AHEAD | 45 | 42 | 42 | 44 |
| ALL | STATIC_AHEAD | 100 | 52 | 51 | 115 |
| ALL | PASSED_BOX | 13 | 6 | 6 | 10 |
| ALL | NOTHING_AHEAD | 3 | 1 | 1 | 3 |

원 규칙의 공통 시점 발동·분류·방향은 Phase37 결과와 4915/4915 시점에서 일치했다. 자료 범위는 동일한 보존 지도와 확인 가능한 과거 이력에 한정된다.

## 정적 장면 SLW·LC

| scene | label | original | PROV_confirmed_history | PROV_lower | PROV_upper |
|---|---|---|---|---|---|
| SLW | BOX_AHEAD | 0 | 0 | 0 | 0 |
| SLW | STATIC_AHEAD | 38 | 10 | 10 | 53 |
| SLW | PASSED_BOX | 0 | 0 | 0 | 0 |
| SLW | NOTHING_AHEAD | 0 | 0 | 0 | 0 |
| LC | BOX_AHEAD | 0 | 0 | 0 | 0 |
| LC | STATIC_AHEAD | 0 | 0 | 0 | 2 |
| LC | PASSED_BOX | 0 | 0 | 0 | 0 |
| LC | NOTHING_AHEAD | 3 | 1 | 1 | 3 |

이 단계에서는 STATIC_AHEAD도 다른 비-BOX 분류와 함께50% 감소 조건에 포함한다. Phase37의 STATIC 제외 gate를 가져오지 않았다.

## 놓친 BOX_AHEAD 사건

원래 BOX_AHEAD인 시점에서 증명된 이력만 사용한 PROV가 off인 사건을 전부 열거한다. DEFINITE_MISS는 누락 이력을 가장 유리하게 보더라도 미발동이며, UNMEASURED_HISTORY_SENSITIVE는 실제 PROV가 놓쳤다고 확정할 수 없다.

| event_key | phase | scene | index | time_s | status | original_component | PROV_component | box_occupied_cells | selected_component_cells | box_first_ray_free_s_range | box_first_confirmed_free_s_range | box_first_occupied_s_range | selected_history_status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 32_H1_201:1736 | 32 | H1 | 201 | 24.11111111111111 | DEFINITE_MISS | 320 | 369 | 244 | 8 | [10.48611111111111, 21.73611111111111] | [10.48611111111111, 12.48611111111111] | [20.23611111111111, 22.23611111111111] | {"NO_VALID_PUBLISHED_FREE": 4, "CONFIRMED": 4} |
| 32_H1_205:1824 | 32 | H1 | 205 | 25.333333333333332 | UNMEASURED_HISTORY_SENSITIVE | 308 | 383 | 255 | 11 | [10.48611111111111, 21.98611111111111] | [10.73611111111111, 12.73611111111111] | [20.23611111111111, 23.48611111111111] | {"CONFIRMED": 6, "MISSING_HISTORY": 5} |
| 35_H1_213:1848 | 35 | H1 | 213 | 25.666666666666668 | UNMEASURED_HISTORY_SENSITIVE | 365 |  | 215 | 5 | [11.98611111111111, 14.23611111111111] | [12.23611111111111, 14.23611111111111] | [21.98611111111111, 23.23611111111111] | {"MISSING_HISTORY": 4, "CONFIRMED": 1} |

각 사건의 셀별 표는 `research/results/phase37b/missed_box_cell_history.csv`다. 실제 상자 footprint와 교차하는 현재 observed occupied 격자 칸(격자 사각형 면적 기준)과 원래 선택 덩어리의 칸을 함께 기록했다. `box_ids`와 `selected_component_cell`로 구분하며, 원래 발동 대상이 옆의 정적 물체였는지도 드러난다. 최초 ray-free·최초 확인된 observed-free·최초 occupied의 tick과 초, 첫 free frame의 observed 상태, 누락 이력 수를 제공한다. 확인할 수 없는 시각은 빈 값으로 남긴다.

## 사전 gate

| original_BOX_AHEAD | retained_confirmed_history | retained_lower | retained_upper | recall_confirmed_history | recall_lower | recall_upper |
|---|---|---|---|---|---|---|
| 45 | 42 | 42 | 44 | 0.93333 | 0.93333 | 0.97778 |

| original_nonbox | PROV_confirmed_history | PROV_lower | PROV_upper | required_max |
|---|---|---|---|---|
| 116 | 59 | 58 | 126 | 58 |

| condition | passed |
|---|---|
| box_retention_guaranteed | False |
| nonbox_reduction_guaranteed | False |

PROV_OK는 BOX_AHEAD 보존율 하한≥95% 및 (STATIC_AHEAD+PASSED_BOX+NOTHING_AHEAD) 발동 상한≤원래의50%를 모두 만족할 때만 부여한다. 가장 유리한 해석에서도 조건을 못 채우면 PROV_FAIL, 누락 이력 때문에 결론이 달라질 수 있으면 PROV_NOT_ESTABLISHED_MISSING_HISTORY다. 수치 기준은 변경하지 않았다.

**PROV_NOT_ESTABLISHED_MISSING_HISTORY**. 결과와 무관하게 주행 준비·실행 명령은 만들지 않는다. 원래 관측 이력만 다시 요구하는 해석은 추가적인 규칙이 아니며, 최종 published observed 상태까지 요구한 해석의 효과를 위와 같이 구분했다.

실행: `PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_phase37b.report`

## 최종 검산과 해석

- 확인된 발행 이력만 사용한 수치는 BOX_AHEAD42/45(93.33%), 비-BOX116→59(49.14% 감소)로 두 수치 문턱에 모두 못 미친다. 다만 전체 실제 이력의 범위는42~44/45와58~126건이므로, 보존되지 않은 이력을 임의로 채우지 않고 전체 PROV의 gate를 **미확정**으로 남긴다.
- `first_free_tick`의 ray-clearing 사실 자체만을 PROV로 해석하면 기존 코드가 이미 만족한다. 그 경우 정확히 BOX_AHEAD45/45, 비-BOX116→116이며 감소 조건을 충족하지 못한다.
- 세 누락 사건 모두 기존 선택 덩어리의 셀은 실제 돌발 상자 footprint 밖이었다(선택 셀과 상자 footprint 교차0). 전방 직사각형에 상자가 있어서 BOX_AHEAD로 분류된 사건이며, 이를 실제 상자 관통이나 주행 실패로 해석하면 안 된다. 분류·gate는 바꾸지 않았다.
- 셀 이력 CSV의 `first_ray_free_observed`는1=관측 상태 확인,0=최종 observed=False,-1=해당 과거 frame 미보존이다. 칸별 timestamp는 실제 저장 이력이며, 범위 요약의 최솟값·최댓값은 서로 다른 칸에서 나올 수 있다.
- 단위테스트11개와 원 규칙4,915개 시점의 회귀가 통과했다. 입력 파일 SHA256과 gate 수치를 독립 검산했으며 기존 코드·raw·이전 결과는 변경하지 않았다.
