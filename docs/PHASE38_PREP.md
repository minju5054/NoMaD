# Phase38 준비

**FROZEN / 실행0회.** 단위테스트31개,180조합 dry-run(밤별90),smoke4조합 인자 검증 통과. Protocol SHA256: `18157ad32580a9fc797108c50e77de338d6fdc7b29fec93e87c658ccf6b8f801`. 여유 공간 1175.7GB.

| 방법 | 정의 |
|---|---|
| NOMAD_RAW / TE / RTC / ASTAR+EC / OURS | Phase35 동결 그대로. RAW의 depth·필터·회복 없음도 유지 |
| TE+EC / RTC+EC | 해당 handoff + Phase32 EC, 다음 SAFE→같은 SAFE들0.1m/s→STOP_WAIT |
| OURS−DETOUR | OURS의 평소 SAFE/EC/회복 유지,트리거 결정 계층·R2/R3 없음 |
| CARE | NOMAD_RAW sample0·동일 chunk 시점 + 현재 depth 프레임 CARE. SAFE·FRESHEST·EC·우회·회복 없음 |

CARE만 smoke 전에 개정했다. 다른8방법·배치·seed·순서·EC·판정은 원 protocol과 동일하다. TE+EC는 기존 ensemble/1초 만료를 검사하며36tick 재검사·다음9Hz tick 적용·감속 상한 유지도 그대로다.

CARE는 현재 프레임의 역투영 점에서 `0<Z≤1m`, 공통 높이 `0.03<h≤0.6m`를 적용하고 카메라 좌우 X 범위를32등분해 칸별 최소 Z점 하나를 남긴다(지도 누적 없음). 로봇 평면(x전방,y왼쪽)에서 `F=Σ(p−o)/‖p−o‖⁴`, 최대 ‖F‖ waypoint의 `atan2(Fy,Fx)`를±π/4로 clip하여 전체 경로를 B 원점 기준 회전한다. 정면 장애물 별도 처리 없음. O가 비면 RAW 경로 그대로다. Safe-FOV는 보정된 p_k*의 heading 오차>π/6이면 **즉시 v=0**, |ω|≤0.4로 제자리 회전하고, 그 외에는 PP/SP를 쓴다. 식의 단일 항 크기는 수학적으로1/d³이며, 사용자 지정 수식 자체를 유지했다.

| 원문과의 차이 | 이번 구현 |
|---|---|
| [CARE v4](https://arxiv.org/html/2506.03834v4) depth 소스 | 단안 추정 대신 공통 depth 카메라·노이즈·높이 필터, 현재 프레임만 사용 |
| CARE 속도 제한 | 공통0.3m/s·0.4rad/s |
| CARE 칸 수 | 원문에 M이 명시되지 않아32로 고정; 유효 카메라 X의 min/max를 균등 분할 |
| CARE 제어 waypoint | Safe-FOV는 p_k*, 전진 조향은 공통 PP lookahead0.25m·SP |
| CARE 식(1) 부호 | 원문 −표기 대신 반발 의도를 따른 사용자 지정 로봇평면 +수식 사용; 카메라→로봇 변환 후 왼쪽 장애물→오른쪽 회전 및 대칭을 단위테스트로 확인 |
| [RTC](https://arxiv.org/html/2506.07339v2): flow 정책·soft masking | 현재 NoMaD DDPM RTC-hard/RePaint prefix+guidance(β5) 유지. 원 논문의 완전 재현으로 부르지 않음 |

장면 SLW,LC,L2,H1,H2 × seed217–220 ×9방법=180회. 밤1=217,218 / 밤2=219,220. seed→scene 블록 안 순서만 RNG20261111로 섞었다. 돌발 상자는 기존 옆 방향 위치에 **U(−0.2,+0.2)m**를 더하며,벽/기존 상자 겹침 또는 넓은 쪽 유효 틈<0.28m이면 재추출한다. 배치는 scene×seed별 모든 방법에 같고 protocol에 수치·재추출 횟수를 고정했다. 새로운 장면 렌더나 주행은 하지 않았다.

밤별 누적 report: 방법×장면 도착·충돌·도착시간(도착 run 중앙값),8짝 비교×두 결과의 McNemar exact/Holm16검정,OURS 대 나머지8방법 도착 비열등성(짝 bootstrap20,000회,seed20261111,장면 내 재표집,95% CI 하한≥−10%p). 밤1은 중간 통계이고 Holm은 각 누적 report의16검정에 적용한다. 기술실패는1회 재시도 후 해당 비교 짝을 제외하고 보고한다. 종료 후cache정리,매 attempt 전30GB 검사,전역 잠금·재개 사용. 밤2는 밤1 완료 후만 시작한다. 각 밤 끝에 `docs/PHASE38_RESULTS.md`와 결과표를 자동 생성·commit·push한다.

명령은 모두 **준비만 했고 실행하지 않았다**. smoke는 H1 seed95에서 TE+EC,RTC+EC,CARE,OURS−DETOUR 각1회 순차 실행한다(본 결과 제외; 기술 실패만 같은 seed로1회 재시도).

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase38.campaign --smoke > ../artifacts/isaac6/phase38_smoke_01.log 2>&1 < /dev/null &
```
```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase38.campaign --smoke --status
```
밤1 / 밤2(각90회,한 번에 하나만):
```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase38.campaign --night 1 > ../artifacts/isaac6/phase38_night1.log 2>&1 < /dev/null &
```
```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase38.campaign --night 2 > ../artifacts/isaac6/phase38_night2.log 2>&1 < /dev/null &
```
```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase38.campaign --status
```

run-root: `../artifacts/isaac6/phase38_01/night1`, `night2`. CARE는 프레임당 최대32점과 메타데이터만 압축 저장하고 SDF는 만들지 않는다. 다른 방법 저장v2는 그대로다. 검증 산출물: `research/results/phase38/preparation/`. venv 설치·기존 phase 소스/결과 변경 없음.
