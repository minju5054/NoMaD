# Phase30-R 준비 — CLR 선호 거리만 0.15→0.08m

**시뮬레이션·렌더·NoMaD 추론·campaign은 실행하지 않았다.** 기존 주행 결과를 읽고 단위테스트/가짜 report/인자 검증만 수행했다. 수치 단위테스트에서 CPU7 worker와 spawn pool 자식은 실행했지만 주행 프로세스는 없다. 기준 commit `c2e9b72f06f10fffa3781fd1901d98c136193227`; 새 protocol SHA256 `4a99d731931a4226316feb4f674219013f2d08bc1cc0c3bbd755a585b75974e1` (`FROZEN`).

## 변경 범위

| 경로 | 변경 | 그대로 두는 것 |
|---|---|---|
| 평소 G18 ClearanceGraph | `max(0,0.08−d)/0.05`, active test `d<0.08`; target metadata도0.08 | 나머지 residual·Jacobian·hard constraint·solver·certificate·prior |
| R3 우회 Graph | clearance residual과 active test의0.15만0.08로 치환 | progress1.2/0.10, smoothness0.03, σ_c0.05, 7개 초기값,4-process,1s, κ≤4, 구간0.10~0.20, radius1.6, near0.3 및 certificate |
| R2 수리 Graph | **변경 없음** | 실제 R2 목적은 intent/smoothness/heading 세 항이며,0.15 clearance soft 항이 없다. 새 항을 추가하지 않음 |

원 파일은 수정하지 않는다. 평소 항은 원 함수의 code object를 그대로 쓰고 private globals의 D_PREF_M만0.08로 바꾼 subclass다. R3는 원 residual 함수 AST에서 해당 두 상수만 치환하고, 각 pool 자식의 메모리에서만 연결한다. `0.08→0.15`로 복원한 AST hash가 원본과 동일하다. R2는 기존 solve_sample을 그대로 호출한다. 새로운 λ/σ/반복/시간 제한 튜닝 없음.

## 동일성·검증

- 동결 파일 SHA256 **307개 일치**. Graph hard 조건·certificate·bounds·초기값 및 NORMAL/R3의 CLR 외 residual/Jacobian이 같음을 검사했다.
- 목표0.08 확인(거리0.07에서 residual0.2,0.10에서 비활성), Jacobian 중앙차분 오차≤1e−5.
- C0-NA PP+SP,90° 초과 정렬, 결정 계층·지도/필터·R2/R3 전달·stale/superseded·회복·평가기를 재사용한다. 런타임 config는 방법 이름/Phase30-R 표식 외 Phase29와 동일하다.
- **단위테스트10개 통과**, 10개 scene×index의 실제 base launcher 인자 검증을 socket/파일/프로세스 생성 전에 중단했다. JSON records는 `default` 없는 표준 json.dumps로 검사했다. CPU7 normal worker와 spawn 자식의 R3 target 및 원 R2 연결을 실제 수치 프로세스로 확인했다.
- 가짜 완료 metrics로 표·짝 비교·INCLUDE_TONIGHT/EXCLUDE 생성을 확인했다. 원 baseline과 raw는 수정하지 않았다. 근거는 `research/results/phase30r/preparation/verification.json`.

## 바꾸지 않은 다른 0.15

| location | meaning | action |
|---|---|---|
| nomad_phase24r/geometry.py: EndDoor cy+.15 | 기존 문 장식 위치 offset | 유지 |
| nomad_phase20c/detour.py: linspace(0,1.5,11) | 초기 구간 간격 0.15m(암묵적) | 유지 |
| nomad_phase28 graph/graph_r1: .15s | 과거 H 시간 budget; 이번 G18 경로에는 미사용 | 유지 |
| Phase29 protocol의 inherited R1 .15 / p95 .15 | 이전 등록/게이트 이력, G18 수치 설정 아님 | 원본 보존 |
| 과거 report/offline/visualize의 .15 | 기존 평가/시각화·다른 방법의 상수 | 모두 유지 |

전체 동결 의존 파일의 literal/string 검색 목록 **72행**은 `preparation/all_015_occurrences.csv`에 파일·행·원문·역할별로 저장했다. 과거 진단/테스트/시각화도 포함한 목록이며, 모두 이번 실행의 활성 수치라는 뜻은 아니다. 전역 문자열 치환은 하지 않았다.

## 10회 실행 및 report

G18-R × SLW/LC/L2/H1/H2 × seed201/202. 순서는 Phase29 dev의 G18 순서를 그대로 취한다. D750, seed offset10000·index,90초, goal radius0.3 등 기존 조건 유지. 단일 시뮬레이터 순차 실행, 기술 실패만 같은 seed 1회 재시도, 기존 완료 run 재개/보존, short socket 사전 검사, run 종료 후 `portable/cache`·`pycache` 정리를 유지한다. 새 root는 `../artifacts/isaac6/phase30r_dev_01`이며 아직 생성하지 않았다.

report는 **Phase29 G18 dev10회만** 재사용(목표 도착5/10, 충돌3). confirm이나 smoke를 섞지 않는다. 결과: `docs/PHASE30R_RESULTS.md`, `research/results/phase30r/`. 방법×장면 및 같은 seed의 도착/충돌/도착시간 짝 차이/평균속도/R3 실행시간/R3 설치 경로 길이/상자 통과시간/최소여유를 생성한다. R3 실제 주행 거리와 R2 시간·길이는 별도 열이다. R3 실행시간은 APPLIED→END(정렬 포함), 경로 길이는 실제 설치된 polyline 길이 합이며 미완료는 종료시각 검열 표식을 남긴다.

`INCLUDE_TONIGHT` = G18-R 도착≥G18, 충돌≤G18, 둘 다 도착한 짝의 도착시간 차이 중앙값(R−old)<0. 그 외 `EXCLUDE`. 성공 짝이 없거나 기술 실패/미완료로 안전 비교가 확인되지 않으면 INCLUDE로 판정하지 않고 EXCLUDE 사유를 명시한다. 최소여유는 참고 지표이며 판정에 넣지 않는다.

디스크: 현재 44.73GB, Phase29 동일 run 실측 저장량 합으로 신규10회 예상 17.26GB, 예상 잔여 27.46GB. Phase29처럼 매 run 전 최소30GB를 검사한다. 10회 전체를 마친 뒤에도30GB를 남기려면 예상 47.26GB가 필요하다. **전체10회+30GB 유지 추정 충족: False**, 추가 필요량 약 2.54GB(저장량 변동·기술 재시도 별도). `enough`는 다음 run 시작의30GB 조건만 뜻한다. 기존 결과/raw 삭제는 하지 않는다.

실행 명령(미실행):

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase30r.campaign --run-root ../artifacts/isaac6/phase30r_dev_01 > ../artifacts/isaac6/phase30r_dev_01.log 2>&1 < /dev/null &
```

진행 확인:

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase30r.campaign --run-root ../artifacts/isaac6/phase30r_dev_01 --status
```

완료 후 report는 campaign이 `/usr/bin/python3`와 `PYTHONPATH=research`로 생성·commit·push한다. 수동 생성 명령: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase30r.report --run-root ../artifacts/isaac6/phase30r_dev_01 --publish`. venv pip install 없음.
