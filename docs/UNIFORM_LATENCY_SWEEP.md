# Full-run uniform latency sweep

2026-10-17. **전달 지연 구현 및 real-time 비동기 검증 PASS, 새 3개 주행은 모두 goal 실패. Qualified reconciliation candidate는 0개이나, 지연 조건의 유효 correspondence가 부족해 Graph 필요성 판정은 `INSUFFICIENT_EVIDENCE`다.** D0만 기존 `NO_QUALIFIED_CANDIDATE`를 유지한다.

기준 `6eedeebf29482a9ada617a3ad774521983d2a8a7`, branch `research/isaac6-uniform-latency`. [사전 protocol](UNIFORM_LATENCY_PROTOCOL.md)은 `3f55d28`, 세 실제 실행의 clean source는 `25bed71995c406be270441854bd1c4a7c32af394`. D250→D500→D750 각 1회, 재시도 0회, 모두 process exit 0. D0는 `async_wide_wall_01`(실행 SHA `fb9bf2253044be477873aa113a19899f479af248`)을 재사용했다.

## 변경 및 검증 범위

`UniformDeliveryDelay`가 기존 IPC monotonic hold를 재사용한다. 모든 accepted result에 `release = packet_received + d` deadline을 적용하며 GPU inference와 완전한 packet 수신 이후 IPC thread만 기다린다. 실제 release에는 OS wakeup 오차가 더해진다. 최초 결과 및 종료 후 drain된 미적용 결과도 포함한다. 기존 single-trigger class, execution core, 1초 timeout, 9 Hz PD 수식, 72 Hz integration, model/checkpoint/native inference/좌표/clearance는 그대로다. FRESH의 controller-side receive는 release이며 pending FRESH가 OLD의 validity를 갱신하지 않는다.

고정 scene은 `two_obstacles_wide_wall_scenario.json`: 장애물 `(1.5,0)/(.4,.5,.8)` 및 `(3,.75)/(.5,1.5,1)`, start `(0,0,0)`, goal `(4.5,0,0)`, goal tolerance .30 m, radius .09 m. 장애물 clearance >=.02 m와 corridor containment >0을 구분한다. Sample 0/index 2, 10 diffusion steps, seed `101+2*request_id`, 4 Hz RGB history를 유지했다. Fixed-goal adapter이며 Topomap은 없다.

실행 환경은 기존 Isaac Sim `6.0.1-rc.7+release.42383.32955d8d.gl`, RTX 5060 Ti/driver 595.99.02, 별도 Python 3.11.16 worker, PyTorch 2.7.0+cu128/torchvision 0.22.0+cu128/Diffusers 0.11.1. Checkpoint SHA-256 `70f79b8262527e20e56ced64a3e3d7ef91855bc9e7c3fa348d78edcb83c6a333`, coverage 100%/645 state tensors. 설치·환경 변경 없음. Startup renderer-step 오류는 navigation 이전 RGB gate를 통과한 뒤 주행한 것으로, shader 준비 시간과 아래 navigation clock을 구분했다.

실행 전 synthetic/기존 runtime·geometry tests **30 passed (0.09 s)**. 실행 후 기존 `async_report.validate`로 모든 raw/derived, normalization/cumsum/scaling, 원본 controller, pose integration, clocks, next-tick switch, obstacle swept clearance를 검증했다. Uniform analyzer는 corridor 전체 intervals, 모든 packet/deadline/release, 과거 commit의 source hash 및 scenario/checkpoint를 추가 검사했다. 별도 raw-log 대조도 통과했다. 최초 적용 전 정지, single outstanding, 최신 4-frame history, busy skip 집계, seed schedule 및 유효 OLD의 GPU/hold 중 이동을 확인했다. Pose integration 오차 0, switch tick mismatch 0. 기존 431개 입력 및 새 run 분석 입력 251개 hash 보존. [검증 기록](../research/results/isaac6_uniform_latency_20261017/review.json).

## Navigation 결과

