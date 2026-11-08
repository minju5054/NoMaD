"""Write registration and run offline tests/dry-runs only."""
import argparse,datetime,json,os,re,shutil,subprocess
from zoneinfo import ZoneInfo
from .config import ROOT,HERE,OUT,RUN_ROOT,SMOKE_ROOT,METHODS,SMOKE_METHODS,SCENES,INDICES,registered_order,verify

PREP=OUT/'preparation'
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def read(p):return json.loads(p.read_text())

BASE_CARE_REGISTRATION='477b651'

def registration_without_care(p):
    import copy
    p=copy.deepcopy(p)
    p.pop('care',None);p.pop('source_sha256',None)
    p['method_definitions'].pop('CARE',None);p['interpretations'].pop('care_input',None)
    return p

def freeze():
    """CARE-only amendment: all other registered definitions remain identical."""
    assert not RUN_ROOT.exists() and not SMOKE_ROOT.exists()
    import hashlib
    from nomad_isaac.common import sha256_file
    original=subprocess.check_output(['git','show',BASE_CARE_REGISTRATION+':research/nomad_phase38/protocol.json'],cwd=ROOT,text=True)
    baseline=json.loads(original);p=read(HERE/'protocol.json')
    assert registration_without_care(p)==registration_without_care(baseline)
    p['method_definitions']['CARE']='Phase35 NOMAD_RAW sample0/chunk timing + current-frame CARE; no SAFE filter, FRESHEST, EC, R2/R3 or recovery'
    p['interpretations']['care_input']='User-fixed NOMAD_RAW first sample, current-frame camera points only'
    p['care']=dict(input='NOMAD_RAW_SAMPLE_0',chunk_timing='Frozen RawNA.apply unchanged',
        obstacles='Current depth frame only: backproject, 0<camera axial Z<=1m, .03<world height<=.6; camera-X bins retain minimum Z',
        bins=32,bin_range='Uniform valid camera-X min/max per frame; inclusive right edge; empty bins omitted',
        bins_reason='M not specified in paper; user fixed32 before smoke',
        map_used=False,depth_filter=False,freshest_selection=False,ec=False,detour=False,recovery=False,
        depth_noise='Frozen common Gaussian sigma=.01*d^2, same per-frame RNG stream; no accumulation',
        force='F(p_k)=sum_m (p_k-o_m)/||p_k-o_m||^4 in robot plane x-forward,y-left',
        single_term_magnitude='1/d^3 mathematically; explicit vector equation takes precedence over inverse-square prose',
        sign_rationale='User-fixed repulsive intent, positive robot-plane sign instead of literal negative sign in paper equation; camera-to-robot and left/right directions unit tested',
        selected_waypoint='argmax norm(F); first index on exact tie',
        rotation='atan2(F_y,F_x), clipped to +/-pi/4; rotate all waypoints about application robot origin B; no special frontal/backward-force case',
        clip_rad=0.7853981633974483,safe_fov_rad=0.5235987755982988,
        safe_fov='If corrected p_k* heading error >pi/6: immediate v=0 in-place rotation capped at .4rad/s; otherwise common PP/SP',
        no_obstacles='unchanged RAW path/executor',v_max_m_s=.3,w_max_rad_s=.4,numerical_epsilon_m=1e-9,
        paper='https://arxiv.org/html/2506.03834v4',
        differences=['camera depth instead of monocular estimate','common .3m/s .4rad/s limits','M32 chosen explicitly','p_k* for Safe-FOV and PP lookahead .25m for translating','user-fixed repulsive robot-plane sign'],
        amended_at_kst=datetime.datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
        previous_protocol_sha256=hashlib.sha256(original.encode()).hexdigest(),before_smoke=True)
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))}
    assert registration_without_care(p)==registration_without_care(baseline)
    save(HERE/'protocol.json',p);verify();return p

