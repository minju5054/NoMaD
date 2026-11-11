# Phase62-P 준비 — UG-GOAL / oracle 분석용

| status | runs | method | scenes | seeds | delay_s | protocol_sha256 |
|---|---|---|---|---|---|---|
| FROZEN; NOT_RUN | 6 | UG-GOAL | H1-v2 / SLW / H2 | 229,230 | 0.75 | 30e2a7ef2573ab8c343f06ce1cfe673b75266ac8de07d51eba1186dd6a1d9dd0 |

Phase61-P와 같은 oracle 관측 시점 위치추정·D075·ENDPOINT latch·EC 제동꼬리·PP/SP·정렬·회복·1s 만료를 유지한다. Phase55 HOLD는 연결하지 않는다. oracle 위치추정과 Topomap pose는 분석용 조건이다.

새 factor는 r_goal=(p_N−목표노드XY)/0.3m의 제곱합(가중1) 하나다. 목표는 사용자 확정대로 최근 도착 chunk의 관측 시점 oracle 노드+2,마지막 노드 clamp다. 주기 재풀이 때 실제 pose가 변해도 다음 chunk가 오기 전에는 목표 노드를 바꾸지 않는다.

Phase55-P의0≤v≤0.3 U-Graph/초기값11개/4process/SLSQP 옵션을 그대로 사용한다. 실제 현재 pose/v/ω에서 동기 풀이하며,XY만 기존 PP/SP로 추종한다. 실제 설치된 마지막 U 해만 일관성 prior다. 후보 해를 비용순으로 최신 EC-tail 검사해 통과한 것을 설치하고 없으면61-P CUT/fallback을 사용한다.

| item | value |
|---|---|
| factor | r=(p_N-goal_xy)/0.3;cost=sum(r²),weight1,analytic gradient via frozen terminal sensitivity |
| sigma_m | 0.3 |
| target | min(latest delivered chunk observation-time oracle closest_node+2,goal_node) |
| target_hold | fixed between chunks including periodic replans |
| initial_state | actual pose,v,omega at synchronous solve;no predicted B |
| prior | last actually installed U solution with frozen Phase55 time-overlap interpolation |
| solver | Phase55 Graph(0<=v<=.3),all original factors/hard constraints/11starts/4process/maxiter100/ftol1e-8/feasibility1e-7 unchanged |
| trigger | chunk arrival or Phase55 independent36tick planning clock;next9Hz control tick actual state;coalesce simultaneous triggers |
| execution | Phase61 CUT PP/SP with ENDPOINT latch,alignment/recovery/full-.1-STOP fallback and1s expiry;NO Phase55 HOLD |
| certificate | same latest-map Phase61 EC-tail;failed/no hard-feasible U uses CUT paths/fallback;recovery not interrupted |
| stationary | frozen Phase55 zero-length XY endpoint STOP (no fake path);not direct Graph angular tracking |
| watchdog | original Phase55 RPC300s technical watchdog and existing launcher600s;no new solver deadline |

| passed | tests | dry_run | simulations_started | solver_runs | real_replays | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|---|
| True | 8 | 6 | 0 | 0 | 0 | 30e2a7ef2573ab8c343f06ce1cfe673b75266ac8de07d51eba1186dd6a1d9dd0 | 1110350630912 |

보고서는61-P 같은seed의 CUT/CONS/CONS+G18 결과를 옆 열에 두고 결과·상자통과·도착/정지시간·U 채택률·채택해 길이 중앙값을 표시한다. 요청한 추가열은 실제 풀이 pose와 목표노드 거리 중앙값이다. 회전만 있는 정지XY 해는 기존 U 규칙대로 STOP이며 PP가 Graph θ/속도를 직접 실행하지 않는다.

시뮬레이션·smoke·solver·실제 로그 재생은 실행하지 않았다. 종료 후 docs/PHASE62P_RESULTS.md와 research/results/phase62p/를 자동 생성하고 PNG도 강제 추가하여 commit·push한다. 동일한1회 기술 재시도/cache정리/저장v2/30GB중단/잠금·재개를 적용한다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase62p.campaign --status`

로그: `../artifacts/isaac6/phase62p_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase62p.campaign > ../artifacts/isaac6/phase62p_01.log 2>&1 < /dev/null &`
