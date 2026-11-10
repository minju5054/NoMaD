# Chunk 적용 위치·잔여 길이와 정렬 회전

| item | value |
|---|---|
| 범위 | Phase47-C60+Phase51-P20+Phase52-P40=120 selected analysis runs; excluded retry attempts not used |
| 원 chunk | 선택된 원 NoMaD8개 waypoint polyline,observation world frame. 관측 원점이나 B를 앞에 덧붙이지 않음. GRAPH_REC도 실행 보정 경로가 아니라 선택한 원 후보를 사용 |
| B와 투영 | PATH_APPLIED의 실제 적용 pose B;가장 가까운 polyline 투영s_B∈[0,L],잔여=L-s_B |
| 잔여 첫 방향 | geometric_suffix/suffix_direction: 투영점에서 다음 원 waypoint로 향하는 첫 suffix 선분과 로봇heading의 wrapped 절댓값. 잔여가0이면NA |
| 실행기 정렬 방향 | suffix_heading/heading_error/mean_heading: 동결 정렬 규칙의 s_B+0.05m 이상 첫 원 waypoint로 실제 B에서 향하는 방향. 해당 점이 없으면NA. 기하학적 suffix 방향과 별도 기록하며 두 방향 모두 ALIGN_ROTATE와 상관 계산 |
| 끝 초과 지표 | 사용자 지정 잔여<0.05m 비율은 끝 근처/짧은 잔여도 포함하므로 실제 초과와 구분. 마지막 구간 tangent에 대한B-end 전진 투영>0인 진짜 끝 초과 수를 별도 열 |
| 설치 중복 | 모든 PATH_APPLIED와 chunk id별 첫 설치 두 범위;Graph 교체·주기EC 대체가 같은chunk를 재설치할 수 있음 |
| 상관 | run별 잔여<5cm비율/잔여중앙값/방향오차평균/투영진행비율 vs실제 ALIGN_ROTATE 상태 지속시간. Pearson와Spearman,상수변수/작은n은NA. 지연·방법·장면·날짜가 교란되어 인과 해석 불가 |
| WIDE | Phase51 WIDE는지연0.75이지만상자기하가다름. 조건별 표를 함께 보며 합산 지연표만으로 효과를 주장하지 않음 |

| scope | delay_s | grouping | runs | n | native_length_median_m | projected_s_median_m | remaining_median_m | remaining_p10_m | heading_error_median_deg | heading_error_p95_deg | heading_defined_n | suffix_direction_median_deg | suffix_direction_p95_deg | suffix_direction_defined_n | remaining_lt_5cm | remaining_lt_5cm_fraction | true_endpoint_overshoot | align_rotate_run_median_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL_INSTALLATIONS | 0.75 | scope/delay_s | 90 | 3599 | 0.36342 | 0.06709 | 0.25556 | 0.11009 | 27.546 | 107.17 | 3460 | 14.477 | 63.077 | 3572 | 139 | 0.038622 | 27 | 0.66667 |
| ALL_INSTALLATIONS | 1.5 | scope/delay_s | 30 | 1281 | 0.3543 | 0.062433 | 0.24127 | 0.025694 | 43.597 | 144.95 | 1113 | 26.381 | 86.162 | 1183 | 168 | 0.13115 | 98 | 7.8333 |
| FIRST_INSTALL_PER_CHUNK | 0.75 | scope/delay_s | 90 | 3337 | 0.36326 | 0.063947 | 0.25419 | 0.11234 | 27.162 | 105.35 | 3222 | 14.556 | 62.672 | 3322 | 115 | 0.034462 | 15 | 0.66667 |
| FIRST_INSTALL_PER_CHUNK | 1.5 | scope/delay_s | 30 | 1085 | 0.35251 | 0.05568 | 0.23735 | 0.046779 | 41.955 | 146.75 | 970 | 27.126 | 88.163 | 1031 | 115 | 0.10599 | 54 | 7.8333 |
| ALL_INSTALLATIONS | 0.75 | scope/phase/condition/delay_s | 60 | 1853 | 0.36256 | 0.085372 | 0.23992 | 0.096728 | 26.002 | 104.78 | 1769 | 13.568 | 62.621 | 1839 | 84 | 0.045332 | 14 | 0.44444 |
| ALL_INSTALLATIONS | 1.5 | scope/phase/condition/delay_s | 10 | 425 | 0.34705 | 0.062414 | 0.22987 | 0.06432 | 34.52 | 118.91 | 387 | 16.188 | 72.771 | 409 | 38 | 0.089412 | 16 | 4 |
| ALL_INSTALLATIONS | 0.75 | scope/phase/condition/delay_s | 10 | 528 | 0.3755 | 0.043252 | 0.28263 | 0.14284 | 28.75 | 119.26 | 516 | 15.173 | 67.003 | 526 | 12 | 0.022727 | 2 | 3.1667 |
| ALL_INSTALLATIONS | 0.75 | scope/phase/condition/delay_s | 20 | 1218 | 0.35901 | 0.059074 | 0.26211 | 0.11882 | 29.707 | 111.75 | 1175 | 15.181 | 61.296 | 1207 | 43 | 0.035304 | 11 | 2.2778 |
| ALL_INSTALLATIONS | 1.5 | scope/phase/condition/delay_s | 20 | 856 | 0.36055 | 0.062643 | 0.25396 | 0.0081747 | 53.496 | 149.84 | 726 | 31.735 | 91.56 | 774 | 130 | 0.15187 | 82 | 15.444 |
| FIRST_INSTALL_PER_CHUNK | 0.75 | scope/phase/condition/delay_s | 60 | 1796 | 0.36248 | 0.082944 | 0.24214 | 0.099052 | 25.705 | 104.15 | 1719 | 13.475 | 61.464 | 1785 | 77 | 0.042873 | 11 | 0.44444 |
| FIRST_INSTALL_PER_CHUNK | 1.5 | scope/phase/condition/delay_s | 10 | 392 | 0.34723 | 0.053165 | 0.23649 | 0.080993 | 32.785 | 120.81 | 371 | 16.184 | 73.017 | 386 | 21 | 0.053571 | 6 | 4 |
| FIRST_INSTALL_PER_CHUNK | 0.75 | scope/phase/condition/delay_s | 10 | 507 | 0.37613 | 0.040037 | 0.28831 | 0.14669 | 27.699 | 117.22 | 498 | 15.173 | 64.041 | 506 | 9 | 0.017751 | 1 | 3.1667 |
| FIRST_INSTALL_PER_CHUNK | 0.75 | scope/phase/condition/delay_s | 20 | 1034 | 0.35791 | 0.053049 | 0.2592 | 0.11976 | 29.969 | 112.12 | 1005 | 15.725 | 61.248 | 1031 | 29 | 0.028046 | 3 | 2.2778 |
| FIRST_INSTALL_PER_CHUNK | 1.5 | scope/phase/condition/delay_s | 20 | 693 | 0.36207 | 0.058655 | 0.23795 | 0.032294 | 53.573 | 152 | 599 | 32.967 | 93.141 | 645 | 94 | 0.13564 | 48 | 15.444 |

