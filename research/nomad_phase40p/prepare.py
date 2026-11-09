"""Registration, tests and argument-only dry runs. Never starts a simulator."""
import argparse,json,os,shutil,subprocess
from datetime import datetime,timezone
from .config import ROOT,HERE,OUT,RUN_ROOT,SMOKE_ROOT,SCENES,INDICES,verify
from nomad_isaac.common import sha256_file

ESCAPE_TIME=('s_esc=(0.03-job c_B)/0.5; first72Hz installed frozen-rollout projected arclength >=s_esc. '
             'If path ends before s_esc use frozen endpoint-reached time. Otherwise if no crossing within2s use t_esc=2s, '
             'not REJECT. Store install_sim_s+t_esc as absolute deadline. Initial capped rollout entirely uses c0.')


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def freeze():
    assert not RUN_ROOT.exists() and not SMOKE_ROOT.exists()
    old=json.loads((ROOT/'research/nomad_phase38/protocol.json').read_text())
    vn=json.loads((ROOT/'research/nomad_phase39o3/protocol.json').read_text())
    p=dict(status='FROZEN',phase='40-P',frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        methods=['OURS-N'],indices=list(INDICES),scenes=old['scenes'],checkpoint_sha256=old['checkpoint_sha256'],
        placements=old['placements'],main_order=[dict(scene=s,index=i,method='OURS-N') for i in INDICES for s in SCENES],
        smoke=dict(scene='H1',index=217,method='OURS-N',attempts=1,excluded=True),
        planner='R2 frozen VE + R3 frozen VN; original CLR soft map retained; no A*',
        prediction=dict(delay_ticks=54,apply_tick='ceil((dispatch_tick+54)/8)*8',
            model='Frozen CappedNA state and current command, 72Hz integrate_se2, 9Hz controller; no future inputs',
            expired='Discard if absent at the designated apply tick or that tick was missed',
            early='Hold early results until the designated tick; install only after actual-pose latest-depth EC',
            superseded='R2 retains fresh-chunk SUPERSEDED; R3 keeps frozen active handover policy'),
        waiting='Frozen Phase38 OURS-DETOUR SAFE+EC alternatives/recovery; no planner-imposed stop command',
        escape_ec=dict(jobs='c_B<0.025 only',time_definition=ESCAPE_TIME,
            c0='First installation actual pose, original base exact clearance minus0.005m',
            periodic='Latest SDF; first installation clock and c0 fixed per job. Never extend on reinstall.',
            comparison='tau+t<=t_esc uses c0, afterward0.025; tau>=t_esc uses frozen EC everywhere',
            normal='All nonescape jobs/normal paths use frozen EC',period_ticks=36,horizon_s=2.),
        decision=dict(PILOT_OK='collision<=1 AND goal>=14',GRAPH_GAIN='goal>=17 AND OURS-N-only success pairs>=3 vs OURS-DETOUR',
                      planned_pairs=20,missing='Do not decide until20 technically valid pairs',mcnemar='Descriptive exact; success and collision vs three cached comparators'),
        execution=dict(serial=True,technical_retries=1,smoke_retries=0,cache_cleanup=True,disk_min_bytes=30_000_000_000,storage_version=2),
        reference_hashes={f:sha256_file(ROOT/f) for f in ('research/nomad_phase38/protocol.json','research/nomad_phase39o3/protocol.json','research/results/phase38/runs.json')},
        frozen_sources={**old['frozen_sources'],**old['source_sha256'],**vn['frozen_sources'],**vn['source_sha256']},
        source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in sorted(HERE.glob('*.py'))})
    save(HERE/'protocol.json',p);verify()


