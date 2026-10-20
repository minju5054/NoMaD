# 실행 기록과 최종 판정

아래 기존 절은 offline preflight 완료 당시의 기록이다. 이후 승인된 Isaac Sim 작업과 현재 remote/검증 상태는 하단의 날짜별 추가 기록을 따른다.

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

## Isaac Sim 6 정적 장애물 추가 기록

2026-10-16. 상세 보고서는 [ISAAC6_STATIC_OBSTACLE.md](ISAAC6_STATIC_OBSTACLE.md)다. 기준 `35c435e3eb19471c8f678ae8387d6c641bcf7623`의 clean tree에서 별도 `research/isaac6-static-obstacle` branch를 생성했다.

1. 기존 설정을 유지하고 별도 scenario에 중심 `(0.75,0)` m, 크기 `(0.30,0.40,0.80)` m의 녹색 box, 반경 0.12 m footprint, clearance 0.02 m를 고정했다. 원본 모델/worker/controller/normalization/선택 point/seed/속도/tolerance 변경 없음. Geometry는 NoMaD에 입력하지 않고 실제 RGB에만 렌더링했다.
2. 매 72 Hz 이동 구간에 chord/AABB 거리와 unicycle arc sagitta를 이용한 보수적 swept clearance를 추가했다. Goal entry만으로 unsafe 경로를 성공 처리하지 않는다. Clearance는 계측/종료에만 쓰며 회피 controller 또는 waypoint 보정에 사용하지 않는다. Sample 0 전체 polyline의 clearance는 별도 planning diagnostic으로 저장한다.
3. 개발 중 두 unit assertion(부동소수점 경계 및 upper-bound 해석)을 바로잡았고, 실행 전 tests 19개와 Isaac Python 검사 10개가 통과했다. 코드와 scenario를 `fe030579cecd9051f22655bc8fccc003be6775d4`로 commit한 후 clean tree에서 단일 `static_obstacle_01`을 실행했다. 기존 장애물 없는 실험은 재실행하지 않았다.
4. **결과는 충돌 없이 목표 도달 실패.** t=7.319444 s에 장애물 왼쪽(+Y)으로 footprint가 통과했다. 최소 swept clearance 하한 0.07519549 m, 상한 0.07519878 m로 0.02 m 기준 만족. Geometric overlap 및 corridor 침범 없음. 하지만 최소 goal 거리 0.46889352 m로 tolerance 0.30 m에 진입하지 못해 t=30 s simulation timeout으로 종료했다. 실행 중 기술적 중단이나 조건 변경/성능 재시도 없음.
5. 117 inference/117 waypoint 적용, 2161 pose records, 270 controller refreshes를 저장하고 재검증했다. 정상 RGB/좌표/원본 controller exact equality와 output finite/shape를 확인했다. 모델 전체 sample 0 polyline은 3회 footprint overlap을 예측했지만 index 2까지의 prefix와 실제 경로는 안전했다. 가까운 goal의 왼쪽 약 0.47 m를 지나 계속 전진한 실패를 기록했으며 camera/domain/topomap 생략의 원인 분리 실험은 하지 않았다. 실제 contact가 없어 runtime collision-stop branch는 **NOT EXERCISED**로 명시했다.
6. 최종 tests는 goal/safety 분류 회귀 검사 포함 **20 passed, 0 skipped**, 2.10 s. 기존 Isaac Python의 adapter/기하 검사 **11개 통과**. 원본 NoMaD source와 baseline worker/scenario의 Git diff는 비어 있다. 시스템/가상환경/Isaac 패키지 설치 변경 없음.
7. Raw/derived 결과는 `../artifacts/isaac6/static_obstacle_01/`에 보존하고 작은 summary/validation/World XY 그림 한 장은 `research/results/isaac6_static_obstacle_20261016/`에 저장했다. 기존 결과를 덮어쓰지 않았다. 실제 overlap이 없으므로 최초 발생 위치는 null/해당 없음이다.
8. 기존 설치의 `isaac-sim.sh`와 이미 포함된 `omni.usd/.../scripts/open_stage.py`로 GUI scene 표시를 확인했다. Raw USD의 runtime capture graph가 GUI에서 반복 오류를 내어 raw를 보존하고 `/World`만 복사한 `scene_gui.usda`를 추가했다. World prim 98개와 모든 attribute/relationship 일치를 검사했다. 최종 GUI는 해당 파일의 실제 open 성공 및 Error 0개를 확인했다. 정적 scene 표시만 하며 recorded trajectory replay 프로그램을 구현하지 않았다. GUI 검증 동안 NoMaD inference/navigation은 실행하지 않았다.
9. 사용자 `minju5054/NoMaD`의 ADMIN 권한과 기존 origin을 확인했다. 관련 코드/tests/docs/작은 결과만 새 연구 branch에 commit하고 일반 push한다. Checkpoint, raw/derived NPZ, USD, RGB, caches, 기존 preflight 결과는 Git에서 제외한다. Force push/history rewrite 없음.

최종 판정: 기술적 실행/계측 PASS, obstacle clearance와 corridor 조건 PASS, goal entry FAIL, **통합 장애물 navigation 성공 FAIL**. 일반적인 obstacle navigation 성공률, 물리 충돌, async/OLD-FRESH/graph optimization은 미검증이다. 결과를 성공으로 바꾸기 위한 추가 실험이나 모델 튜닝은 수행하지 않았다.

## 주행 영상 후속 요청

2026-10-16. 사용자가 정적 scene이 아닌 agent의 실제 주행 영상을 요청했다. `bab1109209891ea06f843806dbd755c9c6725ba3`의 clean `research/isaac6-static-obstacle`에서 영상 후처리를 추가했다.

1. 원래 실험에는 연속 녹화가 없어, 실제 `static_obstacle_01/agent_trajectory.csv`를 기존 Isaac RTX renderer로 재생했다. 당시 촬영본이 아닌 **실제 실행 pose의 사후 렌더링**임을 영상과 문서에 명시했다. 새 NoMaD inference/controller/navigation은 0회다.
2. 원래 agent는 mesh가 없으므로 반경 0.12 m 파란 footprint와 흰 heading 표시를 붙이고, orange goal tolerance와 executed trail, 관찰 camera를 추가했다. 주행 입력이나 모델은 변경하지 않았다. 첫 관찰 camera에서는 장애물에 agent가 가려져 반대편 +Y camera에서 다시 렌더링했다. 두 rendering 산출물은 모두 보존했으며 navigation 재시도는 아니다.
3. 최종 `../artifacts/isaac6/static_obstacle_video_02/nomad_static_obstacle.mp4`: 1280×720 H.264, 24 fps, 721 frames, 30.041667 s, 24,404,436 bytes. 72 Hz 원본 pose를 매 3번째 선택해 t=0…30 s 전체를 1배 simulation time으로 보여준다. 원래 wall time을 재현하지 않는다. 설치된 `omni.videoencoding`을 사용해 package 설치 없이 생성했다.
4. MP4 721 frames 전체 decode, 모든 frame/CSV pose exact equality, source SHA-256 보존, 실제 renderer snapshot hash 일치를 확인했다. Native USD animation 2,161 pose의 최대 절대 오차 4.44e−16. 원래 98개 World prim/default attribute 643개/relationship 72개 보존. 영상 시작/회피/goal 근접/최종 frame을 시각 확인했다.
5. 별도 `recorded_motion.usda`에 실제 실행 pose를 time samples로 넣었다. 이후 native camera metadata만 더한 `recorded_motion_gui.usda`를 별도 저장하고 기존 GUI로 실제 open 성공 및 Error 0개를 확인했다. GUI Play 버튼 수동 조작은 미검증이며 animation 수치 및 MP4 decode는 검증했다. Renderer 마지막 부분에도 동일 GUI metadata export를 추가했으며 영상 실행 당시 source snapshot과 구분했다.
6. 상세 내용은 [ISAAC6_STATIC_OBSTACLE.md](ISAAC6_STATIC_OBSTACLE.md), 작은 검증 기록은 `research/results/isaac6_static_obstacle_20261016/video.json`이다. Video/PNG/USD/cache는 Git에 넣지 않는다. Source/docs/작은 JSON만 현재 research branch에 commit하고 사용자 origin에 일반 push한다. 기존 model/controller와 raw 실행 기록, 시스템 및 Isaac 설치를 변경하지 않았다.

주행 결과는 그대로 **왼쪽 안전 통과, 최소 clearance 7.52 cm, 목표 도달 실패**다. 영상 때문에 성공 판정을 바꾸거나 추가 성능 실험을 하지 않았다.

## GUI 명령의 CUDA library 충돌 수정

2026-10-16. 사용자가 제공한 `__nvJitLinkCreate_12_8` 오류를 실제 `kit_20261016_140832.log`에서 확인했다. 이전 GUI 검증 process에서는 Python/CUDA 환경을 제거했지만 전달한 직접 실행 명령에는 그 처리가 누락되어 있었다.

- 상속된 `LD_LIBRARY_PATH`에 `/usr/local/cuda/lib64`가 있고 실제 target은 CUDA 12.6이었다. `ldd/readelf`로 Isaac cuSPARSE가 12.6 nvJitLink를 먼저 선택하여 필요한 12.8 심볼을 찾지 못함을 확인했다. 환경을 제거하면 Isaac bundled nvJitLink의 올바른 심볼이 선택된다. PyTorch 안내는 deprecation manager가 모든 `ImportError`에 출력하는 공통 메시지였다.
- `research/nomad_isaac/open_scene.sh`를 추가해 해당 GUI child에만 library/Python/venv 환경을 분리했다. 기존 Isaac launcher/opener를 그대로 사용하고, 문서의 static/animated scene 명령 둘 다 수정했다. 새 GUI/replay framework나 package 설치는 없다.
- 실제 CUDA 12.6/ROS 환경을 가진 parent에서 launcher를 실행해 14:13:21 KST에 animation scene open 성공 및 Error 0개를 확인했다. Process maps에서 Isaac 내부 torch/cuSPARSE/nvJitLink 로딩 확인. Parent 환경 및 scene hash 불변, shell syntax/missing-file guard 통과. 검증용 GUI만 정상 종료했고 새 inference/navigation은 실행하지 않았다.
- 검증 기록은 `research/results/isaac6_static_obstacle_20261016/gui_environment_fix.json`, raw log는 `../artifacts/isaac6/gui_environment_fix_01/`에 저장했다. 시스템/driver/CUDA/Isaac/.venv/원본 기록 변경 없이 source/docs/작은 결과만 현재 연구 branch에 commit/push한다.

