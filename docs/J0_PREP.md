# J0 준비 — 장면 선별

| status | runs | method | seeds | order | protocol_sha256 |
| --- | --- | --- | --- | --- | --- |
| FROZEN / NOT_RUN | 20 | OURS-noEC | 221–222 | 0s 10 → 0.75s 10 | 42ebab18c221fdf5525ec83ba5692e8b84eb913b2df07d8f1dd88b743c5d7cee |

J1 전체 실험은 구현·실행하지 않았다. 재사용할 공통부만 research/nomad_j1/에 추가하고, J0 한 방법(OURS-noEC)을 연결했다. 기존 동결 코드·결과는 변경하지 않는다.

종료 판정은 Phase18과 동일(0.3m). 공식 NoMaD closest_node와 subgoal을 사용하지만 목표 노드 기반 종료·HMM·NET은 없다. world 좌표는 관측 pose에 고정하고 적용 B의 suffix 잔여 길이가 가장 긴 SAFE 후보를 쓴다.

실행은 Phase18 PP+CURV(lookahead0.25m,vmax0.3,|ω|≤0.4,4/9/72Hz),1초 만료다. SP·출발 정렬·회전 회복·STOP_WAIT 특수처리·EC 없음. SAFE가 없으면 현재 경로와 기존 유효시간만 유지한다. ENDPOINT는 기존 PP 끝점 판정에 걸리면 새 경로 설치까지0명령을 유지한다.

Graph는 Phase17/18 ClearanceGraph(FlagGraphV4+depth hard+CLR soft)와 원 CPU worker·수락·폐기 규칙을 그대로 호출한다. 즉 FRESH SAFE 원경로를 즉시 설치하고 비동기 보정 결과는 기존 SUPERSEDED/STALE/만료 검사 후 적용한다. 새 factor·튜닝은 없다. NoMaD에는 RGB만 입력하며 지도 unknown은 기존처럼 free다.

| scene | axis | box_id | threshold_m | formula |
| --- | --- | --- | --- | --- |
| H1-v2 | y | DynamicObstacle | 1.6 | box center along axis + projected half extent + 0.30 |
| SLW | x | Slalom3 | 4.6 | box center along axis + projected half extent + 0.30 |
| H2 | x | DynamicObstacle2 | — | actual_last_spawn.center_x + projected_half_extent_x + 0.30 |
| LC | y | AfterCorner | 2.4 | box center along axis + projected half extent + 0.30 |
| CL | x | Clutter4 | 4.4971 | box center along axis + projected half extent + 0.30 |

H1-v2는 y=1.10 돌발 상자의 +y 먼 면+0.30=1.60m. H2는 실제 두 번째 spawn 상자의 center_x+회전을 고려한 x투영 반폭+0.30을 동결하며 미생성이면 checkpoint 미측정이다. run별 임계좌표·시작점에서의 진행축 거리를 기록한다. 방법이1개라 방법 간 좌표 차이는 N/A(범위0), 동일seed 지연 조건 간 차이는 별도 보고한다.

선별: 0s 성공2/2 AND 0.75s checkpoint 평균>0s 평균. 양 조건 각2개가 모두 관측된 장면만 비교(결측 대체 없음). 통과 장면의 0s 평균이 짧은 순 최대3개; 미달이면 통과 장면만. 동률은 H1-v2·SLW·H2·LC·CL 순서다.

| passed | tests | actual_launcher_dry_runs | simulations_started | inference_started | graph_solves_started | protocol_sha256 | disk_free_bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| True | 9 | 20 | 0 | 0 | 0 | 42ebab18c221fdf5525ec83ba5692e8b84eb913b2df07d8f1dd88b743c5d7cee | 1109563097088 |

| source | n | per_run_median_s | per_run_p95_s | total20_at_median_min | total20_at_p95_min | caveat |
| --- | --- | --- | --- | --- | --- | --- |
| stored Phase53-P/H1-v2 trial launcher durations; different executor, estimate only | 44 | 174.05 | 194.15 | 58.016 | 64.717 | Includes startup; J0 audit/report/archive costs can differ.1h is target,not guarantee; partial remains resumable. |

1시간은 목표다. 기존 유사 run 중앙값 기준 추정과 p95 기준 추정을 함께 기록했다. 세션1시간이 지나면 진행 중 run을 마치고 새 run 전 중단·PARTIAL 보고하며 같은 명령으로 재개한다. 두 lock(전역/해당root),짧은socket,원자적state,디스크30GB하한,run종료cache정리를 사용한다. Phase18처럼 기술 실패 재시도는 없고 원자료를 보존한다.

완료/시간중단 시 docs/J0_RESULTS.md·research/results/j0/ 보고서 자동 생성·commit·push. 본 실행·smoke·실제 재풀이 없음.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_j0.campaign --status`

로그: `../artifacts/isaac6/j0_01.log`

본 실행(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_j0.campaign > ../artifacts/isaac6/j0_01.log 2>&1 < /dev/null &`

## 별도 worktree의 H2 등록 범위 수정

원래20회 명령은 최초 J0 준비 기록이다. 현재 수정 브랜치에서는 원 J0 종료 후 H2 네 개만 새 root에서 실행하고 나머지16개와 합쳐 보고한다. [수정·동등성 검증](J0_SDF_FIX.md). 실행 중인 원 작업 트리는 변경하지 않는다.

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer-j0-sdf-fix && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_j0.h2_rerun > ../artifacts/isaac6/j0_h2_sdf_01.log 2>&1 < /dev/null &`
