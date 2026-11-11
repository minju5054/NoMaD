"""Freeze sources/assets, run unit and launcher dry-run checks; never simulate."""
import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime,timezone
from pathlib import Path
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from nomad_j1.common import scene_config,checkpoint_spec
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,METHOD,INDICES,order,verify,protocol

def freeze():
    assert not RUN_ROOT.exists(),'Do not change registration after any run starts'
    from nomad_phase18.config import verify_sources
    old=verify_sources();sources={};assets={}
    for path in list(old['protected_sha256'])+list(old['reused_sha256']):
        f=Path(path);f=f if f.is_absolute() else ROOT/f
        if f.is_relative_to(ROOT):sources[str(f.relative_to(ROOT))]=sha256_file(f)
        else:assets[str(f)]=sha256_file(f)
    families=['nomad_j0','nomad_j1','nomad_phase18','nomad_phase18raw','nomad_phase17','nomad_phase16','nomad_phase15b',
              'nomad_phase15','nomad_phase12','nomad_phase5','nomad_phase4c','nomad_phase4','nomad_phase3_stage2',
              'nomad_h1v2']
    for family in families:
        for f in (ROOT/'research'/family).iterdir():
            if f.suffix not in ('.py','.json') or (f.parent==HERE and f.name=='protocol.json'):continue
            sources[str(f.relative_to(ROOT))]=sha256_file(f)
    extra=['nomad_phase26/config.py','nomad_phase26/protocol.json','nomad_phase26/scenes.py','nomad_phase26/rendering.py',
           'nomad_phase26/simulator.py','nomad_phase26/launch.py','nomad_phase26/storage.py','nomad_phase24/storage.py',
           'nomad_phase24r/geometry.py','nomad_phase28/telemetry.py','nomad_phase38/scenes.py',
           'nomad_phase0/s0_batch.py','nomad_phase0/chunk_execution.py','nomad_phase0/chunk_report.py',
           'nomad_phase0/chunk_pilot_protocol.json','nomad_phase0/pure_pursuit.py',
           'nomad_isaac/async_runtime.py','nomad_isaac/async_core.py','nomad_isaac/worker.py','nomad_isaac/common.py',
           'nomad_isaac/clearance.py','nomad_isaac/topomap.py','nomad_isaac/simulator.py','nomad_isaac/delivery_delay.py']
    for name in extra:
        f=ROOT/'research'/name;sources[str(f.relative_to(ROOT))]=sha256_file(f)
    scenes={}
    for scene in SCENES:
        c,manifest=scene_config(scene);f=Path(manifest);assets[str(f)]=sha256_file(f)
        top=json.loads(f.read_text())
        for n in top['nodes']:
            image=f.parent/n['rgb_file'];assets[str(image)]=sha256_file(image)
        scenes[scene]=dict(topomap=str(f),topomap_sha256=assets[str(f)],checkpoint=checkpoint_spec(scene),
            start_pose=c['start_pose'],goal_pose=c['goal_pose'],geometry={k:c[k] for k in ('corridor','obstacles','agent_radius_m')},
            dynamic_obstacle=c.get('dynamic_obstacle'),spawn=c.get('phase26_spawn'),h1v2_spec=c.get('h1v2'))
    checkpoint=ROOT.parent/'artifacts/checkpoints/nomad.pth';assets[str(checkpoint)]=sha256_file(checkpoint)
    p=dict(phase='J0',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),method=METHOD,indices=list(INDICES),
        delays_s=[0.,.75],planned=20,main_order=order(),scenes=scenes,source_sha256=sources,asset_sha256=assets,
        execution=dict(base='Phase18',controller='protected PP geometry + Phase18 CURV, lookahead .25, vmax .3, |omega|<=.4',
            timing_hz=[4,9,72],expiry_s=1.,goal='true pose distance <=.3m; no closest_node stop',localization='official argmin closest_node/subgoal',
            latency='world-anchor at observed pose, choose by suffix at actual application B; unchanged uniform result-delivery delay',
            graph='frozen Phase17/18 ClearanceGraph factors/solver/initialization/async scheduler; SUPERSEDED/STALE/expiry preserved',
            depth='Phase18 V1, unknown free, sigma=.01*d^2; original map publication/storage',
            no_safe='retain current path/progress, without refreshing its one-second receipt clock; no recovery/STOP_WAIT special rule',
            endpoint='latch protected PP endpoint_stop until a new SAFE or accepted Graph path is installed; zero command',
            EC=False,HMM=False,NET=False,recovery=False,stop_wait_special=False,oracle_for_control=False),
        screening=dict(zero_success_required=2,checkpoint_mean_increase_strict=True,maximum_selected=3,
            rank='zero-delay checkpoint mean ascending; ties frozen scene order',missing='both seeds must be valid and have checkpoints in both conditions; no imputation'),
        session_budget_s=3600,time_goal='20runs within about1hour; no new run at budget, finish current then partial report; resume allowed',
        technical_retries=0,technical_rule='Phase18 one attempt; record failure and continue. Preserve interrupted attempt, never overwrite',
        disk_reserve_bytes=30_000_000_000,simulation_started_during_prep=False)
    atomic_json(HERE/'protocol.json',p);verify()

