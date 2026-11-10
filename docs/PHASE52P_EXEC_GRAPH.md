# 실행 궤적 제약 Graph: 저장 EC REJECT 입력의 오프라인 가능성

| phase | scene | raw_reject_checks | unique_full_speed_inputs | missing_map | completed | found | found_fraction | initial_state_infeasible |
|---|---|---|---|---|---|---|---|---|
| phase47c | H1 | 37 | 20 | 0 | 20 | 20 | 1 | 0 |
| phase47c | H2 | 19 | 11 | 0 | 11 | 11 | 1 | 0 |
| phase47c | L2 | 23 | 9 | 0 | 9 | 9 | 1 | 0 |
| phase47c | LC | 10 | 10 | 0 | 10 | 10 | 1 | 0 |
| phase47c | SLW | 232 | 79 | 0 | 79 | 68 | 0.86076 | 6 |
| phase52p | H1 | 60 | 24 | 0 | 24 | 24 | 1 | 0 |
| phase52p | H2 | 265 | 70 | 0 | 70 | 67 | 0.95714 | 0 |
| phase52p | L2 | 141 | 51 | 0 | 51 | 47 | 0.92157 | 1 |
| phase52p | LC | 33 | 15 | 0 | 15 | 15 | 1 | 0 |
| phase52p | SLW | 301 | 131 | 0 | 131 | 127 | 0.96947 | 0 |
| phase47c | ALL | 321 | 129 | 0 | 129 | 118 | 0.91473 | 6 |
| phase52p | ALL | 800 | 291 | 0 | 291 | 280 | 0.9622 | 1 |
| ALL | ALL | 1121 | 420 | 0 | 420 | 398 | 0.94762 | 7 |

## 채택 해 변위와 계산시간

| phase | scene | displacement_mean_median_m | displacement_max_median_m | mean_edit_p95_m | displacement_max_overall_m | timed_solver_events | solve_verify_sum_p50_s | solve_verify_sum_p95_s |
|---|---|---|---|---|---|---|---|---|
| phase47c | H1 | 0 | 0 | 2.3865e-06 | 0.00018675 | 20 | 0.093091 | 1.0013 |
| phase47c | H2 | 0 | 0 | 3.0753e-05 | 0.00033926 | 11 | 0.14486 | 3.7045 |
| phase47c | L2 | 0 | 0 | 0.0095211 | 0.093604 | 9 | 0.19629 | 7.0824 |
| phase47c | LC | 0 | 0 | 0 | 0 | 10 | 0.089411 | 0.6158 |
| phase47c | SLW | 0 | 0 | 0.00070112 | 0.11355 | 73 | 0.31838 | 6.6029 |
| phase52p | H1 | 0 | 0 | 0 | 0.0047404 | 24 | 0.075366 | 1.1521 |
| phase52p | H2 | 0 | 0 | 0.037558 | 1.0607 | 70 | 1.4443 | 7.1467 |
| phase52p | L2 | 0 | 0 | 0.017754 | 1.0607 | 50 | 1.372 | 8.3645 |
| phase52p | LC | 0 | 0 | 0 | 0 | 15 | 0.082093 | 0.66597 |
| phase52p | SLW | 0 | 0 | 0.0017751 | 0.068127 | 131 | 0.13225 | 5.1745 |
| phase47c | ALL | 0 | 0 | 0.00077355 | 0.11355 | 123 | 0.195 | 6.5901 |
| phase52p | ALL | 0 | 0 | 0.009832 | 1.0607 | 290 | 0.15123 | 6.9121 |
| ALL | ALL | 0 | 0 | 0.0085605 | 1.0607 | 413 | 0.17524 | 6.7505 |

## 기존 대안·재표집·최적화 구분

| phase | scene | original_any_tail_pass | all_original_reject | resampling_only_rescue | optimized_rescue | optimized_mean_edit_median_m | optimized_max_edit_median_m | selected_displacement_from_B_le_5cm |
|---|---|---|---|---|---|---|---|---|
| phase47c | H1 | 17 | 3 | 2 | 1 | 4.7729e-05 | 0.00018675 | 1 |
| phase47c | H2 | 11 | 0 | 0 | 0 | 6.1507e-05 | 0.00033926 | 3 |
| phase47c | L2 | 5 | 4 | 2 | 2 | 0.0062519 | 0.05 | 6 |
| phase47c | LC | 10 | 0 | 0 | 0 | — | — | 0 |
| phase47c | SLW | 50 | 29 | 13 | 5 | 0.00073296 | 0.0028821 | 22 |
| phase52p | H1 | 19 | 5 | 4 | 1 | 0.0023814 | 0.0047404 | 4 |
| phase52p | H2 | 43 | 27 | 8 | 16 | 0.0084649 | 0.037819 | 44 |
| phase52p | L2 | 38 | 13 | 1 | 8 | 0.0098115 | 0.035686 | 20 |
| phase52p | LC | 12 | 3 | 3 | 0 | — | — | 0 |
| phase52p | SLW | 104 | 27 | 17 | 6 | 0.0040785 | 0.020509 | 53 |
| phase47c | ALL | 93 | 36 | 17 | 8 | 0.00086827 | 0.0029295 | 32 |
| phase52p | ALL | 216 | 75 | 33 | 31 | 0.0087381 | 0.031732 | 121 |
| ALL | ALL | 309 | 111 | 50 | 39 | 0.006838 | 0.024901 | 153 |

