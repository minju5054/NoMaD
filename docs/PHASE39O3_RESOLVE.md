# Phase39-O3 — 지도 정책 재풀이 결과

**GO — VN 선택.** 성공률 V0 32/209(15.31%) → VN·VU 각각 109/209(52.15%), **+36.84%p**. VN p95 0.627s, VU 0.709s, 수락 certificate 위반 0.

R3 274건의 재풀이와 저장 경로 418건의 추가 측정이 완료됐다(총 187.21s). V0·VE·R2 재풀이는 0회이며, 입력·동결 소스·기존 결과 해시를 검증했다. R2 58/72는 저장 VE 재사용이고, 새 R3는 VN·VU 각각 51/137이다.

출판 검증에서 상속된 O2 run 요약의 변형 목록 때문에 빠졌던 VN/VU 행을 완성된 jobs/groups 표로 보완했다. solver·protocol·판정과 원 결과는 변경하지 않았다. GO는 사전 지정한 오프라인 기준이며, base exact 경로 여유는 실행 궤적 EC 통과를 뜻하지 않는다.

| variant | label | n | baseline_success_rate | success_rate | p95_s | certificate_failures | checks |
|---|---|---|---|---|---|---|---|
| VN | GO | 209 | 0.15311 | 0.52153 | 0.62708 | 0 | {'success_plus_30pp': True, 'p95_le_1s': True, 'certificate_failures_zero': True} |
| VU | GO | 209 | 0.15311 | 0.52153 | 0.70948 | 0 | {'success_plus_30pp': True, 'p95_le_1s': True, 'certificate_failures_zero': True} |

