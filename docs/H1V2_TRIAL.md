# H1-v2 시험 주행

| status | completed | planned | smoke | protocol_sha256 |
|---|---|---|---|---|
| PREPARED_NOT_RUN | 0 | 4 | False | ad22df578a956218eb94b024e8121a836ae336b8e416932ee786617cde9b0b31 |

Phase53-P CUT·GRAPH-HO, EC 제동꼬리, 1초 만료 및 HMM·공식 도착 판정은 동결 그대로다. 장면만 H1-v2(y=1.10, 65556be)로 연결했다. Smoke는 없고 지정한4회가 본 실행이다.

| scene | seed | method | technical | classification | success | collision | wrong_stop | timeout_without_declaration | box_passage | passage_side | box_passage_from_spawn_s | spawn_time_s | goal_time_s | stopped_s | align_rotate_s | minimum_clearance_m | ec_rejects | graph_adoption_rate | graph_rejection_reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H1-v2_D150 | 221 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D150 | 221 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D075 | 221 | CUT | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| H1-v2_D075 | 221 | GRAPH-HO | NOT_RUN | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

분류·통과·최소 여유·EC·Graph 수치는 기존 평가/log에서 가져온다. 통과 쪽은 +y 진행 기준 +X(오른쪽)/−X(왼쪽), 출현→통과 시간은 실제 spawn 시각부터의 시간이다. Graph 채택률은 실제 Graph 설치/시도이며 실패 사유는 원 solver·certificate·EC 거절 로그명 그대로다.

아직 주행하지 않았다. 종료 후 run별 PNG4장과2×2 종합 PNG를 자동 생성한다.
