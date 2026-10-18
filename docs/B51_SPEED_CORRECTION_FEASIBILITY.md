# B51에서 속도만 줄이는 safety correction의 offline feasibility

2026-10-18 KST. 기준 `6f8267b37e958d5daf2446d6c763b585f90fb8d8`, 입력 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/old_rollout_obstacle_01/`. **고정 grid의 최대 feasible speed는 H1 .18 m/s, H2 .10 m/s다.** B51에서 `(v,w)=(.10,−.4)`를 한 번 결정해 H2 끝까지 유지하면 전진하면서 두 horizon 모두 2cm margin을 충족한다. 이 짧은 위험 구간은 정확한 geometry를 아는 offline 조건에서는 Graph 없이 감속만으로 예방할 수 있었다.

## 실행 전 고정한 비교와 입력 제한

[Protocol](../research/results/isaac6_b51_speed_feasibility_20261018/protocol.json)을 grid 계산 전에 저장했다. 속도 **[0,.02,.04,…,.20] m/s의 11개**, w는 항상 −.4 rad/s. 모든 72Hz interval에서 기존 `swept_clearance`의 **모든 장애물 clearance 하한 ≥.02 m**, `corridor_clearance` 하한 >0을 요구하고 **양수 속도 중 가장 큰 값**을 선택했다. Grid 추가·세분화·threshold 변경은 하지 않았다. 여기서 최대는 **검사한 grid의 최대값**이며 연속 최적 속도는 아니다.

배치 당시 확정된 static/dynamic geometry, B51의 실제 pose/원본 PD/validity, 고정 horizon과 grid만 선택에 사용했다. FRESH 52/53의 prediction·command 또는 B51 이후 실제 pose/clearance를 correction 선택에 사용하지 않았다. 선택을 끝낸 뒤 H1 실제 trace를 읽어 검증했다. H1/H2 종료 시각은 사용자가 지정한 기록 기반 endpoint이며 온라인으로 미래를 예측했다는 의미는 아니다.

`(0,−.4)`는 제자리 회전이므로 전진 feasible speed 선택에서 제외했다. **정지 `(0,0)`**는 별도의 trivial reference이며 reconciliation 성공으로 취급하지 않는다. 원본 controller 파일은 수정하지 않았다.

## B51의 실제 상태

- Tick **1000**, simulation **13.888888889 s**. 저장된 72Hz pose **`(2.097864810,−.001133875,−.966924877)`** m,m,rad로 switch log와 일치한다.
- 원본 PD **`(.2,−.4)`** m/s,rad/s. 수신 기준 timeout 잔여 **.942698223 s**, 긴 H2(.416667 s)보다 길다.
- 반경 .09 m footprint의 dynamic clearance **.044174143 m = 4.417414 cm**. 요구 2cm를 제외한 추가 여유 **2.417414 cm**가 있었다.
- Static 1/2 clearance .307865/.562136 m, corridor clearance 1.408866 m. 모든 초기 조건 충족.

Dynamic box는 중심 `(2.405633551,−.195502975)`, 크기 `(.35,.35,.8)` m로 이미 출현한 상태다. 기존 두 static box와 radius/margin/속도 제한/4·9·72Hz 설정을 변경하지 않았다.

## H1/H2 안전성과 이동

H1은 tick 1000→1016, **.222222222 s**(실제 B52까지), H2는 tick 1000→1030, **.416666667 s**(기존 충돌 검출·정지 시각까지)다. 각 조건은 B51에서 결정한 command를 끝까지 고정하며, 중간에 속도를 바꾸거나 새 observation을 사용하지 않는다.

| Horizon / 조건 | `(v,w)` m/s,rad/s | 최소 swept clearance 하한 (cm) | 2cm margin | Geometric overlap | 이동 거리 (cm) | 감속 |
|---|---|---:|---|---|---:|---:|
| H1 RAW 51 · 실제 기록 일치 | `(.20,−.4)` | **1.918788** | 미달 | 없음 | 4.444444 | 0% |
| H1 SPEED-LIMITED 51 | `(.18,−.4)` | **2.154597** | 충족 | 없음 | 4.000000 | .02 m/s / 10% |
| H2 RAW 51 유지 · counterfactual | `(.20,−.4)` | **.136918** | 미달 | 없음 | 8.333333 | 0% |
| H2 SPEED-LIMITED 51 | `(.10,−.4)` | **2.206896** | 충족 | 없음 | 4.166667 | .10 m/s / 50% |

Minimum은 모든 경우 dynamic obstacle에서 발생했고, **모든 행에서 corridor containment 충족**이다. RAW는 **H1의 마지막 interval `[14.097222222,14.111111111] s`에서 처음 2cm margin을 미충족**했다. H2 RAW는 51의 명령을 계속 유지하는 counterfactual로, 이후 실제 52가 적용되어 충돌했던 경로와 다르다. 이 표의 H2 RAW 자체에는 geometric overlap이 없지만 안전 기준에는 미달한다.

H1에서 .20은 unsafe여서 .18이 grid 최대였다. H2에서는 .12 및 그보다 큰 후보가 모두 unsafe여서 .10이 grid 최대였다. **하나의 B51 command로 두 horizon을 모두 보장하려면 `(.10,−.4)`**를 유지하면 된다. 이 command의 H1 prefix clearance는 **3.097952 cm**, 이동 거리는 2.222222 cm다. .18→.10으로 중간 변경하는 스케줄을 사용한 것이 아니다.

| Horizon / 조건 | 종료 `(x,y,yaw)` m,m,rad |
|---|---|
| H1 RAW 51 | `(2.121443741,−.038790779,−1.055813766)` |
| H1 SPEED-LIMITED .18 | `(2.119085848,−.035025089,−1.055813766)` |
| H2 RAW 51 유지 | `(2.139262446,−.073346201,−1.133591543)` |
| H2 SPEED-LIMITED .10 | `(2.118563628,−.037240038,−1.133591543)` |

정지 `(0,0)`는 양 horizon 모두 clearance 4.417414 cm, 이동 0, 종료 pose=B51이었다. 정지 없이도 움직이는 feasible speed가 있으므로 정지 reference는 결론의 근거로 사용하지 않았다.

## 해석과 검증

**이번 B51 이후의 제한된 horizon에서는 단순 감속만으로 margin을 지키며 전진 가능했다.** 따라서 이 위험에 대해 trajectory reconciliation 또는 Graph Optimization이 추가로 필요하다는 근거는 얻지 못했다. 이는 **offline oracle feasibility** 결과다. NoMaD가 정확한 obstacle geometry를 온라인으로 알고 있거나 실제로 이 correction을 선택·실행했다고 주장하지 않는다.

FRESH 52의 unsafe prediction·방향 반전은 별도 사건이다. 이번 H2 correction은 52를 적용하지 않고 B51의 결정된 command를 유지하는 가정이며, 이후 새로운 prediction 처리나 goal 도달을 검증하지 않았다. 실제 온라인 geometry 추정, 안전한 다음 command 선택, 더 긴 시간의 진행 가능성은 남은 문제지만 이 기록만으로 Graph 필요성을 도출할 수는 없다.

기존 `integrate_se2`, `original_controller`, `swept_clearance`, `corridor_clearance`만 재사용했다. H1 RAW의 **17개 pose/16개 interval**이 실제 incoming ID 51 및 유효 command와 일치한다. 저장된 pose, static/dynamic swept clearance 및 corridor 값과의 **최대 오차 모두 0**. 257개 run input hashes, 기존 분석·그림 및 보호 source 9개 불변. 새 navigation/inference/시각화/test/코드 수정 0회.

결과: [전체 grid CSV](../research/results/isaac6_b51_speed_feasibility_20261018/speed_grid.csv), [RAW/보정/정지 비교 CSV](../research/results/isaac6_b51_speed_feasibility_20261018/comparison.csv), [summary·검증 JSON](../research/results/isaac6_b51_speed_feasibility_20261018/summary.json). 원본 데이터와 기존 결과는 덮어쓰지 않았다.
