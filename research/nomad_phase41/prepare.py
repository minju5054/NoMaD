"""Freeze and minimum verification only. No simulator/worker/inference run."""
import argparse,json,os,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from .config import ROOT,HERE,OUT,RUN_ROOT,INDICES,SCENES,verify


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def freeze():
    assert not RUN_ROOT.exists()
    old=json.loads((ROOT/'research/nomad_phase38/protocol.json').read_text())
    refs={f:sha256_file(ROOT/f) for f in ('research/nomad_phase38/protocol.json','research/nomad_phase40r2/protocol.json','research/results/phase38/runs.json','deployment/src/navigate.py')}
    rows=json.loads((ROOT/'research/results/phase38/runs.json').read_text());baselines=[]
    for r in rows:
        if r['method']!='OURS-DETOUR' or r['index'] not in INDICES:continue
        file=Path(r['output'])/'summary.json';summary=json.loads(file.read_text());refs[str(file)]=sha256_file(file)
        arrival=bool(summary['goal_entry'])
        baselines.append(dict(r,success_0p3=r['success'],success_1p0=r['success'],
            wrong_stop=None,declared_arrival=None,timeout_without_declaration=r['termination'] in ('simulation_timeout','navigation_wall_timeout'),
            stop_distance_m=summary['final_goal_distance_m'] if arrival else None,final_goal_distance_m=summary['final_goal_distance_m']))
    assert len(baselines)==15
    save(OUT/'preparation/baselines.json',baselines)
    refs['research/results/phase41/preparation/baselines.json']=sha256_file(OUT/'preparation/baselines.json')
    p=dict(status='FROZEN',phase='41',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=['OURS-DETOUR'],
        indices=list(INDICES),scenes=old['scenes'],checkpoint_sha256=old['checkpoint_sha256'],placements=old['placements'],
        main_order=[dict(scene=s,index=i,method='OURS-DETOUR') for i in INDICES for s in SCENES],smoke=dict(enabled=False),
        stop=dict(option='nomad_goal_stop',enabled=True,condition='topomap.closest_node==topomap.goal_node',
            official_source='deployment/src/navigate.py: reached_goal = closest_node == goal_node',
            application='Every controller-delivered inference at first72Hz poll, no wait for9Hz/FRESH; D750 unchanged',
            command=[0.,0.],geometric_goal_stop='Disabled only while option is enabled; goal radius/config unchanged and distance evaluation only',
            terminal_result='Do not install its waypoint; do not declare on post-termination drained inference',
            collision_precedence='Frozen collision/corridor stops retain priority at the same integration tick'),
        outcomes=dict(success='declared arrival AND distance<=0.5m AND collision==False',auxiliary_distances_m=[.3,1.],
            wrong_stop='declared arrival AND distance>0.5m',timeout='no declared arrival AND simulation_timeout/navigation_wall_timeout'),
        execution=dict(serial=True,technical_retries=1,cache_cleanup=True,disk_min_bytes=30_000_000_000,storage_version=2),
        reference_hashes=refs,frozen_sources={**old['frozen_sources'],**old['source_sha256'],
            **{str(f.relative_to(ROOT)):sha256_file(f) for f in (ROOT/'research/nomad_phase40r2').glob('*.py')},
            'research/nomad_isaac/async_runtime.py':sha256_file(ROOT/'research/nomad_isaac/async_runtime.py'),
            'research/nomad_isaac/async_core.py':sha256_file(ROOT/'research/nomad_isaac/async_core.py')},
        source_sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')})
    save(HERE/'protocol.json',p);verify()


def validate():
    verify();env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1');folder=OUT/'preparation'
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase41.test_phase41','-v'],cwd=ROOT,env=env,capture_output=True,text=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-3000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase41.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==15 and dry['simulations_started']==0 and not dry['smoke'];save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_phase41.launch,nomad_phase41.campaign;assert 'scipy' not in sys.modules"],cwd=ROOT,env=env,check=True)
    import re
    result=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=15,smoke=False,simulations_started=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',result)
    prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase41.campaign > ../artifacts/isaac6/phase41_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase41.campaign --status'
    save(folder/'commands.json',dict(campaign=cmd,status=status,executed=False))
    fields=[('등록','FROZEN'),('본 실행','OURS-DETOUR ×SLW,LC,L2,H1,H2 ×217,219,220 =15회'),('smoke','생략'),
        ('공통 옵션','nomad_goal_stop: closest_node==goal_node 수신 시 v=ω=0,즉시종료'),
        ('시점','D750 유지;결과 수신 첫72Hz tick,9Hz 제어까지 기다리지 않음'),
        ('기존 거리 종료','옵션ON에서만 비활성;목표거리 평가 전용'),
        ('주 성공','declared arrival AND 목표거리≤0.5m AND 충돌없음'),('보조','0.3m/1.0m 성공,잘못된정지>0.5m,선언없이시간초과'),
        ('비교','같은15쌍의 Phase38 OURS-DETOUR,기존0.3m규칙·다른실행일'),
        ('검증',f"테스트{result['tests']}개 PASS /15조합 dry-run PASS"),('실행횟수',0),
        ('여유공간',f"{result['disk_free_bytes']/1e9:.1f}GB"),('Protocol SHA256',result['protocol_sha256'])]
    (ROOT/'docs/PHASE41_PREP.md').write_text('| 항목 | 결과 |\n|---|---|\n'+''.join(f'| {a} | {b} |\n' for a,b in fields))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()


if __name__=='__main__':main()
