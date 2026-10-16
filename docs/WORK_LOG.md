# 실행 기록과 최종 판정

아래 기존 절은 offline preflight 완료 당시의 기록이다. 이후 승인된 Isaac Sim 작업과 현재 remote/검증 상태는 마지막 **Isaac Sim 6 최소 navigation 추가 기록** 절을 따른다.

작업일: 2026-10-16, Asia/Seoul. 범위: 공식 repository/독립 환경/checkpoint/native offline inference/측정. NoMaD 학습, 모델 개선, Isaac Sim 실행, robot control, obstacle avoidance 평가, OLD/FRESH reconciliation, graph optimization은 수행하지 않았다.

## 공식 repository에서 확인한 사실

- 공식 SHA `dca79815b704e5aa9c6bdc3082351f9e3b2848c2`를 실제 checkout했다. branch는 `research/nomad-preflight`.
- Python 3.8.5와 CUDA 10/11 계열 환경 명세, diffusers 0.11.1, unpinned torch 및 diffusion_policy 설치 안내를 확인했다.
- config는 nomad_vint, EfficientNet-B0, context_size=3, encoding_size=256, 10 diffusion steps, 8 XY waypoints, learn_angle=False, normalize=True.
- 공식 loader는 `strict=False`. 공식 deployment는 sample 0/waypoint index 2를 선택하고 max_v/frame_rate=0.05를 곱한다.
- 공식 DDPM은 t>0의 각 step에서도 RNG를 사용한다. 초기 noise만 고정하는 것은 충분한 반복 재현성 조건이 아니다.
- 위 사실의 source 함수·단위·shape는 [ACTION_SEMANTICS.md](ACTION_SEMANTICS.md)에 기록했다.

## 실행 이력과 실패 처리

1. Workspace 조사: 기존 연구 파일 없음. 루트 `.git`은 비어 있는 read-only mount로 Git 명령이 실패했다. 이를 건드리지 않고 `visualnav-transformer/`에 공식 clone을 만들었다. 기존 프로젝트 파일을 덮어쓰지 않았다.
2. 제한 sandbox에서 Git network DNS 실패와 `nvidia-smi` 실패가 발생했다. 실제 driver 고장으로 단정하지 않았다. 승인된 host 접근의 read-only GPU 조사에서 기존 RTX 5060 Ti/driver 595.99.02가 정상임을 확인했다. driver 설정 변경 없음.
3. workspace `.venv` 생성. PyTorch 2.7.0+cu128 / torchvision 0.22.0+cu128 설치. 사용한 Python은 기존 3.11.16. dependencies는 고정하여 별도 설치했다. 설치 log는 `../artifacts/setup/`에 보존한다.
4. diffusion_policy를 clone한 후 기준일 이전 SHA `548a52bbb105518058e27bf34dcf90bf6f73681a`로 detached checkout했다. 사용된 세 모델 source 파일은 clone 당시 HEAD와 동일했다. training 당시 정확한 dependency commit은 upstream에 기록되어 있지 않아 알 수 없다.
5. `pip install -e` 후 diffusion_policy import가 실패했다. 원인은 namespace directory와 setuptools editable `find_packages`의 빈 mapping이었다. 원본을 수정하지 않고 launcher의 `PYTHONPATH`로 해결했다. 초기 CPU test collection과 첫 host coverage attempt는 실패로 남겼다. 해결 후 sandbox CPU tests는 4 pass/3 skip이었다. 당시 GPU skip은 PASS로 세지 않았다.
6. 공식 README Drive 폴더에서 checkpoint file ID와 byte size를 확인하고 다운로드했다. size/hash/state key/parameter coverage를 검증했다. CUDA `sm_120` 행렬곱을 실제 실행했다.
7. 공개 실내 영상은 합성 화면과 궤적 overlay가 있어, 기준 입력으로 README의 GoStanford 원본 RGB JPEG sequence를 추가 확보했다. JPEG를 재압축하지 않고 ZIP에서 원본 bytes를 추출했다. dataset pickle은 실행/역직렬화하지 않았다.
8. 10:50 KST의 초기 실행 `20261016_preflight_01`에서 GPU forward와 7개 초기 tests는 성공했다. 하지만 추가 grad-scope 비교에서 전체 no_grad wrapper가 원본 navigate.py와 다름을 발견했다. 실제 encoder max abs diff=0.006876945495605469, distance diff=0.006526947021484375. 이 결과는 native parity 기준에서 **무효화**했다. 원본 파일은 그대로 두고 `INVALIDATED.json`을 별도로 추가했다.
9. goal-conditioned encoder/distance는 grad enabled, diffusion은 no_grad로 원본과 동일하게 수정했다. goal-free encoder는 explore.py와 같이 no_grad 유지. 10:54 KST에 `20261016_preflight_02`를 새 폴더에 실행했다. encoder/distance, 원본 AST denoising loop, NumPy selected-point scaling의 exact equality 검증을 추가했다.
10. 사용자가 공식 공개 영상 사용을 선택한 후, 실제 영상의 observation/goal inset을 crop하여 `20261016_video_01`을 10:55 KST에 별도 실행했다. overlay를 보존하고 영상의 presentation time만 input manifest에 기록했다. native action timestamp로 사용하지 않았다.
11. 최종 test는 원본 source hash와 encoder 내부 shape 및 10개 decoder 출력 shape까지 검사한다. 공식 모델과 controller tracked source가 upstream SHA와 동일한지 Git diff로 재확인했다. 모든 package에 대한 `uv pip check`도 수행했다.

