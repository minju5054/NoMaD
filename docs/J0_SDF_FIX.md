# J0 H2 SDF 등록 범위 수정

| passed | tests | rerun_launcher_dry_runs | simulations_started | saved_depth_comparisons | bit_equal_count | query_outside_rule_unchanged | protocol_sha256 | original_protocol_sha256 | branch |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| True | 14 | 4 | 0 | 12 | 12 | True | 5269b6386e91a3f66e8b8eacef1188705c2b85e5c2df468eea813385e2f13309 | 42ebab18c221fdf5525ec83ba5692e8b84eb913b2df07d8f1dd88b743c5d7cee | fix/j0-scene-sdf-bounds |

별도 worktree/브랜치 fix/j0-scene-sdf-bounds에서만 수정했다. 실행 중인 원래 작업 트리·protocol·run-root를 수정하지 않았으며 시뮬레이션은 실행하지 않았다.

원인: H2 장면의 끝벽 내면은 x=9.0m인데 기존 depth 격자 등록 상한은 x=8.0m다. H2 후보 SDF 조회가 등록 밖으로 나가 frozen query의 ValueError로 실행 스레드가 종료됐다. 범위 밖을 free/occupied로 대신 처리하는 규칙은 추가하지 않았다.

장면 벽 외곽(벽 두께0.10m)·정적 물체·고정된 돌발 물체 AABB에0.50m를 더하고, 기존 등록 영역과 합집합을 취한다. 원점(-4,-3.5)·해상도0.01m·기존 셀 인덱스는 보존하며 상한만 원 격자에 맞춰 올림한다. H2의 x상한만9.60m로 확장되고 다른4장면은 기존 배열 크기와 값이 동일하다. 빈 지도 sentinel도 기존 값을 유지한다.

| scene | origin | h | geometry_with_walls | padded | registered |
| --- | --- | --- | --- | --- | --- |
| H1-v2 | [-4.0, -3.5] | 0.01 | [-1.1, -1.1, 4.3, 4.3] | [-1.6, -1.6, 4.8, 4.8] | [-4.0, -3.5, 8.0, 6.2] |
| SLW | [-4.0, -3.5] | 0.01 | [-1.1, -1.0, 6.1, 1.0] | [-1.6, -1.5, 6.6, 1.5] | [-4.0, -3.5, 8.0, 6.2] |
| H2 | [-4.0, -3.5] | 0.01 | [-1.1, -1.6, 9.1, 1.6] | [-1.6, -2.1, 9.6, 2.1] | [-4.0, -3.5, 9.6, 6.2] |
| LC | [-4.0, -3.5] | 0.01 | [-1.1, -1.1, 4.3, 4.3] | [-1.6, -1.6, 4.8, 4.8] | [-4.0, -3.5, 8.0, 6.2] |
| CL | [-4.0, -3.5] | 0.01 | [-1.1, -1.6, 6.1, 1.6] | [-1.6, -2.1, 6.6, 2.1] | [-4.0, -3.5, 8.0, 6.2] |

| scene | saved_depth_frames | overlap_bit_equal | query_value_gradient | initial_empty_map |
| --- | --- | --- | --- | --- |
| SLW | 3 | 3/3 | 3/3 | bit-identical |
| LC | 3 | 3/3 | 3/3 | bit-identical |
| CL | 3 | 3/3 | 3/3 | bit-identical |
| H1-v2 | 3 | 3/3 | 3/3 | bit-identical |

검증은 각 장면의 보존된 depth3프레임을 원래/새 V1에 같은 noise seed로 입력했다. values·occupied·observed·log-odds·hit-count와 bilinear query값/gradient를 바이트 단위로 비교했다. H2 초기 겹침 영역도 동일하며 기존에 예외였던 x=8.1/9.1/9.59 조회가 가능하고 x=9.7은 계속 예외다. 새로 등록된 H2 영역에서 실제 장애물이 관측되면 그 관측에 따른 거리값 변화는 정상이며, 관측을 숨겨 기존 값을 강제 보존하지 않는다.

방법·Graph 비용/제약·판정·체크포인트·seed·지연·실행 순서는 원 protocol과 동일함을 테스트했다. J1 공통 runtime_config와 depth factory도 동일 등록을 사용한다. depth 업데이트·EDT·query·발행 함수는 동결 소스 그대로다.

원 J0가 COMPLETE/DONE이 된 뒤 H2×{0,0.75}s×{221,222} 네 run만 새 root j0_h2_sdf_01에서 실행한다. 기존 H2 네 기록은 보존하고 결과와 무관하게 모두 새 네 기록으로 대체한다. 다른16개 metrics는 원본 그대로 재사용하며 SHA를 merge manifest에 기록한다. 재시도 없이 단계별 재개·전역 잠금·디스크30GB하한·cache정리 유지. 완료 후 J0 report를 같은 선별식으로 재생성하고 이 수정 브랜치로만 자동 commit·push한다.

원래 브랜치로 merge/cherry-pick하지 않았다. 아래 명령은 별도 worktree에서 실행하며 원 캠페인 종료 전에는 실행을 거부한다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer-j0-sdf-fix && PYTHONPATH=research /usr/bin/python3 -m nomad_j0.h2_rerun --status`

로그: `../artifacts/isaac6/j0_h2_sdf_01.log`

J0 종료 후 H2 재실행(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer-j0-sdf-fix && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_j0.h2_rerun > ../artifacts/isaac6/j0_h2_sdf_01.log 2>&1 < /dev/null &`
