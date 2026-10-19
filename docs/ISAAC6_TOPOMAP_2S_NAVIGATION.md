# Topomap 간격 2초: 정적 주행 1회

2026-10-19. 사용자의 “Topomap 사이 간격을 더 넓게 해서 실행” 요청에 따라 기존 약 1초를 **2초**로 넓혔다. 기준 `b2d490a`, branch `research/isaac6-topomap-2s`. 사전 고정 protocol/실행 commit은 **`d1b3b86`**이다. **단일 주행에서 두 정적 장애물을 안전하게 통과하고 25.305556 simulation s에 목표 범위에 진입했다.** 재시도는 없었다.

## 변경한 조건

기존 성공 reference의 26개 RGB 중 parent node **0,2,4,…,24,25**를 선택했다. 새 node는 0–13이며, 원래 node ID와 reference pose/tick/hash를 manifest에 남겼다. 시각은 **0,2,…,24,24.583333 s**로 시작과 마지막 goal-entry 이미지를 포함한다. 간격은 simulation time 기준이고 일정한 metric 거리나 native waypoint timestamp가 아니다. 인접 node XY 거리 median은 **.397388 m**, min/max는 **.116661/.399855 m**다. 처음 정지 구간과 마지막 잔여 구간은 더 짧다.

PNG는 기존 reference에서 **byte-identical 복사**했다. 새 rendering은 0회이며, 원래 render SHA와 subset SHA를 구분했다. 기존 1초 manifest/raw는 그대로다. Node/world pose는 검증용 metadata이고 online closest 선택에는 입력하지 않는다.

유지: radius=4, close_threshold=3, 공식 distance-head/argmin/subgoal 규칙, 선택된 condition의 10-step diffusion 1회, sample 0/index 2, checkpoint와 seed `101+2k`/DDPM `+1`, 기존 두 정적 장애물·camera·시작/목표·radius .09 m·안전 clearance .02 m·goal tolerance .30 m·4/9/72 Hz·PD·1초 timeout·asynchronous execution·추가 latency 0. 원래 60 s simulation timeout을 사용했다. **노드 간격이 넓어졌으므로 같은 radius=4의 탐색창도 더 넓은 공간을 포함한다.**

실행 metadata의 scenario 차이는 Topomap manifest 경로와 hash 두 항목뿐이다. 모델·controller·기존 실행 환경은 변경하지 않았다. 최소 코드 변경은 reference row 간격 인자와 map 검증/기존 그림 label의 가변 간격 지원, 저장 RGB subset 생성 script/protocol이다. 원래 1초가 기본값이다.

## 실측 결과

| 항목 | 기존 1초 / 26 nodes | 새 2초 / 14 nodes |
|---|---:|---:|
| Goal entry | 실패 | **성공** |
| 종료 원인 | 왼쪽 corridor footprint 침범 | goal entry |
| 종료 simulation s | 13.902778 | **25.305556** |
| 최소 goal 거리 m | 2.849002 | **.297394** |
| 장애물 1 minimum swept clearance m | .432678 | **.279149** |
| 장애물 2 minimum swept clearance m | .634763 (미통과) | **.074423** |
| Corridor minimum clearance m | −.001509 | **+.778398** |
| Inference / 실제 switch | 52 / 52 | **98 / 97** |
| Warm inference median / p95 ms | 36.579 / 52.610 | **35.182 / 46.586** |
| 실제 waypoint 적용 빈도 Hz | 3.991 | **4.000** |
| Waypoint timeout | 0 | **0** |

첫 장애물은 **10.986111 s에 왼쪽(+Y)**, 두 번째는 **20.902778 s에 오른쪽(−Y)**으로 통과했다. 실제 swept geometric overlap은 없고, 두 장애물 모두 2 cm 안전 여유를 만족했으며 corridor containment도 통과했다. Kinematic footprint/AABB 평가이며 PhysX collision 검증을 뜻하지 않는다. 최종 pose는 `(4.206426199, −.047513042, .273984436)`이다.