| kind | cB_bin | variant | n | accepted_jobs | success_rate | p50_s | p95_s | certificate_failures | selected_unknown_median | selected_unknown_within_0p6_median | selected_base_exact_median_m |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R2 | <0 | V0 | 55 | 0 | 0 | 0.11916 | 0.12464 | 0 | — | — | — |
| R2 | <0 | VE | 55 | 45 | 0.81818 | 0.14607 | 0.17233 | 0 | 0 | 0 | 0.0044109 |
| R2 | <0 | VN | 55 | 45 | 0.81818 | 0.14607 | 0.17233 | 0 | 0 | 0 | 0.0044109 |
| R2 | <0 | VU | 55 | 45 | 0.81818 | 0.14607 | 0.17233 | 0 | 0 | 0 | 0.0044109 |
| R2 | 0<=cB<0.03125 | V0 | 3 | 2 | 0.66667 | 0.15492 | 0.17325 | 0 | 0 | 0 | 0.033115 |
| R2 | 0<=cB<0.03125 | VE | 3 | 2 | 0.66667 | 0.15463 | 0.1943 | 0 | 0 | 0 | 0.033115 |
| R2 | 0<=cB<0.03125 | VN | 3 | 2 | 0.66667 | 0.15463 | 0.1943 | 0 | 0 | 0 | 0.033115 |
| R2 | 0<=cB<0.03125 | VU | 3 | 2 | 0.66667 | 0.15463 | 0.1943 | 0 | 0 | 0 | 0.033115 |
| R2 | >=0.03125 | V0 | 14 | 11 | 0.78571 | 0.15485 | 0.22 | 0 | 0 | 0 | 0.034967 |
| R2 | >=0.03125 | VE | 14 | 11 | 0.78571 | 0.15918 | 0.18721 | 0 | 0 | 0 | 0.034967 |
| R2 | >=0.03125 | VN | 14 | 11 | 0.78571 | 0.15918 | 0.18721 | 0 | 0 | 0 | 0.034967 |
| R2 | >=0.03125 | VU | 14 | 11 | 0.78571 | 0.15918 | 0.18721 | 0 | 0 | 0 | 0.034967 |
| R2 | ALL | V0 | 72 | 13 | 0.18056 | 0.11987 | 0.1786 | 0 | 0 | 0 | 0.034967 |
| R2 | ALL | VE | 72 | 58 | 0.80556 | 0.14823 | 0.17828 | 0 | 0 | 0 | 0.0044109 |
| R2 | ALL | VN | 72 | 58 | 0.80556 | 0.14823 | 0.17828 | 0 | 0 | 0 | 0.0044109 |
| R2 | ALL | VU | 72 | 58 | 0.80556 | 0.14823 | 0.17828 | 0 | 0 | 0 | 0.0044109 |
| R3 | <0 | V0 | 56 | 0 | 0 | 0.13982 | 0.14338 | 0 | — | — | — |
| R3 | <0 | VE | 56 | 1 | 0.017857 | 0.37393 | 0.65229 | 0 | 0 | 0 | -0.0055783 |
| R3 | <0 | VN | 56 | 3 | 0.053571 | 0.61412 | 0.64198 | 0 | 0.16113 | 0 | -0.0055783 |
| R3 | <0 | VU | 56 | 3 | 0.053571 | 0.59599 | 0.73214 | 0 | 0.16113 | 0 | -0.0055783 |
| R3 | 0<=cB<0.03125 | V0 | 4 | 0 | 0 | 0.37587 | 0.39634 | 0 | — | — | — |
| R3 | 0<=cB<0.03125 | VE | 4 | 0 | 0 | 0.39548 | 0.60705 | 0 | — | — | — |
| R3 | 0<=cB<0.03125 | VN | 4 | 3 | 0.75 | 0.46293 | 0.51217 | 0 | 0.10448 | 0 | 0.033911 |
| R3 | 0<=cB<0.03125 | VU | 4 | 3 | 0.75 | 0.47509 | 0.5236 | 0 | 0.10448 | 0 | 0.033911 |
| R3 | >=0.03125 | V0 | 77 | 19 | 0.24675 | 0.36618 | 0.56348 | 0 | 0 | 0 | 0.11962 |
| R3 | >=0.03125 | VE | 77 | 18 | 0.23377 | 0.422 | 0.597 | 0 | 0 | 0 | 0.12441 |
| R3 | >=0.03125 | VN | 77 | 45 | 0.58442 | 0.48449 | 0.6346 | 0 | 0 | 0 | 0.082269 |
| R3 | >=0.03125 | VU | 77 | 45 | 0.58442 | 0.454 | 0.6346 | 0 | 0 | 0 | 0.074382 |
| R3 | ALL | V0 | 137 | 19 | 0.13869 | 0.27962 | 0.54168 | 0 | 0 | 0 | 0.11962 |
| R3 | ALL | VE | 137 | 19 | 0.13869 | 0.38917 | 0.63582 | 0 | 0 | 0 | 0.12289 |
| R3 | ALL | VN | 137 | 51 | 0.37226 | 0.53369 | 0.64185 | 0 | 0 | 0 | 0.071895 |
| R3 | ALL | VU | 137 | 51 | 0.37226 | 0.50164 | 0.71506 | 0 | 0 | 0 | 0.06803 |
| ALL | <0 | V0 | 111 | 0 | 0 | 0.13513 | 0.14216 | 0 | — | — | — |
| ALL | <0 | VE | 111 | 46 | 0.41441 | 0.27653 | 0.61421 | 0 | 0 | 0 | 0.0044109 |
| ALL | <0 | VN | 111 | 48 | 0.43243 | 0.30467 | 0.62589 | 0 | 0 | 0 | 0.0044109 |
| ALL | <0 | VU | 111 | 48 | 0.43243 | 0.28189 | 0.72074 | 0 | 0 | 0 | 0.0044109 |
| ALL | 0<=cB<0.03125 | V0 | 7 | 2 | 0.28571 | 0.34258 | 0.39407 | 0 | 0 | 0 | 0.033115 |
| ALL | 0<=cB<0.03125 | VE | 7 | 2 | 0.28571 | 0.36605 | 0.57022 | 0 | 0 | 0 | 0.033115 |
| ALL | 0<=cB<0.03125 | VN | 7 | 5 | 0.71429 | 0.40866 | 0.51035 | 0 | 0.10224 | 0 | 0.033911 |
| ALL | 0<=cB<0.03125 | VU | 7 | 5 | 0.71429 | 0.41448 | 0.51933 | 0 | 0.10224 | 0 | 0.033911 |
| ALL | >=0.03125 | V0 | 91 | 30 | 0.32967 | 0.34081 | 0.56024 | 0 | 0 | 0 | 0.079074 |
| ALL | >=0.03125 | VE | 91 | 29 | 0.31868 | 0.38172 | 0.58572 | 0 | 0 | 0 | 0.084822 |
| ALL | >=0.03125 | VN | 91 | 56 | 0.61538 | 0.47231 | 0.63064 | 0 | 0 | 0 | 0.056473 |
| ALL | >=0.03125 | VU | 91 | 56 | 0.61538 | 0.43845 | 0.61117 | 0 | 0 | 0 | 0.056473 |
| ALL | ALL | V0 | 209 | 32 | 0.15311 | 0.14181 | 0.52733 | 0 | 0 | 0 | 0.066679 |
| ALL | ALL | VE | 209 | 77 | 0.36842 | 0.34381 | 0.59787 | 0 | 0 | 0 | 0.0044109 |
| ALL | ALL | VN | 209 | 109 | 0.52153 | 0.44333 | 0.62708 | 0 | 0 | 0 | 0.034456 |
| ALL | ALL | VU | 209 | 109 | 0.52153 | 0.42374 | 0.70948 | 0 | 0 | 0 | 0.034456 |

