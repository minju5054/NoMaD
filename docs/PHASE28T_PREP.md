# Phase28-T 준비 — 시간 구성 진단과 단일 smoke

**본 campaign·smoke·Isaac는 실행하지 않았다.** 저장368개 사건의 로그 분석과 동결0.15s R1 오프라인 재측정, 합성 단위테스트만 수행했다. 기존 주행 결과와 C0-NA·결정·R2/R3·필터·평가기·R1 비용/제약은 보존했다.

## 1. 기존368사건 진단

실제 H 적용0/368. 사건 이유는 `{'TIMEOUT': 358, 'DETOUR_STARTED': 10}`다. 완전한 numerical result가 남은 것은 358건이고 나머지는 CASE_SUMMARY의 총 시간만 있다.

| stage | n | p50_s | p95_s | max_s |
|---|---|---|---|---|
| dispatch→worker completion(total) | 368 | 0.15402 | 0.16705 | 0.23581 |
| before diagnostics(composite) | 358 | 0.15229 | 0.16473 | 0.23338 |
| diagnostic bookkeeping | 358 | 0.00073431 | 0.0051101 | 0.057521 |
| dispatch→decision(wait, not compute) | 368 | 0.22054 | 0.22634 | 0.25594 |

worker 시작·큐 진입, B 예측 시작/끝, NA 초기 적분 시작/끝, SLSQP 시작/끝, certificate 시작/끝은 **기존 로그에 없다**. planning_wall_s는 이들을 합친 값이므로 역으로 분해하거나 queue 시간으로 간주하지 않는다. initialization 메타데이터는 경로 적분이 끝났다는 사실만 알려주며 시간은 알려주지 않는다.

358개 TIMEOUT payload의 iterations=0은 정상 solver 반환 전 예외가 나면 그대로 남는 기본값이다. 초기 x와 마지막 x가 다른 358건에서 solver가 진행된 흔적은 있지만 **TIMEOUT의 정확한 반복 번호는 복원 불가**다. 이번에는 완료 major callback마다 timestamp와 CPU 시간을 기록하고 timeout 시 완료 callback 수를 남긴다. 내부 line-search/minor iteration 수는 SciPy가 공개하지 않으므로 주장하지 않는다.

### 같은 실제 입력의 오프라인 비교

이전 R1 표본은 Phase27-R 자료라 이번 Phase28-C0-H368건과 단순히 seed/id로 짝지을 수 없다. 이번 실제 DISPATCH의 선택 경로·snapshot·예측B/vw를 동결 R1로 한 번씩 다시 풀었다(한도0.15s 유지). 이전 H 적용이0이라 실제 warm state는 모두None이다. 가능하면 저장 OLD NA 상태를 복원하고 같은72Hz 예측을 수행해 B/vw가1e−10 이내로 일치하는지 확인했다.

| scope | n | online_p50_s | online_p95_s | offline_p50_s | offline_p95_s | paired_online_minus_offline_median_s | paired_online_minus_offline_p95_s |
|---|---|---|---|---|---|---|---|
| prediction reproduced | 368 | 0.15402 | 0.16705 | 0.061663 | 0.089065 | 0.094924 | 0.11842 |
| saved B solver-only | 0 | — | — | — | — | — | — |

prediction reproduced 368건은 예측+풀이를 포함한 오프라인 시간이다. 나머지 0건은 저장 B를 직접 쓴 solver-only 비교이며 B 예측 시간이 빠져 있어 전체 dispatch 시간의 동등 비교가 아니다. 두 범위를 섞어 순수 SLSQP speedup으로 주장하지 않는다. 온라인은 Isaac·NoMaD와 동시 실행된 값, 오프라인은 `/usr/bin/python3`에서 계측한 값이다. 원 온라인 NumPy/SciPy 버전과 thread CPU/GIL 대기는 기록되지 않아 계산 지연을 CPU 경쟁 하나로 단정할 수 없다. 오프라인 출력 분포: `{'OPTIMIZED': 269, 'FALLBACK': 90, 'INIT_ONLY': 9}`. 기존 결과는 재분류하지 않는다.

## 2. 사전 고정 시간·자원 정책

