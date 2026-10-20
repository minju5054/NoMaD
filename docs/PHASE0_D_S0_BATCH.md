# Phase 0-D — S0 paired batch infrastructure

기준 `f90b9ae`, 같은 `research/phase0-infrastructure`. 이번 작업은 **runner 구현과 CPU/offline 사전 검증만** 수행한다. 새 Isaac navigation/GPU inference 및 N=10 본 실험은 실행하지 않는다. 이전 pilot의 결과·판정·UNDECIDED 문서는 소급 변경하지 않는다.

현재 확정 연구 결정은 **Pure Pursuit 주 실행기, 제자리 회전 Recovery, oracle geometry, NoMaD navigation policy**다. 이번 S0 runner에는 Recovery를 구현하거나 활성화하지 않는다. 평가 범위는 모든 결과에 `Oracle geometry evaluation; SE(2) kinematic Isaac Sim`으로 명시한다.

## 고정 protocol과 seed

`research/nomad_phase0/s0_batch_protocol.json`에 S0 원본 JSON/hash, 2초14node manifest/hash, 10쌍의 offset, 실행 순서 및 통계를 고정했다. 각 pair에서 PP→PD 순서로 순차 실행하며 조건별 N=10이다. PP는 Phase0-C의 .25m lookahead, .2m/s, ±.4rad/s를 그대로 사용한다. PD는 원본 index2 계산을 사용한다. 원래4/9/72Hz,1초timeout,추가지연0 유지.

| Run ID | PP=PD offset | Request 0 seed | DDPM seed |
|---|---:|---:|---:|
| S0_01 | 10000 | 10101 | 10102 |
| S0_02 | 20000 | 20101 | 20102 |
| S0_03 | 30000 | 30101 | 30102 |
| S0_04 | 40000 | 40101 | 40102 |
| S0_05 | 50000 | 50101 | 50102 |
| S0_06 | 60000 | 60101 | 60102 |
| S0_07 | 70000 | 70101 | 70102 |
| S0_08 | 80000 | 80101 | 80102 |
| S0_09 | 90000 | 90101 | 90102 |
| S0_10 | 100000 | 100101 | 100102 |

Request k의 seed=`101+offset+2k`, DDPM=그 값+1. `--seed-offset` 기본0에서는 기존 seed와 runtime scenario 설정이 같다. Nonzero offset과 `--run-id`는 기존 frozen S0/static Topomap/asynchronous/zero-delay guard로 제한한다. 원본 scenario의 seed101은 변경하지 않고 runtime metadata에 offset/ID를 따로 추가한다. Request·worker inference·received·events 및 provenance에 실제 seed/ID가 남는다.

## Runner 동작

`nomad_phase0.s0_batch`의 `--dry-run`은 명령20개와 seed 대응표를 저장하며 child navigation을 실행하지 않는다. `--execute`는 향후 별도 본 실행용이다. 두 모드는 명시적으로 상호 배타적이고, 실행 root는 항상 새 경로여야 한다.

- 출력: `<root>/S0_01/PP`, `<root>/S0_01/PD`, …, `<root>/S0_10/PD`.
- GPU job은 blocking subprocess 한 개씩 실행한다. 공통 파일 lock으로 다른 S0 batch runner의 동시 실행을 거부한다.
- 실제 실행은 clean checkout에서만 허용하며 각 job 전 Git SHA/dirty 상태와 고정 입력 hash를 재확인한다.
- 각 job START/END, exit code, 오류를 `execution.jsonl`, `launcher_logs/`, `metrics/`에 보존한다. 실패해도 같은 job을 재시도하거나 seed를 대체하지 않는다. 다음 예정 job만 진행한다.
- 기존 출력이 있으면 덮어쓰지 않는다. Resume 및 자동 재실행 기능은 없다. 중단 신호는 journal에 남기고 후속 실행을 멈춘다.
- Batch plan에는 Git SHA, 전체 S0 config, PP 설정, scenario/map/checkpoint/PP/PD hash를 보존한다. Run provenance에는 실행 SHA, config hash 근거, offset, ID, map hash를 기록한다.
- 각 run metric JSON에는 실제 request seed 목록도 저장한다. `aggregate/runs.csv`, `summary.json`, `conditions.csv`, `paired_differences.csv`를 생성한다.

Dry-run 예시(실행 child 없음):

```bash
bash research/python.sh -m nomad_phase0.s0_batch --dry-run --run-root /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/s0_paired_n10_01 --output /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase0d_dryrun_01
```