## 두 장애물 및 증가한 시작 거리

2026-10-16. 사용자가 장애물 2개, 서로 다른 크기·위치, 더 먼 첫 장애물 및 GUI 표시를 요청했다. 단일 장애물 제안은 이 후속 요청으로 대체했다. 기준 `45b6026`에서 `research/isaac6-two-obstacles` branch를 생성했다.

1. 시작 `(0,0,0)`, 장애물 1 중심 `(1.5,0)`/크기 `(0.4,0.5,0.8)` m, 장애물 2 중심 `(3.0,0.35)`/크기 `(0.5,0.6,1.0)` m, 목표 `(4.5,0,0)`, timeout 60 simulation s를 실행 전에 고정했다. 첫 앞면까지 거리는 0.60→1.30 m, footprint gap은 0.48→1.18 m가 됐다. Seed/model/controller/속도/주기/tolerance/clearance는 유지했다.
2. 기존 단일 AABB monitor를 각 장애물에 적용하고 per-obstacle 및 aggregate logs를 추가했다. 어느 장애물이라도 contact이면 중단하며 controller에 장애물 geometry를 입력하지 않는다. 초기 goal 거리의 기록 상수만 실제 값으로 수정했다. 영상의 off-grid 종료 pose 보존과 GUI yaw의 동등한 unwrapped 표시도 추가했다.
3. 실제 host GPU tests **25 passed, 0 skipped**, 2.09 s; 기존 Isaac Python adapter/geometry **16개 통과**. 최초 sandbox socket 검사는 permission 제한으로 실패했고 host에서 통과했다. 코드를 **`bdd0970c1f9ab988f68dc83fbb04fd5b2967ee10`**으로 commit한 clean 상태에서 `two_obstacles_01` 한 번을 실행했다. 기술적 중단/조건 조정/성능 재시도 없음.
4. 두 장애물을 모두 왼쪽으로 통과했고 geometric overlap/corridor 침범은 없었다. 최소 swept clearance 하한은 각각 **0.10384044/0.12270646 m**로 0.02 m 기준 만족. Goal에는 **0.66305456 m**까지 접근했지만 0.30 m tolerance에 진입하지 못하고 돌아와 60 s timeout으로 종료했다. 전체 navigation 성공은 FAIL이다.
5. 237 inference, 540 controller refreshes, 4,321 actual pose rows를 검증했다. 두 장애물의 swept/planning records와 aggregate 판정, 원본 controller/normalization/selected point/history 일치를 확인했다. 최대 pose 재적분 오차 2.6645e−15, predicted sample-0 overlap 0회. Runtime contact-stop은 실제 접촉이 없어 NOT EXERCISED다. 기존 단일 보고서도 offline regression 통과. 보고서에는 기존 시스템 matplotlib를 사용하고 설치를 바꾸지 않았다.
6. `two_obstacles_video_01`에 1,441-frame/24 fps/60.041667 s MP4 및 native GUI animation을 생성했다. 모두 기록 pose 기반 사후 렌더링이며 새 navigation은 아니다. MP4 전체 decode, USD 4,321 poses/101 original prims 보존 검사 통과. GUI `--play` 옵션은 기존 timeline의 반복 재생만 수행한다.
7. GUI를 실제 열고 Error 0개/playing=true를 확인했다. 재생 t=2.013888889 s의 agent pose가 원본 145번 row와 최대 1.61e−15 차이로 일치했다. 기존 환경 분리를 유지해 Isaac nvJitLink 로드도 확인했다. 사용자가 볼 수 있도록 GUI를 열어 두었다.
8. 이전 raw files 10개와 MP4 hash, 공식 model/controller/worker와 이전 scenario가 그대로임을 확인했다. 상세 문서는 [ISAAC6_TWO_OBSTACLES.md](ISAAC6_TWO_OBSTACLES.md), 작은 결과는 `research/results/isaac6_two_obstacles_20261016/`다. Source/tests/docs/작은 JSON/SVG만 새 연구 branch에 commit/push하며 raw/video/USD/cache는 Git에서 제외한다.

## Successive OLD/FRESH geometric handoff audit

2026-10-16. 사용자 요청에 따라 기준 `49f865cb4148fedef6c15be1e9739d5e53ba151b`에서 별도 `research/old-fresh-geometric-audit` branch를 생성했다. 저장된 `two_obstacles_01`만 분석했다.

1. 로그 schema와 기존 source를 확인하고 pair metric 계산 **전에** protocol/threshold를 `0f41d5e`에 commit했다. Observation anchor 유지, 실제 application pose B, 공통 forward station 및 arclength 대응, 짧은 segment heading invalid, early-prefix entry와 rotate/straight/rotate 연결, 5개 분류 및 후보 선택 규칙을 고정했다. 큰 RMSE만으로 후보를 만들지 않는다.
2. NumPy/stdlib 기반 offline audit와 synthetic checks 7개를 추가했다. Tests **7 passed**, 0.07 s. NoMaD/Isaac import나 GPU 실행은 없다. 분석 코드는 `6de5bc6`의 clean 상태에서 실행했고 성공했다. 분석 재시도/결과 후 기준 변경 없음.
3. Raw/derived 237쌍 존재 및 연속 ID를 확인했다. 주 분석 98 predictions(ID 0..97)의 raw→derived/scaling/selected point, observation→world/planning, 원본 controller 및 pose 적분 검증 통과. 사용한 205개 입력의 분석 전후 hash 불변, 기존 pose/scenario hash 및 source 10개 hash 일치. 실행 당시 개별 NPZ/events/controller/planning hash가 없어 이번 hash는 새 baseline이며 과거 무결성 증명으로 과장하지 않았다.
4. 최초 goal 최근접 t=25.25 s까지 적용된 주 분석은 **97 pair**, 이후 139 pair는 후보에서 제외했다. **94 ALREADY_CONSISTENT / 3 INSUFFICIENT_EVIDENCE / 나머지 0**. 3개(94→95, 95→96, 96→97)는 goal 부근 tail의 forward projection이 되접혀 자동 correspondence가 불충분했다. 짧은 segment 14개는 derived heading=null로 기록했다.
5. 유효 94 pair의 equal-progress spatial RMSE median/p95/max **0.01318/0.03543/0.05895 m**, heading RMS **7.09/19.19/31.07°**. 97개 모두 FRESH 및 nearest connector가 안전했고 B→entry 최대 거리 0.06656 m, yaw 차이 최대 11.12°. FRESH 최소 clearance 0.14585 m, connector 최소 0.22144 m. Safe FRESH에서 연결 문제가 입증된 pair **0개**, 후보 그림 0개다.
6. Synchronous inference 중 simulation 경과는 0 s다. 수신 후 controller tick까지 실제 최대 지연 0.083333 s/translation 0.0166667 m만 기록했다. 최대 |Δw|=0.61258 rad/s인 60→61도 실제 다음 switch까지 안전했다. 이를 Graph 필요성이나 목표 실패 원인으로 단정하지 않았다.
7. 최종 판정 **NO_QUALIFIED_CANDIDATE**. 서로 다른 initial/DDPM seed와 observation 변화는 분리하지 못한다. 비동기 reconciliation 필요성, oracle correspondence, Graph 우월성은 미입증이다. 새 inference/navigation/sampling/optimization/video는 모두 0회다.
8. 상세 [보고서](OLD_FRESH_HANDOFF_AUDIT.md), source/tests 및 작은 CSV/JSON만 Git에 포함한다. 전체 세부 수치는 `../artifacts/isaac6/handoff_audit_01/`에 보존했다. 원본 model/controller/geometry/coordinate/environment/실험 데이터는 변경하지 않았다.

## Isaac Sim 6 asynchronous action execution

2026-10-16. 기준 `622d99fae814b5a1b6cb7a262ebf835e14bc36df`에서 `research/isaac6-async-execution` branch를 생성했다. 상세 [ISAAC6_ASYNC_EXECUTION.md](ISAAC6_ASYNC_EXECUTION.md).

1. 공식 navigate/PD/ROSData source를 확인했다. Nominal planning 4 Hz, controller 9 Hz, received age <1 s만 유효하며 처음/timeout에는 zero velocity다. 새 protocol과 soft real-time 기준을 실행 전에 `0cd69f7`에 commit했다.
2. Main RTX capture, 한 개 outstanding request만 처리하는 IPC thread, 72 Hz canonical SE(2) execution thread를 분리했다. USD camera는 촬영 pose snapshot을 표시하며 실제 kinematic 상태와 clock은 rendering/inference 동안 계속 진행한다. Native PhysX/72 Hz USD dynamics라는 주장은 하지 않는다. Worker에는 timing metadata만 추가하고 inference 계산/원본 controller/좌표/clearance 함수는 보존했다.
3. Synthetic tests **5 passed**, 0.06 s: 공식 ROSData와 정확한 timeout 경계 비교, 첫 수신 전 정지/OLD 계속 이동, 다음 controller tick 전환, single outstanding ordering, 72/9 Hz clock/integration. 코드를 **`cef336f6143a36c6e85559213aacfae02b46020b`**에 commit한 clean 상태에서 `async_two_obstacles_01` 주행 **한 번**을 실행했다.
4. 실제 GPU inference 31회, receive/switch 각 31회, control refresh 77회, pose 610개. 첫 적용 t=1.111111 s까지 정지했다. 이후 **30개 inference 모두 유효 OLD의 실제 nonzero pose intervals**가 있었고, next controller tick 적용 오류 0회였다. Timeout 0회/실제 expiry branch NOT_EXERCISED, busy skip 0/missed capture slot 0이다. 강제 지연을 넣지 않았다.
5. Warm inference median/p95 **29.020/30.882 ms**, capture-start→ready **68.167/130.512 ms**, capture-start→switch **138.530/194.272 ms**. Inference 안에 완전히 포함된 실제 OLD tick 이동 거리 median/max **0.002778/0.005556 m**, yaw 절댓값 median/max **0.004700/0.011111 rad**. Observation 대비 switch translation median/max **0.021173/0.036109 m**, yaw **0.033333/0.072222 rad**.
6. 8.458333 simulation s / 8.458429 wall s, RTF **0.999988664**. Pose pacing error p95/max **0.15299/1.22527 ms**, inference duration wall↔sim mapping 오차 p95 **0.12365 ms**. 사전 real-time 기준 모두 통과. Mapping은 기록된 두 clock의 보간 비교이고 OLD 직접 증거는 보간 없는 실제 ticks다.
7. Navigation은 **첫 장애물 geometric collision으로 실패**했다. t=8.458333 s, pose `(1.18006047,-0.11566335,-0.69650412)`, goal 최소 거리 3.32195 m, clearance 하한 −0.000062402 m. 최초 contact 검출 후 추가 integration 없이 중단했다. NoMaD prediction 29의 selected point 자체에도 overlap이 있었고 30은 safety margin 미달이었다. Navigation 실패를 이유로 재시도/scene·seed·controller tuning하지 않았다.
8. 원본 normalization/cumsum/metric/sample/PD command, observation anchor 및 모든 pose 적분/clearance를 검증했다. Coverage 100%, 실제 출력 전부 `(8,8,2)` float32 finite. 실행 source 14개 hash와 기존 baseline 484개 hash 보존. 기존 baseline t_obs는 capture 후여서 offline 보고서 v2에 RGB-available 기준의 공통 비교를 추가했다. 최초 offline report도 보존했으며 추가 주행/기준 변경은 아니다.
9. 판정은 **async execution/soft real-time PASS, navigation safety/goal FAIL**. 실제 timeout, 장시간 busy, 60초 지속 pacing은 미검증이다. 원본 ROS/topomap/PhysX, Graph/correspondence/latency injection/benchmark/MP4/GUI는 구현·실행하지 않았다. 새 source/tests/docs/작은 JSON/CSV만 commit/push하고 raw/derived 및 환경은 보존한다.

