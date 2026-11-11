"""Register oracle-localization analysis and new seeds; plumbing dry-run only."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,ORDER_SEED,registered_order,verify

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def freeze():
    assert not RUN_ROOT.exists()
    from nomad_phase38.scenes import registered_jitter
    original=json.loads((ROOT/'research/nomad_phase58p/protocol.json').read_text());p=copy.deepcopy(original)
    p.update(phase='61-P',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),indices=list(INDICES),main_order=registered_order(),smoke=dict(enabled=False),
        placements={f'{s}_{i}':registered_jitter(s,i) for s in ('H1','H2','SLW') for i in INDICES},oracle_localization_analysis_only=True)
    p['execution']['full_frame_seed']=229
    p['oracle_delta']=dict(source='simulator actual robot observation_pose at NoMaD image capture tick',clock='observation_pose',delivery_delay_s=.75,
        nearest='global Euclidean XY nearest topomap node;lowest node id on tie',HMM_used=False,
        window='compute current oracle node first;unchanged candidate_range(current_node,goal,radius4),including official inclusive-end rule',
        subgoal='min(current_node+int(distance_at_current_node<3),candidate_end)',arrival='unchanged closest==goal declaration on delivered inference',
        oracle_obstacles_for_control=False,analysis_only=True,new_seeds=[229,230])
    p['localization']=dict(kind='ORACLE_NEAREST_XY',HMM_used=False,pose_clock='observation_pose',analysis_only=True,window_radius=4)
    p['report_definitions']['unchanged']='Phase53 depth/EC/Graph/controller/recovery/alignment/fallback/latch/expiry/official arrival and scene geometry unchanged;HMM replaced by observation-pose oracle node,new seeds229/230.'
    for method in METHODS:p['method_definitions'][method]+=' Common Phase61 delta: observation-pose oracle current node,no HMM;new seeds229/230.'
    p['report_definitions']['baselines']='No historical same-seed comparison. Within Phase61 pair differences CONS-CUT,CONS+G18-CUT,CONS+G18-CONS;both technicalPASS only.'
    p['report_definitions']['outputs']='Oracle analysis label,outcome/passage/time/side-flips/backward selections/Graph adoption,paired success differences,one topdown/run;force-add generated PNGs.'
    p['report_definitions']['prepared']='18config/launcher/worker/oracle clock/node/subgoal/declaration/audit/report plumbing;no simulation,solver or actual-log replay.'
    p['frozen_sources']={**original['frozen_sources'],**original['source_sha256']}
    for name in ('nomad_phase43p/worker.py','nomad_phase41/runtime.py','nomad_phase41/stop.py','nomad_phase47c/runtime.py','nomad_isaac/topomap.py','nomad_phase38/scenes.py','nomad_phase60p/report.py'):
        f=ROOT/'research'/name;p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    p['reference_hashes']=dict(original['reference_hashes']);p['reference_hashes']['research/nomad_phase58p/protocol.json']=sha256_file(ROOT/'research/nomad_phase58p/protocol.json')
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')};save(HERE/'protocol.json',p);verify()

def validate():
    verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-phase61p-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase61p.test_phase61p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase61p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==18 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run(['/usr/bin/python3','-c',"import sys;import nomad_phase61p.launch,nomad_phase61p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    value=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=18,simulations_started=0,solver_runs=0,real_replays=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',value)
    from .report import generate
    generate();document(value);print(json.dumps(value))

def document(v):
    p=verify();prefix=f'cd {ROOT} && '
    cmd=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase61p.campaign > ../artifacts/isaac6/phase61p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase61p.campaign --status'
    save(OUT/'preparation/commands.json',dict(campaign=cmd,status=status,executed=False))
    lines=['# Phase61-P 준비 — oracle 위치추정 분석용 조건',
        '**Oracle 위치추정은 분석용 조건이다. 실용 위치추정 방법의 성능을 의미하지 않는다.**',
        table([dict(status='FROZEN; NOT_RUN',runs=18,methods='CUT / CONS / CONS+G18',scenes='H1-v2 / SLW / H2',seeds='229,230',delay_s=.75,protocol_sha256=v['protocol_sha256'])]),
        '사용자 확정대로 영상 관측 시점 observation_pose(시뮬레이터 실제 robot pose)의 XY 최근접 Topomap 노드를 사용한다. 동률은 작은 node ID다. HMM은 실행하지 않는다. 이 노드를 현재 노드로 두고 기존 radius4 후보 창·거리 threshold3 부목표·closest==goal 선언 규칙을 적용한다. D075 전달 지연은 유지한다.',
        '관측 pose를 사용하므로 선언 시점의 현재 pose를 다시 조회해 노드를 바꾸지 않는다. oracle 노드가 이전 창 밖이어도 현재 노드를 중심으로 원래 candidate_range 함수를 호출하므로 필요한 거리·condition이 같은 창 안에 있다. NoMaD decoder/RNG는 기존과 동일하다.',
        'Phase58-P의 controller·depth·EC-tail·latch·후보 선택·회복·정렬·0.1 fallback·1s 만료·Graph·평가기와 장면 기하는 그대로다. 새 seed는 기존 jitter 생성 규칙에 입력하고 H1-v2 고정 상자는 유지한다. 방법 순열 RNG도 Phase58과 같아 블록 순서상 방법 배치는 동일하다.',
        table([dict(item=k,value=x) for k,x in p['oracle_delta'].items()]),table([v]),
        '보고서는 방법별 결과·상자 통과·도착/정지 시간·좌우 전환·뒤 선택·Graph 채택률과 동일(scene,seed) 쌍 성공 차이3개를 표시한다. 두 run 모두 기술 PASS인 짝만 계산하며 미완료는 —다. 그림에도 oracle 분석 조건을 명시한다.',
        '시뮬레이션·smoke·solver·실제 로그 재생은 실행하지 않았다. 종료 시 docs/PHASE61P_RESULTS.md 및 research/results/phase61p/를 생성하고 PNG를 명시적으로 강제 추가해 자동 commit·push한다. 1회 기술 재시도,cache 정리,저장v2,30GB 중단,공유 잠금·재개는 기존과 같다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/phase61p_01.log`','본 실행 명령(미실행):','`'+cmd+'`']
    (ROOT/'docs/PHASE61P_PREP.md').write_text('\n\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
