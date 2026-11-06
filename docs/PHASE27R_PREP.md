# Phase27-R 준비 — SP 출발 정렬 suffix 수정

**Isaac·smoke·본 실험은 실행하지 않았다.** 단위테스트와 Phase27F의 저장 SP 정렬5012건에 대한 목표 방향 재계산만 했다. 기존 주행·결과·Phase26 등록 protocol은 보존했다.

## 1. 허용된 수정 하나

`SPAlignment.replace_path`에서 동일한 `XYPath.project(B[:2])`로 `s_B`를 구하고, 저장된 waypoint 중 **호길이 s≥s_B+0.05m인 첫 점**을 정렬 목표로 선택한다. 5cm는 B와의 직선거리가 아니라 투영점 이후 호길이 기준이다. s_B+0.05m에 새 점을 삽입하지 않는다. 잔여 길이가5cm 미만이면 목표 없음으로 정렬하지 않는다. 경로 끝을 지난 B는 끝점으로 투영되어 같은 처리를 받는다.

정지20°/이동45° 기준, 실제 v<0.01 구분, ω한계0.4rad/s, 가속0.5m/s², SP·PP·TE·RTC·선택·fallback·회복·트리거·우회·certificate·평가 함수는 그대로다. 동작 파일 변경은 [execution.py](../research/nomad_phase20/execution.py#L13)의3줄뿐이다.

- 수정 전 SHA256: `89956a9310336dbb575d2651af9576732845262e5c531a83e45d3c203cab22e6`
- 수정 후 SHA256: `ebcd985e5f7f94878d35cf7361e561a2ce20fa9a482a5a43df05478428e20359`
- 원래 Phase26 protocol SHA256: `36b4d61b0ff3162a2369559e11bc3141f8061f10b20c8da8b47eead515266157` (변경 없음)
- Phase27-R delta 등록: [protocol.json](../research/nomad_phase27r/protocol.json), SHA256 `6d615e7a4c440d9c957025f672514def627ec99d63cdbcaa9dc37832535647f8`

Phase26의 엄격한 source hash 검사를 우회하지 않는다. Phase27-R wrapper에서 이 한 파일의 새 hash만 명시적으로 허용하고 나머지 모든 frozen source·scene·Topomap·checkpoint hash는 그대로 검증한다. 기존 `nomad_phase26.campaign` 직접 실행은 원래 hash와 달라 거부되며, 아래 새 wrapper만 사용한다. wrapper 변경은 검증 예외·프로세스 모듈 경로·결과 저장 경로·provenance 표기뿐이다. 주행 구현은 원래 Phase26 launcher/simulator/실행기를 재사용한다.

## 2. 단위테스트와 무변경 조사

**21개 통과 / 21개**, 실패0·오류0. B가 경로 중간,5cm 미만 suffix, 끝점 이후, 곡선 경로(호길이와 직선거리 구별), 정확5cm 경계, 임계각·회전 명령을 확인했다. 재실행 wrapper의60개 순서·한 파일 hash 예외·이전 raw 경로 거부·결과 파일 byte 동등성도 검증했다. 기존 Phase26 장면·판정 테스트와 Phase20의 SP/정렬 관련 단위테스트를 포함한다. 기존 `test_moving_alignment_brakes_before_rotation` 한 개는 합성 직각 경로108tick 수치 적분으로 감속 후 회전 명령을 검증한다. Isaac·NoMaD·기존 run 재주행은 없으며, 저장5012사건 검산에서는 궤적 rollout 없이 방향만 계산했다.

| 코드 | 조사결과 | 근거 |
|---|---|---|
| [research/nomad_phase19s/srg.py](../research/nomad_phase19s/srg.py#L82) | SAME_PREFIX_SCAN_UNCHANGED | Offline SRG trigger S scans full.points by Euclidean distance; no edit. Phase26 does not call this rollout (SP imports wrap/evaluate only). |
| [research/nomad_phase24r/follower.py](../research/nomad_phase24r/follower.py#L24) | CHORD_DIRECTION_NOT_PREFIX_POINT | Uses segment chord, not B-to-old-waypoint. first_pending also checks segment0 before projected segment: a different potential stale-segment direction; investigated only, unchanged. |
| [research/nomad_phase17/recovery.py](../research/nomad_phase17/recovery.py#L9) | NO_PATH_PREFIX_INPUT | Depth free rays at current heading +/-30deg determine recovery sign. No chunk-prefix target. |
| [research/nomad_phase23/rollout.py](../research/nomad_phase23/rollout.py#L16) | PLANNED_HEADING_SEGMENTS | Native graph rotation uses planned segment theta/omega; does not scan original prefix for a point5cm from B. Unchanged. |
| [research/nomad_phase21/execution.py](../research/nomad_phase21/execution.py#L30) | INHERITS_CORRECTED_SP | SAFE_TE latest selected chunk uses SPAlignment; no independent prefix selector. Ensemble steering and KEEP rules unchanged. |
| [research/nomad_phase23/prediction.py](../research/nomad_phase23/prediction.py#L1) | INHERITED_SP_WITH_SAVED_STATE | Existing prediction reuses SPAlignment and restores saved alignment state when available; not separately edited or used to simulate here. |

Phase19-S의 offline SRG에는 같은 full-prefix 검색이 남아 있지만 요청대로 고치지 않았다. G chord 정렬은 B에서 과거 점을 향하는 동일 계산이 아니다. 다만 `first_pending` 때0번 chord를 별도로 보는 동작은 그대로 남는다. RECOVER_ROTATE는 depth ray 기준으로 경로 prefix를 읽지 않는다. 이들 조사에서 새 주행이나 성능 검증을 하지 않았다.

## 3. 5012개 저장 사건의 오프라인 검산

Phase27F의 `SP_START` 사건만 사용했다(G 정렬 제외). 각 원래 `PATH_APPLIED`의 B·실제 직전 속도·설치 경로를 그대로 넣었다. 수리/우회/HERMITE 경로가 설치됐던 사건도 그 **실제 설치 경로**를 사용한다. 새 FRESHEST 선택이나 NoMaD 재생성은 하지 않았다. 원래 목표각의 재계산과 Phase27F 로그 값의 최대 차이는 9.95e-14°다.

범위는 하한 포함/상한 제외,90°+는180° 포함. 수정 후 목표가 없는 사건은0°로 대체하지 않고 별도 열로 센다. 아래 표는 **원래 정렬이 발동했던5012건에 조건부인 재계산**이다. 원래 정렬하지 않은 사건에서 새로 발동할 수 있는 수나 폐루프에서의 사건 수 변화는 측정하지 않았다.

### 수정 전 방향 오차

| 방법 | 사건 | 0–20° | 20–45° | 45–90° | 90°+ | 목표없음 |
|---|---|---|---|---|---|---|
| ALL | 5012 | 0 | 1241 | 484 | 3287 | 0 |
| B0_NOMAD_RAW | 546 | 0 | 101 | 52 | 393 | 0 |
| B1_SAFE_TE | 742 | 0 | 178 | 62 | 502 | 0 |
| B2_SAFE_RTC | 878 | 0 | 273 | 119 | 486 | 0 |
| B3_SAFE_ROTATE | 696 | 0 | 164 | 78 | 454 | 0 |
| B4_ASTAR | 1059 | 0 | 260 | 88 | 711 | 0 |
| C0 | 1091 | 0 | 265 | 85 | 741 | 0 |

### 수정 후 방향 오차

| 방법 | 사건 | 0–20° | 20–45° | 45–90° | 90°+ | 목표없음 |
|---|---|---|---|---|---|---|
| ALL | 5012 | 1829 | 1835 | 913 | 374 | 61 |
| B0_NOMAD_RAW | 546 | 197 | 185 | 90 | 55 | 19 |
| B1_SAFE_TE | 742 | 300 | 251 | 136 | 46 | 9 |
| B2_SAFE_RTC | 878 | 270 | 358 | 188 | 58 | 4 |
| B3_SAFE_ROTATE | 696 | 241 | 238 | 150 | 61 | 6 |
| B4_ASTAR | 1059 | 395 | 401 | 172 | 76 | 15 |
| C0 | 1091 | 426 | 402 | 177 | 78 | 8 |

### 정렬 발동 수와 이상적 회전 시간

추정 회전 시간은 발동 사건에 한해 `|wrap(목표방향−B heading)|/0.4rad/s`를 합한 값이다. 감속·제어 이산화·경로 만료·새 chunk 교체를 포함하지 않는다. 수정 전후 모두 같은 식을 사용했다. Phase27F에서 관측한 잘린 회전 시간과 이 이상적 정렬 완수 시간을 혼동해서는 안 된다.

| 방법 | 사건 | 전_발동 | 후_발동 | 후_정지20도 | 후_이동45도 | 전_추정회전_s | 후_추정회전_s |
|---|---|---|---|---|---|---|---|
| ALL | 5012 | 5012 | 2311 | 1559 | 752 | 27659.295 | 5750.228 |
| B0_NOMAD_RAW | 546 | 546 | 231 | 136 | 95 | 3210.081 | 634.201 |
| B1_SAFE_TE | 742 | 742 | 314 | 200 | 114 | 4229.214 | 764.542 |
| B2_SAFE_RTC | 878 | 878 | 491 | 387 | 104 | 4199.240 | 1130.196 |
| B3_SAFE_ROTATE | 696 | 696 | 334 | 192 | 142 | 3844.613 | 894.668 |
| B4_ASTAR | 1059 | 1059 | 461 | 310 | 151 | 5961.701 | 1136.726 |
| C0 | 1091 | 1091 | 480 | 334 | 146 | 6214.444 | 1189.894 |

수정 후 발동은 **2311/5012건**, 이상적 회전 시간 합은 **27659.295→5750.228s**다. 실제 시간 절약·성공률 개선을 의미하지 않는다. 전체 사건별 수치 및 Phase26 subset 표는 [preparation](../research/results/phase27r/preparation/)에 별도로 보존했다.

## 4. 재실행 준비 — 실행하지 않음

원래 Phase26 그대로 B0/B1/B2/B3/B4/C0 × SLW/LC/L2/H1/H2 × seed201,202 =60회다. 원래 `main_order`·등록 판정·기술 실패1회 동일 seed 재시도와 그룹 제외·잠금·재개·socket 사전 검사·벽 검증·저장량 정책을 재사용한다. 모든 가능한120개 attempt의 socket 길이는100bytes 미만(최대 99bytes)이다. 원래 smoke 자료는 기술적 선행 자료로만 재사용하며, 이번 수정 후 smoke를 실행했다고 주장하지 않는다.

raw run-root: `../artifacts/isaac6/phase27r_pilot_01` (새 경로). 최종 결과: `research/results/phase27r/`. 준비 자료는 그 아래 `preparation/`, 완료 후 결과 문서는 `docs/PHASE27R_RESULTS.md`다. Phase26의 기존 report 함수·판정 함수를 다른 out/doc 인수로 호출하며 기존 결과를 덮어쓰지 않는다. 가짜60행 입력으로 기존 결과와 새 경로 결과의 runs/summary/paired/decision/exclusions가 byte 단위로 일치함을 확인했다.

### 디스크·시간

- 현재 여유 **80.84GB (75.28GiB)**.
- 원래 Phase26 용량 계산 그대로 남은60run 예상 **144.45GB**,20GB여유 포함 필요 **164.45GB**.
- 현재 상태: **DISK_NOT_READY**. 부족분 **83.62GB**. 자동 삭제나 보관 정책 변경을 하지 않았다. 공간이 부족한 채 아래 명령을 실행하면 기존 사전 점검이 첫 run 이전에 LOW_DISK_STOP으로 정지한다.
- seed201은 scene별 원본 RGB/depth 전체 보존, seed202는 기존 축소 보관 규칙 그대로다. 매 run/재시도 직전에 남은 추정량+20GB를 재검사한다.
- 과거 Phase26 smoke 기반 예상 약 **3.70시간**. 이번 버그 수정 후 주행을 측정하지 않아 소요시간은 검증되지 않았다. 회복·주행 변화에 따라 달라질 수 있다.

공간 확보 후 사용자가 한 번 실행할 명령(이번 준비에서는 실행하지 않음):

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase27r.campaign --run-root ../artifacts/isaac6/phase27r_pilot_01 > ../artifacts/isaac6/phase27r_pilot_01.log 2>&1 < /dev/null &
```

진행 확인(한 줄):

```bash
cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase27r.campaign --run-root ../artifacts/isaac6/phase27r_pilot_01 --status
```

준비 보고서 재생성(주행 없음): `PYTHONPATH=research /usr/bin/python3 -m nomad_phase27r.report --prepare`. 본 campaign 완료 시 새 경로에 report를 생성하고 결과 commit·push하는 구조는 Phase26과 같다. venv 패키지를 설치하거나 환경을 변경하지 않았다.
