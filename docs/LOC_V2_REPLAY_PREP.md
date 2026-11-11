# LOC v2 재생 준비

| passed | synthetic_tests | real_calibration_fits | real_replays | simulations | protocol_sha256 |
|---|---|---|---|---|---|
| True | 9 | 0 | 0 | 0 | be81e9b807ca0059bf7e7070ae0c22d5509b8b69fe4893ef4ab8710dddfdcf08 |

| calibration_available | evaluation_available | calibration_expected | evaluation_expected | simulations | real_replays | calibration_fits | protocol_sha256 |
|---|---|---|---|---|---|---|---|
| 172 | 43 | 172 | 48 | 0 | 0 | 0 | be81e9b807ca0059bf7e7070ae0c22d5509b8b69fe4893ef4ab8710dddfdcf08 |

실제 보정·평가 재생과 시뮬레이션은 실행하지 않았다. 합성 테스트와 입력 가용성 dry-run만 수행했다. 기존 모듈은 수정하지 않고 nomad_hmm_replay의 입력 정렬·HMM0/NET·선언 연결을 재사용한다.

HMM 사용 run만 포함한다. 보정: Phase47-C OURS-DETOUR+HMM,Phase52/53 전 방법,NIGHT E1/E3. 평가: Phase57 MIN/MIN+G18,Phase58/59 전 방법(seed227,228). 예정172/48개 중 실제 가용 수는 위 표다. 본 report에는 phase별 실제 사용 run·추론 수를 표기한다.

OBS는 k=후보−가설 노드,거리 bin0.5,Laplace1의 조건부 히스토그램을 보정 자료로만 만든다. SIGN은 로그의 직전 HMM0 MAP 접선에서 계산한 true node change−s/ℓ의 분산(ddof0)을 사용한다. 평가에서는 각 변형의 MAP 접선을 사용한다. 보정값과 입력 hash를 먼저 저장·동결한 뒤 평가를 시작하며 평가 데이터로 재보정하지 않는다.

목표 지연은 true_node가 처음 goal인 추론 이후 첫 MAP=goal까지의 추론 간격이다. 미확인 run은 우측 검열 수를 중앙값 옆에 표기한다. 이전에 MAP=goal을 냈다면 음수 선행 지연을 별도 집계하며 부호 있는 최초 지연 보조 중앙값도 병기한다. 실제 목표 노드가 기록상 도달하지 않은 run은 따로 표시한다.

Topomap 노드 pose가 같은 오도메트리 좌표계에 주어진다는 가정을 명시한다. report 한계 항목은 OBS 독립성 곱에 따른 과신 가능성과 로그 HMM0 MAP 오류의 SIGN 분산 혼입 두 항목만 둔다.

run별 원자적 cache,실행 잠금,중단/실패 상태,1분 진행 로그를 지원한다. 같은 명령으로 재개한다. 보정 corpus가 바뀌면 동결 모델을 자동 갱신하지 않고 중단한다. 종료 후 docs/LOC_V2_REPLAY.md 및 research/results/loc_v2_replay/를 자동 생성·commit·push한다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_loc_v2.replay --status`

로그: `../artifacts/isaac6/loc_v2_replay_01.log`

실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_loc_v2.replay > ../artifacts/isaac6/loc_v2_replay_01.log 2>&1 < /dev/null &`
