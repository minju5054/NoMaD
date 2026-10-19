# Isaac Sim 6: 공식 NoMaD Topomap 연결

2026-10-19 KST. 기준 `c6a72d53cc34a5160d42f0114939943d7c93a223`, 별도 branch `research/isaac6-topomap`. 기존 fixed-goal 성공 run `async_wide_wall_01`은 재실행하지 않았다. 원본 model/checkpoint, preprocessing, normalization/scaling, sample 0/index 2, 원본 PD 및 async execution의 의미를 유지하면서 RGB Topomap localization/local subgoal 선택만 추가했다.

**Topomap 기술 연결은 PASS, 단일 navigation은 실패했다.** 첫 장애물은 왼쪽으로 통과했지만 두 번째에는 도달하지 못했고, **13.902778 s에 왼쪽 corridor footprint 침범으로 중단**했다. Topomap 간격/threshold/seed를 바꾸거나 재시도하지 않았다.

## Reference Topomap과 실행 전 검증

Reference 실행 SHA는 `fb9bf2253044be477873aa113a19899f479af248`. 저장된 1,771개 72 Hz pose에서 tick **0,72,…,1728,1770**, simulation **0,1,…,24,24.583333 s**를 선택해 실제 Isaac RGB **26장**을 새로 렌더링했다. 시작 pose와 마지막 기록된 goal-entry pose `(4.221781760,−.105946843,.149874675)`를 포함하며, 마지막 이미지를 임의의 정확한 goal pose로 대체하지 않았다.

두 static box와 corridor/camera 설정은 동일하고 dynamic obstacle은 없다. 기존 `build_scene`/RGB capture/main-thread pose setting을 재사용했으며, 이 단계의 새 navigation/inference는 **0회**다. Node 순서·source row/time·world pose·PNG SHA-256·decoded RGB SHA-256·reference/render SHA를 [manifest](/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/topomap_reference_01/topomap/manifest.json)에 보존했다. PNG와 원본 RGB가 일치했고 USD pose 최대 오차는 **3.33e−16**이었다. 시작·장애물 부근·종료 RGB를 확인했다. Initial shader 준비 중 renderer-step 오류 6개는 원본 로그에 남겼고 이후 RGB/frame gate를 통과했다.

- Reference rendering: `../artifacts/isaac6/topomap_reference_01/`; protocol/runtime commit **`5b05a1c`**.
- GPU equivalence: `../artifacts/isaac6/topomap_gpu_validation_01/gpu_equivalence.json`.
- 새 navigation: `../artifacts/isaac6/topomap_static_01/`; clean execution commit **`fd125a4`**.

공식 `navigate.py`의 AST 선택식과 threshold/tie/end-clamp/backtracking을 비교하고 기존 async/geometry tests를 재사용해 **17 passed**. 실제 GPU에서는 공식 batched vision encoder/distance head, single-goal encoder와 distance, 동일 condition·initial noise·DDPM seed의 normalized diffusion/cumulative/metric/selected waypoint가 모두 **bitwise equal, 최대 오차 0**이었다. Topomap inference 한 번의 호출 수는 **vision encoder 1 / distance head 1 / noise predictor 10**이다. Validation의 RGB history는 map node 0–3이며, 실제 navigation의 4 Hz history와 구분한다. 검증을 위해 실행한 GPU calls를 navigation run으로 집계하지 않는다.

## 공식 선택 로직과 adapter 차이

`closest_node=0`, 최종 node=25로 시작한다. 후보 범위는 공식 NoMaD branch 그대로 `start=max(closest−4,0)`, `end=min(closest+4+1,goal_node)`의 **inclusive start…end**다. 중간에서는 최대 **10개** 후보이며 대칭 9개로 바꾸지 않았다. 후보마다 동일 RGB history와 해당 node 이미지를 함께 vision encoder에 넣고 distance head를 평가한다. `argmin`으로 closest를 갱신하고, 최소 distance가 **3 미만**이면 그 다음 후보, 아니면 가장 가까운 후보를 local subgoal로 선택한다. 마지막 후보를 넘지 않도록 clamp한다. 후보마다 diffusion을 실행하지 않고 **선택 condition에만 기존 10-step diffusion 1회**를 수행한다.