| 조건 | Goal / 종료 원인 | 종료 sim s | 최소 goal m | 장애물 1 / 2 최소 swept clearance m | 최소 corridor clearance m |
|---|---|---:|---:|---:|---:|
| D0 참고 | 도달 | 24.5833 | .29771 | .06963 / .08284 | .79039 |
| D250 | 실패 / corridor footprint 침범 | 23.1806 | 2.47177 | .10492 / .64817 | −.000153 |
| D500 | 실패 / corridor footprint 침범 | 17.3056 | 2.62027 | .48827 / .37539 | −.000521 |
| D750 | 실패 / corridor footprint 침범 | 18.3194 | 2.43429 | .51405 / .14422 | −.000179 |

새 3개 run 모두 첫 장애물을 왼쪽으로 통과했지만 두 번째 장애물 통과 전에 복도 밖으로 나갔다. **장애물과 geometric overlap은 0회, 장애물 2 cm margin 위반도 0회다.** Corridor footprint 침범을 검출한 첫 72 Hz interval에서 중단했다. 이는 실제 kinematic pose의 기하학적 실패이며 PhysX 충돌 판정이 아니다. D0는 첫 왼쪽/둘째 오른쪽 통과 및 corridor containment를 만족했다.

## Timing 및 OLD 실행

아래 시간은 host monotonic의 차이며 단위 ms, 각 셀은 median / p95. GPU 열은 최초 cold inference 제외, observation 시간은 render 시작을 포함한다. Observation→ready/release는 모든 수신 결과, →switch는 실제 적용된 결과(초기 적용 포함)만 사용했다. D0 packet/release는 기존 received clock의 alias로 별도 hold 계측이 없다.

| 조건 | 실제 packet→release | Warm GPU | Observation→ready | →release | →switch |
|---|---:|---:|---:|---:|---:|
| D0 | 0 / 0 (추가 지연 없음) | 29.187 / 31.903 | 67.489 / 127.727 | 69.632 / 129.625 | 138.283 / 176.113 |
| D250 | 250.075 / 250.098 | 30.129 / 31.938 | 69.356 / 131.483 | 321.668 / 383.687 | 415.721 / 460.539 |
| D500 | 500.074 / 500.088 | 30.544 / 32.188 | 69.029 / 134.370 | 571.474 / 636.440 | 638.081 / 694.091 |
| D750 | 750.072 / 750.101 | 30.150 / 33.486 | 70.881 / 212.680 | 823.011 / 967.402 | 916.141 / 1049.811 |

설정 delay 대비 maximum deadline overshoot는 D250 .103 ms, D500 .190 ms, D750 .105 ms. **45/45, 23/23, 18/18 accepted results 모두 지연 적용을 확인했다.** Render median/p95는 각각 36.65/41.84, 36.61/97.60, 37.28/98.55 ms로 GPU inference 및 전달 지연과 분리했다.

| 조건 | Request / receive / switch | Busy skip / missed capture | Timeout episodes / zero ticks | Pacing 절대 오차 p95 / max ms | RTF |
|---|---:|---:|---:|---:|---:|
| D0 | 95 / 95 / 94 | 1 / 0 | 0 / 0 | .155 / 1.199 | .99999589 |
| D250 | 45 / 45 / 45 | 45 / 0 | 0 / 0 | .154 / 1.574 | .99999424 |
| D500 | 23 / 23 / 22 | 44 / 0 | 0 / 0 | .152 / 1.446 | .99999605 |
| D750 | 18 / 18 / 17 | 53 / 0 | 2 / 2 | .155 / 1.489 | .99999527 |

모든 조건이 기존 soft real-time 기준을 통과했고 한 integration tick 이상 늦은 pose는 없었다. Inference clock mapping 최대 오차는 D0/.250/.500/.750 순서 .274/.585/.047/.462 ms. D750 timeout은 t_sim 3.6667 s(ID 1, age 1.032653 s), 12.6667 s(ID 10, age 1.096471 s)에서 원본처럼 `(v,w)=(0,0)`을 출력했다. 각 다음 8개 integration intervals에서 pose 정지도 확인했다. 다른 조건의 자연 timeout은 발생하지 않았으며 synthetic exact-timeout 검증만 PASS다.

