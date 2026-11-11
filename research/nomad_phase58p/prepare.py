"""Freeze and dry plumbing only; no simulation, replay or numerical solver."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,ORDER_SEED,registered_order,verify

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def freeze():
    assert not RUN_ROOT.exists()
    old=json.loads((ROOT/'research/nomad_phase53p/protocol.json').read_text());p=copy.deepcopy(old)
    previous=json.loads((ROOT/'research/nomad_phase57p/protocol.json').read_text())
    p.update(phase='58-P',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),indices=list(INDICES),
        scenes={s:copy.deepcopy(old['scenes'][('H1' if s=='H1-v2' else s)+'_D075']) for s in SCENES},conditions=dict(D075=.75),
        main_order=registered_order(),order_seed=ORDER_SEED,smoke=dict(enabled=False),placements=copy.deepcopy(previous['placements']),
        execution=dict(serial=True,technical_retries=1,cache_cleanup=True,storage_version=2,full_frame_seed=227,disk_min_bytes=30_000_000_000))
    p['method_definitions']={
        'CUT':'Phase53 CUT fully retained +ENDPOINT latch;longest depth-safe remaining suffix,then frozen EC full/slow/STOP choice.',
        'CONS':'Same CUT except selection order among depth-safe/EC-passing candidates:minimum absolute angle from B->previous actually installed endpoint,then longer remaining length,then lower index. First/zero reference direction=current robot heading. Backward>90 only if no <=90candidate passes in that frozen speed tier.',
        'CONS+G18':'CONS then frozen Phase53 Graph-HO job/solver. Import nightE2 HoldClearanceGraph/worker:abs(v)<.02 orabs(w/v)>8 drops only initial boundary curvature equality. Graph exact certificate and tailEC required,otherwise the selected CONS path.'}
    p['report_definitions']={
        'unchanged':'Phase53 depth filter,RECOVER_ROTATE,>90degree alignment,fullspeed/.1/STOP fallback,EC36tick reinspection,next9Hz reject application,HMM,1sexpiry,officialarrival,geometry/depth remain unchanged. No Phase57 MIN policy switches.',
        'selector':'One pure selection function reorders frozen depth-safe options by abs wrapped B-to-end direction difference and remaining length;uses frozen normal_choice for cap/fallback phases. It tests angles ascending,so a passing <=90option always precedes >90 in each tier. Fullspeed remains before slow,as frozen.',
        'reference':'Store only actual installed XY endpoint;recompute vector from current B at each choice. Update at every installation including Graph/cap/periodic replacements. Rejections/STOP do not update. Direction undefined at zero displacement uses current heading,without extra tuning.',
        'latch':'Common LatchedProfile inherits CappedNA (alignment and cap retained). Only completed flag persistence is new;reset at actual new path. Actual frozen stop_command repeats until rest. EC-tail uses the same profile and continuation state.',
        'counting':'Left/right from selected native candidate direction relative to robot heading;CENTER(abs angle<=1e-12) skipped. Count successive non-centre changes. Backward reference>90 and backward robot>90 reported separately;this threshold is descriptive and not a new policy gate.',
        'baselines':'Phase57 published runs.json,NOMAD_RAW/MIN,same scene/seed. File read only at report generation with result hash saved. No raw-log replay or rewrite;missing results/fields —.',
        'order':'scene then seed,methods perblock random.Random(20261118),18runs.',
        'outputs':'Classifications,passage,arrival/stoppedtime,side flips,backward choices,Graph adoption/solve times;one saved-log150dpi topdown perrun. Automatic report commit/push.',
        'prepared':'Only18config/actuallauncherargument/selection/JSON/latch/fallback/report plumbing tests. No smoke,simulator or solver execution.'}
    for k in ('blocks','primary_tests','analysis','nights'):p.pop(k,None)
    p['frozen_sources']={**old['frozen_sources'],**old['source_sha256']}
    for name in ('nomad_night20261111/graph.py','nomad_night20261111/worker.py','nomad_phase55p/campaign.py','nomad_phase57p/launch.py','nomad_phase57p/figures.py','nomad_run_plots.py','nomad_h1v2/scene.py'):
        f=ROOT/'research'/name;p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    p['reference_hashes']=dict(old['reference_hashes'])
    for name in ('research/nomad_phase53p/protocol.json','research/nomad_phase57p/protocol.json','research/nomad_h1v2/scene.json'):
        p['reference_hashes'][name]=sha256_file(ROOT/name)
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')};save(HERE/'protocol.json',p);verify()

def validate():
    verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-phase58p-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase58p.test_phase58p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase58p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==18 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run(['/usr/bin/python3','-c',"import sys;import nomad_phase58p.launch,nomad_phase58p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=18,simulations_started=0,solver_runs=0,protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',v)
    from .report import generate
    generate();document(v);print(json.dumps(v))

def document(v):
    p=verify();prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase58p.campaign > ../artifacts/isaac6/phase58p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase58p.campaign --status'
    save(OUT/'preparation/commands.json',dict(campaign=cmd,status=status,executed=False))
    lines=['# Phase58-P 준비',table([dict(status='FROZEN; NOT_RUN',runs=18,scenes='H1-v2 / SLW / H2',seeds='227,228',delay_s=.75,protocol_sha256=v['protocol_sha256'])]),
        table([dict(method=k,definition=x) for k,x in p['method_definitions'].items()]),
        '세 방법 모두 Phase53 CUT의 depth 필터·RECOVER_ROTATE·정렬·0.1m/s fallback·HMM·1s 만료·공식 도착 판정을 그대로 사용한다. ENDPOINT latch만 공통 추가하며 새 경로 설치 전까지 동결 stop_command로 정지를 유지한다. EC도 동일한 latch/정렬/속도 cap 실행기를 검사한다.',
        'CONS는 최신 B에서 이전 실제 설치 경로 끝점 방향과 각도가 가장 작은 depth-safe 후보부터 EC 검사한다. 동률은 잔여 길이, 그다음 sample index다. 각 속도 단계 안에서 ≤90° 통과 후보가 먼저이며, 전속도 단계 자체는 기존대로 0.1m/s보다 앞선다. 최초 또는 끝점=B인 경우 기준은 현재 heading이다. Graph가 채택되면 다음 기준은 Graph 끝점이다.',
        'CONS+G18은 Phase53 설치 배관과 E2의 조건부 시작 경계 곡률 제외 class/worker를 그대로 import한다. factor·가중치·solver 옵션·certificate는 바꾸지 않는다.',
        table([dict(item=k,value=x) for k,x in p['report_definitions'].items()]),table([v]),
        '좌우 전환은 실제 robot heading 기준 선택 후보 방향 부호의 전환이다. 뒤 선택은 CONS 기준 >90°와 실제 heading >90°를 구분해 남긴다. Phase57-P 같은 seed NOMAD_RAW·MIN 발표 결과를 report 생성 시 옆 열로 읽으며, 누락은 —다. 실행 중인 Phase57 파일은 변경하지 않는다.',
        '주행 종료 후 docs/PHASE58P_RESULTS.md와 research/results/phase58p/에 표·run별 top-down을 만들고 자동 commit·push한다. 기술 실패 1회 재시도, cache 정리, 저장 v2,30GB 미만 중단,공유 실행 잠금·재개 지원.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/phase58p_01.log`','본 실행 명령(미실행):','`'+cmd+'`']
    (ROOT/'docs/PHASE58P_PREP.md').write_text('\n\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
