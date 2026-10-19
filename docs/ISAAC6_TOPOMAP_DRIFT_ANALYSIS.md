# Topomap 정적 주행: 최초 경로 이탈 원인 분석

2026-10-19. 기준 `edf716eb7b9b03cca1ddc3fb508f40d8315e7c9d`, 분석 branch `research/isaac6-topomap-drift-audit`. 저장된 `topomap_static_01`, reference `async_wide_wall_01`, Topomap manifest만 사용했다. **최초 0.20 m 초과는 8.833333 s, Prediction 30 실행 중**이다. 큰 localization 후퇴 11→7→3은 이후 사건이다. 다만 그 전에도 작은 node 후퇴와 뒤쪽 subgoal 선택이 있었으므로 localization/subgoal의 기여를 배제할 수 없다. 단일 원인의 인과 판정은 **`INSUFFICIENT_EVIDENCE`**다.

## 방법과 원본 보존

실제 모든 1,002개 72 Hz pose를 reference 1,771개 pose의 **world XY polyline 전체**에 최근접 projection했다. Reference 시간과 실제 시간을 대응시키지 않았다. 길이 1e−9 m 이하인 정지 segment 80개를 제외하고, 정확한 동률은 먼저 기록된 segment를 택했다. 횡방향 부호는 reference 진행 tangent의 왼쪽이 양수다. 0.20 m 기준은 point-to-polyline Euclidean 거리이며, 최초 초과 지점에서는 signed lateral과 정확히 같다. 꼭짓점 projection의 longitudinal residual은 별도 보존했다(0–12 s 최대 2.701 mm).

최소 거리+1 mm 이내인 projection들이 reference 진행거리 0.10 m 이상 벌어지면 모호하다고 표시하는 규칙으로 **모호한 실제 pose 0개**였다. 최대 근접 projection 진행거리 폭은 0.061111 m다. 시작 node 0/1은 같은 pose여서 nearest-node tie로 표시했다. 이 진단은 시각 localization의 정답을 제공하지 않는다.

기존 `topomap_report.validate_map`, 선택 함수, `local_to_world`, 원본 PD AST loader, `integrate_se2`, swept/corridor 함수를 재사용했다. 52개 실제 switch 전체에서 선택 score/기존 CSV, RGB history hash, sample 0/index 2, observation anchor와 적용 interval을 대조했다. Pose integration 및 원본 PD 오차 **0**, swept/corridor 최대 오차 **2.22e−16 m**. 최초 projection을 별도 scalar segment 계산으로 확인한 차이는 **2.78e−17 m**였다. 기존 runtime audit의 117개 hash와 이번에 사용한 총 208개 input/result/RGB hash를 확인·보존했다. 원본 실행 source와의 기존 차이는 이전 보고서 작성 때 수정된 `topomap_report.py` 하나이며 이번 runtime 변경은 없다.

새 navigation/GPU inference/시각화/테스트/parameter 변경은 **0회**. 기존 [경로 그림](../research/results/isaac6_topomap_20261019/topomap_navigation.svg)을 재사용한다. 상세 수치는 [prediction CSV](../research/results/isaac6_topomap_drift_20261019/prediction_diagnosis.csv), [projection checkpoints](../research/results/isaac6_topomap_drift_20261019/reference_projection_checkpoints.csv), [요약·hash](../research/results/isaac6_topomap_drift_20261019/summary.json), [관심 prediction의 8-point 원본 경로](../research/results/isaac6_topomap_drift_20261019/focused_native_paths.json)에 있다. Checkpoint CSV는 controller tick·정수 초·threshold 전후를 추린 것이며, 초과/지속 판정은 전체 72 Hz 기록에서 계산했다.

## 1. 최초 0.20 m 초과와 실제 적용 prediction

