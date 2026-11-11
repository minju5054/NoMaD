# U-Graph 오프라인 타당성 검증

| status | selected | completed | map_available | protocol_sha256 |
|---|---|---|---|---|
| PREPARED_NOT_RUN | 4449 | 0 | 3096 | a306eaacab407690d7083981b519786d043c7316038f47b3b17bf68a6e5532ed |

실제 개발 입력 풀이 전에는 해 존재율을 보고하지 않는다. 아래 표의 미실행 값은—이다. 기존 동결 코드·원 로그·실험 결과는 수정하지 않는다.

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

## 입력 및 해 존재율 / 시간

| scope | scene | selected | map_available | completed | EC_valid_solutions | solution_rate | job_wall_p50_s | job_wall_p95_s | job_wall_max_s | solve_11starts_p50_s | solve_11starts_p95_s | fixed_start_infeasible | reverse_in_solution | feasible_but_nonconverged |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL_SELECTED | SLW | 943 | 662 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| ALL_SELECTED | LC | 758 | 461 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| ALL_SELECTED | L2 | 904 | 630 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| ALL_SELECTED | H1 | 772 | 502 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| ALL_SELECTED | H2 | 930 | 699 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| ALL_SELECTED | H1-v2 | 142 | 142 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| ALL_SELECTED | ALL | 4449 | 3096 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| AFTER_BOX_SPAWN | SLW | 0 | 0 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| AFTER_BOX_SPAWN | LC | 0 | 0 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| AFTER_BOX_SPAWN | L2 | 718 | 523 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| AFTER_BOX_SPAWN | H1 | 242 | 184 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| AFTER_BOX_SPAWN | H2 | 762 | 605 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| AFTER_BOX_SPAWN | H1-v2 | 115 | 115 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |
| AFTER_BOX_SPAWN | ALL | 1837 | 1427 | 0 | 0 | — | — | — | — | — | — | 0 | 0 | 0 |

해 존재=hard 제약 허용오차1e−7 이내인 최종iterate 중 독립 EC-tail PASS가 하나 이상. 수렴상태는 별도 기록하며 수렴 실패여도 실제 hard+EC를 통과한 최종iterate는 유효한 feasible 해다. 입력자료 누락은 planner 실패로 세지 않는다. 시간은 SDF 로드·11starts의4worker wall·EC재검증을 포함하는 전체 job이며 solver stage wall도 따로 기록한다. 초기 상태 자체가 hard SDF/속도 한계를 위반하면 즉시 불가능으로 기록한다.

## 채택 해 유형 / 실제 동작 교차표

자료 없음

자료 없음

유형: 계획 이동거리≤1mm이면 총회전>1mrad일 때 제자리회전, 아니면 정지. 이동 해는 첫 제어 a0·v0<−1e−7이면 감속, 나머지는 전진/이동이다. |v| 제약은 후진도 허용하므로 음의속도 포함수는 별도로 보여 전진으로 오인하지 않게 한다. 표는 채택된 해만 대상으로 한다.

## 좌우 번복

| scope | common_adjacent_pairs | U_flips | actual_flips | U_rate | actual_rate |
|---|---|---|---|---|---|
| ALL | 0 | 0 | 0 | — | — |
| AFTER_BOX_SPAWN | 0 | 0 | 0 | — | — |

각 상태의 현재 heading 기준 endpoint 횡변위>1cm=LEFT,<−1cm=RIGHT,그 사이는CENTER. 직전 추출 입력과현재 입력 모두 채택되고 실제 설치경로도 있는 공통쌍에서 LEFT↔RIGHT를 센다. 균등 추출한 상태의 번복이며 전체4Hz 정책의 번복률은 아니다. 직전 U해는 실제 실행되지 않았으므로 일관성 factor는 순차 오프라인 반사실이다.

## 고정 대표 입력6개

| scene | case_id | status |
|---|---|---|
| SLW | U01268 | NOT_RUN |
| LC | U00958 | NOT_RUN |
| L2 | U00639 | NOT_RUN |
| H1 | U00041 | NOT_RUN |
| H2 | U00348 | NOT_RUN |
| H1-v2 | U04312 | NOT_RUN |

한계: 최신 보존 SDF를 고정한2.5초 단일계획이다. 다음 NoMaD 추론·depth 갱신·3D 물리는 반영하지 않는다. EC는 Graph XY를 동결 PP/SP로 실행하므로 Graph v·ω를 그대로 추종한 안전 증명이 아니다. 정지·제자리회전의 정확히 고정된 중심은 원형footprint 불변성을 사용해 같은 EC 함수의 종료점 제동 경로로 검증한다. 주행 실험 결과나 성공률을 대신하지 않는다.