## 실제 측정 결과

기준 입력: GoStanford `no3vcF_33_0`, obs=10,11,12,13 / goal=25. 영상 보조 입력: 공식 nomad_indoors.mp4의 카메라 inset obs frame=30,38,46,54 / 표시된 goal inset frame=60.

| 검사 / 측정 | 기준 dataset 실행 | 공식 영상 보조 실행 |
|---|---:|---:|
| 실제 GPU full forward | PASS | PASS |
| checkpoint coverage | 645/645 state tensors, parameter elements 100% | 동일 |
| missing / unexpected / mismatch keys | 0 / 0 / 0 | 동일 |
| output normalized/cumulative/metric | `(8,8,2)`, float32, finite | 동일 |
| cold forward | 194.19 ms | 189.56 ms |
| warm median / p95, n=30 | 23.95 / 24.38 ms | 25.48 / 28.80 ms |
| peak allocated (warm, torch) | 172.75 MiB | 172.75 MiB |
| peak reserved (warm, torch) | 192.00 MiB | 192.00 MiB |
| fixed initial + DDPM RNG | bitwise equal; max abs 0 | bitwise equal; max abs 0 |
| different seeds, raw output max abs diff | 0.112308614 | 0.130552620 |
| fixed initial only / changed DDPM seed, max abs diff | 0.155785233 | 0.173611104 |
| different observation, same goal/noise, max abs diff | 0.188401312 | 0.159130886 |
| goal-free / changed actual goal, max abs diff | 0 | 0 |
| sample 0, selected waypoint index 2 (derived m) | (0.199176103, 0.020874692) | (0.160228118, 0.024882555) |

차이 통계는 **normalized raw diffusion output**에 대해 계산했다. meter 차이로 해석하지 않는다. 동일 입력 반복, seed 변화, observation 변화는 독립 case/파일이다. observation 변화 실험은 감응 여부를 보여주며 정확한 주행 trajectory, collision-free 여부 또는 목표 도달을 입증하지 않는다.

Peak memory와 latency의 정확한 범위·제외 항목은 [SETUP.md](SETUP.md)에 있다. PyTorch deterministic algorithms를 강제하지 않았고 CuDNN deterministic=False, benchmark=False, matmul TF32=False, CuDNN TF32=True였다. 이 설정에서 동일 장치/환경의 측정된 반복은 bitwise equal이다. 다른 GPU/torch 버전에 대한 보장은 아니다.

최종 테스트 결과는 `research/results/validation.json`에 기록한다. raw 로그는 `../artifacts/setup/gpu-tests-final.log`다. GPU가 없는 실행에서 pytest가 skip을 출력하면 해당 검사는 미실행이며 성공으로 세면 안 된다.

## 구현 변경과 제한

