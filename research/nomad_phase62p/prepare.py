"""Freeze one goal factor and validate plumbing/algebra without navigation or solves."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,registered_order,verify

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def freeze():
    assert not RUN_ROOT.exists()
    original=json.loads((ROOT/'research/nomad_phase61p/protocol.json').read_text());p=copy.deepcopy(original)
    p.update(phase='62-P',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),main_order=registered_order(),smoke=dict(enabled=False))
    p['method_definitions']={'UG-GOAL':'Phase61 CUT execution/rules plus frozen Phase55 forward-only U-Graph and one terminal XY goal factor;EC-tail accepted U replaces CUT,otherwise original CUT fallback.'}
    p['u_goal']=dict(factor='r=(p_N-goal_xy)/0.3;cost=sum(r²),weight1,analytic gradient via frozen terminal sensitivity',sigma_m=.3,
        target='min(latest delivered chunk observation-time oracle closest_node+2,goal_node)',target_hold='fixed between chunks including periodic replans',
        initial_state='actual pose,v,omega at synchronous solve;no predicted B',prior='last actually installed U solution with frozen Phase55 time-overlap interpolation',
        solver='Phase55 Graph(0<=v<=.3),all original factors/hard constraints/11starts/4process/maxiter100/ftol1e-8/feasibility1e-7 unchanged',
        trigger='chunk arrival or Phase55 independent36tick planning clock;next9Hz control tick actual state;coalesce simultaneous triggers',
        execution='Phase61 CUT PP/SP with ENDPOINT latch,alignment/recovery/full-.1-STOP fallback and1s expiry;NO Phase55 HOLD',
        certificate='same latest-map Phase61 EC-tail;failed/no hard-feasible U uses CUT paths/fallback;recovery not interrupted',
        stationary='frozen Phase55 zero-length XY endpoint STOP (no fake path);not direct Graph angular tracking',
        watchdog='original Phase55 RPC300s technical watchdog and existing launcher600s;no new solver deadline')
    p['report_definitions']['outputs']='Six UG-GOAL runs;Phase61 same seed CUT/CONS/CONS+G18 alongside,outcomes/passage/arrival/stopped,U adoption,accepted U length median,and one extra actual solve-pose to target-node distance median. Topdown/run with forced PNG staging.'
    p['report_definitions']['baselines']='Reuse published Phase61 same scene/seed outcomes;different execution day;no historical replay.'
    p['report_definitions']['prepared']='Six launcher/config dry-runs,goal Jacobian/unchanged constraints/seeds,latched CUT fallback and target-clock plumbing;no simulation or solver execution.'
    p['frozen_sources']={**original['frozen_sources'],**original['source_sha256']}
    for name in ('nomad_phase55p/graph.py','nomad_phase55p/runtime.py','nomad_phase55p/worker.py','nomad_ugraph/graph.py','nomad_ugraph/dynamics.py','nomad_ugraph/certificate.py'):
        f=ROOT/'research'/name;p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    p['reference_hashes']=dict(original['reference_hashes'])
    for name in ('research/nomad_phase61p/protocol.json','research/nomad_phase55p/protocol.json','research/results/phase61p/runs.json'):
        p['reference_hashes'][name]=sha256_file(ROOT/name)
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')};save(HERE/'protocol.json',p);verify()

def validate():
    verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-phase62p-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase62p.test_phase62p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase62p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==6 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run(['/usr/bin/python3','-c',"import sys;import nomad_phase62p.launch,nomad_phase62p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=6,simulations_started=0,solver_runs=0,real_replays=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',v)
    from .report import generate
    generate();document(v);print(json.dumps(v))

def document(v):
    p=verify();prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase62p.campaign > ../artifacts/isaac6/phase62p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase62p.campaign --status'
    save(OUT/'preparation/commands.json',dict(campaign=cmd,status=status,executed=False))
    lines=['# Phase62-P 준비 — UG-GOAL / oracle 분석용',table([dict(status='FROZEN; NOT_RUN',runs=6,method='UG-GOAL',scenes='H1-v2 / SLW / H2',seeds='229,230',delay_s=.75,protocol_sha256=v['protocol_sha256'])]),
        'Phase61-P와 같은 oracle 관측 시점 위치추정·D075·ENDPOINT latch·EC 제동꼬리·PP/SP·정렬·회복·1s 만료를 유지한다. Phase55 HOLD는 연결하지 않는다. oracle 위치추정과 Topomap pose는 분석용 조건이다.',
        '새 factor는 r_goal=(p_N−목표노드XY)/0.3m의 제곱합(가중1) 하나다. 목표는 사용자 확정대로 최근 도착 chunk의 관측 시점 oracle 노드+2,마지막 노드 clamp다. 주기 재풀이 때 실제 pose가 변해도 다음 chunk가 오기 전에는 목표 노드를 바꾸지 않는다.',
        'Phase55-P의0≤v≤0.3 U-Graph/초기값11개/4process/SLSQP 옵션을 그대로 사용한다. 실제 현재 pose/v/ω에서 동기 풀이하며,XY만 기존 PP/SP로 추종한다. 실제 설치된 마지막 U 해만 일관성 prior다. 후보 해를 비용순으로 최신 EC-tail 검사해 통과한 것을 설치하고 없으면61-P CUT/fallback을 사용한다.',
        table([dict(item=k,value=x) for k,x in p['u_goal'].items()]),table([v]),
        '보고서는61-P 같은seed의 CUT/CONS/CONS+G18 결과를 옆 열에 두고 결과·상자통과·도착/정지시간·U 채택률·채택해 길이 중앙값을 표시한다. 요청한 추가열은 실제 풀이 pose와 목표노드 거리 중앙값이다. 회전만 있는 정지XY 해는 기존 U 규칙대로 STOP이며 PP가 Graph θ/속도를 직접 실행하지 않는다.',
        '시뮬레이션·smoke·solver·실제 로그 재생은 실행하지 않았다. 종료 후 docs/PHASE62P_RESULTS.md와 research/results/phase62p/를 자동 생성하고 PNG도 강제 추가하여 commit·push한다. 동일한1회 기술 재시도/cache정리/저장v2/30GB중단/잠금·재개를 적용한다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/phase62p_01.log`','본 실행 명령(미실행):','`'+cmd+'`']
    (ROOT/'docs/PHASE62P_PREP.md').write_text('\n\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