## Async footprint 반경 9 cm 재실행 및 GUI 저장

2026-10-16. 사용자 후속 요청에 따라 `b0ab3d2`에서 `research/isaac6-async-radius09`를 생성했다. 이전 12 cm async 기록을 GUI로 보여준 후, 새 반경으로 주행하고 GUI를 즉시 저장하라는 요청을 수행했다. 상세 [ISAAC6_ASYNC_RADIUS09.md](ISAAC6_ASYNC_RADIUS09.md).

1. 새 scenario에서 radius만 0.12→0.09 m로 변경하고 나머지 모델·장애물·seed schedule·controller·async runtime·안전 및 timeout 기준을 유지했다. 설정과 native GUI-only exporter를 실행 전 `c8fcf516d2dd35c59bfb408d88f1347ec43d4b01`에 commit했다. 기존 source 및 raw는 보존했다.
2. 새 정상 주행 1회, 기술적/성능 재시도 0회. 147 inference, 2,718 poses, 37.736111 simulation s를 기록했다. 장애물 두 개를 왼쪽으로 통과했으며 최소 clearance는 0.256990/0.328163 m, obstacle overlap 없음. 목표에는 0.650837 m까지 접근했지만 미도달했고 복도 끝 footprint 침범으로 즉시 중단했다. 전체 navigation FAIL.
3. Warm GPU median/p95 29.183/30.990 ms, OLD 이동 median/max 0.002778/0.005556 m, 이후 146개 inference 모두 OLD nonzero 이동. RTF 0.999997428, pacing p95/max 0.154665/1.396211 ms. Async/soft real-time PASS. Timeout 0회, busy observation skip 1회, missed slot 0회.
4. 주행 summary 생성 후 0.962 s에 GUI USD를 저장했다. 모든 2,718 pose와 기존 101 prim을 검증했고 source 보존 및 9 cm 표시를 확인했다. 기존 Isaac GUI에서 반복 재생을 열어 playing=true, 원본 row 145 pose 일치, startup Error 0개 확인. GUI는 저장된 실제 주행 재생이며 추가 navigation/MP4는 없다.
5. Synthetic tests 5 passed/0.06 s, 전체 raw/derived/PD/pose/timing/clearance offline 검증 PASS. 이전 async raw 주요 83개와 sync 484개 hash 불변. 초기 RGB hash 및 timing이 다른 단일 run이므로 경로 변화를 radius만의 효과로 주장하지 않는다. source·작은 JSON·문서만 commit/push하고 USD/raw/cache는 Git에 넣지 않는다.

## 두 번째 장애물을 왼쪽 벽에 붙인 async 실행

2026-10-16. 사용자 기대 시나리오인 첫 장애물 왼쪽/두 번째 오른쪽 통과를 조사했다. 기준 `12c8fc3`, branch `research/isaac6-async-wall-obstacle`. [상세 보고서](ISAAC6_ASYNC_LEFT_WALL.md).

1. Footprint 반경 9 cm 및 기존 모든 실행 조건을 유지하고 두 번째 장애물 중심 Y만 0.35→1.20 m로 변경했다. 크기 0.5×0.6×1.0 m, +Y 면 1.5 m가 왼쪽 벽에 닿아 gap=0 m다. 설정을 주행 전에 `b6ecb8449de29f4ce5b89d16cb5e369134c500e4`에 commit했다. 회피 방향을 강제하는 logic은 추가하지 않았다.
2. 정상 주행 1회, 기술적/성능 재시도 0회. 첫 장애물 왼쪽 t=10.958333 s, 두 번째 오른쪽 t=18.777778 s 통과. 최소 swept clearance 0.101514/0.429708 m, overlap/corridor 침범 없음. t=23.958333 s에 거리 0.299932 m로 goal tolerance 진입. 기대한 순서와 navigation 안전 조건 모두 PASS.
3. 92 GPU inference/receive/switch, 1,726 poses. Warm median/p95 30.233/33.046 ms, 이후 91/91 inference 중 OLD 이동. RTF 0.999994371, pacing p95/max 0.153655/4.958789 ms. Async/soft real-time PASS, timeout 0회/NOT_EXERCISED, busy skip 1회.
4. 주행 summary 후 0.978 s에 GUI animation 저장. 모든 pose/101 prim 보존 검증, native GUI 재생 및 row 145 pose 일치/Error 0개 확인. 저장된 실제 기록의 반복 재생이며 추가 navigation/MP4가 아니다.
5. 기존 offline validator와 실제 USD geometry 검사 통과. 이전 9 cm run 주요 321개 및 synchronous 484개 hash 보존. 원본 model/controller/runtime/clearance/exporter 및 환경 변경 없음. 한 scenario의 성공을 일반적 성능이나 Graph 필요성으로 확대하지 않는다. 새 scenario·작은 JSON·문서만 commit/push한다.

## 두 번째 벽 부착 장애물의 Y 폭 1.5 m 확대

2026-10-16. 사용자 요청으로 두 번째 장애물을 0.5×1.5×1.0 m로 확대했다. 기준 `54cac31`, branch `research/isaac6-async-wide-wall`. [상세 보고서](ISAAC6_ASYNC_WIDE_WALL.md).

1. 왼쪽 벽 부착을 유지하려고 두 번째 중심 Y를 1.20→0.75 m, 폭 Y를 0.6→1.5 m로 변경했다. 다른 scenario 값은 그대로다. 실제 USD AABB `[2.75,0,0]..[3.25,1.5,1]`, left gap=0 m를 확인했다. 실행 전에 `fb9bf2253044be477873aa113a19899f479af248`에 고정했고 clean tree에서 정상 주행 1회만 수행했다.
2. 첫 장애물 왼쪽 t=11.319444 s, 두 번째 오른쪽 t=20.138889 s 통과. 최소 swept clearance 0.069630/0.082836 m, 충돌·corridor 침범 없이 t=24.583333 s에 거리 0.297708 m로 goal entry. 기대한 방향 및 안전/목표 PASS. 재시도/회피 logic/model/controller 변경 없음.
3. 95 inference/receive, 94 switch, 1,771 poses. 마지막 ID 94는 수신 후 다음 controller tick 전에 목표 진입해 미적용 상태로 보존했다. Warm median/p95 29.187/31.903 ms, 이후 94/94 inference 동안 OLD 실제 이동. RTF 0.999995888, pacing p95/max 0.154592/1.198826 ms. Async/soft real-time PASS; timeout 0회/NOT_EXERCISED, busy skip 1회.
4. Summary 생성 후 0.965 s에 GUI animation 저장. 원본 pose 전체/101 prim 보존과 9 cm footprint 검사 통과. 기존 GUI native replay playing=true, row 145 pose 일치, startup Error 0개 확인. 추가 inference/navigation/MP4 없음.
5. 모든 raw/derived/PD/pose/timing/clearance offline 검증 PASS. 이전 run 주요 208개 및 sync baseline 484개 hash 보존. 기존 source 및 환경은 변경하지 않고 새 scenario·작은 JSON·문서만 commit/push한다. 단일 run의 성공을 일반적인 성능 또는 Graph 필요성으로 확대하지 않는다.

## 성공한 async run의 OLD/FRESH Graph 필요성 audit

2026-10-16. 새 사용자 요청에 따라 기준 `929a9dc`에서 `research/isaac6-async-handoff-audit`를 생성했다. 중단된 폭 2.0 m 실험 결과는 별도 `research/isaac6-async-wall-width20`의 `0683639`에 보존했으며 이번 분석에는 사용하지 않았다. [상세 보고서](ASYNC_OLD_FRESH_HANDOFF_AUDIT.md).