## 0.1m/s 입력: 집계만, 재풀이 없음

| phase | scene | slow_reject_records | slow_unique_not_solved |
|---|---|---|---|
| phase47c | SLW | 80 | 18 |
| phase47c | LC | 0 | 0 |
| phase47c | L2 | 10 | 2 |
| phase47c | H1 | 7 | 3 |
| phase47c | H2 | 0 | 0 |
| phase52p | SLW | 46 | 12 |
| phase52p | LC | 0 | 0 |
| phase52p | L2 | 42 | 8 |
| phase52p | H1 | 4 | 1 |
| phase52p | H2 | 34 | 8 |

## 정식화와 사전 고정 정의

| item | value |
|---|---|
| phase | 52-EC-OFFLINE |
| input_phases | ['phase47c', 'phase52p'] |
| expected_runs | 100 |
| start | B=recorded EC start actual pose;recorded actual v,w;exact check snapshot only;missing maps excluded with counts |
| termination | Brake request at earlier path endpoint recognition or2.0s;latched stop_command until v=0,w=0 |
| clock | 72Hz integration,9Hz control. Continuation keeps absolute phase;2s brake request applied at next9Hz tick (0 or4 extra ticks on these logs),all held-motion ticks checked |
| replay | Original INSTALL checks rebuild fresh frozen NA profile;continuation restores installed generation and recorded control-state evolution before check;regression matches pass,duration,endpoint,clearance<=1e-6m |
| tail_comparison | All recorded checks;confirmed PASS->REJECT requires original replay match. Mismatches separated,not claimed as tail effects |
| graph | Reduced SE(2) execution graph:14 XY variables (B+7 future points);all72Hz SE(2) states eliminated through frozen PP/SP integrate_se2 equality factors;no independent yaw/time variables |
| graph_reference | Each of8 current stored NoMaD candidates separately:project B,connect B to suffix,re-sample8 arc-length points;B fixed;no0.25m short cutoff,degenerate suffix reported |
| objective | sum_i //p_i-q_candidate_i//^2 only;unit weight,no extra sigma or tuning |
| bounds | Each future XY coordinate within +/-0.75m of its own initial reference |
| execution_constraint | Minimum continuous circular-footprint clearance on PP/SP72Hz trajectory including braking tail >=0.025m;terminal v=w=0 by construction |
| graph_clock | New-path INSTALL EC semantics:initial PP control at t=0,then9Hz;actual initial pose/v/w from check. No replanning delay,NoMaD regeneration or depth update simulated |
| optimizer | {'method': 'SLSQP', 'maxiter': 100, 'ftol': 1e-08, 'objective_gradient': 'analytic', 'constraint_gradient': '2-point finite difference', 'eps_m': 1e-06} |
| acceleration | Compiled arithmetic mirror with exact arc/site clearance clipped only above+0.075m;no fast-math;geometry-equivalent .025 feasible set;tested vs Python |
| acceptance | Solver success + numerical violation<=1e-7 + independent Python braking-tail EC >=.025 and terminal stop;reject independent failures |
| infeasible_boundary | If fixed initial footprint itself fails exact.025 clearance,all8 starts proven infeasible without SLSQP;count as no solution and record reason |
| dedup | Unique(run,tick,pose,v,w,snapshot frame/file,current candidate bank id,cap). Original REJECT only;full-speed inputs solved once;0.1m/s unique inputs counted but never solved |
| candidate_selection | Lowest objective among independently verified8 solutions,tie sample index. Report original-candidate tail PASS and solved-only rescue separately |
| timing | Four independent event workers,BLAS1. Per-event time includes8 starts and independent checks;map loading/startup separate. Per-start timing also reported |
| limitations | Same historical data;offline feasibility only. Distance-only objective can shorten/stop or rotate without progress:travel and <=5cm motion reported. No oracle used for solve/certificate |
| no_simulation | True |
| no_new_inference | True |
| no_parameter_tuning | True |

변수는 후보별 B+7개 XY점이다. SE(2) 상태 x_j=(x,y,theta)는 PP/SP 명령과 72Hz integrate_se2 등식으로 결정되어 최적화에서 소거된다. 독립 yaw·시간변수나 새로운 조향기는 사용하지 않는다. 목적은 sum_i ||p_i-q_ki||² 하나이고, 제약은 제동 꼬리 포함 실행 궤적의 최소 footprint depth clearance>=0.025m와 최종v=omega=0이다. 목표/진전/길이 항은 추가하지 않아 짧게 멈추거나 회전만 하는 해도 가능하며 별도로 표시한다.

