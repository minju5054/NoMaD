# Phase39-O2 — 재풀이 결과

**NO_GO — 선택 변형 없음.** 627/627개 새 작업 완료, 241.04s(약4분). V0는 저장 결과209건만 재사용했고 재실행0회이며 원본 hash도 변하지 않았다.

- 전체 성공: **V0 32/209, VB 31/209, VO 31/209, VE 77/209**. VE는 +21.53%p로 사전 기준 +30%p 미달이다.
- VB/VO/VE p95: **0.497/0.542/0.598s**. 수락 해 certificate 재검사 실패는 모두0건이다.
- VO와 VE 각각 추가 초기값 **0/274개**: 원 경계 접촉272개, 띠 안 성분 없음2개. 따라서 두 변형에서 선택된 기하 초기값도0개다.
- VE의 음수 c_B 수락은 **46 job(수락 해209개)**이다. 이는 오프라인 계획 결과이며, 동결 EC를 그대로 적용한 온라인 실행 가능성을 뜻하지 않는다.


| variant | label | n | baseline_success_rate | success_rate | p95_s | certificate_failures | checks |
|---|---|---|---|---|---|---|---|
| VB | NO_GO | 209 | 0.15311 | 0.14833 | 0.49699 | 0 | {'success_plus_30pp': False, 'p95_le_1s': True, 'certificate_failures_zero': True} |
| VO | NO_GO | 209 | 0.15311 | 0.14833 | 0.54247 | 0 | {'success_plus_30pp': False, 'p95_le_1s': True, 'certificate_failures_zero': True} |
| VE | NO_GO | 209 | 0.15311 | 0.36842 | 0.59787 | 0 | {'success_plus_30pp': False, 'p95_le_1s': True, 'certificate_failures_zero': True} |

