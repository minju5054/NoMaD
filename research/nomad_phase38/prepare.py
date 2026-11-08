"""Write registration and run offline tests/dry-runs only."""
import argparse,datetime,json,os,re,shutil,subprocess
from zoneinfo import ZoneInfo
from .config import ROOT,HERE,OUT,RUN_ROOT,SMOKE_ROOT,METHODS,SMOKE_METHODS,SCENES,INDICES,registered_order,verify

PREP=OUT/'preparation'
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def read(p):return json.loads(p.read_text())

def freeze():
    assert not RUN_ROOT.exists() and not SMOKE_ROOT.exists()
    from nomad_isaac.common import sha256_file
    from .scenes import registered_jitter
    baseline=read(ROOT/'research/nomad_phase35/protocol.json');blocks,order=registered_order()
    sources={**baseline['frozen_sources'],**baseline['source_sha256']}
    for f in ('research/nomad_phase35/protocol.json','research/nomad_phase8/rtc_hard.py'):sources[f]=sha256_file(ROOT/f)
    p=dict(status='FROZEN',phase='38',frozen_at_kst=datetime.datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
        base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        methods=list(METHODS),indices=list(INDICES),scenes=baseline['scenes'],checkpoint_sha256=baseline['checkpoint_sha256'],
        planned=180,order_seed=20261111,blocks=blocks,main_order=order,nights={'1':[217,218],'2':[219,220]},
        smoke=dict(methods=list(SMOKE_METHODS),scene='H1',index=95,count=4,executed=False),
        method_definitions={
            'NOMAD_RAW':'Phase35 NOMAD_RAW frozen: sample0, no depth/filter/recovery; PP/SP >90deg alignment',
            'TE':'Phase35 SAFE_TE frozen: K3, older-heavy exp(-.5k), 1s expiry, SAFE/KEEP and recovery',
            'RTC':'Phase35 SAFE_RTC frozen: NoMaD DDPM RTC-hard/RePaint beta5, SAFE and recovery',
            'ASTAR+EC':'Phase35 ASTAR+EC frozen; original A* R2/R3 bridges',
            'OURS':'Phase35 OURS frozen; original R2/R3/trigger/EC',
            'TE+EC':'TE handoff plus Phase32 NORMAL EC/fallback, ensemble-aware forward integration',
            'RTC+EC':'RTC plus Phase32 NORMAL EC/fallback',
            'OURS-DETOUR':'OURS normal SAFE/EC/fallback/recovery; no trigger decision layer, R2 or R3',
            'CARE':'FRESHEST-SAFE then registered CARE rotation, recovery; no EC or R2/R3'},
        executor=baseline['executor'],
        interpretations=dict(care_input='FRESHEST-SAFE follows the requested common depth filter',
            te_ec='Inspect actual ensemble steering rather than mismatched single PP trajectory',
            jitter='Uniform continuous offset in [-.2,+.2]m; chosen before any driving data'),
        care=dict(input='FRESHEST_SAFE',obstacles='observed AND occupied common top-down cell centers within 1m of current robot center',
            force='sum unit(waypoint-obstacle)/distance^2; waypoint with largest norm; rotate full world path around application pose B',
            clip_rad=0.7853981633974483,safe_fov_rad=0.5235987755982988,
            safe_fov='Current corrected maximum-repulsion waypoint heading; brake within .5m/s2 then v0 rotation within .4rad/s until <=pi/6',
            numerical_epsilon_m=1e-9,coincident_direction='backward in robot frame',no_obstacles='unchanged path',
            paper='https://arxiv.org/html/2506.03834v4',adaptation_not_exact_reproduction=True),
        rtc=dict(implementation='research/nomad_phase8/rtc_hard.py',beta=5,unchanged=True,
            difference='DDPM waypoint RePaint hard-prefix+guidance, not original flow-policy soft mask',paper='https://arxiv.org/html/2506.07339v2'),
        ec_extension=dict(te_rollout='ENSEMBLE',margin_m=.025,horizon_s=2.,period_ticks=36,apply='next 9Hz tick, <=4 tick delay',
            fallback='primary full, next SAFE FRESHEST at full, all SAFE FRESHEST at .1m/s, STOP_WAIT',
            slow_cap='until next full-speed EC-PASS FRESH installation',
            te_expiry='advance retained chunk clock by rollout time; no future NoMaD chunks invented',
            te_candidate='hypothetical accepted candidate replaces its same-ID chunk; keep other valid chunks and original weights; rejected previews do not mutate live ensemble',
            te_keep='original SAFE KEEP pruning then EC on retained ensemble; reject -> STOP_WAIT'),
        placements={f'{s}_{i}':registered_jitter(s,i) for s in SCENES for i in (*INDICES,95)},
        placement_rule=dict(distribution='Uniform(-.2,.2)m added to frozen lateral center',seed_stream='SeedSequence([20261111,index,dynamic_scene_number,box_number])',
            shared_across_methods=True,reject='wall/static overlap or widest available side gap < .28m',robot_diameter_m=.18,extra_gap_m=.1),
        statistics=dict(comparisons=[['OURS',x] for x in ('NOMAD_RAW','TE','RTC','CARE')]+[['TE','TE+EC'],['RTC','RTC+EC'],['OURS-DETOUR','OURS'],['ASTAR+EC','OURS']],
            outcomes=['success','collision'],mcnemar='two-sided exact binomial on discordant pairs',holm_family=16,
            family_scope='all 8 pairs x 2 endpoints per cumulative report; night1 interim, no sequential-error guarantee',
            noninferiority='OURS goal rate minus each other method, CI lower >= -0.10',bootstrap_replicates=20000,bootstrap_seed=20261111,
            bootstrap_unit='paired scene x seed; resample within scene',bootstrap_interval='percentile95, not multiplicity adjusted',
            missing='exclude a comparison pair when either measurement technically invalid; no outcome imputation'),
        technical_retries=1,sequential=True,cache_cleanup=True,disk_min_bytes=30_000_000_000,
        storage=dict(version=2,values_saved=False,loader='nomad_storage_sdf.loader',archive_retention='Phase35 unchanged'),
        report=dict(automatic_after_each_night=True,cumulative=True,python='/usr/bin/python3',module='nomad_phase38.report',publish=True,
            document='docs/PHASE38_RESULTS.md',output='research/results/phase38'),
        preparation_only=True,simulations_started=0,frozen_sources=sources,
        source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))})
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
| CARE | FRESHEST-SAFE 입력→역제곱 반발 최대 waypoint의 방향으로 전체 경로±π/4 회전; 그 waypoint heading>π/6이면 제동 후 제자리 회전. EC/우회 없음 |