다음은 **초기 적용과 미적용 result를 제외한 실제 handoff**의 observation snapshot→switch 측정, median / p95 / max다. OLD 이동은 valid command의 적분 길이, yaw는 signed 변화의 절댓값이다. World prediction은 항상 각 observation pose에 고정하며 B로 re-anchor하지 않는다.

| 조건 | OLD 이동 m | OLD yaw 변화 ° | B−observation XY 거리 m (median / max) | 원본 PD local point와 anchored selected point의 world 차이 m (median / max) |
|---|---:|---:|---:|---:|
| D0 | .02778 / .03611 / .04444 | 1.15 / 3.84 / 5.09 | .02777 / .04444 | .02774 / .04492 |
| D250 | .08056 / .08611 / .09444 | 8.28 / 9.55 / 10.82 | .08048 / .09444 | .07792 / .09716 |
| D500 | .12500 / .13889 / .13889 | 12.09 / 15.60 / 15.92 | .12489 / .13887 | .12570 / .15029 |
| D750 | .18333 / .18611 / .18611 | 20.69 / 21.33 / 21.33 | .18231 / .18504 | .18344 / .20234 |

Packet→release 안에 완전히 포함된 valid OLD intervals의 이동 median은 .04722/.09722/.14722 m. GPU window의 실제 OLD 이동도 각각 최대 .00556 m를 확인했다. 이 두 통계는 초기 적용 제외, terminal-unapplied는 주행 종료까지의 관측치로 포함한다. 종료 후 packet drain을 추가 로봇 움직임으로 계산하지 않았다.

## Handoff geometry

기존 common-forward-station correspondence, 최소 overlap .10 m, tangent segment .02 m, entry index<=2, consistent 거리 .10 m/각도 30°, safety 기준을 그대로 적용했다. Waypoint index 동일성을 물리적 대응으로 가정하지 않는다. NoMaD에 native yaw/timestamp를 부여하지 않았다. 아래 RMSE/RMS는 **유효 correspondence만**, median / p95 / max다.

| 조건 | 실제 handoff / 유효 correspondence | Position RMSE m | Tangent heading RMS ° | Lateral RMS m | Longitudinal RMS m |
|---|---:|---:|---:|---:|---:|
| D0 | 93 / 87 | .01356 / .04510 / .05745 | 6.62 / 19.78 / 22.38 | .01350 / .04343 / .05385 | .00144 / .01290 / .02106 |
| D250 | 44 / 24 | .03526 / .08132 / .08503 | 12.20 / 38.25 / 38.58 | .03434 / .06827 / .07784 | .00510 / .04101 / .04535 |
| D500 | 21 / 4 | .05486 / .09791 / .10022 | 13.91 / 31.59 / 33.77 | .05057 / .08788 / .08971 | .02117 / .04313 / .04467 |
| D750 | 16 / 1 | .04670 / .04670 / .04670 | 17.07 / 17.07 / 17.07 | .04639 / .04639 / .04639 | .00542 / .00542 / .00542 |

유효 entry가 존재하는 pair는 93/40/16/13개. **모두 검사한 connector 중 적어도 하나가 안전했다.** Nearest entry 거리 median/max는 D0 .02947/.04866, D250 .00606/.03317, D500 .01293/.07550, D750 .05346/.12862 m. Boundary yaw→entry tangent 차이 median/max는 1.50/16.48°, 4.82/41.42°, 14.20/38.78°, 21.69/52.84°. Entry로 향하는 connector bearing 차이 median은 3.37/93.75/104.20/139.76°였다. 뒤쪽에 남은 entry로 회전 후 직선 연결이 가능해도 원본 PD가 그 staging을 실행했다는 뜻은 아니다. Connector obstacle clearance 최솟값은 .07165/.10615/.49054/.47702 m.