| kind | cB_bin | variant | n | accepted_jobs | success_rate | p50_s | p95_s | certificate_failures |
|---|---|---|---|---|---|---|---|---|
| R2 | <0 | V0 | 55 | 0 | 0 | 0.11916 | 0.12464 | 0 |
| R2 | <0 | VB | 55 | 0 | 0 | 0.1195 | 0.12452 | 0 |
| R2 | <0 | VO | 55 | 0 | 0 | 0.11932 | 0.12478 | 0 |
| R2 | <0 | VE | 55 | 45 | 0.81818 | 0.14607 | 0.17233 | 0 |
| R2 | 0<=cB<0.03125 | V0 | 3 | 2 | 0.66667 | 0.15492 | 0.17325 | 0 |
| R2 | 0<=cB<0.03125 | VB | 3 | 2 | 0.66667 | 0.14353 | 0.1786 | 0 |
| R2 | 0<=cB<0.03125 | VO | 3 | 2 | 0.66667 | 0.14785 | 0.19594 | 0 |
| R2 | 0<=cB<0.03125 | VE | 3 | 2 | 0.66667 | 0.15463 | 0.1943 | 0 |
| R2 | >=0.03125 | V0 | 14 | 11 | 0.78571 | 0.15485 | 0.22 | 0 |
| R2 | >=0.03125 | VB | 14 | 11 | 0.78571 | 0.15422 | 0.18781 | 0 |
| R2 | >=0.03125 | VO | 14 | 11 | 0.78571 | 0.15716 | 0.18973 | 0 |
| R2 | >=0.03125 | VE | 14 | 11 | 0.78571 | 0.15918 | 0.18721 | 0 |
| R2 | ALL | V0 | 72 | 13 | 0.18056 | 0.11987 | 0.1786 | 0 |
| R2 | ALL | VB | 72 | 13 | 0.18056 | 0.12006 | 0.17343 | 0 |
| R2 | ALL | VO | 72 | 13 | 0.18056 | 0.12047 | 0.16914 | 0 |
| R2 | ALL | VE | 72 | 58 | 0.80556 | 0.14823 | 0.17828 | 0 |
| R3 | <0 | V0 | 56 | 0 | 0 | 0.13982 | 0.14338 | 0 |
| R3 | <0 | VB | 56 | 0 | 0 | 0.13937 | 0.14235 | 0 |
| R3 | <0 | VO | 56 | 0 | 0 | 0.18873 | 0.19207 | 0 |
| R3 | <0 | VE | 56 | 1 | 0.017857 | 0.37393 | 0.65229 | 0 |
| R3 | 0<=cB<0.03125 | V0 | 4 | 0 | 0 | 0.37587 | 0.39634 | 0 |
| R3 | 0<=cB<0.03125 | VB | 4 | 0 | 0 | 0.34674 | 0.46391 | 0 |
| R3 | 0<=cB<0.03125 | VO | 4 | 0 | 0 | 0.39462 | 0.51017 | 0 |
| R3 | 0<=cB<0.03125 | VE | 4 | 0 | 0 | 0.39548 | 0.60705 | 0 |
| R3 | >=0.03125 | V0 | 77 | 19 | 0.24675 | 0.36618 | 0.56348 | 0 |
| R3 | >=0.03125 | VB | 77 | 18 | 0.23377 | 0.36954 | 0.54691 | 0 |
| R3 | >=0.03125 | VO | 77 | 18 | 0.23377 | 0.42752 | 0.58927 | 0 |
| R3 | >=0.03125 | VE | 77 | 18 | 0.23377 | 0.422 | 0.597 | 0 |
| R3 | ALL | V0 | 137 | 19 | 0.13869 | 0.27962 | 0.54168 | 0 |
| R3 | ALL | VB | 137 | 18 | 0.13139 | 0.28194 | 0.5134 | 0 |
| R3 | ALL | VO | 137 | 18 | 0.13139 | 0.32591 | 0.55603 | 0 |
| R3 | ALL | VE | 137 | 19 | 0.13869 | 0.38917 | 0.63582 | 0 |
| ALL | <0 | V0 | 111 | 0 | 0 | 0.13513 | 0.14216 | 0 |
| ALL | <0 | VB | 111 | 0 | 0 | 0.1354 | 0.14156 | 0 |
| ALL | <0 | VO | 111 | 0 | 0 | 0.18318 | 0.19115 | 0 |
| ALL | <0 | VE | 111 | 46 | 0.41441 | 0.27653 | 0.61421 | 0 |
| ALL | 0<=cB<0.03125 | V0 | 7 | 2 | 0.28571 | 0.34258 | 0.39407 | 0 |
| ALL | 0<=cB<0.03125 | VB | 7 | 2 | 0.28571 | 0.32083 | 0.444 | 0 |
| ALL | 0<=cB<0.03125 | VO | 7 | 2 | 0.28571 | 0.36858 | 0.49067 | 0 |
| ALL | 0<=cB<0.03125 | VE | 7 | 2 | 0.28571 | 0.36605 | 0.57022 | 0 |
| ALL | >=0.03125 | V0 | 91 | 30 | 0.32967 | 0.34081 | 0.56024 | 0 |
| ALL | >=0.03125 | VB | 91 | 29 | 0.31868 | 0.33532 | 0.53231 | 0 |
| ALL | >=0.03125 | VO | 91 | 29 | 0.31868 | 0.38335 | 0.57793 | 0 |
| ALL | >=0.03125 | VE | 91 | 29 | 0.31868 | 0.38172 | 0.58572 | 0 |
| ALL | ALL | V0 | 209 | 32 | 0.15311 | 0.14181 | 0.52733 | 0 |
| ALL | ALL | VB | 209 | 31 | 0.14833 | 0.14068 | 0.49699 | 0 |
| ALL | ALL | VO | 209 | 31 | 0.14833 | 0.18948 | 0.54247 | 0 |
| ALL | ALL | VE | 209 | 77 | 0.36842 | 0.34381 | 0.59787 | 0 |

## 기하 초기값

| variant | r3_jobs | attempted_sides | generated_sides | generation_rate | jobs_with_any_extra | selected_paths | job_any_generation_rate | selected_geometric | selected_geometric_fraction | exclusion_reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| VO | 137 | 274 | 0 | 0 | 0 | 18 | 0 | 0 | 0 | {'SIDE_TOUCHES_DISK_BOUNDARY': 272, 'NO_COMPONENT_IN_STRIP': 2} |
| VE | 137 | 274 | 0 | 0 | 0 | 19 | 0 | 0 | 0 | {'SIDE_TOUCHES_DISK_BOUNDARY': 272, 'NO_COMPONENT_IN_STRIP': 2} |