Observation→switch wall delay median/p95 **138.242/166.411 ms**. RTF **.999994655**, pacing 절대 오차 p95/max **.151901/1.205512 ms**, late >1 integration tick **0회**. Busy skip 1, missed observation 0. 유효 OLD의 inference 중 이동 median/max **.005556/.008333 m**. GPU inference·wall/simulation clock 대응 통과. 실제 timeout은 발생하지 않았고 기존 synthetic timeout test를 재사용했다.

Goal node 13 선택은 실제 적용된 ID 93·96에서 확인됐다. 마지막 ID **97**도 수신됐지만 goal 종료로 **미적용**이며 switch 성공 횟수에 포함하지 않았다. Closest 후퇴 11회, subgoal 후퇴 13회, 실제 w 부호 반전 23회는 여전히 존재했다. 성공했다고 node/steering 불안정성이 사라졌다고 주장하지 않는다. 주행 길이가 달라 이전 run과 단순 횟수를 직접 비교하지 않는다.

## 검증·저장·한계

- 기존 CPU tests **17 passed**. Node PNG/pixel hash, pose/tick 대응과 parent manifest lineage 통과.
- 기존 GPU 동등성 검증을 2초 map RGB로 수행: 같은 condition/noise/DDPM seed의 normalized diffusion/cumulative/metric/selected waypoint는 **bitwise equal, 최대 차이 0**. Encoder 1 / distance head 1 / noise predictor 10회. 이 검증 history는 map node 0–3이며 4 Hz 주행 history 실험과 구분한다.
- 실제 주행의 모든 input RGB history/score/공식 선택식/sample 0/index 2/원본 PD/normalization/cumsum/observation anchor 통과. **Pose integration 오차 0, corridor 재계산 오차 0**, swept clearance 재계산 일치. Checkpoint coverage 100%, 출력 finite. Switch tick 불일치 없음.
- 기존 1초 run의 **117개** hash와 reference source hashes 보존. 기존 runtime validator가 확인하는 synchronous baseline **484개** hash도 보존. 실행 시 working tree는 clean이었으며 실행 source hashes 유지.
- 초기 renderer 준비 중 step error 5개는 기존 로그에 남겼고 이후 RGB gate와 정상 주행이 완료됐다. 이를 navigation failure나 무시된 collision으로 분류하지 않는다.

새 map: `../artifacts/isaac6/topomap_reference_2s_01/topomap/manifest.json`  
새 raw run: `../artifacts/isaac6/topomap_static_2s_01/`  
GPU 검증: `../artifacts/isaac6/topomap_2s_gpu_validation_01/gpu_equivalence.json`  
주행 검증: `../artifacts/isaac6/topomap_static_2s_01_validation/`

[작은 summary](../research/results/isaac6_topomap_2s_20261019/summary.json), [비교 CSV](../research/results/isaac6_topomap_2s_20261019/comparison.csv), [node metadata](../research/results/isaac6_topomap_2s_20261019/topomap_nodes.csv), [선택 기록](../research/results/isaac6_topomap_2s_20261019/topomap_selection.csv), [실제 XY 경로](../research/results/isaac6_topomap_2s_20261019/topomap_navigation.svg), [보존·검증 요약](../research/results/isaac6_topomap_2s_20261019/review.json).

**이번 2초 간격 조건의 성공은 확인했지만, 간격 변경만의 인과 효과나 일반적인 성공률 개선은 입증하지 않았다.** 두 실행의 RGB/관측 시점/request별 seed 대응이 달라 직접적인 paired comparison이 아니다. 성공한 정적 Topomap 기록은 확보됐으며, 동적 장애물·Graph·reranking·recovery·추가 간격 sweep·영상/GUI 작업은 수행하지 않았다.

사용한 명령(기존 output 경로는 재사용 금지):

```bash
env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV bash research/python.sh -m nomad_isaac.launch --asynchronous --topomap /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/topomap_reference_2s_01/topomap/manifest.json --scenario research/nomad_isaac/two_obstacles_wide_wall_scenario.json --output /home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/topomap_static_2s_01
```
