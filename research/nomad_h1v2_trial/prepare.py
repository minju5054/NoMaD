"""Freeze/validate only: no smoke, model, solver, simulator or historical study."""
import argparse,copy,json,os,re,shutil,subprocess,hashlib
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,CONDITIONS,INDICES,ORDER_SEED,registered_order,split,verify

def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def freeze():
    assert not RUN_ROOT.exists(),'Main must not be started or refrozen'
    from nomad_phase53p.config import verify as verify53
    from nomad_h1v2.scene import load_spec
    old=verify53();scene=load_spec();p=copy.deepcopy(old)
    hashes={}
    for f in sorted((ROOT/'research/nomad_h1v2').glob('*')):
        if f.suffix not in ('.py','.json'):continue
        name=str(f.relative_to(ROOT));committed=subprocess.check_output(['git','show','65556be:'+name],cwd=ROOT)
        assert hashlib.sha256(committed).hexdigest()==sha256_file(f),f
        hashes[name]=sha256_file(f)
    p.update(phase='H1-v2-trial',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),methods=list(METHODS),indices=list(INDICES),
        main_order=registered_order(),order_seed=ORDER_SEED,smoke=dict(enabled=False,reason='User:these four trials are main;no separate smoke'),
        scenes={s:copy.deepcopy(old['scenes']['H1_'+split(s)[1]]) for s in SCENES},conditions=dict(D075=.75,D150=1.5),
        environment=dict(scene='H1-v2',source_commit='65556be',scene_file='research/nomad_h1v2/scene.json',
            center_xy_m=scene['box']['center_xy_m'],size_xyz_m=scene['box']['size_xyz_m'],spawn_arc_m=scene['spawn']['arc_m'],jitter='ignored;fixed scene center',
            integration='Phase53 runtime install,then nomad_h1v2.scene.install_environment;configure on frozen H1 config;topomap/geometry unchanged'))
    p['frozen_sources']={**old['frozen_sources'],**old['source_sha256'],**hashes,
        'research/nomad_phase53p/protocol.json':sha256_file(ROOT/'research/nomad_phase53p/protocol.json'),
        'research/nomad_run_plots.py':sha256_file(ROOT/'research/nomad_run_plots.py')}
    p['reference_hashes']=copy.deepcopy(old['reference_hashes'])
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')}
    p['report_definitions'].update(historical='No historical comparison or extra analysis in this trial.',
        execution='Four main runs only,no smoke;randomize all four with seed20261116;serial,one technical retry,resume/lock,storagev2,portable/cache+pycache cleanup,30GB disk reserve,automatic report+figures+commit+push',
        passage='Frozen H1(+y AxisMonitor) contact/passage evaluator;side±X and actual spawn-to-passage time',
        figures='Per-run top-down only +2x2;actual72Hz state-colored trajectory,installed CUT/GRAPH,all8 original candidates per latched chunk,topomap nodes,EC reject and spawn positions;no timeline panels')
    save(HERE/'protocol.json',p);verify()

def document(v):
    p=verify();prefix=f'cd {ROOT} && '
    command=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_h1v2_trial.campaign > ../artifacts/isaac6/h1v2_trial_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_h1v2_trial.campaign --status'
    save(OUT/'preparation/commands.json',dict(campaign=command,status=status,executed=False))
    order=[dict(order=i+1,**j) for i,j in enumerate(p['main_order'])]
    text=['# H1-v2 시험 주행 준비',table([dict(status='FROZEN_PREPARED_NOT_RUN',main_runs=4,smoke=False,scene='H1-v2 @65556be',seed=221,order_seed=ORDER_SEED,protocol_sha256=sha256_file(HERE/'protocol.json'))]),
        'Phase53-P 동결 CUT·GRAPH-HO를 그대로 import한다. EC 제동꼬리·1초 waypoint 만료·FRESHEST·HMM·공식 도착 판정·PP/SP·90° 정렬·Graph factor/가중치/옵션을 변경하지 않았다. 변경은 H1 config에 configure를 적용하고 Phase53 초기화 뒤 install_environment를 호출하는 장면 연결뿐이다.',
        '상자 중심(2.876453,1.100000)m, 크기0.5×0.4×0.8m, 고정 위치이며 기존 jitter를 쓰지 않는다. Spawn은 실제 pose를 동일 Topomap polyline에 투영한 호장이2.253355m 이상이 되는 첫72Hz tick. H1-v2 기하·spawn·Topomap은65556be의 hash로 확인했다.',table(order),
        '별도 smoke 없이 위4회가 본 실행이다. 순차 실행·기술 실패1회 재시도·완료 run 재개 시 건너뛰기·글로벌 잠금·저장v2·종료 후 portable/cache 및 pycache 정리·매 run 전 여유30GB 검사 규칙을 재사용한다.',table([v]),
        '완료 후 /usr/bin/python3 + PYTHONPATH=research로 report를 자동 실행한다. docs/H1V2_TRIAL.md와 research/results/h1v2_trial/에 run별 분류, 상자 통과/쪽/출현→통과, 도착/정지/ALIGN_ROTATE 시간, 최소 여유, EC 거절, Graph 채택률/거절 사유를 저장한다. 주행 PNG4장과2×2 종합 그림은 docs/figures/에 생성하고 commit·push한다. 현재 그림은 아직 실행되지 않은 주행으로 만들지 않는다.',
        '그림: 벽·정적 장애물·실제 H1-v2 상자/출현 위치·Topomap 노드·목표·상태별 궤적, CUT 회색 점선·GRAPH 주황 파선, 각 수신 chunk의 저장된 원8후보(아주 옅은 선), EC REJECT 빨간x. 시간축 패널 없음. 기술 실패는 검증된 데이터 없음으로 표시한다.',
        '추가 분석·오프라인 재풀이·시뮬레이션은 하지 않았다. 테스트의 가짜 자료는 그림/report 코드 검증용 임시 폴더에서만 사용하고 삭제했다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/h1v2_trial_01.log`','본 실행 명령(미실행):','`'+command+'`']
    (ROOT/'docs/H1V2_TRIAL_PREP.md').write_text('\n\n'.join(text)+'\n')

def validate():
    verify();env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-h1v2-trial-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_h1v2_trial.test_trial','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    folder=OUT/'preparation';(folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-5000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_h1v2_trial.campaign','--dry-run'],cwd=ROOT,env=env,text=True));assert dry['planned']==4 and not dry['simulations_started'];save(folder/'dry_run.json',dry)
    subprocess.run([str(ROOT.parent/'.venv/bin/python'),'-c',"import sys;import nomad_h1v2_trial.launch,nomad_h1v2_trial.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    assert not RUN_ROOT.exists()
    v=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=4,simulations_started=0,smoke=0,offline_resolves=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',v)
    from .report import generate
    generate();document(v);print(json.dumps(v))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