목적 gradient는 해석적, 실행 제약 gradient는 2점 유한차분(eps=1e-6m)이다. 최적화 내부 산술 커널과 별개로 동결 Python 제어기·적분·exact swept 검사로 다시 PASS한 해만 해 찾음으로 센다. 원 후보가 이미 새 EC를 통과한 경우와 모든 원 후보가 거절됐는데 보정이 통과한 경우를 분리한다. Graph 계산시간은 `solve_verify_sum_p50/p95_s`: 입력1개에서 기록한8개 초기화 solve+독립 검증 시간을 합산한 값이며 solver가 실제 시작한 입력만 포함한다. `eight_start_p50/p95_s`는 원 후보8개의 비교용 EC 검사와 초기상태 검사까지 포함한 분석 호출 전체 wall time이다. 지도 디스크 로드·프로세스 시작은 두 값에서 제외한다. 초기 B 불가능으로 solver를 생략한 입력 수를 별도 표시하며, 그 초기검사 시간만은 따로 계측되지 않았다.

## Solver 상태

| phase | scene | status | message | starts |
|---|---|---|---|---|
| phase47c | H1 | 0 | Optimization terminated successfully | 153 |
| phase47c | H1 | 8 | Positive directional derivative for linesearch | 4 |
| phase47c | H1 | 9 | Iteration limit reached | 3 |
| phase47c | H2 | 0 | Optimization terminated successfully | 84 |
| phase47c | H2 | 9 | Iteration limit reached | 4 |
| phase47c | L2 | 0 | Optimization terminated successfully | 51 |
| phase47c | L2 | 8 | Positive directional derivative for linesearch | 4 |
| phase47c | L2 | 9 | Iteration limit reached | 17 |
| phase47c | LC | 0 | Optimization terminated successfully | 73 |
| phase47c | LC | 8 | Positive directional derivative for linesearch | 6 |
| phase47c | LC | 9 | Iteration limit reached | 1 |
| phase47c | SLW | 0 | Optimization terminated successfully | 439 |
| phase47c | SLW | 8 | Positive directional derivative for linesearch | 78 |
| phase47c | SLW | 9 | Iteration limit reached | 67 |
| phase47c | SLW | None | INFEASIBLE_FIXED_INITIAL_STATE | 48 |
| phase52p | H1 | 0 | Optimization terminated successfully | 183 |
| phase52p | H1 | 8 | Positive directional derivative for linesearch | 6 |
| phase52p | H1 | 9 | Iteration limit reached | 3 |
| phase52p | H2 | 0 | Optimization terminated successfully | 359 |
| phase52p | H2 | 4 | Inequality constraints incompatible | 1 |
| phase52p | H2 | 8 | Positive directional derivative for linesearch | 51 |
| phase52p | H2 | 9 | Iteration limit reached | 149 |
| phase52p | L2 | 0 | Optimization terminated successfully | 281 |
| phase52p | L2 | 4 | Inequality constraints incompatible | 1 |
| phase52p | L2 | 8 | Positive directional derivative for linesearch | 49 |
| phase52p | L2 | 9 | Iteration limit reached | 69 |
| phase52p | L2 | None | INFEASIBLE_FIXED_INITIAL_STATE | 8 |
| phase52p | LC | 0 | Optimization terminated successfully | 114 |
| phase52p | LC | 8 | Positive directional derivative for linesearch | 5 |
| phase52p | LC | 9 | Iteration limit reached | 1 |
| phase52p | SLW | 0 | Optimization terminated successfully | 846 |
| phase52p | SLW | 8 | Positive directional derivative for linesearch | 115 |
| phase52p | SLW | 9 | Iteration limit reached | 87 |

사건별 결과: [graph_selections.csv](../research/results/phase52ec/graph_selections.csv). 후보별 status·경로·재검증 결과: `research/results/phase52ec/graph/`.

변위는 선택된 원 후보의 B 이후 suffix를 B+7점으로 재표집한 기준과의 점별 거리(고정 B 포함8점)다. 1μm 이하 변경은 수치적으로 초기값 그대로인 해로 따로 세었다. `resampling_only_rescue`는 원 후보8개가 모두 꼬리 EC에 실패했지만 재표집 초기값이 통과한 경우, `optimized_rescue`는 그 집합에서1μm 넘게 수정한 해가 통과한 경우다. 이 분해는 결과 해석용이며 solver·채택 규칙은 바꾸지 않았다.

안전성은 저장된 **depth 지도상 2초 또는 끝점+제동 꼬리**에만 해당한다. unknown=free인 동결 EC 지도 규칙을 유지했으며 oracle 안전·전체 경로·목표 도착을 보장하지 않는다. 짧은 정지/회전만으로도 목적이 만족될 수 있어 실제 순변위5cm 이하 해를 함께 보고했다.
