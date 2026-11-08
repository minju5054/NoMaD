# Phase38 준비

**FROZEN / 실행0회.** 단위테스트22개,180조합 dry-run(밤별90),smoke4조합 인자 검증 통과. Protocol SHA256: `612d79d6b7d483353379ba2115802417ba4ffd50df208e734468a1cd2d25320e`. 여유 공간 1175.7GB.

| 방법 | 정의 |
|---|---|
| NOMAD_RAW / TE / RTC / ASTAR+EC / OURS | Phase35 동결 그대로. RAW의 depth·필터·회복 없음도 유지 |
| TE+EC / RTC+EC | 해당 handoff + Phase32 EC, 다음 SAFE→같은 SAFE들0.1m/s→STOP_WAIT |
| OURS−DETOUR | OURS의 평소 SAFE/EC/회복 유지,트리거 결정 계층·R2/R3 없음 |
| CARE | FRESHEST-SAFE 입력→역제곱 반발 최대 waypoint의 방향으로 전체 경로±π/4 회전; 그 waypoint heading>π/6이면 제동 후 제자리 회전. EC/우회 없음 |

공통 이동은 C0-NA PP/SP(90° 초과 출발 정렬),depth V1,회복,저장v2다(RAW는 동결 예외). CARE의30° Safe-FOV 회전은 사용자 지정 추가 규칙이다. TE+EC는 실제 ensemble 조향·원1초 만료를 복제해 EC를 계산한다. 거절 preview는 실제 chunk를 바꾸지 않으며,주기적 대안은 같은 chunk ID/수신시각을 유지한다.36tick 재검사와 다음9Hz tick 적용,0.1m/s 상한의 다음 전속도 PASS FRESH까지 유지를 보존한다.

| 원문과의 차이 | 이번 구현 |
|---|---|
| [CARE v4](https://arxiv.org/html/2506.03834v4): RGB 추정 depth·전방 bin 최근점·식(1)의 거리 가중 | 공통 관측/점유 지도1m 이내 셀 중심; 사용자 지정 **역제곱의 바깥 방향 벡터**. 원문 식(1)을 그대로 복제한 것이 아님 |
| CARE 입력·출력 | SAFE 선택 후 현재 B에서 보정,공통 PP/SP·0.3m/s·0.4rad/s 및 회복. 원문의 별도 전진/회전 제어와 다름 |
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

run-root: `../artifacts/isaac6/phase38_01/night1`, `night2`. 검증 산출물: `research/results/phase38/preparation/`. venv 설치·기존 phase 소스/결과 변경 없음.