## run별 위치 중복 제거 통계

| run | variant | jobs | accepted_jobs | groups | successful_groups | group_success_rate | run_any_success |
|---|---|---|---|---|---|---|---|
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_217_OURS/attempt1 | V0 | 11 | 5 | 11 | 5 | 0.45455 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_217_OURS/attempt1 | VB | 11 | 5 | 11 | 5 | 0.45455 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_217_OURS/attempt1 | VO | 11 | 5 | 11 | 5 | 0.45455 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_217_OURS/attempt1 | VE | 11 | 5 | 11 | 5 | 0.45455 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_218_OURS/attempt1 | V0 | 21 | 8 | 17 | 6 | 0.35294 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_218_OURS/attempt1 | VB | 21 | 8 | 17 | 6 | 0.35294 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_218_OURS/attempt1 | VO | 21 | 8 | 17 | 6 | 0.35294 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_218_OURS/attempt1 | VE | 21 | 8 | 17 | 6 | 0.35294 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_217_OURS/attempt1 | V0 | 10 | 1 | 10 | 1 | 0.1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_217_OURS/attempt1 | VB | 10 | 1 | 10 | 1 | 0.1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_217_OURS/attempt1 | VO | 10 | 1 | 10 | 1 | 0.1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_217_OURS/attempt1 | VE | 10 | 1 | 10 | 1 | 0.1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_218_OURS/attempt1 | V0 | 5 | 2 | 5 | 2 | 0.4 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_218_OURS/attempt1 | VB | 5 | 2 | 5 | 2 | 0.4 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_218_OURS/attempt1 | VO | 5 | 2 | 5 | 2 | 0.4 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_218_OURS/attempt1 | VE | 5 | 2 | 5 | 2 | 0.4 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_217_OURS/attempt1 | V0 | 12 | 5 | 7 | 5 | 0.71429 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_217_OURS/attempt1 | VB | 12 | 5 | 7 | 5 | 0.71429 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_217_OURS/attempt1 | VO | 12 | 5 | 7 | 5 | 0.71429 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_217_OURS/attempt1 | VE | 12 | 5 | 7 | 5 | 0.71429 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_218_OURS/attempt1 | V0 | 13 | 7 | 10 | 7 | 0.7 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_218_OURS/attempt1 | VB | 13 | 6 | 10 | 6 | 0.6 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_218_OURS/attempt1 | VO | 13 | 6 | 10 | 6 | 0.6 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_218_OURS/attempt1 | VE | 13 | 6 | 10 | 6 | 0.6 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_217_OURS/attempt1 | V0 | 2 | 2 | 2 | 2 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_217_OURS/attempt1 | VB | 2 | 2 | 2 | 2 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_217_OURS/attempt1 | VO | 2 | 2 | 2 | 2 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_217_OURS/attempt1 | VE | 2 | 2 | 2 | 2 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_218_OURS/attempt1 | V0 | 1 | 1 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_218_OURS/attempt1 | VB | 1 | 1 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_218_OURS/attempt1 | VO | 1 | 1 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_218_OURS/attempt1 | VE | 1 | 1 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_217_OURS/attempt1 | V0 | 111 | 0 | 1 | 0 | 0 | False |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_217_OURS/attempt1 | VB | 111 | 0 | 1 | 0 | 0 | False |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_217_OURS/attempt1 | VO | 111 | 0 | 1 | 0 | 0 | False |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_217_OURS/attempt1 | VE | 111 | 46 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_218_OURS/attempt1 | V0 | 23 | 1 | 17 | 1 | 0.058824 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_218_OURS/attempt1 | VB | 23 | 1 | 17 | 1 | 0.058824 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_218_OURS/attempt1 | VO | 23 | 1 | 17 | 1 | 0.058824 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_218_OURS/attempt1 | VE | 23 | 1 | 17 | 1 | 0.058824 | True |

메시지 분포와 개별 초기값 제외 사유는 messages.csv / geometry.csv, 연속 그룹 구성은 groups.csv에 있다.

## 고정된 준비 기록

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