def estimate():
    # Only launch-completion metadata; no simulation or trajectory replay.
    import numpy as np
    rr=[]
    for folder in ('phase53p_01','h1v2_trial_01'):
        parent=ROOT.parent/'artifacts/isaac6'/folder/'main'
        files=list(parent.glob('*/attempt1/launch_complete.json'))+list(parent.glob('*/launch_complete.json'))
        for f in files:
            r=json.loads(f.read_text())
            if r.get('launcher_wall_s') is not None:rr.append(float(r['launcher_wall_s']))
    return dict(source='stored Phase53-P/H1-v2 trial launcher durations; different executor, estimate only',n=len(rr),
        per_run_median_s=float(np.median(rr)) if rr else None,per_run_p95_s=float(np.quantile(rr,.95)) if rr else None,
        total20_at_median_min=float(20*np.median(rr)/60) if rr else None,total20_at_p95_min=float(20*np.quantile(rr,.95)/60) if rr else None,
        caveat='Includes startup; J0 audit/report/archive costs can differ.1h is target,not guarantee; partial remains resumable.')

def validate():
    p=verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    run=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_j0.test_j0','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(run.stdout+run.stderr)
    assert run.returncode==0,run.stderr[-6000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_j0.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    plans=[]
    for j in dry['jobs']:
        plans.append(json.loads(subprocess.check_output([*j['argv'],'--dry-run'],cwd=ROOT,env=env,text=True)))
    assert len(plans)==20 and all(x['simulations_started']==0 for x in plans)
    subprocess.run(['/usr/bin/python3','-c',"import sys;import nomad_j0.launch;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',run.stderr).group(1)),actual_launcher_dry_runs=20,simulations_started=0,
           inference_started=0,graph_solves_started=0,protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    atomic_json(folder/'validation.json',v);atomic_json(folder/'dry_run.json',dict(campaign=dry,launches=plans))
    timing=estimate();atomic_json(folder/'time_estimate.json',timing)
    from .report import generate
    generate();document(v,timing)
    print(json.dumps(v))

def document(v,timing):
    from nomad_phase18.report import table
    p=protocol()
    command=f'cd {ROOT} && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_j0.campaign > ../artifacts/isaac6/j0_01.log 2>&1 < /dev/null &'
    status=f'cd {ROOT} && PYTHONPATH=research /usr/bin/python3 -m nomad_j0.campaign --status'
    lines=['# J0 준비 — 장면 선별',table([dict(status='FROZEN / NOT_RUN',runs=20,method=METHOD,seeds='221–222',order='0s 10 → 0.75s 10',protocol_sha256=v['protocol_sha256'])]),
        'J1 전체 실험은 구현·실행하지 않았다. 재사용할 공통부만 research/nomad_j1/에 추가하고, J0 한 방법(OURS-noEC)을 연결했다. 기존 동결 코드·결과는 변경하지 않는다.',
        '종료 판정은 Phase18과 동일(0.3m). 공식 NoMaD closest_node와 subgoal을 사용하지만 목표 노드 기반 종료·HMM·NET은 없다. world 좌표는 관측 pose에 고정하고 적용 B의 suffix 잔여 길이가 가장 긴 SAFE 후보를 쓴다.',
        '실행은 Phase18 PP+CURV(lookahead0.25m,vmax0.3,|ω|≤0.4,4/9/72Hz),1초 만료다. SP·출발 정렬·회전 회복·STOP_WAIT 특수처리·EC 없음. SAFE가 없으면 현재 경로와 기존 유효시간만 유지한다. ENDPOINT는 기존 PP 끝점 판정에 걸리면 새 경로 설치까지0명령을 유지한다.',
        'Graph는 Phase17/18 ClearanceGraph(FlagGraphV4+depth hard+CLR soft)와 원 CPU worker·수락·폐기 규칙을 그대로 호출한다. 즉 FRESH SAFE 원경로를 즉시 설치하고 비동기 보정 결과는 기존 SUPERSEDED/STALE/만료 검사 후 적용한다. 새 factor·튜닝은 없다. NoMaD에는 RGB만 입력하며 지도 unknown은 기존처럼 free다.',
        table([dict(scene=s,axis='xy'[p['scenes'][s]['checkpoint']['axis']],**{k:p['scenes'][s]['checkpoint'][k] for k in ('box_id','threshold_m','formula')}) for s in SCENES]),
        'H1-v2는 y=1.10 돌발 상자의 +y 먼 면+0.30=1.60m. H2는 실제 두 번째 spawn 상자의 center_x+회전을 고려한 x투영 반폭+0.30을 동결하며 미생성이면 checkpoint 미측정이다. run별 임계좌표·시작점에서의 진행축 거리를 기록한다. 방법이1개라 방법 간 좌표 차이는 N/A(범위0), 동일seed 지연 조건 간 차이는 별도 보고한다.',
        '선별: 0s 성공2/2 AND 0.75s checkpoint 평균>0s 평균. 양 조건 각2개가 모두 관측된 장면만 비교(결측 대체 없음). 통과 장면의 0s 평균이 짧은 순 최대3개; 미달이면 통과 장면만. 동률은 H1-v2·SLW·H2·LC·CL 순서다.',
        table([v]),table([timing]),
        '1시간은 목표다. 기존 유사 run 중앙값 기준 추정과 p95 기준 추정을 함께 기록했다. 세션1시간이 지나면 진행 중 run을 마치고 새 run 전 중단·PARTIAL 보고하며 같은 명령으로 재개한다. 두 lock(전역/해당root),짧은socket,원자적state,디스크30GB하한,run종료cache정리를 사용한다. Phase18처럼 기술 실패 재시도는 없고 원자료를 보존한다.',
        '완료/시간중단 시 docs/J0_RESULTS.md·research/results/j0/ 보고서 자동 생성·commit·push. 본 실행·smoke·실제 재풀이 없음.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/j0_01.log`','본 실행(미실행):','`'+command+'`']
    (ROOT/'docs/J0_PREP.md').write_text('\n\n'.join(lines)+'\n')
    atomic_json(OUT/'preparation/commands.json',dict(campaign=command,status=status,executed=False))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()

if __name__=='__main__':main()
