# Prediction 50→51→52 방향 반전 및 충돌 원인

2026-10-18 KST. 기준 `31f7881719719e25c1bd0b1a49e45f0faf2b8efb`, 입력 `artifacts/isaac6/old_rollout_obstacle_01/`. **51→52의 각속도 부호 반전은 selected local waypoint의 dy 부호 변화로 설명된다. 52는 observation anchor 기준 full/prefix부터 unsafe였다.** Anchor diagnostic은 회전 방향을 바꾸지 않고 전진 속도를 낮춘다. 동일 B52의 짧은 비교에서 HOLD 51과 OBS-ANCHORED 52는 geometric overlap을 피하지만 **모든 조건이 2cm safety margin에 미달**한다.

50은 실제 구간도 안전했다. 51은 충돌하지 않았지만 실행 구간 끝 clearance가 **1.918788cm**여서 안전 기준을 이미 미충족했다. 따라서 두 prediction의 실행이 모두 안전했다는 전제로 분석하지 않는다. 49는 출현 전 OLD 참고로만 유지했고, 53은 수신됐으나 **실제 미적용**이다.

## Prediction, timing 및 원본 PD

시간은 simulation과 host monotonic을 구분한다. Ready는 host epoch `465296795716396 ns` 이후 경과시간이며, 이를 simulation 시각과 직접 빼지 않는다. Observation simulation time은 렌더링에 사용한 pose snapshot, host observation time은 capture start다. [JSON](../research/results/isaac6_direction_reversal_20261018/summary.json)에 원시 host ns, snapshot/ready 보간값, pose와 8개 local/world points를 보존했다.

| ID | Observation sim s | Ready host elapsed s | Switch sim s | Obs→ready / switch (host ms) |
|---|---:|---:|---:|---:|
| 50 | 13.486111 | 13.578777 | 13.666667 | 76.285 / 164.542 |
| 51 | 13.736111 | 13.830064 | 13.888889 | 78.858 / 138.241 |
| 52 | 13.986111 | 14.083449 | 14.111111 | 82.570 / 110.747 |

| ID | Observation `(x,y,yaw)` m,m,rad | Switch `(x,y,yaw)` m,m,rad |
|---|---|---|
| 50 | `(2.048656,.062617,−.926568)` | `(2.071036,.034281,−.878036)` |
| 51 | `(2.079757,.023472,−.905814)` | `(2.097865,−.001134,−.966925)` |
| 52 | `(2.108592,−.017350,−1.005814)` | `(2.121444,−.038791,−1.055814)` |

원본 [pd_controller](../deployment/src/pd_controller.py)의 이번 입력은 모두 `abs(dx)>=EPS` 분기다. **`v=dx/.25`, `w=arctan(dy/dx)/.25`** 다음 `v∈[0,.2]`, `w∈[−.4,.4]`로 clipping한다. `.25 s`는 원본 설정의 DT이며, controller refresh는 별도로 **9Hz**다. NoMaD local +x는 forward, +y는 left이므로 양의 w는 좌회전이다.

| ID | 실제 local `(dx,dy)` m | Observation-anchored selected world XY m | Clipping 전 `(v,w)` | 실제 `(v,w)` |
|---|---|---|---|---|
| 50 | `(.110200,−.014694)` | `(2.103092,−.034320)` | `(.440799,−.530218)` | `(.2,−.4)` |
| 51 | `(.080564,−.018535)` | `(2.114883,−.051363)` | `(.322255,−.904530)` | `(.2,−.4)` |
| 52 | `(.062752,+.043183)` | `(2.178662,−.047230)` | `(.251009,+2.410915)` | `(.2,+.4)` |

51→52에서 **dx는 계속 양수, dy는 −.018535→+.043183 m**로 바뀐다. 이 때문에 clipping **이전부터** 각속도가 음수→양수다. Clipping은 부호를 만들거나 반전시키지 않고 크기만 제한한다. 저장된 50·51·52의 모든 controller refresh와 원본 함수의 출력이 일치했다.

| ID | Native full / prefix clearance (cm) | 실제 적용 구간 min swept clearance (cm) | 실제 구간 판정 |
|---|---:|---:|---|
| 50 | +3.754 / +3.754 | +4.417 | Margin 충족, 충돌 없음 |
| 51 | +2.491 / +2.491 | +1.919 | Margin 미달, 충돌 없음 |
| 52 | **−7.184 / −3.803** | **−.126** | Geometric collision |

Full은 원본 8 points를 연결한 경로, prefix는 0–2를 연결한 경로다. Observation origin→prefix도 따로 재검사했고 같은 minimum이었다. 모든 경로는 **각 observation pose**로 world 변환했으며, 모든 장애물 중 minimum은 dynamic obstacle에서 발생했다. 52의 selected index 2 자체도 clearance −.038028 m다. 따라서 unsafe 상태는 tail에만 있거나 switch re-anchor 때문에 생긴 것이 아니다. 이 polyline diagnostic은 실제 원본 PD의 경로를 뜻하지 않는다.

## Observation anchor와 실제 switch pose

기존 `selected_point_semantics()`로 **고정된 observation-anchored world selected point 하나만 B local frame으로 표현**했다. 전체 FRESH trajectory를 B로 이동하지 않았다. 아래 계산은 실제 실행·검증된 correction이 아닌 offline diagnostic이다.

