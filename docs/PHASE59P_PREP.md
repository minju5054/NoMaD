# Phase59-P 준비

| status | runs | methods | scenes | seeds | delay_s | protocol_sha256 |
|---|---|---|---|---|---|---|
| FROZEN; NOT_RUN | 18 | CUT / CONS / CONS+G18 | H1-v2 / SLW / H2 | 227,228 | 0.75 | 27081d1ff2f87d8d083ce8f9823e472c2b225b552573a7b32fa116f8cdc14780 |

Phase58-P 코드·장면·jitter·seed·블록 내 순서를 그대로 사용한다. 실행 함수도 Phase58 install/run_without_oracle을 그대로 import한다. 유일한 정책 변경은 HMM 전이를 HMM_REPLAY의 NET으로 연결하는 것이다.

w=round(현재 영상 observation tick의 odometry XY와 현재 MAP 진입 XY 사이 거리/ℓ). ℓ은 기존 양수 인접 Topomap 노드 간격 중앙값,최소1 없음,자기 전이 포함,MAP 변경 때 진입 위치 갱신이다. Python의 ties-to-even round와 초기 균등 prior도 HMM_REPLAY 그대로다. MEM은 적용하지 않는다.

Phase43의 후보 창(radius4),방출,subgoal threshold3 및 end-window clamp,closest==goal 선언은 원래 함수를 재사용한다. 현재 영상의 observation_pose를 exact odometry로 사용하며 실제 정답 노드나 목표 좌표를 필터에 넣지 않는다. NET의 MAP이 달라지면 다음 창이 달라지는 것은 동일한 기존 창 규칙의 결과다.

| item | value |
|---|---|
| success | unchanged declared distance<=.5 and collision-free |
| reached_goal | min(saved72Hz goal_distance)<=.7 regardless of declaration |
| arrived_without_declaration | reached_goal_0p7 and no declared_arrival through termination;additional<=.5 counter reported separately |
| false_goal | inference MAP==goal AND observation-time true_node<goal-2;count and affected runs,distinct from distance-based wrong stop |
| declaration_nodes | logged closest_node and nearest node at actual declared pose |
| baseline | Phase58 same(scene,seed,method),new supplementary fields derived from saved logs only when final report runs |

| passed | tests | dry_run | simulations_started | solver_runs | real_replays | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|---|
| True | 8 | 18 | 0 | 0 | 0 | 27081d1ff2f87d8d083ce8f9823e472c2b225b552573a7b32fa116f8cdc14780 | 1114704953344 |

시뮬레이션·smoke·실제 로그 재생·solver 실행은 하지 않았다. 합성 NET 동치성/실제 worker 배관/18개 실제 launcher 인자/JSON/감사 체인/report 검증만 수행했다. 기본 성공 조건은 그대로0.5m이며0.7m 도달·미선언은 보조 집계다.

끝나면 docs/PHASE59P_RESULTS.md와 research/results/phase59p/에 Phase58 같은키 비교 표와 run별 top-down을 생성하고 자동 commit·push한다. Phase58 보조 항목은 그때 저장 로그에서 읽어 계산하며 기존 파일은 수정하지 않는다. 1회 기술 재시도,cache 정리,저장v2,30GB 미만 중단,공유 실행 잠금·재개를 유지한다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase59p.campaign --status`

로그: `../artifacts/isaac6/phase59p_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase59p.campaign > ../artifacts/isaac6/phase59p_01.log 2>&1 < /dev/null &`
