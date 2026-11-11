# Phase57-P 준비

| status | runs | scenes | seeds | delay_s | protocol_sha256 |
|---|---|---|---|---|---|
| FROZEN; NOT_RUN | 18 | H1-v2 / SLW / H2 | 227,228 | 0.75 | 8a7c1e827306abda407d386a9c934bccee400a261700b3d6963f9f284886dca0 |

| method | definition |
|---|---|
| NOMAD_RAW | Phase47-C NOMAD_RAW exactly: sample0/world anchor,original argmin localization,PP/SP with frozen >90degree alignment,1s expiry,official declared arrival. No depth/EC/HMM/recovery; no new endpoint latch. |
| MIN | Phase53 CUT minus depth prefilter/RECOVER_ROTATE/ALIGN/0.1tier. All8world candidates ordered by B-projected remaining length,index tie. Full-speed tailEC at install and36ticks. All reject=>STOP_WAIT until nextchunk,noKEEP. HMM,1sexpiry,officialarrival. ENDPOINT latch resets only on actual new path. |
| MIN+G18 | MIN plus Phase53 synchronous ClearanceGraph wiring. Reuse nightE2 HoldClearanceGraph: only boundary curvature equality omitted when abs(v)<.02 or abs(w/v)>8. Remaining factors/weights/options/certificate unchanged. Graph on final EC-approved MIN candidate;tailEC accepts Graph otherwise same MIN path. |

MIN 두 방법은 depth 선별·회복·정렬·0.1m/s 후보 단계를 끈다. 모든 후보는 관측 pose에서 world 고정 후 B 이후 잔여 길이 순서로 EC 검사한다. 전부 거절되면 STOP_WAIT이며 기존 경로 KEEP 없이 다음 chunk를 기다린다.

ENDPOINT는 새 경로가 실제 설치될 때만 해제한다. 매 제어 tick 동결 stop_command로 감속해 정지를 유지한다. 설치/주기 EC도 동일한 정렬 OFF·ENDPOINT latch 실행기를 사용하고, 제동꼬리 적분과 안전 하한은 동결이다. 1s 만료는 그대로 유지한다.

MIN+G18은 Phase53 GRAPH-HO 배관과 E2의 조건부 시작 경계 곡률 제외 class/worker를 그대로 import한다. 원 MIN 경로가 EC를 통과한 뒤 Graph를 적용하며, Graph 실패/EC 거절은 그 MIN 경로로 fallback한다. solver 실행이나 수치 튜닝은 하지 않았다.

NOMAD_RAW는 Phase47-C 정의 그대로이므로 원래 argmin 위치추정/sample0/90° 정렬이며 HMM·EC·새 latch를 적용하지 않는다. 공식 도착 판정과 1s 만료는 세 방법 모두 사용한다.

| item | value |
|---|---|
| switches | Private function bindings/MRO bridges;no frozen files modified. candidate safe=True is inherited eligibility only,never depth clearance;selection records depth_filter_disabled. |
| controller | Same PP/SP control and limits;NoAlignment replace_path computes frozen SP then trigger_S=False,modeGO. Completion latched and actual frozen stop_command repeats to rest,until any new path installation. Numeric threshold field90 retained for inherited audit;alignment_disabled flag and absenceofALIGN prove switch. |
| EC | Frozen Phase53 tail72Hz integration with same MIN controller(copy for periodic continuation),not original aligning controller. Endpoint/2s then stop_command to rest;>=.025m. Fullspeed candidates only;never cap.1. Reject applies following9Hztick as frozen. |
| graph | Same Phase53 job construction,prior,synchronous RPC,solver settings. Existing E2 graph class/worker directly imported. No new solver. Original MIN candidate is already tailEC-passed before optionalGraph;allMINcandidatesreject=>STOP. |
| scene | H1-v2 fixed y1.10 box/arcspawn,SLW andH2 frozengeometry/topomap. H2 newseed jitter uses Phase38 registered_jitter;all3methods shareplacement. H1-v2 fixedbox overrides H1jitter. |
| order | scene then seed;three methods shuffled perblock with random.Random(20261117),18runs. |
| outputs | Frozen arrival success<=.5m/no collision,wrongstop,timeout,boxpassage,arrival/stoppedtime,Graph adopted/attempted;one150dpi saved-log topdown eachrun. Incomplete results marked;technicalfailure empty panel. |
| prepared | No simulations,no smoke,no recorded-input solve. 18configs/actuallauncherargument boundary/JSON/controller switches/fallback/report plumbing only. |

| passed | tests | dry_run | simulations_started | solver_runs | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|
| True | 10 | 18 | 0 | 0 | 8a7c1e827306abda407d386a9c934bccee400a261700b3d6963f9f284886dca0 | 1116600676352 |

본 실행 종료 후 docs/PHASE57P_RESULTS.md 및 research/results/phase57p/에 표와 run별 top-down PNG를 생성하고 자동 commit·push한다. 기술 실패 1회 재시도, run별 cache 정리, 디스크 30GB 미만 중단, 동일 root 재개.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase57p.campaign --status`

로그: `../artifacts/isaac6/phase57p_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase57p.campaign > ../artifacts/isaac6/phase57p_01.log 2>&1 < /dev/null &`
