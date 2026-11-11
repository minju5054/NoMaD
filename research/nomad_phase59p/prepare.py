"""Freeze the single NET delta and validate plumbing without simulation."""
import argparse,copy,json,os,re,shutil,subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase31p.report import table
from .config import ROOT,HERE,OUT,RUN_ROOT,METHODS,SCENES,INDICES,ORDER_SEED,registered_order,verify

def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def freeze():
    assert not RUN_ROOT.exists()
    original=json.loads((ROOT/'research/nomad_phase58p/protocol.json').read_text());p=copy.deepcopy(original)
    p.update(phase='59-P',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),smoke=dict(enabled=False))
    p['net_delta']=dict(only_policy_change='online HMM transition HMM0 -> NET',implementation='nomad_hmm_replay.filter.Replay(...,NET)',
        width='min(node_count-1,round(norm(observation_odometry_xy-current_MAP_entry_xy)/ell));minimum1 removed;selftransition always included',
        ell='same median positive adjacent Topomap node spacing',entry='first step initializes MAP anchor;each subsequent MAP change resets anchor',
        coordinate='request observation_pose[:2] at hmm_odometry_tick,existing exact simulator odometry assumption;no true_node input',
        unchanged='Phase43 window(radius4),emission,official subgoal threshold3/end-window clamp and closest==goal declaration;all Phase58 execution/selection/Graph/EC/scene/seed/order rules',
        no_MEM=True,no_tuning=True)
    p['net_report']=dict(success='unchanged declared distance<=.5 and collision-free',reached_goal='min(saved72Hz goal_distance)<=.7 regardless of declaration',
        arrived_without_declaration='reached_goal_0p7 and no declared_arrival through termination;additional<=.5 counter reported separately',
        false_goal='inference MAP==goal AND observation-time true_node<goal-2;count and affected runs,distinct from distance-based wrong stop',
        declaration_nodes='logged closest_node and nearest node at actual declared pose',baseline='Phase58 same(scene,seed,method),new supplementary fields derived from saved logs only when final report runs')
    p['report_definitions']['baselines']='Phase58 published same(scene,seed,method) results. Required new supplementary metrics derived from saved logs only at report time;no historical rewrite.'
    p['report_definitions']['outputs']='Phase59 success/collision/wrong stop/timeout,stop distance,declared estimated/true node,goal<=.7 reach,undeclared reach,false-goal node counts;Phase58 paired columns and saved topdown/run.'
    p['report_definitions']['prepared']='NET synthetic/worker/audit and18 actual launcher argument dry checks only;no simulation,solver or real-log replay.'
    p['frozen_sources']={**original['frozen_sources'],**original['source_sha256']}
    for name in ('nomad_hmm_replay/filter.py','nomad_phase43p/worker.py','nomad_phase43p/localization.py','nomad_phase43p/odometry.py','nomad_phase43p/metrics.py','nomad_phase47c/metrics.py','nomad_phase57p/figures.py'):
        f=ROOT/'research'/name;p['frozen_sources'][str(f.relative_to(ROOT))]=sha256_file(f)
    p['reference_hashes']=dict(original['reference_hashes'])
    for name in ('research/nomad_phase58p/protocol.json','research/nomad_hmm_replay/protocol.json','research/results/phase58p/runs.json'):
        p['reference_hashes'][name]=sha256_file(ROOT/name)
    p['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.glob('*.py')};save(HERE/'protocol.json',p);verify()

def validate():
    verify();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-phase59p-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_phase59p.test_phase59p','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6500:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_phase59p.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    assert dry['planned']==18 and dry['simulations_started']==0;save(folder/'dry_run.json',dry)
    subprocess.run(['/usr/bin/python3','-c',"import sys;import nomad_phase59p.launch,nomad_phase59p.campaign;assert 'scipy' not in sys.modules;assert 'torch' not in sys.modules"],cwd=ROOT,env=env,check=True)
    value=dict(passed=True,tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),dry_run=18,simulations_started=0,solver_runs=0,real_replays=0,
        protocol_sha256=sha256_file(HERE/'protocol.json'),disk_free_bytes=shutil.disk_usage(ROOT).free)
    save(folder/'validation.json',value)
    from .report import generate
    generate(prepare_only=True);document(value);print(json.dumps(value))

def document(v):
    p=verify();prefix=f'cd {ROOT} && '
    command=prefix+'nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_phase59p.campaign > ../artifacts/isaac6/phase59p_01.log 2>&1 < /dev/null &'
    status=prefix+'PYTHONPATH=research /usr/bin/python3 -m nomad_phase59p.campaign --status'
    save(OUT/'preparation/commands.json',dict(campaign=command,status=status,executed=False))
    lines=['# Phase59-P 준비',table([dict(status='FROZEN; NOT_RUN',runs=18,methods='CUT / CONS / CONS+G18',scenes='H1-v2 / SLW / H2',seeds='227,228',delay_s=.75,protocol_sha256=v['protocol_sha256'])]),
        'Phase58-P 코드·장면·jitter·seed·블록 내 순서를 그대로 사용한다. 실행 함수도 Phase58 install/run_without_oracle을 그대로 import한다. 유일한 정책 변경은 HMM 전이를 HMM_REPLAY의 NET으로 연결하는 것이다.',
        'w=round(현재 영상 observation tick의 odometry XY와 현재 MAP 진입 XY 사이 거리/ℓ). ℓ은 기존 양수 인접 Topomap 노드 간격 중앙값,최소1 없음,자기 전이 포함,MAP 변경 때 진입 위치 갱신이다. Python의 ties-to-even round와 초기 균등 prior도 HMM_REPLAY 그대로다. MEM은 적용하지 않는다.',
        'Phase43의 후보 창(radius4),방출,subgoal threshold3 및 end-window clamp,closest==goal 선언은 원래 함수를 재사용한다. 현재 영상의 observation_pose를 exact odometry로 사용하며 실제 정답 노드나 목표 좌표를 필터에 넣지 않는다. NET의 MAP이 달라지면 다음 창이 달라지는 것은 동일한 기존 창 규칙의 결과다.',
        table([dict(item=k,value=x) for k,x in p['net_report'].items()]),table([v]),
        '시뮬레이션·smoke·실제 로그 재생·solver 실행은 하지 않았다. 합성 NET 동치성/실제 worker 배관/18개 실제 launcher 인자/JSON/감사 체인/report 검증만 수행했다. 기본 성공 조건은 그대로0.5m이며0.7m 도달·미선언은 보조 집계다.',
        '끝나면 docs/PHASE59P_RESULTS.md와 research/results/phase59p/에 Phase58 같은키 비교 표와 run별 top-down을 생성하고 자동 commit·push한다. Phase58 보조 항목은 그때 저장 로그에서 읽어 계산하며 기존 파일은 수정하지 않는다. 1회 기술 재시도,cache 정리,저장v2,30GB 미만 중단,공유 실행 잠금·재개를 유지한다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/phase59p_01.log`','본 실행 명령(미실행):','`'+command+'`']
    (ROOT/'docs/PHASE59P_PREP.md').write_text('\n\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',action='store_true');ap.add_argument('--validate',action='store_true');a=ap.parse_args()
    if a.freeze:freeze()
    if a.validate:validate()
if __name__=='__main__':main()
