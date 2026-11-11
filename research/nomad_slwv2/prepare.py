"""Freeze/dry-run only; saved H1-v3 plots are the sole data processing here."""
import copy
import json
import os
import re
import subprocess
from datetime import datetime,timezone
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from nomad_j0.config import protocol as base_protocol,verify as base_verify
from nomad_j1.depth import registration
from .config import ROOT,HERE,OUT,RUN_ROOT,REFERENCE_ROOT,TOPOMAP,METHOD,SCENES,INDICES,DELAYS,order,build_scene,checkpoint_spec,verify

def freeze():
    assert not RUN_ROOT.exists(),'No ref/nav stage may have started before registration'
    base_verify();old=base_protocol();c=build_scene();atomic_json(HERE/'scene.json',c)
    sources={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.iterdir() if f.suffix in ('.py','.json') and f.name!='protocol.json'}
    extra=['research/nomad_phase17/simulator.py','research/nomad_phase16/geometry.py','research/nomad_isaac/scenarios/phase17_slw.json',
           'research/nomad_h1v3/report.py','research/nomad_h1v3/protocol.json']
    sources.update({f:sha256_file(ROOT/f) for f in extra})
    sdf=registration(c)
    p=dict(phase='SLW-v2 J0 screen',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),planned=4,
        publish_branch='research/phase0-infrastructure',method=METHOD,indices=list(INDICES),delays_s=list(DELAYS),main_order=order(),
        source_sha256=sources,parent_j0_protocol_sha256=sha256_file(ROOT/'research/nomad_j0/protocol.json'),
        execution=copy.deepcopy(old['execution']),screening=copy.deepcopy(old['screening']),
        session_budget_s=old['session_budget_s'],technical_retries=old['technical_retries'],disk_reserve_bytes=old['disk_reserve_bytes'],
        scene_geometry=c,depth_bounds_m=sdf['registered_bounds_m'],
        reference=dict(center_to_obstacle_m=.25,center_to_wall_m=.25,spacing_sim_s=2.,
            planner='nomad_phase16.geometry.reference_path',rollout='nomad_phase16.geometry.reference_rollout',renderer='nomad_phase17.simulator reference branch',
            grid_m=.02,smooth_passes=20,speed_m_s=.2,lookahead_m=.25,max_reference_s=120,
            executed_during_prep=False,topomap_sha256='DEFERRED: sealed in resolved_assets.json after user-run reference preparation'),
        scenes={'SLW-v2':dict(topomap=str(TOPOMAP),topomap_sha256=None,checkpoint=checkpoint_spec('SLW-v2'),sdf_registration=sdf)},
        simulations_started_during_prep=0,changes=['start x0 -> -1','corridor xmin -1 -> -2','Slalom1/2/3 solid red/blue/yellow'],
        reference_preparation_in_campaign=True)
    atomic_json(HERE/'protocol.json',p);verify()

def document(v):
    from nomad_phase18.report import table
    p=verify();command=f'cd {ROOT} && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_slwv2.campaign > ../artifacts/isaac6/slwv2_j0_01.log 2>&1 < /dev/null &'
    status=f'cd {ROOT} && PYTHONPATH=research /usr/bin/python3 -m nomad_slwv2.campaign --status'
    c=p['scene_geometry'];spec=p['scenes']['SLW-v2']
    lines=['# SLW-v2 준비',table([v]),
        '기존 SLW를 보존하고 시작점x만0→−1.0m, 통로 시작벽xmin만−1→−2.0m로 연장했다. Slalom1/2/3 색만 빨강(0.85,0.08,0.08),파랑(0.08,0.20,0.85),노랑(0.95,0.80,0.04) 단색으로 바꾼다. 상자 위치·크기·통로 폭·목표·checkpoint는 동일하다.',
        table([dict(start=c['start_pose'],corridor=c['corridor'],goal=c['goal_pose'],checkpoint_x_m=4.6,start_to_checkpoint_m=5.6,sdf_bounds=spec['sdf_registration']['registered_bounds_m'])]),
        '사용자 실행 명령은 먼저 새 reference 경로를 Phase16/17 SLW의 clearance-weighted grid +20회 smoothing 절차로 계산하고, 같은 PP reference rollout을 수행한다. 그 뒤 원 Phase17 reference renderer가 새 외관으로 RGB를2초(144tick) 간격과 마지막점에서 캡처한다. 이 준비는 NoMaD 추론 없는 reference 단계이며 선별4회의 결과에 포함하지 않는다. 지금은 경로 생성·rollout·Isaac·NoMaD 모두 실행하지 않았다.',
        'Topomap/이미지는 아직 존재하지 않는다. 생성 후 reference/scenario/manifest/이미지 SHA를 resolved_assets.json에 봉인하며, 본 주행은 이 검증을 통과해야 시작한다. scene/방법/선별 protocol은 이미 FROZEN이다. reference가 실패하면 바꾸거나 재시도하지 않고 중단·보고하며, 완료된 reference는 재개 시 재사용한다.',
        '선별4회는 J0 OURS-noEC 그대로: D000 seed221,222 후 D750 seed221,222. 종료 판정은 Phase18과 동일(0.3m). 최장 SAFE+ClearanceGraph,PP/CURV,1s 만료,ENDPOINT latch; EC·회복·STOP_WAIT 특수처리·HMM/NET 없음. 선별은 0s 성공2/2 AND 0.75s checkpoint 평균>0s 평균이며 두 조건의 두 checkpoint가 모두 필요하다.',
        'J0 SDF fix 등록(벽 포함bbox+0.5m와 기존영역 합집합,원점·1cm 격자 보존)을 사용한다. 이 장면의 등록영역은 기존 [-4,-3.5,8,6.2] 그대로다. 전역 잠금·재개·30GB하한·run후cache정리·기술실패1attempt 유지.',
        '완료 시 docs/SLWV2_J0_RESULTS.md·research/results/slwv2_j0/와 4회 top-down 주행 PNG를 자동 생성·commit·push한다. 실행/자동push 브랜치는 research/phase0-infrastructure이며 명령의 cwd는 원래 저장소다.',
        'H1-v3 기존4회 그림은 저장된 trajectory/summary만 읽어 docs/H1V3_J0_RESULTS.md에 추가했다. 과거 metrics·판정·코드·시뮬레이션은 재실행/변경하지 않았다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/slwv2_j0_01.log`','미실행 명령(reference 준비 포함):','`'+command+'`']
    (ROOT/'docs/SLWV2_SCENE_PREP.md').write_text('\n\n'.join(lines)+'\n')
    atomic_json(OUT/'preparation/commands.json',dict(campaign=command,status=status,executed=False))

def main():
    freeze();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-slwv2-mpl')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_slwv2.test_scene','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-6000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_slwv2.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    launches=[json.loads(subprocess.check_output([*j['argv'],'--dry-run'],cwd=ROOT,env=env,text=True)) for j in dry['jobs']]
    atomic_json(folder/'dry_run.json',dict(campaign=dry,launches=launches))
    from .figures import add_h1v3
    pictures=add_h1v3()
    v=dict(tests=int(re.search(r'Ran (\d+) tests',r.stderr).group(1)),launcher_dry_runs=4,reference_launch_planned=True,
        reference_rollouts_executed=0,simulations=0,inference=0,H1v3_saved_trajectory_figures=len(pictures),protocol_sha256=sha256_file(HERE/'protocol.json'))
    atomic_json(folder/'validation.json',v);document(v)
    from .report import generate
    generate();print(json.dumps(v))

if __name__=='__main__':main()