공통 이동은 C0-NA PP/SP(90° 초과 출발 정렬),depth V1,회복,저장v2다(RAW는 동결 예외). CARE의30° Safe-FOV 회전은 사용자 지정 추가 규칙이다. TE+EC는 실제 ensemble 조향·원1초 만료를 복제해 EC를 계산한다. 거절 preview는 실제 chunk를 바꾸지 않으며,주기적 대안은 같은 chunk ID/수신시각을 유지한다.36tick 재검사와 다음9Hz tick 적용,0.1m/s 상한의 다음 전속도 PASS FRESH까지 유지를 보존한다.

| 원문과의 차이 | 이번 구현 |
|---|---|
| [CARE v4](https://arxiv.org/html/2506.03834v4): RGB 추정 depth·전방 bin 최근점·식(1)의 거리 가중 | 공통 관측/점유 지도1m 이내 셀 중심; 사용자 지정 **역제곱의 바깥 방향 벡터**. 원문 식(1)을 그대로 복제한 것이 아님 |
| CARE 입력·출력 | SAFE 선택 후 현재 B에서 보정,공통 PP/SP·0.3m/s·0.4rad/s 및 회복. 원문의 별도 전진/회전 제어와 다름 |
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

run-root: `../artifacts/isaac6/phase38_01/night1`, `night2`. 검증 산출물: `research/results/phase38/preparation/`. venv 설치·기존 phase 소스/결과 변경 없음.
'''
    (ROOT/'docs/PHASE38_PREP.md').write_text(text)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');ap.add_argument('--document',action='store_true');a=ap.parse_args()
    if a.freeze:freeze();print('Registration frozen; no driving')
    if a.validate:print(json.dumps(validate()))
    if a.document:document();print('Short PREP document written')
if __name__=='__main__':main()
