# H1-v3 — J0 선별

| status | planned | completed | eligible | protocol_sha256 |
| --- | --- | --- | --- | --- |
| COMPLETE | 4 | 4 | False | 60280e37fae59be42f8930dc00914be2fcd666110574e992736392405bb16846 |

방법·판정은 J0와 동일한 OURS-noEC, Phase18 PP/CURV·1s 만료·공식 NoMaD subgoal·ENDPOINT latch다. 종료 판정은 Phase18과 동일(0.3m). EC·HMM/NET·회복·STOP_WAIT 특수처리 없음.

| axis | direction | box_id | dynamic | threshold_m | formula |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | DynamicObstacle | False | 1.2 | box center along +y + projected half extent + 0.30 |

| scene | delay_s | planned | completed | technical_failures | success | collision | wall_intrusion | timeout | checkpoint_n | checkpoint_mean_s | checkpoint_median_s | checkpoint_p95_s | arrival_median_s | arrival_p95_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1-v3 | 0 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |
| H1-v3 | 0.75 | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | — | — | — | — | — |

| scene | zero_success | required_success | complete | all_checkpoints_observed | zero_checkpoint_mean_s | delayed_checkpoint_mean_s | difference_s | passed | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H1-v3 | 0 | 2 | False | False | — | — | — | False | INCOMPLETE_OR_MISSING_CHECKPOINT |

| index | delay | classification | technical_validation | success | collision | wall_intrusion | timeout | checkpoint_threshold_m | checkpoint_start_distance_m | checkpoint_time_s | goal_time_s | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 221 | 0 | TECHNICAL_FAILURE | FAIL | — | — | — | — | — | — | — | — | RuntimeError('Launcher exit 1') |
| 222 | 0 | TECHNICAL_FAILURE | FAIL | — | — | — | — | — | — | — | — | RuntimeError('Launcher exit 1') |
| 221 | 0.75 | TECHNICAL_FAILURE | FAIL | — | — | — | — | — | — | — | — | RuntimeError('Launcher exit 1') |
| 222 | 0.75 | TECHNICAL_FAILURE | FAIL | — | — | — | — | — | — | — | — | RuntimeError('Launcher exit 1') |

선별 기준: 0s 성공2/2 AND 0.75s checkpoint 평균>0s 평균. 두 조건 모두 seed221·222의 checkpoint가 있어야 하며 결측 대체 없음. 0s 두 run을 먼저 실행한다. 기존 H1-v2 코드·결과는 수정하지 않는다.

![H1-v3 geometry](figures/h1v3_scene_preview.png)
