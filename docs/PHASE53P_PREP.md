# Phase53-P 준비

| status | runs | conditions | seeds | methods | protocol_sha256 |
|---|---|---|---|---|---|
| FROZEN; MAIN_NOT_RUN | 40 | D075/D150 | 221,222 | CUT/GRAPH-HO | 1cc31fda1f431072cb8687d9ea7b1c1e70e628b05f0346067a6199fdd558f6eb |

| method | definition |
|---|---|
| CUT | Phase47 OURS-DETOUR+HMM native FRESHEST-SAFE handoff; original1s expiry; only common EC tail changed |
| GRAPH-HO | Same CUT EC selection and fallback; final chunk installation synchronously reconstructs selected native8-waypoint path with unmodified Phase17/18 ClearanceGraph; current actual pose and actual command; accept only solver feasible/certificate AND tail EC;otherwise identical CUT path |

| item | value |
|---|---|
| frozen | Phase47 HMM/official declared arrival,geometry/jitter/controller/SAFE/filter/RECOVER; no R2/R3;original1s receipt-age expiry. No Phase52 HOLD or predictedB dispatch. |
| tail | At earlier path endpoint/2s request frozen stop_command until v=0 at72Hz;omega also frozen stop_command. Swept depth footprint>=.025. Periodic continuation respects original9Hz phase (36tick checks). |
| graph | Direct nomad_phase17.graph.ClearanceGraph (Phase18 same implementation), native8SE2poses/24variables, SLSQP maxiter100 ftol1e-8 analytic Jacobians; no factor/weight/option changes;previous prior last actually installed acceptedGraph; no new init or resampling. |
| heading_curvature | Start heading SOFT sigma10deg at interpolated entry E; boundary position sigma.01m. Hard boundary tangent-circle curvature kappa_before=w/v plus Menger abs<=8. Not hard fixed B pose. v=0 undefined curvature and abs(w/v)>8 retain frozen initialization rejection and CUT fallback. |
| synchronous | One external system-Python persistent RPC, caller waits synchronously at installation actual pose; no predicted pose or delayed result reuse. RPC30s watchdog is technical error,not solver tuning. Solver compute time and wholeRPC logged. |
| install_scope | Final EC-selected native CUT chunk installation,including alternative SAFE candidates selected by unchanged fallback. On periodic replacement refine the corresponding native candidate rather than recursively refine Graph XY. EC-tail rechecks Graph with latest map;failed/no-convergence uses the same already-passed CUT candidate. |
| success | Frozen official declared stop, distance<=.5m and no collision;wrong stop>.5m; timeout without declaration unchanged. |
| heading_discontinuity | At actual installation B: wrapped direction difference between previous and installed XY suffixes projected at B,first .05m; p50/p95 degrees;undefined endpoint directions excluded/count recorded. |
| time | Actual72Hz /v/<.01 stop duration; command-state intervals include ALIGN_ROTATE;arrival median only successes. |
| graph_rate | Actually installed Graph / synchronous Graph attempts;also attempts,installations,reasons,solve p50/p95. No Graph in CUT. |
| historical | Same seed published Phase47/51/52 aggregates reused without extra analysis. Different days;Phase51 WIDE geometry differs;Phase52 HOLD differs. Historical missing fields remain empty,not zero-filled. |
| execution | 40main serial,one technical retry,global lock,resume completed runs,storagev2,cache cleanup,30GB reserve,automatic systemPython report+commit+push. One LC smoke only;no main in preparation. |

LC GRAPH-HO seed95 smoke 1회만 허용(본 결과 제외). reference 최단 LC/H1 동률 중 LC 선택. 추가 분석·오프라인 재풀이 없음.

| scene | reference_m |
|---|---|
| SLW | 6.2971 |
| LC | 5.6934 |
| L2 | ~7.7 (straight reference) |
| H1 | 5.6934 |
| H2 | ~7.7 (straight reference) |

| passed | tests | dry_run | main_started | offline_resolves | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|
| True | 11 | 40 | 0 | 0 | 1cc31fda1f431072cb8687d9ea7b1c1e70e628b05f0346067a6199fdd558f6eb | 1132937232384 |

| technical_validation | graph_attempts | graph_applied | graph_reasons | ec_checks | ec_rejects | new_timeout_count |
|---|---|---|---|---|---|---|
| PASS | 35 | 32 | {'INITIALIZATION_REJECTED': 2, 'ACCEPTED': 32, 'SOLVER_OR_CERTIFICATE_REJECT': 1} | 135 | 0 | 1 |

smoke는 기술 audit만 평가한다. 수치 성과로 method/parameter를 바꾸지 않는다. 본 실행은 사용자가 수행한다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase53p.campaign --status`

로그: `../artifacts/isaac6/phase53p_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase53p.campaign > ../artifacts/isaac6/phase53p_01.log 2>&1 < /dev/null &`
