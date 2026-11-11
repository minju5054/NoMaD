# Phase60-P 준비

| status | runs | methods | scenes | seeds | delay_s | protocol_sha256 |
|---|---|---|---|---|---|---|
| FROZEN; NOT_RUN | 18 | CUT / CONS / CONS+G18 | H1-v2 / SLW / H2 | 227,228 | 0.75 | 96c16d63403bc8ae0a32291b5550f72ba250f5212346066356c6159925ee810c |

사용자 확정: 원래 동결 σ²=0.14923311275040188를 보정 파일에서 직접 읽는다. 0.1492는 반올림 표기일 뿐 온라인 상수로 대체하지 않는다. `model_sha256=f806c6236bfdf0470faca8578fcb9ab749770d859856de411d4d341f0417c8ca` 전체 일치 시에만 launcher/worker/audit/report를 진행하고 불일치하면 거부한다. 보정값은 재추정하지 않는다.

전이는 LOC_V2 Filter(SIGN)를 그대로 import한다. 직전 MAP의 Topomap 노드 접선에 observation-tick 오도메트리 변위를 투영한 s/ℓ를 평균으로 쓰고 정수 offset Gaussian을 전역 노드 범위에서 행 정규화한다. 노드 pose와 오도메트리는 같은 좌표계로 제공된다고 가정한다.

Phase59-P의 실행 함수·방법·장면·jitter·seed·순서를 그대로 재사용한다. 방출·radius4 창·부목표 threshold3·closest==goal 선언도 기존 함수를 쓴다. 유일한 정책 변경은 NET→SIGN 전이다. OBS/MEM은 사용하지 않는다.

| item | value |
|---|---|
| only_policy_change | online transition NET -> SIGN |
| implementation | nomad_loc_v2.filter.Filter(node_xy,ell,SIGN,verified_calibration) |
| model_file | research/results/loc_v2_replay/calibration.json |
| model_sha256 | f806c6236bfdf0470faca8578fcb9ab749770d859856de411d4d341f0417c8ca |
| sigma2 | 0.14923 |
| no_refit | True |
| mean | signed dot(current minus previous observation odometry XY, tangent at previous MAP)/ell |
| transition | frozen Gaussian log density at integer node offsets,row normalization over global nodes,no support cutoff |
| tangent | frozen central adjacent node pose difference,one-sided ends,nearest valid oriented adjacent segment for zero vector |
| coordinate | request observation_pose[:2] at hmm_odometry_tick,exact simulator odometry assumption;no true_node input |
| unchanged | Phase59/58 controller,Graph,EC,latch,selection,recovery,1s expiry,geometry,jitter,seed,method order;Phase43 emission/window radius4/subgoal threshold3/end clamp/declaration |
| no_OBS | True |
| no_MEM | True |

| passed | tests | dry_run | simulations_started | solver_runs | real_replays | calibration_refits | model_sha256 | sigma2 | protocol_sha256 | disk_free_bytes |
|---|---|---|---|---|---|---|---|---|---|---|
| True | 9 | 18 | 0 | 0 | 0 | 0 | f806c6236bfdf0470faca8578fcb9ab749770d859856de411d4d341f0417c8ca | 0.14923 | 96c16d63403bc8ae0a32291b5550f72ba250f5212346066356c6159925ee810c | 1113336078336 |

성공은 기존0.5m 선언+무충돌이다. 0.7m 실제 접근·미선언과 거짓 목표(node 기준)는 Phase59 정의를 그대로 사용하며 거리 기준 잘못된 도착과 구분한다. Phase58/59 같은(scene,seed,method)를 모두 옆 열로 표시한다.

시뮬레이션·smoke·solver·실제 로그 재생·보정 재추정은 실행하지 않았다. 종료 후 docs/PHASE60P_RESULTS.md와 research/results/phase60p/를 생성하고 run별 PNG도 명시적으로 git add -f하여 commit·push한다. 기술 실패1회 재시도,cache 정리,저장v2,30GB 중단,공유 실행 잠금·재개는 기존과 같다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase60p.campaign --status`

로그: `../artifacts/isaac6/phase60p_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase60p.campaign > ../artifacts/isaac6/phase60p_01.log 2>&1 < /dev/null &`