| scope | delay_s | predictor | response | n | pearson_r | spearman_rho | note |
|---|---|---|---|---|---|---|---|
| ALL_INSTALLATIONS | 0.75 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 90 | -0.024033 | -0.058107 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 90 | 0.60826 | 0.68745 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | mean_heading_error_deg | ALIGN_ROTATE seconds | 90 | 0.6382 | 0.68399 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | remaining_median_m | ALIGN_ROTATE seconds | 90 | 0.065543 | 0.19894 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | projection_fraction_mean | ALIGN_ROTATE seconds | 90 | -0.61297 | -0.78762 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 30 | -0.12475 | -0.028501 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 30 | 0.80476 | 0.87047 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | mean_heading_error_deg | ALIGN_ROTATE seconds | 30 | 0.81677 | 0.86334 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | remaining_median_m | ALIGN_ROTATE seconds | 30 | 0.38261 | 0.37859 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | projection_fraction_mean | ALIGN_ROTATE seconds | 30 | -0.53899 | -0.56733 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 90 | -0.055308 | -0.058251 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 90 | 0.59444 | 0.69448 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | mean_heading_error_deg | ALIGN_ROTATE seconds | 90 | 0.6174 | 0.66801 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | remaining_median_m | ALIGN_ROTATE seconds | 90 | 0.051182 | 0.17316 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | projection_fraction_mean | ALIGN_ROTATE seconds | 90 | -0.6319 | -0.77644 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 30 | 0.022618 | 0.15068 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 30 | 0.7916 | 0.82195 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | mean_heading_error_deg | ALIGN_ROTATE seconds | 30 | 0.8059 | 0.8442 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | remaining_median_m | ALIGN_ROTATE seconds | 30 | 0.39371 | 0.29713 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | projection_fraction_mean | ALIGN_ROTATE seconds | 30 | -0.50462 | -0.52237 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 60 | -0.068954 | -0.046578 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 60 | 0.59409 | 0.67361 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | mean_heading_error_deg | ALIGN_ROTATE seconds | 60 | 0.59171 | 0.63053 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | remaining_median_m | ALIGN_ROTATE seconds | 60 | -0.0082879 | 0.056808 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | projection_fraction_mean | ALIGN_ROTATE seconds | 60 | -0.61089 | -0.71386 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 10 | 0.47667 | 0.21474 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 10 | 0.75855 | 0.74239 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | mean_heading_error_deg | ALIGN_ROTATE seconds | 10 | 0.80312 | 0.82828 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | remaining_median_m | ALIGN_ROTATE seconds | 10 | 0.11204 | 0.31291 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | projection_fraction_mean | ALIGN_ROTATE seconds | 10 | -0.71927 | -0.6933 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 10 | 0.48906 | 0.55319 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 10 | 0.61267 | 0.50303 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | mean_heading_error_deg | ALIGN_ROTATE seconds | 10 | 0.70031 | 0.67273 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | remaining_median_m | ALIGN_ROTATE seconds | 10 | -0.0091689 | -0.13939 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | projection_fraction_mean | ALIGN_ROTATE seconds | 10 | -0.47224 | -0.33333 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 20 | 0.35846 | 0.27153 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 20 | 0.82075 | 0.77468 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | mean_heading_error_deg | ALIGN_ROTATE seconds | 20 | 0.79351 | 0.76262 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | remaining_median_m | ALIGN_ROTATE seconds | 20 | -0.16147 | 0.12359 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 0.75 | projection_fraction_mean | ALIGN_ROTATE seconds | 20 | -0.62894 | -0.80859 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 20 | -0.65068 | -0.68197 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 20 | 0.76803 | 0.77143 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | mean_heading_error_deg | ALIGN_ROTATE seconds | 20 | 0.75977 | 0.76992 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | remaining_median_m | ALIGN_ROTATE seconds | 20 | 0.51671 | 0.53233 | descriptive/repeated seeds,not independent causal evidence |
| ALL_INSTALLATIONS | 1.5 | projection_fraction_mean | ALIGN_ROTATE seconds | 20 | -0.78122 | -0.78496 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 60 | -0.071441 | -0.0055163 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 60 | 0.58135 | 0.66685 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | mean_heading_error_deg | ALIGN_ROTATE seconds | 60 | 0.5754 | 0.60839 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | remaining_median_m | ALIGN_ROTATE seconds | 60 | -0.0079509 | 0.075978 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | projection_fraction_mean | ALIGN_ROTATE seconds | 60 | -0.61451 | -0.67855 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 10 | 0.51741 | 0.30064 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 10 | 0.73743 | 0.68103 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | mean_heading_error_deg | ALIGN_ROTATE seconds | 10 | 0.8217 | 0.7792 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | remaining_median_m | ALIGN_ROTATE seconds | 10 | 0.15852 | 0.20247 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | projection_fraction_mean | ALIGN_ROTATE seconds | 10 | -0.80902 | -0.82828 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 10 | 0.19386 | 0.1902 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 10 | 0.62806 | 0.47879 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | mean_heading_error_deg | ALIGN_ROTATE seconds | 10 | 0.67963 | 0.62424 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | remaining_median_m | ALIGN_ROTATE seconds | 10 | -0.020034 | -0.11515 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | projection_fraction_mean | ALIGN_ROTATE seconds | 10 | -0.61837 | -0.33333 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 20 | 0.46962 | 0.30232 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 20 | 0.76785 | 0.79201 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | mean_heading_error_deg | ALIGN_ROTATE seconds | 20 | 0.73646 | 0.73323 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | remaining_median_m | ALIGN_ROTATE seconds | 20 | -0.14032 | 0.039186 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 0.75 | projection_fraction_mean | ALIGN_ROTATE seconds | 20 | -0.65624 | -0.80709 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | end_lt_5cm_fraction | ALIGN_ROTATE seconds | 20 | -0.61927 | -0.68571 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | mean_geometric_heading_error_deg | ALIGN_ROTATE seconds | 20 | 0.73341 | 0.70677 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | mean_heading_error_deg | ALIGN_ROTATE seconds | 20 | 0.7305 | 0.73684 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | remaining_median_m | ALIGN_ROTATE seconds | 20 | 0.61383 | 0.60752 | descriptive/repeated seeds,not independent causal evidence |
| FIRST_INSTALL_PER_CHUNK | 1.5 | projection_fraction_mean | ALIGN_ROTATE seconds | 20 | -0.84194 | -0.78797 | descriptive/repeated seeds,not independent causal evidence |

