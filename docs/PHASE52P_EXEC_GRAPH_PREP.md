# Graph 안전 필터 오프라인 분석 재개

| 항목 | 상태 |
|---|---|
| 대상 | Phase47-C·Phase52-P의 원 EC REJECT; 전속도 고유 입력420개 |
| 저장 계산 | 작업 방식 변경 지시 전에420/420 완료,추가 계산 중지 |
| 현재 남은 재풀이 | 0개;실행하면 완료 캐시를 그대로 재사용 |
| 0.1m/s 입력 | 고유52개는 집계만,solver 미실행 |
| 재개 | 입력당 atomic JSON;완료 입력 재계산 금지,손상 캐시는 보존 후 오류로 중단 |
| 로그 | 시작/완료 및 진행 중60초마다;캐시420개면1분을 기다리지 않고 보고 단계로 이동 |
| 중간 저장 | 입력 완료마다 phase×scene summary JSON/CSV 갱신 |
| 종료 | report 자동 생성→Graph 보고서·결과 commit·push |
| 계산 중 중단 | 진행 중 입력만 저장 후 중단;다시 같은 명령으로 재개 |
| 잠금 | artifacts/isaac6/.phase52ec_graph.lock |
| 실행 범위 | 오프라인만. Isaac·새 NoMaD 추론·새 렌더 없음 |
| 완료 결과 검증 | 420개 캐시·독립 EC 통과 플래그·선택 최소비용·입력 일치 확인 |

수치 정식화·가중치·solver 옵션은 `protocol_numerics_frozen.json` 그대로다. 이후 수정은 보고표 분해·chunk 방향 정의 구분과 재개 wrapper만이며 수치 재풀이·튜닝은 하지 않았다. 캐시가 이미 모두 있으므로 이 명령은 현재 상태에서 새 Graph solve 없이 보고서 생성과 commit·push를 수행한다.

1번 결과: [EC 제동 꼬리 보고서](PHASE52P_EC_BRAKING_TAIL.md). 추가 분석: [chunk 적용 기하·ALIGN_ROTATE 상관](PHASE47_51_52_CHUNK_GEOMETRY.md).

원격에는 보고서·스크립트·사건별/장면별 결과표만 포함한다. 재개용 전체 `graph/`, `replay/` 캐시와 원 입력·전체 검사 archive는 현재 workspace에 그대로 보존하고, 이 phase의 `.gitignore`로 자동 publish에서도 제외한다. 현재 workspace에는420개 완료 캐시가 모두 있으므로 재계산하지 않는다.

진행 확인: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase52ec.campaign --status`

실행 명령(미실행):

`cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase52ec.campaign > ../artifacts/isaac6/phase52ec_graph.log 2>&1 < /dev/null &`
