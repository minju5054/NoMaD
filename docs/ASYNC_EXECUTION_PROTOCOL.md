# Asynchronous execution: 실행 전 고정 사항

기준 `622d99fae814b5a1b6cb7a262ebf835e14bc36df`, 기존 `two_obstacles_scenario.json`의 scene/start/goal/seed schedule/model/controller를 유지한다. 기존 synchronous raw run은 수정·재실행하지 않는다. 새 async bounded run 한 번이며 navigation 실패로 재시도/조건 변경하지 않는다.

공식 `navigate.py`는 image callback으로 최신 history를 유지하고, nominal 4 Hz planning thread에서 한 번에 한 inference를 실행한다. `pd_controller.py`는 독립된 9 Hz loop이며, `ros_data.py`의 `is_valid`는 **수신 후 time_waited < 1 s**다. 처음에는 valid waypoint가 없어서 0 velocity다. 여기서는 ROS 없이 동일한 2D point/controller와 수신-timeout 의미를 재현한다. Original topomap/ROS scheduler를 완전히 복제하는 것은 아니다.

렌더링 main thread, IPC 송수신 thread, 72 Hz canonical SE(2) execution thread를 구분한다. Isaac/USD API는 main thread만 호출한다. Canonical agent state가 실제 kinematic execution 상태이며, USD agent/camera는 nominal 4 Hz observation snapshot을 표시한다. 촬영 중 USD를 해당 pose에 고정하되 execution thread는 계속 진행한다. **USD/PhysX가 72 Hz로 독립 운동한다는 주장은 하지 않는다.** 기존 설정에서도 agent는 PhysX가 아닌 SE(2) kinematic 모델이었다. 실제 RTX RGB의 pose와 observation anchor를 저장하고 camera snapshot/display 주기와 control/integration 주기를 혼동하지 않는다.

모든 scheduling은 host monotonic ns 기준 고정 deadline이다. 72 Hz의 simulation time은 tick/72이며 실제 update monotonic time도 기록한다. Ahead-of-time 진행을 막기 위한 deadline wait만 사용한다. 인위적인 inference sleep/delay는 없다. 늦은 tick은 원래 deadline 기준 catch-up하며 jitter/late tick을 숨기거나 simulation dt를 변경하지 않는다. 사전 numerical real-time 기준은 `async_protocol.json`에 고정했다: pose tick pacing absolute error p95<=1 tick, max<=4 ticks, 전체 real-time factor 오차<=2%, inference interval wall→기록 sim time 대응 오차 p95<=2 ticks. 이는 soft real-time 계측 기준이며 hard real-time 보장이 아니다.

관측은 nominal 4 Hz에 최신 state snapshot을 받아 render한다. Capture start/end, pose sample time, render duration, request submit/send를 구분한다. Render가 다음 slot을 넘기면 누락 slot을 기록하고 과거 촬영을 한꺼번에 재생하지 않는다. Worker busy 시 현재 RGB를 history에 넣되 inference request는 skip한다. Queue는 request/result를 합쳐 하나만 outstanding으로 두고 전체 8-point trajectory를 실행 queue로 바꾸지 않는다. Request ID는 실제 제출 순서이며 seed=101+2*ID, DDPM seed=seed+1이다. 서로 다른 모드에서는 busy/처리시간 때문에 ID와 observation 시점 대응이 달라질 수 있다.

기존 socket NPZ protocol과 GPU worker를 재사용한다. Worker `t_ready`는 CUDA-synchronized inference end와 같은 시점이다. CPU copy/validation/persistence 완료 및 client receive는 별도다. Complete packet을 받은 host monotonic time부터 timeout이 시작되며, 다음 9 Hz controller tick에서 최신 point를 최초 적용한다. FRESH curve는 항상 observation pose로 world 변환한다. `t_switch`의 pose로 다시 anchor하지 않는다.

OLD 이동의 직접 증거는 inference start/end host time 안에 **양 끝점이 모두 있는 실제 72 Hz pose interval** 중 이전 valid waypoint로 수행한 nonzero 이동이다. 그 interval들의 거리/yaw 합을 보수적 실측량으로 보고한다. 추가로 기록된 wall-time pose 사이의 시간 대응으로 inference 양 끝을 보간한 sim duration/pose 변화는 derived estimate로 표시한다. 서로 다른 clock을 직접 빼지 않는다. 첫 inference는 OLD가 없어 이동 비교 분모에서 제외한다.

정상 주행에서 waypoint expiry가 없으면 runtime timeout은 `NOT_EXERCISED`로 기록한다. 최초 수신 전 정지는 별도 검증한다. Exact 1-second timeout, receive/switch 순서, one-inflight 및 OLD integration은 synthetic clock tests로 공식 ROSData/controller와 비교한다. Timeout을 유발하기 위한 지연은 넣지 않는다.

Async reproduction PASS는 실제 GPU inference, valid OLD의 동시 이동, 9 Hz/1 s 의미, pose/timing 정확성, 원본 output/controller 보존, pacing/latency mapping 기준을 모두 만족할 때만 부여한다. Navigation goal/collision 판정은 별도다. Collision monitor는 기존 geometric swept clearance를 재사용하고 contact 시 즉시 kinematic 실행을 멈춘다. Graph/correspondence/latency injection/benchmark/MP4/GUI는 추가하지 않는다.
