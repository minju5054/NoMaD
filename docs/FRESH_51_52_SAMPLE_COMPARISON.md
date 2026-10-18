# FRESH 51·52: 저장된 8개 diffusion sample 비교

2026-10-19 KST. 기준 `0df5ec6de26e37ad0b403925d7841a7c8be44890`, 입력 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/old_rollout_obstacle_01/`. **51에는 native/짧은 PD 실행 모두 안전한 대안 3개가 있었지만, 52에는 요구 2cm 기준을 만족하는 native sample이 하나도 없었다.** 52의 다른 sample 5개는 짧은 실행에서 overlap을 피했지만 모두 margin 미달이다. 따라서 52의 실패를 sample 0에만 국한할 수 없다.

## 기준과 복원

`model/derived/0051.npz`, `0052.npz`의 `metric`은 각각 **(8,8,2), float32, finite**였다. 모든 sample은 각 prediction의 **observation pose**로 `local_to_world()` 변환했다. Switch pose로 trajectory를 re-anchor하지 않았다. 각 sample의 local index 2를 원본 `original_controller()`에 입력했으며, +w=좌회전/−w=우회전/0=직진으로 집계했다. 회전 부호는 실제 장애물 통과 측면을 뜻하지 않는다.

Native full은 8 points를 이은 polyline, prefix는 index 0–2, origin-prefix는 observation origin→index 0–2다. 기존 `path_safety`/`clearance.py`로 **두 static box와 실제 출현한 dynamic box 모두**, radius .09 m, obstacle clearance ≥.02 m 및 corridor containment를 검사했다. Unsafe는 margin 미달을 포함하며 모두 geometric overlap이라는 뜻은 아니다.

| ID | Observation `(x,y,yaw)` m,m,rad | 실제 switch B `(x,y,yaw)` | 고정 PD rollout |
|---|---|---|---|
| 51 | `(2.079756858,.023472090,−.905813766)` | `(2.097864810,−.001133875,−.966924877)` | 13.888888889→14.111111111 s, **16/72 s** |
| 52 | `(2.108592054,−.017350072,−1.005813766)` | `(2.121443741,−.038790779,−1.055813766)` | 14.111111111→14.305555556 s, **14/72 s** |

PD rollout은 동일 ID의 모든 sample에 동일한 실제 B, horizon, geometry를 사용했다. `integrate_se2`, `swept_clearance`, `corridor_clearance`를 재사용하여 command를 고정했다. Sample 0만 실제 실행이고 **1–7은 전부 미실행 counterfactual**이다. B51 초기 clearance는 4.417414 cm, **B52는 1.918981 cm로 이미 2cm 미달**이므로 초기 상태를 포함해 판정했다.

## 분포와 sample 0

| 집계 (각 8 samples) | FRESH 51 | FRESH 52 |
|---|---:|---:|
| Native full 안전 | **7/8** | **0/8** |
| Native index 2 prefix 안전 | **7/8** | **0/8** |
| Observation origin 포함 prefix 안전 | **7/8** | **0/8** |
| PD rollout geometric overlap 없음 | **8/8** | **5/8** |
| PD rollout 2cm margin + corridor 충족 | **3/8** | **0/8** |
| 우회전 / 좌회전 / 직진 | **6 / 2 / 0** | **4 / 4 / 0** |
| Native full / PD rollout corridor containment | **8/8 / 8/8** | **8/8 / 8/8** |

51 sample 0: `(v,w)=(.2,−.4)`, native full/prefix clearance **2.490854 cm**, 실제 rollout **1.918788 cm**로 margin 미달/overlap 없음. 52 sample 0: `(.2,+.4)`, full **−7.184310 cm**, prefix **−3.802845 cm**, 실제 rollout **−.126189 cm**로 overlap. 두 sample 0의 원본 PD, native full/prefix/origin-prefix 값은 기존 분석과 일치했고, 저장된 pose 및 static/dynamic swept clearance 재현의 **최대 오차는 각각 0**이었다.

51에서 **sample 4·6·7**은 native full/prefix와 짧은 PD 실행 모두 안전했다. 각 command는 `(.176267,−.4)`, `(.122251,−.4)`, `(.104971,+.4)`이고 rollout clearance는 **2.198616 / 2.835484 / 2.868918 cm**다. Sample 0·2·3·5는 서로 다른 native 경로여도 clipping 후 같은 `(.2,−.4)`를 내므로 실제 구간의 margin도 동일하게 미충족했다. Native 안전성만으로 실제 PD 안전성을 대체할 수 없다.

## 52에서 sample 0보다 안전한 후보가 있었는가?

**2cm를 충족하는 후보는 없었다. 다만 이 짧은 구간의 충돌을 피하는 대안은 1·4·5·6·7번이었다.** 아래 minimum은 footprint를 반영한 값이며 모두 cm 단위다.

| 52 sample | `(v,w)` m/s,rad/s | Native full | Prefix / origin-prefix | PD swept 하한 | PD overlap |
|---|---|---:|---:|---:|---|
| 0 (실제 선택) | `(.200000,+.4)` | −7.184310 | −3.802845 | −.126189 | 있음 |
| 1 | `(.200000,−.4)` | +.964232 | +.964232 | +.136918 | 없음 |
| 2 | `(.200000,+.4)` | −2.558745 | −1.541917 | −.126189 | 있음 |
| 3 | `(.200000,+.4)` | −4.656425 | −1.639891 | −.126189 | 있음 |
| 4 | `(.112362,−.4)` | +1.957811 | +1.957811 | +.917798 | 없음 |
| 5 | `(.149009,−.4)` | +1.984963 | +1.984963 | +.591261 | 없음 |
| 6 | `(.200000,−.4)` | +.818917 | +.818917 | +.136918 | 없음 |
| 7 | `(.141367,+.4)` | −1.305879 | +.152441 | +.473384 | 없음 |

51의 실제 우회전과 같은 회전 부호를 갖는 52 sample은 **1·4·5·6의 4개**다. Sample 7은 좌회전이지만 낮은 속도 덕분에 이 구간에서 overlap이 없다. 따라서 좌/우 부호만으로 안전한 회피를 판정할 수 없다. Native full 기준으로 52 sample **0·2·3·7은 geometric overlap**, **1·4·5·6은 overlap은 없지만 2cm margin 미달**이다. Tail만 unsafe인 경우(7)와 prefix부터 overlap인 경우(0·2·3)를 구분한다.

## 해석과 한계

**51에서는 sample selection만으로 이 짧은 구간의 안전성을 높일 가능성이 있었다.** 그러나 이는 exact geometry를 이용한 offline oracle 판정이며 온라인 선택 정책을 구현·검증한 것이 아니다. 52에서는 8개 전반의 native margin 미충족과 이미 소진된 B52의 여유 때문에 sample 선택만으로 요구한 전체 구간 2cm 기준을 만족시킬 수 없다. Sample 0 대신 다른 sample을 선택하면 단기 collision outcome은 달라질 수 있지만, 충분한 safety margin이나 closed-loop 성공을 보장하지 않는다.

따라서 앞선 시점의 sample 선택·단순 감속 등 안전 보정을 검토할 근거는 있다. [기존 B51 speed-only feasibility](B51_SPEED_CORRECTION_FEASIBILITY.md)와도 일관된다. 추가 trajectory correction의 필요성이나 Graph의 우월성이 입증된 것은 아니다. 서로 다른 prediction의 같은 sample index를 대응 경로로 취급하지 않았고, 회전 부호와 실제 통과 측면을 동일시하지 않았다. Observation/history와 noise/DDPM seed(51:203/204, 52:205/206)가 다르며, 한 쌍의 8개 표본 분포를 일반적인 모델 성능으로 확대하지 않는다.

결과는 [16개 sample CSV](../research/results/isaac6_sample_comparison_20261019/samples_51_52.csv)에 local waypoint, 원본 PD, world selected point, 세 native safety 검사, corridor, swept bound/overlap, 종료 pose를 저장했다. CSV SHA-256: `bcfa7262504f50e6cc5374cd4d1e6cd511aecc8c3aaa53ab90b255b72f16bb73`.

입력 NPZ SHA-256은 51 `b1856a630fac405d41c8e2d52ef363818e4c9d16a76ce97c0dc98cdcba265062`, 52 `5621d69d94875dc5e943b874557ee987fa7c2f8dfc07209fd86db601c93c8afe`. 기존 manifest의 **257개 run inputs**, 이전 분석 및 보호 source 9개 hash가 유지됐다. 새 inference/navigation/시각화/test/reranking/controller 변경/Graph/새 correspondence 없이 CSV 하나와 본 보고서만 추가했다.
