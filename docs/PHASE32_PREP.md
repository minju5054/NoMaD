# Phase32 준비 — C0-NA+EC / G18+EC

**준비 단계만 수행. 시뮬레이션·smoke·렌더·NoMaD 추론·campaign을 실행하지 않았다.** 새 run-root는 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase32_01`이며 기존 결과를 덮어쓰지 않는다. Protocol **FROZEN**, SHA256 `3b0e631cde0bc69d82b81815aad39b847f931f03c748a5e5e28d284dde2b3378`.

## 사전등록 이탈 — 사용자 결정(2026-11-07)

Phase32-O 원 판정 **OFFLINE_FAIL**을 그대로 보존한다. 전체 전방 적분 위치오차 p95 **0.030037125m**가 원 gate **0.03m**를 넘었다. 동일 C0-NA 실행기 구간 오차 p95는 **0m**이므로 사용자가 진행을 명시적으로 승인했다. 이를 PASS로 재명명하거나 기존 gate·결과를 변경하지 않는다. Phase32-O 원 decision hash도 protocol에 고정했다.

## 공통 적용 규칙

- 두 방법의 실행기는 동결 C0-NA(PP0.25m+SP,90° 초과 정렬, v≤0.3·|ω|≤0.4·a≤0.5)다. G18 정상 Graph와 R2/R3 수식·가중치·초기값·solver·원 certificate·online stale/superseded 규칙, 결정 계층·depth/필터·평가기는 재사용한다. G18-R을 섞지 않는다.
- 설치 직전 해당9Hz 제어 tick에서 최신 immutable V1 depth로 EC를 수행한다. oracle을 검사 API에 전달하지 않는다. 원형 반경0.09m, swept minimum≥0.025m, 지평선은 기존 endpoint 도달 또는2s다.
- 설치 후 **36tick=0.5s마다**72Hz integrate callback에서 재검사한다. 제자리 정렬 목표·PP progress·감속 cap 등 현재 follower 상태를 복제하고 실제9Hz clock phase를 유지한다. tick36검사는 현재 명령을4tick 유지한 뒤 tick40에서 다음 제어를 계산한다. 이는 실행기 함수/수치를 바꾸는 것이 아니라 현재 실행 상태에서의 예측이다.
- 주기 REJECT 경로 교체/STOP_WAIT은 다음9Hz tick에 적용한다. 검사 tick·적용 tick·simulation-clock 지연 tick/ms(0 또는4tick, 최대55.56ms)와 실제 monotonic wall-clock 지연을 따로 기록한다. wall-clock 지연은 검사·fallback 계산과 pacing 초과를 포함할 수 있다. 이전 경로의 검사 결과를 새 경로에 적용하지 않도록 generation을 대조한다.
- NORMAL: primary 경로 → 남은 SAFE 후보(FRESHEST 잔여 길이 내림차순, index 동점 규칙) 전속도 검사 → **같은 SAFE 후보 전부를 같은 순서로0.1m/s 재검사** → 처음 PASS 설치 → 없으면 기존 STOP_WAIT. G18 primary는 해당 후보의 Graph XY, 나머지는 원 SAFE XY이며 추가 Graph 풀이를 하지 않는다.
- 주기 REJECT의 NORMAL 대안은 적용 tick에 이용 가능한 최신 NoMaD 후보 세트를 최신 지도에서 다시 SAFE/FRESHEST 순서로 검사한다. 이미 거절된 활성 경로를 전속도로 다시 설치해 검사를 우회하지 않는다.
- 0.1m/s 상한은 가속도 제한을 지켜 적용하고 **다음 FRESH가 전속도 PASS로 설치될 때만 해제**한다. 그 전 periodic/Graph/R2/R3 경로 교체에서도 유지한다. 감속 설치 수·유지 시간·선택 FRESHEST 순위를 기록한다.
- R2는 EC REJECT이면 기존 R3 단계로 보낸다. R3는7개 초기화의 원래 수락 해 중 EC PASS인 해만 대상으로 **기존 최대 전진→최소 길이→index** 선택을 쓴다. 없으면 원래 실패 처리다. 원 numerical results는 그대로 로그에 보존하고 EC 선택만 별도 기록한다.
- EC STOP이 부모 코드의 NORMAL 알림으로 잘못 초기화되지 않도록 adapter가 알림을 보호한다. RECOVER_ROTATE의 조건·회전량·횟수 상한은 바꾸지 않는다.

EC 검사에 실제 사용한 snapshot은 기존 비동기 archive queue로 보존한다. 지도 계산/갱신/노이즈/unknown 정책은 바뀌지 않는다. 검사 연산은 실행 thread에서 동기적으로 수행되며 그 비용과 pacing 영향은 보정하지 않는다. R3 여러 해를 검사하는 batch에는 여러 EC 호출이 포함된다.

## 실행 행렬·과거 비교

H1/H2/L2 × seed201~205 × 두 방법 =30회. seed→scene, 각 블록 방법 순서는 `random.Random(20261107)`로 사전에 고정했다.

| scene | index | methods |
|---|---|---|
| H1 | 201 | ['C0-NA+EC', 'G18+EC'] |
| H2 | 201 | ['C0-NA+EC', 'G18+EC'] |
| L2 | 201 | ['G18+EC', 'C0-NA+EC'] |
| H1 | 202 | ['G18+EC', 'C0-NA+EC'] |
| H2 | 202 | ['C0-NA+EC', 'G18+EC'] |
| L2 | 202 | ['G18+EC', 'C0-NA+EC'] |
| H1 | 203 | ['G18+EC', 'C0-NA+EC'] |
| H2 | 203 | ['G18+EC', 'C0-NA+EC'] |
| L2 | 203 | ['C0-NA+EC', 'G18+EC'] |
| H1 | 204 | ['G18+EC', 'C0-NA+EC'] |
| H2 | 204 | ['G18+EC', 'C0-NA+EC'] |
| L2 | 204 | ['G18+EC', 'C0-NA+EC'] |
| H1 | 205 | ['C0-NA+EC', 'G18+EC'] |
| H2 | 205 | ['G18+EC', 'C0-NA+EC'] |
| L2 | 205 | ['C0-NA+EC', 'G18+EC'] |

| method | n | goal | collision |
|---|---|---|---|
| C0-NA | 15 | 10 | 2 |
| G18 | 15 | 10 | 2 |

과거 대조는 같은 scene×seed의 C0-NA15개와 G1815개다. C0-NA201/202는Phase28,203~205는Phase29 confirm; G18은Phase29 dev/confirm. Phase31-P seed206/207은 비교 키에 없어 사용하지 않는다. **실행일이 다른 역사적 짝 비교**라는 한계를 명시한다. 원 데이터·출력 폴더·source hash를 `preparation/baselines.json`과 protocol에 고정했다.

## 판정과 report

`EC_HELPS` = 두 EC 방법의 충돌 합 < 기존 두 방법의 충돌 합 **AND** EC 도착 합 ≥ 기존 도착 합−1. 그 외 `EC_NO_HELP`.30개가 모두 기술적으로 유효하지 않으면 안전 개선을 주장하지 않고 EC_NO_HELP와 근거 불완전 사유를 남긴다. 기술 실패는 기존 campaign처럼 동일 seed1회만 재시도하며 완료 run은 재실행하지 않는다.

완료 후 `/usr/bin/python3 + PYTHONPATH=research` report가 `docs/PHASE32_RESULTS.md`, `research/results/phase32/`를 만들고 commit·push한다. 방법×장면 도착/충돌/도착시간/정지비율, 같은 seed 차이, 상태별 EC 호출/REJECT, fallback별 수, REJECT로 인한 실제 정지시간, 계산 p50/p95, 주기검사 적용 지연, 감속 설치/유지/순위를 포함한다. STOP latch 이후 물리정지 총시간과 순수 STOP_WAIT시간을 분리한다.

## 검증·용량

30개 config는 Phase29 원 설정에서 Phase32 식별 필드를 제거하면 hash가 일치한다. 실제 base launcher의 argparse/status/index 검증30개를 socket 계산 경계에서 중단해 확인하며, worker/Isaac 프로세스는 생성하지 않는다. SimulationApp 이전에는 EC/SciPy를 import하지 않는다. 신규 EC 테스트23개와 동결 EXEC-CERT 테스트13개, 총36개를 통과했다. 실제 base launcher 인자 검증30개와 campaign30조합 dry-run도 통과했으며 세부 결과는 `preparation/tests.json`에 저장한다.

현재 여유 **72.72GB**. 같은 과거 run 저장량+compact run의 추가 EC map 보존 상한으로30회 **약 75.36GB**,30GB reserve 포함 **105.36GB**를 예상한다. 전체 예상 충족 `False`; 부족분 약 **32.64GB**(기술 재시도 별도). run별 실제 여유30GB 미만이면 다음 run 전에 LOW_DISK_STOP. 기존 raw를 삭제하지 않는다. 기존 full-frame seed201/compact 나머지 규칙과 종료 후 portable/cache·pycache 정리를 유지한다.

과거 launcher 실측 합에 EC 처리 여유15%를 둔 예상 시간은 **약 1.50시간**(재시도·디스크 정지 제외). 준비 중 새 주행으로 시간을 측정하지 않았다.

## 사용자 실행 명령 — 실행하지 않음

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase32.campaign --run-root ../artifacts/isaac6/phase32_01 > ../artifacts/isaac6/phase32_01.log 2>&1 < /dev/null &
```

진행 확인:

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase32.campaign --run-root ../artifacts/isaac6/phase32_01 --status
```

수동 report: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase32.report --run-root ../artifacts/isaac6/phase32_01 --publish`
