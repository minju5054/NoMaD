"""Freeze and document the preparation; never starts navigation."""
import argparse,hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,ORDER_SEED,registered_order,runtime_config,verify
from nomad_phase31p.report import save,table

COMMAND='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase34p.campaign --run-root ../artifacts/isaac6/phase34p_01 > ../artifacts/isaac6/phase34p_01.log 2>&1 < /dev/null &'
STATUS='cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase34p.campaign --run-root ../artifacts/isaac6/phase34p_01 --status'

def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()

def freeze():
    from nomad_phase32.config import verify as frozen_verify
    from .routing import AST_PROOF
    old=frozen_verify();assets=json.loads((ROOT/'research/nomad_phase29/protocol.json').read_text())
    blocks,order=registered_order();frozen={**old['frozen_sources'],**old['source_sha256']}
    for relative in ('research/nomad_phase33p/storage.py','research/nomad_storage_sdf/loader.py'):
        frozen[relative]=sha(ROOT/relative)
    p=dict(status='FROZEN',phase='34-P',frozen_utc=datetime.now(timezone.utc).isoformat(),base='Phase32 C0-NA+EC',base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           methods=list(METHODS),display_name={METHODS[1]:'C0-NA+EC−R2'},indices=list(INDICES),planned=20,order_seed=ORDER_SEED,blocks=blocks,main_order=order,
           scenes={s:assets['scenes'][s] for s in SCENES},checkpoint_sha256=assets['checkpoint_sha256'],technical_retries=1,cache_cleanup=True,disk_min_bytes=30_000_000_000,
           change='ALL_UNSAFE dispatch branch calls existing start_detour(A) instead of R2; pending R3 blocks same-tick recovery exactly as pending R2 did',routing_ast=AST_PROOF,
           direction_A='frozen radial_reference: start to current displacement, <0.5m uses start heading',trigger_B='unchanged Phase32/24-R new-obstacle rule',
           unchanged=['R3 objective/constraints/7 starts/SLSQP/1s deadline','R3 EC candidate filtering and selection','fallback/recovery','depth update/filter','C0-NA PP+SP+alignment','oracle evaluation/goal0.3m/90s'],
           execution_certificate=old['execution_certificate'],storage=dict(version=2,snapshot_values=False,repair_input_values=False,compressed=True,loader='STORAGE_RETROFIT',
             live_update='unchanged',history='all required tick/component arrays retained',derived_cache='frozen R3 cache transport retained',raw_frame_retention='frozen Phase26 rule; seed201 full, other seeds compact',cleanup=['portable/cache','pycache']),
           primary=dict(pairs=10,positive='PROMISING',negative='NOT_PROMISING',rule='variant arrivals >= baseline arrivals AND variant collisions <= baseline collisions',
             evidence='all20 technically valid required; unknown collision does not count as safe; no group exclusion or imputation'),
           precheck=dict(source='all Phase32 attempts with repair SUBMIT logs',events=44,methods={'C0-NA+EC':31,'G18+EC':13},
             input='same R2-call B, previous_vw, snapshot, tick; original A radial u_ref; current retained EC cap',
             selection='frozen R3 seven starts -> EC filter all accepted -> original max progress/min length/index selection -> existing certificate',used_for_decision=False),
           frozen_sources=frozen,source_sha256={str(f.relative_to(ROOT)):sha(f) for f in HERE.glob('*.py')})
    save(HERE/'protocol.json',p)