def validate():
    from nomad_isaac.common import sha256_file
    verify();assert not RUN_ROOT.exists() and not SMOKE_ROOT.exists();PREP.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    result=subprocess.run(['/usr/bin/python3','-m','unittest','discover','-s','research/nomad_phase38','-t','research','-p','test_*.py','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (PREP/'tests.txt').write_text(result.stdout+result.stderr)
    assert result.returncode==0,(result.stdout+result.stderr)[-3500:]
    for name,args in [('all',[]),('night1',['--night','1']),('night2',['--night','2']),('smoke',['--smoke'])]:
        data=subprocess.check_output(['/usr/bin/python3','-m','nomad_phase38.campaign','--dry-run',*args],cwd=ROOT,env=env,text=True);save(PREP/f'dry_{name}.json',json.loads(data))
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase38.launch,nomad_phase38.campaign;assert 'scipy' not in sys.modules"],cwd=ROOT,env=env,check=True)
    inherited=read(ROOT/'research/results/phase26/preflight.json');assert inherited['passed'] and inherited['protocol_sha256']==sha256_file(ROOT/'research/nomad_phase26/protocol.json')
    result=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',result.stderr).group(1)),dry_run=180,night_jobs=[90,90],smoke_commands=4,
        simulations_started=0,venv_stdlib_import_passed=True,protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    import hashlib
    before=json.loads(subprocess.check_output(['git','show',BASE_CARE_REGISTRATION+':research/nomad_phase38/protocol.json'],cwd=ROOT,text=True))
    after=read(HERE/'protocol.json');unchanged=registration_without_care(after)
    assert unchanged==registration_without_care(before)
    stable_files=['campaign.py','ec_normal.py','launch.py','metrics.py','report.py','scenes.py','simulator.py','statistics.py']
    assert all(sha256_file(HERE/f)==before['source_sha256']['research/nomad_phase38/'+f] for f in stable_files)
    save(PREP/'care_revision_scope.json',dict(base_commit=BASE_CARE_REGISTRATION,
        previous_protocol_sha256=after['care']['previous_protocol_sha256'],protocol_sha256=result['protocol_sha256'],
        non_care_registration_equal=True,non_care_registration_sha256=hashlib.sha256(json.dumps(unchanged,sort_keys=True).encode()).hexdigest(),
        unchanged_operational_sources=stable_files,simulation_runs=0))
    save(PREP/'validation.json',result);return result

def document():
    from nomad_isaac.common import sha256_file
    p=verify();v=read(PREP/'validation.json');digest=sha256_file(HERE/'protocol.json');assert v['protocol_sha256']==digest
    prefix=f'cd {ROOT} && '
    env='env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase38.campaign'
    commands={f'night{n}':prefix+f'nohup {env} --night {n} > ../artifacts/isaac6/phase38_night{n}.log 2>&1 < /dev/null &' for n in (1,2)}
    commands['smoke']=prefix+f'nohup {env} --smoke > ../artifacts/isaac6/phase38_smoke_01.log 2>&1 < /dev/null &'
    commands['status']=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase38.campaign --status'
    commands['smoke_status']=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase38.campaign --smoke --status'
    save(PREP/'commands.json',dict(commands,executed=False))
    text=f'''# Phase38 준비

**FROZEN / 실행0회.** 단위테스트{v['tests']}개,180조합 dry-run(밤별90),smoke4조합 인자 검증 통과. Protocol SHA256: `{digest}`. 여유 공간 {v['disk_free_bytes']/1e9:.1f}GB.

| 방법 | 정의 |
|---|---|
| NOMAD_RAW / TE / RTC / ASTAR+EC / OURS | Phase35 동결 그대로. RAW의 depth·필터·회복 없음도 유지 |
| TE+EC / RTC+EC | 해당 handoff + Phase32 EC, 다음 SAFE→같은 SAFE들0.1m/s→STOP_WAIT |
| OURS−DETOUR | OURS의 평소 SAFE/EC/회복 유지,트리거 결정 계층·R2/R3 없음 |
| CARE | NOMAD_RAW sample0·동일 chunk 시점 + 현재 depth 프레임 CARE. SAFE·FRESHEST·EC·우회·회복 없음 |

CARE만 smoke 전에 개정했다. 다른8방법·배치·seed·순서·EC·판정은 원 protocol과 동일하다. TE+EC는 기존 ensemble/1초 만료를 검사하며36tick 재검사·다음9Hz tick 적용·감속 상한 유지도 그대로다.

CARE는 현재 프레임의 역투영 점에서 `0<Z≤1m`, 공통 높이 `0.03<h≤0.6m`를 적용하고 카메라 좌우 X 범위를32등분해 칸별 최소 Z점 하나를 남긴다(지도 누적 없음). 로봇 평면(x전방,y왼쪽)에서 `F=Σ(p−o)/‖p−o‖⁴`, 최대 ‖F‖ waypoint의 `atan2(Fy,Fx)`를±π/4로 clip하여 전체 경로를 B 원점 기준 회전한다. 정면 장애물 별도 처리 없음. O가 비면 RAW 경로 그대로다. Safe-FOV는 보정된 p_k*의 heading 오차>π/6이면 **즉시 v=0**, |ω|≤0.4로 제자리 회전하고, 그 외에는 PP/SP를 쓴다. 식의 단일 항 크기는 수학적으로1/d³이며, 사용자 지정 수식 자체를 유지했다.

| 원문과의 차이 | 이번 구현 |
|---|---|
| [CARE v4](https://arxiv.org/html/2506.03834v4) depth 소스 | 단안 추정 대신 공통 depth 카메라·노이즈·높이 필터, 현재 프레임만 사용 |
| CARE 속도 제한 | 공통0.3m/s·0.4rad/s |
| CARE 칸 수 | 원문에 M이 명시되지 않아32로 고정; 유효 카메라 X의 min/max를 균등 분할 |
| CARE 제어 waypoint | Safe-FOV는 p_k*, 전진 조향은 공통 PP lookahead0.25m·SP |
| CARE 식(1) 부호 | 원문 −표기 대신 반발 의도를 따른 사용자 지정 로봇평면 +수식 사용; 카메라→로봇 변환 후 왼쪽 장애물→오른쪽 회전 및 대칭을 단위테스트로 확인 |
| [RTC](https://arxiv.org/html/2506.07339v2): flow 정책·soft masking | 현재 NoMaD DDPM RTC-hard/RePaint prefix+guidance(β5) 유지. 원 논문의 완전 재현으로 부르지 않음 |

장면 SLW,LC,L2,H1,H2 × seed217–220 ×9방법=180회. 밤1=217,218 / 밤2=219,220. seed→scene 블록 안 순서만 RNG20261111로 섞었다. 돌발 상자는 기존 옆 방향 위치에 **U(−0.2,+0.2)m**를 더하며,벽/기존 상자 겹침 또는 넓은 쪽 유효 틈<0.28m이면 재추출한다. 배치는 scene×seed별 모든 방법에 같고 protocol에 수치·재추출 횟수를 고정했다. 새로운 장면 렌더나 주행은 하지 않았다.

밤별 누적 report: 방법×장면 도착·충돌·도착시간(도착 run 중앙값),8짝 비교×두 결과의 McNemar exact/Holm16검정,OURS 대 나머지8방법 도착 비열등성(짝 bootstrap20,000회,seed20261111,장면 내 재표집,95% CI 하한≥−10%p). 밤1은 중간 통계이고 Holm은 각 누적 report의16검정에 적용한다. 기술실패는1회 재시도 후 해당 비교 짝을 제외하고 보고한다. 종료 후cache정리,매 attempt 전30GB 검사,전역 잠금·재개 사용. 밤2는 밤1 완료 후만 시작한다. 각 밤 끝에 `docs/PHASE38_RESULTS.md`와 결과표를 자동 생성·commit·push한다.

명령은 모두 **준비만 했고 실행하지 않았다**. smoke는 H1 seed95에서 TE+EC,RTC+EC,CARE,OURS−DETOUR 각1회 순차 실행한다(본 결과 제외; 기술 실패만 같은 seed로1회 재시도).

```bash
{commands['smoke']}
```
```bash
{commands['smoke_status']}
```
밤1 / 밤2(각90회,한 번에 하나만):
```bash
{commands['night1']}
```
```bash
{commands['night2']}
```
```bash
{commands['status']}
```

run-root: `../artifacts/isaac6/phase38_01/night1`, `night2`. CARE는 프레임당 최대32점과 메타데이터만 압축 저장하고 SDF는 만들지 않는다. 다른 방법 저장v2는 그대로다. 검증 산출물: `research/results/phase38/preparation/`. venv 설치·기존 phase 소스/결과 변경 없음.
'''
    (ROOT/'docs/PHASE38_PREP.md').write_text(text)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');ap.add_argument('--document',action='store_true');a=ap.parse_args()
    if a.freeze:freeze();print('Registration frozen; no driving')
    if a.validate:print(json.dumps(validate()))
    if a.document:document();print('Short PREP document written')
if __name__=='__main__':main()
