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
from .config import ROOT,HERE,OUT,RUN_ROOT,SMOKE_ROOT,SCENES,METHODS,INDICES,ORDER_SEED,order,scene_config,checkpoint_spec,verify
from .depth import registration

def freeze():
    assert not RUN_ROOT.exists(),'Cannot refreeze after main execution starts'
    from nomad_j0.config import verify as base_verify
    old=base_verify();sources=dict(old['source_sha256']);assets=dict(old['asset_sha256']);scenes={}
    for family in ('nomad_j1','nomad_phase18raw','nomad_phase8','nomad_phase7','nomad_phase52ec','nomad_phase32o'):
        for f in (ROOT/'research'/family).glob('*.py'):sources[str(f.relative_to(ROOT))]=sha256_file(f)
    for name in ('nomad_h1v3/config.py','nomad_h1v3/scene.py','nomad_h1v3/scene.json','nomad_slwv2/config.py',
                 'nomad_slwv2/protocol.json','nomad_phase18/metrics.py','nomad_phase32/policy.py'):
        f=ROOT/'research'/name;sources[str(f.relative_to(ROOT))]=sha256_file(f)
    for s in SCENES:
        c,manifest=scene_config(s);f=Path(manifest);assets[str(f)]=sha256_file(f);m=json.loads(f.read_text())
        for n in m['nodes']:
            image=f.parent/n['rgb_file'];assets[str(image)]=sha256_file(image)
        scenes[s]=dict(topomap=str(f),topomap_sha256=sha256_file(f),checkpoint=checkpoint_spec(s),sdf_registration=registration(c),
            start_pose=c['start_pose'],goal_pose=c['goal_pose'])
    decisions={}
    for key,file in [('J0','research/results/j0/decision.json'),('H1-v3','research/results/h1v3_j0/decision.json'),('SLW-v2','research/results/slwv2_j0/decision.json')]:
        f=ROOT/file;assets[str(f)]=sha256_file(f);decisions[key]=json.loads(f.read_text())
    p=dict(phase='J1',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),scenes=scenes,
        indices=list(INDICES),main_order=order(),planned=195,order_seed=ORDER_SEED,block_size=15,session_budget_s=5.5*3600,
        budget='Finish an already-started seed block; do not start a new seed after19800s; same command resumes',
        source_sha256=sources,asset_sha256=assets,screening_results=decisions,
        inclusion='LC passed J0; H1-v3 and SLW-v2 failed screen but preregistered for sudden-obstacle/narrow-corridor coverage',
        execution=dict(base='J0 Phase18 PP/CURV',goal_radius_m=.3,goal_pose_truth=True,node_based_stop=False,waypoint_expiry_s=1.,
            depth='V1 + J0 scene SDF registration',endpoint_latch=True,NoMaD='official closest_node/subgoal',HMM=False,NET=False,recovery=False,STOP_WAIT_special=False,
            RAW='Phase18-RAW sample0 + common endpoint latch',RTC='Phase18 RTC-hard generation and SAFE selection; common no recovery/special fallback',
            OURS_noEC='exact J0 Execution object',OURS='same SAFE selection/frozen CLR worker + install/periodic EC',
            OURS_noGRAPH='same SAFE selection/install/periodic EC, no Graph',
            Graph='same8-point frozen factors/options,async stale/superseded/expiry; SAFE raw interim and graph output independently EC-gated'),
        EC=dict(methods=['OURS','OURS-noGRAPH'],period_ticks=36,apply_at='next9Hz control tick',
            tail='Phase52: endpoint or2s,then frozen stop_command until0; same continuous occupied-site footprint certificate>=.025',
            controller='actual Phase18 PP/CURV adapter; noSP or start alignment',installation_reject='retain old path/progress/receipt expiry',
            periodic_reject='retain path,stop_command(.5m/s2,omega0);remain blocked until new install passes',
            alternate_candidates=False,slow_tier=False,recovery=False),
        statistics=dict(primary=['OURS-RTC checkpoint mean paired difference','OURS vs OURS-noEC safety exact McNemar'],
            bootstrap_repetitions=20000,bootstrap_seed=20261030,clusters='seed across3scenes',CI=.95,
            bootstrap_p='two-sided centered null; (1+count(|boot-mean|>=|mean|))/(20000+1)',
            McNemar='two-sided exact binomial discordant pairs',family='Holm two tests,alpha.05',
            missing='valid observed matched checkpoint pairs only; no imputation',interim='completed seed blocks only; 중간 결과, 판정 보류'),
        smoke=dict(scene='LC',method='OURS',index=95,delay=.75,timeout_sim_s=30,excluded=True,count=1),
        technical_rule='first main technical failure stops; one explicit plumbing-fix retry allowed; all other runs one attempt,continue',
        disk_reserve_bytes=30_000_000_000,cache_cleanup=True)
    atomic_json(HERE/'protocol.json',p);verify()

