# E3_D150_R3 준비

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

| status |
|---|
| SMOKE_NOT_RUN |

PREP·코드 commit/push 후 등록 smoke1회만 실행한다. audit 실패 시 수정·재시도하지 않고 SKIPPED. PASS 실험만 E1→E2→E3 단일 대기열. 총6시간 종료선 이후에는 다음run/재시도를 시작하지 않고 진행 중run만 마친다. 저장v2·portable/cache/pycache정리·30GB 여유·기술실패1회재시도. 실험 종료/시간제한 시 완료된짝만 report하고 미완료표시,자동commit/push.

OURS-R3라는 이름에도 R2와R3를 모두 사용한다(요청정의). 상자 통과 검정은상자있는8블록,목표도착/충돌은전체12블록. statics의상자통과를실패로대체하지 않는다.
