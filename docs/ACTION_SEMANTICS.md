# NoMaD native action 의미

기준: 공식 SHA `dca79815b704e5aa9c6bdc3082351f9e3b2848c2`, `train/config/nomad.yaml`. 아래 source 경로는 모두 이 SHA의 파일이다. **Normalized diffusion output, 역정규화된 누적 trajectory, metric 파생 trajectory는 서로 다른 값이다.**

## 입력과 history

`deployment/src/navigate.py:callback_obs`는 `context_size+1`장의 queue를 유지한다. 설정 `context_size=3`은 과거 3장 + 최신 1장으로, 총 4장이다. 새 이미지가 오면 가장 오래된 것을 버린다. model 입력은 oldest→newest 순서다. ROS callback 주기는 모델 자체의 timestamp가 아니며, `frame_rate=4`가 곧 callback image 간격이라고 보장되지 않는다.

`deployment/src/utils.py:transform_images`:

1. RGB PIL image를 받는다. 원본 `msg_to_pil`은 메시지 bytes를 그대로 읽으며 encoding별 RGB/BGR 변환을 보장하지 않는다. 이번 입력은 Pillow로 실제 RGB decoding했다.
2. native deployment는 `center_crop=False`. image를 PIL `resize([96,96])`로 직접 resize하므로 원본 비율을 정사각형으로 바꾼다. RGB에서 Pillow의 기본 resize resampling은 BICUBIC이다. training의 4:3 center crop 설명과 deployment 동작을 혼동하지 않는다.
3. `ToTensor`: uint8 `[0,255]` → float32 `[0,1]`, HWC → CHW.
4. ImageNet mean `[.485,.456,.406]`, std `[.229,.224,.225]`로 normalize.
5. 각 image에 batch dimension을 넣고 channel 축으로 concatenate한다.

## 단계별 contract

B=선택할 goal 후보 수, S=trajectory samples=8, T=8. 이번 실행은 이미 선택된 한 goal(B=1)을 입력한다.

| 단계 | Shape / dtype / 위치 | 의미 및 source |
|---|---|---|
| RGB 원본 | 4×`(120,160,3)` uint8, CPU (기준 데이터) | 시간순 observation JPEG; goal도 RGB |
| observation | `(1,12,96,96)` float32, GPU | `utils.transform_images`; 3채널×4장 |
| goal | `(1,3,96,96)` float32, GPU | 같은 preprocessing |
| goal mask | `(1,)` int64, GPU | 0=goal 사용, 1=goal token masking |
| obs EfficientNet 입력 | `(4,3,96,96)` float32 | `NoMaD_ViNT.forward`에서 channel split 후 batch concat |
| goal EfficientNet 입력 | `(1,6,96,96)` float32 | 최신 observation RGB와 goal RGB concat |
| attention token | `(1,5,256)` float32 | observation 4개 + goal 1개, positional encoding 및 4-layer attention |
| pooled condition | `(1,256)` float32, GPU | `NoMaD_ViNT.forward`; masked average pool |
| distance head | `(1,1)` float32, GPU | `DenseNetwork.forward`; topological goal-distance score, meter/초 아님 |
| repeated condition | `(8,256)` float32, GPU | 선택한 condition을 S번 repeat |
| initial Gaussian noise | `(8,8,2)` float32, GPU | standard normal, 좌표/단위 없음 |
| predicted epsilon | `(8,8,2)` float32, GPU | `ConditionalUnet1D.forward`, 각 denoising step |
| final normalized diffusion | `(8,8,2)` float32, GPU | 역정규화 전의 XY **delta** 값 |
| inverse-normalized delta | `(8,8,2)` NumPy float64, CPU | `unnormalize_data`; dataset waypoint-spacing으로 정규화된 상대 길이 단위 |
| cumulative trajectory | `(8,8,2)` torch float32, GPU | `get_action`: NumPy cumsum 후 `from_numpy(...).float()` |
| metric trajectory (derived) | `(8,8,2)` float32, GPU | cumulative × 0.05, deployment scale를 전체 trajectory로 확장 |
| selected waypoint | `(2,)` float32 | sample 0, waypoint index 2 (세 번째 point), 공식 scale 적용 |