Encoder는 공식 goal-conditioned branch의 grad-enabled scope를 유지했다. 원본 NoMaD/단일-goal `native.infer`는 수정하지 않았으며 새 selected-condition decoder를 동등성 검증했다. Worker가 보유하는 선택 입력은 RGB·node 순서·이전 closest뿐이다. Map의 world pose나 실제 agent pose로 node를 선택하지 않는다. Candidate range/scores, closest/subgoal, backward/update flag, selection monotonic time, image hashes가 worker→receive→switch 로그에 보존된다.

ROS Topomap 파일 로딩 대신 manifest/PNG를 쓰고, 원래 두 process/IPC를 유지했다. Topomap mode에서는 최종 fixed-goal RGB를 worker로 전송하지 않는다. 기존 `goal.png`는 camera gate용 진단 이미지이며 policy goal은 각 결과에 기록된 selected subgoal image다. 모든 실제 observation RGB를 추가 저장해 worker 입력 history hash를 독립 검증한다. Whole-trajectory 실행, smoothing, reranking, recovery, pose re-anchoring은 없다.

`closest_node==25`는 별도 topology flag일 뿐이며 **종료/성공은 기존 world XY goal 0.30 m 기준**이다. 원본의 distance score를 metric 거리로 해석하지 않는다. 1초 map 간격과 learned temporal-distance scale의 일치는 별도 calibration 없이 기본 threshold=3으로 고정했다.

## 고정한 단일 주행 조건