- Tick **635 / 8.819444 s**: +0.198785730 m.
- Tick **636 / 8.833333 s**: **+0.200121247 m**, 왼쪽 이탈. Pose `(1.278630977, 0.816051948, 0.400693887)`; projection `(1.258154225, 0.616981066)`. 연속시간의 정확한 첫 초과는 두 tick 사이로만 한정한다.
- 당시 **ID 30**: observation **8.486111 s**, switch **8.666667 s**. 다음 ID 31 observation은 이미 **8.736111 s**에 촬영됐지만 threshold 시점에는 아직 수신되지 않았다. ID 31 switch는 **8.888889 s**다. 다음 observation은 ID 32의 **8.986111 s**다.
- Ready는 host monotonic epoch 기준 ID 30 **8.574599259 s**, ID 31 **8.882933039 s**다. 이 값들을 simulation timestamp로 변환하거나 서로 다른 clock끼리 빼지 않았다.
- 이후 12 s까지 **229/229 pose**가 0.20 m 초과이고, 종료까지도 복귀하지 않았다. 이탈 거리: 7 s **0.090949 m**, 8 s **0.129834 m**, 9 s **0.216216 m**, 10 s **0.321028 m**, 11 s **0.456197 m**, 12 s **0.633105 m**, 종료 **0.988399 m**. 처음부터 0.20 m였다가 회복한 구간은 없다.

ID 30의 observation pose는 `(1.215686, .786740, .455145)`, B30은 `(1.248219, .802411, .442609)`다. Closest/subgoal은 **9/9**, node 9 pose는 `(1.383283, .592551, −.262887)`다. Observation 위치의 geometric nearest node는 **8**, distance-head score는 node 8 **8.189460**, node 9 **7.584473**으로 공식 argmin은 9다. 최소 score가 3 이상이어서 node 10으로 전진하지 않았다. Score는 m 단위가 아니다.

Node 9는 observation projection보다 reference arclength **0.172222 m**, B30 projection보다 **0.148821 m 앞**에 있다. Observation body frame에서도 `(forward,left)=(+.065171,−.248095)m`로 오른쪽 앞이다. 따라서 이 시점의 subgoal을 명백한 후방 목표 또는 대규모 localization 실패라고 볼 증거는 없다. 반대로 geometric nearest와의 1-node 차이가 시각적으로 타당한지, 해당 subgoal이 회복 가능한 목표인지도 pose 정보만으로 확정할 수 없다.

## 2. Localization / subgoal: 선행 문제와 후행 문제

아래 이탈은 **switch 시점**, nearest node는 **observation pose 기준 offline** 값이다. `SG 앞거리`는 switch pose projection에서 SG까지의 reference arclength 차이다. 음수면 참조 경로 진행 방향의 뒤쪽이다.

| ID | Obs / switch (s) | Closest / SG | Nearest node | Min score | 이탈 (m) | SG 앞거리 (m) |
|---|---|---|---|---|---|---|
| 21 | 6.236 / 6.333 | 5 / 5 | 6 | 4.268 | .0626 | −.2679 |
| 23 | 6.736 / 6.889 | 7 / 7 | 7 | 4.093 | .0868 | +.0322 |
| 24 | 6.986 / 7.111 | 6 / 7 | 7 | 2.096 | .0950 | −.0072 |
| 27 | 7.736 / 7.889 | 7 / 7 | 8 | 5.211 | .1242 | −.1404 |
| 30 | 8.486 / 8.667 | 9 / 9 | 8 | 7.584 | .1841 | +.1488 |
| 34 | 9.486 / 9.667 | 9 / 9 | 9 | 9.593 | .2837 | +.0181 |
| 36 | 9.986 / 10.111 | 10 / 10 | 9 | 10.030 | .3343 | +.1578 |
| 37 | 10.236 / 10.333 | 10 / 10 | 9 | 9.971 | .3627 | +.1279 |
| 42 | 11.486 / 11.667 | 7 / 7 | 10 | 12.373 | .5698 | −.6000 |
| 44 | 11.986 / 12.111 | 3 / 3 | 10 | 10.982 | .6548 | −1.4114 |