| ID | Obs→switch 위치 차이 / yaw 변화 | World point를 B local로 표현 `(dx,dy)` m | Diagnostic clipping 전 `(v,w)` | Diagnostic 최종 `(v,w)` |
|---|---:|---|---|---|
| 50 | 3.611cm / +2.781° | `(.073260,−.019146)` | `(.293041,−1.022518)` | `(.2,−.4)` |
| 51 | 3.055cm / −3.501° | `(.051009,−.014514)` | `(.204035,−1.108822)` | `(.2,−.4)` |
| 52 | 2.500cm / −2.865° | `(.035526,+.045640)` | `(.142104,+3.637490)` | **`(.142104,+.4)`** |

52의 원본 local input과 B 기준 표현의 차이는 **2.733694cm**다. Anchor 차이를 반영하면 v가 .2→.142104 m/s(**−28.948%**)로 낮아지지만 w는 여전히 +.4 rad/s다. 즉 stale 좌표 해석은 이 구간의 속도·충돌 여부에 영향을 줄 수 있지만, **51→52 회전 반전의 원인은 아니다**. 50·51에서는 동일 diagnostic의 clipping 후 command도 원본과 같다.

## 동일 B52의 제한된 counterfactual

초기 pose는 실제 B52 `(2.121443741,−.038790779,−1.055813766)`. 구간은 실제 S52 **14.111111111 s부터 충돌 검출·정지 tick 14.305555556 s까지**, **14×1/72=0.194444444 s**다. 더 이른 연속 contact bracket을 종료 시각으로 바꾸지 않았다. 모든 조건에서 동일 geometry/radius/limits를 사용하고 B52에서 계산한 command를 이 구간 동안 고정한다. World point를 매 tick 재계산하는 새 controller는 없다.

`integrate_se2`, `original_controller`, `swept_clearance`를 재사용했다. 먼저 RAW 52의 15개 pose 및 14개 swept 결과가 저장된 실제 실행과 일치함을 확인했다(**최대 오차 0**). HOLD 51의 receive-based timeout 잔여는 시작 .720519 s, 종료 .526444 s로 전체 구간에서 유효하다.

| 조건 | `(v,w)` m/s,rad/s | Min clearance 하한–상한 (mm) | Geometric overlap | 20mm margin |
|---|---|---:|---|---|
| RAW 52 · 실제 실행 | `(.2,+.4)` | **−1.261889 … −1.259960** | 있음 | 미달 |
| HOLD 51 · offline | `(.2,−.4)` | **+1.369177 … +1.371106** | 없음 | 미달 |
| OBS-ANCHORED 52 · offline | `(.142104,+.4)` | **+4.658447 … +4.659817** | 없음 | 미달 |

| 조건 | 종료 XY (m) | 종료 yaw (rad / deg) |
|---|---|---|
| RAW 52 | `(2.141893512,−.071857232)` | `−.978035988 / −56.0373°` |
| HOLD 51 | `(2.139262446,−.073346201)` | `−1.133591543 / −64.9500°` |
| OBS-ANCHORED 52 | `(2.135973734,−.062285191)` | `−.978035988 / −56.0373°` |

**B52 자체의 clearance가 19.189810mm**로 이미 20mm 미만이다. 두 counterfactual을 “안전한 회피”라고 부를 수 없다. HOLD 51은 같은 시간에 왼쪽 장애물 쪽으로 덜 접근하고, OBS-ANCHORED 52는 같은 w에서 덜 전진해 이 짧은 구간의 overlap을 피한다. 이후에도 충돌하지 않거나 goal에 도달한다는 결과는 없다. Geometric overlap이며 PhysX collision 실험이 아니다.

## 원인 판정과 범위

1. **Prediction 문제 확인:** 52는 observation 당시부터 full/prefix/선택 point가 unsafe했다. 내부적으로 왜 이런 sample을 생성했는지는 이번 기록만으로 확정할 수 없다. 50/51/52의 noise/DDPM seed도 201/202, 203/204, 205/206으로 다르고 RGB/history도 바뀐다.
2. **원본 controller 실행 문제 확인:** dy 부호 변화가 포화된 w의 반전을 직접 설명한다. 원본 controller는 전체 8-point path를 따라가지 않고 selected local point로 `(v,w)`를 반복 계산한다. Prediction 51의 경로가 safe여도 실제 실행 margin은 미충족했다.
3. **Temporal/frame mismatch 확인, Graph 필요성은 미입증:** Obs→switch 이동은 존재하며 B52 좌표 diagnostic이 속도와 단기 overlap 여부를 바꾼다. 그러나 FRESH 52 자체가 unsafe이고, HOLD와 anchor diagnostic 모두 2cm margin을 만족하지 못했다. “안전한 FRESH가 있지만 단순 연결로 해결할 수 없는 handoff”의 qualified 근거가 없으므로 이번 실패를 Graph가 해결할 문제로 단정할 수 없다. 이 결과는 unsafe prediction·원본 controller 실행·기존 margin 소진을 분리할 필요성을 보여준다.

작은 [prediction CSV](../research/results/isaac6_direction_reversal_20261018/predictions_50_52.csv), [B52 비교 CSV](../research/results/isaac6_direction_reversal_20261018/b52_counterfactuals.csv), [전체 수치/검증 JSON](../research/results/isaac6_direction_reversal_20261018/summary.json)을 저장했다. [기존 확대 그림](../research/results/isaac6_old_rollout_obstacle_20261018/old_rollout_detail.svg)을 그대로 참조했다. 257개 run 입력, 이전 분석·그림 hash, 보호 source 9개 불변. 실제 50–52 pose/clearance도 원본 기록과 최대 오차 0으로 재계산했다. 새 navigation/inference/시각화/test 0회, 모델·PD·scene·latency·seed 변경 및 Graph/새 correspondence/리팩터링 없음.