- 적용: dispatch 후 **세 번째9Hz tick**, 즉24개의72Hz tick 뒤(0.333333s). B는 원 실행기와 원 plant 적분 함수로 그 tick까지 예측한다. 비용·제약·초기화·fallback 선택 규칙·controller·지도는 같다.
- 계산 예산: **0.30s**, dispatch에서 B 예측·대기·전송·worker·certificate·결과 수신까지 포함한다. 넘으면 FALLBACK. worker 계산이 성공했어도 전송 포함 시간이 넘으면 수락하지 않고 원 numerical type을 별도 보존한다.
- 기존 R1.solve의 세0.15시간 비교만0.30으로 치환하고 원 함수·factor·Jacobian을 재사용한다. AST 검사와 수치 동등성 테스트로 다른 상수/식을 바꾸지 않았음을 확인한다.
- 기존 thread는 Isaac와 PID/GIL을 공유하므로 H 수치 worker만 별도 프로세스로 옮긴다. 실제 Isaac 부모의 Python executable, NumPy/SciPy 파일 경로·버전을 그대로 넘기고 일치를 검사한다. 새 venv나 패키지는 설치하지 않는다. R2/R3 worker는 변경하지 않는다.
- 선택 core 계획: `{'possible': True, 'allowed': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], 'driver_cpus': [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14], 'worker_cpu': 7, 'reserved_siblings': [7, 15], 'physical_core': [0, 7]}`. worker는 CPU 7에, Isaac/NoMaD 등 이 launcher의 자식들은 나머지 driver CPU에 고정한다. SMT sibling도 driver에서 제외한다. `os.sched_setaffinity` 실패/지원 불가 시 사유와 실제 mask를 기록하며 분리 성공을 허위로 표시하지 않는다. 다른 사용자 프로세스의 affinity는 바꾸지 않는다.

SDF는 immutable array를 공유 메모리로 복사해 전송하며 값/점유/관측 배열은 바꾸지 않는다. 큐·복사·IPC·attach·worker·반복별·certificate·반환 timestamp를 남기고, 계산 p95에 전송 overhead도 포함한다. solver cost/constraints나 선택·우회 정책을 수정하는 추가 최적화는 없다.

## 3. 계측 및 smoke report

새 로그: `phase28_handoff.jsonl`의 TIMING_RESULT에 모든 dispatched job의 최종 계측(폐기/timeout 포함), WORKER_READY에 PID·core·library 정보를 남긴다. 원 CASE_OUTCOME/CASE_SUMMARY/COMMAND 로그도 유지한다. 단계는 B prediction, client queue, SDF copy, send→receive, attach, NA72Hz 초기 적분, SLSQP, 초기/최종 certificate, application certificate, result receive/decode/cleanup으로 나눈다. nested 구간(예: initialization_total 안의 NA 적분)을 합산하지 않는다.

smoke report는 사건별 시간 분포 CSV, OPTIMIZED/INIT_ONLY/FALLBACK(실제 case·future·worker 원출력별), 실제 적용 수, feedback clip 비율, 단계별 p50/p95/max, 완료 major 반복 수·간격·반복당 시간을 출력한다. application certificate는 계산 예산과 별도로 표시한다. 알 수 없는 값은NA로 남긴다.

게이트는 사용자 확정대로 다음을 모두 만족해야 한다.

- **실제 적용된 OPTIMIZED 또는 INIT_ONLY 사건 수 / (전체 H 사건 수 − 버려진 DETOUR_STARTED 사건 수) ≥70%.** R2/R3 우회 시작으로 버려진 DETOUR_STARTED만 분모에서 제외하고 그 수를 별도 보고한다. SUPERSEDED, WORKER_BUSY, TIMEOUT, TERMINAL 등 다른 사유는 모두 분모에 포함한다. 사건별 포함·제외는 `gate_cases.csv`에 남긴다.
- **전체 dispatched job 계산 p95≤0.30s**는 그대로 유지한다. DETOUR_STARTED가 적용 비율 분모에서 제외되어도 해당 job의 측정 계산시간은 p95에 포함한다. 시간초과·다른 폐기 job도 제외하지 않는다. WORKER_BUSY는 계산을 시작한 job이 없으므로 사건 수에는 포함하되 계산 p95에는 넣지 않는다.

전체 H 사건 대비 원 비율과 numerical OPTIMIZED/INIT_ONLY 대비 적용률도 참고로 보고하지만 게이트에는 사용하지 않는다. 기술 실패나 유효 분모0은 통과로 처리하지 않는다.

## 4. 준비 검증·명령(실행하지 않음)

단위테스트 15개 통과. 적용 tick, 예측 적분, budget-only AST, factor/제약 수치 보존, timeout 반복 계측, 프로세스 전달·affinity 선택, report/gate를 검증했다. 실제 H1 렌더/NoMaD/주행 smoke는 실행하지 않았다. Protocol SHA256 `aab511238b48d82dca217912b7cdddd47c63a60bf3a409e925c4c98da3db5823`.

H1 × C0-H × seed201 **한 번만**, 기존90초 주행 상한을 유지한다. 본 campaign 호출이나 자동 재시도는 없다. 기존 smoke 폴더가 있으면 덮어쓰거나 재실행하지 않는다. 결과는 본 실험에서 제외한다. 완료 후 `docs/PHASE28T_SMOKE.md`, `research/results/phase28t/smoke/`를 생성한다.

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase28t.smoke --output ../artifacts/isaac6/phase28t_smoke_01 > ../artifacts/isaac6/phase28t_smoke_01.log 2>&1 < /dev/null &
```

로그 확인: `tail -n 20 /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase28t_smoke_01.log`

report 재생성: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase28t.report --smoke-root ../artifacts/isaac6/phase28t_smoke_01`