Start `(0,0,0)`, world goal `(4.5,0,0)`. Obstacle1 center `(1.5,0)`, size `(.4,.5,.8)` m; obstacle2 center `(3,.75)`, size `(.5,1.5,1)` m. Radius .09 m, required clearance .02 m, simulation timeout 60 s. 기존 observation 4 Hz/controller 9 Hz/integration 72 Hz, 1초 receive-based timeout, max v=.2 m/s/w=.4 rad/s, seed `101+2k`/DDPM `+1`, sample 0/index 2 및 soft real-time pacing을 유지했다. 추가 latency는 0 ms다. 실패해도 map 간격·threshold·seed를 바꾸거나 재시도하지 않는다.

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV bash research/python.sh -m nomad_isaac.launch --asynchronous --topomap /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/topomap_reference_01/topomap/manifest.json --scenario research/nomad_isaac/two_obstacles_wide_wall_scenario.json --output /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/topomap_static_01
```

기존 경로는 재사용할 수 없으며 launcher가 overwrite를 거부한다. 기존 Isaac 설치·시스템 Python/CUDA/driver·가상환경을 변경하지 않았다.

## 실제 단일 주행 결과

**52 inference / 52 receive / 52 switch**, 실제 pose 1,002개. 모든 후보 범위·distance argmin·threshold·subgoal clamp·backward flag·selected image hash를 다시 계산해 공식 규칙과 일치함을 확인했다. 실제 저장 RGB로 모든 worker input history를 복원해 hash를 검증했다. Raw normalized diffusion→cumsum→metric→sample0/index2와 원본 PD command가 정확히 일치했고, observation pose 기반 world 변환도 일치했다. 모든 pose integration 재계산 최대 오차 **0**, corridor 계산 오차 **0**이며 swept obstacle clearance도 재검증했다.

| 항목 | 기존 fixed-goal reference | 새 Topomap 주행 |
|---|---:|---:|
| 목표 진입 / 최소 목표 거리 | **성공 / .297708 m** | **실패 / 2.849002 m** |
| 종료 시각 / 원인 | 24.583333 s / goal entry | **13.902778 s / corridor footprint stop** |
| 첫 장애물 통과 | 왼쪽, 11.319444 s | **왼쪽, 11.722222 s** |
| 두 번째 장애물 통과 | 오른쪽, 20.138889 s | **미도달** |
| 장애물 1 / 2 최소 swept clearance | .069630 / .082836 m | **.432678 / .634763 m** |
| Static box geometric overlap | 없음 | 없음 |
| Corridor 최소 clearance 하한 | +.790389 m | **−.001509 m** |
| Request / switch | 95 / 94 | **52 / 52** |
| Warm inference median / p95 | 29.187 / 31.903 ms | **36.579 / 52.610 ms** |
| Observation→switch median / p95 | 138.283 / 176.113 ms | **138.291 / 193.967 ms** |
| 첫 적용 이후 실제 waypoint 적용 빈도 | 4.005 Hz | **3.991 Hz** |
| 적용 간격 median / p95 | .222222 / .333333 s | .222222 / .333333 s |
| Timeout / busy skip / missed capture | 0 / 1 / 0 | **0 / 1 / 0** |

Warm latency는 첫 request를 제외한 **worker inference 구간의 monotonic wall-time**이며 preprocessing/encoder/distance/decoder/action 처리를 포함한다. 순수 CUDA kernel time으로 해석하지 않는다. Topomap의 후보 encoding/selection median/p95는 **17.881/34.113 ms**, diffusion/action은 **17.815/18.932 ms**였다. 다른 전체 주행의 RGB·관측 시점·seed와 observation의 대응이 달라졌으므로 navigation 차이를 Topomap 또는 latency만의 paired causal 효과로 주장하지 않는다.

최종 pose는 **`(2.025235709,1.411507114,.740370522)`**. Radius .09 m를 포함한 footprint는 `y=1.5` 왼쪽 벽 경계를 실제로 **1.507114 mm** 넘었다. 72 Hz 첫 위반 interval에서 기존 stop rule이 작동했다. Static boxes의 2 cm margin은 충족했지만 **corridor containment가 실패했으므로 전체 obstacle-avoidance 성공이 아니다**. PhysX collision을 주장하지 않는다. 첫 obstacle 통과 pose의 y는 1.067988 m로 reference의 .385653 m보다 왼쪽에 치우쳤다.

Soft real-time 검증 PASS: RTF **.999993906**, pacing absolute error p95/max **.145488/1.293862 ms**, inference wall→sim mapping error p95 **.049799 ms**, 다음 유효 controller tick 전환 오류 0. 첫 waypoint 전 정지와 유효 OLD의 inference 중 이동도 확인했다. 자연 timeout은 0회라 실제 timeout 상황은 이번 run에서 `NOT_EXERCISED`이며 기존 synthetic test가 경계 의미를 검사했다. 단순한 IPC 정지·timeout·실행 빈도 붕괴로 인한 실패 근거는 없다.

## Node 진행과 prediction 변화

최대 closest/subgoal은 **11/11**, 마지막 closest는 **7**, goal node **25**에 도달했다는 topology flag도 한 번도 발생하지 않았다. Subgoal 선택/갱신 **19회(초기 선택 포함)**, closest 역방향 이동 **5회**, subgoal 역방향 이동 **6회**였다.

| Request ID | 실제 switch t | closest 변화 | 선택 subgoal | 최소 learned distance | 실제 w |
|---|---:|---|---:|---:|---:|
| 27 | 7.888889 s | 7→7 | 8→7 | 5.2114 | −.057270→+.270093 |
| 34 | 9.666667 s | 9→9 | 9→9 | 9.5933 | −.225096→+.4 |
| 42 | 11.666667 s | **11→7** | 11→7 | 12.3730 | +.4 유지 |
| 44 | 12.111111 s | **7→3** | 7→3 | 10.9819 | +.4 유지 |
| 51 | 13.888889 s | 3→7 | 3→7 | 10.0893 | −.239760→−.4 |

ID27처럼 closest가 같아도 score가 3 이상이면 공식 규칙상 다음 node 대신 closest 자체를 선택할 수 있다. 모든 위 선택은 기록된 후보 점수에 따른 것이며 pose oracle을 쓰지 않았다. 후반의 높은 score, node 후퇴 및 reference route 이탈은 관찰됐지만 distance-head 오류·domain mismatch·sampling의 기여를 분리해 입증한 것은 아니다.

사전 정의한 첫 장애물 부근 `B.x∈[1,2]`에서 26 applied pairs 중 **8개**의 w 부호 반전이 관찰됐다: FRESH **27,29,34,35,36,37,38,46**. 전체는 **13회**다. 같은 subgoal을 유지한 ID34·36·37에서도 반전이 있어 node 변경만으로 모든 steering 변화를 설명할 수 없다. 이 구간의 observation-anchored selected-world-target revision median/p95/max는 **.049861/.083270/.084121 m**였다. 이것은 **제어 target 변화량**이며 다른 prediction의 index 2를 같은 물리적 correspondence라고 간주한 trajectory RMSE가 아니다. Reference의 같은 X 범위에서는 반전 1회였으나 주행 조건이 paired가 아니며, 작은 w 부호 변화까지 포함한 서술 통계다. 두 번째 장애물 부근 `[2.5,3.6]`에는 도달하지 않아 평가 표본이 없다.

## 판정·보존·다음 단계

**공식 Topomap localization/local subgoal 선택, 단일 selected-condition diffusion 및 비동기 controller 연결은 기술적으로 검증됐다.** 반면 이 map/scene/기본 threshold에서 정적 목표 도달은 확보하지 못했다. 따라서 같은 OLD 기반 sudden-obstacle을 연결할 기술적 기반은 있지만 **성공한 정적 Topomap baseline을 전제로 한 후속 비교를 시작할 상태는 아니다**. Map 간격과 learned distance scale, reference route에서 벗어난 시점의 RGB/localization 및 prediction 변화가 남은 uncertainty다. 새 실험이나 조정은 자동으로 진행하지 않았다. Dynamic avoidance 또는 Graph 필요성은 판단하지 않았다.

실행 commit은 clean `fd125a493e7ff3523d0cd10dec6ef094ed7a1f51`. 실행 후 source 변경은 offline report/그림뿐이며 runtime source hashes가 일치한다. Official train/deployment, `native.py`, PD, coordinate/clearance/async core 및 scenario는 기준 커밋과 동일하다. Checkpoint SHA-256도 기존 reference와 같다. Reference **203개**, 기존 OLD-rollout **257개**, 기존 validator의 synchronous baseline **484개** input hashes가 유지됐다. 새로운 모든 raw/derived와 RGB는 별도 run 폴더에 보존했다. Navigation의 초기 renderer-step 오류 5개도 남겼으며 이후 RGB gate와 정상 bounded 실행을 완료했다.

작은 결과: [summary JSON](../research/results/isaac6_topomap_20261019/summary.json), [node pose/hash CSV](../research/results/isaac6_topomap_20261019/topomap_nodes.csv), [모든 후보 점수·선택 CSV](../research/results/isaac6_topomap_20261019/topomap_selection.csv), [Topomap node와 실제 XY 경로 그림](../research/results/isaac6_topomap_20261019/topomap_navigation.svg), [보존·최종 검증](../research/results/isaac6_topomap_20261019/review.json). 상세 기존 runtime 검증은 `../artifacts/isaac6/topomap_static_01_validation/runtime_validation/`에 있다. 이 범용 validator의 legacy 설명 중 Topomap 제외 문구는 해당 timing validator의 범위를 뜻하며, Topomap은 별도 report의 GPU/selection/RGB 검사로 검증했다.
