# Phase55-P 준비

| status | runs | method | scenes | conditions | seeds | protocol_sha256 |
|---|---|---|---|---|---|---|
| FROZEN; NOT_RUN | 24 | U-GRAPH | SLW, LC, L2, H1, H2, H1-v2 | D075/D150 | 221,222 | 6ebbc5ead8a42acac1eecd16eb1e609eaefed9bc5d9697e5abe41d8f993cd61b |

시뮬레이션·저장 입력 재풀이·smoke는 실행하지 않았다. 24개 조합의 실제 launcher 인자 검증과 배관 테스트만 수행했다. 실행 순서는 조건 → seed → 장면이며 방법은 하나다.

Graph의 변경은 0≤v≤0.3뿐이다. 해석적 SLSQP 11개 초기값을 4개 worker로 동기 풀이하고, 현재 pose에서 최신 지도 EC-tail을 통과한 최소 비용 해를 설치한다. 직전 실제 설치 U 해만 일관성 prior로 사용한다. 원 Graph의 계획 v·ω 대신 동결 PP+SP가 XY를 따라가므로, 계획 운동학과 실제 명령은 같지 않다.

chunk 도착 및 36tick 재검사 때 재풀이한다. 36tick이 9Hz 제어 tick 사이이면 다음 제어 tick의 실제 상태를 사용하며 검사·적용 tick과 지연을 기록한다. 해 없음/EC 거절은 CUT-HOLD fallback, 회복 중 설치는 보류한다. 제자리 회전 해도 XY가 정지면 PP의 끝점 STOP으로 처리하고 별도 기록한다.

수치 풀이 시간 상한을 새로 추가하지 않았다. 기존 launcher 600초 및 RPC 300초 watchdog 초과는 기술 실패이며 한 번 재시도한다. 준비 단계에서 성능·실행 시간은 측정하지 않았다.

| item | value |
|---|---|
| basis | Phase53 CUT EC braking tail/HMM/official arrival/depth/filter/geometry/fallback unchanged;receipt expiry replaced by frozen Phase52 HoldCore and no-minimum-residual hold rule. No R2/R3,NoMaD or Graph18 refinement. |
| graph | Import nomad_ugraph.Graph/SLSQP analytically;only inequalities .3+v>=0 become v>=0,matching nonnegative initial controls. N25,dt.1,11starts,maxiter100,ftol1e-8,tolerance1e-7 and all soft factors frozen. First omega is saved actual omega. No tuning; no new numerical deadline. |
| prior | Last actually installed U-Graph states and installation simulation time,using frozen shifted_prior overlap. CUT fallback does not become a U solution and never advances its prior clock. |
| periodic | Independent36tick clock starts at first chunk. At next9Hz control tick,solve from then-actual pose/latest depth. Frozen ongoing EC checks and reject handling retained. CHUNK+PERIODIC at same control tick coalesce to one solve;both triggers recorded. |
| recovery | RECOVER_ROTATE and WAIT_FRESH remain frozen. Attempts may be computed but are not installed mid-recovery;RECOVERY_DEFERRED counted in adoption denominator. |
| stationary | Zero-length feasible XY is an endpoint STOP,validated by frozen EC-tail using StationaryEndpoint(circle footprint). No fake path;PP cannot execute planned in-place theta without XY. Recorded as stationary installation,not a graph-angular controller. |
| installation | Current actual pose, synchronous system-Python RPC. Check hard-feasible results in ascending objective/start-index order using latest-map EC-tail and current cap. Failed U uses same CUT/HOLD fallback;0.1cap persists except full-speed fresh installation. No new controller. |
| time | Log solve_s for full11start4workerjob,rpc_s,and total_s including independentEC. Existing600s launcher watchdog and300s RPC watchdog are technical errors,not successful no-solution outcomes. |
| telemetry | classification,box passage,arrival/stopped/ALIGN_ROTATE seconds,appliedU/attempts,solve p50/p95 and total p50/p95,left-right reversals. Reversal=end XY lateral in current B heading,1cm deadband,compare consecutive non-centre installed sides;report-only. |
| comparison | Published same seed/scene/delay Phase53 CUT and Phase52 CUT-HOLD only. Missing H1-v2 comparisons —. Different days and original expiry/EC differences are explicit;no historical replay. |
| execution | 24serial runs,one technical retry,global lock,resume,storagev2,cache cleanup,30GB reserve,automatic report+commit+push. No preparation smoke/simulation/real input solves. |

| passed | tests | dry_run | simulations_started | offline_solves | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|
| True | 13 | 24 | 0 | 0 | 6ebbc5ead8a42acac1eecd16eb1e609eaefed9bc5d9697e5abe41d8f993cd61b | 1118870528000 |

비교군은 기존 Phase53-P CUT·Phase52-P CUT-HOLD의 같은 seed·조건이다. H1-v2 등 없는 항목은 —로 표시한다. 종료 후 docs/PHASE55P_RESULTS.md와 research/results/phase55p/를 자동 생성하고 commit·push한다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase55p.campaign --status`

로그: `../artifacts/isaac6/phase55p_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase55p.campaign > ../artifacts/isaac6/phase55p_01.log 2>&1 < /dev/null &`
