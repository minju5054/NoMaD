"""Freeze and plumbing dry-runs only. No saved-input solve or simulation."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,BASE_SCENES,CONDITIONS,INDICES,registered_order,split,verify

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def freeze():
    assert not RUN_ROOT.exists(),'Do not re-register a running/existing campaign'
    old=json.loads((ROOT/'research/nomad_phase53p/protocol.json').read_text());p=copy.deepcopy(old)
    hashes={};baselines=[]
    for phase,method in [('phase53p','CUT'),('phase52p','CUT-HOLD')]:
        file=ROOT/f'research/results/{phase}/runs.json';hashes[str(file.relative_to(ROOT))]=sha256_file(file)
        for r in json.loads(file.read_text()):
            if r['method']!=method:continue
            b={k:v for k,v in r.items() if k not in ('attempts','node_errors','graph_prediction_errors_m','ec_exhausted_intervals')}
            b.update(phase='Phase53' if phase=='phase53p' else 'Phase52')
            if phase=='phase52p':b['align_rotate_s']=b.get('command_state_seconds',{}).get('ALIGN_ROTATE')
            baselines.append(b)
    save(OUT/'preparation/baselines.json',baselines)
    p.update(phase='55-P',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),indices=list(INDICES),
        main_order=registered_order(),order_seed=None,conditions=dict(D075=.75,D150=1.5),
        scenes={s:copy.deepcopy(old['scenes'][('H1' if split(s)[0]=='H1-v2' else split(s)[0])+'_'+split(s)[1]]) for s in SCENES},
        smoke=dict(enabled=False,reason='User forbids simulation; plumbing dry-run only'))
    p['method_definitions']={'U-GRAPH':'Phase53 CUT + HOLD. On every latched chunk and every36tick periodic check solve frozen U-Graph from actual current pose/v/omega,only v lower bound changed from-.3 to0.11starts,fourprocess pool. Choose lowest cost hard-feasible candidate passing latest-map frozen tailEC. PP+SP follows XY;Graph v/omega not executed.'}
    p['report_definitions']={
        'basis':'Phase53 CUT EC braking tail/HMM/official arrival/depth/filter/geometry/fallback unchanged;receipt expiry replaced by frozen Phase52 HoldCore and no-minimum-residual hold rule. No R2/R3,NoMaD or Graph18 refinement.',
        'graph':'Import nomad_ugraph.Graph/SLSQP analytically;only inequalities .3+v>=0 become v>=0,matching nonnegative initial controls. N25,dt.1,11starts,maxiter100,ftol1e-8,tolerance1e-7 and all soft factors frozen. First omega is saved actual omega. No tuning; no new numerical deadline.',
        'prior':'Last actually installed U-Graph states and installation simulation time,using frozen shifted_prior overlap. CUT fallback does not become a U solution and never advances its prior clock.',
        'periodic':'Independent36tick clock starts at first chunk. At next9Hz control tick,solve from then-actual pose/latest depth. Frozen ongoing EC checks and reject handling retained. CHUNK+PERIODIC at same control tick coalesce to one solve;both triggers recorded.',
        'recovery':'RECOVER_ROTATE and WAIT_FRESH remain frozen. Attempts may be computed but are not installed mid-recovery;RECOVERY_DEFERRED counted in adoption denominator.',
        'stationary':'Zero-length feasible XY is an endpoint STOP,validated by frozen EC-tail using StationaryEndpoint(circle footprint). No fake path;PP cannot execute planned in-place theta without XY. Recorded as stationary installation,not a graph-angular controller.',
        'installation':'Current actual pose, synchronous system-Python RPC. Check hard-feasible results in ascending objective/start-index order using latest-map EC-tail and current cap. Failed U uses same CUT/HOLD fallback;0.1cap persists except full-speed fresh installation. No new controller.',
        'time':'Log solve_s for full11start4workerjob,rpc_s,and total_s including independentEC. Existing600s launcher watchdog and300s RPC watchdog are technical errors,not successful no-solution outcomes.',
        'telemetry':'classification,box passage,arrival/stopped/ALIGN_ROTATE seconds,appliedU/attempts,solve p50/p95 and total p50/p95,left-right reversals. Reversal=end XY lateral in current B heading,1cm deadband,compare consecutive non-centre installed sides;report-only.',
        'comparison':'Published same seed/scene/delay Phase53 CUT and Phase52 CUT-HOLD only. Missing H1-v2 comparisons —. Different days and original expiry/EC differences are explicit;no historical replay.',
        'execution':'24serial runs,one technical retry,global lock,resume,storagev2,cache cleanup,30GB reserve,automatic report+commit+push. No preparation smoke/simulation/real input solves.'}
    p['frozen_sources']={**old['frozen_sources'],**old['source_sha256']}
    for name in ('nomad_ugraph/graph.py','nomad_ugraph/dynamics.py','nomad_ugraph/certificate.py','nomad_phase52p/runtime.py','nomad_phase52p/metrics.py',
                 'nomad_night20261111/runtime.py','nomad_h1v2/scene.py','nomad_phase33p/storage.py','nomad_phase28/storage.py'):
        f=ROOT/'research'/name;p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    p['reference_hashes']={**old['reference_hashes'],**hashes}
    for f in [ROOT/'research/nomad_phase53p/protocol.json',ROOT/'research/nomad_ugraph/protocol.json',ROOT/'research/nomad_h1v2/scene.json',OUT/'preparation/baselines.json']:
        if f.exists():p['reference_hashes'][str(f.relative_to(ROOT))]=sha256_file(f)
    # configure() itself checks the existing H1-v2 registration hashes.
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    save(HERE/'protocol.json',p);verify()

def document():
    p=verify();validation=json.loads((OUT/'preparation/validation.json').read_text());prefix=f'cd {ROOT} && '
    command=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase55p.campaign > ../artifacts/isaac6/phase55p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase55p.campaign --status'
    save(OUT/'preparation/commands.json',dict(campaign=command,status=status,main_executed=False))
    lines=['# Phase55-P 준비',table([dict(status='FROZEN; NOT_RUN',runs=24,method='U-GRAPH',scenes=', '.join(BASE_SCENES),conditions='D075/D150',seeds='221,222',protocol_sha256=sha256_file(HERE/'protocol.json'))]),
        '시뮬레이션·저장 입력 재풀이·smoke는 실행하지 않았다. 24개 조합의 실제 launcher 인자 검증과 배관 테스트만 수행했다. 실행 순서는 조건 → seed → 장면이며 방법은 하나다.',
        'Graph의 변경은 0≤v≤0.3뿐이다. 해석적 SLSQP 11개 초기값을 4개 worker로 동기 풀이하고, 현재 pose에서 최신 지도 EC-tail을 통과한 최소 비용 해를 설치한다. 직전 실제 설치 U 해만 일관성 prior로 사용한다. 원 Graph의 계획 v·ω 대신 동결 PP+SP가 XY를 따라가므로, 계획 운동학과 실제 명령은 같지 않다.',
        'chunk 도착 및 36tick 재검사 때 재풀이한다. 36tick이 9Hz 제어 tick 사이이면 다음 제어 tick의 실제 상태를 사용하며 검사·적용 tick과 지연을 기록한다. 해 없음/EC 거절은 CUT-HOLD fallback, 회복 중 설치는 보류한다. 제자리 회전 해도 XY가 정지면 PP의 끝점 STOP으로 처리하고 별도 기록한다.',
        '수치 풀이 시간 상한을 새로 추가하지 않았다. 기존 launcher 600초 및 RPC 300초 watchdog 초과는 기술 실패이며 한 번 재시도한다. 준비 단계에서 성능·실행 시간은 측정하지 않았다.',
        table([dict(item=k,value=v) for k,v in p['report_definitions'].items()]),table([validation]),
        '비교군은 기존 Phase53-P CUT·Phase52-P CUT-HOLD의 같은 seed·조건이다. H1-v2 등 없는 항목은 —로 표시한다. 종료 후 docs/PHASE55P_RESULTS.md와 research/results/phase55p/를 자동 생성하고 commit·push한다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/phase55p_01.log`','본 실행 명령(미실행):','`'+command+'`']
    (ROOT/'docs/PHASE55P_PREP.md').write_text('\n\n'.join(lines)+'\n')

def validate():
    verify();folder=OUT/'preparation';env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase55p.test_phase55p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-5000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase55p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==24 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run(['/usr/bin/python3','-c',"import sys;import nomad_phase55p.launch,nomad_phase55p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    value=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=24,simulations_started=0,offline_solves=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',value)
    from .report import generate
    generate();document();print(json.dumps(value))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
