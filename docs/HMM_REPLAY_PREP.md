# HMM 재생 준비

동결 protocol SHA256: `90c344085b7c94b1d828f7069d28e3930b351beef9276ada52c241861acfaa6a`. 합성 테스트 10개 PASS. 기존 run 재생과 시뮬레이션은 실행하지 않았다.

HMM0는 Phase42-L 함수 그대로 재사용한다. NET은 현재 MAP 진입 후 XY 순변위/노드 간격을 round하고 최소1을 제거한다. 자기 전이를 포함한다. MAP이 바뀌면 진입 위치를 새로 저장한다. NET+MEM의 ℓ은 기존 중앙 노드 간격이며 p_j는 최초 방문 위치를 유지한다(사용자 확정). 튜닝은 없다.

입력 예정86 run 중 준비 시점 완료·가용 입력은 74개다. 실행/재개 때 완료 metrics를 다시 스캔하므로 Phase57/58에서 이후 완료되는 run도 추가된다. 미완료/누락은 report 가용률에 표시하며 기다리거나 실행 중 파일을 읽지 않는다. 전체 데이터가 필요하면 해당 주행 종료 후 실행한다.

캐시는 run 단위이며 입력·프로토콜 hash가 같을 때만 재사용한다. 원자적 저장,실행 잠금,최대1분 간격 진행률,예외/중단 상태 기록을 지원한다. 완료 후 docs/HMM_REPLAY.md와 research/results/hmm_replay/를 생성하고 자동 commit·push한다. 같은 명령으로 새로 완료된 run을 추가하거나 중단 지점부터 재개한다.

기록 창만 사용하므로 최종 MAP의 창 밖 여부는 구조상0이다. 대신 이전 MAP 이탈/창 조건 전 전이 예측 MAP 이탈/강제 재초기화를 각각 보고한다. 거짓 목표는 노드 기준,기존 잘못된 도착은 거리 기준이라 별도 표로 구분한다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_hmm_replay.replay --status`

로그: `../artifacts/isaac6/hmm_replay_01.log`

실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_hmm_replay.replay > ../artifacts/isaac6/hmm_replay_01.log 2>&1 < /dev/null &`
