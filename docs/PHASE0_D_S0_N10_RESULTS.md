# Phase 0-D — S0 paired N=10 본 실험

2026-10-20. **PP 10회 / PD 10회 완료, 기술적 실패 0회, 재시도 0회.** 이 결과를 Phase 2의 S0 baseline으로 고정한다. 평가 범위는 **Oracle geometry evaluation; SE(2) kinematic Isaac Sim**이다. 실제 로봇/PhysX 동역학 검증으로 확대하지 않는다.

## 실행과 검증

Clean `5ec2d1eb2e67479c3c7f54765fd5e3ed84812e51`, `research/phase0-infrastructure`에서 기존 runner를 변경 없이 실행했다. 모든 child도 같은 SHA/clean checkout이다. PP→PD 순서로 10 pair를 직렬 실행했고 전체 wall time은 2,720.24초였다. 기존 pilot은 표본에 포함하지 않았다.

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV bash research/python.sh -m nomad_phase0.s0_batch --execute --run-root /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/s0_paired_n10_01
```

위 명령은 **완료된 실행 기록**이다. 해당 출력 경로는 이미 존재하며 재실행 대상으로 사용하지 않는다.

- Protocol: `research/nomad_phase0/s0_batch_protocol.json`. S0/Topomap/모델/PP/PD/4·9·72Hz/1초 waypoint timeout/추가 지연 0 설정 불변.
- Pair `S0_01`…`S0_10`: PP=PD offset `10000,20000,…,100000`. 실제 1,570개 request의 `101+offset+2*request_id`, DDPM `+1` 확인. Pair별 request 개수/RGB가 같다는 의미는 아니다.
- S0 SHA-256: `f2090961b1699285f6c5986abaeed6c3fb28516c582f11cd5fa6d6c2d7ce3a27`.
- 2초/14-node manifest SHA-256: `5b720e71b03b9809488ca81c340bfe691f39542371bad03eddf7a40246285f36`.
- Checkpoint SHA-256: `70f79b8262527e20e56ced64a3e3d7ef91855bc9e7c3fa348d78edcb83c6a333`.
- 실행 전후 frozen input hash 및 Topomap RGB/pose 검증 PASS. 20회 RGB gate/finite output PASS, checkpoint parameter coverage 100%, missing/unexpected key 없음.
- 기존 metric extractor의 PP applied command / PD 원본 명령과 72Hz trace 대조 PASS. Pose 재적분 최대 오차 0, 장애물별 logged swept minimum과 summary 일치. Aggregate를 기존 함수로 다시 계산한 결과도 원본 aggregate와 동일하다.
- 기존 pacing 기준 20/20 PASS: run별 p95 오차의 최댓값 0.165ms, 전체 최대 오차 2.099ms, real-time factor 0.9999624…0.9999962. Waypoint timeout 0회. 정지는 모두 첫 이동 이전 대기이며, 첫 이동 후 `(v,w)=(0,0)` 정지 구간은 없다.

프로토콜의 과거 “preflight only” 문구는 변경하지 않았다. 이번 본 실행은 별도 사용자 승인에 따른 것이며, 아래 결과는 본 실험이다. 원본 aggregate/CSV는 byte-for-byte 복사했고, 기존 집계에 없는 충돌/복도 침범별 CI만 기존 `wilson`/`bootstrap_mean`으로 별도 보충했다.

## 결과

SUCCESS는 goal entry AND geometric overlap 없음 AND corridor 침범 없음이다. 2cm 장애물 margin 위반은 성공 여부와 독립적인 72Hz 검사 interval 누적 시간이다.

| 결과 | PP (n=10), Wilson 95% CI | PD (n=10), Wilson 95% CI |
|---|---:|---:|
| SUCCESS / goal entry | 9/10, 90% [59.6, 98.2]% | 3/10, 30% [10.8, 60.3]% |
| Geometric obstacle collision | 0/10, 0% [0, 27.8]% | 3/10, 30% [10.8, 60.3]% |
| Corridor footprint 침범 | 1/10, 10% [1.8, 40.4]% | 4/10, 40% [16.8, 68.7]% |
| SAFETY_FAILURE (둘 중 하나) | 1/10, 10% [1.8, 40.4]% | 7/10, 70% [39.7, 89.2]% |
| 60초 timeout | 0/10, 0% [0, 27.8]% | 0/10, 0% [0, 27.8]% |
| 기술적 실패 | 0/10, 0% [0, 27.8]% | 0/10, 0% [0, 27.8]% |

`OTHER_TERMINATION`/conservative contact stop은 0회다. 아래 모든 복도 실패는 conservative bound만의 실패가 아니라 실제 constant-command arc의 footprint 침범으로 확인했다.

- **PP S0_08:** 13.888889s corridor 침범. 나머지 PP 9회는 goal entry.
- **PD S0_01/03/06/10:** 각각 12.583333/13.458333/12.833333/13.486111s corridor 침범.
- **PD S0_02/08/09:** 각각 16.458333/16.763889/17.222222s StaticObstacle2 충돌. 2cm margin 위반 누적 시간은 0.138889/0.138889/0.236111s.
- **PD S0_04/05/07:** goal entry. 모든 성공 run은 두 장애물 모두 통과했다.

Run별 평균 [bootstrap 95% CI]다. Goal time만 PP n=9 / PD n=3이며 나머지는 각 n=10이다. Switch median/max도 먼저 run별로 계산한 뒤 평균했다.

| 지표 | PP | PD |
|---|---:|---:|
| Goal time, 도달 조건부 (s) | 24.360 [24.244, 24.491] | 25.185 [24.611, 26.000] |
| 종료 시간 (s) | 23.313 [21.174, 24.449] | 17.836 [14.893, 21.146] |
| 이동 거리 (m) | 4.438 [4.011, 4.666] | 3.315 [2.730, 3.973] |
| 정지 시간 (s) | 1.122 [1.111, 1.144] | 1.111 [1.111, 1.111] |
| 2cm margin 위반 시간 (s) | 0 [0, 0] | 0.05139 [0, 0.10833] |
| StaticObstacle1 최소 clearance (m) | 0.16452 [0.13217, 0.21049] | 0.29831 [0.24867, 0.34997] |
| StaticObstacle2 최소 clearance (m) | 0.12124 [0.05688, 0.23976] | 0.37142 [0.11401, 0.63134] |
| Switch \|Δw\| median (rad/s) | 0.11875 [0.10568, 0.13295] | 0.08102 [0.06530, 0.09470] |
| Switch \|Δw\| max (rad/s) | 0.73088 [0.66506, 0.78842] | 0.68633 [0.62542, 0.74230] |
| Switch w 부호 전환 횟수 | 24.2 [21.0, 26.9] | 16.1 [12.9, 19.6] |
| 실제 w clipping 비율 | 20.00% [15.43, 25.63]% | 30.32% [26.28, 34.68]% |

PP 전체 실행에서 가장 작은 obstacle clearance는 **32.209mm**, PD는 **−0.498mm**다. PP margin 위반 총합은 0s, PD는 0.513889s다. PP의 corridor 실패는 이 obstacle margin 지표와 별개다.

통과 측면(기존 footprint rear-clear 기준): 첫 장애물 +Y 통과 PP 10/10, PD 8/10; 둘째 −Y 통과 PP 9/10, PD 3/10. 나머지는 미통과이며 다른 측면 통과는 없었다. 각 비율의 Wilson CI는 `conditions.csv`에 보존했다.

**종료 시간이 짧거나 장애물 minimum clearance 평균이 크다는 것만으로 더 효율적/안전하다고 판단하지 않는다.** PD는 다수가 조기 종료했고 일부는 둘째 장애물에 접근하기 전에 끝났기 때문에 해당 minimum이 크게 남는다. 부호 전환 횟수도 실행 시간·switch 수에 영향을 받는다.

## Paired PP−PD

Protocol대로 PCG64 seed `20261020`, 10,000회 bootstrap, run ID를 단위로 재표본화했다. 모두 n=10 pair이고 goal time만 양쪽 goal에 도달한 `S0_04/05/07`의 n=3이다. 미도달 goal time은 null이며 60초로 대체하지 않았다.

| Paired 차이 | 평균 [95% CI] |
|---|---:|
| 성공률 | +60%p [+30, +90]%p |
| Obstacle collision 비율 | −30%p [−60, 0]%p |
| Corridor 침범 비율 | −30%p [−70, +10]%p |
| Goal time (양쪽 도달 n=3) | −0.958s [−1.722, −0.403] |
| 이동 거리 | +1.123m [+0.391, +1.831] |
| 2cm margin 위반 시간 | −0.05139s [−0.10833, 0] |
| Switch \|Δw\| median | +0.03773rad/s [+0.01775, +0.05733] |
| Switch \|Δw\| max | +0.04454rad/s [−0.03920, +0.12875] |
| 실제 w clipping | −10.32%p [−15.43, −4.74]%p |

PP의 관측 성공률과 clipping 비율은 유리했지만 switch 불연속은 감소하지 않았다. 동일 offset은 동일 RGB·FRESH·물리적 correspondence를 뜻하지 않는다. N=10 및 조건부 goal-time n=3의 불확실성이 크며, 고정 PP→PD 순서 효과도 남는다. PP의 보편적 우월성이나 동일 prediction에 대한 제어기만의 인과효과로 일반화하지 않는다.

## 보존과 다음 단계

- [원본 aggregate JSON](../research/results/phase0d_s0_paired_n10_20261020/summary.json)
- [Run별 CSV](../research/results/phase0d_s0_paired_n10_20261020/runs.csv), [조건별 CI](../research/results/phase0d_s0_paired_n10_20261020/conditions.csv), [paired CI](../research/results/phase0d_s0_paired_n10_20261020/paired_differences.csv)
- [충돌/복도별 CI](../research/results/phase0d_s0_paired_n10_20261020/outcome_components.json), [seed·hash·실행 검증](../research/results/phase0d_s0_paired_n10_20261020/verification.json)

Raw/RGB/model/전체 pose 및 command trace는 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/s0_paired_n10_01/`에 유지하고 Git에서 제외한다. 기존 결과 및 실행 코드는 수정하지 않았다. 새로운 시각화나 추가 navigation은 없다.

**Phase 2 S0 baseline으로 사용 가능하다.** 20개 유효 표본과 실패 사례까지 포함해 고정하며, 다음 단계는 실제 pose를 시작점으로 하는 feasibility 실험 B다. 이번 작업에서는 B의 대상 pose·탐색 프로토콜을 임의로 정하거나 추가 실행하지 않았다. 연구 결정(PP 주 실행기/제자리 회전 Recovery/oracle geometry/NoMaD)은 유지하되 이 batch에는 Recovery가 없다.