1. 성공한 `async_wide_wall_01`의 저장 데이터만 분석했다. Fixed-goal adapter 유지, 새 Topomap/navigation/inference/latency/Graph/영상 없음. 기존 correspondence/entry/classify 및 thresholds를 유지하고 async scope/clock 규칙을 metric 계산 전 `dc6c69d`에 고정했다. 분석 코드는 `1c34d6f` clean 상태에서 실행했다.
2. 95 predictions, 94 실제 적용 중 initialization ID 0을 제외한 **93 handoff**를 복원했다. 수신됐지만 미적용된 ID 94는 별도 제외. 각 path는 자신의 observation pose에 고정하고 B는 실제 switch pose로 사용했다.
3. 분류는 **consistent 85 / staging 1 / unsafe FRESH 1 / potential reconciliation 0 / insufficient 6**. 유효 correspondence 87개, classifiable 93.55%. 최종 **NO_QUALIFIED_CANDIDATE**. 후보 0개라 그림도 생략했다.
4. Equal-progress position RMSE median/p95/max 0.01356/0.04510/0.05745 m, tangent heading RMS 6.62/19.78/22.38°. Observation pose→switch OLD 이동 0.02778/0.03611/0.04444 m, robot yaw 절댓값 1.15/3.84/5.09°. Controller local-point world 의미와 observation-anchored point의 거리 median/max 0.02774/0.04492 m를 별도 측정했다.
5. 두 번째 장애물 접근·통과 24개 모두 consistent. 모든 nearest connectors가 안전했고 실제 93개 실행 구간도 안전했다. Prediction 29는 tail 6→7만 unsafe인 반면 prefix와 실행은 안전했다. Pair 83→84는 1.15 mm 연결의 큰 bearing 때문에 staging으로 분류됐지만 연결과 실제 실행 모두 안전했다. 6개 invalid correspondence는 판정을 보류했다.
6. 기존 7+새 최소 3 tests, **10 passed/0.08 s**. 95 raw/derived/원본 PD/pose/timing/clearance 재검증 및 기존 async report 93행 교차 검증 PASS. 과거 203개 input hash 일치, 분석 전후 205개 hash 불변, 실행 source 17개 보존. Source/작은 CSV·JSON/docs만 commit/push한다.
7. 현재 성공 baseline에서 해결해야 할 연결 실패는 발견하지 못한 negative evidence다. Graph 필요성·성능·우월성은 미입증. 더 큰 OLD 이동 조건의 문제 존재성을 조사하려면 후속 controlled latency 실험을 검토할 수 있으나 이번 작업에서는 실행하지 않는다.

## 장애물 부근 OLD/FRESH pair 그림

2026-10-16. 사용자 후속 요청으로 위 audit의 저장 데이터를 시각화했다. 모델/주행/분류를 변경하지 않았다.

1. 첫 장애물 접근/통과와 두 번째 접근에서 각 구간 최대 유효 spatial RMSE인 18→19, 28→29, 53→54를 선택했다. 두 번째 통과에서는 실제 다음 switch까지 clearance가 가장 작은 62→63을 선택했다. 사후 설명용 선정이며 qualified candidate나 새로운 correspondence가 아니다.
2. 전체 주행 위치도 및 4개 확대 패널에 observation-anchored OLD/FRESH, index 2, observation/switch pose, 9 cm footprint, 기존 entry와 미실행 connector, 실제 다음 handoff까지 실행 구간을 표시했다. 28→29의 tail overlap은 실제 충돌과 분리했다. 기존 `NO_QUALIFIED_CANDIDATE` 유지.
3. Plot 전후 원본 run 205개 및 audit/plot 입력 5개 hash 불변, 표시 좌표의 derived NPZ→world 변환 및 실제 B/구간 시각 대조 통과. 첫 그림의 caption 간격을 수정한 최종 PNG/SVG는 `../artifacts/isaac6/async_handoff_plots_03/`에 보존했다. 새 inference/navigation/Graph/영상 0회, 환경 변경 없음.
4. 작은 SVG/manifest, plot source와 [보고서](ASYNC_OLD_FRESH_HANDOFF_AUDIT.md)만 Git에 추가한다. PNG와 기존 raw는 Git에서 제외한다.

## Controlled latency handoff — 실행 준비

2026-10-17. 사용자 요청으로 기준 `671ea9732125be10d38b04d31d5ad03fe1723e85`에서 `research/isaac6-controlled-latency`를 생성했다.

1. Observation X [2.1, 2.4] m + 유효 OLD + 최초 accepted request에 한해 physical packet 수신 후 0.5 s를 IPC thread에서 지연한다. B0/B_delay 정의, 기존 geometric thresholds 및 OLD_EXECUTION_RISK 우선 분류를 실행 전에 [protocol](CONTROLLED_LATENCY_PROTOCOL.md), commit `131bb3e`에 고정했다.
2. Scene/model/checkpoint/native inference/원본 PD/coordinate/clearance 및 기존 scenario를 변경하지 않았다. 전달 옵션과 packet/release clock만 추가했다. OLD timeout은 유지하며 FRESH의 controller-side receive clock은 release 시각이다. 72 Hz 실행 thread는 hold를 기다리지 않는다.
3. Trigger inclusive boundaries/one-shot, monotonic deadline early wake, busy skip/queue isolation, OLD timeout/FRESH release, B0 first-tick 선택 및 기존 async/geometric tests 합계 **21 passed (0.09 s)**. 구문 검사/whitespace 검사 통과. 기존 baseline 205개 파일 hash 일치 및 pre-run preservation manifest를 별도로 저장했다.
4. 새 정상 navigation은 `../artifacts/isaac6/controlled_latency_01/`에 한 번만 실행한다. 기존 baseline 재실행, sweep, Graph, 영상/GUI 생성은 하지 않는다. 결과는 종료 후 추가한다.

## Controlled latency handoff — 단일 실행 결과

2026-10-17. [상세 보고서](CONTROLLED_LATENCY_HANDOFF.md). Clean runtime commit `1487acd`, 정상 navigation 1회/재시도 0회.

1. 최초 조건 만족 FRESH **54**, OLD **53**, observation pose `(2.105113842, -0.123311859, -1.085187329 rad)`, t_sim 14.5 s. 물리적 packet 수신 후 전달 지연 실측 **500.072776 ms**, 해당 GPU inference **29.559979 ms**. 지연은 한 번만 주입됐다.
2. B0 t=14.666666667 s, B_delay t=15.111111111 s. 사이의 32개 유효 OLD intervals에서 **0.088888889 m / +3.281076°** 추가 실행. Host switch 증가량 0.444725807 s는 9 Hz tick 위상을 반영한다. Hold 중 OLD timeout 0회, busy skip 2개(전체 3개), miss 0개. 모든 next-tick switch/pose 기록 일치.
3. B0 **ALREADY_CONSISTENT**, B_delay **STAGING_SUFFICIENT**. Entry 거리 0.000583→0.021058 m, connector clearance 0.330987→0.361717 m, 양쪽 entry 10/10 안전. B_delay에서 entry가 뒤쪽에 남아 bearing 168.30°지만 기존 제자리 회전+직선 staging family로 안전 연결 가능. FRESH full/prefix clearance 0.331248 m, OLD/FRESH 실제 구간 0.321651/0.376355 m 안전. **NO_QUALIFIED_CANDIDATE**.
4. Goal entry true, 26.222222 s, goal 거리 0.298718 m. 첫 왼쪽/둘째 오른쪽 통과, 전체 최소 swept clearance 0.080234 m, 충돌/corridor 침범 없음. Warm GPU median/p95 30.147740/31.740886 ms, RTF 0.999996588, pacing p95/max 0.153885/1.442259 ms. Async/controlled-delivery/soft real-time PASS.
5. 기존 validator의 99 raw/derived/PD/pose/clock/clearance 검증 통과. Baseline 205개 및 새 run 분석 입력 226개 hash 보존, 별도 raw-record 수치 검토 통과. Startup shader compile/renderer-step 오류 5개는 RGB gate 통과 이전이며 navigation clock과 구분했다. 기존 환경 변경 없음.
6. 같은 prediction의 두 boundary와 전체 장애물을 보여주는 비교 그림 한 장을 보존했다. 최초 close-up에 장애물이 보이지 않아 figure layout에 전체 위치도만 추가했으며 수치/threshold는 그대로다. Baseline/start/goal image hash 차이와 같은 run 내 B0 counterfactual 한계를 명시했다. 두 번째 장애물에 대한 FRESH clearance 약 54 cm 및 B_delay overlap 10.07 cm의 제한 때문에 좁은 통로·다른 latency로 일반화하지 않는다. 추가 실험/Graph/영상/GUI는 수행하지 않았다.

## Full-run uniform latency sweep — 실행 전

2026-10-17. 사용자 요청으로 `6eedeeb`에서 `research/isaac6-uniform-latency`를 생성했다. [Protocol](UNIFORM_LATENCY_PROTOCOL.md)을 `3f55d28`에 실행 전에 고정했다.

1. D0는 `async_wide_wall_01`을 재사용하고 D250/D500/D750 각 1회, 고정 순서로 실행한다. 모든 accepted result(초기 및 terminal-unapplied 포함)에 IPC packet 수신 후 동일 d를 적용한다. 기존 single-trigger class의 AST가 변하지 않았고 기존 core/controller/model/scene/checkpoint/좌표/clearance/seed schedule을 유지했다.
2. 새 uniform 정책과 deadline/timeout/OLD window 분리 및 기존 async/geometric tests **30 passed (0.09 s)**. D0 93개 handoff를 새 offline 분석으로 재계산해 이전 class 및 position/heading mismatch median/p95/max가 일치했다. 실패 run과 unapplied result도 분석하며 실제 OLD 위험과 geometric class를 별도 기록한다.
3. Baseline 205개 + 직전 controlled run 226개, 총 **431개** input hash를 실행 전 확인·보존했다. 새 결과는 별도 raw/audit 폴더에 저장하며 원본을 덮어쓰지 않는다. 추가 figure/GUI/영상/Graph/Topomap은 만들지 않는다.

## Full-run uniform latency sweep — 실제 결과

2026-10-17. [상세 보고서](UNIFORM_LATENCY_SWEEP.md). Clean runtime `25bed71995c406be270441854bd1c4a7c32af394`에서 D250/D500/D750 각 1회, 재시도 없이 완료했다. 모든 process exit 0, D0 navigation 재실행 없음.

