# 20261111 밤샘 대기열

**SKIPPED_ALL — 대기열 미시작, 주행0회.** E1/E2/E3 smoke가 공통 launcher의 provenance 기록에서 `nomad_night20261111/protocol.json`을 읽으려다 FileNotFoundError로 종료됐다. 등록된 파일은 `protocol_E1.json`, `protocol_E2.json`, `protocol_E3.json`이다. NoMaD worker와 Isaac은 시작되지 않았다. 사용자 지시대로 코드 수정·재시도 없이 각1회 실패를 보존했다. PASS 실험이 없어 nohup은 실행하지 않았다.

| priority | experiment | planned | smoke | prep | report |
|---|---|---|---|---|---|
| 1 | E1 | 36 | SKIPPED | NIGHT_E1_20261111_PREP.md | NIGHT_E1_20261111_RESULTS.md |
| 2 | E2 | 48 | SKIPPED | NIGHT_E2_20261111_PREP.md | NIGHT_E2_20261111_RESULTS.md |
| 3 | E3 | 36 | SKIPPED | NIGHT_E3_20261111_PREP.md | NIGHT_E3_20261111_RESULTS.md |

최신 확정6장면(SLW,LC,L2,H1,H2,H1-v2),seed225·226. 총120run. Smoke3회는본결과제외,실패실험은수정없이SKIPPED. 통과실험만순차실행한다. 대기열시작부터6시간경과시새run/재시도를금지하고진행중run만완료한다. 미완료짝은표시하되비교에서제외한다. 실험마다report·PNG·commit·push.

`--start`는nohup프로세스를정확히하나생성하고첫launcher PID의시작영수증을pipe로한번확인한뒤반환한다. 주행완료를기다리거나poll하지않는다. 재실행중복은pid/lock으로거부한다. 기존deadline은재개해도연장하지않는다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_night20261111.queue --status`

전체로그: `../artifacts/isaac6/night_queue_20261111_01.log`

Smoke로그: `../artifacts/isaac6/night_queue_20261111_smoke.log`

개별로그·상태: `../artifacts/isaac6/night_queue_20261111_01/{E1,E2,E3}/` (smoke는`smoke/{E1,E2,E3}/`).

시작명령(내부nohup1회): `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m nomad_night20261111.queue --start`
