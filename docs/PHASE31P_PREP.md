# Phase31-P 준비 — 동결 G18-R / C0 / C0-NA

**시뮬레이션·smoke·렌더·NoMaD 추론·campaign은 실행하지 않았다.** 단위테스트10개와 실제 base launcher 인자 검증30개(dry-run 경계에서 중단)를 완료했다. 새 run-root도 생성하지 않았다. 기존 방법 코드·수치·평가기·장면·이전 raw/results를 변경하지 않았다.

Protocol: `research/nomad_phase31p/protocol.json`, **FROZEN**. SHA256 `67d16e7c5a2f7fadb10b0cb96e58d669ddd799a22a3f165a22fe2e10785e8417`. 기준 commit `cce34ad730306ca5f4b0285651a991a604bff2aa`. 원본 동결 소스 324개 및 과거 결과2개 hash를 실행 전에 확인한다. 새 seed/ID/Phase31-P 표식만 정규화한 config hash30개가 각 방법의 기존 config와 일치한다(`preparation/config_hash_comparisons.json`).

## 동결 방법과 실행 경로

| 방법 | 재사용 코드 | 유지 내용 |
|---|---|---|
| G18-R | Phase30-R `runtime.install` | 정상/R3 CLR 목표0.08, σ0.05, 원 R2, 하드 제약·certificate·초기값·C0-NA PP/SP·>90° 정렬·CPU7 worker |
| C0 | Phase27-R 수정이 검증된 Phase26 `execution.install` | 원 C0 결정/필터/R2/R3·PP/SP·출발 정렬 |
| C0-NA | Phase28 `online_r1.install`의 C0-NA 분기 | 원 NA PP/SP·90° 초과 정렬, 원 결정/우회/필터 |

실행기/factor를 새로 구현하지 않고 각 동결 install 진입점을 직접 호출한다. 원 config factory의 seed 제한 때문에 허용된201 config를 만든 뒤 지정 seed206/207의 `seed_offset=10000·index`와 ID/표식만 바꾼다. 나머지 값은 전부 동일하다. G18-R은 Phase30-R의 CPU7 고정/driver affinity를 유지하고, C0·C0-NA는 각 기존 launcher의 inherited affinity를 유지한다. G18-R 전용 수치 패치를 다른 방법에 설치하지 않는다. SciPy/runtime import는 기존 SimulationApp 초기화 이후다.

## 블록과 방법 순서

SLW/LC/L2/H1/H2 × seed206/207 =10블록, 각3방법 =30회. 블록 순서는 seed→위 장면 순서다. 블록 내부는 **Python `random.Random(20261107).shuffle`**로 각 블록의 새 방법 목록을 섞고, 하나의 RNG stream을 이어 쓴다. 아래 순열을 protocol에 저장하고 검증 시 재생성하여 일치시킨다.

| block | scene | index | method_order |
|---|---|---|---|
| 1 | SLW | 206 | G18-R → C0 → C0-NA |
| 2 | LC | 206 | C0-NA → G18-R → C0 |
| 3 | L2 | 206 | C0-NA → C0 → G18-R |
| 4 | H1 | 206 | C0 → C0-NA → G18-R |
| 5 | H2 | 206 | C0 → G18-R → C0-NA |
| 6 | SLW | 207 | G18-R → C0 → C0-NA |
| 7 | LC | 207 | C0 → C0-NA → G18-R |
| 8 | L2 | 207 | C0-NA → C0 → G18-R |
| 9 | H1 | 207 | C0-NA → C0 → G18-R |
| 10 | H2 | 207 | C0-NA → C0 → G18-R |

순차 실행·잠금·재개를 기존 campaign에서 재사용한다. 기술 실패만 동일 seed1회 재시도하며 완료 run은 재실행하지 않는다. 모든 attempt 및 최종 기술 실패를 보존한다. 매 run 시작 전 실제 여유 공간이 **30,000,000,000bytes 미만이면 다음 run을 시작하지 않고 LOW_DISK_STOP**으로 기록한다. run 종료 후 두 자식 프로세스 종료를 확인하여 `portable/cache`·`pycache`만 삭제한다. raw는 삭제하지 않는다. short socket 경로는 두 attempt를 포함해 사전 검사한다.