## 기하 초기값

| variant | r3_jobs | attempted_sides | generated_sides | generation_rate | jobs_with_extra | selected_paths | selected_geometric | selected_geometric_fraction | exclusion_reasons |
|---|---|---|---|---|---|---|---|---|---|
| VE | 137 | 274 | 0 | 0 | 0 | 19 | 0 | 0 | {'SIDE_TOUCHES_DISK_BOUNDARY': 272, 'NO_COMPONENT_IN_STRIP': 2} |
| VN | 137 | 274 | 158 | 0.57664 | 111 | 51 | 16 | 0.31373 | {'SIDE_TOUCHES_DISK_BOUNDARY': 86, 'VIA_OUTSIDE_DISK': 10, 'VIA_BLOCKED': 7, 'NO_COMPONENT_IN_STRIP': 12, 'FORWARD_SPACING_OR_DISK_INFEASIBLE': 1} |
| VU | 137 | 274 | 154 | 0.56204 | 108 | 51 | 19 | 0.37255 | {'SIDE_TOUCHES_DISK_BOUNDARY': 86, 'VIA_OUTSIDE_DISK': 10, 'VIA_BLOCKED': 8, 'NO_COMPONENT_IN_STRIP': 14, 'FORWARD_SPACING_OR_DISK_INFEASIBLE': 2} |

## 수락 해의 base exact clearance

| kind | cB_bin | variant | accepted_paths | base_exact_min_m | base_exact_median_m | base_exact_ge_0p025 | base_exact_ge_0p025_fraction |
|---|---|---|---|---|---|---|---|
| R2 | ALL | V0 | 73 | 0.031159 | 0.034911 | 73 | 1 |
| R2 | ALL | VE | 280 | -0.0055783 | 0.0044109 | 74 | 0.26429 |
| R2 | ALL | VN | 280 | -0.0055783 | 0.0044109 | 74 | 0.26429 |
| R2 | ALL | VU | 280 | -0.0055783 | 0.0044109 | 74 | 0.26429 |
| R3 | ALL | V0 | 65 | 0.050511 | 0.12766 | 65 | 1 |
| R3 | ALL | VE | 67 | -0.0055783 | 0.12763 | 64 | 0.95522 |
| R3 | ALL | VN | 105 | -0.0055783 | 0.073327 | 100 | 0.95238 |
| R3 | ALL | VU | 97 | -0.0055783 | 0.074382 | 92 | 0.94845 |
| ALL | ALL | V0 | 138 | 0.031159 | 0.035535 | 138 | 1 |
| ALL | ALL | VE | 347 | -0.0055783 | 0.0044109 | 138 | 0.39769 |
| ALL | ALL | VN | 385 | -0.0055783 | 0.0044109 | 174 | 0.45195 |
| ALL | ALL | VU | 377 | -0.0055783 | 0.0044109 | 166 | 0.44032 |

