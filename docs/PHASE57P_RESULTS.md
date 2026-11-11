# Phase57-P

| status | planned | completed | protocol_sha256 |
|---|---|---|---|
| PREPARED_NOT_RUN | 18 | 0 | 8a7c1e827306abda407d386a9c934bccee400a261700b3d6963f9f284886dca0 |

NOMAD_RAW는 Phase47-C 원래 argmin 위치추정/sample0/실행기를 유지한다. MIN 두 방법만 HMM·EC-tail·ENDPOINT latch를 사용하고 depth 사전 필터·회복·정렬·저속 후보 단계는 끈다. 1s 만료와 공식 도착 판정은 유지한다. 성과로 파라미터를 바꾸지 않는다.

| method | scene | n | valid | success | collision | wrong_stop | timeout_without_declaration | box_passage | goal_time_s | stopped_s | graph_attempts | graph_applied | graph_adoption_rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOMAD_RAW | H1-v2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| NOMAD_RAW | SLW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| NOMAD_RAW | H2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| NOMAD_RAW | ALL | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| MIN | H1-v2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| MIN | SLW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| MIN | H2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| MIN | ALL | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| MIN+G18 | H1-v2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| MIN+G18 | SLW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| MIN+G18 | H2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |
| MIN+G18 | ALL | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | — | 0 | 0 | — |

| scene | index | method | status | classification | success | collision | wrong_stop | timeout_without_declaration | box_passage | box_passage_from_spawn_s | goal_time_s | stopped_s | graph_adoption_rate | graph_solve_p50_s | graph_solve_p95_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-v2 | 227 | MIN | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 227 | MIN+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 227 | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 228 | MIN | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 228 | MIN+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2 | 228 | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 227 | MIN+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 227 | MIN | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 227 | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 228 | MIN+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 228 | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| SLW | 228 | MIN | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 227 | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 227 | MIN+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 227 | MIN | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 228 | MIN | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 228 | MIN+G18 | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
| H2 | 228 | NOMAD_RAW | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — |
