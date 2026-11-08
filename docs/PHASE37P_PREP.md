# Phase37-P — PROV 라이브 파일럿 준비

준비 완료. **본 주행·smoke·시뮬레이션·추론 실행 0회**. 저장 run 재생, 단위테스트 23개, 20조합 dry-run 및 launcher 인자 검증이 통과했다. 실제 주행은 사용자가 아래 명령으로 시작한다.

## 사용자 결정과 동결

2026-11-08: Phase37-B의 **PROV_NOT_ESTABLISHED_MISSING_HISTORY**와 기존 결과를 보존한다. 확인된 이력만 보면 BOX **42/45(93.33%)**, 비-BOX **116→59(49.14% 감소)**다. 누락된 발행 지도 때문에 전체 이력 기준 오프라인 판정은 불가능하므로, 사용자가 발행마다 free 증거를 추적하는 주행 파일럿으로 확인하기로 결정했다. 이를 사전등록 경위/이탈로 기록했으며 OFFLINE_OK로 바꾸지 않았다.

Protocol: `research/nomad_phase37p/protocol.json`, **FROZEN**. SHA256 `a455d695db4a0e3a0c9b0fc1038751782feefc72e21c14bd11996aeff7955811`. 기존 동결/참조 소스 342개와 새 준비 소스 13개의 SHA256, 장면/Topomap/checkpoint hash를 기록했다. 실행 시 모두 재검증한다.

## 방법과 유일한 변경

| 방법 | 실행·지도·Graph | 트리거 B |
|---|---|---|
| OURS | Phase35 OURS 동결 그대로 | 기존 PersistentNoProgress |
| OURS+PROV | 동일 | 기존 component 집계 셀에 확인 free 플래그만 추가 |

라이브 발행 지도마다 `last_free_tick == frame_tick AND observed AND NOT occupied`가 성립하고 최초 occupied 이전인 칸의 플래그를 켠다. 최초 occupied 이전은 `first_occupied_tick` 미설정 또는 `frame_tick < first_occupied_tick`이다. 한 번 확인된 플래그는 유지하고, 처음부터 occupied였던 칸이 나중에 비어도 과거 증거를 소급 생성하지 않는다. 판정은 ray 갱신 직후가 아니라 **shadow 처리를 마친 최종 발행 지도**를 사용한다.

매 발행 때 별도 지도 스레드에서 플래그를 갱신한다. 제어 루프가 읽지 않은 frame과 디스크에 생략된 frame도 포함된다. 기존 occupied/observed/SDF/last-free 계산은 건드리지 않으며, 불변 snapshot에 플래그와 최초 확인 tick을 복사한다. 저장 v2는 values를 생략하고 `prov_confirmed_free`, `prov_first_confirmed_free_tick`을 추가 보존한다. 복원은 STORAGE_RETROFIT 로더를 재사용한다.

B 집계는 기존 free→occupied 후보 중 위 플래그가 참인 셀만 4연결·최소5칸 규칙으로 센다. ID/t_new/u_ref는 기존 정의를 유지한다. 트리거 A, 유지·넘김·종료, R2/R3, EC, fallback, RECOVER_ROTATE, PP/SP 및90° 초과 정렬은 변경하지 않는다. **10초 u_ref 보정·TOPO-H는 적용하지 않는다.** Oracle은 사후 분류와 그림에만 사용한다.

## 저장 run 재생과 검증

| case | published_frames | replayed_saved_frames | matched_decisions | live_triggers | offline_triggers | cell_timestamp_comparisons |
|---|---|---|---|---|---|---|
| 32_H1_201 | 110 | 110 | 152 | 0 | 0 | 1002100 |
| 35_L2_212 | 357 | 232 | 164 | 10 | 10 | 3289528 |

전체 보존 run과 compact 저장 run을 비교했다. 발동이 있는 L2 run을 포함해 미발동/발동 양쪽을 검증했다. 각 보존 frame에서 기존 지도 배열 불변성, 관련 셀의 최초 확인 tick, 공통 관측 시점의 B 발동·component ID·t_new·u_ref가 Phase37-B 재생과 일치했다. 누락 frame을 이전 지도로 대체하지 않았다. 이 검증은 동일한 **보존 지도 스트림**에 대한 구현 일치 증거이며 누락된 원래 이력을 복원하거나 오프라인 라벨을 뒤집는 검증은 아니다.