Encoder는 공식 `NoMaD_ViNT`, EfficientNet-B0 두 개, BatchNorm→GroupNorm 변환, encoding size 256, attention heads 4/layers 4/FF factor 4다. Diffusion은 공식 `ConditionalUnet1D(input_dim=2, global_cond_dim=256, down_dims=[64,128,256], cond_predict_scale=False)`다. 최종 config와 state tensor를 모두 검증했다.

## Diffusion schedule과 RNG

`navigate.py` / `explore.py`와 같은 `diffusers==0.11.1`의 `DDPMScheduler`를 사용한다:

```python
DDPMScheduler(
    num_train_timesteps=10,
    beta_schedule="squaredcos_cap_v2",
    clip_sample=True,
    prediction_type="epsilon",
)
```

`set_timesteps(10)` 결과는 `[9,8,7,6,5,4,3,2,1,0]`이다. 기본 variance type은 `fixed_small`. 매 step에서 `model('noise_pred_net', ...)` 후 `scheduler.step(...).prev_sample`를 사용한다. 최종 t=0의 predicted sample clipping과 중간 noisy sample을 같은 범위로 해석하면 안 된다.

**초기 Gaussian noise를 고정하는 것만으로 출력 재현성은 보장되지 않는다.** 0.11.1 `scheduling_ddpm.py:DDPMScheduler.step`은 t>0에서 추가 Gaussian variance noise를 매번 생성한다. wrapper는 initial noise를 raw로 저장하고 DDPM 전체 RNG seed를 별도로 고정한다. 원본 step 계산은 바꾸지 않는다. fixed-all-noise 반복, 초기 noise만 고정한 실험, 다른 seed, 다른 observation 실험을 각각 저장했다.

## 역정규화, 누적, 좌표계

`train/vint_train/training/train_utils.py:unnormalize_data`, `get_action`과 `data/data_config.yaml`을 그대로 사용한다. normalized delta를 z라고 하면:

```text
min = [-2.5, -4.0], max = [5.0, 4.0]
delta = ((z + 1) / 2) * (max - min) + min
trajectory[t] = sum(delta[0:t+1])
```

z=0은 delta=(1.25,0)이며 정지 명령이 아니다. cumsum은 시간/waypoint 축(axis=1)에 적용한다. 이 trajectory는 **현재 observation pose를 원점으로 한 누적 local XY displacement**이며 각 waypoint마다 새 body frame으로 재해석하는 증분 pose가 아니다.

`vint_dataset.py:_compute_actions`는 global position에서 현재 위치를 빼고 `data_utils.to_local_coords`의 현재 yaw 회전을 적용한다. 행 벡터 표현으로 `(position-current_position).dot(R(current_yaw))`다. 표준 planar yaw/ROS body convention으로 +x는 forward, +y는 left에 해당하며 positive yaw는 반시계방향이다. image pixel 축(+x right, +y down)이나 Isaac world/camera 축과 동일하다고 가정하지 않는다. 카메라↔base extrinsic은 별도 입력이며 이번 검증에서 추정하지 않았다.

Training은 local XY를 `metric_waypoint_spacing * waypoint_spacing`으로 나눈다. 예를 들어 GoStanford dataset의 metric_waypoint_spacing은 0.12m다. inverse diffusion min/max normalization을 한 뒤에도 이 dataset-level 공간 정규화 단위가 남아 있다. 따라서 `get_action()` 출력을 그 자체로 meter라고 이름 붙이지 않는다.

## Deployment metric scale와 selection

`deployment/config/robot.yaml`: max_v=0.2m/s, frame_rate=4Hz. `navigate.py`는 먼저 sample 0의 waypoint index 2를 선택하고 XY에 `MAX_V/RATE=0.05m`를 곱한다. 후보를 평균하거나 가장 좋은 sample을 고르는 최적화는 없다. 여러 sample은 생성되지만 선택 규칙은 기본값 그대로 첫 sample이다.