## 사전 판정 — Phase31-P만

10개 scene×seed 짝에서 다음 네 조건이 모두 참이면 `EXPAND`, 아니면 `HOLD`다.

1. G18-R 도착 수 > C0-NA 도착 수.
2. G18-R 충돌 수 ≤ C0-NA 충돌 수.
3. G18-R 도착 수 ≥ C0 도착 수.
4. G18-R 충돌 수 ≤ C0 충돌 수.

기술 실패1회 재시도 후에도 유효하지 않거나 미완료이면10짝 안전 근거가 확인되지 않은 것으로 HOLD와 사유를 표시하며, 유효 부분 결과/실패를 숨기지 않는다. 통계 검정이나 별도 속도/clearance 문턱을 판정에 추가하지 않는다.

보조 지표는 둘 다 도착한 동일 scene×seed의 G18-R−C0 도착시간 차이 중앙값(n 병기), 평균속도, 정지비율, 최소여유(참고), G18-R 적용률/거절 사유다. 이 값들이 EXPAND/HOLD 계산에 사용되지 않고, 과거 합산 행이 판정 함수에 전달되지 않음을 테스트했다.

## Report 및 과거 합산

완료 후 `docs/PHASE31P_RESULTS.md`, `research/results/phase31p/`에 Phase31-P 전용 runs/decision/summary/paired 및 G18-R statistics, 기술 실패 목록을 생성한다. campaign 마지막 단계에서 `/usr/bin/python3`, `PYTHONPATH=research`로 report를 실행해 commit·push한다.

별도 과거 자료 절은 아래 행과 Phase31-P를 합친다. Phase29 파일의 reused/dev/smoke 행은 중복/다른 연구이므로 제외하고, Phase29 G18(0.15m)은 G18-R과 다른 방법이라 제외한다. Phase30-R에서도 재사용 G18 baseline을 제외한다. 과거와 새 자료의 seed·날짜·n·launcher resource 정책이 다르므로 합산은 서술용이다. **주 판정은 언제나 Phase31-P 30회만 사용한다.**

| source | method | n | indices | role |
|---|---|---|---|---|
| Phase29 confirm | C0 | 15 | 203,204,205 | descriptive only |
| Phase29 confirm | C0-NA | 15 | 203,204,205 | descriptive only |
| Phase30-R | G18-R | 10 | 201,202 | descriptive only |

## 검증·디스크

테스트10개: 동결 source/config hash, 세 install 진입점, 10블록 재현성과 완전성,30개 실제 argparse/status/index 검증, Kit-first import, strict `>`/`≥` 경계, 보조 지표 독립성, 과거 데이터를 바꿔도 주 판정 불변, 가짜 결과 report, retry/30GB 조건. 시뮬레이터/worker 생성 직전이 아니라 **socket 경로 계산 전에** 인자 dry-run을 중단했다.

현재 여유 48.31GB. 이전 compact run의 같은 scene·방법별 실측 최대값으로 신규30회 예상 저장량 64.45GB, 완료 후에도30GB를 남기려면 약 94.45GB가 필요하다. 전체 저장량 추정 충족 `False`; 추가 확보 추정 **46.14GB**(변동/기술 재시도 별도). 실제 중단 기준은 매 run 전30GB이며, 예측값으로 조건을 바꾸지 않는다. 기존 결과/raw 삭제나 venv pip install은 하지 않았다.

## 사용자 실행 명령 — 미실행

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase31p.campaign --run-root ../artifacts/isaac6/phase31p_01 > ../artifacts/isaac6/phase31p_01.log 2>&1 < /dev/null &
```

진행 확인:

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase31p.campaign --run-root ../artifacts/isaac6/phase31p_01 --status
```

수동 report: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase31p.report --run-root ../artifacts/isaac6/phase31p_01 --publish`
