# SLW-v2 준비

| tests | launcher_dry_runs | reference_launch_planned | reference_rollouts_executed | simulations | inference | H1v3_saved_trajectory_figures | protocol_sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 4 | True | 0 | 0 | 0 | 4 | 7b9b69d1991df02fb663e657fe5cd63adda67205f60631a6accd5c60589a4c5c |

기존 SLW를 보존하고 시작점x만0→−1.0m, 통로 시작벽xmin만−1→−2.0m로 연장했다. Slalom1/2/3 색만 빨강(0.85,0.08,0.08),파랑(0.08,0.20,0.85),노랑(0.95,0.80,0.04) 단색으로 바꾼다. 상자 위치·크기·통로 폭·목표·checkpoint는 동일하다.

| start | corridor | goal | checkpoint_x_m | start_to_checkpoint_m | sdf_bounds |
| --- | --- | --- | --- | --- | --- |
| [-1.0, 0.0, 0.0] | {'xmin': -2.0, 'xmax': 6.0, 'half_width': 0.9, 'height': 2.6} | [5.0, 0.0, 0.0] | 4.6 | 5.6 | [-4.0, -3.5, 8.0, 6.2] |

사용자 실행 명령은 먼저 새 reference 경로를 Phase16/17 SLW의 clearance-weighted grid +20회 smoothing 절차로 계산하고, 같은 PP reference rollout을 수행한다. 그 뒤 원 Phase17 reference renderer가 새 외관으로 RGB를2초(144tick) 간격과 마지막점에서 캡처한다. 이 준비는 NoMaD 추론 없는 reference 단계이며 선별4회의 결과에 포함하지 않는다. 지금은 경로 생성·rollout·Isaac·NoMaD 모두 실행하지 않았다.

Topomap/이미지는 아직 존재하지 않는다. 생성 후 reference/scenario/manifest/이미지 SHA를 resolved_assets.json에 봉인하며, 본 주행은 이 검증을 통과해야 시작한다. scene/방법/선별 protocol은 이미 FROZEN이다. reference가 실패하면 바꾸거나 재시도하지 않고 중단·보고하며, 완료된 reference는 재개 시 재사용한다.

선별4회는 J0 OURS-noEC 그대로: D000 seed221,222 후 D750 seed221,222. 종료 판정은 Phase18과 동일(0.3m). 최장 SAFE+ClearanceGraph,PP/CURV,1s 만료,ENDPOINT latch; EC·회복·STOP_WAIT 특수처리·HMM/NET 없음. 선별은 0s 성공2/2 AND 0.75s checkpoint 평균>0s 평균이며 두 조건의 두 checkpoint가 모두 필요하다.

J0 SDF fix 등록(벽 포함bbox+0.5m와 기존영역 합집합,원점·1cm 격자 보존)을 사용한다. 이 장면의 등록영역은 기존 [-4,-3.5,8,6.2] 그대로다. 전역 잠금·재개·30GB하한·run후cache정리·기술실패1attempt 유지.

완료 시 docs/SLWV2_J0_RESULTS.md·research/results/slwv2_j0/와 4회 top-down 주행 PNG를 자동 생성·commit·push한다. 실행/자동push 브랜치는 research/phase0-infrastructure이며 명령의 cwd는 원래 저장소다.

H1-v3 기존4회 그림은 저장된 trajectory/summary만 읽어 docs/H1V3_J0_RESULTS.md에 추가했다. 과거 metrics·판정·코드·시뮬레이션은 재실행/변경하지 않았다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_slwv2.campaign --status`

로그: `../artifacts/isaac6/slwv2_j0_01.log`

미실행 명령(reference 준비 포함):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_slwv2.campaign > ../artifacts/isaac6/slwv2_j0_01.log 2>&1 < /dev/null &`
