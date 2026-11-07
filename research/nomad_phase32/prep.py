"""Preparation only: hashes, saved baselines, fixed matrix and dry-run evidence."""
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,ORDER_SEED,registered_order,runtime_config,verify
from nomad_phase31p.report import save,table
COMMAND='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase32.campaign --run-root ../artifacts/isaac6/phase32_01 > ../artifacts/isaac6/phase32_01.log 2>&1 < /dev/null &'
STATUS='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase32.campaign --run-root ../artifacts/isaac6/phase32_01 --status'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def freeze():
 original=json.loads((ROOT/'research/nomad_phase29/protocol.json').read_text());old=[];sources={}
 for name in ('phase28','phase29'):
  file=ROOT/'research/results'/name/'runs.json';sources[str(file.relative_to(ROOT))]=digest(file)
  for r in json.loads(file.read_text()):
   if r['scene'] not in SCENES or r['index'] not in INDICES:continue
   keep=(name=='phase28' and r['method']=='C0-NA' and r['index'] in (201,202)) or (name=='phase29' and ((r['method']=='C0-NA' and r.get('stage')=='confirm') or (r['method']=='G18' and r.get('stage') in ('dev','confirm'))))
   if keep:old.append(dict(r,baseline_source=name,execution_day_proxy_kst=datetime.fromtimestamp((Path(r['output'])/'launch_complete.json').stat().st_mtime,ZoneInfo('Asia/Seoul')).date().isoformat()))
 assert len(old)==30 and len({(r['scene'],r['index'],r['method']) for r in old})==30
 save(OUT/'preparation/baselines.json',old);sources[str((OUT/'preparation/baselines.json').relative_to(ROOT))]=digest(OUT/'preparation/baselines.json')
 offline=json.loads((ROOT/'research/results/phase32o/decision.json').read_text());assert offline['label']=='OFFLINE_FAIL'
 sources['research/results/phase32o/decision.json']=digest(ROOT/'research/results/phase32o/decision.json')
 frozen={**original['frozen_sources'],**original['source_sha256']}
 for p in ['research/nomad_phase28/alignment.py','research/nomad_phase28/runtime.py','research/nomad_phase32o/exec_cert.py','research/nomad_phase26/execution.py','research/nomad_phase26/rendering.py','research/nomad_phase24r/online_execution.py','research/nomad_phase24r/trigger.py','research/nomad_phase20c/detour.py']:
  frozen[p]=digest(ROOT/p)
 estimates=[]
 for r in old:
  size=int(subprocess.check_output(['du','-sb',r['output']],text=True).split()[0]);files=list((Path(r['output'])/'depth').glob('snapshot_*.npz'));sizes=sorted(f.stat().st_size for f in files);map_size=sizes[len(sizes)//2] if sizes else 0
  extra=0 if r['index']==201 else 180*map_size
  estimates.append(dict(scene=r['scene'],index=r['index'],method=r['method']+'+EC',baseline_bytes=size,ec_extra_map_bytes_upper=extra,estimated_bytes=size+extra,baseline_launcher_wall_s=r.get('launcher_wall_s'),baseline_output=r['output']))
 blocks,order=registered_order();p=dict(status='FROZEN',phase='32',base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),methods=list(METHODS),indices=list(INDICES),planned=30,order_seed=ORDER_SEED,blocks=blocks,main_order=order,scenes={s:original['scenes'][s] for s in SCENES},checkpoint_sha256=original['checkpoint_sha256'],
  disk_min_bytes=30_000_000_000,storage_estimates=estimates,technical_retries=1,cache_cleanup=True,
  deviation=dict(date='2026-11-07',authority='explicit user decision',original_label='OFFLINE_FAIL',original_position_p95_m=offline['validation']['position_p95_m'],gate_m=.03,same_na_p95_m=offline['validation']['same_executor_p95_m'],decision='Proceed because identical C0-NA executor segment error is0m; original OFFLINE_FAIL remains unchanged'),
  execution_certificate=dict(period_ticks=36,integration_hz=72,control_tick_interval=8,max_reject_apply_delay_ticks=4,max_reject_apply_delay_ms=4/72*1000,installation='same9Hz tick immediate',horizon_s=2.,minimum_clearance_m=.025,radius_m=.09,
   map='latest immutable V1 depth snapshot, unknown free, oracle prohibited',periodic_state='copy active NA follower state/progress/alignment/cap; preserve9Hz phase and current command between control ticks',
   normal='primary then all remaining SAFE candidates in descending remaining length, index ties; if all fail, same SAFE list at.10m/s, first PASS; else STOP_WAIT',
   periodic_fallback_candidates='latest available saved NoMaD candidate set at the application tick, reranked with the latest depth map; native SAFE paths, no extra Graph solve',
   normal_graph_candidate='selected native candidate represented by its G18 XY when that is primary; other candidates are original SAFE XY; no extra Graph solves',
   capped='cap persists through periodic/Graph/R2/R3 replacements until next FRESH installs after full-speed PASS; acceleration .5 retained',
   r2='EC rejection -> unchanged R3 stage',r3='original solver-accepted outputs among7; EC PASS only, then unchanged max progress/min length/index selection; no eligible output -> unchanged failure',
   archive='retain exact snapshots inspected by EC through existing asynchronous archive queue; occupancy/capture/publisher untouched'),
  primary=dict(label_success='EC_HELPS',label_other='EC_NO_HELP',collision='sum both EC arms < historical sum both arms',goal='sum both EC arms >= historical sum minus1',technical_evidence='all30 technically valid required; otherwise EC_NO_HELP with incomplete-evidence reason'),
  frozen_sources=frozen,historical_sources=sources,source_sha256={str(f.relative_to(ROOT)):digest(f) for f in HERE.glob('*.py')})
 save(HERE/'protocol.json',p)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');a=ap.parse_args()
 if a.freeze:freeze()
 p=verify();from .campaign import base,capacity
 old=base.protocol;base.protocol=lambda:p
 try:jobs=base.jobs(RUN_ROOT)
 finally:base.protocol=old
 disk=capacity(RUN_ROOT,jobs);save(OUT/'preparation/capacity.json',disk)
 matches=[]
 from nomad_phase29.config import runtime_config as old_config
 for j in p['main_order']:
  c=runtime_config(j['method'],j['index'],90,j['scene']);b=old_config(j['method'].removesuffix('+EC'),j['index'],90,j['scene']);c={k:v for k,v in c.items() if k not in ('phase32','phase32_method','phase32_index')};assert c==b
  matches.append(dict(j,normalized_config_sha256=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()))
 save(OUT/'preparation/config_hash_comparisons.json',matches)
 oldrows=json.loads((OUT/'preparation/baselines.json').read_text());baseline_counts=[dict(method=m,n=15,goal=sum(r['method']==m and r['success'] for r in oldrows),collision=sum(r['method']==m and r['collision'] for r in oldrows)) for m in ('C0-NA','G18')]
 times=[r['baseline_launcher_wall_s'] for r in p['storage_estimates'] if r['baseline_launcher_wall_s'] is not None];estimated=sum(times)*1.15
 save(OUT/'preparation/commands.json',dict(campaign=COMMAND,status=STATUS,executed=False))
 hashes=digest(HERE/'protocol.json');save(OUT/'preparation/verification.json',dict(protocol_sha256=hashes,config_hash_matches=30,planned=30,navigation_started=0,run_root_exists=RUN_ROOT.exists()))
 text=f'''# Phase32 준비 — C0-NA+EC / G18+EC

**준비 단계만 수행. 시뮬레이션·smoke·렌더·NoMaD 추론·campaign을 실행하지 않았다.** 새 run-root는 `{RUN_ROOT}`이며 기존 결과를 덮어쓰지 않는다. Protocol **FROZEN**, SHA256 `{hashes}`.

## 사전등록 이탈 — 사용자 결정(2026-11-07)

Phase32-O 원 판정 **OFFLINE_FAIL**을 그대로 보존한다. 전체 전방 적분 위치오차 p95 **0.030037125m**가 원 gate **0.03m**를 넘었다. 동일 C0-NA 실행기 구간 오차 p95는 **0m**이므로 사용자가 진행을 명시적으로 승인했다. 이를 PASS로 재명명하거나 기존 gate·결과를 변경하지 않는다. Phase32-O 원 decision hash도 protocol에 고정했다.

## 공통 적용 규칙

- 두 방법의 실행기는 동결 C0-NA(PP0.25m+SP,90° 초과 정렬, v≤0.3·|ω|≤0.4·a≤0.5)다. G18 정상 Graph와 R2/R3 수식·가중치·초기값·solver·원 certificate·online stale/superseded 규칙, 결정 계층·depth/필터·평가기는 재사용한다. G18-R을 섞지 않는다.
- 설치 직전 해당9Hz 제어 tick에서 최신 immutable V1 depth로 EC를 수행한다. oracle을 검사 API에 전달하지 않는다. 원형 반경0.09m, swept minimum≥0.025m, 지평선은 기존 endpoint 도달 또는2s다.
- 설치 후 **36tick=0.5s마다**72Hz integrate callback에서 재검사한다. 제자리 정렬 목표·PP progress·감속 cap 등 현재 follower 상태를 복제하고 실제9Hz clock phase를 유지한다. tick36검사는 현재 명령을4tick 유지한 뒤 tick40에서 다음 제어를 계산한다. 이는 실행기 함수/수치를 바꾸는 것이 아니라 현재 실행 상태에서의 예측이다.
- 주기 REJECT 경로 교체/STOP_WAIT은 다음9Hz tick에 적용한다. 검사 tick·적용 tick·simulation-clock 지연 tick/ms(0 또는4tick, 최대55.56ms)와 실제 monotonic wall-clock 지연을 따로 기록한다. wall-clock 지연은 검사·fallback 계산과 pacing 초과를 포함할 수 있다. 이전 경로의 검사 결과를 새 경로에 적용하지 않도록 generation을 대조한다.
- NORMAL: primary 경로 → 남은 SAFE 후보(FRESHEST 잔여 길이 내림차순, index 동점 규칙) 전속도 검사 → **같은 SAFE 후보 전부를 같은 순서로0.1m/s 재검사** → 처음 PASS 설치 → 없으면 기존 STOP_WAIT. G18 primary는 해당 후보의 Graph XY, 나머지는 원 SAFE XY이며 추가 Graph 풀이를 하지 않는다.
- 주기 REJECT의 NORMAL 대안은 적용 tick에 이용 가능한 최신 NoMaD 후보 세트를 최신 지도에서 다시 SAFE/FRESHEST 순서로 검사한다. 이미 거절된 활성 경로를 전속도로 다시 설치해 검사를 우회하지 않는다.
- 0.1m/s 상한은 가속도 제한을 지켜 적용하고 **다음 FRESH가 전속도 PASS로 설치될 때만 해제**한다. 그 전 periodic/Graph/R2/R3 경로 교체에서도 유지한다. 감속 설치 수·유지 시간·선택 FRESHEST 순위를 기록한다.
- R2는 EC REJECT이면 기존 R3 단계로 보낸다. R3는7개 초기화의 원래 수락 해 중 EC PASS인 해만 대상으로 **기존 최대 전진→최소 길이→index** 선택을 쓴다. 없으면 원래 실패 처리다. 원 numerical results는 그대로 로그에 보존하고 EC 선택만 별도 기록한다.
- EC STOP이 부모 코드의 NORMAL 알림으로 잘못 초기화되지 않도록 adapter가 알림을 보호한다. RECOVER_ROTATE의 조건·회전량·횟수 상한은 바꾸지 않는다.

EC 검사에 실제 사용한 snapshot은 기존 비동기 archive queue로 보존한다. 지도 계산/갱신/노이즈/unknown 정책은 바뀌지 않는다. 검사 연산은 실행 thread에서 동기적으로 수행되며 그 비용과 pacing 영향은 보정하지 않는다. R3 여러 해를 검사하는 batch에는 여러 EC 호출이 포함된다.

## 실행 행렬·과거 비교

H1/H2/L2 × seed201~205 × 두 방법 =30회. seed→scene, 각 블록 방법 순서는 `random.Random({ORDER_SEED})`로 사전에 고정했다.

{table(p['blocks'])}

{table(baseline_counts)}

과거 대조는 같은 scene×seed의 C0-NA15개와 G1815개다. C0-NA201/202는Phase28,203~205는Phase29 confirm; G18은Phase29 dev/confirm. Phase31-P seed206/207은 비교 키에 없어 사용하지 않는다. **실행일이 다른 역사적 짝 비교**라는 한계를 명시한다. 원 데이터·출력 폴더·source hash를 `preparation/baselines.json`과 protocol에 고정했다.

## 판정과 report

`EC_HELPS` = 두 EC 방법의 충돌 합 < 기존 두 방법의 충돌 합 **AND** EC 도착 합 ≥ 기존 도착 합−1. 그 외 `EC_NO_HELP`.30개가 모두 기술적으로 유효하지 않으면 안전 개선을 주장하지 않고 EC_NO_HELP와 근거 불완전 사유를 남긴다. 기술 실패는 기존 campaign처럼 동일 seed1회만 재시도하며 완료 run은 재실행하지 않는다.

완료 후 `/usr/bin/python3 + PYTHONPATH=research` report가 `docs/PHASE32_RESULTS.md`, `research/results/phase32/`를 만들고 commit·push한다. 방법×장면 도착/충돌/도착시간/정지비율, 같은 seed 차이, 상태별 EC 호출/REJECT, fallback별 수, REJECT로 인한 실제 정지시간, 계산 p50/p95, 주기검사 적용 지연, 감속 설치/유지/순위를 포함한다. STOP latch 이후 물리정지 총시간과 순수 STOP_WAIT시간을 분리한다.

## 검증·용량

30개 config는 Phase29 원 설정에서 Phase32 식별 필드를 제거하면 hash가 일치한다. 실제 base launcher의 argparse/status/index 검증30개를 socket 계산 경계에서 중단해 확인하며, worker/Isaac 프로세스는 생성하지 않는다. SimulationApp 이전에는 EC/SciPy를 import하지 않는다. 신규 EC 테스트23개와 동결 EXEC-CERT 테스트13개, 총36개를 통과했다. 실제 base launcher 인자 검증30개와 campaign30조합 dry-run도 통과했으며 세부 결과는 `preparation/tests.json`에 저장한다.

현재 여유 **{disk['free_bytes']/1e9:.2f}GB**. 같은 과거 run 저장량+compact run의 추가 EC map 보존 상한으로30회 **약 {disk['expected_remaining_bytes']/1e9:.2f}GB**,30GB reserve 포함 **{disk['estimated_full_with_reserve_bytes']/1e9:.2f}GB**를 예상한다. 전체 예상 충족 `{disk['estimated_full_with_reserve_enough']}`; 부족분 약 **{max(0,disk['estimated_full_with_reserve_bytes']-disk['free_bytes'])/1e9:.2f}GB**(기술 재시도 별도). run별 실제 여유30GB 미만이면 다음 run 전에 LOW_DISK_STOP. 기존 raw를 삭제하지 않는다. 기존 full-frame seed201/compact 나머지 규칙과 종료 후 portable/cache·pycache 정리를 유지한다.

과거 launcher 실측 합에 EC 처리 여유15%를 둔 예상 시간은 **약 {estimated/3600:.2f}시간**(재시도·디스크 정지 제외). 준비 중 새 주행으로 시간을 측정하지 않았다.

## 사용자 실행 명령 — 실행하지 않음

```bash
{COMMAND}
```

진행 확인:

```bash
{STATUS}
```

수동 report: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase32.report --run-root ../artifacts/isaac6/phase32_01 --publish`
'''
 (ROOT/'docs/PHASE32_PREP.md').write_text(text)
 print(json.dumps(dict(protocol_sha256=hashes,planned=30,navigation_started=0,run_root_exists=RUN_ROOT.exists(),free_GB=disk['free_bytes']/1e9,estimated_GB=disk['expected_remaining_bytes']/1e9)))
if __name__=='__main__':main()
