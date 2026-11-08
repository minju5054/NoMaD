# Phase39-O3 — unknown 지도 정책 비교 준비

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

검증: 합성 테스트11개·새 R3 274개 dry-run 통과. 실데이터 재풀이0회.
