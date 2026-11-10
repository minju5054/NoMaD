# Phase52-P 준비

| status | runs | methods | conditions | seeds | scenes |
|---|---|---|---|---|---|
| FROZEN_PREPARED_NOT_RUN | 40 | CUT-HOLD / GRAPH-REC | D075 / D150 | 221,222 | SLW,LC,L2,H1,H2 |

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

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase52p.campaign --status`

실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase52p.campaign > ../artifacts/isaac6/phase52p_01.log 2>&1 < /dev/null &`