공식 sampled-actions topic은 **scale 적용 전** trajectory들을 publish한다. metric scale는 선택한 point에만 적용한다. 연구 wrapper는 비교를 위해 전체 cumulative trajectory에도 같은 0.05를 적용한 `metric` 배열을 **derived**로 저장한다. 이 확장은 새로운 모델 출력이 아니며, selected point는 원본 NumPy in-place scaling 결과와 정확히 일치함을 테스트했다. 전체 배열을 복사해서 계산하므로 raw/cumulative를 수정하지 않는다.

이 deployment scale은 robot 설정에 기반한 변환이다. dataset의 0.12m spacing과 혼동하거나 예측이 그만큼의 실제 이동거리/도달시간을 보장한다고 해석하지 않는다.

원본 topomap navigation은 후보 goal별 condition/distance를 만들고 `argmin(dists)`로 가까운 node를 찾는다. distance가 close_threshold(기본 3)보다 작으면 다음 subgoal로 이동한다. 이번 wrapper는 사용자가 준 goal 하나를 이미 선택된 subgoal로 취급한다. **topomap localization과 목표 달성 판정은 실행하지 않았다.** 이 범위를 navigation 전체 재현이라고 주장하지 않는다.

## Goal-free, yaw, time

Goal-free는 동일 encoder에 `mask=1`을 전달한다. 공식 `explore.py`는 임의 fake goal을 넣지만, wrapper는 유효한 RGB goal을 그대로 넣고 masking한다. 서로 다른 실제 goal을 넣어도 masked encoder/action이 같은지 별도 검사했다. 목표 distance head는 goal-free에서 의미 있는 navigation 지표로 사용하지 않는다.

`learn_angle=False`, input_dim=2이므로 **native yaw output이 없다**. 8 point에 intrinsic timestamp, dt, velocity 또는 covariance도 없다. waypoint tangent로 만든 yaw나 `1/frame_rate`로 붙인 시간을 native output이라 부르면 안 된다. `frame_rate=4`는 deployment loop 및 scale에 쓰이는 설정이지 8 waypoint의 0.25초 sampling을 보증하는 metadata가 아니다. 향후 reconciliation에서는 capture pose/time과 좌표 변환, 모델의 spatial trajectory에 붙일 실행 시간 모델을 별도로 정의해야 한다.

## 원본과 wrapper의 동등성 및 차이

`research/nomad_preflight/native.py`는 AST로 `utils.load_model`, `utils.transform_images`, training의 normalization/get_action 및 to_numpy/from_numpy **원본 함수 정의 전체**를 읽어 실행한다. import namespace만 inference에 필요한 것으로 공급해 ROS 및 training side effect를 피한다. 모델 파일을 복사·수정·monkeypatch하지 않는다.

PyTorch 2.7에서는 encoder grad scope가 Transformer fast path에 영향을 준다. 따라서 goal-conditioned path는 원본 `navigate.py`처럼 **encoder/distance에서 grad enabled**, 반복 condition과 diffusion loop에서 no_grad를 사용한다. goal-free는 `explore.py`처럼 encoder도 no_grad다. grad-enabled encoder의 결과는 반환 시 detach하여 연구 결과가 graph를 오래 붙잡지 않게 한다. 이 detach는 계산을 마친 뒤 수행된다.

검증은 원본 encoder/distance 출력 exact equality, `navigate.py`에서 추출한 원본 denoising FOR statement와 exact equality, 원본 NumPy waypoint scaling equality, normalization/cumsum의 알려진 수치, 실제 checkpoint coverage/shape/finite, full-noise 반복, goal masking을 포함한다. 고정하지 않은 구형 torch/Python 환경과 bitwise equality까지 검증했다는 뜻은 아니다. GPU/버전 간 재현성 보장도 아니다.

wrapper가 추가한 것은 coverage 검사, 독립 RNG 제어, 동기화된 timer/memory 측정, raw/derived 저장, 전체 metric trajectory뿐이다. ROS transport, topomap search, controller 실행은 포함하지 않는다.