def validate():
    folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_j1.test_j1','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-7000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_j1.campaign','--dry-run'],cwd=ROOT,env=env,text=True));atomic_json(folder/'dry_run.json',dry)
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),launcher_dry_runs=195,main_runs_started=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    atomic_json(folder/'validation.json',v)
    from .report import generate
    generate();document(v);print(json.dumps(v))

def document(v):
    from nomad_phase18.report import table
    cmd=f'cd {ROOT} && setsid nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_j1.campaign > ../artifacts/isaac6/j1_01.log 2>&1 < /dev/null &'
    status=f'cd {ROOT} && PYTHONPATH=research /usr/bin/python3 -m nomad_j1.campaign --status'
    p=verify();lines=['# J1 사전 등록',table([v]),
        'SLW-v2·H1-v3·LC × seed231–243 ×5방법=195회. 15회 seed블록 안 순서만 RNG20261112로 섞고, 5.5h 이후 새seed블록을 시작하지 않는다. 진행 중 블록은 끝내고 중간 결과를push하며 동일 명령으로 재개한다. 본 실행은 원래 저장소 cwd에서만 허용한다.',
        'LC는 J0 통과. H1-v3·SLW-v2는 미달이나 돌발 장애물·좁은 통로 평가용으로 사전 포함. scene·Topomap·선별결과 hash를 protocol에 기록했다.',
        table([dict(scene=s,**p['scenes'][s]['checkpoint']) for s in SCENES]),
        '실행기는 Phase18 PP/CURV이고 목표0.3m 참위치 종료, 공식NoMaD argmin closest/subgoal·1s 만료·지연보정·V1 depth·SDF fix·ENDPOINT latch 공통이다. 회복·STOP_WAIT 특수처리·HMM/NET은 없다. OURS-noEC는 기존 J0 객체 그대로다. RAW는 Phase18-RAW 재사용+공통latch,RTC는 Phase18 생성/SAFE를 재사용한다.',
        'EC는 OURS/OURS-noGRAPH만 설치시+36tick 주기로 검사한다. 다음9Hz tick에 거절을 적용한다. 설치거절은 기존 경로·진행도·만료시각 유지. 주기거절은 같은경로에서 frozen stop_command로감속,새경로가EC통과해설치되어야재개한다. 회복·대체후보·0.1m/s 없음. 원SAFE의EC거절은Graph시도를억제하지 않으며Graph결과도설치전EC검사한다.',
        '52-P 대비: 제동꼬리/정확swept/주기는같고 컨트롤러는공통Phase18 PP/CURV를전달하며사용자지시에따라대체후보/0.1/STOP_WAIT를제거한다. ENDPOINT·2s이후실제stop_command로정지까지검사한다.',
        '주비교2개: OURS−RTC checkpoint평균짝차 seed클러스터bootstrap20,000회(seed20261030),양측95% CI와중심화bootstrap p; OURS대noEC 안전실패(충돌OR벽침범) exact McNemar양측p. Holm α=.05. 주비교는완료seed블록의기술PASS관측짝만,결측대체없음. 중간report는「중간 결과, 판정 보류」로명시한다.',
        'LC/OURS/seed95/30s smoke1회만결과제외. 첫main RUN_DONE을1회확인하며기술실패면중지·배관수정1회재실행만허용한다. root/global lock,30GB디스크하한,run후cache정리. report는systemPython으로자동commit/push한다.',
        '진행확인: `'+status+'`','로그: `../artifacts/isaac6/j1_01.log`','실행/재개 명령:','`'+cmd+'`']
    (ROOT/'docs/J1_PREP.md').write_text('\n\n'.join(lines)+'\n');atomic_json(OUT/'preparation/commands.json',dict(campaign=cmd,status=status))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()

if __name__=='__main__':main()