def validate():
    verify();assert not RUN_ROOT.exists() and not SMOKE_ROOT.exists()
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    result=subprocess.run(['/usr/bin/python3','-m','unittest','discover','-s','research/nomad_phase40p','-t','research','-p','test_*.py','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    (folder/'tests.txt').write_text(result.stdout+result.stderr)
    assert result.returncode==0,(result.stdout+result.stderr)[-5000:]
    for name,flags in [('main',[]),('smoke',['--smoke'])]:
        raw=subprocess.check_output(['/usr/bin/python3','-m','nomad_phase40p.campaign','--dry-run',*flags],cwd=ROOT,env=env,text=True)
        save(folder/f'dry_{name}.json',json.loads(raw))
    raw=subprocess.check_output(['/usr/bin/python3','-m','nomad_phase40p.campaign','--dry-run','--with-smoke'],cwd=ROOT,env=env,text=True)
    save(folder/'dry_campaign.json',json.loads(raw))
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase40p.launch,nomad_phase40p.campaign;assert 'scipy' not in sys.modules"],cwd=ROOT,env=env,check=True)
    import re
    save(folder/'validation.json',dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',result.stderr).group(1)),
         simulations_started=0,smoke_executed=False,dry_main=20,dry_smoke=1,protocol_sha256=sha256_file(HERE/'protocol.json'),
         disk_free_bytes=shutil.disk_usage(ROOT).free))
    historical=json.loads((ROOT/'research/results/phase38/runs.json').read_text())
    from pathlib import Path
    times=[json.loads((Path(r['output'])/'launch_complete.json').read_text())['launcher_wall_s'] for r in historical if r['method']=='OURS']
    assert len(times)==20
    save(folder/'runtime_estimate.json',dict(reference='Phase38 OURS20 frozen launcher wall times',n=20,
         mean_run_s=sum(times)/20,main_minutes=sum(times)/60,smoke_minutes=sum(times)/20/60,
         estimate_only=True,retries_excluded=True,simulations_started=0))


def document():
    p=verify();v=json.loads((OUT/'preparation/validation.json').read_text())
    assert v['protocol_sha256']==sha256_file(HERE/'protocol.json')
    base=f'cd {ROOT} && '
    env='env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase40p.campaign'
    commands=dict(smoke=base+f'nohup {env} --smoke > ../artifacts/isaac6/phase40p_smoke_01.log 2>&1 < /dev/null &',
                  main=base+f'nohup {env} --with-smoke > ../artifacts/isaac6/phase40p_01.log 2>&1 < /dev/null &',
                  status=base+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase40p.campaign --status')
    save(OUT/'preparation/commands.json',dict(commands,executed=False))
    text=f'''# Phase40-P 준비

**FROZEN / 실행0회.** 테스트{v['tests']}개, 본20조합·smoke1조합 dry-run 통과. 여유 공간 {v['disk_free_bytes']/1e9:.1f}GB. Protocol SHA256 `{v['protocol_sha256']}`.

OURS-N은 Phase38 OURS의 결정·넘김·RECOVER·C0-NA·평가기·jitter를 재사용한다. R2는39-O3가 재사용한 VE, R3는VN 그대로이며, CLR soft 지도/가중치도 동결한다. R3 hard/certificate/기하 지도만 occupied OR (B반경0.6m 내 unknown)이다. B행 제외와 낮은 c_B 탈출 기준은39-O2/3와 같다. A* 없음.

계산 중에는 Phase38 OURS-DETOUR의 SAFE·EC 대안·RECOVER 동작을 유지한다. 우회 job 때문에 정지를 명령하지 않지만, EC 대안이 없거나 회복 동작이면 정지할 수 있고 실제 대기 정지 시간을 따로 센다. dispatch 후54tick을 지나 처음 오는8tick 제어격자의 예측 pose로 풀고, 조기 결과도 그 tick에서만 실제 pose·최신 depth EC를 통과해야 설치한다. 지나간 결과는 폐기하며 R2의 FRESH SUPERSEDED도 유지한다. 예측에는 현재 실행기 상태/명령과 동결72Hz 적분만 사용한다.

탈출 EC는 설치 시 동결72Hz rollout에서 경로 위 투영 호장이 `s_esc=(0.03−job c_B)/0.5`에 처음 도달한 시각을 t_esc로 쓴다. 경로 끝이 s_esc보다 앞이면 동결 끝점 도달 시각을 쓴다. 2초 안에 도달하지 않으면 **거부하지 않고2초 상한**을 쓰며 최초 rollout 전 구간은c0로 검사한다. `c0=설치 시 base exact clearance−0.005`와 `설치 시각+t_esc` 절대시각을 job별로 고정한다. 재검사에서는 최신 지도와 남은 시간만 쓰고, 마감 이후는동결0.025 기준이다. 같은 job 재설치로 연장하지 않는다. 탈출 설치·연속 탈출 설치·탈출 중 재검사 거절·t_esc분포·2초 상한 적용 건수를 보고한다.

SLW,LC,L2,H1,H2 ×217–220, OURS-N20회. Phase38 OURS-DETOUR(15/20도착), OURS, ASTAR+EC의 같은20쌍을 재사용한다(실행일 차이). PILOT_OK=충돌≤1 AND 도착≥14, GRAPH_GAIN=도착≥17 AND OURS-N만 도착≥3쌍. McNemar exact는 참고; 둘 다 도착한 짝의 시간·주행거리 차이, 우회/탈출 설치, 대기 정지 시간을 자동 report한다. 저장v2,30GB reserve, 본실험 기술실패1회재시도·cache정리·잠금·재개를 유지한다.

사용자가 실행: 아래 본 campaign 명령 하나는 smoke H1/217/OURS-N1회(본 결과 제외,자동재시도 없음)를 먼저 수행하고 기술 PASS 후 본20회로 진행한다. 이미 완료된 smoke와 run은 재개 시 반복하지 않는다. 이 준비 작업에서는 둘 다 실행하지 않았다.

```bash
{commands['main']}
```
```bash
{commands['status']}
```
smoke만 따로 실행할 때의 선택 명령(위 본 campaign을 쓰면 별도 실행 불필요):
```bash
{commands['smoke']}
```

본실험 완료 후 `/usr/bin/python3 + PYTHONPATH=research`로 `docs/PHASE40P_RESULTS.md`, `research/results/phase40p/`를 자동 생성·commit·push한다. Phase38 저장 launcher 시간 기준 본20회 약56분,smoke 약3분(재시도 제외 추정; preparation/runtime_estimate.json).
'''
    (ROOT/'docs/PHASE40P_PREP.md').write_text(text)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');ap.add_argument('--document',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
    if a.document:document()


if __name__=='__main__':main()
