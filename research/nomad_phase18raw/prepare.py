"""Registration after explicit goal-rule choice; no new simulation or replay."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from nomad_phase18 import config as original
from nomad_phase26.storage import atomic_json
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,INDICES,registered_order,verify_sources,protocol

def freeze():
    goal_rule='PHASE18_GEOMETRIC'
    assert not RUN_ROOT.exists();base=original.verify_sources();p=copy.deepcopy(base)
    p.update(status='FROZEN',phase='18-RAW',experiment_label='EXPLORATORY',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),
        main_indices=list(INDICES),main_max=24,main_order=registered_order(),raw_goal_rule=goal_rule,raw_comparison_alpha=base['statistics']['main_alpha'])
    p['raw_definition']=dict(sample=0,executor='Frozen Phase18 PP+CURV;lookahead.25,maxv.3,omega.4,original acceleration/plant',depth_filter=False,graph=False,EC=False,
        recovery=False,SP=False,alignment=False,endpoint_latch=False,waypoint_timeout_s=1.,
        depth_render_and_map='Retained exactly as Phase18;never queried for RAW selection/control',goal_rule=goal_rule,success_radius_m=.3,
        checkpoint='Exact Phase18 first saved72Hz pose meeting scene checkpoint axis/threshold',
        bootstrap='Phase18 paired seed clusters across scenes,20000 draws,seed20261030;RAW minus comparator;missing checkpoints not imputed',
        scope='Posthoc additional RAW baseline on same seeds,run on a different date;exploratory only',retries=0,
        assets='Original scene/reference/topomap/gates reused with original hashes;no new reference/gate/smoke')
    p['smoke']=dict(enabled=False,reason='User forbids simulation in preparation;plumbing dry-run only')
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    extra=['research/nomad_phase18/config.py','research/nomad_phase18/execution.py','research/nomad_phase18/launch.py','research/nomad_phase18/campaign.py',
        'research/nomad_phase18/metrics.py','research/nomad_phase18/statistics.py','research/nomad_phase17/simulator.py','research/nomad_phase17/metrics.py',
        'research/nomad_phase4c/execution.py','research/nomad_phase4c/plant.py','research/nomad_phase0/chunk_execution.py','research/nomad_phase18/protocol.json',
        'research/results/phase18/runs.json']
    p['phase18_statistics_reference']=copy.deepcopy(base['statistics'])
    p['statistics']=dict(bootstrap_replicates=20000,bootstrap_seed=20261030,resampling=base['statistics']['resampling'],alpha=base['statistics']['main_alpha'],scope='EXPLORATORY ONLY',difference='RAW minus comparator',missing='paired observed valid checkpoints only,no imputation')
    p['extra_frozen_sha256']={f:sha256_file(ROOT/f) for f in extra}
    atomic_json(HERE/'protocol.json',p);verify_sources()

def validate():
    p=verify_sources();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-phase18raw-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase18raw.test_raw','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase18raw.campaign','--dry-run'],cwd=ROOT,env=env,text=True));assert dry['planned']==24 and dry['navigation_started']==0
    atomic_json(folder/'dry_run.json',dry)
    subprocess.run(['/usr/bin/python3','-c',"import sys;import nomad_phase18raw.launch,nomad_phase18raw.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=24,simulations_started=0,real_replays=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),runtime_source_sha256=p['source_sha256'],disk_free_bytes=shutil.disk_usage(ROOT).free)
    atomic_json(folder/'validation.json',v)
    from .report import generate
    generate();document(v);print(json.dumps({k:v for k,v in v.items() if k!='runtime_source_sha256'}))

def document(v):
    p=protocol();prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase18raw.campaign > ../artifacts/isaac6/phase18raw_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase18raw.campaign --status'
    atomic_json(OUT/'preparation/commands.json',dict(campaign=cmd,status=status,executed=False))
    from nomad_phase18.report import table
    rules='종료 판정은 Phase18과 동일(0.3m)'
    lines=['# Phase18-RAW 준비',table([dict(status='FROZEN; NOT_RUN',runs=24,method='NOMAD_RAW',scenes='SLW / LC / CL',seeds='66–73',delay_s=.75,goal_rule=p['raw_goal_rule'],protocol_sha256=v['protocol_sha256'])]),
        'Phase18 동결 scene·reference·Topomap·게이트 결과·checkpoint 정의와 PP+CURV 실행기를 재사용한다. SP·출발 정렬·HMM·ENDPOINT latch·EC는 적용하지 않는다. depth 렌더/지도는 동일하게 켜지만 경로 선택에 쓰지 않으며,관측 pose에 고정된 sample0의 원8점을 그대로 PP가 따라간다.',rules,
        f"checkpoint 차이는 RAW−OURS(GRAPH-depth-CLR),RAW−RTC-hard다. 동일 seed의 장면 클러스터 bootstrap20,000회,seed20261030,신뢰수준{100*(1-p['raw_comparison_alpha']):.5f}%를 고정한다. 관측된 기술PASS checkpoint 쌍만 사용하고 결측은 대체하지 않는다. 다른 날짜의 추가 기준선이므로 탐색적 비교이며확인 실험 라벨을 붙이지 않는다.",
        'Phase18과 동일하게 기술 실패는 재시도하지 않고 계속한다. 원본 run을 덮어쓰지 않는 단계별 재개·로그·짧은socket검사를 재사용한다. 새 gate/reference/smoke는 없다. 디스크30GB미만이면 새 run 전에 중단한다. depth원본 저장 형식도 Phase18 그대로다.',
        table([{k:x for k,x in v.items() if k!='runtime_source_sha256'}]),
        '시뮬레이션·추론·실제 로그 재생은 실행하지 않았다. 종료 후 docs/PHASE18_RAW_RESULTS.md 및 research/results/phase18raw/를 자동 생성·commit·push한다. 기존 Phase18 코드·결과·raw는 수정하지 않는다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/phase18raw_01.log`','본 실행 명령(미실행):','`'+cmd+'`']
    (ROOT/'docs/PHASE18_RAW_PREP.md').write_text('\n\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