**0.20 m 초과 전의 문제도 있었다.** ID 21은 closest 5 유지 중 최소 score가 3을 넘으면서 SG 6→5로 후퇴했다. ID 23·24는 closest **8→7→6**으로 후퇴했으며, 각각 6.889·7.111 s에 이미 약 8.7·9.5 cm 이탈 상태였다. 이들은 0.20 m 초과보다 앞선다. ID 27은 closest 7 그대로 최소 score **2.930→5.211**이 되어 SG **8→7**로 후퇴했고, 이후 명령은 `w −.057270→+.270093`로 바뀌었다. 여기서는 subgoal과 observation/seed가 함께 변해 각각의 영향을 분리할 수 없다.

**큰 후퇴 11→7→3은 최초 큰 이탈의 시작 원인이 될 수 없다.** ID 42 observation 때부터 이탈 **.5370 m**, switch 때 **.5698 m**였고, ID 44에서는 각각 **.6304/.6548 m**였다. 선택 node 7/3은 observation body frame에서 전방 성분 **−.878/−1.687 m**로 뒤에 있었다. 당시 geometric nearest는 둘 다 node 10이다. ID 42는 후보 7…16의 하한 7, ID 44는 후보 3…12의 하한 3을 선택했다. 이는 이미 이탈한 관측에서의 localization/subgoal 실패와 부합하지만, 경로 이탈이 distance score를 악화시켰는지 또는 선택이 이후 이탈을 얼마나 악화시켰는지는 확정할 수 없다.

Node 변경 없이도 이탈은 증가했다. **ID 30–34에서 closest/SG 9/9 고정**인 동안 **.1841→.3078 m**, **ID 35–37에서 10/10 고정**인 동안 **.3078→.4078 m**다. 마지막 범위는 해당 마지막 prediction의 다음 switch까지를 포함한다.

## 3. Sample 0와 원본 PD: 경로와 실행 arc의 차이

원본 2D PD는 `v=clip(dx/.25,0,.2)`, `w=clip(atan(dy/dx)/.25,−.4,.4)`다. 아래 구간에서 dx는 모두 양수이며 v는 모두 .2 m/s로 clipping됐다. 각속도 반전은 **이미 local dy에서 발생**하고 clipping은 크기만 제한했다. 계산·전달·적용 pose의 구현 오류는 발견하지 못했다.

| ID | SG | Local index 2 (dx,dy) m | Clipping 전 w | 실제 w (rad/s) | 실제 interval 이탈 변화 (m) |
|---|---|---|---|---|---|
| 30 | 9 | (.123385, −.007768) | −.251488 | −.251488 | .1841→.2055 |
| 33 | 9 | (.154951, −.008729) | −.225096 | −.225096 | .2499→.2837 |
| 34 | 9 | (.160756, +.026941) | +.664196 | +.400000 | .2837→.3078 |
| 35 | 10 | (.136550, −.000671) | −.019653 | −.019653 | .3078→.3343 |
| 36 | 10 | (.145792, +.027839) | +.754704 | +.400000 | .3343→.3627 |
| 37 | 10 | (.114982, −.002316) | −.080571 | −.080571 | .3627→.4078 |

**최초 초과는 좌회전 반전 순간이 아니다.** B30에서 로봇 yaw는 **+25.360°**, reference tangent는 **−3.482°**로 약 **28.842°** 벌어져 있었다. ID 30은 우회전했지만 전진하는 동안 왼쪽 횡오차는 커졌다. Native 8-point path는 뒤쪽 point에서 더 크게 오른쪽으로 굽는다(local index 2 y=−.007768 m, final y=−.171296 m). Observation-anchored selected point의 이탈은 **.224584 m**, final point는 **.134741 m**다. 이 회복 곡선 전체를 순차 실행한 것이 아니라 index 2가 만든 하나의 원본 PD arc를 다음 switch까지 실행했다. Native path의 tail 복귀를 실제 복귀로 해석할 수 없다.