| 조건 | ALREADY_CONSISTENT | STAGING_SUFFICIENT | UNSAFE_FRESH | OLD_EXECUTION_RISK (적용 pair) | POTENTIAL_RECONCILIATION_CASE | INSUFFICIENT_EVIDENCE | 미적용 pending OLD risk |
|---|---:|---:|---:|---:|---:|---:|---|
| D0 | 85 | 1 | 1 | 0 | 0 | 6 | 없음 (미적용 94) |
| D250 | 0 | 24 | 2 | 0 | 0 | 18 | 없음 |
| D500 | 0 | 4 | 0 | 0 | 0 | 17 | ID 22: 1개 |
| D750 | 0 | 1 | 0 | 0 | 0 | 15 | ID 17: 1개 |

비단조 forward station으로 무효가 된 pair는 D250 20개, D500 12개, D750 8개이며, overlap 부족은 D500 5개/D750 7개다. D250의 직접 unsafe FRESH 2개는 correspondence 없이도 footprint geometry로 판정했다. Classifiable 비율은 93.55/59.09/19.05/6.25%. 기존 negative verdict 기준 90% 때문에 지연 3조건은 `INSUFFICIENT_EVIDENCE`이며 **0 candidates를 전체 안전성 또는 Graph 불필요의 증명으로 해석하지 않는다.**

## 실제 failure와 prediction 위험

[Incident JSON](../research/results/isaac6_uniform_latency_20261017/incidents.json)에 해당 OLD/FRESH, observation/B pose, full/prefix clearance, 실제 interval와 controller row를 보존했다. 아래 좌표는 실제 footprint 침범을 검출한 interval의 끝 pose, command는 그 interval에 사용된 값이다.

| 조건 | 마지막 적용 OLD→FRESH | 실패 sim s / pose (x,y,yaw rad) | 실제 (v m/s, w rad/s) | 종료 당시 pending |
|---|---|---|---|---|
| D250 | 43→44 | 23.18056 / (1.77414, −1.41015, −.59872) | (.181961, +.4) | 없음 |
| D500 | 20→21 | 17.30556 / (2.28461, 1.41052, 1.27277) | (.101388, +.4) | 22, GPU inference 중 |
| D750 | 15→16 | 18.31944 / (2.51578, 1.41018, .10865) | (.187765, −.4) | 17, post-inference delivery hold 중 |

- **D250 FRESH 23/28:** native full obstacle clearance −.01447/−.01655 m로 tail unsafe. Index 2까지 prefix는 .11300/.21756 m, 실제 다음 switch까지 실행은 .10615/.22233 m로 안전했다. Full 8-point 위험을 실제 충돌로 계산하지 않는다.
- **마지막 적용 FRESH 44/21/16:** observation-anchored full과 prefix는 기존 기준상 안전했지만 실제 PD 실행은 corridor를 침범했다. Full obstacle clearance는 .92106/.38380/.21372 m, corridor clearance .02761/.00889/.03352 m. 세 pair 모두 nonmonotone correspondence이며 index 2까지 유효한 .02 m heading segment가 없어 entry 판정도 불가했다. Safe prediction과 실제 실행 실패의 차이는 확인됐으나 단순 staging이 불가능하다는 증거는 없어 candidate로 승격하지 않는다.
- **D500 pending FRESH 22:** 실제 OLD 21이 GPU inference 도중 경계를 침범했다. 동일 host epoch에서 inference 17.29227→17.32130 s, physical packet 17.33122 s, release 17.83130 s. 종료가 packet보다 앞서므로 이 마지막 실패를 ID 22의 post-inference hold 탓으로 주장하지 않는다. 미적용 FRESH 자체도 full/prefix corridor clearance −.07144/−.05678 m로 unsafe다.
- **D750 pending FRESH 17:** physical packet 17.84867 s, release 18.59874 s 사이에 실제 OLD 16이 경계를 침범했다. 주행 종료 host elapsed 18.31953 s. Hold 안에서 끝까지 기록된 OLD 이동 .08606 m/yaw −10.50°, observation snapshot부터는 .10692 m/−13.05°. 미적용 FRESH full/prefix obstacle clearance .17519/.21189 m, corridor .01114 m로 기존 기준상 안전하지만 **실제 switch B가 없으므로 handoff 성공·실패 pair로 만들지 않았다.** `OLD_EXECUTION_RISK` 사례이며 안전한 FRESH가 있었으니 무지연 전달로 반드시 회피했을 것이라는 반사실 주장은 하지 않는다.

