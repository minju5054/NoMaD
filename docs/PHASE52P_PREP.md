# Phase52-P 준비

| status | runs | methods | conditions | seeds | scenes |
|---|---|---|---|---|---|
| FROZEN_PROTOCOL / AUDIT_REPAIRED / RESUME_READY | 40 | CUT-HOLD / GRAPH-REC | D075 / D150 | 221,222 | SLW,LC,L2,H1,H2 |

| item | value |
|---|---|
| solver | Phase35 graph_pool R2 branch = nomad_phase20.repair.RepairGraphR2 + Phase19R.initialize |
| points | 8 |
| variables_xy | 14 |
| maxiter | 100 |
| ftol | 1e-08 |
| workers | 4 |
| prior_sigma_m | 0.1 |
| smoothness_sigma_m | 0.02 |
| heading_sigma_rad | 0.5236 |
| safety_m | 0.025 |
| maximum_abs_curvature_m_inv | 8 |
| trust_region_m | 0.75 |
| source_constraints_and_certificate | inherited unchanged,including NEGATIVE_DEPTH_AT_B and SHORT_REMAINING |
| old_factor | 0.5 sum_i w_i //p_i-old(s_i)//²;w=max(0,1-s_i/0.5);s_i fixed by this initialization cumulative arclength;no added sigma |
| old_scope | previous installation before immediate CUT replacement;project predicted B onto old path;use only available suffix up to0.5m;no extrapolated endpoint weight |
| b | Frozen Phase40-P schedule.predict(current CUT controller,state,command):apply_tick=ceil((dispatch_tick+54)/8)*8;dispatch after current tick control |
| apply | Only that tick;actual pose/current velocity/latest EC map;lowest objective among all R2-accepted and EC-passing candidates,tie sample index |
| superseded | Any newer FRESH before or at target tick discards old job. Late/missing/EC failure keeps CUT path;no Graph wait stop |
| recovery | Phase47 recovery unchanged;FRESH received during active recovery retains original deferred handling;Graph cannot replace during recovery |
| queue | One4-process broker,per-FRESH FIFO transport;late jobs logged/discarded without extra navigation attempts |
| map | Same latest base snapshot as EC at dispatch;latest map again at application;no strict R3 map,no oracle |
| waypoint_expiry | False |
| keep_remaining_minimum_m | — |
| periodic_ec_ticks | 36 |
| exhausted | Before STOP on unavailable/rejected fresh candidates,continue active follower only if latest continuation EC passes,including suffix shorter0.25m |
| terminal | Existing path endpoint,official declared arrival,run90s timeout and evaluation collision stops remain;RECOVER remains last resort |
| physical | Frozen C0-NA PP/SP,90degree rotation policy,v<=.3,w<=.4,a<=.5 unchanged |

| passed | tests | dry_run | simulations_started | new_nomad_inferences | renders | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|---|
| True | 13 | 40 | 0 | 0 | 0 | 57838e8042c9d156c728313a61432c2e3eccb000530f20ef654b2045978a57c4 | 1136205783040 |

[Phase51-P WIDE 저장 후보 분석](PHASE51P_WIDE_ANALYSIS.md)

## 시작 대기 audit 수정 및 저장 attempt1 복구

2026-11-10T17:04:26+09:00: 최초 chunk 이전 `status=missing`, `valid=false`, id<0, age=null인 `WAYPOINT_TIMEOUT` 출처만 시작 대기로 허용한다. 최초 chunk 수신 이후 같은 출처 또는 어느 시점의 `new_timeout`은 여전히 기술 실패다. `initial_wait_s`는 첫 chunk가 있는 제어 tick까지의 대기이며, 실제 수신 latch 시각은 `first_chunk_received_s`로 별도 기록한다. 원본 controller/주행 로그는 수정하지 않았다.

요청한 6개와 추가 확인된 H1 GRAPH-REC 1개를 동일한 결과 무관 규칙으로 복구했다. **attempt1 exit0·summary 완료·이번 audit 오류만 존재·수정 audit PASS**를 모두 만족해야 선택한다. attempt2는 6개 완료본과 1개 중단본 모두 사용하지 않고 `attempt_metrics`에 제외 사유를 기록했다. 원래 실패 metrics와 state는 run-root의 `audit_recovery/STARTUP_MISSING_AUDIT_V1/before/` 및 저장소 `research/results/phase52p/audit_fix/original_metadata.json`에 보존했다.

