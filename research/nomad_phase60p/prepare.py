"""Freeze verified SIGN calibration reference; validate wiring without simulation."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,ORDER_SEED,registered_order,verify,load_model,MODEL_FILE,MODEL_SHA256

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def freeze():
    assert not RUN_ROOT.exists();model=load_model()
    original=json.loads((ROOT/'research/nomad_phase59p/protocol.json').read_text());p=copy.deepcopy(original)
    p.update(phase='60-P',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),smoke=dict(enabled=False),model_sha256=MODEL_SHA256)
    p.pop('net_delta',None)
    p['sign_delta']=dict(only_policy_change='online transition NET -> SIGN',implementation='nomad_loc_v2.filter.Filter(node_xy,ell,SIGN,verified_calibration)',
        model_file=str(MODEL_FILE.relative_to(ROOT)),model_sha256=MODEL_SHA256,sigma2=model['sigma2'],no_refit=True,
        mean='signed dot(current minus previous observation odometry XY, tangent at previous MAP)/ell',
        transition='frozen Gaussian log density at integer node offsets,row normalization over global nodes,no support cutoff',
        tangent='frozen central adjacent node pose difference,one-sided ends,nearest valid oriented adjacent segment for zero vector',
        coordinate='request observation_pose[:2] at hmm_odometry_tick,exact simulator odometry assumption;no true_node input',
        unchanged='Phase59/58 controller,Graph,EC,latch,selection,recovery,1s expiry,geometry,jitter,seed,method order;Phase43 emission/window radius4/subgoal threshold3/end clamp/declaration',
        no_OBS=True,no_MEM=True)
    if 'net_report' in p:p['localization_report']=p.pop('net_report')
    p['localization_report']['baseline']='Phase58 and Phase59 same(scene,seed,method);supplementary values read from saved logs only at final report'
    p['report_definitions']['baselines']='Phase58-P and Phase59-P paired columns;no historical result rewrite.'
    p['report_definitions']['outputs']='Phase60 outcomes,stop distance,declared estimated/true node,actual<=.7 reach,false goals,undeclared reach. One topdown/run;force-add PNGs despite repository ignore rule;automatic commit/push.'
    p['report_definitions']['prepared']='SIGN model-hash refusal/synthetic equivalence/worker/audit/18launcher argument dry-runs only,no simulation/solver/refit/real-log replay.'
    p['frozen_sources']={**original['frozen_sources'],**original['source_sha256']}
    for name in ('nomad_loc_v2/filter.py','nomad_loc_v2/data.py','nomad_loc_v2/calibration.py','nomad_phase57p/figures.py'):
        f=ROOT/'research'/name;p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    p['reference_hashes']=dict(original['reference_hashes'])
    for name in ('research/nomad_phase59p/protocol.json','research/nomad_loc_v2/protocol.json','research/results/phase59p/runs.json',str(MODEL_FILE.relative_to(ROOT))):
        p['reference_hashes'][name]=sha256_file(ROOT/name)
    assert p['reference_hashes'][str(MODEL_FILE.relative_to(ROOT))]==MODEL_SHA256
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')};save(HERE/'protocol.json',p);verify()

def validate():
    verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-phase60p-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase60p.test_phase60p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase60p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==18 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run(['/usr/bin/python3','-c',"import sys;import nomad_phase60p.launch,nomad_phase60p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=18,simulations_started=0,solver_runs=0,real_replays=0,calibration_refits=0,
        model_sha256=MODEL_SHA256,sigma2=load_model()['sigma2'],protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',v)
    from .report import generate
    generate(prepare_only=True);document(v);print(json.dumps(v))

def document(v):
    p=verify();prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase60p.campaign > ../artifacts/isaac6/phase60p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase60p.campaign --status'
    save(OUT/'preparation/commands.json',dict(campaign=cmd,status=status,executed=False))
    lines=['# Phase60-P 준비',table([dict(status='FROZEN; NOT_RUN',runs=18,methods='CUT / CONS / CONS+G18',scenes='H1-v2 / SLW / H2',seeds='227,228',delay_s=.75,protocol_sha256=v['protocol_sha256'])]),
        f"사용자 확정: 원래 동결 σ²={v['sigma2']}를 보정 파일에서 직접 읽는다. 0.1492는 반올림 표기일 뿐 온라인 상수로 대체하지 않는다. `model_sha256={MODEL_SHA256}` 전체 일치 시에만 launcher/worker/audit/report를 진행하고 불일치하면 거부한다. 보정값은 재추정하지 않는다.",
        '전이는 LOC_V2 Filter(SIGN)를 그대로 import한다. 직전 MAP의 Topomap 노드 접선에 observation-tick 오도메트리 변위를 투영한 s/ℓ를 평균으로 쓰고 정수 offset Gaussian을 전역 노드 범위에서 행 정규화한다. 노드 pose와 오도메트리는 같은 좌표계로 제공된다고 가정한다.',
        'Phase59-P의 실행 함수·방법·장면·jitter·seed·순서를 그대로 재사용한다. 방출·radius4 창·부목표 threshold3·closest==goal 선언도 기존 함수를 쓴다. 유일한 정책 변경은 NET→SIGN 전이다. OBS/MEM은 사용하지 않는다.',
        table([dict(item=k,value=x) for k,x in p['sign_delta'].items()]),table([v]),
        '성공은 기존0.5m 선언+무충돌이다. 0.7m 실제 접근·미선언과 거짓 목표(node 기준)는 Phase59 정의를 그대로 사용하며 거리 기준 잘못된 도착과 구분한다. Phase58/59 같은(scene,seed,method)를 모두 옆 열로 표시한다.',
        '시뮬레이션·smoke·solver·실제 로그 재생·보정 재추정은 실행하지 않았다. 종료 후 docs/PHASE60P_RESULTS.md와 research/results/phase60p/를 생성하고 run별 PNG도 명시적으로 git add -f하여 commit·push한다. 기술 실패1회 재시도,cache 정리,저장v2,30GB 중단,공유 실행 잠금·재개는 기존과 같다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/phase60p_01.log`','본 실행 명령(미실행):','`'+cmd+'`']
    (ROOT/'docs/PHASE60P_PREP.md').write_text('\n\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
