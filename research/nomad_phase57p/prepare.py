"""Registration and plumbing dry-run only; no simulation or solver exercise."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,ORDER_SEED,registered_order,verify

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def freeze():
    assert not RUN_ROOT.exists()
    from nomad_phase38.scenes import registered_jitter
    old=json.loads((ROOT/'research/nomad_phase53p/protocol.json').read_text());p=copy.deepcopy(old)
    p.update(phase='57-P',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),indices=list(INDICES),
        scenes={s:copy.deepcopy(old['scenes'][('H1' if s=='H1-v2' else s)+'_D075']) for s in SCENES},conditions=dict(D075=.75),
        main_order=registered_order(),order_seed=ORDER_SEED,smoke=dict(enabled=False),
        placements={f'{s}_{i}':registered_jitter(s,i) for s in ('H1','H2','SLW') for i in INDICES},
        execution=dict(serial=True,technical_retries=1,cache_cleanup=True,storage_version=2,full_frame_seed=227,disk_min_bytes=30_000_000_000))
    p['method_definitions']={
        'NOMAD_RAW':'Phase47-C NOMAD_RAW exactly: sample0/world anchor,original argmin localization,PP/SP with frozen >90degree alignment,1s expiry,official declared arrival. No depth/EC/HMM/recovery; no new endpoint latch.',
        'MIN':'Phase53 CUT minus depth prefilter/RECOVER_ROTATE/ALIGN/0.1tier. All8world candidates ordered by B-projected remaining length,index tie. Full-speed tailEC at install and36ticks. All reject=>STOP_WAIT until nextchunk,noKEEP. HMM,1sexpiry,officialarrival. ENDPOINT latch resets only on actual new path.',
        'MIN+G18':'MIN plus Phase53 synchronous ClearanceGraph wiring. Reuse nightE2 HoldClearanceGraph: only boundary curvature equality omitted when abs(v)<.02 or abs(w/v)>8. Remaining factors/weights/options/certificate unchanged. Graph on final EC-approved MIN candidate;tailEC accepts Graph otherwise same MIN path.'}
    p['report_definitions']={
        'switches':'Private function bindings/MRO bridges;no frozen files modified. candidate safe=True is inherited eligibility only,never depth clearance;selection records depth_filter_disabled.',
        'controller':'Same PP/SP control and limits;NoAlignment replace_path computes frozen SP then trigger_S=False,modeGO. Completion latched and actual frozen stop_command repeats to rest,until any new path installation. Numeric threshold field90 retained for inherited audit;alignment_disabled flag and absenceofALIGN prove switch.',
        'EC':'Frozen Phase53 tail72Hz integration with same MIN controller(copy for periodic continuation),not original aligning controller. Endpoint/2s then stop_command to rest;>=.025m. Fullspeed candidates only;never cap.1. Reject applies following9Hztick as frozen.',
        'graph':'Same Phase53 job construction,prior,synchronous RPC,solver settings. Existing E2 graph class/worker directly imported. No new solver. Original MIN candidate is already tailEC-passed before optionalGraph;allMINcandidatesreject=>STOP.',
        'scene':'H1-v2 fixed y1.10 box/arcspawn,SLW andH2 frozengeometry/topomap. H2 newseed jitter uses Phase38 registered_jitter;all3methods shareplacement. H1-v2 fixedbox overrides H1jitter.',
        'order':'scene then seed;three methods shuffled perblock with random.Random(20261117),18runs.',
        'outputs':'Frozen arrival success<=.5m/no collision,wrongstop,timeout,boxpassage,arrival/stoppedtime,Graph adopted/attempted;one150dpi saved-log topdown eachrun. Incomplete results marked;technicalfailure empty panel.',
        'prepared':'No simulations,no smoke,no recorded-input solve. 18configs/actuallauncherargument boundary/JSON/controller switches/fallback/report plumbing only.'}
    for k in ('blocks','primary_tests','analysis','nights'):p.pop(k,None)
    p['frozen_sources']={**old['frozen_sources'],**old['source_sha256']}
    for name in ('nomad_night20261111/graph.py','nomad_night20261111/worker.py','nomad_phase55p/campaign.py','nomad_run_plots.py','nomad_h1v2/scene.py'):
        f=ROOT/'research'/name;p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    p['reference_hashes']=dict(old['reference_hashes'])
    for name in ('research/nomad_phase53p/protocol.json','research/nomad_h1v2/scene.json'):
        p['reference_hashes'][name]=sha256_file(ROOT/name)
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')};save(HERE/'protocol.json',p);verify()

def validate():
    verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-phase57p-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase57p.test_phase57p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase57p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==18 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run(['/usr/bin/python3','-c',"import sys;import nomad_phase57p.launch,nomad_phase57p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    value=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=18,simulations_started=0,solver_runs=0,protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',value)
    from .report import generate
    generate();document(value);print(json.dumps(value))

def document(v):
    p=verify();prefix=f'cd {ROOT} && '
    command=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase57p.campaign > ../artifacts/isaac6/phase57p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase57p.campaign --status'
    save(OUT/'preparation/commands.json',dict(campaign=command,status=status,executed=False))
    lines=['# Phase57-P 준비',table([dict(status='FROZEN; NOT_RUN',runs=18,scenes='H1-v2 / SLW / H2',seeds='227,228',delay_s=.75,protocol_sha256=v['protocol_sha256'])]),
        table([dict(method=k,definition=x) for k,x in p['method_definitions'].items()]),
        'MIN 두 방법은 depth 선별·회복·정렬·0.1m/s 후보 단계를 끈다. 모든 후보는 관측 pose에서 world 고정 후 B 이후 잔여 길이 순서로 EC 검사한다. 전부 거절되면 STOP_WAIT이며 기존 경로 KEEP 없이 다음 chunk를 기다린다.',
        'ENDPOINT는 새 경로가 실제 설치될 때만 해제한다. 매 제어 tick 동결 stop_command로 감속해 정지를 유지한다. 설치/주기 EC도 동일한 정렬 OFF·ENDPOINT latch 실행기를 사용하고, 제동꼬리 적분과 안전 하한은 동결이다. 1s 만료는 그대로 유지한다.',
        'MIN+G18은 Phase53 GRAPH-HO 배관과 E2의 조건부 시작 경계 곡률 제외 class/worker를 그대로 import한다. 원 MIN 경로가 EC를 통과한 뒤 Graph를 적용하며, Graph 실패/EC 거절은 그 MIN 경로로 fallback한다. solver 실행이나 수치 튜닝은 하지 않았다.',
        'NOMAD_RAW는 Phase47-C 정의 그대로이므로 원래 argmin 위치추정/sample0/90° 정렬이며 HMM·EC·새 latch를 적용하지 않는다. 공식 도착 판정과 1s 만료는 세 방법 모두 사용한다.',
        table([dict(item=k,value=x) for k,x in p['report_definitions'].items()]),table([v]),
        '본 실행 종료 후 docs/PHASE57P_RESULTS.md 및 research/results/phase57p/에 표와 run별 top-down PNG를 생성하고 자동 commit·push한다. 기술 실패 1회 재시도, run별 cache 정리, 디스크 30GB 미만 중단, 동일 root 재개.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/phase57p_01.log`','본 실행 명령(미실행):','`'+command+'`']
    (ROOT/'docs/PHASE57P_PREP.md').write_text('\n\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
