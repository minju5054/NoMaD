# OLD50 → FRESH51: 최소 SE(2) Graph offline 실험

2026-10-19. **수치 최적화는 수렴했지만 H1 실행 안전성 개선에는 실패했다** (`CONVERGED_BUT_H1_SAFETY_FAILED`). GRAPH는 boundary mismatch와 native polyline clearance를 개선했으나, 원본 PD clipping 때문에 RAW·RIGID·GRAPH 모두 동일한 `(0.2, −0.4)`를 출력했다. 최소 swept clearance는 모두 **1.918788 cm**, 요구 2 cm에 **0.812119 mm 미달**이다. 이 H1에는 geometric overlap이 없다.

기준 `c6a72d53cc34a5160d42f0114939943d7c93a223`, 별도 브랜치 `research/isaac6-minimal-se2-graph`. 입력은 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/old_rollout_obstacle_01/`. Protocol을 **`7ecee7f`**, 구현을 **`227c9d4`**에 먼저 commit하고 **최적화 1회**만 수행했다. 이후 변경은 그림 설명과 결과 기록뿐이다. 새 navigation/inference, parameter sweep/restart, 환경 설치, 원본 controller/model 수정은 없다.

## 입력과 graph

FRESH51 sample 0의 원본 metric XY를 observation pose `(2.079756858, .023472090, −.905813766)`로 world 변환했다. B51은 실제 tick 1000, `13.888888889 s`, `(2.097864810, −.001133875, −.966924877)`로 고정했다. 초기 dynamic clearance는 **4.417414 cm**. Static box 2개와 tick 970에 출현한 dynamic box의 정확한 geometry, radius .09 m 및 요구 clearance .02 m를 재사용했다.

Editable node는 **8개 SE(2) future pose = 24 variables**, B51은 고정 node다. Node 0–6 heading은 outgoing segment tangent, 마지막 node는 마지막 incoming tangent로 초기화했다. 최초 7 segments는 모두 기존 최소 길이 .02 m 이상(최소 .029162 m)이었고, 최적화 후에도 유효했다. 이것은 **보조 heading이며 NoMaD native yaw나 intrinsic timestamp가 아니다**. OLD50은 실제 이전 prediction임을 확인하고 그림의 맥락으로만 사용했다. 실제 OLD 실행을 요약한 B51이 boundary이며 OLD/FRESH 동일 index correspondence factor는 만들지 않았다.

`Fj`는 원본 observation-anchored pose, `Zj = Fj⁻¹ Fj+1`이다. SE(2) logarithm은 rotation뿐 아니라 `V(θ)⁻¹`로 translation도 변환한다. 목적함수는 `0.5 Σ r²`이며 scalar residual은 100개다.

| Factor | Residual / 고정 scale |
|---|---|
| FRESH prior (8개) | `Log(Fj⁻¹ Xj)`; XY σ=.02 m, yaw σ=15° |
| Relative pose (7개) | `Log(Zj⁻¹ (Xj⁻¹ Xj+1))`; XY σ=.01 m, yaw σ=10° |
| Boundary (1개) | `Log(B51⁻¹ X0)`; XY σ=.01 m, yaw σ=10° |
| Heading/길이 일치 | node yaw−실제 XY tangent, σ=10°; segment 길이 .02 m 미달 hinge, σ=.005 m |
| Native obstacle safety | 7 future segments와 B51→X0를 3개 AABB와 검사; `max(0,.025−clearance)/.002` |
| Controller-aware safety | world index 2를 B51 local로 표현→원본 PD→16 tick 고정 command; 각 장애물의 최소 swept clearance에 같은 hinge |
| Corridor | B51/future points 및 PD arc의 containment; .005 m target, σ=.002 m |

Safety target **.025 m**는 soft penalty의 사전 고정 5 mm reserve이며 **pass threshold는 .02 m**다. 강제 안전 제약은 아니다. `integrate_se2`, `original_controller`, `swept_clearance`, `corridor_clearance`, `path_safety`를 그대로 재사용했다.

기존 CPU 환경(SciPy **1.11.4**, 시스템 Python **3.12.3**, NumPy **1.26.4**)을 사용했다. `least_squares(method='trf', jac='3-point', ftol=xtol=gtol=1e-8, max_nfev=200)`를 원본 FRESH pose의 zero increment에서 한 번 실행했다. Scale은 pose당 `[.02 m,.02 m,15°]`, bounds 없음, linear loss다. 가중치나 초기화를 결과에 따라 조정하지 않았다.

## 동일 B51에서 RAW / RIGID / GRAPH

- **RAW:** 원본 observation-anchored XY와 원래 observation-local index 2 PD input을 유지한다.
- **RIGID:** `A = B51 F0⁻¹`, `Xj = A Fj`. 첫 future pose의 XY/derived heading을 B51에 맞추는 명시적인 correction으로 모든 상대 SE(2) transform을 보존한다. 원본 anchor 데이터는 덮어쓰지 않는다.
- **GRAPH:** 위 factor로 8 future poses를 편집한다. RIGID/GRAPH의 PD input은 수정된 world index 2를 **B51 local frame**으로 표현한 값이다. 이를 원본 NoMaD 실행 방식이라고 주장하지 않는다.

H1은 사전 지정 **16/72 = .222222222 s**, `13.888888889→14.111111111 s`. 모든 방법은 동일 B51/geometry에서 한 번 계산한 command를 고정한다. 원본 PD 수식의 DT=.25 s 및 속도 제한을 바꾸지 않는다.

| 항목 | RAW | RIGID | GRAPH |
|---|---:|---:|---:|
| Optimizer | 해당 없음 | 해당 없음(닫힌 형태) | `ftol` 종료, status=2 |
| 동일 graph 목적함수 비용 | 4.717882 | 8.315142 | **4.418301** |
| Boundary 위치 차이 (mm) | 6.866 | **0** | **2.342** |
| Boundary 실제 tangent 방향 차이 (°) | 7.172 | **0** | **2.829** |
| 원본 대비 XY RMS / max (mm) | 0 / 0 | 15.796 / 28.373 | **1.870 / 4.553** |
| 원본 대비 tangent heading RMS (°) | 0 | 7.172 | **1.708** |
| 상대 transform translation RMS (mm) / yaw RMS (°) | 0 / 0 | ≈0 / ≈0 | **.4465 / .9001** |
| Native full / index 2 prefix clearance (cm) | 2.490854 / 2.490854 | 2.335115 / 2.335115 | **2.634236 / 2.634236** |
| Controller input `(dx,dy)` (m) | `(.080564,−.018535)` | `(.055040,−.014379)` | `(.051358,−.015473)` |
| PD `(v,w)` (m/s, rad/s) | `(.2,−.4)` | `(.2,−.4)` | `(.2,−.4)` |
| H1 swept clearance (cm) | **1.918788** | **1.918788** | **1.918788** |
| 2 cm margin / geometric overlap | **미충족 / 없음** | **미충족 / 없음** | **미충족 / 없음** |
| 이동 거리 (cm) | 4.444444 | 4.444444 | 4.444444 |

Native full은 원점 없이 node 0–7, prefix는 node 0–2다. B51→prefix connector 포함 검사도 별도로 저장했으며 같은 minimum이다. 세 native 경로 모두 .02 m와 corridor containment를 만족했다. 세 H1 끝 pose는 모두 `(2.121443741,−.038790779,−1.055813766)`, swept upper bound는 .019189810 m, corridor clearance는 1.371207292 m다. **Native polyline safety와 실제 PD safety는 다르다.**

GRAPH는 `nfev=5, njev=5`(finite-difference 포함 residual 호출 245회), CPU wall .659856 s에 종료했다. 최종 residual L2 **2.972642**, max **2.906059**, gradient optimality **2.7951e−5**다. `ftol` 수렴은 모든 factor 만족을 뜻하지 않는다. GRAPH auxiliary pose heading의 boundary mismatch는 3.230°, 실제 XY tangent mismatch는 2.829°이며, 전체 node에서 둘의 최대 불일치는 .402°다. 목적함수 비교는 공통 corrected-point controller semantics이고, 실제 RAW 명령과 rollout 평가는 원래 local input을 사용했다. 이번에는 양쪽 command가 같다.

## 안전성이 개선되지 않은 직접 원인

원본 PD는 이 입력들에서 `v=clip(dx/.25,0,.2)`, `w=clip(atan(dy/dx)/.25,−.4,.4)`다. RAW/RIGID/GRAPH의 clipping 전 `(v,w)`는 각각 `(.322255,−.904530)`, `(.220162,−1.022154)`, `(.205432,−1.170504)`다. **모두 v/w가 포화되어 실제 command가 완전히 같았다.**

GRAPH의 B51-local dx=.051358 m는 속도가 감소하기 시작하는 .05 m보다 크다. Local XY 각 축 ±1 μm 확인에서도 세 방법 모두 command 변화 0이었다. 따라서 이 해 부근의 controller-aware clearance residual은 국소적으로 평평하다. 최종 비용 중 **4.222590/4.418301**이 그대로 남은 controller safety penalty다. 해당 factor를 실제 포함했어도, clipped controller를 통과하는 단일 국소 least-squares가 안전한 command 영역을 찾는다는 보장은 없다. 추가 초기화·가중치 tuning·optimizer 변경은 수행하지 않았다.

## 기존 단순 baseline 참고값

아래는 기존 CSV의 **H1 결과**이며 이번에 다시 최적화하거나 rollout하지 않았다. Sample 4/6/7은 온라인 선택 정책이 아닌 exact-geometry offline oracle 참고값이다.

| 기존 방법 | `(v,w)` | H1 minimum clearance (cm) | 2 cm 충족 |
|---|---|---:|---|
| SPEED-LIMITED 51 | `(.18,−.4)` | **2.154597** | 예 |
| FRESH51 sample 4 | `(.176267,−.4)` | **2.198616** | 예 |
| FRESH51 sample 6 | `(.122251,−.4)` | **2.835484** | 예 |
| FRESH51 sample 7 | `(.104971,+.4)` | **2.868918** | 예 |

작은 shape 수정으로 boundary/prior/relative-pose factor의 기하학적 절충을 수행하는 mechanism은 확인했다. 그러나 **실행 안전성의 추가 이점은 없었으며 기존 감속/다른 sample의 H1 안전 결과에도 미치지 못했다**. 이 실패가 Graph 방식 전체의 불가능성이나 새로운 Graph 기법의 필요성을 증명하지 않는다. 정확한 geometry, 고정 goal adapter, 한 boundary·sample·짧은 horizon의 oracle 실험이다. OLD/FRESH correspondence, 온라인 geometry 인지, 다음 prediction 적용, 전체 navigation 및 VLA 성능 개선은 미검증이다.

## 보존과 검증

RAW의 **17개 pose/16개 interval**을 실제 H1 trace, static/dynamic swept clearance와 corridor에 대조했다. 최대 pose·clearance 오차 모두 **0**. SE(2) log/inverse frame 검증 통과, RIGID 상대 transform 최대 오차 **4.44e−16**. 기존 raw **257개**와 보호 source **9개** hash 일치. Prediction 52/53·B51 이후 실제 주행은 optimization/parameter 선택에 사용하지 않았고, H1 실제 trace와 기존 baseline 참고값은 solve 완료 후 읽었다.

결과: [summary JSON](../research/results/isaac6_minimal_se2_graph_20261019/summary.json), [3방법 CSV](../research/results/isaac6_minimal_se2_graph_20261019/comparison.csv), [비교 XY 그림 한 장](../research/results/isaac6_minimal_se2_graph_20261019/comparison.svg). 같은 폴더에 frozen protocol, input hashes, solver residual 및 clipping 검증을 보존했다. 그림의 세 H1 rollout은 **실제로 겹친다**. RAW만 기록된 실행이며 RIGID/GRAPH는 미실행 counterfactual이다.

실제 분석 명령(기존 output이 있으면 덮어쓰지 않고 중단):

```bash
PYTHONPATH=research MPLCONFIGDIR=/tmp/nomad-se2-graph-mpl /usr/bin/python3 -m nomad_isaac.minimal_se2_graph --run ../artifacts/isaac6/old_rollout_obstacle_01 --out research/results/isaac6_minimal_se2_graph_20261019
```