- 공식 모델/controller 변경 없음. AST를 이용해 원본 함수 body를 그대로 실행하고 필요한 import namespace만 공급했다. ROS node를 띄우지 않는다.
- Goal 하나가 이미 선택되었다고 가정하는 offline wrapper다. topomap localization/search, ROS camera callback transport, navigation goal completion은 검증하지 않았다.
- Grad scope 차이는 실제 수치 차이를 찾아 수정했다. 최종 wrapper는 원본 navigate/explore 경로의 encoder grad 모드를 각각 유지한다.
- checkpoint loader의 partial loading 가능성을 별도 coverage 검사로 차단했다. Config/normalization/scheduler 기본 의미를 변경하지 않았다.
- 수치 비교용 RNG seed와 동기화 timer, memory 계측, raw/derived 저장을 추가했다. Goal-free에서는 실제 RGB goal을 masked placeholder로 사용했다.
- 전체 metric trajectory는 공식 selected-point scale를 모든 point에 적용한 파생 배열이다. 모델 native metric output, yaw 또는 timestamp를 새로 만들어냈다는 뜻이 아니다.
- Historical Python 3.8/CUDA 10/11 실행과 bitwise 대조는 **NOT RUN**. 원본 source의 현재 GPU/runtime에서의 계산 동등성을 검사했다.
- 공식 영상은 RGB이지만 overlay/encoding이 포함된 편집 영상이다. 기준 원본 dataset도 training data일 수 있다. 어느 결과도 obstacle avoidance 성능이나 일반화 능력 검증으로 주장하지 않는다.

## Git 및 산출물

Git에 포함: `research/`의 wrapper/scripts/tests, requirements/lock, 작은 JSON summary/manifest와 `docs/` 문서, ignore 규칙. 포함하지 않음: `.venv`, checkpoint, diffusion_policy 외부 clone, ZIP/video/JPEG/PNG/NPZ 원본, 설치 캐시, 큰 runtime 결과.

checkpoint와 raw input/output은 기존 파일을 덮어쓰지 않는 경로/모드로 저장했다. 최종 실행은 새 디렉터리를 요구한다. Source/hash snapshot은 `research/results/source_manifest.json`이다.

검증된 추가 내용을 `research/nomad-preflight`에 commit한다. 기존 Git author identity가 구성되어 있지 않아 commit에만 `Codex <codex@openai.com>` identity를 사용하며 global identity는 설정하지 않는다. 사용자 소유 remote는 없고 origin은 공식 upstream이다. **Push는 하지 않는다.** Force push/history rewrite 없음.

## 미실행 연구 단계와 Isaac Sim 6 uncertainty

| 단계 | 상태 |
|---|---|
| NoMaD 공식 checkpoint GPU offline inference | PASS |
| 원본 function/encoder/diffusion 계산 동등성 (현 환경) | PASS |
| Isaac Sim 6 camera/robot/process 연동 | NOT RUN |
| robot navigation/controller 실행 | NOT RUN |
| obstacle avoidance / collision / success-rate 평가 | NOT RUN |
| OLD/FRESH consistency 분석과 SE(2) reconciliation | NOT RUN |
| graph optimization | NOT RUN |
| NoMaD 재학습/모델 개선 | NOT RUN, 이번 범위 아님 |

다음 integration 단계로 진행할 수 있다. 다만 camera FOV/intrinsics 및 색순서, observation capture rate와 history stride, simulation/render/control clock 및 pose 동기화, camera/base/world 좌표 변환, deployment 0.05 scale의 대상 로봇 적합성, inference 결과의 실행 시간/heading 정의, Isaac Sim 환경과 독립 inference process의 통신 및 GPU memory 공존은 아직 확인해야 한다. 기존 Isaac Sim 설정을 변경하거나 simulator를 실행해 이 항목을 검증하지 않았다.

## Isaac Sim 6 최소 navigation 추가 기록

작업일: 2026-10-16, Asia/Seoul. 사용자 후속 승인 범위는 장애물 없는 복도의 단일 bounded closed-loop 주행이다. 상세 결과·재실행 명령·제한은 [ISAAC6_MINIMAL_NAVIGATION.md](ISAAC6_MINIMAL_NAVIGATION.md)에 기록한다.