def document():
    p=verify();pre=json.loads((OUT/'preparation/precheck_summary.json').read_text());direction=json.loads((OUT/'preparation/direction_regression.json').read_text())
    from .campaign import base,capacity
    old=base.protocol;base.protocol=lambda:p
    try:jobs=base.jobs(RUN_ROOT)
    finally:base.protocol=old
    assert len(jobs)==20;assert not RUN_ROOT.exists()
    disk=capacity(RUN_ROOT,jobs);save(OUT/'preparation/capacity.json',disk);save(OUT/'preparation/commands.json',dict(campaign=COMMAND,status=STATUS,executed=False))
    original=json.loads((ROOT/'research/results/phase32/runs.json').read_text());times=[r['launcher_wall_s'] for r in original if r['method']=='C0-NA+EC']
    estimate=sum(times)/len(times)*20;checks=json.loads((OUT/'preparation/tests.json').read_text())
    h=sha(HERE/'protocol.json');save(OUT/'preparation/verification.json',dict(protocol_sha256=h,planned=20,navigation_started=0,run_root_exists=False,tests=checks,disk=disk))
    text=f'''# Phase34-P 준비 — C0-NA+EC / C0-NA+EC−R2

**준비만 완료. 본 주행·smoke·Isaac·렌더·NoMaD 추론은 실행하지 않았다.** Protocol **FROZEN**, SHA256 `{h}`.

## 방법과 변경 범위

| 방법 | ALL_UNSAFE(A) | B | 공통 |
| --- | --- | --- | --- |
| C0-NA+EC | 기존 R2 → 실패 시 R3 | 기존 R3 | Phase32 동결 |
| C0-NA+EC−R2 | R2 호출 없이 기존 R3로 바로 진입 | 변경 없음 | 같은 R3/EC/fallback/실행기/지도/평가기 |

파일·CLI 식별자는 ASCII `{METHODS[1]}`을 사용한다. A의 u_ref는 기존 `radial_reference` 그대로다: 출발점→현재 위치 단위벡터, 변위0.5m 미만이면 출발 heading. 원 코드의 R2 dispatch body만 기존 `start_detour(A)` 호출로 바꿨다. 같은 tick에 pending R3와 RECOVER가 동시에 시작되지 않도록 pending-planner guard만 동등하게 확장했다. 이 두 AST 변경을 되돌리면 원 AST hash가 일치한다. NORMAL 선택·worker-busy fallback·B·R3 해 선택·EC·90° 초과 출발 정렬·PP/SP·회복 수치·목표0.3m·90s 제한을 바꾸지 않는다.

## 저장 v2

두 방법 모두 Phase33 저장 어댑터를 사용한다. snapshot과 repair input에는 values를 쓰지 않고 `savez_compressed`로 기록하며 STORAGE_RETROFIT 로더로 복원한다. tick/component metadata와 빈 지도 상수를 보존한다. 라이브 SDF 갱신/노이즈/필터 계산은 그대로다. R3의 기존 derived-cache 전송도 그대로이며, run 종료 후 기존 cleanup 옵션으로 `portable/cache`, `pycache`를 정리한다. 원본 RGB/depth 보존 여부도 기존 Phase26 규칙을 유지한다. 새 seed210/211은 compact 기록이다.

## 저장 로그 사전 확인 — 판정 미사용

Phase32 전체30 run/attempt의 R2 SUBMIT44건을 빠짐없이 사용했다. 각 호출의 B·이전(v,ω)·snapshot·tick·기존 속도 상한을 고정하고 R3 초기값7개를 기존4-process pool에서 한 번씩 풀었다. 원래 A→R3 로그의 방향 {direction['A_R3_directions_matched']}건도 같은 함수로 재현해 일치를 확인했다.

{table(pre['summary'])}

`R3_solution`은 EC 이전 수락 해 존재, `pre_EC_selected_pass`는 원 numerical winner의 EC 통과, `EC_eligible_solution`은 기존 EC 필터 뒤 선택 가능한 해 존재다. `available_with_existing_rules`는 여기에 기존 certificate와1s 한도를 포함한다. 고정 snapshot 반사실이며 계산 대기 중 이동·다음 관측/NoMaD 갱신은 재현하지 않는다. **이 수치로 실행/판정 조건을 바꾸지 않았다.**

## 사전등록 실행·판정

SLW/LC/L2/H1/H2 × seed210/211 ×2방법 =20회. seed→scene 블록, 블록 내 방법 순서는 `random.Random({ORDER_SEED})`로 고정했다.

{table(p['blocks'])}

10개 같은 scene×seed 짝에서 `PROMISING` = −R2 도착 수≥baseline 도착 수 AND −R2 충돌 수≤baseline 충돌 수. 그 외 `NOT_PROMISING`.20개 기술적으로 유효한 run이 없으면 unknown collision을 안전으로 간주하지 않고 `NOT_PROMISING`과 근거 불완전 사유를 함께 남긴다. 동일 seed 기술 실패1회 재시도, 완료 run 재실행 없음, 잠금/재개/원자 state 저장을 그대로 사용한다. 매 run/attempt 전 여유30GB 미만이면 중단한다.

자동 report는 `/usr/bin/python3 + PYTHONPATH=research`로 `docs/PHASE34P_RESULTS.md`, `research/results/phase34p/`를 생성하고 commit·push한다. 도착/충돌 외 지표는 판정에 쓰지 않는다: A 횟수, A의 R3 적용 성공/실패·EC 거절(job/후보), 우회 실행 시간, 도착시간 짝차이(둘 다 성공한 짝), 정지비율, 기존 평가기 contact 구간의 실행 상태. 기존 평가 결과를 다시 계산하거나 고치지 않는다.

## 검증·용량

단위 테스트 {checks['passed']}개 통과, 실제 base launcher 인자 검증20개는 socket 경계에서 중단해 프로세스 생성0을 확인했다. campaign20개 조합 dry-run과40개 attempt의 짧은 socket 경로 검사를 통과했다. Simulator는 SimulationApp 뒤에만 numerical/storage 모듈을 import한다. 모든 config는 허용한 seed/식별자 변경을 제외하면 동결 C0-NA 설정과 같다.

현재 여유 {disk['free_bytes']/1e9:.2f}GB. Phase32 C0-NA+EC launcher 실측 평균을20회에 적용한 참고 예상은 약 {estimate/3600:.2f}시간(새 장면의 경로 차이·재시도 제외)이다. 본 주행으로 시간을 다시 측정하지 않았다.

## 사용자 실행 명령 — 실행하지 않음

```bash
{COMMAND}
```

진행 확인:

```bash
{STATUS}
```

수동 report: `cd /home/gpuadmin/Workspace/NoMaD/visualnav-transformer && PYTHONPATH=research /usr/bin/python3 -m nomad_phase34p.report --run-root ../artifacts/isaac6/phase34p_01 --publish`
'''
    (ROOT/'docs/PHASE34P_PREP.md').write_text(text);print(json.dumps(dict(protocol_sha256=h,planned=20,navigation_started=0,free_GB=disk['free_bytes']/1e9)))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    else:document()

if __name__=='__main__':main()