| run | attempt | audit | initial_wait_s | first_chunk_received_s | startup_missing_rows | new_timeout | post_chunk_timeout | reason | attempt2 |
|---|---|---|---|---|---|---|---|---|---|
| SLW_D075_221_CUT-HOLD | 1 | PASS | 2.8889 | 2.8333 | 26 | 0 | 0 | exit0 + summary complete + startup audit error only | EXCLUDED / preserved |
| SLW_D075_221_GRAPH-REC | 1 | PASS | 2.8889 | 2.8333 | 26 | 0 | 0 | exit0 + summary complete + startup audit error only | EXCLUDED / preserved |
| LC_D075_221_GRAPH-REC | 1 | PASS | 2.8889 | 2.8333 | 26 | 0 | 0 | exit0 + summary complete + startup audit error only | EXCLUDED / preserved |
| LC_D075_221_CUT-HOLD | 1 | PASS | 2.8889 | 2.8472 | 26 | 0 | 0 | exit0 + summary complete + startup audit error only | EXCLUDED / preserved |
| L2_D075_221_CUT-HOLD | 1 | PASS | 2.8889 | 2.8333 | 26 | 0 | 0 | exit0 + summary complete + startup audit error only | EXCLUDED / preserved |
| L2_D075_221_GRAPH-REC | 1 | PASS | 2.8889 | 2.8472 | 26 | 0 | 0 | exit0 + summary complete + startup audit error only | EXCLUDED / preserved |
| H1_D075_221_GRAPH-REC | 1 | PASS | 2.8889 | 2.8611 | 26 | 0 | 0 | exit0 + summary complete + startup audit error only | EXCLUDED / preserved |

| tests_passed | reaudited_attempt1 | excluded_attempt2 | remaining_combinations | next_key | simulations_started | protocol_sha256 | audit_revision_sha256 | raw_files_unchanged | H1_CUT_HOLD_pending | original_protocol_and_runtime_preserved |
|---|---|---|---|---|---|---|---|---|---|---|
| 12 | 7 | 7 | 33 | H1_D075_221_CUT-HOLD | 0 | 57838e8042c9d156c728313a61432c2e3eccb000530f20ef654b2045978a57c4 | fe15bfafb4bf96a5b7f997652b1e05a4d99e448decce1cd1779496030079fb09 | 11412 | True | True |

재개하면 공통 campaign lock 안에서 이 7개 attempt1의 audit을 먼저 다시 실행한다. 하나라도 실패하면 `AUDIT_GATE_FAILED`로 멈추며 새 주행을 시작하지 않는다. 통과하면 이미 복구된 7개를 건너뛰고 **나머지 33개를 원래 순서**로 실행한다. 첫 대상은 `H1_D075_221_CUT-HOLD`다. 새 시뮬레이션 smoke는 없다.

실험 `protocol.json`과 run-root `plan.json`은 그대로다. 방법·solver·controller·장면·seed·순서 변경 없이 audit/report/resume 수정만 `audit_revision.json`에 별도 hash로 기록했다. 이전 전체 로그를 보존하도록 재개 명령은 `>>`로 덧붙인다.

## Closure 보존 및 실제 재개 dry-run 검증

2026-11-10T17:30:20+09:00: 재개 초기화가 `jobs`를 closure로 바꾸는데 복제 시 closure를 누락해 audit gate 진입 전에 Exit1이 났다. `resume.planned()`와 `campaign.jobs()` 모두 `FunctionType(..., __name__, __defaults__, __closure__)`로 복제한다. 같은 누락이 있는 과거 wrapper를 경유하지 않고 현재 실제 Phase26 `jobs` binding을 사용한다. 재개 setup 내부 복제에도 defaults/closure를 보존한다. 이전 phase 파일은 수정하지 않았다.

기존 dry-run은 closure 재바인딩 전에 반환했으므로 오류를 놓쳤다. 이제 `--dry-run`도 실제 campaign setup과 공통 lock을 거쳐 보존 run audit gate까지 실행하고, 주행 시작 전에 반환한다. mock 없이 `planned(RUN_ROOT)` 및 실제 CLI로 검증했다. 복구된 7개·attempt2 제외 기록·원 protocol·plan·주행 코드는 바꾸지 않았다.

| 검증 | 결과 |
|---|---|
| 테스트 | 14 PASS |
| 실제 plan / 복구 key | 40 / 7 |
| 실제 재바인딩 jobs closure cell | 1 |
| 실제 run-root audit gate | 7/7 PASS |
| 남은 조합 / 다음 실행 | 33 / H1_D075_221_CUT-HOLD |
| 보존 원본 파일 | 11,412개 변경 없음 |
| 시뮬레이션 | 0회 |
| 원 protocol SHA256 | 57838e8042c9d156c728313a61432c2e3eccb000530f20ef654b2045978a57c4 |
| 현재 audit revision SHA256 | 8777f1e1fdc492c58c1338111e05855b37a8c2439660d76ba07e55d81f7e0172 |

검증 기록: `research/results/phase52p/closure_fix/`. 재개 명령은 아래와 같으며 실행하지 않았다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase52p.campaign --status`

재개 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase52p.campaign >> ../artifacts/isaac6/phase52p_01.log 2>&1 < /dev/null &`