향후 본 실행용 명령이며 **이번 작업에서는 실행하지 않는다**:

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV bash research/python.sh -m nomad_phase0.s0_batch --execute --run-root /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/s0_paired_n10_01
```

## Batch metric 정의

기존 pilot의 `SAFE_GOAL_SUCCESS`와 다른 새 판정이다.

- `SUCCESS`: goal entry, geometric overlap 없음, corridor footprint 침범 없음.
- `SAFETY_FAILURE`: 확정 geometric overlap 또는 corridor footprint 침범.
- `STUCK`: 위 두 판정에 해당하지 않고 실제 simulation60초 timeout.
- `OTHER_TERMINATION`: 충돌이 확정되지 않은 `conservative_contact_stop` 등. 원본 종료 이유를 그대로 보존한다.
- `TECHNICAL_FAILURE`: launcher/자료 검증 실패. 실제 충돌이나 timeout으로 만들지 않는다.
- `margin_violation_s`: aggregate swept lower bound<.02m인 **양의 길이72Hz interval 시간 합**. 여러 장애물에 동시에 위반해도 interval을 한 번만 센다. `SUCCESS`/`SAFETY_FAILURE`와 독립적이며 정확한 연속시간 crossing 시각을 주장하지 않는다.

기존 conservative corridor bound가 containment를 증명하지 못한 것과 실제 침범도 구분한다. 저장된 명령의 기존 `integrate_se2`로 interval 끝점 및 x/y extrema를 평가해 footprint가 실제 corridor 밖으로 나갔는지 확인한다. 제어·기존 monitor 종료 규칙은 변경하지 않는다.

정지 시간은 실제 명령(v,w)=(0,0)인 interval 합이다. Switch |Δw|는 새 FRESH가 적용된 controller tick의 actual w와 직전 controller tick의 actual w 차이이며, OLD가 없는 첫 switch는 제외한다. PP는 `applied_*`와 PP의 unclipped w, PD는 실제 원본 PD 명령과 원본2D 식의 unclipped w를 사용한다. Clipping 비율은 전체 실제 제어 tick 중 strict clipping 비율이며 상한 점유율로 대체하지 않는다. 72Hz trace 명령 및 pose 재적분과 대조한다.

## 통계와 결측

- 이항 비율: Wilson95% CI.
- 연속 metric의 run별 평균: PCG64 seed20261020, 10,000회 percentile bootstrap95% CI.
- Paired PP−PD: 같은 run ID의 두 값 차이를 구하고 **pair 단위**로 재표본화한다. 서로 다른 조건을 독립적으로 resample하지 않는다.
- 성공률은 모든 시도(기술 실패 포함)가 분모다. 확정 safety failure/timeout/goal entry 비율은 관측 가능한 유효 navigation record가 분모이고, 기술 실패 수/율을 별도로 보고한다.
- Goal time은 실제 goal entry가 있는 경우만 사용한다. 미도달은 null이며60초로 대체하지 않는다. Paired goal-time은 양쪽 모두 goal에 도달한 pair만 사용한다. 모든 metric에 유효 n, missing을 보고한다.
- Clipping/전환/clearance 등 조건별 통계는 **run별 metric 평균**이다. 여러 run의 tick이나 switch를 한 덩어리로 합친 값이 아니다. 장애물별 통과 방향은 원래 label과 +Y/−Y/미통과 비율(Wilson)을 함께 남긴다.

N=10의 불확실성이 크며 작은 표본·상수값 bootstrap CI는 퇴화할 수 있다. 동일 seed offset도 서로 다른 closed-loop RGB와 request 발생 시각을 동일하게 만들지 않는다. Paired는 seed ID의 pairing이다. 고정 PP→PD 순서의 시간/order 효과도 남는다. 도달한 run만의 시간 비교는 조건부 결과이며 전체 navigation 성공 비교를 대체하지 않는다.

## 사전 검증

최소 신규6개+기존chunk3개/async5개, 총14 tests PASS. Zero offset 동일성, S0 제한,20job/seed 대응, 서로 다른 pair seed stream 분리, dry-run child 미호출, 실패 기록/재시도0/직렬 순서, lock, margin 독립성, conservative contact 구분, Wilson 경계, deterministic paired bootstrap 및 goal-time 결측을 검증했다. Fake child를 이용한 runner test는 GPU/navigation 실행이 아니다.

저장된 PP `phase0c_pure_pursuit_01`, PD `topomap_static_2s_01`을 read-only로 추출한 값:

| Metric | 기존 PP | 기존 PD |
|---|---:|---:|
| 새 batch 판정 | SUCCESS | SUCCESS |
| Goal time | 24.180556s | 25.305556s |
| 정지 누적 | 1.111111s | 1.111111s |
| Margin 위반 | 0s | 0s |
| 장애물1/2 최소clearance | .123676/.072557m | .279149/.074423m |
| 장애물1/2 통과 | +Y/−Y | +Y/−Y |
| Switch \|Δw\| median/max | .109232/.726350rad/s | .089287/.800000rad/s |
| Switch 각속도 부호 전환 | 27 | 23 |
| 실제 w clipping | 19/218=8.72% | 66/228=28.95% |
| 저장 pose 재적분 최대 오차 | 0 | 0 |

위 두 기록은 offset0의 **metric 검증용 기존 자료**이며 N=10 batch 표본으로 포함하거나 paired CI를 계산하지 않는다. 실제 nonzero-offset GPU 주행은 아직 실행하지 않았으므로 그 live 실행 검증은 미완료다.
