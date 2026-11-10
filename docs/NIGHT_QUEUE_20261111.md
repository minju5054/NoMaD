# 20261111 밤샘 대기열 — READY_PENDING_USER

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


| priority | experiment | planned | smoke | prep | report |
|---|---|---|---|---|---|
| 1 | E1 | 36 | PASS | NIGHT_E1_20261111_PREP.md | NIGHT_E1_20261111_RESULTS.md |
| 2 | E2 | 48 | PASS | NIGHT_E2_20261111_PREP.md | NIGHT_E2_20261111_RESULTS.md |
| 3 | E3 | 36 | PASS | NIGHT_E3_20261111_PREP.md | NIGHT_E3_20261111_RESULTS.md |

6장면(SLW,LC,L2,H1,H2,H1-v2), seed225·226, 총120run. 실행 순서 E1→E2→E3. 순차 실행·기술 실패1회 재시도·6시간 이후 새run/재시도 금지·진행 중run 완료·완료된짝만 비교·미완료 표시·실험별 report/PNG/commit/push는 동결 그대로다.

대기열로그: `../artifacts/isaac6/night_queue_20261111_01.log`

재검증로그: `../artifacts/isaac6/night_queue_20261111_smoke_recheck_01.log`

원 실패로그: `../artifacts/isaac6/night_queue_20261111_smoke.log`

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_night20261111.queue --status`

사용자 실행용 nohup (미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/nomad-night-mpl /usr/bin/python3 -u -m nomad_night20261111.launch --queue-run > ../artifacts/isaac6/night_queue_20261111_01.log 2>&1 < /dev/null &`