1. 실제 Git repository는 workspace 아래 `visualnav-transformer/`였다. 기존 branch `research/nomad-preflight`, clean HEAD `517ab41eb4a1a0e1927c1e62753172714f1c8507`, 설정 문서/native wrapper/공식 navigate/controller를 확인하고 별도 `research/isaac6-minimal-navigation` branch를 만들었다. `origin`은 이미 사용자 fork `https://github.com/minju5054/NoMaD.git`, `upstream`은 공식 저장소였다. 이름/remote를 임의 변경하지 않았다. `gh repo view`에서 사용자 fork와 현재 `ADMIN` 권한을 확인했다.
2. 기존 Isaac `/home/gpuadmin/isaacsim`의 VERSION은 `6.0.1-rc.7+release.42383.32955d8d.gl`, bundled Python은 3.12.13/NumPy 2.3.1이었다. NoMaD의 기존 `.venv` Python 3.11.16/NumPy 1.26.4/torch 2.7.0+cu128/diffusers 0.11.1을 유지했다. Package/system/driver/Isaac 설정 설치·업그레이드 없음. Process별 환경, runtime cache와 log를 분리했다.
3. 별도 Python process + local Unix socket adapter, actual RTX camera/goal capture, SE(2) kinematic pose update, 원본 AST controller 호출을 추가했다. 시작 `(0,0,0)`, 목표 `(1.5,0,0)`, tolerance 0.30 m, simulation timeout 30 s를 실행 전에 고정했다. dt 1/72 s, observation 4 Hz, controller refresh 9 Hz/계산 DT 0.25 s, sample 0/point index 2, 8 samples/8 XY points/10 DDPM steps를 사용했다.
4. Static render gate 01/02는 empty RGB로 실패했다. Camera/renderer adapter의 process-only 설정과 render-product 유지 후 gate 03에서 RGB/색상/좌표 검사가 통과했다. 이 단계에서는 모델 inference나 navigation을 실행하지 않았다. 실패/경고 로그는 보존했다.
5. 초기 코드 `2761d9a`에서 host tests 13개가 통과했다. 하지만 `navigation_01`의 첫 GPU inference 이후, 이동 전 controller 범위 assertion이 실패했다. NumPy 2에서 float32 clip 결과가 `0.20000000298`이 되는 scalar 차이를 두 환경에서 기록된 point로 확인했다. 원본 ROS와 같은 Python float list로 전달하도록 adapter만 고쳤다. Point 값/원본 수식/실험 조건 변경 없음. 실제 이동 0, 적용 waypoint 0인 중단 시도를 성공으로 세지 않는다.
6. 회귀 검사 추가 후 `.venv` GPU/IPC tests **14 passed, 0 skipped**, 2.11 s. 기존 Isaac Python에서도 adapter 5개 검사를 직접 실행해 통과했다. 수정한 실행 source는 `5cda940ed0fa07137e1549ce165560b757475ca5`로 commit했다. 실행 당시 미추적 파일은 작성 중인 보고서뿐이었고 각 source hash도 저장했다.
7. `../artifacts/isaac6/navigation_02/`에 동일 조건으로 단일 bounded closed-loop 실행 완료. **실제 RGB→NoMaD→원본 controller→agent 이동 성공, goal entry 성공.** 25회 GPU inference/25 waypoint 적용, 1.211111 m 이동, t=6.833333 simulation s에서 goal 거리 **0.299905 m**로 0.30 m tolerance에 진입했다. 최종 pose는 `(1.2078296845, 0.0676732474, 0.1360954405)`다. Navigation wall time 2.274564 s는 startup을 제외하며, wall clock에 맞춰 simulation을 sleep하지 않는다.
8. 저장 결과를 재분석했다. 493 actual USD pose rows/62 controller refreshes/25 applied events에서 normalization/cumsum/scaling/selected point/원본 controller exact equality, history 순서와 주기, inference 대기 중 clock 정지, observation/application 순서, world pose 기반 goal entry를 검증했다. 최대 SE(2) 재적분 차이 4.9960e−16. 실제 출력 `(8,8,2)` float32 finite. World XY 그림 한 장과 작은 summary/validation을 `research/results/isaac6_minimal_20261016/`에 저장했다. 추가 성능 주행 없음.
9. `git diff`로 공식 `train/`, `deployment/`가 upstream SHA와 동일하고 기존 `research/nomad_preflight/`가 preflight commit과 동일함을 확인했다. Raw outputs, checkpoint, `.venv`, 외부 dependency, renderer caches, 기존 preflight 결과는 Git에 넣거나 덮어쓰지 않았다. 신규 code/tests/docs/small result만 commit하고 확인된 사용자 origin에 일반 push한다. Force push/history rewrite 없음.

현재 판정: 최소 synchronous navigation integration **PASS**, 단일 근거리 goal entry **PASS**. 다음 제한된 장애물 실험을 준비할 수 있으나 footprint/collision/clearance와 고정 평가 기준을 별도로 정의해야 한다. 원본 topomap navigation, 장애물 회피 성능/성공률, 비동기 실행·OLD/FRESH handoff, reconciliation/graph optimization, robot dynamics, 모델 학습은 **NOT RUN**이다. 이 결과의 yaw/time은 agent 실행 기록이며 NoMaD의 intrinsic timestamp나 yaw가 아니다.
