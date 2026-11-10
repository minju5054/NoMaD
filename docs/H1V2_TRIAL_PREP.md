# H1-v2 시험 주행 준비

| status | main_runs | smoke | scene | seed | order_seed | protocol_sha256 |
|---|---|---|---|---|---|---|
| FROZEN_PREPARED_NOT_RUN | 4 | False | H1-v2 @65556be | 221 | 20261116 | ad22df578a956218eb94b024e8121a836ae336b8e416932ee786617cde9b0b31 |

Phase53-P 동결 CUT·GRAPH-HO를 그대로 import한다. EC 제동꼬리·1초 waypoint 만료·FRESHEST·HMM·공식 도착 판정·PP/SP·90° 정렬·Graph factor/가중치/옵션을 변경하지 않았다. 변경은 H1 config에 configure를 적용하고 Phase53 초기화 뒤 install_environment를 호출하는 장면 연결뿐이다.

상자 중심(2.876453,1.100000)m, 크기0.5×0.4×0.8m, 고정 위치이며 기존 jitter를 쓰지 않는다. Spawn은 실제 pose를 동일 Topomap polyline에 투영한 호장이2.253355m 이상이 되는 첫72Hz tick. H1-v2 기하·spawn·Topomap은65556be의 hash로 확인했다.

| order | scene | index | method |
|---|---|---|---|
| 1 | H1-v2_D150 | 221 | CUT |
| 2 | H1-v2_D150 | 221 | GRAPH-HO |
| 3 | H1-v2_D075 | 221 | CUT |
| 4 | H1-v2_D075 | 221 | GRAPH-HO |

별도 smoke 없이 위4회가 본 실행이다. 순차 실행·기술 실패1회 재시도·완료 run 재개 시 건너뛰기·글로벌 잠금·저장v2·종료 후 portable/cache 및 pycache 정리·매 run 전 여유30GB 검사 규칙을 재사용한다.

| passed | tests | dry_run | simulations_started | smoke | offline_resolves | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|---|
| True | 6 | 4 | 0 | 0 | 0 | ad22df578a956218eb94b024e8121a836ae336b8e416932ee786617cde9b0b31 | 1130261639168 |

완료 후 /usr/bin/python3 + PYTHONPATH=research로 report를 자동 실행한다. docs/H1V2_TRIAL.md와 research/results/h1v2_trial/에 run별 분류, 상자 통과/쪽/출현→통과, 도착/정지/ALIGN_ROTATE 시간, 최소 여유, EC 거절, Graph 채택률/거절 사유를 저장한다. 주행 PNG4장과2×2 종합 그림은 docs/figures/에 생성하고 commit·push한다. 현재 그림은 아직 실행되지 않은 주행으로 만들지 않는다.

그림: 벽·정적 장애물·실제 H1-v2 상자/출현 위치·Topomap 노드·목표·상태별 궤적, CUT 회색 점선·GRAPH 주황 파선, 각 수신 chunk의 저장된 원8후보(아주 옅은 선), EC REJECT 빨간x. 시간축 패널 없음. 기술 실패는 검증된 데이터 없음으로 표시한다.

추가 분석·오프라인 재풀이·시뮬레이션은 하지 않았다. 테스트의 가짜 자료는 그림/report 코드 검증용 임시 폴더에서만 사용하고 삭제했다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_h1v2_trial.campaign --status`

로그: `../artifacts/isaac6/h1v2_trial_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_h1v2_trial.campaign > ../artifacts/isaac6/h1v2_trial_01.log 2>&1 < /dev/null &`
