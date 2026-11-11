# J0 장면 선별

| status | completed | planned | selected_J1_scenes | protocol_sha256 |
| --- | --- | --- | --- | --- |
| PREPARED_NOT_RUN | 0 | 20 | — | 42ebab18c221fdf5525ec83ba5692e8b84eb913b2df07d8f1dd88b743c5d7cee |

종료 판정은 Phase18과 동일(0.3m). 실제 목표 반경 진입이며 closest_node 기반 종료는 쓰지 않는다.

OURS-noEC: Phase18 최장 SAFE + GRAPH-depth-CLR + PP/CURV와 ENDPOINT latch. EC·회복·STOP_WAIT 특수처리·HMM/NET 없음. 0s 10회가 먼저, 0.75s 10회가 뒤다. seed221·222 공통.

체크포인트는 로봇 중심이 마지막 상자 먼 면+0.30m를 진행축으로 처음 넘는 저장72Hz 시점이다. H1-v2의 대상은 새 돌발 상자이며, H2는 실제 마지막 spawn 상자의 +x 투영 반폭을 사용한다. H2 마지막 상자 미생성 시 미측정이다.

| scene | axis | direction | box_id | dynamic | threshold_m | formula |
| --- | --- | --- | --- | --- | --- | --- |
| H1-v2 | 1 | 1 | DynamicObstacle | False | 1.6 | box center along axis + projected half extent + 0.30 |
| SLW | 0 | 1 | Slalom3 | False | 4.6 | box center along axis + projected half extent + 0.30 |
| H2 | 0 | 1 | DynamicObstacle2 | True | — | actual_last_spawn.center_x + projected_half_extent_x + 0.30 |
| LC | 1 | 1 | AfterCorner | False | 2.4 | box center along axis + projected half extent + 0.30 |
| CL | 0 | 1 | Clutter4 | False | 4.4971 | box center along axis + projected half extent + 0.30 |

| scene | delay_s | planned | completed | technical_failures | success | collision | wall_intrusion | timeout | checkpoint_n | checkpoint_mean_s | checkpoint_median_s | checkpoint_p95_s | arrival_median_s | arrival_p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1-v2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| H1-v2 | 0.75 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SLW | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| SLW | 0.75 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| H2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| H2 | 0.75 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| LC | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| LC | 0.75 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| CL | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| CL | 0.75 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |

| scene | zero_success | required_success | complete | all_checkpoints_observed | zero_checkpoint_mean_s | delayed_checkpoint_mean_s | difference_s | passed | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1-v2 | 0 | 2 | False | False | — | — | — | False | INCOMPLETE_OR_MISSING_CHECKPOINT |
| SLW | 0 | 2 | False | False | — | — | — | False | INCOMPLETE_OR_MISSING_CHECKPOINT |
| H2 | 0 | 2 | False | False | — | — | — | False | INCOMPLETE_OR_MISSING_CHECKPOINT |
| LC | 0 | 2 | False | False | — | — | — | False | INCOMPLETE_OR_MISSING_CHECKPOINT |
| CL | 0 | 2 | False | False | — | — | — | False | INCOMPLETE_OR_MISSING_CHECKPOINT |

선별: 0s 성공2/2 AND 0.75s 체크포인트 평균>0s 평균. 조건마다 두 checkpoint가 모두 관측된 장면만 비교하며 결측을 대체하지 않는다. 통과 장면을 0s 평균 오름차순으로 최대3개 선택한다. 동률은 동결 장면 순서. 기술 실패·미완료는 선별하지 않는다.

None.

동일seed 방법 간 임계좌표 최대차: J0는 방법1개라 비교 불가(관측값 존재 시 범위0). 지연 조건 간 차이는 별도 열이며 장면별 지연 비교 해석 시 함께 확인한다.

| scene | index | threshold_observations | methods | max_same_seed_between_methods_m | between_methods_scope | max_same_seed_between_delays_m |
| --- | --- | --- | --- | --- | --- | --- |
| H1-v2 | 221 | 0 | 0 | — | N/A: one method only | — |
| H1-v2 | 222 | 0 | 0 | — | N/A: one method only | — |
| SLW | 221 | 0 | 0 | — | N/A: one method only | — |
| SLW | 222 | 0 | 0 | — | N/A: one method only | — |
| H2 | 221 | 0 | 0 | — | N/A: one method only | — |
| H2 | 222 | 0 | 0 | — | N/A: one method only | — |
| LC | 221 | 0 | 0 | — | N/A: one method only | — |
| LC | 222 | 0 | 0 | — | N/A: one method only | — |
| CL | 221 | 0 | 0 | — | N/A: one method only | — |
| CL | 222 | 0 | 0 | — | N/A: one method only | — |

새 시뮬레이션을 하지 않은 PREP 단계에서는 결과·장면 선택을 주장하지 않는다. 누적 결과는 같은run-root에서 재개하며 과거 실험 결과를 덮어쓰지 않는다.
