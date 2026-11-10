# E3_D150_R3 준비

## Launcher 배관 수정 후 재검증 — 2026-11-11

사용자가 승인한 변경은 launcher가 실험별 protocol_E1/E2/E3.json을 선택하도록 하는 배관 수정이다. 원 protocol의 바이트와 source hash 항목은 그대로 보존하고, launcher_revision.json에 원/수정 launcher hash와 protocol 전후 hash를 추가 기록했다. 기존 verifier의 모든 검사를 유지하면서 이 한 파일의 승인된 hash만 별도로 검증한다. 실제 launch 경로로 provenance를 기록하고 첫 NoMaD 프로세스 시작 직전에 멈추는 dry-run을 세 실험 모두 통과했다.

기존 smoke의 시뮬레이터 시작 전 실패 자료는 보존했다. 사용자 승인으로 각1회 재검증했으며 세 audit 모두 PASS, 추가 수정·재시도0회다. 방법·factor·트리거·장면·seed·순서·지표·protocol 내용은 변경하지 않았다. 재검증은 smoke/{E1,E2,E3}/recheck_01/에 저장했다.

| experiment | status | technical_validation | exit_code | ec_checks | graph_attempts | graph_applied | new_timeout_count |
|---|---|---|---|---|---|---|---|
| E1 | PASS | PASS | 0 | 119 | 0 | 0 | 2 |
| E2 | PASS | PASS | 0 | 106 | 21 | 19 | 0 |
| E3 | PASS | PASS | 0 | 117 | 0 | 0 | 28 |

| experiment | before | after | unchanged |
|---|---|---|---|
| E1 | 46eb5be0e6a0ee2c2ef39d76b2fa779f6e55b36d2c14e3410da763ba969dde12 | 46eb5be0e6a0ee2c2ef39d76b2fa779f6e55b36d2c14e3410da763ba969dde12 | True |
| E2 | 28bffd0bc277174fd63eda89acea342088fb787789e7095c41c7637291ef50c0 | 28bffd0bc277174fd63eda89acea342088fb787789e7095c41c7637291ef50c0 | True |
| E3 | 123ba3c9c7fd2208f21b9070f92fcc91f418d932d89f0a476856f254ed5ee4ae | 123ba3c9c7fd2208f21b9070f92fcc91f418d932d89f0a476856f254ed5ee4ae | True |

본 대기열은 아직 실행하지 않았다. 원 queue.py와 report.py를 수정하지 않고, 승인된 launcher hash 검증을 공유하는 `launch --queue-run`/`launch --report` 배관으로 기존 함수를 그대로 호출한다. 아래 명령이 현재 실행용이며 이전 `queue --start` 명령 대신 사용한다. 이번 smoke 재검증은 사용자의 명시적 승인 예외이며 원 프로토콜의 main 재시도/6시간 제한은 그대로다.


| experiment | status | runs | scenes | seeds | protocol_sha256 |
|---|---|---|---|---|---|
| E3 | FROZEN | 36 | SLW,LC,L2,H1,H2,H1-v2 | 225,226 | 123ba3c9c7fd2208f21b9070f92fcc91f418d932d89f0a476856f254ed5ee4ae |

최신 사용자 확정: 초기5장면/기존 seed 설계를 대체해 모든 실험을6장면×신규 seed225·226으로 고정. E1·E3는각12블록/36run,E2는각지연12블록/총48run. 방법 순서는 블록 내부에서 seed20261117로 무작위화. H1-v2는65556be;기존5장면과Topomap 불변. 새 seed jitter는 동결Phase38 알고리즘으로 생성해 세 실험/방법이 공유한다.

| method | definition |
|---|---|
| CUT | Frozen Phase53 CUT,1s expiry,HMM,official stop,EC braking tail |
| GRAPH-HO | Frozen Phase53 GRAPH-HO,1s expiry,HMM,official stop,EC braking tail |
| OURS-R3 | Frozen Phase38 OURS R2+R3/triggers/handover/RECOVER restored on Phase47 HMM;only EC predicate changed to registered braking tail;1s expiry |

| item | value |
|---|---|
| primary | box passage;exact two-sided McNemar OURS-R3 vs CUT and vs GRAPH-HO |
| pairing | same scene,seed,both completed technical PASS;static SLW/LC have no box and are N/A;12run blocks,8box blocks |
| secondary | spawn-to-passage time only both pass;goal,wrong stop,collision(all must be0) |
| candidate | OURS-R3 only-pass pairs minus CUT only-pass pairs>=3;report this rule and collision-free condition separately;never hide safety failures |

| enabled | maximum_attempts | scene | method | index | reason |
|---|---|---|---|---|---|
| True | 1 | LC_D150 | OURS-R3 | 95 | Shortest reference LC5.693m,tied with H1/H1-v2;newest code method;technical audit only |

| passed | tests | dry_run | simulations_started | protocol_sha256 | free_bytes |
|---|---|---|---|---|---|
| True | 9 | 36 | 0 | 123ba3c9c7fd2208f21b9070f92fcc91f418d932d89f0a476856f254ed5ee4ae | 1129865801728 |

| experiment | status | selection | key | reason | output | attempts | simulator_started | protocol_sha256 | launcher_sha256 | technical_validation | exit_code | smoke_excluded | main_started | ec_checks | graph_attempts | graph_applied | new_timeout_count | previous_smoke_preserved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E3 | PASS | PASS | LC_D150_095_OURS-R3 | AUDIT_PASS | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/night_queue_20261111_01/smoke/E3/recheck_01/main/LC_D150_095_OURS-R3/attempt1 | 1 | True | 123ba3c9c7fd2208f21b9070f92fcc91f418d932d89f0a476856f254ed5ee4ae | 14445bf73bbfd3b16662cca56fff8ed7a122cb4dd3b2e71b687e46e496d3d24a | PASS | 0 | True | False | 117 | 0 | 0 | 28 | /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/night_queue_20261111_01/smoke/E3/main/LC_D150_095_OURS-R3/attempt1 |

PREP·코드 commit/push 후 등록 smoke1회만 실행한다. audit 실패 시 수정·재시도하지 않고 SKIPPED. PASS 실험만 E1→E2→E3 단일 대기열. 총6시간 종료선 이후에는 다음run/재시도를 시작하지 않고 진행 중run만 마친다. 저장v2·portable/cache/pycache정리·30GB 여유·기술실패1회재시도. 실험 종료/시간제한 시 완료된짝만 report하고 미완료표시,자동commit/push.

OURS-R3라는 이름에도 R2와R3를 모두 사용한다(요청정의). 상자 통과 검정은상자있는8블록,목표도착/충돌은전체12블록. statics의상자통과를실패로대체하지 않는다.
