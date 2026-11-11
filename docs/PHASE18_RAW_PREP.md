# Phase18-RAW 준비

| status | runs | method | scenes | seeds | delay_s | goal_rule | protocol_sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FROZEN; NOT_RUN | 24 | NOMAD_RAW | SLW / LC / CL | 66–73 | 0.75 | PHASE18_GEOMETRIC | 0b32140138b40ced900ea0ce470631c48c73e8d26ec07b452c5041cd38b43a6c |

Phase18 동결 scene·reference·Topomap·게이트 결과·checkpoint 정의와 PP+CURV 실행기를 재사용한다. SP·출발 정렬·HMM·ENDPOINT latch·EC는 적용하지 않는다. depth 렌더/지도는 동일하게 켜지만 경로 선택에 쓰지 않으며,관측 pose에 고정된 sample0의 원8점을 그대로 PP가 따라간다.

종료 판정은 Phase18과 동일(0.3m)

checkpoint 차이는 RAW−OURS(GRAPH-depth-CLR),RAW−RTC-hard다. 동일 seed의 장면 클러스터 bootstrap20,000회,seed20261030,신뢰수준98.33333%를 고정한다. 관측된 기술PASS checkpoint 쌍만 사용하고 결측은 대체하지 않는다. 다른 날짜의 추가 기준선이므로 탐색적 비교이며확인 실험 라벨을 붙이지 않는다.

Phase18과 동일하게 기술 실패는 재시도하지 않고 계속한다. 원본 run을 덮어쓰지 않는 단계별 재개·로그·짧은socket검사를 재사용한다. 새 gate/reference/smoke는 없다. 디스크30GB미만이면 새 run 전에 중단한다. depth원본 저장 형식도 Phase18 그대로다.

| passed | tests | dry_run | simulations_started | real_replays | protocol_sha256 | disk_free_bytes |
| --- | --- | --- | --- | --- | --- | --- |
| True | 7 | 24 | 0 | 0 | 0b32140138b40ced900ea0ce470631c48c73e8d26ec07b452c5041cd38b43a6c | 1109595398144 |

시뮬레이션·추론·실제 로그 재생은 실행하지 않았다. 종료 후 docs/PHASE18_RAW_RESULTS.md 및 research/results/phase18raw/를 자동 생성·commit·push한다. 기존 Phase18 코드·결과·raw는 수정하지 않는다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase18raw.campaign --status`

로그: `../artifacts/isaac6/phase18raw_01.log`

본 실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase18raw.campaign > ../artifacts/isaac6/phase18raw_01.log 2>&1 < /dev/null &`
