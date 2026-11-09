# Phase40-P 준비

**FROZEN / 실행0회.** 테스트24개, 본20조합·smoke1조합 dry-run 통과. 여유 공간 1158.2GB. Protocol SHA256 `2690cf07f89fc4646383c498f41095d443d0459f2b1a7840923cc04db83ee699`.

OURS-N은 Phase38 OURS의 결정·넘김·RECOVER·C0-NA·평가기·jitter를 재사용한다. R2는39-O3가 재사용한 VE, R3는VN 그대로이며, CLR soft 지도/가중치도 동결한다. R3 hard/certificate/기하 지도만 occupied OR (B반경0.6m 내 unknown)이다. B행 제외와 낮은 c_B 탈출 기준은39-O2/3와 같다. A* 없음.

계산 중에는 Phase38 OURS-DETOUR의 SAFE·EC 대안·RECOVER 동작을 유지한다. 우회 job 때문에 정지를 명령하지 않지만, EC 대안이 없거나 회복 동작이면 정지할 수 있고 실제 대기 정지 시간을 따로 센다. dispatch 후54tick을 지나 처음 오는8tick 제어격자의 예측 pose로 풀고, 조기 결과도 그 tick에서만 실제 pose·최신 depth EC를 통과해야 설치한다. 지나간 결과는 폐기하며 R2의 FRESH SUPERSEDED도 유지한다. 예측에는 현재 실행기 상태/명령과 동결72Hz 적분만 사용한다.

탈출 EC는 설치 시 동결72Hz rollout에서 경로 위 투영 호장이 `s_esc=(0.03−job c_B)/0.5`에 처음 도달한 시각을 t_esc로 쓴다. 경로 끝이 s_esc보다 앞이면 동결 끝점 도달 시각을 쓴다. 2초 안에 도달하지 않으면 **거부하지 않고2초 상한**을 쓰며 최초 rollout 전 구간은c0로 검사한다. `c0=설치 시 base exact clearance−0.005`와 `설치 시각+t_esc` 절대시각을 job별로 고정한다. 재검사에서는 최신 지도와 남은 시간만 쓰고, 마감 이후는동결0.025 기준이다. 같은 job 재설치로 연장하지 않는다. 탈출 설치·연속 탈출 설치·탈출 중 재검사 거절·t_esc분포·2초 상한 적용 건수를 보고한다.

SLW,LC,L2,H1,H2 ×217–220, OURS-N20회. Phase38 OURS-DETOUR(15/20도착), OURS, ASTAR+EC의 같은20쌍을 재사용한다(실행일 차이). PILOT_OK=충돌≤1 AND 도착≥14, GRAPH_GAIN=도착≥17 AND OURS-N만 도착≥3쌍. McNemar exact는 참고; 둘 다 도착한 짝의 시간·주행거리 차이, 우회/탈출 설치, 대기 정지 시간을 자동 report한다. 저장v2,30GB reserve, 본실험 기술실패1회재시도·cache정리·잠금·재개를 유지한다.

사용자가 실행: 아래 본 campaign 명령 하나는 smoke H1/217/OURS-N1회(본 결과 제외,자동재시도 없음)를 먼저 수행하고 기술 PASS 후 본20회로 진행한다. 이미 완료된 smoke와 run은 재개 시 반복하지 않는다. 이 준비 작업에서는 둘 다 실행하지 않았다.

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase40p.campaign --with-smoke > ../artifacts/isaac6/phase40p_01.log 2>&1 < /dev/null &
```
```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase40p.campaign --status
```
smoke만 따로 실행할 때의 선택 명령(위 본 campaign을 쓰면 별도 실행 불필요):
```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase40p.campaign --smoke > ../artifacts/isaac6/phase40p_smoke_01.log 2>&1 < /dev/null &
```

본실험 완료 후 `/usr/bin/python3 + PYTHONPATH=research`로 `docs/PHASE40P_RESULTS.md`, `research/results/phase40p/`를 자동 생성·commit·push한다. Phase38 저장 launcher 시간 기준 본20회 약56분,smoke 약3분(재시도 제외 추정; preparation/runtime_estimate.json).