D500/D750의 마지막 interval은 각각 직전 FRESH의 실행이면서 다음 pending prediction 관점에서는 OLD 실행이다. 하나의 corridor 실패를 두 사건으로 중복 집계하지 않는다. Native waypoint를 원본 PD가 local point로 반복 사용하는 실행 의미, observation→switch pose 차이, full polyline의 안전성은 별개다.

## 판정 및 보존

실측 OLD 이동·switch offset 증가, correspondence 가용성 감소, 원본 RAW navigation의 corridor 실패, D750의 timeout/hold 중 OLD 위험은 확인했다. 하지만 검사 가능한 entry는 모두 단순 geometric staging으로 연결 가능했고, 실패 지점은 유효 correspondence/heading 또는 실제 switch가 부족하다. **Graph 비교에 바로 사용할 qualified handoff는 확보하지 못했다. 최종 `INSUFFICIENT_EVIDENCE`; D0의 제한된 negative evidence만 `NO_QUALIFIED_CANDIDATE`로 유지한다.**

각 조건은 1회뿐이며 D0는 과거 코드/관측 시점의 참고 baseline이다. RGB/start/goal 렌더 hash 및 seed와 observation의 대응이 run마다 달라질 수 있다. 전체 성능 차이를 지연만의 paired causal effect나 일반적인 성능 곡선으로 주장하지 않는다. D750 mismatch 통계는 단 1개 유효 pair이므로 감소/증가 추세 판단에 쓸 수 없다. Staging/Graph closed-loop 성능·우월성, Topomap navigation 및 비관측 미래 구간은 미검증이다. 최초 sweep 단계에서는 추가 실험·Graph·figure·GUI·영상을 수행하지 않았다.

Raw는 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/uniform_d{250,500,750}_01/`, offline audit는 `uniform_audit_d{0,250,500,750}_01/`, 집계는 `uniform_sweep_report_01/`에 별도 보존했다. 큰 raw/NPZ/환경/cache는 Git에서 제외한다. [전체 비교 CSV](../research/results/isaac6_uniform_latency_20261017/comparison.csv), [수치 summary](../research/results/isaac6_uniform_latency_20261017/summary.json), 각 조건의 `pairs.csv`/`timing.csv`/input hash와 검증 JSON만 작은 결과로 추적한다.

## 후속 요청: 각 조건의 실제 주행 그래프

사용자의 추가 요청으로 저장된 72 Hz world pose만 사용해 [4조건 비교 그림](../research/results/isaac6_uniform_latency_20261017/plots/uniform_navigation_comparison.svg) 및 개별 [D0](../research/results/isaac6_uniform_latency_20261017/plots/D0_world_xy.svg), [D250](../research/results/isaac6_uniform_latency_20261017/plots/D250_world_xy.svg), [D500](../research/results/isaac6_uniform_latency_20261017/plots/D500_world_xy.svg), [D750](../research/results/isaac6_uniform_latency_20261017/plots/D750_world_xy.svg)를 생성했다. 동일 축 범위에서 실제 경로·진행 방향·장애물·start/goal·최종 9 cm footprint를 표시한다. 점선은 벽에서 agent radius를 뺀 중심 한계이며 장애물 safety margin과 다르다. Native prediction이나 가상 connector는 표시하지 않는다.

새 navigation/inference 0회, 결과 및 판정 변경 없음. Plot 입력 472개 hash를 생성 전후 대조하고 start/end pose, 72 Hz 시간 간격, goal entry와 최소 goal 거리를 기존 summary와 확인했다. 개별 4장과 비교 1장의 PNG/SVG를 육안 확인했다. PNG는 `/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/uniform_navigation_plots_01/`에, 작은 SVG 및 [manifest](../research/results/isaac6_uniform_latency_20261017/plots/manifest.json)는 Git에 보존한다.
