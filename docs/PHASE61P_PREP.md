# Phase61-P 준비 — oracle 위치추정 분석용 조건

**Oracle 위치추정은 분석용 조건이다. 실용 위치추정 방법의 성능을 의미하지 않는다.**

| status | runs | methods | scenes | seeds | delay_s | protocol_sha256 |
|---|---|---|---|---|---|---|
| FROZEN; NOT_RUN | 18 | CUT / CONS / CONS+G18 | H1-v2 / SLW / H2 | 229,230 | 0.75 | 63d91d2ecae5eecef4ad3edfbcadd18ae0cb107c6e864f2fb8e80f71c9a527e4 |

사용자 확정대로 영상 관측 시점 observation_pose(시뮬레이터 실제 robot pose)의 XY 최근접 Topomap 노드를 사용한다. 동률은 작은 node ID다. HMM은 실행하지 않는다. 이 노드를 현재 노드로 두고 기존 radius4 후보 창·거리 threshold3 부목표·closest==goal 선언 규칙을 적용한다. D075 전달 지연은 유지한다.

관측 pose를 사용하므로 선언 시점의 현재 pose를 다시 조회해 노드를 바꾸지 않는다. oracle 노드가 이전 창 밖이어도 현재 노드를 중심으로 원래 candidate_range 함수를 호출하므로 필요한 거리·condition이 같은 창 안에 있다. NoMaD decoder/RNG는 기존과 동일하다.

Phase58-P의 controller·depth·EC-tail·latch·후보 선택·회복·정렬·0.1 fallback·1s 만료·Graph·평가기와 장면 기하는 그대로다. 새 seed는 기존 jitter 생성 규칙에 입력하고 H1-v2 고정 상자는 유지한다. 방법 순열 RNG도 Phase58과 같아 블록 순서상 방법 배치는 동일하다.

| item | value |
|---|---|
| source | simulator actual robot observation_pose at NoMaD image capture tick |
| clock | observation_pose |
| delivery_delay_s | 0.75 |
| nearest | global Euclidean XY nearest topomap node;lowest node id on tie |
| HMM_used | False |
| window | compute current oracle node first;unchanged candidate_range(current_node,goal,radius4),including official inclusive-end rule |
| subgoal | min(current_node+int(distance_at_current_node<3),candidate_end) |
| arrival | unchanged closest==goal declaration on delivered inference |
| oracle_obstacles_for_control | False |
| analysis_only | True |
| new_seeds | [229, 230] |

| passed | tests | dry_run | simulations_started | solver_runs | real_replays | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|---|
| True | 9 | 18 | 0 | 0 | 0 | 63d91d2ecae5eecef4ad3edfbcadd18ae0cb107c6e864f2fb8e80f71c9a527e4 | 1112288595968 |

보고서는 방법별 결과·상자 통과·도착/정지 시간·좌우 전환·뒤 선택·Graph 채택률과 동일(scene,seed) 쌍 성공 차이3개를 표시한다. 두 run 모두 기술 PASS인 짝만 계산하며 미완료는 —다. 그림에도 oracle 분석 조건을 명시한다.

시뮬레이션·smoke·solver·실제 로그 재생은 실행하지 않았다. 종료 시 docs/PHASE61P_RESULTS.md 및 research/results/phase61p/를 생성하고 PNG를 명시적으로 강제 추가해 자동 commit·push한다. 1회 기술 재시도,cache 정리,저장v2,30GB 중단,공유 잠금·재개는 기존과 같다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase61p.campaign --status`

로그: `../artifacts/isaac6/phase61p_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase61p.campaign > ../artifacts/isaac6/phase61p_01.log 2>&1 < /dev/null &`