**동일 SG에서도 Sample 0 방향 변화가 있었다.** ID 34는 SG 9 유지 중 오른쪽→왼쪽, ID 36·37은 SG 10 유지 중 오른쪽→왼쪽→오른쪽이다. ID 34/36의 native selected point 이탈은 **.375592/.430466 m**, final point는 **.464322/.459704 m**로 원래 이탈 방향을 더 키운다. 이들 full polyline은 두 static box 및 corridor 기준으로는 안전하지만, reference 복귀 경로는 아니다. Reference deviation과 geometric collision을 구분해야 한다.

Subgoal의 `reference상 앞쪽`과 `현재 body frame의 앞쪽`도 다르다. ID 34는 reference 진행거리로 아직 **+.018080 m**지만 observation body 전방 성분은 **−.098842 m**다. ID 36·37도 reference상 앞쪽이지만 body frame에서는 뒤쪽/오른쪽이다. 따라서 “subgoal이 완전히 적절했는데 sampling만 문제”라고 단정할 수 없다. 다만 같은 goal image hash와 node를 유지해도 trajectory/제어 방향이 바뀐다는 사실은 확인됐다.

ID 33→34, 35→36, 36→37에서 observation은 각각 약 **5 cm** 이동했고 yaw는 **−2.469°, +3.392°, +2.724°** 변했다. 실제 새 RGB의 평균 절대 pixel 변화는 **6.846, 6.822, 5.995 /255**, history는 각각 새 frame 1장을 포함했다. Seed도 **167→169, 171→173, 173→175**로 달랐다. 동일 subgoal의 반전을 diffusion noise 하나의 효과라고 분리할 근거는 없다. Native yaw/timestamp는 만들지 않았고 FRESH world 경로는 observation pose를 유지했다.

## 판정과 다음 최소 검증

1. **직접 확인된 실행 메커니즘:** reference보다 왼쪽을 향한 상태에서 Sample 0/index 2의 원본 PD 전진이 계속됐고, 일부 동일 SG prediction은 추가 좌회전을 요구했다. 원본 PD 계산 오류는 없지만, native 곡선과 index 2만 사용하는 PD 실행의 차이는 실제로 확인됐다.
2. **Localization/subgoal의 상대적 근거:** 초기 후방 SG 선택과 작은 node 후퇴는 선행 요인 후보다. 최초 0.20 m 초과의 SG 9는 reference 진행 방향상 앞쪽이어서 큰 후방 localization 실패로 설명되지 않는다. 큰 11→7→3 후퇴는 이미 .5 m 이상 이탈한 후의 문제다. Pose nearest node를 시각적 정답으로 간주하거나 단일 원인을 확정하지 않는다.
3. **다음 한 가지:** **저장된 ID 34의 8개 sample만**, 같은 실제 B34와 다음 switch까지의 동일 구간에서 원본 PD로 offline 비교한다. 회전 방향·reference 횡오차 증가량을 보면 sample 0이 다른 출력들과 다르게 이탈을 키우는지, 8개 전반의 goal-conditioned prediction/PD 문제인지 좁힐 수 있다. 새 inference·navigation·reranking 정책 없이 가능한 가장 작은 검증이며, 이번에는 실행하지 않았다. 개선 성공을 보장하거나 online selection 기준을 제시하는 실험은 아니다.

재실행 명령(기존 결과가 없는 **새** 출력 경로 필요):

```bash
PYTHONPATH=research /usr/bin/python3 -m nomad_isaac.topomap_drift_audit --run ../artifacts/isaac6/topomap_static_01 --topomap ../artifacts/isaac6/topomap_reference_01/topomap/manifest.json --out /tmp/nomad_topomap_drift_audit
```
