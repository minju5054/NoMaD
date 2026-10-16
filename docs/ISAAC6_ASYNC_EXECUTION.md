# Isaac Sim 6 asynchronous NoMaD action execution

**비동기 실행·soft real-time 계측: PASS. Navigation: FAIL, 첫 장애물 geometric collision.** 실제 GPU inference 도중 유효한 OLD command로 이동하는 것을 30회 확인했다. Runtime timeout은 자연 발생하지 않아 `NOT_EXERCISED`이며, 정확한 1초 경계와 zero-velocity 의미는 공식 ROSData와 synthetic clock test로 확인했다. 관측한 real-time 구간은 collision까지의 **8.458 s**이며 60초 지속 성능을 검증한 것은 아니다.

## 변경 및 실행

기준 `622d99fae814b5a1b6cb7a262ebf835e14bc36df`, branch `research/isaac6-async-execution`. [실행 전 protocol](ASYNC_EXECUTION_PROTOCOL.md)은 `0cd69f7`에 고정했다. 실행 코드 **`cef336f6143a36c6e85559213aacfae02b46020b`**, 실행 시작 시 clean tree였다. 기존 scene/start/goal/seed schedule/NoMaD/controller 설정을 유지하고 effective scenario의 `synchronous`만 false로 바꿨다. 정상 navigation **1회**, 기술적 재시도/성능 튜닝 **0회**다.

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV bash research/python.sh -m nomad_isaac.launch --asynchronous --scenario research/nomad_isaac/two_obstacles_scenario.json --output /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_two_obstacles_01
```

위는 실제 실행한 명령이며 해당 output은 이미 존재한다. Launcher는 기존 output 덮어쓰기를 거부한다. 새 주행을 추가로 실행하지 않았다.

- `async_core.py`: single outstanding request/result, 별도 IPC thread, 수신 timestamp 기반 waypoint validity, 다음 9 Hz tick에서 원본 PD 계산. 최초 수신 전 및 age>=1 s에는 zero velocity다. Point 0/index 2를 유지하고 8-point 순차 controller를 만들지 않았다.
- `async_runtime.py`: 독립 72 Hz SE(2) execution thread, fixed monotonic deadline pacing, main thread의 nominal 4 Hz RGB history/planning. Busy 시 request를 쌓지 않으며 history는 최신으로 유지한다. `receive_packet()`의 blocking은 IPC thread 안에만 남아 있다.
- 기존 worker에는 CUDA sync 종료인 `t_ready`, CPU output-ready, persistence-end timestamp만 추가했다. Model/infer/10-step sampling/normalization/scaling/공식 controller 수식은 그대로다.
- **Canonical SE(2) state가 실제 kinematic 실행 상태**다. Isaac/USD agent와 camera는 촬영 시작의 snapshot pose에서 실제 RGB를 렌더링하며, 촬영 중에는 그 USD pose를 고정한다. Kinematic 실행은 그동안 계속된다. 따라서 USD/PhysX 자체를 72 Hz로 돌렸다는 주장은 하지 않는다. Camera snapshot은 약 4 Hz, control 9 Hz, canonical integration 72 Hz다.

## 실제 측정

31 requests / 31 GPU inference / 31 receive / 31 switch, 77 controller refreshes, 610 pose rows가 저장됐다. 첫 waypoint 적용 t=1.111111 simulation s까지 pose 변화는 정확히 0이다. 이후 30 requests 모두 inference wall interval 내부에 완전히 들어가는 유효 OLD integration step에서 nonzero pose 이동이 있었다. [원본 tick 두 구간을 포함한 증거](../research/results/isaac6_async_20261016/old_motion_evidence.json).

| 측정 | Median | p95 | Max |
|---|---:|---:|---:|
| Warm inference, 첫 호출 제외 30개 (ms) | **29.020** | **30.882** | 31.996 |
| Observation capture-start→ready, 31개 (ms) | **68.167** | **130.512** | 300.288 |
| Observation capture-start→switch, wall (ms) | **138.530** | **194.272** | 360.999 |
| Observation pose→switch, simulation (ms) | 138.889 | 201.389 | 361.111 |
| Ready→complete packet receive (ms) | 2.059 | 2.486 | 18.428 |
| Receive→next controller tick (ms) | 40.222 | 96.439 | 96.953 |
| RGB render duration (ms) | 36.888 | 95.080 | 103.007 |
| Observation→request submit (ms) | 37.147 | 95.406 | 103.258 |
| Request submit→inference start (ms) | 1.856 | 2.249 | 6.333 |
| Inference 중 OLD 완전 tick 이동 거리 (m) | **0.002778** | 0.005556 | **0.005556** |
| 같은 OLD 구간의 yaw 변화 절댓값 (rad) | 0.004700 | 0.011111 | 0.011111 |
| Switch pose의 observation 대비 translation (m) | **0.021173** | 0.036103 | **0.036109** |
| Switch pose의 observation 대비 yaw 절댓값 (rad) | **0.033333** | 0.072222 | **0.072222** |

Cold inference는 **258.752 ms**다. OLD 이동 수치는 첫 inference를 제외하고, 양 끝 timestamp가 inference start/end 안에 있는 실제 72 Hz 구간만 합한 **보수적 직접 측정**이다. Inference 경계에 걸친 partial tick을 포함하지 않아 전체 inference 시간 동안의 이동량보다 작을 수 있다. Switch yaw median/max는 약 **1.910°/4.138°**다. 각 request의 t_obs/start/end/ready/receive/switch, 원본 observation/switch SE(2), OLD validity, timeout, selected point/command는 [timing CSV](../research/results/isaac6_async_20261016/request_timing.csv) 및 raw logs에 있다.

Waypoint timeout episodes **0**, expired control ticks **0**. Missing waypoint 정지는 실제 검증됐으나, 수신 후 1초 expiry는 이번 정상 주행에서 발생하지 않았다. Busy request skip **0**, missed capture slot **0**. 캡처 35장 중 history warmup 3장, request 사용 31장, 종료 부근 history-only 1장이다. Busy 중 queue를 추가하지 않는 동작은 synthetic IPC test로 검증했다. First cold inference 도중에도 RGB 촬영은 진행됐지만 해당 RGB가 완성될 때는 이전 result가 처리돼 busy skip이 필요하지 않았다.

## Real-time 및 clock 검증

| 측정 | 결과 |
|---|---|
| Simulation / 실제 실행 wall time | 8.458333333 / 8.458429215 s |
| Real-time factor | **0.999988664** |
| Pose deadline absolute error median / p95 / max | **0.09885 / 0.15299 / 1.22527 ms** |
| 1 tick(13.8889 ms)보다 늦은 pose update | **0 / 610** |
| 실제 pose 간 wall 간격 median / p95 | 13.88880 / 13.94051 ms |
| 실제 controller 간 wall 간격 median / p95 | 111.11589 / 111.95135 ms |
| Inference wall duration↔기록 sim duration 차이 p95 / max | **0.12365 / 0.48013 ms** |
| FRESH 첫 적용 tick 오류 / 누락 | **0 / 0** |

마지막 duration 비교는 실제 monotonic pose trace 사이의 **보간된 simulation time**에 기반한다. 서로 다른 clock 값을 직접 뺀 것이 아니며, waypoint intrinsic time을 만든 것도 아니다. 직접 OLD 이동 증거는 보간 없이 실제 pose intervals만 사용했다. Capture 시작 시 pose는 마지막 72 Hz 표본이므로 표본 age도 별도 기록했다(median 1.075 ms, max 14.743 ms). `t_ready`는 CUDA sync가 끝난 `t_infer_end`와 같고, 파일 저장/전송/수신은 별도 시간이다.

사전 soft real-time 기준(pacing p95<=1 tick, max<=4 ticks, real-time factor 오차<=2%, inference clock 대응 p95<=2 ticks)을 모두 만족했다. OS hard real-time이나 더 긴 주행의 deadline 보장을 주장하지 않는다.

## Navigation 및 synchronous baseline 비교

첫 장애물 geometric overlap이 **t=8.458333 s**에 검출돼 다음 integration 없이 중단했다. 최종 pose는 **(1.18006047, −0.11566335, −0.69650412 rad)**, 최소 goal 거리는 **3.32195371 m**, goal entry=false다. 첫 장애물 swept clearance 하한 **−0.000062402 m**, 상한 −0.000060473 m이므로 안전 기준 0.02 m 미달이고 실제 footprint overlap도 있다. Corridor 침범은 없고 두 번째 장애물에는 도달하지 않았다. 이는 원형 footprint/AABB geometric contact이며 PhysX 충돌이 아니다.

기존 planning diagnostic에서도 prediction **29**의 observation-anchored selected point가 clearance −0.004300 m로 overlap했고, prediction **30**은 +0.002237 m로 0.02 m margin에 못 미쳤다. 원본 waypoint/controller가 그대로 사용됐고 transport/frame 변조는 발견하지 못했다. Collision 결과를 지연만의 효과로 분리하는 실험은 하지 않았다.

기존 synchronous run은 재사용만 했다. **기존 t_obs는 RGB capture 후**, 이번 t_obs는 capture-start이므로 단순히 두 host-delay 컬럼을 같은 의미로 비교하면 안 된다. 아래 delay 비교는 양쪽 모두 **RGB 사용 가능 시점부터** 계산했다. 기존 로그에는 정확한 capture-start가 없어 그것을 만들어내지 않았다.

| 측정 | 기존 synchronous | 새 asynchronous |
|---|---:|---:|
| 주행 관측 길이 / inference 수 | 60 s / 237 | 8.458 s / 31 |
| Warm inference median / p95(ms) | 29.594 / 32.386 | 29.020 / 30.882 |
| RGB available→ready median / p95(ms) | 31.329 / 40.313 | 31.240 / 33.593 |
| RGB available→switch median / p95(ms) | 36.238 / 44.022 | 73.204 / 129.538 |
| Inference 중 OLD 이동 | 0 m / 0 rad | 완전 tick 거리 median/max 0.002778/0.005556 m |
| Observation→switch translation median / max(m) | 0.005556 / 0.016667 | 0.021173 / 0.036109 |
| Observation→switch yaw 절댓값 median / max(rad) | 0.004666 / 0.033333 | 0.033333 / 0.072222 |
| Goal entry / 최소 goal 거리 | false / 0.66305 m | false / 3.32195 m |
| 첫 장애물 최소 clearance 하한 | +0.10384 m | −0.0000624 m |
| 장애물 결과 | 두 장애물 안전 통과 후 timeout | 첫 장애물 geometric collision으로 종료 |

Baseline은 wall보다 빠르게 실행됐고 inference 중 simulation이 정지했다. 관측 길이·실행 path·observation와 seed의 대응이 달라 위 표는 동일 상태에서의 causal latency 비교나 성능 benchmark가 아니다. 동일 scene/config라도 RTX RGB/goal의 pixel hash가 이전 run과 같지는 않으며, sampling 및 입력 차이의 영향도 분리하지 않았다.

## 검증·보존·남은 범위

Synthetic scheduler/timeout/ordering/integration tests **5 passed**. 실제 31 outputs 모두 `(8,8,2)` float32 finite, raw→cumsum→metric→sample 0/index 2 exact equality, 원본 PD command 및 모든 pose 재적분 일치(최대 오차 0). World path는 observation pose anchor와 기존 planning 기록에 일치한다. 기존 clearance 함수로 모든 실행 arc를 재평가했다. Checkpoint state 645/645, parameter coverage 100%, missing/unexpected/mismatch 0이며 실제 GPU forward가 완료됐다.

실행 source 14개의 저장 hash와 commit을 확인했고, 기존 synchronous 입력/결과 **484개 hash 불변**이다. 원본 `train/`, `deployment/`, `nomad_preflight`, common coordinate/clearance 및 scenario source 변경 없음. Package/system Python/CUDA/driver/Isaac/.venv 변경 없음. 기존 shader 준비 단계의 transient renderer-step 오류는 있었지만 RGB gate 이후 기술적 중단은 없었다.

Raw run: `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/async_two_obstacles_01/`. 첫 offline report를 보존하고 clock 정의를 맞춘 비교 컬럼을 추가한 최종 report는 `async_two_obstacles_01_validation_v2/`에 저장했다. 이는 새 주행이나 threshold 변경이 아니다. [작은 summary](../research/results/isaac6_async_20261016/summary.json) · [검증 기록](../research/results/isaac6_async_20261016/review.json) · [입력 hash](../research/results/isaac6_async_20261016/input_hashes.json).

미검증: 자연 발생 timeout/장시간 worker busy, 60초 이상의 real-time 안정성, 원본 ROS/topomap 전체 실행, PhysX dynamics. 별도 Graph/correspondence/latency injection/benchmark/MP4/GUI 구현·실행은 하지 않았다. 이번 PASS는 **실제 RGB와 GPU inference를 연결한 paced kinematic OLD/FRESH 실행·타이밍 의미**에 대한 것이며, navigation 안전성 PASS가 아니다.
