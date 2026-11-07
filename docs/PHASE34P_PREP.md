# Phase34-P 준비 — C0-NA+EC / C0-NA+EC−R2

**준비만 완료. 본 주행·smoke·Isaac·렌더·NoMaD 추론은 실행하지 않았다.** Protocol **FROZEN**, SHA256 `3df6d2a2bdc21e3caf4756ce54217a42e27cb1c929df9a29cda8c7c1dc047b01`.

## 방법과 변경 범위

| 방법 | ALL_UNSAFE(A) | B | 공통 |
| --- | --- | --- | --- |
| C0-NA+EC | 기존 R2 → 실패 시 R3 | 기존 R3 | Phase32 동결 |
| C0-NA+EC−R2 | R2 호출 없이 기존 R3로 바로 진입 | 변경 없음 | 같은 R3/EC/fallback/실행기/지도/평가기 |

파일·CLI 식별자는 ASCII `C0-NA+EC-R2`을 사용한다. A의 u_ref는 기존 `radial_reference` 그대로다: 출발점→현재 위치 단위벡터, 변위0.5m 미만이면 출발 heading. 원 코드의 R2 dispatch body만 기존 `start_detour(A)` 호출로 바꿨다. 같은 tick에 pending R3와 RECOVER가 동시에 시작되지 않도록 pending-planner guard만 동등하게 확장했다. 이 두 AST 변경을 되돌리면 원 AST hash가 일치한다. NORMAL 선택·worker-busy fallback·B·R3 해 선택·EC·90° 초과 출발 정렬·PP/SP·회복 수치·목표0.3m·90s 제한을 바꾸지 않는다.

## 저장 v2

두 방법 모두 Phase33 저장 어댑터를 사용한다. snapshot과 repair input에는 values를 쓰지 않고 `savez_compressed`로 기록하며 STORAGE_RETROFIT 로더로 복원한다. tick/component metadata와 빈 지도 상수를 보존한다. 라이브 SDF 갱신/노이즈/필터 계산은 그대로다. R3의 기존 derived-cache 전송도 그대로이며, run 종료 후 기존 cleanup 옵션으로 `portable/cache`, `pycache`를 정리한다. 원본 RGB/depth 보존 여부도 기존 Phase26 규칙을 유지한다. 새 seed210/211은 compact 기록이다.

## 저장 로그 사전 확인 — 판정 미사용

Phase32 전체30 run/attempt의 R2 SUBMIT44건을 빠짐없이 사용했다. 각 호출의 B·이전(v,ω)·snapshot·tick·기존 속도 상한을 고정하고 R3 초기값7개를 기존4-process pool에서 한 번씩 풀었다. 원래 A→R3 로그의 방향 25건도 같은 함수로 재현해 일치를 확인했다.

| source | n | R3_solution | pre_EC_selected_pass | EC_eligible_solution | available_with_existing_rules | pool_p95_s |
|---|---|---|---|---|---|---|
| ALL | 44 | 6 | 4 | 4 | 4 | 0.54976 |
| C0-NA+EC | 31 | 6 | 4 | 4 | 4 | 0.51398 |
| G18+EC | 13 | 0 | 0 | 0 | 0 | 0.55807 |

`R3_solution`은 EC 이전 수락 해 존재, `pre_EC_selected_pass`는 원 numerical winner의 EC 통과, `EC_eligible_solution`은 기존 EC 필터 뒤 선택 가능한 해 존재다. `available_with_existing_rules`는 여기에 기존 certificate와1s 한도를 포함한다. 고정 snapshot 반사실이며 계산 대기 중 이동·다음 관측/NoMaD 갱신은 재현하지 않는다. **이 수치로 실행/판정 조건을 바꾸지 않았다.**

## 사전등록 실행·판정

SLW/LC/L2/H1/H2 × seed210/211 ×2방법 =20회. seed→scene 블록, 블록 내 방법 순서는 `random.Random(20261108)`로 고정했다.

| scene | index | methods |
|---|---|---|
| SLW | 210 | ['C0-NA+EC', 'C0-NA+EC-R2'] |
| LC | 210 | ['C0-NA+EC', 'C0-NA+EC-R2'] |
| L2 | 210 | ['C0-NA+EC-R2', 'C0-NA+EC'] |
| H1 | 210 | ['C0-NA+EC', 'C0-NA+EC-R2'] |
| H2 | 210 | ['C0-NA+EC', 'C0-NA+EC-R2'] |
| SLW | 211 | ['C0-NA+EC-R2', 'C0-NA+EC'] |
| LC | 211 | ['C0-NA+EC', 'C0-NA+EC-R2'] |
| L2 | 211 | ['C0-NA+EC-R2', 'C0-NA+EC'] |
| H1 | 211 | ['C0-NA+EC', 'C0-NA+EC-R2'] |
| H2 | 211 | ['C0-NA+EC-R2', 'C0-NA+EC'] |

10개 같은 scene×seed 짝에서 `PROMISING` = −R2 도착 수≥baseline 도착 수 AND −R2 충돌 수≤baseline 충돌 수. 그 외 `NOT_PROMISING`.20개 기술적으로 유효한 run이 없으면 unknown collision을 안전으로 간주하지 않고 `NOT_PROMISING`과 근거 불완전 사유를 함께 남긴다. 동일 seed 기술 실패1회 재시도, 완료 run 재실행 없음, 잠금/재개/원자 state 저장을 그대로 사용한다. 매 run/attempt 전 여유30GB 미만이면 중단한다.

자동 report는 `/usr/bin/python3 + PYTHONPATH=research`로 `docs/PHASE34P_RESULTS.md`, `research/results/phase34p/`를 생성하고 commit·push한다. 도착/충돌 외 지표는 판정에 쓰지 않는다: A 횟수, A의 R3 적용 성공/실패·EC 거절(job/후보), 우회 실행 시간, 도착시간 짝차이(둘 다 성공한 짝), 정지비율, 기존 평가기 contact 구간의 실행 상태. 기존 평가 결과를 다시 계산하거나 고치지 않는다.

## 검증·용량

단위 테스트 17개 통과, 실제 base launcher 인자 검증20개는 socket 경계에서 중단해 프로세스 생성0을 확인했다. campaign20개 조합 dry-run과40개 attempt의 짧은 socket 경로 검사를 통과했다. Simulator는 SimulationApp 뒤에만 numerical/storage 모듈을 import한다. 모든 config는 허용한 seed/식별자 변경을 제외하면 동결 C0-NA 설정과 같다.

현재 여유 1190.43GB. Phase32 C0-NA+EC launcher 실측 평균을20회에 적용한 참고 예상은 약 0.90시간(새 장면의 경로 차이·재시도 제외)이다. 본 주행으로 시간을 다시 측정하지 않았다.

## 사용자 실행 명령 — 실행하지 않음

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase34p.campaign --run-root ../artifacts/isaac6/phase34p_01 > ../artifacts/isaac6/phase34p_01.log 2>&1 < /dev/null &
```

진행 확인:

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase34p.campaign --run-root ../artifacts/isaac6/phase34p_01 --status
```

수동 report: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase34p.report --run-root ../artifacts/isaac6/phase34p_01 --publish`
