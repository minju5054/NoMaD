# NoMaD pretrained inference preflight

검증일: 2026-10-16, Asia/Seoul. **현재 RTX 5060 Ti에서 공식 checkpoint의 GPU inference 실행 가능.** Isaac Sim 연동은 아직 실행하지 않았다. 최종 기준은 `research/results/20261016_preflight_02.json`이다. 단계별 의미는 [ACTION_SEMANTICS.md](ACTION_SEMANTICS.md), 실패·수정 이력은 [WORK_LOG.md](WORK_LOG.md)를 참고한다.

## 저장소와 보존 범위

- Workspace: `/home/gpuadmin/Workspace/NoMaD`
- 시작 시 기존 연구 파일 없음. 루트 `.git`, `.agents`, `.aws`, `.codex`는 비어 있는 읽기 전용 디렉터리였으며 보존했다. 루트 자체는 Git repository가 아니었다.
- 실제 repository: `/home/gpuadmin/Workspace/NoMaD/visualnav-transformer`
- 공식 origin: <https://github.com/robodhruv/visualnav-transformer>
- 기준 SHA: `dca79815b704e5aa9c6bdc3082351f9e3b2848c2`
- 연구 branch: `research/nomad-preflight`
- 공식 `train/`, `deployment/` tracked source/config/controller 수정 없음. 추가 코드는 `research/`, 문서는 `docs/`, ignore 규칙은 `.gitignore`에 있다.
- 환경: `/home/gpuadmin/Workspace/NoMaD/.venv`. 캐시와 실험 원본은 workspace 내부 `.cache/`, `artifacts/`에 있고 연구 Git 밖이다. 외부 dependency는 repository의 `external/`에 있으며 Git에서 제외한다.
- 시스템 Python/CUDA/driver, Isaac Sim 6, 다른 프로젝트/가상환경, shell 설정, global Git 설정을 변경하지 않았다. Isaac Sim 실행·업그레이드·의존성 설치도 하지 않았다.

## 공식 환경과 현재 환경의 차이

확인한 공식 파일: `train/train_environment.yml`, `deployment/deployment_environment.yaml`, README 설치 절차.

| 항목 | 공식 명세 | 이번 검증 |
|---|---|---|
| Python | 3.8.5 | 기존 설치된 3.11.16으로 workspace `.venv` 생성 |
| CUDA | train `cudatoolkit=10.`, deployment `11.` | torch wheel의 CUDA 12.8 runtime |
| torch / torchvision | 고정 버전 없음 | 2.7.0+cu128 / 0.22.0+cu128 |
| diffusers | 0.11.1 | **0.11.1 유지** |
| GPU | CUDA 10+ 당시 환경 | RTX 5060 Ti, capability (12,0), sm_120 |
| driver | 별도 명세 없음 | 기존 595.99.02 유지 |