1. 모든 accepted result 45/45, 23/23, 18/18에 동일 전달 지연 적용을 확인했다. 실측 packet→release median 250.075/500.074/750.072 ms, warm GPU median/p95 30.129/31.938, 30.544/32.188, 30.150/33.486 ms. 실제 GPU delay와 post-inference delivery delay를 구분했다.
2. 새 3개 run 모두 corridor footprint 침범으로 goal 실패, 종료 23.18056/17.30556/18.31944 sim s. 최소 goal 거리 2.47177/2.62027/2.43429 m. 장애물 overlap/2 cm margin 위반은 0회이며 corridor 실패와 구분했다. 첫 장애물 왼쪽 통과, 둘째 통과 전 중단. D0의 성공 결과를 보존했다.
3. 실제 handoff OLD 이동 median은 D0/D250/D500/D750 .02778/.08056/.12500/.18333 m, yaw median 1.15/8.28/12.09/20.69°. 모든 soft real-time/clock/output/controller/pose 검증 PASS. 새 run pacing p95 <.156 ms, max <1.575 ms. D750은 1초 timeout 2회와 실제 zero-motion intervals를 확인했고 나머지는 자연 timeout 없음.
4. 실제 handoff 수 93/44/21/16, 유효 correspondence 87/24/4/1. Qualified candidate 전부 0개. 새 조건의 classifiable fraction은 59.09/19.05/6.25%로 기존 90% negative-verdict 기준에 못 미쳐 **INSUFFICIENT_EVIDENCE**. D0만 기존 **NO_QUALIFIED_CANDIDATE** 유지. 가능한 entry는 모두 안전한 staging connector가 하나 이상 있었으며 큰 RMSE/방향 변화만으로 Graph 후보를 만들지 않았다.
5. D250 FRESH 23/28은 tail unsafe이나 prefix/실제 실행은 안전했다. 마지막 적용 ID 44/21/16의 실제 PD 실행은 corridor를 침범했지만 correspondence/prefix heading이 무효라 candidate 판정 보류. D500 pending ID 22는 GPU inference 중 OLD 21이 위험해졌고 FRESH도 corridor unsafe. D750 pending ID 17은 안전한 prediction이나 delivery hold 중 OLD 16이 corridor를 침범했다. 두 pending 결과에 실제 switch B를 만들지 않고 OLD_EXECUTION_RISK로 별도 보존했다.
6. 이전 431개 입력 hash와 새 251개 audit 입력 hash 보존, 보호 source 11개 및 checkpoint 불변. Source/문서/약 349 KB의 작은 CSV·JSON만 추적하고 raw는 별도 artifacts에 유지한다. D0와 새 run 간 RGB/seed-observation 대응 차이 및 단일 시행의 인과 해석 한계를 명시했다. Graph/Topomap/추가 주행·시각화·영상·GUI·환경 변경 없음.

## Uniform latency 주행 결과 그래프

사용자 후속 요청으로 D0/D250/D500/D750의 기존 world pose를 각각 PNG/SVG로 그리고, 동일 축의 2×2 비교 그림을 추가했다. 실제 경로·방향·장애물·목표·종료 pose와 9 cm footprint를 표시했다. D250은 아래쪽, D500/D750은 위쪽 corridor footprint 침범이며 D0의 목표 진입과 구분된다. 새 navigation/inference 0회, smoothing 및 기존 판정 변경 없음.