## 위치 그룹/run

| run | variant | jobs | accepted_jobs | groups | successful_groups | group_success_rate | run_any_success |
|---|---|---|---|---|---|---|---|
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_217_OURS/attempt1 | V0 | 11 | 5 | 11 | 5 | 0.45455 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_217_OURS/attempt1 | VE | 11 | 5 | 11 | 5 | 0.45455 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_217_OURS/attempt1 | VN | 11 | 3 | 11 | 3 | 0.27273 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_217_OURS/attempt1 | VU | 11 | 3 | 11 | 3 | 0.27273 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_218_OURS/attempt1 | V0 | 21 | 8 | 17 | 6 | 0.35294 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_218_OURS/attempt1 | VE | 21 | 8 | 17 | 6 | 0.35294 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_218_OURS/attempt1 | VN | 21 | 12 | 17 | 8 | 0.47059 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H1_218_OURS/attempt1 | VU | 21 | 12 | 17 | 8 | 0.47059 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_217_OURS/attempt1 | V0 | 10 | 1 | 10 | 1 | 0.1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_217_OURS/attempt1 | VE | 10 | 1 | 10 | 1 | 0.1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_217_OURS/attempt1 | VN | 10 | 7 | 10 | 7 | 0.7 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_217_OURS/attempt1 | VU | 10 | 8 | 10 | 8 | 0.8 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_218_OURS/attempt1 | V0 | 5 | 2 | 5 | 2 | 0.4 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_218_OURS/attempt1 | VE | 5 | 2 | 5 | 2 | 0.4 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_218_OURS/attempt1 | VN | 5 | 5 | 5 | 5 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/H2_218_OURS/attempt1 | VU | 5 | 5 | 5 | 5 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_217_OURS/attempt1 | V0 | 12 | 5 | 7 | 5 | 0.71429 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_217_OURS/attempt1 | VE | 12 | 5 | 7 | 5 | 0.71429 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_217_OURS/attempt1 | VN | 12 | 10 | 7 | 6 | 0.85714 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_217_OURS/attempt1 | VU | 12 | 10 | 7 | 6 | 0.85714 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_218_OURS/attempt1 | V0 | 13 | 7 | 10 | 7 | 0.7 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_218_OURS/attempt1 | VE | 13 | 6 | 10 | 6 | 0.6 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_218_OURS/attempt1 | VN | 13 | 10 | 10 | 8 | 0.8 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/L2_218_OURS/attempt1 | VU | 13 | 10 | 10 | 8 | 0.8 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_217_OURS/attempt1 | V0 | 2 | 2 | 2 | 2 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_217_OURS/attempt1 | VE | 2 | 2 | 2 | 2 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_217_OURS/attempt1 | VN | 2 | 2 | 2 | 2 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_217_OURS/attempt1 | VU | 2 | 2 | 2 | 2 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_218_OURS/attempt1 | V0 | 1 | 1 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_218_OURS/attempt1 | VE | 1 | 1 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_218_OURS/attempt1 | VN | 1 | 1 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/LC_218_OURS/attempt1 | VU | 1 | 1 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_217_OURS/attempt1 | V0 | 111 | 0 | 1 | 0 | 0 | False |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_217_OURS/attempt1 | VE | 111 | 46 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_217_OURS/attempt1 | VN | 111 | 48 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_217_OURS/attempt1 | VU | 111 | 48 | 1 | 1 | 1 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_218_OURS/attempt1 | V0 | 23 | 1 | 17 | 1 | 0.058824 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_218_OURS/attempt1 | VE | 23 | 1 | 17 | 1 | 0.058824 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_218_OURS/attempt1 | VN | 23 | 11 | 17 | 11 | 0.64706 | True |
| /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase38_01/night1/main/SLW_218_OURS/attempt1 | VU | 23 | 10 | 17 | 10 | 0.58824 | True |

