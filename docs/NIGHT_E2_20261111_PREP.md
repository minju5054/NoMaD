# Phase54-P 준비

| experiment | status | runs | scenes | seeds | protocol_sha256 |
|---|---|---|---|---|---|
| E2 | FROZEN | 48 | SLW,LC,L2,H1,H2,H1-v2 | 225,226 | 28bffd0bc277174fd63eda89acea342088fb787789e7095c41c7637291ef50c0 |

최신 사용자 확정: 초기5장면/기존 seed 설계를 대체해 모든 실험을6장면×신규 seed225·226으로 고정. E1·E3는각12블록/36run,E2는각지연12블록/총48run. 방법 순서는 블록 내부에서 seed20261117로 무작위화. H1-v2는65556be;기존5장면과Topomap 불변. 새 seed jitter는 동결Phase38 알고리즘으로 생성해 세 실험/방법이 공유한다.

| method | definition |
|---|---|
| CUT-HOLD | Phase53 CUT + receipt does not expire;keep current path to endpoint if latest periodic EC-tail passes,including<.25m remainder |
| GRAPH-HOLD | CUT-HOLD + Phase53 Graph-HO;only start boundary curvature hard equality omitted when abs(v)<.02 or abs(w/v)>8;all costs,inequalities,certificate,solver options unchanged |

| item | value |
|---|---|
| primary | D15012pairs:graph adoption,paired ALIGN_ROTATE and both-arrival time deltas,goal descriptive noninferiority |
| noninferiority | GRAPH-HOLD goals minus CUT-HOLD goals>=-1;pilot descriptive rule,NOT statistical noninferiority test;report discordant pairs |
| margin_runs | -1 |
| expected_pairs_per_condition | 12 |
| delay_comparison | D150 vs D075 differences,matched complete4-run blocks;no imputation |

| enabled | maximum_attempts | scene | method | index | reason |
|---|---|---|---|---|---|
| True | 1 | LC_D150 | GRAPH-HOLD | 95 | Shortest reference LC5.693m,tied with H1/H1-v2;newest code method;technical audit only |

| passed | tests | dry_run | simulations_started | protocol_sha256 | free_bytes |
|---|---|---|---|---|---|
| True | 9 | 48 | 0 | 28bffd0bc277174fd63eda89acea342088fb787789e7095c41c7637291ef50c0 | 1129865801728 |

| status | reason | protocol_sha256 | key | output | attempts | original_reason | failure_stage | simulations_started | launcher_log | launcher_log_sha256 | code_repaired | retried |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SKIPPED | FileNotFoundError: [Errno 2] No such file or directory: '/home/gpuadmin/Workspace/NoMaD/visualnav-transformer/research/nomad_night20261111/protocol.json' | 28bffd0bc277174fd63eda89acea342088fb787789e7095c41c7637291ef50c0 | LC_D150_095_GRAPH-HOLD | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/night_queue_20261111_01/smoke/E2/main/LC_D150_095_GRAPH-HOLD/attempt1 | 1 | Launcher failure; preserved; no source repair during this queue | PROVENANCE_BEFORE_WORKER_AND_SIMULATOR | 0 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/night_queue_20261111_01/smoke/E2/logs/LC_D150_095_GRAPH-HOLD_1.log | d36a37c18b07023deedda85c73860f6b2060486b6ab657505e2605f54de7fba1 | False | False |

PREP·코드 commit/push 후 등록 smoke1회만 실행한다. audit 실패 시 수정·재시도하지 않고 SKIPPED. PASS 실험만 E1→E2→E3 단일 대기열. 총6시간 종료선 이후에는 다음run/재시도를 시작하지 않고 진행 중run만 마친다. 저장v2·portable/cache/pycache정리·30GB 여유·기술실패1회재시도. 실험 종료/시간제한 시 완료된짝만 report하고 미완료표시,자동commit/push.

E2 boundary equality 제외는 낮은v/과대w/v에서만 적용한다. 기존 초기화의 해당 곡률정의 사전거부도 그 경우에만 건너뛰며, 시작heading 소프트항·Menger hard·진전/여유/이전prior·solver옵션은 동일하다. HOLD에서 활성경로가EC-tail통과면 짧은잔여도 유지;새chunk우선설치·정렬·RECOVER는그대로다.
