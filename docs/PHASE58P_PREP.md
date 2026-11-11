# Phase58-P 준비

| status | runs | scenes | seeds | delay_s | protocol_sha256 |
|---|---|---|---|---|---|
| FROZEN; NOT_RUN | 18 | H1-v2 / SLW / H2 | 227,228 | 0.75 | 617d7de3b84686e2c10b20c57e3c1eeade14699f61ddf60825cd09dd7df05921 |

| method | definition |
|---|---|
| CUT | Phase53 CUT fully retained +ENDPOINT latch;longest depth-safe remaining suffix,then frozen EC full/slow/STOP choice. |
| CONS | Same CUT except selection order among depth-safe/EC-passing candidates:minimum absolute angle from B->previous actually installed endpoint,then longer remaining length,then lower index. First/zero reference direction=current robot heading. Backward>90 only if no <=90candidate passes in that frozen speed tier. |
| CONS+G18 | CONS then frozen Phase53 Graph-HO job/solver. Import nightE2 HoldClearanceGraph/worker:abs(v)<.02 orabs(w/v)>8 drops only initial boundary curvature equality. Graph exact certificate and tailEC required,otherwise the selected CONS path. |

세 방법 모두 Phase53 CUT의 depth 필터·RECOVER_ROTATE·정렬·0.1m/s fallback·HMM·1s 만료·공식 도착 판정을 그대로 사용한다. ENDPOINT latch만 공통 추가하며 새 경로 설치 전까지 동결 stop_command로 정지를 유지한다. EC도 동일한 latch/정렬/속도 cap 실행기를 검사한다.

CONS는 최신 B에서 이전 실제 설치 경로 끝점 방향과 각도가 가장 작은 depth-safe 후보부터 EC 검사한다. 동률은 잔여 길이, 그다음 sample index다. 각 속도 단계 안에서 ≤90° 통과 후보가 먼저이며, 전속도 단계 자체는 기존대로 0.1m/s보다 앞선다. 최초 또는 끝점=B인 경우 기준은 현재 heading이다. Graph가 채택되면 다음 기준은 Graph 끝점이다.

CONS+G18은 Phase53 설치 배관과 E2의 조건부 시작 경계 곡률 제외 class/worker를 그대로 import한다. factor·가중치·solver 옵션·certificate는 바꾸지 않는다.

| item | value |
|---|---|
| unchanged | Phase53 depth filter,RECOVER_ROTATE,>90degree alignment,fullspeed/.1/STOP fallback,EC36tick reinspection,next9Hz reject application,HMM,1sexpiry,officialarrival,geometry/depth remain unchanged. No Phase57 MIN policy switches. |
| selector | One pure selection function reorders frozen depth-safe options by abs wrapped B-to-end direction difference and remaining length;uses frozen normal_choice for cap/fallback phases. It tests angles ascending,so a passing <=90option always precedes >90 in each tier. Fullspeed remains before slow,as frozen. |
| reference | Store only actual installed XY endpoint;recompute vector from current B at each choice. Update at every installation including Graph/cap/periodic replacements. Rejections/STOP do not update. Direction undefined at zero displacement uses current heading,without extra tuning. |
| latch | Common LatchedProfile inherits CappedNA (alignment and cap retained). Only completed flag persistence is new;reset at actual new path. Actual frozen stop_command repeats until rest. EC-tail uses the same profile and continuation state. |
| counting | Left/right from selected native candidate direction relative to robot heading;CENTER(abs angle<=1e-12) skipped. Count successive non-centre changes. Backward reference>90 and backward robot>90 reported separately;this threshold is descriptive and not a new policy gate. |
| baselines | Phase57 published runs.json,NOMAD_RAW/MIN,same scene/seed. File read only at report generation with result hash saved. No raw-log replay or rewrite;missing results/fields —. |
| order | scene then seed,methods perblock random.Random(20261118),18runs. |
| outputs | Classifications,passage,arrival/stoppedtime,side flips,backward choices,Graph adoption/solve times;one saved-log150dpi topdown perrun. Automatic report commit/push. |
| prepared | Only18config/actuallauncherargument/selection/JSON/latch/fallback/report plumbing tests. No smoke,simulator or solver execution. |

| passed | tests | dry_run | simulations_started | solver_runs | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|
| True | 10 | 18 | 0 | 0 | 617d7de3b84686e2c10b20c57e3c1eeade14699f61ddf60825cd09dd7df05921 | 1115455217664 |

좌우 전환은 실제 robot heading 기준 선택 후보 방향 부호의 전환이다. 뒤 선택은 CONS 기준 >90°와 실제 heading >90°를 구분해 남긴다. Phase57-P 같은 seed NOMAD_RAW·MIN 발표 결과를 report 생성 시 옆 열로 읽으며, 누락은 —다. 실행 중인 Phase57 파일은 변경하지 않는다.

주행 종료 후 docs/PHASE58P_RESULTS.md와 research/results/phase58p/에 표·run별 top-down을 만들고 자동 commit·push한다. 기술 실패 1회 재시도, cache 정리, 저장 v2,30GB 미만 중단,공유 실행 잠금·재개 지원.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase58p.campaign --status`

로그: `../artifacts/isaac6/phase58p_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase58p.campaign > ../artifacts/isaac6/phase58p_01.log 2>&1 < /dev/null &`