Plot 입력 472개 hash 불변, 시작/종료 pose·72 Hz 시각·goal metric 대조 PASS. 5개 PNG의 layout을 확인했다. 재생성 source, SVG/manifest 및 문서만 추가하며 PNG는 `../artifacts/isaac6/uniform_navigation_plots_01/`에 보존한다. [그림 링크](UNIFORM_LATENCY_SWEEP.md#후속-요청-각-조건의-실제-주행-그래프).

## Sudden obstacle pilot — 실행 전

사용자 요청으로 `8e157a7`에서 `research/isaac6-sudden-obstacle`을 만들었다. [Protocol](SUDDEN_OBSTACLE_PROTOCOL.md)과 새 scenario를 실제 실행 전에 `b2155f0`에 고정했다. 중심 `(2.45,-.18)` m, 크기 `(.35,.35,.8)` m, spawn tick 970 / 13.472222222 s, 추가 delivery latency 0 ms, navigation 1회/재시도 없음.

기준 성공 run의 spawn pose clearance .127289 m, OLD 49의 새 장애물 full/prefix clearance −.09/.037442 m를 선정 근거로 보존했다. USD time-sampled visibility와 integer-tick collision gate를 추가했으며 첫 active tick의 zero-duration 검사/이전 interval 소급 제외/다음 full swept 검사 및 기존 async/geometry tests **30 passed (0.15 s)**. 원본 controller/model/core/clearance와 정적 scenario 불변, 기존 698개 입력 hash 보존. RGB·instance mask를 observation별 저장하고 최초 visible FRESH의 실제 worker history hash와 대조한다. 결과에 따라 위치·크기·seed를 바꾸지 않는다.


## Sudden obstacle pilot — 단일 실행 결과

2026-10-17~18 KST. [상세 결과](SUDDEN_OBSTACLE_PILOT.md). Clean runtime `4dbea71`, navigation **1회**, 재시도/geometry·seed 조정 0회. 추가 delivery latency 0 ms.

1. Tick 970 / 13.472222222 sim s에 중심 `(2.45,-.18)` m, 크기 `(.35,.35,.8)` m 장애물이 활성화됐다. 실제 spawn pose `(1.977326927,.022482045,-1.334215243 rad)`, footprint clearance .208938993 m. 이전 970 rows에서 collision 비활성, 이후 1,456개 swept 검사를 재계산했다.
2. Instance mask는 모든 135 frames에서 0 / 빈 ID를 기록해 **계측 FAILED**. Label mapping 원본 미보존으로 정확한 원인은 확정하지 않았다. 주행을 반복하지 않고 원본 RGB 53/54를 직접 확인했으며 기존 magenta 식을 전체 RGB에 적용하는 offline 복구를 명시했다. 출현 전 54개 RGB 모두 0 pixels, 첫 visible RGB 54 / 13.5 s에서 20,602 pixels. Raw mask와 metadata는 그대로 보존했다.
3. 최초 visible FRESH **50**, history [51,52,53,54] / [12.75,12.986111111,13.25,13.5] s. 전체 131 worker input hash 일치. 원본 CPU preprocessing의 마지막 frame에 2,491 pixels가 남으며 최초 3 frames는 0. OLD **49**, 실제 FRESH switch 13.666666667 s, B `(1.986426397,-.015327282,-1.335025651 rad)`. FRESH 관측/적용 근거는 RGB로 확인했으며 mask gate PASS로 바꾸지 않았다.
4. OLD/FRESH 새 장애물 full clearance .101933001/.171541004 m, prefix .161912916/.171541004 m. **OLD_SAFE_FRESH_SAFE**. 출현→switch의 실제 OLD 이동 .038888889 m, yaw −.046433°, dynamic clearance .198573583 m. 실제 FRESH 다음 switch까지 .189413022 m로 안전했다. Position RMSE .073165248 m / tangent heading RMS 28.158651°지만 B→entry .034522079 m, tangent 차이 2.674131°, connector clearance .188255291 m, 16/16 entries 안전. **ALREADY_CONSISTENT / NO_QUALIFIED_CANDIDATE**.
5. Goal entry 33.680555556 s, min goal .298252070 m. Static 1/2/dynamic minimum swept clearance .073508257/.566122074/.180577735 m, overlap/corridor 침범 없음. Corridor clearance .013217019 m는 containment를 만족하나 .02 m wall margin을 주장하지 않는다. Warm GPU median/p95 29.689112/31.502001 ms, pacing p95/max .152915/1.384874 ms, RTF .999996807. Request/receive/switch 131/131/131, busy skip 1, miss 0, timeout 0(자연 timeout 미검증), 기존 async 검증 PASS.
6. Baseline과 실제 spawn pose가 9.47 cm/−32.63° 달라 OLD 위험이 재현되지 않았다. Actual obstacle center bearing 53.26°로 왼쪽 RGB에 부분 출현했다. Noise/DDPM seed 199/200→201/202 차이도 존재해 안전한 FRESH의 생성이나 revision을 장애물 반응만의 효과로 주장하지 않는다. Graph가 해결할 후보는 없었다.
7. 기존 698/new 565 input hashes 보존, 공식 train/deployment 및 보호 source 9개 불변. 원래 mask audit와 첫 RGB 복구 float32 JSON export 실패 기록을 보존하고 최종 offline audit를 별도 폴더에 생성했다. Source·작은 CSV/JSON·원본 RGB를 포함한 비교 SVG 한 장을 추가했다. Runtime 계측 실패는 그대로 공개하며 추가 navigation/inference/Graph/Topomap/영상/환경 변경 없음.

## Sudden obstacle — 전체 주행 재생 요청

2026-10-18. 후속 사용자 요청으로 출발부터 목표 진입까지 전체 실제 pose를 기존 Isaac renderer로 재생했다. MP4 1280×720/H.264/24 fps, 810 frames/33.75 s에 t=0…33.680555556 s 및 마지막 실제 pose를 보존했다. 새 navigation/inference 0회. 원래 DynamicObstacle visibility time samples를 유지하고 숨김→출현 전환을 전체 overhead RGB로 검증했다. 원래 inference instance mask 실패와 별도다.

전체 video decode/mapping, GUI 2,426 pose(최대 오차 6.66e−16), 원래 104 prim의 attributes/relationships/time samples 보존을 확인했다. GUI 자동 재생 `playing=true`, 실제 sample pose 일치, startup Error 0개를 확인하고 창을 열어 두었다. Renderer 최초 RGB 준비 전 step 오류 5개는 로그에 보존했다. 기존 698/new 565 input hashes 유지. 파일은 `../artifacts/isaac6/sudden_obstacle_video_01/`, [상세 재생 설명](SUDDEN_OBSTACLE_PILOT.md#후속-요청-출발부터-목표-도달까지-전체-주행). Renderer의 scenario 기반 자막/반경과 dynamic visibility 확인, 작은 video validation JSON 및 문서만 Git에 추가한다.


## Actual OLD rollout obstacle — 실행 전

2026-10-18. 사용자 요청으로 `9792056`에서 `research/isaac6-old-rollout-obstacle` 생성. [Protocol](OLD_ROLLOUT_OBSTACLE_PROTOCOL.md)/새 scenario를 `84118c3`에 실행 전 고정했다. Tick 970의 실제 applied OLD pose/command/receive-based remaining timeout만 사용하며 arc length [.42,.45,.48] m의 최초 유효 후보를 선택한다. 최초 .55 s 동안 .02 m margin, 현재 footprint .10 m clearance, 남은 timeout 안의 counterfactual collision, FOV/LOS/static/corridor 및 빈 side strip을 요구한다. No valid placement면 중단하며 navigation 1회/재시도 없음.

동일 resolved geometry를 execution snapshot과 main-thread USD update에 사용하고 RGB magenta 검출을 사전 gate로 정했다. 기존 instance mask 기능은 수정하지 않았다. Synthetic exact arc/timeout/infeasible/RGB와 pending result가 있어도 실제 applied OLD를 사용하는 thread snapshot 검증 및 기존 async/geometric tests **35 passed (0.20 s)**. 이전 1,266개 input hashes, 원본 train/deployment 및 보호 source 9개 불변. 과거 저장 pose를 이용한 배치 함수의 offline 예시는 계산 약 1.23 ms였으며 새 주행 결과나 배치 보장이 아니다. 실제 run은 `../artifacts/isaac6/old_rollout_obstacle_01/`에 한 번만 실행한다. 추가 latency/Graph/Topomap/영상/GUI 없음.


## Actual OLD rollout obstacle — 단일 실행 결과

2026-10-18. Clean runtime `9dd129d`로 navigation **1회** 실행, 추가 지연 0 ms. Tick 970의 applied OLD 49 `(v,w)=(.2,.268792886)`와 remaining timeout .856371351 s에서 고정 후보 .42 m 거부/.45 m 채택. Dynamic center `(2.405633551,−.195502975)`, 최초 footprint clearance .112504 m. Counterfactual OLD를 유지하면 약 .699605 s에 contact하며 timeout 안에 overlap witness가 존재했다. 첫 .55 s clearance .021154 m로 사전 반응 조건도 충족했다. Rendering과 monitor의 실제 resolved AABB 일치, 배치 계산 1.409 ms.

최초 visible observation 54의 RGB magenta 47,101 pixels, 출현 전 전부 0. FRESH 50의 [51,52,53,54] worker input history hash 일치, 공식 CPU preprocessing 후 96×96 frame에서도 5,629 magenta pixels 확인. 새 inference 없음. FRESH 50 full/prefix clearance +.037542 m, OLD native full −.09 m/prefix +.035650 m. 출현→switch 194.640 ms(host), OLD 실제 이동 .038889 m/yaw +2.9946°, 실제 minimum clearance .078737 m. **UNSAFE_OLD_SAFE_FRESH**.

B→entry .006655 m, tangent 10.760°, connector clearance .072366 m 및 10/10 safe entry. 기존 correspondence는 `nonmonotone_forward_station`으로 invalid여서 revision 통계를 만들지 않았다. Graph 판정 **INSUFFICIENT_EVIDENCE**, qualified candidate 미확인. 최초 FRESH 50 실제 실행도 .044172 m clearance로 안전했다. 이후 safe prediction 51의 실제 PD 실행은 .019188 m로 margin 미충족, unsafe full/prefix prediction 52 실행 중 14.305556 s에 dynamic geometric collision로 종료. 당시 FRESH 53 GPU inference 진행 중이었고 수신 후에도 switch 없이 보존했다. 최초 handoff와 이후 failure를 분리했다. Goal false, corridor 침범 없음. 재시도/튜닝 없음.

Warm GPU median/p95 30.782/33.078 ms, RTF .999990, pacing p95/max .154/1.423 ms. 54 request/54 received/53 switch, busy 1/missed 0/timeout 0(실제 timeout은 NOT_EXERCISED). 최소 tests 35 passed, 원본 PD/raw scaling/anchor/pose/clock/clearance 검증 PASS. RGB 준비 전 renderer step error 5개는 원본 로그에 남겼다. Prior 1,266/new 257 input hashes 및 보호 source 9개/공식 train·deployment 불변. Raw `../artifacts/isaac6/old_rollout_obstacle_01`, 최종 offline audit `old_rollout_obstacle_audit_02`; audit 01도 보존. 작은 JSON/CSV/SVG 한 장과 [상세 보고서](OLD_ROLLOUT_OBSTACLE_PILOT.md)를 추가했다. Post-run 수정은 offline analyzer/documentation뿐이며 새 navigation, Graph, Topomap, 영상, 환경 변경 없음.


## Actual OLD rollout obstacle — 49–53 확대 그림 요청

2026-10-18. 사용자가 요청한 장애물 부근 확대 그림 한 장을 추가했다. Native sample 0 예측 49–53과 실제 center path, index 2, observation O49…O53, 실제 switch S49…S52, 원본 applied command별 execution segment, 진행 화살표, spawn 및 충돌 footprint를 표시했다. 53은 terminal unapplied이므로 S53/실행 경로를 만들지 않았다. 각 marker는 72 Hz trace와 일치하고 colored interval incoming ID를 검증했으며 원본 257개 input hash 보존. 한글 PNG/SVG 육안 검토 완료. 새 navigation/inference 없이 기존 raw/그림을 유지하고 `old_rollout_obstacle_detail_01`에 별도 저장했다. Plot script·작은 manifest/SVG 및 문서만 commit한다.


## Prediction 50→51→52 방향 반전 및 B52 counterfactual

2026-10-18. `31f7881`의 저장된 `old_rollout_obstacle_01`만 분석했다. 51→52에서 local dy −.018535→+.043183 m, 원본 unclipped w −.904530→+2.410915 rad/s로 부호가 바뀌며 clipping 후 −.4→+.4다. 52 native full/prefix는 observation anchor부터 −.071843/−.038028 m로 unsafe. B52 기준 world selected point의 local 표현은 (.035526,.045640) m이며 PD 결과 (.142104,+.4); 회전 부호는 같고 v가 28.948% 줄었다.

동일 B52에서 실제 14 tick/.194444 s 구간만 비교: RAW52 clearance −1.262mm/overlap, HOLD51 +1.369mm/no overlap, OBS-ANCHORED52 +4.658mm/no overlap. B52 초기 clearance부터 19.190mm로 20mm margin 미달이고 **세 조건 모두 margin 미달**이다. 실제 51은 충돌하지 않았으나 margin을 소진했다. RAW52 및 실제 50–52의 전체 pose/각 tick swept 값은 저장값과 최대 오차 0. HOLD51의 timeout은 종료까지 유효하다. Counterfactual의 단기 no-overlap을 safe navigation이나 correction 검증으로 해석하지 않는다.

Unsafe prediction/원본 PD 실행과 frame mismatch를 분리했으며 qualified Graph 후보는 입증하지 못했다. 53은 미적용, 49는 참고로만 유지. 기존 함수만 재사용해 작은 JSON/CSV와 [분석 보고서](PREDICTION_50_52_DIRECTION_REVERSAL.md)를 추가했다. 원본 257개 input hashes, 기존 분석·확대 그림 및 보호 source 9개 유지. 새 navigation/inference/시각화/test/Graph/새 correspondence/환경 변경 없음.


## B51 speed-only safety feasibility

2026-10-18. 기준 `6f8267b`의 저장된 run으로 offline oracle 검증. B51 tick1000 pose `(2.097864810,−.001133875,−.966924877)`, dynamic clearance 4.417414cm/timeout 잔여 .942698s. 실행 전 protocol에 v=[0,.02,…,.20] 11개, w=−.4, H1=16ticks/H2=30ticks를 고정했다. FRESH52/53 및 이후 실제 pose/clearance는 속도 선택에 사용하지 않았다. 선택 후 H1 RAW51의 17pose/16interval을 검증했고 pose·static/dynamic swept·corridor 오차 모두 0이다.

Grid 최대 feasible v는 H1 .18m/s(10% 감소, clearance 2.154597cm, 전진4cm), H2 .10m/s(50% 감소, clearance2.206896cm, 전진4.166667cm). RAW .2m/s는 H1 1.918788cm/H2 .136918cm로 margin 미달이나 geometric overlap은 없다. 최초 미달은 H1 마지막 interval [14.097222222,14.111111111]s. B51부터 .10m/s를 한 번 선택해 유지하면 H1 prefix도 3.097952cm로 안전하며 중간 감속 스케줄은 없다. `(0,0)` 정지는 별도 trivial reference로만 저장했다.

이번 정확한 geometry/제한 horizon에서는 전진하며 감속만으로 충분해 Graph 필요성 근거를 추가하지 못했다. H2 RAW·보정은 실제52실행과 다른 counterfactual이며 온라인 geometry 인지/후속prediction/목표도달은 미검증. 작은 protocol/summary JSON, 22행 grid·6행 comparison CSV 및 [보고서](B51_SPEED_CORRECTION_FEASIBILITY.md)만 추가했다. 257개 run inputs, 이전 분석·그림과 보호 source9개 hash 유지. 새 navigation/inference/시각화/test/실행코드 변경 없음.


## Isaac Sim Topomap — reference 생성 및 단일 정적 주행

2026-10-19. 사용자 지정 `c6a72d5`에서 별도 `research/isaac6-topomap` 생성. 성공 reference `async_wide_wall_01`의 tick0,72,…,1728,1770에서 실제 정적 RGB26장을 렌더링했다(새 navigation/inference0회). Node pose/PNG/pixel hash와 원래 execution SHA를 새 manifest에 저장했다. 최대 USD pose 오차3.33e−16. 공식 radius4의 inclusive/+1 candidate 범위(최대10개), argmin/strict distance<3/clamp/closest 갱신을 그대로 사용하며 pose로 localization하지 않는다. 선택 condition에만 diffusion10steps를 한 번 적용했다.

Protocol·adapter `5b05a1c`, GPU 및 최소 tests 검증 후 clean runtime `fd125a4`에서 navigation1회. CPU tests17 passed; 실제 GPU의 official encoder/distance 및 동일 condition/noise/DDPM seed decoder가 bitwise equal, 차이0. 실제 component 호출 encoder1/distance1/noise10 확인. Model/checkpoint/original PD·좌표·geometry·4/9/72Hz·1초 timeout·seed101+2k/추가지연0 유지.

**Topomap 기술검증 PASS / navigation 실패**. Request/receive/switch52/52/52, 첫 장애물은 왼쪽11.722222s 통과, 두 번째 미도달. 13.902778s pose `(2.025235709,1.411507114,.740370522)`에서 corridor footprint stop; actual wall footprint intrusion1.507mm. Static obstacle clearance .432678/.634763m 및 no box overlap이지만 corridor 하한−.001509m, goal false/min distance2.849002m. 최종closest7/goal25, 최대closest11, closest역방향5/subgoal역방향6. 첫 장애물 X범위에서 steering부호반전8개와 node11→7→3 후퇴 관찰; 원인별 기여나 동적 회피 성능으로 확대하지 않았다.

Warm inference median/p95 36.579/52.610ms(reference29.187/31.903), 실제 waypoint적용3.991Hz(reference4.005). Timeout0/busy1/missed0, RTF.999993906, pacing p95/max .145488/1.293862ms. Input history RGB/선택score/원본PD/normalization·sample0·index2/observation anchor/모든 pose·swept·corridor 검증 통과, integration/corridor error0. Reference203/OLD-rollout257/synchronous484 hashes 보존. Reference rendering startup error6/navigation startup error5는 로그에 보존 후 RGB gate 통과. Retry·threshold/spacing tuning·Graph·smoothing·recovery·dynamic실험·video/GUI재생 없음. 작은 JSON/CSV/XY SVG 한 장과 [보고서](ISAAC6_TOPOMAP_NAVIGATION.md) 저장. 기술 연결은 준비됐으나 성공한 정적 Topomap baseline은 미확보이므로 후속 sudden-obstacle 비교의 전제는 아직 충족하지 못했다.


## Topomap 정적 경로 이탈 원인 분석

2026-10-19. 기준 `edf716e`에서 `research/isaac6-topomap-drift-audit` 생성. 저장된 Topomap run의 1,002개 실제 pose를 성공 reference 1,771개 pose의 polyline에 공간 projection했다. 동시각 correspondence는 사용하지 않았고, 정지 segment 80개 제외·1mm 근접 projection의 arclength 폭 10cm 초과 규칙에서 모호한 pose 0개다. 첫 20cm 초과는 tick636/8.833333s, ID30 실행 중 +.200121247m. 직전 tick .198785730m이며 이후 12s까지229/229 pose와 종료까지 초과 유지, 12s .633105m/종료 .988399m.

ID30 closest/SG9는 geometric nearest8과 한 node 차이지만 B30 reference projection보다 .148821m 앞이다. B30 yaw는 reference tangent보다 +28.842°이며 원본 PD (.2,−.251488) 실행으로 이탈 .184052→.205454m. Native tail은 오른쪽으로 더 굽지만 실제로는 index2의 고정 PD arc만 실행했다. ID34(SG9),36·37(SG10)은 동일 SG에서 dy/각속도 부호가 바뀌었고 clipping이 부호를 만든 것은 아니다. Observation은 각각 약5cm 이동, yaw/RGB/seed도 바뀌므로 diffusion 단독 원인으로 확정하지 않는다.

작은 closest 후퇴8→7→6은6.889/7.111s에 선행했으며, ID21·27의 뒤쪽 SG 선택도 있었다. 큰11→7→3 후퇴는11.667/12.111s, 이미 .569793/.654804m 이탈 후다. 후퇴 전 closest/SG9 고정 중에도 .1841→.3078m,10 고정 중 .3078→.4078m 증가했다. 따라서 큰 후퇴를 최초 원인으로 볼 수 없으며 early localization/subgoal 기여와 Sample0/PD 실행을 분리했다. 단일 원인 판정 `INSUFFICIENT_EVIDENCE`.

기존함수/CSV 재사용, 52개 selection/history/PD/실행interval 일치. Pose·PD 오차0, swept/corridor오차2.22e−16m. 기존117개 run hash 포함208개 input/result/RGB 보존, 새 runtime 변경·test·시각화·navigation·inference 없음. 작은 CSV2/JSON2와 [보고서](ISAAC6_TOPOMAP_DRIFT_ANALYSIS.md), 재현 가능한 offline analyzer만 추가했다. 다음 최소 검증은 저장된 ID34의8sample을 동일 B34/실제 다음switch 구간으로 비교하는 한 가지이며 이번에는 수행하지 않았다.


## Topomap 간격 2초 — 사용자 요청 단일 주행

2026-10-19. 사용자의 간격 확대·실행 요청에 따라 `b2d490a`에서 `research/isaac6-topomap-2s` 생성. `d1b3b86`에 protocol/간격 변경을 사전 고정했다. 기존 reference RGB parent IDs0,2,…,24,25의 PNG를 그대로 복사해 14node/2초 간격으로 구성했고 시작·최종24.583333s 포함, 새 reference render0회. Node spacing median .397388m. Radius4/threshold3, checkpoint/모델/PD/scenario/seed schedule/4·9·72Hz/1초timeout/추가지연0을 유지했다.

기존 tests17passed, 새 map GPU 동등성 bitwise equal/최대오차0. Clean d1b3b86에서 navigation1회/재시도0. **25.305556s goal entry 성공**, 최종거리 .297394m, pose `(4.206426199,−.047513042,.273984436)`. 장애물1왼쪽10.986111s/장애물2오른쪽20.902778s 통과. Min swept clearance .279149/.074423m, overlap없음/2cm충족, corridor minimum+.778398m. 98request/receive,97switch,마지막ID97미적용. Warm inference35.182/46.586ms(median/p95), waypoint4Hz, timeout0/busy1/missed0. RTF .999994655,pacingp95/max .151901/1.205512ms.

실제 score/선택/workerhistory/normalization/원본PD/anchor/pose/clearance 검증PASS, integration/corridor오차0. 이전1초run117개·기존syncbaseline484개hash 보존. Startup renderer error5개 이후RGBgate/주행정상완료. Closest후퇴11/subgoal후퇴13/turn반전23회는 남아있으며 안정성 일반화나 간격만의 인과효과를 주장하지 않는다. 두실행은 RGB/관측시각/seed대응이 다르다. 새 raw `topomap_static_2s_01`, map `topomap_reference_2s_01`, 작은JSON/CSV/기존report의XY그림과 [보고서](ISAAC6_TOPOMAP_2S_NAVIGATION.md) 저장. Dynamic/Graph/reranking/recovery/추가sweep/영상/GUI실행 없음.


## 2초 Topomap + 실제 OLD rollout sudden obstacle

2026-10-19. 기준 `62809c0`에서 `research/isaac6-topomap-sudden-obstacle` 생성. 좁은 async/zero-extra-delay 조합 gate와 기존 scenario/map hash 고정 protocol을 `be51bb4`에 사전 commit했다. 14-node map/모델/공식 선택/PD/placement/4·9·72Hz/1초 timeout/seed를 유지하고 tests33passed 후 clean runtime에서 navigation **1회, retry0회** 실행했다. 기존 static2s 성공 run은 재실행하지 않았다.

Tick970/13.472222s, OLD49 `(.2,−.4)`/timeout잔여 .852955s의 첫 .42m 후보가 통과해 box `(2.372279542,.110674603)`에 배치됐다. 초기 clearance .106013m, .55s 반응 구간 .021761m, 동일 OLD 유지시 약 .699936s 뒤 접촉/timeout 내 overlap이다. Renderer/monitor geometry 일치, 첫 RGB54(tick971)에 magenta46,570pixels, 출현 전0. FRESH50의 실제 [51,52,53,54] history hash 일치. 출현→첫 switch OLD 실제 .038889m/−4.4563°, clearance .079174m로 안전했다.

첫 FRESH50 native full/prefix .030975/.059524m, 실제 .048466m; 8 samples full안전4/8(0,1,5,6), prefix/origin-prefix8/8, 좌/우4/4. 이후51도 native .052852m/실제 .023339m 안전. **52는 native .026485m 안전이나 실제 .002654m로 margin 미달**, 첫 미달14.152778s. **53 native .002057m margin 미달(양수, overlap 아님), 실제 −.000941m overlap으로14.375s 중단**. Goal false/min2.200973m, 정적box와corridor 침범없음. `UNSAFE_OLD_SAFE_FRESH`, `LATER_UNSAFE_FRESH`, `HANDOFF_OR_EXECUTION_FAILURE`를 사건별로 구분했다.

OLD49→50은 동일SG2에서 −.4→+.340089 반전했지만 첫 FRESH 이후50→51→52→53은 양의w 유지, SG2→6→9→9/후퇴없음. 모든54개 Topomap score/선택/worker/switch 검증PASS. First B→entry .005640m/connector .079176m, 52 connector도 .023340m로 안전한 entry4개. 기존 correspondence invalid로 revision 통계를 만들지 않았고 qualified Graph 후보 미확인/근거 `INSUFFICIENT_EVIDENCE`. Unsafe53 upstream과 safe-native52/PD 실행 차이를 확인했으나 anchor/PD 각각의 인과기여는 미확정이다.

WarmGPU median/p95 35.536/53.096ms, request/receive/switch54/54/54, 모두적용. Busy1/missed0/timeout0(자연timeout NOT_EXERCISED), RTF .999993035,pacingp95/max .147790/1.082767ms. Pose integration오차0, 원본PD/scaling/anchor/swept 검증PASS. Prior488/new257 input hashes 보존, execution source36개 중34개 동일(2개는 post-run report표기만 수정), 공식train/deployment diff없음. Startup renderer error5개 로그보존 후RGBgate통과. 기존 fixed-goal pilot과 event별로만 비교했고 causal 개선효과를 주장하지 않았다. 작은JSON/CSV, 기존plot의XY그림 한 장, [상세보고서](ISAAC6_TOPOMAP_SUDDEN_OBSTACLE.md)를 저장했다. 추가navigation/inference, Graph, reranking, recovery, 영상, 환경 변경 없음.


## Topomap sudden obstacle — FRESH 50–53 왼쪽 회전 그림

2026-10-19. 사용자 요청에 따라 저장 데이터만으로 native 8점/실제 경로/B50–B53, 실제 PD w 시간축, 실제 yaw 시간축을 한 그림에 표시했다. w=+.340089/+.4/+.4/+.4, yaw −45.881°→−30.410°로 모두 왼쪽 회전이며 world Y 감소와 구분했다. 원본 PD·9Hz command·72Hz pose/incoming ID·yaw increment 검증, 기존257개 raw hash 보존. PNG/SVG 육안 검토 완료, 원래 그림·결과 보존, 새 주행/inference0회. 별도 `topomap_left_turns_01` 저장 후 plot source/작은manifest/SVG와 문서만 추가했다.


## Topomap Oracle Safety Stop — 사전 검증

2026-10-20. 기준8307288에서 별도 research/isaac6-topomap-oracle-stop 브랜치. 실제9Hz 원본PD 계산 직후 actual integration 명령만 opt-in STOP override한다. Tick970 실제 adaptive spawn 이후16/72초 horizon, swept obstacle>=.02m 및 corridor containment, 원래4/9/72Hz·timeout·worker·Topomap·placement 유지. Nominal/actual 별도 로그, waypoint 갱신 중 정지 가능. 저장된B52 RAW clearance .002653804024m 위험/STOP .023340344453m 안전, RAW16pose 오차0. 최소 신규2개+기존tests 총23passed; prior745hash 및14node map 검증PASS. Protocol/code commit 후 clean 상태에서 단일 navigation1회/재시도0회 예정. [보고서](ISAAC6_TOPOMAP_ORACLE_SAFETY_STOP.md).


## Topomap Oracle Safety Stop — 단일 closed-loop 결과

2026-10-20. Clean32ca832에서 기존Isaac6/NoMaD 환경으로 navigation1회/재시도0회. 결과 **SAFE_BUT_STUCK**: 60s timeout, goal false/min distance2.267660m. Tick970 OLD49 기반 dynamic center(2.354396712,.077716494), 실제placement/render/monitor 일치. Static1/2 최소clearance .300221/.397675m, dynamic .024828160m, corridor .725852m. 충돌·2cm위반·검사시이미위반 모두0.

Tick976부터gate활성, 첫STOP13.888889s의 현재46.871mm/예측17.869mm. 4stop episode 총45.777778sim s; FRESH54/56/70에서각8tick씩3회재출발했으나18.777778s 이후종료까지정지. 정지중183RGB/184FRESH수신, 전체236request/receive/switch, timeout0/busy1/missed0. 최종정지중71–235 계속수신됐으나 nominal short rollout 모두2cm미달. 원본waypoint/PD/worker/Topomap를 유지하고 actual명령만(0,0)으로차단했다.

WarmGPU35.543/37.311ms,gate2.631/3.458ms median/p95. RTF.99998957,pacingp95/max .153/1.412ms,asyncPASS. 4321pose/540control,nominalPD와actual적분,normalization·observationanchor·Topomap선택·RGBhistoryhash·dynamic및corridor재계산PASS/최대오차0. 모델환경·checkpoint동일,기존745hash보존,새input999hash검증. Startup renderer error4건보존후RGBgate통과. Natural timeout NOT_EXERCISED,syntheticPASS. 새 raw/작은JSON·CSV·XY그림한장과 [보고서](ISAAC6_TOPOMAP_ORACLE_SAFETY_STOP.md). 기존collisionbaseline과는adaptive위치·RGB가다른비paired비교; oracleSTOP의안전정지와navigation성공을구분. Graph/recovery/reranking/추가실험없음.


## Early fixed obstacle + online Graph — 사전 고정

2026-10-20. Runtimea76ed2b / Graph3a60531에서 research/isaac6-early-online-graph 생성. 새fixedcenter(2.372279542,.110674603),size(.35,.35,.8),tick792/11s scenario만추가; 기존adaptive/frozenvalidator보존. 저장reference11s clearance.4263/.4653m 및FOV/occlusion/boxseparationPASS. 필요Graph정의8개AST동일,원래factorprotocol byte동일. 별도CPUprocess(systemPython/SciPy1.11.4) B52단일preflight solve1.765s,기존해1e-9내동일,21testsPASS. 1744 prior hash항목보존. Stop-and-plan에서1outstanding,FreshID당1attempt,원래1초timeout은nominal에유지; 늦은Graph는B/geometry/safety재검사후최대16tick별도action. VLA관측계속. Protocol/codecommit후EARLY-RAW/GRAPH각1회,재시도0회. [보고서](ISAAC6_EARLY_ONLINE_GRAPH.md).

## Early fixed obstacle + online Graph — 실제 closed-loop 결과

2026-10-20. Clean `7428f28`에서 EARLY-RAW/GRAPH 각 1회, 재시도·튜닝 0회. 두 run 모두 tick792에 동일 fixed box 활성화, 첫 visible RGB45/11.236111s 확인. RAW는 동적 장애물을 왼쪽으로 17s에 통과(clearance22.320mm)했으나 Static2에 17.152778s 충돌(−.509mm), goal false/min1.869510m. FRESH63/64의 Static2 native prefix도 unsafe여서 upstream prediction과 실제 PD 실행의 위험을 함께 확인했다.

GRAPH는 **SAFE_BUT_STUCK**, 60s timeout/goal false/min2.342423m. Dynamic clearance21.406mm, static1/2 .369350/.468548m, overlap·corridor·2cm 위반 없음. Dynamic과 Static2는 미통과. 고유 FRESH18개 시도 중13개는 기존 heading 규칙 미충족으로 solve하지 않았다. 실제 solve5회/수렴3회/안전 재검사 통과 및 실제 적용2회. 다른 수렴1개는19.086mm로 차단,2개는200nfev 미수렴. 마지막 pending 결과는 종료 후 보존하고 미적용했다.

Graph6(FRESH58): 원본(.151153,+.4)→보정(.018810,+.4), Graph16(FRESH196): 원본(.2,−.287461)→보정(.017014,+.4). 각각8tick 동안2.090/1.890mm 전진 후 다음16tick 안전 검사에서 차단, 실제 Graph 전진 합3.980mm. 최신 nominal ID70/216과 오래된 Graph source ID를 구분해 기록했다. 이후 실제 이동 pose의 RGB75/221이 request71/217 입력에 포함돼 **Graph 제어→실제 pose→RGB→새 inference** 검증 PASS.

Solve wall median/p95/max5.859/23.404/23.740s, 주행 중 Graph 대기43.777778s/전체정지46.555556s. 대기 중 RGB175장/FRESH172개 수신 유지. 적용 input age3.166/5.111s는 원본1초timeout을 넘는 별도 Graph action이며 nominal timeout은0회. 72Hz RTF RAW.999994137/GRAPH.999985167, pacing max1.274/2.004ms로 execution은 유지됐으나 실시간 Graph 성공은 아니다.

모든 actual command/72Hz pose 오차0, swept/corridor오차1.11e−16m; nominalPD·Topomap·RGB history·observation anchor·single outstanding·B/geometry 재검사 PASS. 기존1744개/new1329개 hash 항목 보존, 모델환경/checkpoint/Topomap 동일. 첫 offline report의 파일 나열 순서 assertion은 ID 정렬로 수정 후 새 comparison_02에 분석만 실행했고 partial comparison_01은 보존했다. 작은 JSON/CSV와 실제 XY 비교 그림1장 및 [보고서](ISAAC6_EARLY_ONLINE_GRAPH.md) 저장. Oracle geometry·STOP과 계산 대기 효과를 분리했고 두 비paired 단일 주행으로 Graph 우월성·목표 성공을 주장하지 않는다.

## Phase 0-A — 독립 offline scenario feasibility checker

2026-10-20. 기준 `3ec84aa`에서 이후 인프라 작업용 `research/phase0-infrastructure` 생성. `research/nomad_phase0/`만 추가해 기존 exact SE(2) 적분·swept/corridor geometry 재사용. NoMaD/Topomap/PD/Graph/시나리오 변경 없음. `3637f5a`에 XY5cm/yaw64bin, 0.5s 전진 primitive5개(v=.2,w=0/±.2/±.4), weighted Hybrid A*, 30,000 expansion/120wall-s/60path-s budget 고정 후 S0/S2만 검사했다. 신규5+기존geometry6 tests PASS.

S0 `FEASIBLE`, S2 우측 `FEASIBLE`: 각각166 expansion,325 generated,44arc/45pose,4.4m/22s, goal거리.286888838m. 전체 swept 최소clearance21.829288mm, corridor .954015310m, overlap없음/pose재구성오차0. S2 dynamic clearance149.394826mm. 동일 witness가 첫 정적 장애물부터 음의Y를 택하므로 기존 실제 OLD 실행 pose에서의 recovery 가능성이나 NoMaD 성능으로 확대하지 않는다. S2는 등장 후 geometry를 전체 경로에 고정한 검사다.

S2 Dynamic–Static2 실제틈202.720458mm/요구220mm/부족17.279542mm 재현. 단순틈폭뿐 아니라 두 금지단면과 +Y벽, center-X선 재횡단 금지를 결합해 좌측 one-pass goal연결을 `GEOMETRICALLY_BLOCKED`로 판정. 한번 좌측통과후 앞쪽으로돌아와 우측으로빠지는 경로는 좌측성공으로 집계하지 않는다. 전체 S2는 우측witness가 있어FEASIBLE. S0 dynamic좌/우는N/A.

작은 S0/S2 JSON과 [보고서](PHASE0_A_SCENARIO_FEASIBILITY.md) 저장. 새 navigation/inference/시각화/환경변경/scene설계/runner/controller 없음. 탐색미발견은 불가능증명아님. 사용자 확인 연구계획7번 네항목(trajectory follower 전환, recovery 후진, oracle/depth 안전인식, 언어VLA 필수성)은 모두 `UNDECIDED`; checker의 전진 primitive와 정확한JSON geometry 사용은 이 정책들을 결정하지 않는다.

## Phase 0-B — 독립 Pure Pursuit 사전 고정

2026-10-20. 동일 `research/phase0-infrastructure`, 기준67c3304. S0 witness만 입력으로 별도XY follower 추가: lookahead.25m, constant v.2m/s, w±.4 clipping, endpoint1cm 정지,9Hz/72Hz/최대60s. 원본44개 .5s primitive는72Hz geometric reference 재구성과 exact replay에만 사용하며 follower에는XY만 전달한다. 장애물·goal·yaw/timestamp를제어입력으로전달하지않는다. 이미실행된구간을별도평가해충돌/복도이탈종료,2cm위반은기록만수행. 최소tests3passed; 코드·설정commit후 원본pose/primitive clearance 일치검증 및PurePursuit1회예정. 네미확정정책모두UNDECIDED. [보고서](PHASE0_B_PURE_PURSUIT.md).