PyTorch 2.7은 Blackwell 및 CUDA 12.8 wheel 지원을 발표했다: [PyTorch 공식 릴리스](https://pytorch.org/blog/pytorch-2-7/). CUDA 10/11 시대 runtime은 이 GPU에 맞는 기준으로 쓰지 않았다. `nvidia-smi`의 CUDA 13.2 표시는 driver가 지원하는 CUDA 수준이며, 이번 torch runtime은 **12.8**이다. 시스템 CUDA toolkit 설치·교체는 필요하지 않았다.

실제 확인: `torch.cuda.is_available() == True`, capability `(12,0)`, wheel arch 목록에 `sm_120`, CUDA 64×64 행렬곱의 모든 값이 정확히 64, 실제 NoMaD encoder/U-Net forward 성공. arch 목록만으로 성공을 판정하지 않았다.

## 최소 dependency와 호환성 결정

직접 dependency는 `research/requirements.txt`, 실제 설치된 전체 버전은 `research/requirements.lock`에 고정했다. 영상 decoding만 `research/video-requirements.txt`의 OpenCV headless를 추가한다.

- `diffusers==0.11.1`이 import하는 `cached_download`를 유지하기 위해 `huggingface-hub==0.25.2` 사용. 해당 API가 제거된 새 hub로 일괄 업그레이드하지 않았다. 최신 hub 설치 실패를 일부러 유발한 것은 아니다.
- `numpy==1.26.4`, `Pillow==10.4.0`, `efficientnet-pytorch==0.7.1`, `einops==0.6.1`, `PyYAML==6.0.2` 고정. torch 최초 설치가 가져온 NumPy 2.4.6 / Pillow 12.3.0을 새 `.venv` 안에서만 이 버전으로 조정했다. 이는 실패한 ABI 충돌의 수정이라고 주장하지 않으며, 구형 코드의 동작 범위를 고정하기 위한 선택이다.
- 학습·ROS 전체 환경의 wandb, rosbag, roslz4, h5py, lmdb, ROS daemon, controller를 설치/실행하지 않았다. 쓰지 않는 ViT 경로의 dependency도 설치하지 않았다.
- 공식 dependency: <https://github.com/real-stanford/diffusion_policy>. README는 commit을 고정하지 않는다. 이번에는 upstream 기준일 이전 이력의 `548a52bbb105518058e27bf34dcf90bf6f73681a` (2023-10-26)를 선택했다. 이는 checkpoint 학습에 실제 사용된 commit을 알아냈다는 뜻이 아니다.
- clone 당시 HEAD는 `5ba07ac6661db573af695b419a7947ecb704690f`였다. 사용한 U-Net, conv1d, positional embedding 세 파일은 두 SHA 간 diff가 없었다. 파일 hash는 `research/results/source_manifest.json`에 저장했다.
- 이 dependency의 `setup.py`는 `find_packages()`를 사용하지만 source가 namespace package라, 현대 editable 설치만으로는 import mapping이 비었다. 첫 import가 `ModuleNotFoundError`로 실패했다. 외부 source를 수정하지 않고 `research/python.sh`에서 해당 source 경로를 명시해 해결했다.
- 최종 `uv pip check`: 모든 설치 package 호환. torch의 `norm_first=True`에 따른 nested tensor 비활성화 warning은 남아 있으며 오류가 아니다.

## Checkpoint와 입력 출처

공식 README의 [pretrained Drive folder](https://drive.google.com/drive/folders/1a9yWR2iooXFAqjQHetz263--4_2FFggg)에서 확인한 `nomad.pth`만 사용했다.

| 항목 | 값 |
|---|---|
| Drive file ID | `1YJhkkMJAYOiKNyCaelbS_alpUpAJsOUb` |
| 크기 | 76,473,631 bytes |
| SHA-256 | `70f79b8262527e20e56ced64a3e3d7ef91855bc9e7c3fa348d78edcb83c6a333` |
| 경로 | `/home/gpuadmin/Workspace/NoMaD/artifacts/checkpoints/nomad.pth` |
| State tensor | 645 / 645 일치 |
| Parameter elements | 19,049,675 / 19,049,675 (100%) |
| Missing / unexpected / shape mismatch | 모두 0 |

원본 `load_model`은 `strict=False` 그대로 실행했고 별도의 coverage 검증을 추가했다. PyTorch 2.7의 기본 `weights_only` 로딩으로 이 state dict를 읽을 수 있었다. 불필요하게 unsafe pickle loader로 바꾸지 않았다. 이 결과는 실제 GPU forward로도 확인했다. SHA-256은 이번 다운로드의 재현용 fingerprint이며 저자가 서명한 checksum은 아니다.

기준 입력은 README가 제공한 [GoStanford ZIP](https://drive.google.com/drive/folders/1RYseCpbtHEFOsmSX2uqNY_kvSxwZLVP_)의 첫 번째로 열거된 trajectory `go_stanford/no3vcF_33_0`이다. 10–13번 JPEG를 oldest→newest observation으로, 25번을 future goal로 사용했다. 별도 입력 변화 실험은 14–17번 observation과 같은 goal을 사용한다. 160×120 RGB JPEG 원본 bytes를 그대로 추출했으며 pickle은 열지 않았다. 입력 선택은 모델 출력을 보기 전에 고정했다. training dataset일 수 있으므로 일반화 성능 평가가 아니다.

- ZIP: 781,698,396 bytes, SHA-256 `1fe1411945abd9cd0f335e845fe40d3477aac641aeb5669c961ec9debc4fb8a4`
- 경로: `../artifacts/inputs/raw/go_stanford.zip`
- 프레임별 출처/hash: `research/results/input_manifest.json`

사용자가 선택한 [공식 실내 주행 영상](https://general-navigation-models.github.io/nomad/static/videos/nomad_indoors.mp4)도 **별도 보조 검증**했다. video 전체를 원본 보존하고, 표시된 observation/goal inset을 PNG로 추출했다. observation에는 저자가 그린 노란 trajectory overlay가 남는다. crop 좌표, video frame index, presentation time, hash는 `research/results/video_input_manifest.json`에 있다. 이 영상은 raw camera stream이 아니며, presentation time은 센서 timestamp나 native action time이 아니다.

## 재실행

현재 설치된 환경에서는 다음 명령으로 실행한다. `research/python.sh`가 작업 디렉터리와 `PYTHONPATH`를 설정한다. **GPU device 접근이 가능한 host terminal**에서 실행해야 한다. 이번 제한 sandbox는 `/dev/nvidia*`와 네트워크를 노출하지 않아 GPU/다운로드 명령만 승인된 host 접근으로 실행했다.

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer
bash research/python.sh -m nomad_preflight.download_assets --root ../artifacts checkpoint inputs

# 입력 폴더가 이미 있으면 이 단계는 생략한다. 기존 폴더를 덮어쓰지 않는다.
bash research/python.sh -m nomad_preflight.prepare_inputs \
  --archive ../artifacts/inputs/raw/go_stanford.zip \
  --output ../artifacts/inputs/stanford_sequence

# 매번 새로운 output 이름을 사용한다. 기존 결과 폴더이면 실패한다.
bash research/python.sh -m nomad_preflight.run \
  --checkpoint ../artifacts/checkpoints/nomad.pth \
  --observations ../artifacts/inputs/stanford_sequence/obs_{0,1,2,3}.jpg \
  --goal ../artifacts/inputs/stanford_sequence/goal.jpg \
  --alternate-observations ../artifacts/inputs/stanford_sequence/alternate_{0,1,2,3}.jpg \
  --output ../artifacts/runs/new_run_name

NOMAD_CHECKPOINT=../artifacts/checkpoints/nomad.pth \
NOMAD_INPUTS=../artifacts/inputs/stanford_sequence \
bash research/python.sh -m pytest research/tests -q -rs
```

환경을 **새 경로에서 새로 구축할 때만** 아래 절차를 사용한다. 기존 환경을 재설치하는 명령으로 실행할 필요가 없다. Python 3.11은 이미 설치되어 있어야 한다.

```bash
# workspace 루트에서, 공식 clone/연구 branch가 준비된 상태
UV_CACHE_DIR="$PWD/.cache/uv" uv venv --python python3.11 .venv
UV_CACHE_DIR="$PWD/.cache/uv" uv pip install --python .venv/bin/python \
  torch==2.7.0 torchvision==0.22.0 \
  -c visualnav-transformer/research/requirements.lock \
  --index-url https://download.pytorch.org/whl/cu128
UV_CACHE_DIR="$PWD/.cache/uv" uv pip install --python .venv/bin/python \
  -r visualnav-transformer/research/requirements.txt \
  -c visualnav-transformer/research/requirements.lock
git clone https://github.com/real-stanford/diffusion_policy.git \
  visualnav-transformer/external/diffusion_policy
git -C visualnav-transformer/external/diffusion_policy checkout --detach \
  548a52bbb105518058e27bf34dcf90bf6f73681a
UV_CACHE_DIR="$PWD/.cache/uv" uv pip install --python .venv/bin/python --no-deps \
  -e visualnav-transformer/train -e visualnav-transformer/external/diffusion_policy
UV_CACHE_DIR="$PWD/.cache/uv" uv pip check --python .venv/bin/python
```

영상 입력을 다시 추출하려면 `video-requirements.txt`도 이 `.venv`에 설치하고 `prepare_video_inputs --video ../artifacts/inputs/raw/nomad_indoors.mp4 --output <새폴더>`를 실행한다. 영상 inference는 위 명령의 observation/goal 경로만 `video_sequence/*.png`로 변경한다. 입력 원본이 없으면 위 공식 영상 URL에서 다운로드하되 manifest의 SHA-256을 확인한다.

## 결과 저장과 측정 범위

`../artifacts/runs/20261016_preflight_02/`가 기준 실행이고 `20261016_video_01/`는 영상 보조 실행이다. 각 실행의 `raw/`에는 입력 image bytes, preprocessing tensor, encoder condition, distance, initial noise, normalized final diffusion이 있다. `derived/`에는 cumulative trajectory, metric trajectory, selected waypoint가 있다. `summary.json`에는 seed, 환경, shape/dtype, finite, latency, memory, 차이 통계가 있다. 원본 checkpoint와 실험 결과는 덮어쓰지 않는다.

| 기준 실행 (8 samples × 8 waypoints, 10 steps) | 측정 |
|---|---:|
| checkpoint/model load (CUDA sync 포함) | 159.69 ms |
| Cold model inference 1회 | 194.19 ms |
| Warm median / p95 (5 warmup 후 30회) | 23.95 / 24.38 ms |
| Cold peak allocated | 171.69 MiB |
| Warm peak allocated | 172.75 MiB |
| Warm peak reserved | 192.00 MiB |
| normalized/cumulative/metric output | `(8,8,2)`, float32, 전부 finite |
| 동일 초기 noise + 동일 DDPM step RNG | bitwise equal, max abs 0 |

Cold는 **새 프로세스의 첫 model forward**이며 CUDA kernel 확인과 model load 뒤 측정했다. interpreter/import/CUDA context 초기화/디스크 이미지 decoding/초기 noise 생성은 제외한다. PIL preprocessing, GPU 전송, vision/distance network, 10 diffusion steps, 공식 CPU NumPy normalization/cumsum 왕복, metric scaling, `torch.cuda.synchronize()`는 포함한다. 원본의 비동기 `time.time()` diffusion-only print와 다른, 명시적인 측정 구간이다. Cold 1회와 warm 30회는 통계적 장기 SLA나 순수 GPU kernel 시간 측정이 아니다.

Memory는 **PyTorch allocator 기준**이다. CUDA context, driver, 다른 desktop process까지 포함하는 장치 전체 peak라고 해석하지 않는다. GPU는 display process와 공유되었으며 독점/clock 고정하지 않았다.

`20261016_preflight_01`은 encoder 전체에 no_grad를 적용했던 초기 실험이다. 원본과 수치 차이를 발견해 **native parity 판정에서 무효화**했다. raw 파일과 당시 summary는 보존하고 별도 INVALIDATED 기록을 추가했다. 최종 보고에 이 초기 latency/memory를 사용하지 않는다.

## 다음 단계 판정

**Isaac Sim integration 구현 단계로 진행 가능**: checkpoint, runtime, action 해석, 원본 함수/loop 동등성의 preflight가 충족되었다. 이는 Isaac Sim 또는 navigation 성능 검증 완료라는 뜻은 아니다.

다음 단계에서 camera intrinsics/FOV와 crop, RGB channel order, observation queue sampling rate, capture time/pose 동기화, robot/base와 camera/world 축 변환, deployment scaling의 로봇별 타당성, selected waypoint/controller 연결, process 간 통신·latency, Isaac Sim의 별도 환경과 GPU memory 공존을 확인해야 한다. NoMaD에는 native yaw/timestamp가 없으므로 OLD/FRESH reconciliation 입력의 pose/time 정의도 별도로 설계해야 한다. 이 작업에서는 해당 설계·구현이나 simulator 설치 상태 검증을 수행하지 않았다.
