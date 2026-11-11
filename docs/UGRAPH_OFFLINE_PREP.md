# U-Graph 오프라인 준비

| status | selected | map_available | maximum_solver_starts | simulations | development_solves | protocol_sha256 |
|---|---|---|---|---|---|---|
| PREPARED_NOT_RUN | 4449 | 3096 | 34056 | 0 | 0 | a306eaacab407690d7083981b519786d043c7316038f47b3b17bf68a6e5532ed |

긴 계산은 이 세션에서 실행하지 않았다. 아래 명령은 실제 주행·NoMaD 추론·렌더를 시작하지 않고 저장된 입력만 재풀이한다. 새 코드는 research/nomad_ugraph/에만 추가했고 기존 동결 코드는 변경하지 않았다.

| reason | n |
|---|---|
| NO_PUBLISHED_DEPTH_MAP | 436 |
| READY | 3096 |
| LATEST_SNAPSHOT_NOT_RETAINED | 917 |

개발144run에서 균등추출4,449상태. 최신 보존 지도 있는3,096상태에서최대34,056초기값을푼다.436상태는depth발행없음,917상태는그순간최신파일미보존이며과거지도로대체하지않는다. 누락은planner실패와분리한다. 무거운inventory/cache는artifacts/isaac6/ugraph_offline_01에두고Git에는요약만저장한다.

## 구현 해석과 검증 범위

| item | value |
|---|---|
| state/control | x=(x,y,unwrapped theta,v),u=(a,omega),N25,dt.1;actual saved pose/v fixed,first omega fixed to actual saved omega |
| dynamics | Exact constant a/omega unicycle interval;state variables algebraically eliminated,50control unknowns;analytic chained Jacobians. Speed/SDF checked at all26nodes,terminal v25=0;no start relaxation. |
| prior | All8world-fixed candidate suffixes after closest B projection;arc-length26point resampling within actual remaining length;do not discard short/zero-length candidates. Sum all26position errors/sigma.1 squared;minimum component active,lowest index tie. |
| consistency | Immediately preceding sampled state in same run must have an EC-accepted U solution. Linear time alignment on overlapping horizon only,sigma.2;no extrapolation after previous horizon;missing/no solution clears prior. |
| progress | Negative projection -(p25-p0) dot active candidate endpoint direction from B,weight1;no added desired progress length. Zero endpoint direction disables this term. |
| clearance | sum(max(0,.15-d)/.05)^2;d already subtracts radius.09. Hard d>=.025 at26nodes. Field-domain inequalities only keep SDF queries inside recorded grid. |
| smoothness | sum((a[k+1]-a[k])/.5)^2+sum((omega[k+1]-omega[k])/.4)^2;no extra weights/heading/reference factors |
| initialization | 8candidate-derived bounded steering/control seeds + brake-to-stop + brake/rotate-left + brake/rotate-right;actual initial velocity retained;terminal braking seeds;no A* or oracle. |
| EC | Direct frozen Phase52EC braking-tail certify on Graph XY using actual saved pose/v/omega and frozen PP/SP. Graph v/omega are NOT followed by this EC. Exact stationary center and zero velocities use endpoint controller with the same EC;circle footprint invariant,including in-place rotation. No epsilon path. |
| selection | Lowest objective among hard-feasible final iterates that pass independent EC;check sorted final iterates until firstPASS. Convergence status separately reported;hard-feasible nonconverged iterates can be accepted. Tolerance1e-7;no kinematic relaxation. |
| sampling | All four requested development cohorts,144runs,max40uniform ordinal arrivals/run. Select before map check. Latest published snapshot at latch time must physically exist;no older substitute. NIGHT225/226 forbidden. |
| comparison | Actual mode and installed path at same arrival time. Side=end lateral offset relative current robot heading;deadband1cm. Adjacent sampled pairs common to accepted U and recorded path only;not full4Hz reversal rate. |
| types | Travel<=1mm:rotation>1mrad=>in-place rotation,otherwiseSTOP;moving with first a0*v0<-1e-7=>DECEL,otherwiseFORWARD/MOVE;reverse velocity flag always reported because /v/ allows reverse. |
| offline_limit | Saved actual starting states,one fixed2.5s path/snapshot;previous U never physically executed;no new NoMaD/depth/physics. Next2.5s actual trace is visual comparison only. |

질문의 미지정 세부에 대해서는 위 해석을 코드/프로토콜에 명시했다. 특히 EC는Graph의시간계획을실행하는검사가아니고,동결PP/SP에XY를주는별도안전검사다. 제자리정지/회전은원형footprint불변성을사용한다. |v|가음수도허용하므로후진포함수를별도로보고한다.

## Solver 선택

| name | analytic_jacobian | maxiter | ftol | workers | starts | cyipopt_available | casadi_available | choice_reason | comparative_speed_test | technical_watchdog_per_input_s |
|---|---|---|---|---|---|---|---|---|---|---|
| SLSQP | True | 100 | 1e-08 | 4 | 11 | False | False | Only installed usable optimizer;SciPy SLSQP. IPOPT bindings unavailable,no install performed;cannot claim faster than an unmeasured IPOPT. | UNAVAILABLE_NO_IPOPT_BINDING | 300 |

현재/usr/bin/python3에SciPy1.11.4만있고cyipopt/casadi가없어IPOPT와의직접속도비교는수행할수없다. SLSQP를사용가능한선택으로고정했으며IPOPT보다빠르다고주장하지않는다. 패키지설치없음. 상태를제어로소거해정확한hard운동학을항상만족시키고50변수의dense SLSQP를사용한다.

단위테스트: 운동학·목적함수·SDF/속도/종단제약의해석적Jacobian vs 중앙차분(≤1e−5), max-mixture전환, 초기ω고정,11초기값, 이전해시간정렬, 합성직선해의hard조건과독립EC-tail,정지/회전footprint를확인했다. 실제개발입력풀이결과는아직없다.

## 실행·재개·출력

같은명령으로재개하면완료case는protocol/직전해ID를확인해재사용한다. run내시간순서를유지하고11starts를4CPU worker로계산한다. 매60초진행률,case별원자적cache,장면별중간집계. 오류·신호는FAILED/INTERRUPTED와원인을저장한다. 입력300초watchdog는기술실패로중단하며해없음으로세지않는다. 종료시report·6대표그림·commit·push를자동수행한다. 전체입력은풀지않아정밀한총시간추정은없으며,수천job이므로사용자nohup실행대상이다.

출력: docs/UGRAPH_OFFLINE.md, research/results/ugraph/. 그림은결과를보기전에고정한각장면입력1개(총6개),현재후보8개·U계획·저장된실제다음2.5초를겹친다. 입력이run끝에가까우면실제궤적은저장된길이만그린다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_ugraph.evaluate --status`

로그: `../artifacts/isaac6/ugraph_offline_01.log`

본 오프라인 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/nomad-ugraph-mpl /usr/bin/python3 -u -m nomad_ugraph.evaluate > ../artifacts/isaac6/ugraph_offline_01.log 2>&1 < /dev/null &`