수락 해별 원 base exact clearance는 base_clearances.csv, 선택 경로의 미관측 비율은 jobs.csv에 있다.

## 고정된 준비 기록

실데이터 재풀이·시뮬레이션0회. V0/VE209건씩은 저장 결과만 재사용하며 solver 진입을 금지한다. R2는 VE와 동일해72건의 결과·시간을 VN/VU에서도 재사용한다. 새 재풀이는 R3 137건×VN/VU=274건,4프로세스다. A*·경로 검색·슬랙은 사용하지 않는다.

| 변형 | R3 hard 제약 / certificate / VO 기하 초기값 지도 |
|---|---|
| VU | 원 base occupied만; unknown=free |
| VN | occupied OR (~observed AND 셀 중심이 B에서0.6m 이내); 바깥 unknown=free |

지도는 첫0.3m를 포함한 전체 경로에 적용한다. CLR soft 조회 지도는 기존 VE(base 첫0.3m/strict 이후) 그대로다. c_B와 보고 구간은 항상 원 base의 `d(B)−h/√2`로 유지한다. B행 제외·낮은 c_B 탈출·s_esc certificate·초기값 생성/선택·곡률/길이/반경·SLSQP 설정은 VE 그대로다. 기하 초기값은39-O2의 동일 함수다.

실제39-O2 strict 구현은 shadow.py의 occupied|~observed뿐 아니라 **last_free<0 또는 관측 후2초 초과**도 차단하는 recent.py의 build_cache다. 새 hard/certificate/기하 지도는 위 표의 mask만 쓰므로 이 추가 recency 차단을 포함하지 않는다. 이 차이를 숨기지 않고 기록한다.

보고는 V0/VE/VN/VU의 c_B(<0 / 0~0.03125 / ≥0.03125)×R2/R3 표와SLSQP 메시지,기하 초기값 생성률·선택 비율,위치 중복 그룹/run 표다. 선택 경로는 전체 호길이5mm 이하 균등 표본이 놓인 **원 observed=false 칸** 비율과 그중 B반경0.6m 내의 조건부 비율을 기록한다. 같은 job의 모든 수락 해에 **원 base 지도 exact clearance**와≥0.025 여부를 기록하고 선택 해를 표시한다. 이는 EC와 같은 지도의 경로 검사이며,PP/SP 실행 궤적을 검사하는 EC PASS를 의미하지 않는다. EC·oracle은 실행하지 않는다.

전체209 job 성공률이 저장 V0보다≥30%p 증가 AND p95≤1s AND certificate 실패0이면 GO. 둘 다 통과하면 더 보수적인 VN→VU 순으로 선택한다. p95에는 동일한 R2의 과거 VE시간과 새 R3 job시간이 함께 들어가며,R3 단독 시간도 표에 표시한다. 미완료 자료는 판정하지 않는다. 새 job시간에는 map/cache·기하 생성·IPC·선택이 포함되며,기존 경로의 추가 측정/audit는 제외한다.

Protocol SHA256 `c2c9b7634fb1961f1df61db52f4a7208a5020b9112e4c2cf10b036cc49657312`. 예상 약8.6분(저장 VE R3 시간의 보수적 계수와추가 측정 여유 기반 계획 추정).55분 후 새 job을 시작하지 않고 현재 job 완료 후 PARTIAL로 저장하며 같은 명령으로 재개한다. 원본 입력·V0·VE hash를 검증하고 수정하지 않는다.

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase39o3.run > ../artifacts/isaac6/phase39o3_01.log 2>&1 < /dev/null &
```

진행 확인: `PYTHONPATH=research /usr/bin/python3 -m nomad_phase39o3.run --status`. 완료 후 이 문서와 `research/results/phase39o3/` 표를 자동 생성한다. 온라인 준비는 하지 않는다.
