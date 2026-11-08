# Phase39-O2 — B행·기하 초기값·탈출 비교 준비

**실행 준비만 완료.** Phase39-O의209개 입력과 저장 V0 결과를 재사용한다. V0 solve 경로는 코드에서 거부한다. 실제 재풀이 대상은 VB/VO/VE, 총627 job×변형이다. A* 및 경로 검색, 슬랙 변수는 사용하지 않는다. 기존 코드·결과는 보존한다.

| 변형 | 고정 정의 |
|---|---|
| VB | R2/R3에서 첫 선분 k=0의 SDF 행 하나만 제외. 나머지 비용·제약·certificate와 음수 B 사전거부 유지 |
| VO | VB+R3 기하 초기값 좌/우 최대2개. 기존7개 유지 |
| VE | VO 상속. c_B<0.025에서만 c(s)=min(0.025,c_B−0.005+0.5s),음수 B 사전거부 제거. 높은 c_B도 B행은 제외 |

c_B는 동결 `d(B)−h/√2`다. VE certificate: s_esc=(0.03−c_B)/0.5, 닫힌[0,s_esc]는 exact≥c_B−0.005, [s_esc,끝]은 exact≥0.025. 0.3m는 기존 base/strict 지도 전환이며, 두 경계에서 경로를 나눠 상수 기준의 exact certificate를 적용한다. c_B≥0.025는 제약(B행 제외)·certificate 모두 동결이다. EC는 실행하지 않는다. VE 온라인 적용 시 동결 EC(항상0.025)는 탈출 경로를 거절하므로 EC에도 같은 탈출 기준이 필요하다.

VO는 전체 R3 보수적 지도(점유·unknown·last-free>2s 차단)를8-연결로 라벨링한다. B의 u_ref 띠(길이1.6m,폭0.18m)와 가장 먼저 만나는 성분을 고르고 B 반경1.6m로 자른 후 좌우 극값을 구한다. 극값 셀의 사각형이 원 경계에 닿는 쪽은 제외한다. 극값 동률이면 B에 가장 가까운 셀(다음 row/column 순)을 쓴다. 경유점=극값 셀 중심±수직방향0.14m; 점유/지도 밖이면 제외한다. B→경유점→u_ref 방향의 두 직선에10개 구간을 폐형식으로 배분한다(선호 간격0.15m,끝점 전진 목표1.2m). 경유점은 실제 vertex로 유지하고, 간격0.1~0.2m/반경1.6m를 만족하지 못하면 해당 초기값만 제외한다. 다른 경유점을 찾거나 재시도하지 않는다.

판정은 전체209 job의 원래 분모로, V0 성공률+30%p AND p95≤1s AND certificate 실패0. 통과한 것 중 VB→VO→VE 순으로 가장 단순한 변형을 선택한다. V0 시간은39-O 실측치를 그대로 쓴다. 새 job 시간은4프로세스 풀 전체 시간으로 지도 복원/cache/기하 초기값 생성/선택을 포함한다.

보고: c_B(<0 / 0~0.03125 / ≥0.03125)×R2/R3×변형의 수락률·SLSQP 메시지, VO 초기값 생성률·선택 비율. 동일 run 안 시간순 인접 job의 XY 이동<1cm이면 같은 그룹으로 이어 묶는다(R2/R3를 함께 묶고 heading/map 차이는 분리 조건에 쓰지 않음). 그룹은 해가 하나라도 있으면 성공, run별 그룹 성공률과 하나 이상의 성공 그룹 여부를 함께 보고한다(계획 해 생성 기준이며 도착 성공이 아님). 이 보조 통계는 원 job 기준 판정을 바꾸지 않는다.

Protocol SHA256 `63e06628e57e7029efbd7c6807dd284a5a3fcc545d636bd893ca92acdf70ed0a`. 예상 약17.0분(저장 V0 시간·최대9 초기값·보수적 연산 계수 기반 계획 추정).55분 이후 새 job을 시작하지 않고 현재 job 완료 후 PARTIAL 저장; 같은 명령으로 재개한다. 미완료 자료는 판정하지 않는다. baseline/input hash 검증,실행 잠금,원자적 결과 저장을 사용한다.

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase39o2.run > ../artifacts/isaac6/phase39o2_01.log 2>&1 < /dev/null &
```

진행 확인: `PYTHONPATH=research /usr/bin/python3 -m nomad_phase39o2.run --status`. 완료 후 이 문서와 `research/results/phase39o2/` 표가 자동 갱신된다. V0 원본과39-O 로컬 입력 사본은 읽기 전용이며 재생성하지 않는다.

검증: 합성 테스트15개와627개 새 job×변형 dry-run 통과. 저장 입력 및 V0 재풀이는0회.