테스트에는 최초 occupied 전후, observed=False/shadow·다른 frame tick 제외, 발행 간 제어 호출 없이 누적, snapshot 불변성, v2 저장/복원, 필터 후5칸, B만 변경·기존 유지/종료 불변, cooldown/busy, 표준 json.dumps, 판정 경계, 가짜20run report, 기술 실패 그림 생략/한쪽 데이터 처리도 포함했다. venv에서 launcher/campaign import 시 SciPy를 가져오지 않는다. 수치 모듈은 기존 SimulationApp 초기화 이후에만 import한다. 시뮬레이터 프로세스를 만들기 전에 중단하는 launcher 인자 검증20건, 고유 짧은 socket40개(재시도 포함,<100byte)를 확인했다.

## 실행 계획

SLW·LC·L2·H1·H2 × seed215,216 × 두 방법 =20회. seed→scene 블록 안 순서만 seed20261110으로 무작위화했다.

| scene | index | methods |
|---|---|---|
| SLW | 215 | ['OURS', 'OURS+PROV'] |
| LC | 215 | ['OURS+PROV', 'OURS'] |
| L2 | 215 | ['OURS', 'OURS+PROV'] |
| H1 | 215 | ['OURS', 'OURS+PROV'] |
| H2 | 215 | ['OURS', 'OURS+PROV'] |
| SLW | 216 | ['OURS+PROV', 'OURS'] |
| LC | 216 | ['OURS', 'OURS+PROV'] |
| L2 | 216 | ['OURS+PROV', 'OURS'] |
| H1 | 216 | ['OURS', 'OURS+PROV'] |
| H2 | 216 | ['OURS', 'OURS+PROV'] |

동시 실행은 금지하고 기존 전역 잠금·재개 구조를 사용한다. 기술 실패만 같은 seed로1회 재시도하고 attempt를 보존한다. run 종료 후 portable/cache·pycache를 정리한다. 매 attempt 전에 여유가30GB 미만이면 중단한다. 준비 시 디스크 여유 **1180.89GB**. 아직 run-root를 만들지 않았다.

## 사전 판정과 자동 report

10개 scene×seed 짝에서 **PROMISING = PROV 도착>OURS 도착 AND PROV 충돌≤OURS 충돌**, 그 외 NOT_PROMISING. 기술 실패로 증거가 불완전하면 evidence_valid=false로 표시하고 누락 충돌을0으로 대체하지 않는다. 도착시간은 판정에 사용하지 않는다.

campaign 완료 후 `/usr/bin/python3`·`PYTHONPATH=research`로 report를 자동 실행해 `docs/PHASE37P_RESULTS.md`, `research/results/phase37p/`의 runs/decision/summary/triggers/paired/failures/technical_failures 및 그림을 생성하고 commit·push한다. 장면별 A/B 트리거와 Phase37 oracle4분류, APPLIED 우회 수, Phase31-D 실패 원인, 둘 다 도착한 짝의 PROV−OURS 도착시간을 보고한다. 그림은 `figures/trajectories_<scene>_<seed>.png`10장(150dpi,1:1 축,벽·상자·출발·목표·종료,실제 R3 굵은 선,두 방법 겹침)이다. 기술 실패 칸은 no data로 표시하고 둘 다 없으면 생략 사유를 기록한다. 기존 결과는 덮어쓰지 않는다.

## 사용자가 실행할 명령 — 준비 단계에서는 실행하지 않음

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase37p.campaign --run-root ../artifacts/isaac6/phase37p_01 > ../artifacts/isaac6/phase37p_01.log 2>&1 < /dev/null &
```

로그: `../artifacts/isaac6/phase37p_01.log`. 진행 확인:

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase37p.campaign --run-root ../artifacts/isaac6/phase37p_01 --status
```

검증 산출물: `research/results/phase37p/preparation/`의 replay.json/replay_events.csv/replay_input_hashes.json,validation.json,dry_run.json,tests.log. 재개 시 같은 명령을 사용한다.