| uid | phase | condition | delay_s | scene | method | seed | scope | installations | align_rotate_s | align_rotate_fraction | end_lt_5cm_fraction | remaining_median_m | mean_heading_error_deg | mean_geometric_heading_error_deg | heading_defined_n | projection_fraction_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| phase47c/H1/221/NOMAD_RAW | phase47c | D075 | 0.75 | H1 | NOMAD_RAW | 221 | ALL_INSTALLATIONS | 24 | 0.33333 | 0.012422 | 0.041667 | 0.23024 | 37.692 | 19.543 | 23 | 0.25844 |
| phase47c/H1/221/NOMAD_RAW | phase47c | D075 | 0.75 | H1 | NOMAD_RAW | 221 | FIRST_INSTALL_PER_CHUNK | 24 | 0.33333 | 0.012422 | 0.041667 | 0.23024 | 37.692 | 19.543 | 23 | 0.25844 |
| phase47c/H1/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H1 | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 28 | 0 | 0 | 0.071429 | 0.23736 | 32.219 | 17.964 | 26 | 0.33628 |
| phase47c/H1/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H1 | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 28 | 0 | 0 | 0.071429 | 0.23736 | 32.219 | 17.964 | 26 | 0.33628 |
| phase47c/H1/221/OURS-DETOUR | phase47c | D075 | 0.75 | H1 | OURS-DETOUR | 221 | ALL_INSTALLATIONS | 27 | 0 | 0 | 0.037037 | 0.24087 | 29.152 | 14.597 | 26 | 0.35676 |
| phase47c/H1/221/OURS-DETOUR | phase47c | D075 | 0.75 | H1 | OURS-DETOUR | 221 | FIRST_INSTALL_PER_CHUNK | 25 | 0 | 0 | 0 | 0.24611 | 29.285 | 14.483 | 25 | 0.32172 |
| phase47c/H1/222/NOMAD_RAW | phase47c | D075 | 0.75 | H1 | NOMAD_RAW | 222 | ALL_INSTALLATIONS | 28 | 0.11111 | 0.0036331 | 0.10714 | 0.24947 | 29.989 | 14.964 | 25 | 0.37277 |
| phase47c/H1/222/NOMAD_RAW | phase47c | D075 | 0.75 | H1 | NOMAD_RAW | 222 | FIRST_INSTALL_PER_CHUNK | 28 | 0.11111 | 0.0036331 | 0.10714 | 0.24947 | 29.989 | 14.964 | 25 | 0.37277 |
| phase47c/H1/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H1 | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 30 | 0.94444 | 0.031657 | 0 | 0.27582 | 30.936 | 14.647 | 30 | 0.31588 |
| phase47c/H1/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H1 | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 27 | 0.94444 | 0.031657 | 0 | 0.27823 | 29.885 | 14.222 | 27 | 0.31308 |
| phase47c/H1/222/OURS-DETOUR | phase47c | D075 | 0.75 | H1 | OURS-DETOUR | 222 | ALL_INSTALLATIONS | 30 | 0.66667 | 0.021798 | 0.066667 | 0.26937 | 28.018 | 17.4 | 28 | 0.31928 |
| phase47c/H1/222/OURS-DETOUR | phase47c | D075 | 0.75 | H1 | OURS-DETOUR | 222 | FIRST_INSTALL_PER_CHUNK | 28 | 0.66667 | 0.021798 | 0.071429 | 0.26937 | 27.373 | 17.438 | 26 | 0.31875 |
| phase47c/H1/223/NOMAD_RAW | phase47c | D075 | 0.75 | H1 | NOMAD_RAW | 223 | ALL_INSTALLATIONS | 34 | 0.33333 | 0.0091116 | 0.058824 | 0.23421 | 24.254 | 13.004 | 32 | 0.28824 |
| phase47c/H1/223/NOMAD_RAW | phase47c | D075 | 0.75 | H1 | NOMAD_RAW | 223 | FIRST_INSTALL_PER_CHUNK | 34 | 0.33333 | 0.0091116 | 0.058824 | 0.23421 | 24.254 | 13.004 | 32 | 0.28824 |
| phase47c/H1/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H1 | OURS-DETOUR+HMM | 223 | ALL_INSTALLATIONS | 31 | 0 | 0 | 0.064516 | 0.24217 | 33.848 | 18.335 | 29 | 0.34868 |
| phase47c/H1/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H1 | OURS-DETOUR+HMM | 223 | FIRST_INSTALL_PER_CHUNK | 29 | 0 | 0 | 0.034483 | 0.24643 | 32.752 | 18.177 | 28 | 0.31506 |
| phase47c/H1/223/OURS-DETOUR | phase47c | D075 | 0.75 | H1 | OURS-DETOUR | 223 | ALL_INSTALLATIONS | 27 | 0.33333 | 0.011976 | 0 | 0.24763 | 30.485 | 14.028 | 27 | 0.34748 |
| phase47c/H1/223/OURS-DETOUR | phase47c | D075 | 0.75 | H1 | OURS-DETOUR | 223 | FIRST_INSTALL_PER_CHUNK | 25 | 0.33333 | 0.011976 | 0 | 0.25007 | 29.072 | 13.733 | 25 | 0.32435 |
| phase47c/H1/224/NOMAD_RAW | phase47c | D075 | 0.75 | H1 | NOMAD_RAW | 224 | ALL_INSTALLATIONS | 25 | 0 | 0 | 0.04 | 0.23632 | 36.802 | 16.349 | 24 | 0.39633 |
| phase47c/H1/224/NOMAD_RAW | phase47c | D075 | 0.75 | H1 | NOMAD_RAW | 224 | FIRST_INSTALL_PER_CHUNK | 25 | 0 | 0 | 0.04 | 0.23632 | 36.802 | 16.349 | 24 | 0.39633 |
| phase47c/H1/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H1 | OURS-DETOUR+HMM | 224 | ALL_INSTALLATIONS | 27 | 0.44444 | 0.015152 | 0.037037 | 0.25436 | 28.475 | 14.019 | 26 | 0.33241 |
| phase47c/H1/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H1 | OURS-DETOUR+HMM | 224 | FIRST_INSTALL_PER_CHUNK | 27 | 0.44444 | 0.015152 | 0.037037 | 0.25436 | 28.475 | 14.019 | 26 | 0.33241 |
| phase47c/H1/224/OURS-DETOUR | phase47c | D075 | 0.75 | H1 | OURS-DETOUR | 224 | ALL_INSTALLATIONS | 18 | 0.33333 | 0.016 | 0 | 0.26869 | 28.793 | 16.254 | 18 | 0.25522 |
| phase47c/H1/224/OURS-DETOUR | phase47c | D075 | 0.75 | H1 | OURS-DETOUR | 224 | FIRST_INSTALL_PER_CHUNK | 18 | 0.33333 | 0.016 | 0 | 0.26869 | 28.793 | 16.254 | 18 | 0.25522 |
| phase47c/H2/221/NOMAD_RAW | phase47c | D075 | 0.75 | H2 | NOMAD_RAW | 221 | ALL_INSTALLATIONS | 16 | 0 | 0 | 0.1875 | 0.14856 | 32.295 | 25.065 | 13 | 0.49944 |
| phase47c/H2/221/NOMAD_RAW | phase47c | D075 | 0.75 | H2 | NOMAD_RAW | 221 | FIRST_INSTALL_PER_CHUNK | 16 | 0 | 0 | 0.1875 | 0.14856 | 32.295 | 25.065 | 13 | 0.49944 |
| phase47c/H2/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H2 | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 81 | 6.6667 | 0.08 | 0.024691 | 0.30459 | 36.893 | 19.916 | 79 | 0.21763 |
| phase47c/H2/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H2 | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 80 | 6.6667 | 0.08 | 0.025 | 0.3037 | 37.22 | 20.126 | 78 | 0.21844 |
| phase47c/H2/221/OURS-DETOUR | phase47c | D075 | 0.75 | H2 | OURS-DETOUR | 221 | ALL_INSTALLATIONS | 13 | 0 | 0 | 0.15385 | 0.16922 | 33.386 | 18.732 | 11 | 0.42494 |
| phase47c/H2/221/OURS-DETOUR | phase47c | D075 | 0.75 | H2 | OURS-DETOUR | 221 | FIRST_INSTALL_PER_CHUNK | 13 | 0 | 0 | 0.15385 | 0.16922 | 33.386 | 18.732 | 11 | 0.42494 |
| phase47c/H2/222/NOMAD_RAW | phase47c | D075 | 0.75 | H2 | NOMAD_RAW | 222 | ALL_INSTALLATIONS | 16 | 1.5278 | 0.081967 | 0.0625 | 0.14755 | 38.931 | 22.889 | 15 | 0.39593 |
| phase47c/H2/222/NOMAD_RAW | phase47c | D075 | 0.75 | H2 | NOMAD_RAW | 222 | FIRST_INSTALL_PER_CHUNK | 16 | 1.5278 | 0.081967 | 0.0625 | 0.14755 | 38.931 | 22.889 | 15 | 0.39593 |
| phase47c/H2/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H2 | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 43 | 2.3611 | 0.048599 | 0.023256 | 0.24945 | 38.145 | 18.747 | 42 | 0.31545 |
| phase47c/H2/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H2 | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 43 | 2.3611 | 0.048599 | 0.023256 | 0.24945 | 38.145 | 18.747 | 42 | 0.31545 |
| phase47c/H2/222/OURS-DETOUR | phase47c | D075 | 0.75 | H2 | OURS-DETOUR | 222 | ALL_INSTALLATIONS | 19 | 1.1111 | 0.054422 | 0.052632 | 0.23251 | 46.689 | 24.468 | 18 | 0.28534 |
| phase47c/H2/222/OURS-DETOUR | phase47c | D075 | 0.75 | H2 | OURS-DETOUR | 222 | FIRST_INSTALL_PER_CHUNK | 18 | 1.1111 | 0.054422 | 0.055556 | 0.25066 | 45.135 | 24.224 | 17 | 0.28688 |
| phase47c/H2/223/NOMAD_RAW | phase47c | D075 | 0.75 | H2 | NOMAD_RAW | 223 | ALL_INSTALLATIONS | 12 | 0 | 0 | 0.083333 | 0.12712 | 19.955 | 12.222 | 11 | 0.49342 |
| phase47c/H2/223/NOMAD_RAW | phase47c | D075 | 0.75 | H2 | NOMAD_RAW | 223 | FIRST_INSTALL_PER_CHUNK | 12 | 0 | 0 | 0.083333 | 0.12712 | 19.955 | 12.222 | 11 | 0.49342 |
| phase47c/H2/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H2 | OURS-DETOUR+HMM | 223 | ALL_INSTALLATIONS | 44 | 1.4444 | 0.031344 | 0.022727 | 0.26463 | 34.282 | 18.549 | 43 | 0.20699 |
| phase47c/H2/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H2 | OURS-DETOUR+HMM | 223 | FIRST_INSTALL_PER_CHUNK | 44 | 1.4444 | 0.031344 | 0.022727 | 0.26463 | 34.282 | 18.549 | 43 | 0.20699 |
| phase47c/H2/223/OURS-DETOUR | phase47c | D075 | 0.75 | H2 | OURS-DETOUR | 223 | ALL_INSTALLATIONS | 17 | 1 | 0.051064 | 0.058824 | 0.19796 | 47.285 | 24.235 | 16 | 0.33134 |
| phase47c/H2/223/OURS-DETOUR | phase47c | D075 | 0.75 | H2 | OURS-DETOUR | 223 | FIRST_INSTALL_PER_CHUNK | 17 | 1 | 0.051064 | 0.058824 | 0.19796 | 47.285 | 24.235 | 16 | 0.33134 |
| phase47c/H2/224/NOMAD_RAW | phase47c | D075 | 0.75 | H2 | NOMAD_RAW | 224 | ALL_INSTALLATIONS | 14 | 0.33333 | 0.020851 | 0.071429 | 0.13134 | 44.684 | 17.788 | 13 | 0.49991 |
| phase47c/H2/224/NOMAD_RAW | phase47c | D075 | 0.75 | H2 | NOMAD_RAW | 224 | FIRST_INSTALL_PER_CHUNK | 14 | 0.33333 | 0.020851 | 0.071429 | 0.13134 | 44.684 | 17.788 | 13 | 0.49991 |
| phase47c/H2/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H2 | OURS-DETOUR+HMM | 224 | ALL_INSTALLATIONS | 86 | 1.5556 | 0.018123 | 0.023256 | 0.28538 | 29.177 | 15.077 | 84 | 0.24528 |
| phase47c/H2/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | H2 | OURS-DETOUR+HMM | 224 | FIRST_INSTALL_PER_CHUNK | 84 | 1.5556 | 0.018123 | 0.011905 | 0.29244 | 29.341 | 15.197 | 83 | 0.23117 |
| phase47c/H2/224/OURS-DETOUR | phase47c | D075 | 0.75 | H2 | OURS-DETOUR | 224 | ALL_INSTALLATIONS | 24 | 0.55556 | 0.021097 | 0.041667 | 0.30135 | 29.296 | 14.268 | 23 | 0.26632 |
| phase47c/H2/224/OURS-DETOUR | phase47c | D075 | 0.75 | H2 | OURS-DETOUR | 224 | FIRST_INSTALL_PER_CHUNK | 24 | 0.55556 | 0.021097 | 0.041667 | 0.30135 | 29.296 | 14.268 | 23 | 0.26632 |
| phase47c/L2/221/NOMAD_RAW | phase47c | D075 | 0.75 | L2 | NOMAD_RAW | 221 | ALL_INSTALLATIONS | 17 | 0.33333 | 0.016807 | 0.11765 | 0.22521 | 36.411 | 21.498 | 15 | 0.38465 |
| phase47c/L2/221/NOMAD_RAW | phase47c | D075 | 0.75 | L2 | NOMAD_RAW | 221 | FIRST_INSTALL_PER_CHUNK | 17 | 0.33333 | 0.016807 | 0.11765 | 0.22521 | 36.411 | 21.498 | 15 | 0.38465 |
| phase47c/L2/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | L2 | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 40 | 0 | 0 | 0.075 | 0.24296 | 30.271 | 15.635 | 37 | 0.36867 |
| phase47c/L2/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | L2 | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 40 | 0 | 0 | 0.075 | 0.24296 | 30.271 | 15.635 | 37 | 0.36867 |
| phase47c/L2/221/OURS-DETOUR | phase47c | D075 | 0.75 | L2 | OURS-DETOUR | 221 | ALL_INSTALLATIONS | 19 | 0.88889 | 0.040712 | 0.052632 | 0.24994 | 43.361 | 22.179 | 18 | 0.30074 |
| phase47c/L2/221/OURS-DETOUR | phase47c | D075 | 0.75 | L2 | OURS-DETOUR | 221 | FIRST_INSTALL_PER_CHUNK | 19 | 0.88889 | 0.040712 | 0.052632 | 0.24994 | 43.361 | 22.179 | 18 | 0.30074 |
| phase47c/L2/222/NOMAD_RAW | phase47c | D075 | 0.75 | L2 | NOMAD_RAW | 222 | ALL_INSTALLATIONS | 42 | 0.33333 | 0.0074349 | 0.02381 | 0.24037 | 28.313 | 13.384 | 41 | 0.34758 |
| phase47c/L2/222/NOMAD_RAW | phase47c | D075 | 0.75 | L2 | NOMAD_RAW | 222 | FIRST_INSTALL_PER_CHUNK | 42 | 0.33333 | 0.0074349 | 0.02381 | 0.24037 | 28.313 | 13.384 | 41 | 0.34758 |
| phase47c/L2/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | L2 | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 47 | 1.3333 | 0.026359 | 0.021277 | 0.30878 | 38.377 | 20.682 | 46 | 0.25812 |
| phase47c/L2/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | L2 | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 46 | 1.3333 | 0.026359 | 0.021739 | 0.30911 | 36.626 | 19.47 | 45 | 0.262 |
| phase47c/L2/222/OURS-DETOUR | phase47c | D075 | 0.75 | L2 | OURS-DETOUR | 222 | ALL_INSTALLATIONS | 15 | 0.33333 | 0.018663 | 0.066667 | 0.24944 | 30.76 | 13.217 | 14 | 0.3236 |
| phase47c/L2/222/OURS-DETOUR | phase47c | D075 | 0.75 | L2 | OURS-DETOUR | 222 | FIRST_INSTALL_PER_CHUNK | 15 | 0.33333 | 0.018663 | 0.066667 | 0.24944 | 30.76 | 13.217 | 14 | 0.3236 |
| phase47c/L2/223/NOMAD_RAW | phase47c | D075 | 0.75 | L2 | NOMAD_RAW | 223 | ALL_INSTALLATIONS | 12 | 0 | 0 | 0.083333 | 0.15567 | 27.576 | 10.271 | 11 | 0.47774 |
| phase47c/L2/223/NOMAD_RAW | phase47c | D075 | 0.75 | L2 | NOMAD_RAW | 223 | FIRST_INSTALL_PER_CHUNK | 12 | 0 | 0 | 0.083333 | 0.15567 | 27.576 | 10.271 | 11 | 0.47774 |
| phase47c/L2/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | L2 | OURS-DETOUR+HMM | 223 | ALL_INSTALLATIONS | 61 | 7.1111 | 0.10802 | 0.016393 | 0.29146 | 44.766 | 26.728 | 60 | 0.14297 |
| phase47c/L2/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | L2 | OURS-DETOUR+HMM | 223 | FIRST_INSTALL_PER_CHUNK | 59 | 7.1111 | 0.10802 | 0.016949 | 0.29146 | 42.857 | 25.621 | 58 | 0.14575 |
| phase47c/L2/223/OURS-DETOUR | phase47c | D075 | 0.75 | L2 | OURS-DETOUR | 223 | ALL_INSTALLATIONS | 16 | 0.66667 | 0.035398 | 0.0625 | 0.2105 | 31.958 | 15.564 | 15 | 0.29825 |
| phase47c/L2/223/OURS-DETOUR | phase47c | D075 | 0.75 | L2 | OURS-DETOUR | 223 | FIRST_INSTALL_PER_CHUNK | 16 | 0.66667 | 0.035398 | 0.0625 | 0.2105 | 31.958 | 15.564 | 15 | 0.29825 |
| phase47c/L2/224/NOMAD_RAW | phase47c | D075 | 0.75 | L2 | NOMAD_RAW | 224 | ALL_INSTALLATIONS | 14 | 1.3333 | 0.080402 | 0.14286 | 0.14367 | 51.075 | 21.963 | 12 | 0.45349 |
| phase47c/L2/224/NOMAD_RAW | phase47c | D075 | 0.75 | L2 | NOMAD_RAW | 224 | FIRST_INSTALL_PER_CHUNK | 14 | 1.3333 | 0.080402 | 0.14286 | 0.14367 | 51.075 | 21.963 | 12 | 0.45349 |
| phase47c/L2/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | L2 | OURS-DETOUR+HMM | 224 | ALL_INSTALLATIONS | 51 | 0.66667 | 0.012678 | 0.019608 | 0.26709 | 31.751 | 13.747 | 50 | 0.33975 |
| phase47c/L2/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | L2 | OURS-DETOUR+HMM | 224 | FIRST_INSTALL_PER_CHUNK | 50 | 0.66667 | 0.012678 | 0.02 | 0.26731 | 31.231 | 13.847 | 49 | 0.33026 |
| phase47c/L2/224/OURS-DETOUR | phase47c | D075 | 0.75 | L2 | OURS-DETOUR | 224 | ALL_INSTALLATIONS | 12 | 0 | 0 | 0.083333 | 0.17822 | 22.982 | 10.036 | 11 | 0.39299 |
| phase47c/L2/224/OURS-DETOUR | phase47c | D075 | 0.75 | L2 | OURS-DETOUR | 224 | FIRST_INSTALL_PER_CHUNK | 12 | 0 | 0 | 0.083333 | 0.17822 | 22.982 | 10.036 | 11 | 0.39299 |
| phase47c/LC/221/NOMAD_RAW | phase47c | D075 | 0.75 | LC | NOMAD_RAW | 221 | ALL_INSTALLATIONS | 39 | 1.4444 | 0.034736 | 0 | 0.19913 | 37.804 | 20.88 | 39 | 0.24735 |
| phase47c/LC/221/NOMAD_RAW | phase47c | D075 | 0.75 | LC | NOMAD_RAW | 221 | FIRST_INSTALL_PER_CHUNK | 39 | 1.4444 | 0.034736 | 0 | 0.19913 | 37.804 | 20.88 | 39 | 0.24735 |
| phase47c/LC/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | LC | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 26 | 0.44444 | 0.015414 | 0.038462 | 0.24139 | 27.767 | 15.171 | 25 | 0.34775 |
| phase47c/LC/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | LC | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 26 | 0.44444 | 0.015414 | 0.038462 | 0.24139 | 27.767 | 15.171 | 25 | 0.34775 |
| phase47c/LC/221/OURS-DETOUR | phase47c | D075 | 0.75 | LC | OURS-DETOUR | 221 | ALL_INSTALLATIONS | 25 | 0.44444 | 0.017204 | 0.04 | 0.25 | 26.762 | 15.023 | 24 | 0.34805 |
| phase47c/LC/221/OURS-DETOUR | phase47c | D075 | 0.75 | LC | OURS-DETOUR | 221 | FIRST_INSTALL_PER_CHUNK | 23 | 0.44444 | 0.017204 | 0.043478 | 0.25 | 28.162 | 16.047 | 22 | 0.34345 |
| phase47c/LC/222/NOMAD_RAW | phase47c | D075 | 0.75 | LC | NOMAD_RAW | 222 | ALL_INSTALLATIONS | 26 | 0 | 0 | 0.076923 | 0.24109 | 24.349 | 11.601 | 24 | 0.38334 |
| phase47c/LC/222/NOMAD_RAW | phase47c | D075 | 0.75 | LC | NOMAD_RAW | 222 | FIRST_INSTALL_PER_CHUNK | 26 | 0 | 0 | 0.076923 | 0.24109 | 24.349 | 11.601 | 24 | 0.38334 |
| phase47c/LC/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | LC | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 27 | 0.33333 | 0.011662 | 0 | 0.27372 | 27.37 | 13.751 | 27 | 0.31206 |
| phase47c/LC/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | LC | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 26 | 0.33333 | 0.011662 | 0 | 0.27775 | 28.081 | 14.166 | 26 | 0.30323 |
| phase47c/LC/222/OURS-DETOUR | phase47c | D075 | 0.75 | LC | OURS-DETOUR | 222 | ALL_INSTALLATIONS | 25 | 0.61111 | 0.023656 | 0 | 0.24879 | 37.944 | 18.073 | 25 | 0.36452 |
| phase47c/LC/222/OURS-DETOUR | phase47c | D075 | 0.75 | LC | OURS-DETOUR | 222 | FIRST_INSTALL_PER_CHUNK | 23 | 0.61111 | 0.023656 | 0 | 0.24879 | 37.354 | 17.794 | 23 | 0.35891 |
| phase47c/LC/223/NOMAD_RAW | phase47c | D075 | 0.75 | LC | NOMAD_RAW | 223 | ALL_INSTALLATIONS | 34 | 5.1111 | 0.14116 | 0.029412 | 0.19852 | 44.367 | 26.533 | 33 | 0.26867 |
| phase47c/LC/223/NOMAD_RAW | phase47c | D075 | 0.75 | LC | NOMAD_RAW | 223 | FIRST_INSTALL_PER_CHUNK | 34 | 5.1111 | 0.14116 | 0.029412 | 0.19852 | 44.367 | 26.533 | 33 | 0.26867 |
| phase47c/LC/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | LC | OURS-DETOUR+HMM | 223 | ALL_INSTALLATIONS | 29 | 0.33333 | 0.011268 | 0 | 0.25841 | 34.823 | 16.519 | 29 | 0.3415 |
| phase47c/LC/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | LC | OURS-DETOUR+HMM | 223 | FIRST_INSTALL_PER_CHUNK | 27 | 0.33333 | 0.011268 | 0 | 0.26267 | 34.014 | 16.426 | 27 | 0.33288 |
| phase47c/LC/223/OURS-DETOUR | phase47c | D075 | 0.75 | LC | OURS-DETOUR | 223 | ALL_INSTALLATIONS | 25 | 0 | 0 | 0 | 0.26357 | 26.492 | 12.275 | 25 | 0.34522 |
| phase47c/LC/223/OURS-DETOUR | phase47c | D075 | 0.75 | LC | OURS-DETOUR | 223 | FIRST_INSTALL_PER_CHUNK | 25 | 0 | 0 | 0 | 0.26357 | 26.492 | 12.275 | 25 | 0.34522 |
| phase47c/LC/224/NOMAD_RAW | phase47c | D075 | 0.75 | LC | NOMAD_RAW | 224 | ALL_INSTALLATIONS | 27 | 0 | 0 | 0.037037 | 0.20753 | 34.656 | 15.385 | 26 | 0.3871 |
| phase47c/LC/224/NOMAD_RAW | phase47c | D075 | 0.75 | LC | NOMAD_RAW | 224 | FIRST_INSTALL_PER_CHUNK | 27 | 0 | 0 | 0.037037 | 0.20753 | 34.656 | 15.385 | 26 | 0.3871 |
| phase47c/LC/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | LC | OURS-DETOUR+HMM | 224 | ALL_INSTALLATIONS | 28 | 0.44444 | 0.015414 | 0.035714 | 0.25325 | 32.172 | 16.504 | 27 | 0.36097 |
| phase47c/LC/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | LC | OURS-DETOUR+HMM | 224 | FIRST_INSTALL_PER_CHUNK | 26 | 0.44444 | 0.015414 | 0.038462 | 0.25325 | 29.309 | 15.626 | 25 | 0.35551 |
| phase47c/LC/224/OURS-DETOUR | phase47c | D075 | 0.75 | LC | OURS-DETOUR | 224 | ALL_INSTALLATIONS | 25 | 0.33333 | 0.012422 | 0 | 0.26198 | 29.302 | 13.954 | 25 | 0.33716 |
| phase47c/LC/224/OURS-DETOUR | phase47c | D075 | 0.75 | LC | OURS-DETOUR | 224 | FIRST_INSTALL_PER_CHUNK | 24 | 0.33333 | 0.012422 | 0 | 0.27355 | 29.432 | 14.123 | 24 | 0.33106 |
| phase47c/SLW/221/NOMAD_RAW | phase47c | D075 | 0.75 | SLW | NOMAD_RAW | 221 | ALL_INSTALLATIONS | 23 | 2.7778 | 0.10753 | 0.13043 | 0.1581 | 42.712 | 30.484 | 20 | 0.34137 |
| phase47c/SLW/221/NOMAD_RAW | phase47c | D075 | 0.75 | SLW | NOMAD_RAW | 221 | FIRST_INSTALL_PER_CHUNK | 23 | 2.7778 | 0.10753 | 0.13043 | 0.1581 | 42.712 | 30.484 | 20 | 0.34137 |
| phase47c/SLW/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | SLW | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 51 | 4.4444 | 0.087864 | 0.11765 | 0.21917 | 46.916 | 27.798 | 45 | 0.29341 |
| phase47c/SLW/221/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | SLW | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 47 | 4.4444 | 0.087864 | 0.085106 | 0.21917 | 47.244 | 28.508 | 43 | 0.26643 |
| phase47c/SLW/221/OURS-DETOUR | phase47c | D075 | 0.75 | SLW | OURS-DETOUR | 221 | ALL_INSTALLATIONS | 10 | 0 | 0 | 0 | 0.24641 | 30.093 | 13.864 | 10 | 0.37764 |
| phase47c/SLW/221/OURS-DETOUR | phase47c | D075 | 0.75 | SLW | OURS-DETOUR | 221 | FIRST_INSTALL_PER_CHUNK | 8 | 0 | 0 | 0 | 0.24641 | 29.999 | 13.902 | 8 | 0.34859 |
| phase47c/SLW/222/NOMAD_RAW | phase47c | D075 | 0.75 | SLW | NOMAD_RAW | 222 | ALL_INSTALLATIONS | 9 | 0 | 0 | 0 | 0.22757 | 15.501 | 6.2297 | 9 | 0.36894 |
| phase47c/SLW/222/NOMAD_RAW | phase47c | D075 | 0.75 | SLW | NOMAD_RAW | 222 | FIRST_INSTALL_PER_CHUNK | 9 | 0 | 0 | 0 | 0.22757 | 15.501 | 6.2297 | 9 | 0.36894 |
| phase47c/SLW/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | SLW | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 92 | 8.8889 | 0.098765 | 0.043478 | 0.22782 | 46.12 | 26.363 | 88 | 0.24315 |
| phase47c/SLW/222/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | SLW | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 84 | 8.8889 | 0.098765 | 0.035714 | 0.23519 | 44.264 | 25.76 | 81 | 0.22348 |
| phase47c/SLW/222/OURS-DETOUR | phase47c | D075 | 0.75 | SLW | OURS-DETOUR | 222 | ALL_INSTALLATIONS | 26 | 1.375 | 0.047711 | 0.11538 | 0.20306 | 39.507 | 20.242 | 23 | 0.32603 |
| phase47c/SLW/222/OURS-DETOUR | phase47c | D075 | 0.75 | SLW | OURS-DETOUR | 222 | FIRST_INSTALL_PER_CHUNK | 23 | 1.375 | 0.047711 | 0.086957 | 0.22707 | 38.192 | 20.569 | 21 | 0.28839 |
| phase47c/SLW/223/NOMAD_RAW | phase47c | D075 | 0.75 | SLW | NOMAD_RAW | 223 | ALL_INSTALLATIONS | 18 | 2 | 0.096064 | 0.16667 | 0.15916 | 44.406 | 40.311 | 15 | 0.31976 |
| phase47c/SLW/223/NOMAD_RAW | phase47c | D075 | 0.75 | SLW | NOMAD_RAW | 223 | FIRST_INSTALL_PER_CHUNK | 18 | 2 | 0.096064 | 0.16667 | 0.15916 | 44.406 | 40.311 | 15 | 0.31976 |
| phase47c/SLW/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | SLW | OURS-DETOUR+HMM | 223 | ALL_INSTALLATIONS | 73 | 9.5556 | 0.10617 | 0.027397 | 0.23502 | 50.865 | 30.807 | 71 | 0.18168 |
| phase47c/SLW/223/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | SLW | OURS-DETOUR+HMM | 223 | FIRST_INSTALL_PER_CHUNK | 68 | 9.5556 | 0.10617 | 0.029412 | 0.23506 | 46.818 | 28.624 | 66 | 0.18825 |
| phase47c/SLW/223/OURS-DETOUR | phase47c | D075 | 0.75 | SLW | OURS-DETOUR | 223 | ALL_INSTALLATIONS | 14 | 1.2222 | 0.072547 | 0.14286 | 0.22651 | 36.927 | 29.876 | 12 | 0.32679 |
| phase47c/SLW/223/OURS-DETOUR | phase47c | D075 | 0.75 | SLW | OURS-DETOUR | 223 | FIRST_INSTALL_PER_CHUNK | 14 | 1.2222 | 0.072547 | 0.14286 | 0.22651 | 36.927 | 29.876 | 12 | 0.32679 |
| phase47c/SLW/224/NOMAD_RAW | phase47c | D075 | 0.75 | SLW | NOMAD_RAW | 224 | ALL_INSTALLATIONS | 8 | 0 | 0 | 0 | 0.22274 | 45.856 | 19.373 | 8 | 0.4282 |
| phase47c/SLW/224/NOMAD_RAW | phase47c | D075 | 0.75 | SLW | NOMAD_RAW | 224 | FIRST_INSTALL_PER_CHUNK | 8 | 0 | 0 | 0 | 0.22274 | 45.856 | 19.373 | 8 | 0.4282 |
| phase47c/SLW/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | SLW | OURS-DETOUR+HMM | 224 | ALL_INSTALLATIONS | 53 | 4.5556 | 0.077432 | 0.056604 | 0.2261 | 45.404 | 27.222 | 50 | 0.22876 |
| phase47c/SLW/224/OURS-DETOUR+HMM | phase47c | D075 | 0.75 | SLW | OURS-DETOUR+HMM | 224 | FIRST_INSTALL_PER_CHUNK | 50 | 4.5556 | 0.077432 | 0.06 | 0.22466 | 45.311 | 27.554 | 47 | 0.22028 |
| phase47c/SLW/224/OURS-DETOUR | phase47c | D075 | 0.75 | SLW | OURS-DETOUR | 224 | ALL_INSTALLATIONS | 80 | 13 | 0.14444 | 0.0375 | 0.17636 | 48.122 | 28.063 | 77 | 0.22277 |
| phase47c/SLW/224/OURS-DETOUR | phase47c | D075 | 0.75 | SLW | OURS-DETOUR | 224 | FIRST_INSTALL_PER_CHUNK | 77 | 13 | 0.14444 | 0.038961 | 0.17704 | 48.85 | 28.476 | 74 | 0.20651 |
| phase51p/H1_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | H1 | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 28 | 1 | 0.016854 | 0.10714 | 0.20184 | 33.285 | 14.614 | 25 | 0.42403 |
| phase51p/H1_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | H1 | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 27 | 1 | 0.016854 | 0.074074 | 0.21014 | 33.285 | 14.766 | 25 | 0.40504 |
| phase51p/H1_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | H1 | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 26 | 2 | 0.042254 | 0.076923 | 0.17414 | 35.214 | 17.085 | 24 | 0.46567 |
| phase51p/H1_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | H1 | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 25 | 2 | 0.042254 | 0.04 | 0.17424 | 35.214 | 17.085 | 24 | 0.4443 |
| phase51p/H1_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | H1 | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 43 | 2.4444 | 0.046267 | 0 | 0.26775 | 40.169 | 20.991 | 43 | 0.27966 |
| phase51p/H1_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | H1 | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 41 | 2.4444 | 0.046267 | 0 | 0.27519 | 41.443 | 21.86 | 41 | 0.26827 |
| phase51p/H1_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | H1 | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 41 | 4.8889 | 0.11481 | 0.04878 | 0.30276 | 31.894 | 15.323 | 39 | 0.26616 |
| phase51p/H1_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | H1 | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 37 | 4.8889 | 0.11481 | 0 | 0.30785 | 31.552 | 16.059 | 37 | 0.22822 |
| phase51p/H2_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | H2 | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 51 | 4 | 0.044444 | 0.078431 | 0.29105 | 44.932 | 25.748 | 47 | 0.23771 |
| phase51p/H2_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | H2 | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 49 | 4 | 0.044444 | 0.061224 | 0.29111 | 44.61 | 26.568 | 46 | 0.21298 |
| phase51p/H2_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | H2 | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 42 | 4 | 0.054545 | 0.047619 | 0.23683 | 36.602 | 16.038 | 40 | 0.38778 |
| phase51p/H2_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | H2 | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 39 | 4 | 0.054545 | 0.025641 | 0.24072 | 36.394 | 16.509 | 38 | 0.35902 |
| phase51p/H2_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | H2 | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 62 | 3.2222 | 0.049132 | 0.016129 | 0.33848 | 41.662 | 22.223 | 61 | 0.18986 |
| phase51p/H2_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | H2 | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 60 | 3.2222 | 0.049132 | 0.016667 | 0.34055 | 40.489 | 21.587 | 59 | 0.18549 |
| phase51p/H2_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | H2 | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 81 | 4.5556 | 0.0537 | 0.012346 | 0.31118 | 39.23 | 20.3 | 80 | 0.16422 |
| phase51p/H2_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | H2 | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 80 | 4.5556 | 0.0537 | 0.0125 | 0.31316 | 38.741 | 20.133 | 79 | 0.15976 |
| phase51p/L2_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | L2 | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 51 | 6 | 0.066667 | 0.019608 | 0.28944 | 42.292 | 23.263 | 50 | 0.22705 |
| phase51p/L2_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | L2 | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 49 | 6 | 0.066667 | 0.020408 | 0.28996 | 43.694 | 24.127 | 48 | 0.21603 |
| phase51p/L2_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | L2 | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 54 | 7.3333 | 0.081481 | 0.092593 | 0.29581 | 50.515 | 26.293 | 49 | 0.26325 |
| phase51p/L2_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | L2 | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 50 | 7.3333 | 0.081481 | 0.06 | 0.30072 | 49.766 | 26.295 | 47 | 0.23158 |
| phase51p/L2_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | L2 | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 76 | 1.8889 | 0.024037 | 0.013158 | 0.30911 | 38.043 | 21.01 | 75 | 0.16476 |
| phase51p/L2_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | L2 | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 75 | 1.8889 | 0.024037 | 0.013333 | 0.31067 | 37.579 | 20.959 | 74 | 0.16539 |
| phase51p/L2_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | L2 | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 63 | 3.1111 | 0.04893 | 0.015873 | 0.32556 | 38.807 | 21.23 | 62 | 0.15393 |
| phase51p/L2_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | L2 | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 61 | 3.1111 | 0.04893 | 0.016393 | 0.3288 | 36.145 | 19.96 | 60 | 0.15195 |
| phase51p/LC_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | LC | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 38 | 4 | 0.06053 | 0.052632 | 0.21819 | 54.426 | 32.326 | 36 | 0.33037 |
| phase51p/LC_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | LC | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 36 | 4 | 0.06053 | 0.055556 | 0.21819 | 51.931 | 32.124 | 34 | 0.31739 |
| phase51p/LC_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | LC | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 31 | 3 | 0.057325 | 0.096774 | 0.18379 | 37.081 | 17.003 | 28 | 0.43446 |
| phase51p/LC_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | LC | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 28 | 3 | 0.057325 | 0 | 0.2026 | 37.081 | 17.003 | 28 | 0.37386 |
| phase51p/LC_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | LC | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 27 | 0 | 0 | 0.037037 | 0.23435 | 30.375 | 16.787 | 26 | 0.36475 |
| phase51p/LC_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | LC | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 26 | 0 | 0 | 0.038462 | 0.23883 | 30.381 | 16.932 | 25 | 0.36086 |
| phase51p/LC_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | LC | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 27 | 0.33333 | 0.011765 | 0 | 0.26809 | 28.734 | 14.326 | 27 | 0.30938 |
| phase51p/LC_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | LC | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 26 | 0.33333 | 0.011765 | 0 | 0.27391 | 27.866 | 14.077 | 26 | 0.30486 |
| phase51p/SLW_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | SLW | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 53 | 11 | 0.12222 | 0.16981 | 0.18421 | 58.978 | 34.659 | 44 | 0.23867 |
| phase51p/SLW_L150/221/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | SLW | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 46 | 11 | 0.12222 | 0.1087 | 0.19432 | 57.956 | 34.22 | 41 | 0.18134 |
| phase51p/SLW_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | SLW | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 51 | 7 | 0.077778 | 0.13725 | 0.17833 | 45.202 | 24.886 | 44 | 0.34768 |
| phase51p/SLW_L150/222/OURS-DETOUR+HMM | phase51p | L150 | 1.5 | SLW | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 43 | 7 | 0.077778 | 0.069767 | 0.19976 | 42.752 | 23.107 | 40 | 0.29488 |
| phase51p/SLW_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | SLW | OURS-DETOUR+HMM | 221 | ALL_INSTALLATIONS | 48 | 4.6667 | 0.090032 | 0.020833 | 0.22769 | 45.655 | 26.954 | 47 | 0.22152 |
| phase51p/SLW_WIDE/221/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | SLW | OURS-DETOUR+HMM | 221 | FIRST_INSTALL_PER_CHUNK | 46 | 4.6667 | 0.090032 | 0.021739 | 0.22769 | 45.426 | 27.325 | 45 | 0.20906 |
| phase51p/SLW_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | SLW | OURS-DETOUR+HMM | 222 | ALL_INSTALLATIONS | 60 | 5.5556 | 0.097324 | 0.066667 | 0.21243 | 49.479 | 28.562 | 56 | 0.25711 |
| phase51p/SLW_WIDE/222/OURS-DETOUR+HMM | phase51p | WIDE | 0.75 | SLW | OURS-DETOUR+HMM | 222 | FIRST_INSTALL_PER_CHUNK | 55 | 5.5556 | 0.097324 | 0.054545 | 0.21862 | 48.325 | 28.317 | 52 | 0.22215 |
| phase52p/H1_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | H1 | CUT-HOLD | 221 | ALL_INSTALLATIONS | 23 | 0.33333 | 0.011976 | 0 | 0.26496 | 41.956 | 21.144 | 23 | 0.31228 |
| phase52p/H1_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | H1 | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 23 | 0.33333 | 0.011976 | 0 | 0.26496 | 41.956 | 21.144 | 23 | 0.31228 |
| phase52p/H1_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | H1 | GRAPH-REC | 221 | ALL_INSTALLATIONS | 31 | 0.22222 | 0.0069778 | 0.032258 | 0.26105 | 37.316 | 19.546 | 30 | 0.3342 |
| phase52p/H1_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | H1 | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 28 | 0.22222 | 0.0069778 | 0.035714 | 0.25584 | 38.746 | 20.713 | 27 | 0.34136 |
| phase52p/H1_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | H1 | CUT-HOLD | 222 | ALL_INSTALLATIONS | 30 | 0.33333 | 0.011976 | 0.033333 | 0.2405 | 33.035 | 19.099 | 29 | 0.36143 |
| phase52p/H1_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | H1 | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 25 | 0.33333 | 0.011976 | 0.04 | 0.24918 | 35.143 | 20.379 | 24 | 0.35564 |
| phase52p/H1_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | H1 | GRAPH-REC | 222 | ALL_INSTALLATIONS | 34 | 0.33333 | 0.011152 | 0.029412 | 0.26013 | 22.231 | 11.115 | 33 | 0.35008 |
| phase52p/H1_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | H1 | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 27 | 0.33333 | 0.011152 | 0 | 0.25566 | 24.539 | 12.055 | 27 | 0.32004 |
| phase52p/H1_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | H1 | CUT-HOLD | 221 | ALL_INSTALLATIONS | 31 | 16.556 | 0.27786 | 0.19355 | 0.17614 | 60.862 | 33.824 | 25 | 0.39291 |
| phase52p/H1_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | H1 | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 29 | 16.556 | 0.27786 | 0.13793 | 0.19905 | 60.862 | 33.824 | 25 | 0.35104 |
| phase52p/H1_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | H1 | GRAPH-REC | 221 | ALL_INSTALLATIONS | 30 | 3.3333 | 0.075997 | 0.23333 | 0.26515 | 47.89 | 24.747 | 23 | 0.44756 |
| phase52p/H1_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | H1 | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 22 | 3.3333 | 0.075997 | 0.22727 | 0.25202 | 54.454 | 28.442 | 17 | 0.45594 |
| phase52p/H1_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | H1 | CUT-HOLD | 222 | ALL_INSTALLATIONS | 20 | 4.75 | 0.14358 | 0.3 | 0.12276 | 48.162 | 22.608 | 14 | 0.57 |
| phase52p/H1_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | H1 | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 17 | 4.75 | 0.14358 | 0.17647 | 0.17533 | 48.162 | 22.608 | 14 | 0.49412 |
| phase52p/H1_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | H1 | GRAPH-REC | 222 | ALL_INSTALLATIONS | 33 | 11.778 | 0.25949 | 0.060606 | 0.26912 | 74.215 | 44.298 | 31 | 0.23735 |
| phase52p/H1_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | H1 | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 24 | 11.778 | 0.25949 | 0.041667 | 0.25834 | 78.539 | 46.351 | 23 | 0.26917 |
| phase52p/H2_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | H2 | CUT-HOLD | 221 | ALL_INSTALLATIONS | 89 | 3.4444 | 0.038272 | 0.022472 | 0.28774 | 36.172 | 19.552 | 87 | 0.20166 |
| phase52p/H2_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | H2 | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 88 | 3.4444 | 0.038272 | 0.022727 | 0.2872 | 36.142 | 19.49 | 86 | 0.20267 |
| phase52p/H2_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | H2 | GRAPH-REC | 221 | ALL_INSTALLATIONS | 109 | 2.7778 | 0.030864 | 0.018349 | 0.29783 | 33.917 | 16.887 | 107 | 0.25653 |
| phase52p/H2_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | H2 | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 88 | 2.7778 | 0.030864 | 0.011364 | 0.29809 | 36.296 | 18.019 | 87 | 0.25643 |
| phase52p/H2_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | H2 | CUT-HOLD | 222 | ALL_INSTALLATIONS | 42 | 1.7778 | 0.0401 | 0.02381 | 0.28352 | 31.928 | 15.966 | 41 | 0.30643 |
| phase52p/H2_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | H2 | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 41 | 1.7778 | 0.0401 | 0.02439 | 0.28027 | 31.487 | 15.831 | 40 | 0.30494 |
| phase52p/H2_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | H2 | GRAPH-REC | 222 | ALL_INSTALLATIONS | 130 | 3.6667 | 0.040741 | 0.0076923 | 0.29099 | 38.447 | 19.246 | 129 | 0.21907 |
| phase52p/H2_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | H2 | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 88 | 3.6667 | 0.040741 | 0.011364 | 0.3095 | 41.097 | 21.925 | 87 | 0.1947 |
| phase52p/H2_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | H2 | CUT-HOLD | 221 | ALL_INSTALLATIONS | 50 | 23 | 0.25556 | 0.08 | 0.26752 | 63.861 | 39.853 | 46 | 0.26762 |
| phase52p/H2_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | H2 | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 48 | 23 | 0.25556 | 0.0625 | 0.27572 | 62.303 | 37.348 | 45 | 0.2513 |
| phase52p/H2_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | H2 | GRAPH-REC | 221 | ALL_INSTALLATIONS | 65 | 36.222 | 0.40247 | 0.076923 | 0.28957 | 68.48 | 40.492 | 60 | 0.21369 |
| phase52p/H2_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | H2 | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 46 | 36.222 | 0.40247 | 0.086957 | 0.28877 | 75.516 | 46.21 | 42 | 0.20874 |
| phase52p/H2_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | H2 | CUT-HOLD | 222 | ALL_INSTALLATIONS | 47 | 21 | 0.26141 | 0.17021 | 0.22215 | 67.831 | 39.905 | 39 | 0.36196 |
| phase52p/H2_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | H2 | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 42 | 21 | 0.26141 | 0.14286 | 0.22963 | 64.563 | 38.906 | 36 | 0.35225 |
| phase52p/H2_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | H2 | GRAPH-REC | 222 | ALL_INSTALLATIONS | 74 | 19.667 | 0.21852 | 0.10811 | 0.28829 | 68.022 | 36.305 | 66 | 0.27651 |
| phase52p/H2_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | H2 | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 48 | 19.667 | 0.21852 | 0.125 | 0.28354 | 74.227 | 39.365 | 42 | 0.28912 |
| phase52p/L2_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | L2 | CUT-HOLD | 221 | ALL_INSTALLATIONS | 34 | 0.66667 | 0.017621 | 0.029412 | 0.23807 | 34.169 | 14.913 | 33 | 0.40171 |
| phase52p/L2_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | L2 | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 34 | 0.66667 | 0.017621 | 0.029412 | 0.23807 | 34.169 | 14.913 | 33 | 0.40171 |
| phase52p/L2_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | L2 | GRAPH-REC | 221 | ALL_INSTALLATIONS | 18 | 0.66667 | 0.035036 | 0.11111 | 0.19508 | 30.731 | 13.294 | 16 | 0.40639 |
| phase52p/L2_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | L2 | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 15 | 0.66667 | 0.035036 | 0.066667 | 0.17142 | 31.464 | 14.252 | 14 | 0.40545 |
| phase52p/L2_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | L2 | CUT-HOLD | 222 | ALL_INSTALLATIONS | 92 | 6.3333 | 0.07037 | 0.032609 | 0.29583 | 43.783 | 24.663 | 89 | 0.1768 |
| phase52p/L2_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | L2 | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 87 | 6.3333 | 0.07037 | 0.022989 | 0.30092 | 41.05 | 22.622 | 85 | 0.16583 |
| phase52p/L2_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | L2 | GRAPH-REC | 222 | ALL_INSTALLATIONS | 77 | 7.5556 | 0.11829 | 0.038961 | 0.2689 | 43.744 | 23.476 | 74 | 0.19686 |
| phase52p/L2_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | L2 | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 58 | 7.5556 | 0.11829 | 0.034483 | 0.25901 | 47.728 | 25.761 | 56 | 0.18066 |
| phase52p/L2_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | L2 | CUT-HOLD | 221 | ALL_INSTALLATIONS | 15 | 5.3333 | 0.059259 | 0.2 | 0.17138 | 49.905 | 28.291 | 12 | 0.39381 |
| phase52p/L2_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | L2 | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 15 | 5.3333 | 0.059259 | 0.2 | 0.17138 | 49.905 | 28.291 | 12 | 0.39381 |
| phase52p/L2_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | L2 | GRAPH-REC | 221 | ALL_INSTALLATIONS | 33 | 8.3333 | 0.15831 | 0.24242 | 0.19174 | 52.178 | 28.19 | 25 | 0.49247 |
| phase52p/L2_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | L2 | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 28 | 8.3333 | 0.15831 | 0.25 | 0.14648 | 55.174 | 29.973 | 21 | 0.5242 |
| phase52p/L2_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | L2 | CUT-HOLD | 222 | ALL_INSTALLATIONS | 50 | 20.333 | 0.22761 | 0.1 | 0.25563 | 73.738 | 39.992 | 45 | 0.34317 |
| phase52p/L2_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | L2 | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 48 | 20.333 | 0.22761 | 0.10417 | 0.25651 | 73.107 | 40.143 | 43 | 0.34068 |
| phase52p/L2_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | L2 | GRAPH-REC | 222 | ALL_INSTALLATIONS | 75 | 19.667 | 0.21852 | 0.08 | 0.30254 | 67.464 | 37.378 | 69 | 0.2367 |
| phase52p/L2_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | L2 | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 50 | 19.667 | 0.21852 | 0.08 | 0.30304 | 75.972 | 44.137 | 46 | 0.23909 |
| phase52p/LC_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | LC | CUT-HOLD | 221 | ALL_INSTALLATIONS | 27 | 0.22222 | 0.007913 | 0.037037 | 0.21552 | 26.422 | 11.519 | 26 | 0.40778 |
| phase52p/LC_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | LC | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 26 | 0.22222 | 0.007913 | 0 | 0.21707 | 26.422 | 11.519 | 26 | 0.385 |
| phase52p/LC_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | LC | GRAPH-REC | 221 | ALL_INSTALLATIONS | 69 | 3.7778 | 0.064196 | 0 | 0.27152 | 38.774 | 20.156 | 69 | 0.21191 |
| phase52p/LC_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | LC | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 56 | 3.7778 | 0.064196 | 0 | 0.26231 | 39.272 | 21.03 | 56 | 0.22095 |
| phase52p/LC_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | LC | CUT-HOLD | 222 | ALL_INSTALLATIONS | 30 | 0.88889 | 0.028829 | 0 | 0.26853 | 35.822 | 18.459 | 30 | 0.28186 |
| phase52p/LC_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | LC | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 28 | 0.88889 | 0.028829 | 0 | 0.26853 | 33.472 | 17.853 | 28 | 0.27201 |
| phase52p/LC_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | LC | GRAPH-REC | 222 | ALL_INSTALLATIONS | 30 | 0.33333 | 0.011538 | 0.033333 | 0.25325 | 33.254 | 15.613 | 29 | 0.34317 |
| phase52p/LC_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | LC | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 26 | 0.33333 | 0.011538 | 0.038462 | 0.25045 | 32.604 | 15.549 | 25 | 0.33915 |
| phase52p/LC_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | LC | CUT-HOLD | 221 | ALL_INSTALLATIONS | 20 | 3.5556 | 0.10135 | 0.3 | 0.16595 | 54.896 | 24.531 | 14 | 0.54715 |
| phase52p/LC_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | LC | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 18 | 3.5556 | 0.10135 | 0.22222 | 0.21807 | 54.896 | 24.531 | 14 | 0.49683 |
| phase52p/LC_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | LC | GRAPH-REC | 221 | ALL_INSTALLATIONS | 31 | 4.4444 | 0.10558 | 0.19355 | 0.24744 | 38.874 | 26.548 | 25 | 0.47385 |
| phase52p/LC_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | LC | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 22 | 4.4444 | 0.10558 | 0.18182 | 0.17059 | 44.778 | 31.472 | 18 | 0.47755 |
| phase52p/LC_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | LC | CUT-HOLD | 222 | ALL_INSTALLATIONS | 47 | 21.306 | 0.25041 | 0.085106 | 0.30861 | 68.263 | 44 | 43 | 0.23968 |
| phase52p/LC_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | LC | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 47 | 21.306 | 0.25041 | 0.085106 | 0.30861 | 68.263 | 44 | 43 | 0.23968 |
| phase52p/LC_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | LC | GRAPH-REC | 222 | ALL_INSTALLATIONS | 23 | 5.7778 | 0.16462 | 0.13043 | 0.21135 | 47.763 | 32.79 | 20 | 0.40744 |
| phase52p/LC_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | LC | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 18 | 5.7778 | 0.16462 | 0.11111 | 0.17623 | 55.113 | 38.448 | 16 | 0.42256 |
| phase52p/SLW_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | SLW | CUT-HOLD | 221 | ALL_INSTALLATIONS | 87 | 12.667 | 0.14074 | 0.08046 | 0.22918 | 50.704 | 27.79 | 80 | 0.24075 |
| phase52p/SLW_D075/221/CUT-HOLD | phase52p | D075 | 0.75 | SLW | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 78 | 12.667 | 0.14074 | 0.051282 | 0.23011 | 49.48 | 27.046 | 74 | 0.21435 |
| phase52p/SLW_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | SLW | GRAPH-REC | 221 | ALL_INSTALLATIONS | 76 | 6.875 | 0.10436 | 0.052632 | 0.23223 | 43.071 | 23.749 | 72 | 0.2258 |
| phase52p/SLW_D075/221/GRAPH-REC | phase52p | D075 | 0.75 | SLW | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 60 | 6.875 | 0.10436 | 0.033333 | 0.20455 | 45.833 | 25.124 | 58 | 0.21525 |
| phase52p/SLW_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | SLW | CUT-HOLD | 222 | ALL_INSTALLATIONS | 86 | 16.111 | 0.17901 | 0.05814 | 0.21803 | 48.141 | 27.512 | 81 | 0.23196 |
| phase52p/SLW_D075/222/CUT-HOLD | phase52p | D075 | 0.75 | SLW | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 79 | 16.111 | 0.17901 | 0.063291 | 0.21843 | 44.636 | 25.955 | 74 | 0.22204 |
| phase52p/SLW_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | SLW | GRAPH-REC | 222 | ALL_INSTALLATIONS | 104 | 3.7778 | 0.041975 | 0.067308 | 0.24363 | 41.065 | 21.667 | 97 | 0.24694 |
| phase52p/SLW_D075/222/GRAPH-REC | phase52p | D075 | 0.75 | SLW | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 79 | 3.7778 | 0.041975 | 0.050633 | 0.22006 | 40.691 | 22.417 | 75 | 0.2269 |
| phase52p/SLW_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | SLW | CUT-HOLD | 221 | ALL_INSTALLATIONS | 53 | 16.556 | 0.18395 | 0.20755 | 0.18937 | 59.265 | 33.98 | 42 | 0.36456 |
| phase52p/SLW_D150/221/CUT-HOLD | phase52p | D150 | 1.5 | SLW | CUT-HOLD | 221 | FIRST_INSTALL_PER_CHUNK | 46 | 16.556 | 0.18395 | 0.15217 | 0.20089 | 56.988 | 33.928 | 39 | 0.3102 |
| phase52p/SLW_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | SLW | GRAPH-REC | 221 | ALL_INSTALLATIONS | 48 | 14.333 | 0.21594 | 0.22917 | 0.20235 | 59.693 | 36.244 | 37 | 0.33707 |
| phase52p/SLW_D150/221/GRAPH-REC | phase52p | D150 | 1.5 | SLW | GRAPH-REC | 221 | FIRST_INSTALL_PER_CHUNK | 35 | 14.333 | 0.21594 | 0.22857 | 0.19177 | 62.668 | 37.214 | 27 | 0.3394 |
| phase52p/SLW_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | SLW | CUT-HOLD | 222 | ALL_INSTALLATIONS | 57 | 17.778 | 0.19753 | 0.22807 | 0.16153 | 63.237 | 38.606 | 44 | 0.38026 |
| phase52p/SLW_D150/222/CUT-HOLD | phase52p | D150 | 1.5 | SLW | CUT-HOLD | 222 | FIRST_INSTALL_PER_CHUNK | 49 | 17.778 | 0.19753 | 0.16327 | 0.16509 | 60.48 | 39.155 | 41 | 0.32208 |
| phase52p/SLW_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | SLW | GRAPH-REC | 222 | ALL_INSTALLATIONS | 54 | 14.333 | 0.1902 | 0.14815 | 0.25428 | 67.497 | 40.867 | 46 | 0.31713 |
| phase52p/SLW_D150/222/GRAPH-REC | phase52p | D150 | 1.5 | SLW | GRAPH-REC | 222 | FIRST_INSTALL_PER_CHUNK | 41 | 14.333 | 0.1902 | 0.14634 | 0.18426 | 67.869 | 42.948 | 35 | 0.31748 |

전체 적용 시점: [applications.csv](../research/results/phase52ec/chunks/applications.csv). 방법·장면별 상세 표: [summary.csv](../research/results/phase52ec/chunks/summary.csv).
