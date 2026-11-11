"""Static geometry + four launcher dry-runs only. Never starts Isaac."""
import copy
import json
import os
import re
import subprocess
from datetime import datetime,timezone
import numpy as np
from nomad_isaac.common import sha256_file
from nomad_phase26.storage import atomic_json
from nomad_j0.config import protocol as base_protocol,verify as base_verify
from nomad_j1.depth import registration
from .config import ROOT,HERE,OUT,RUN_ROOT,SCENES,INDICES,DELAYS,METHOD,order,checkpoint_spec,scene_config,verify
from .scene import build_spec,load_spec

def freeze():
    assert not RUN_ROOT.exists()
    base_verify();spec=build_spec();atomic_json(HERE/'scene.json',spec)
    assert spec['status']=='GEOMETRY_PREPARED',spec['static_checks']
    c,topomap=scene_config('H1-v3');old=base_protocol()
    sources={str(f.relative_to(ROOT)):sha256_file(f) for f in HERE.iterdir() if f.suffix in ('.py','.json') and f.name!='protocol.json'}
    p=dict(phase='H1-v3 J0 screen',status='FROZEN',frozen_at_utc=datetime.now(timezone.utc).isoformat(),planned=4,
        publish_branch='feat/h1-v3-screening',method=METHOD,indices=list(INDICES),delays_s=list(DELAYS),main_order=order(),
        parent_j0_protocol_sha256=sha256_file(ROOT/'research/nomad_j0/protocol.json'),source_sha256=sources,
        execution=copy.deepcopy(old['execution']),screening=copy.deepcopy(old['screening']),
        session_budget_s=old['session_budget_s'],technical_retries=old['technical_retries'],disk_reserve_bytes=old['disk_reserve_bytes'],
        scenes={'H1-v3':dict(topomap=topomap,topomap_sha256=sha256_file(topomap),checkpoint=checkpoint_spec('H1-v3'),
            sdf_registration=registration(c),scene_sha256=sha256_file(HERE/'scene.json'))},
        simulations_started_during_prep=0,scene_change='Only sudden-box center on same node polyline; y=.70, single .65 adjustment only for corner overlap',
        adjustment=spec['requested_target'])
    atomic_json(HERE/'protocol.json',p);verify()

def preview(p):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from nomad_h1v2.scene import polyline
    c=p['frozen_geometry'];co=c['corridor'];x0,x1=co['xmin'],co['xmax'];y0,y1=co['ymin'],co['ymax']
    plt.rcParams.update({'font.size':10})
    fig,ax=plt.subplots(figsize=(10,8));fig.subplots_adjust(left=.08,right=.74,top=.92,bottom=.10)
    for x,y,w,h in [(x0-.1,y0-.1,.1,y1-y0+.2),(x1,y0-.1,.1,y1-y0+.2),(x0,y0-.1,x1-x0,.1),(x0,y1,x1-x0,.1)]:
        ax.add_patch(Rectangle((x,y),w,h,fc='#999999',ec='#666666',lw=.6))
    for obj in c['obstacles']:
        mid=np.array(obj['center_xy_m']);half=np.array(obj['size_xyz_m'][:2])/2
        ax.add_patch(Rectangle(mid-half,*2*half,fc='#cccccc',ec='#777777'))
        ax.text(*mid,obj['id'],ha='center',va='center',fontsize=9,color='#444444')
    points=np.array(p['topomap_nodes_xy_m']);ax.plot(*points.T,'o-',color='#0072B2',ms=4,lw=1.1,label='Frozen topomap nodes')
    for i,q in enumerate(points):ax.annotate(str(i),q,xytext=(-10,6),textcoords='offset points',fontsize=7,color='#0072B2')
    previous=p['previous_h1v2_preview']['box'];a=np.array(previous['center_xy_m']);half=np.array(previous['size_xyz_m'][:2])/2
    ax.add_patch(Rectangle(a-half,*2*half,fc='none',ec='#7B3294',ls='--',lw=1.8,label='H1-v2 (y=1.10)'))
    center=np.array(p['box']['center_xy_m']);half=np.array(p['box']['size_xyz_m'][:2])/2
    ax.add_patch(Rectangle(center-half,*2*half,fc='#E69F00',ec='#996500',alpha=.65,label=f"H1-v3 (y={center[1]:.2f})"))
    spawn=np.array(p['spawn']['position_xy_m']);front=np.array(p['box_front']['position_xy_m'])
    ax.scatter(*spawn,c='#D55E00',marker='D',s=65,zorder=8,label='Spawn threshold')
    ax.scatter(*front,c='#996500',marker='s',s=28,zorder=8,label='Box front on path')
    _,arc=polyline(points);segment=np.vstack([spawn,points[(arc>p['spawn']['arc_m'])&(arc<p['box_front']['arc_m'])],front])
    ax.plot(*segment.T,c='#D55E00',lw=2.7,alpha=.8,label='1.00m arc before box')
    ax.scatter(2.4,.9,c='#000000',marker='+',s=65,zorder=10,label='Wall-block corner')
    ax.annotate(f"spawn ({spawn[0]:.3f}, {spawn[1]:.3f})",spawn,xytext=(.9,-.5),fontsize=8,
        arrowprops=dict(arrowstyle='->',color='#D55E00'),color='#A54100')
    right=p['gap_check']['right_m'];edge=center[0]+half[0]
    ax.annotate('',xy=(edge,center[1]),xytext=(edge+right,center[1]),arrowprops=dict(arrowstyle='<->',color='#009E73',lw=1.5))
    ax.text(edge+right/2,center[1]-.14,f'right {right:.3f}m',ha='center',color='#007958',fontsize=9)
    back=p['return_gap_check'];qa=np.array(back['closest_box_point_xy_m']);qb=np.array(back['closest_aftercorner_point_xy_m'])
    ax.annotate('',xy=qa,xytext=qb,arrowprops=dict(arrowstyle='<->',color='#A23B72',lw=1.5))
    ax.annotate(f"surface {back['diagonal_minimum_m']:.3f}m",(qa+qb)/2,xytext=(3.45,1.25),fontsize=8,color='#A23B72',
        arrowprops=dict(arrowstyle='-',color='#A23B72'),bbox=dict(fc='white',ec='none',alpha=.8))
    ax.scatter(*c['start_pose'][:2],c='#111111',marker='^',s=80,label='Start')
    ax.scatter(*c['goal_pose'][:2],c='#009E73',marker='*',s=140,label='Goal')
    ax.set(xlim=(x0-.15,x1+.15),ylim=(y0-.15,y1+.15),xlabel='World x (m)',ylabel='World y (m)');ax.set_aspect('equal');ax.grid(alpha=.15)
    ax.legend(loc='upper left',bbox_to_anchor=(1.02,1.),frameon=False,fontsize=9)
    ax.text(1.02,.40,f"STATIC CHECK: PASS\nCenter: ({center[0]:.6f}, {center[1]:.2f})m\nRight gap: {right:.6f}m (>=0.28)\nTop-to-AfterCorner: {back['top_to_aftercorner_m']:.6f}m\nSurface minimum: {back['diagonal_minimum_m']:.6f}m\nAdjustment: {p['requested_target']['adjustments']}\n\nGeometry only\nNo simulation or render\nSame topomap and reference",transform=ax.transAxes,va='top',fontsize=8.5)
    fig.suptitle('H1-v3 | static geometry preview',fontsize=14)
    path=ROOT/'docs/figures/h1v3_scene_preview.png';path.parent.mkdir(exist_ok=True);fig.savefig(path,dpi=150);plt.close(fig)
    return path

def document(p,v):
    from nomad_phase18.report import table
    b=p['box'];front=p['box_front'];spawn=p['spawn'];g=p['gap_check'];back=p['return_gap_check']
    command=f'cd {ROOT} && nohup env -u LD_LIBRARY_PATH -u LD_PRELOAD -u PYTHONHOME -u VIRTUAL_ENV PYTHONPATH=research OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -u -m nomad_h1v3.campaign > ../artifacts/isaac6/h1v3_j0_01.log 2>&1 < /dev/null &'
    status=f'cd {ROOT} && PYTHONPATH=research /usr/bin/python3 -m nomad_h1v3.campaign --status'
    values=[dict(item='H1-v3 center',value=b['center_xy_m'],arc_m=b['arc_m']),dict(item='size / yaw',value='0.5 x 0.4 x 0.8m / 0rad',arc_m=None),
        dict(item='front/polyline intersection',value=front['position_xy_m'],arc_m=front['arc_m']),dict(item='spawn threshold',value=spawn['position_xy_m'],arc_m=spawn['arc_m']),
        dict(item='right passage width',value=g['right_m'],arc_m=None),dict(item='top-to-AfterCorner y gap',value=back['top_to_aftercorner_m'],arc_m=None),
        dict(item='minimum surface distance',value=back['diagonal_minimum_m'],arc_m=None),dict(item='checkpoint +y',value=checkpoint_spec('H1-v3')['threshold_m'],arc_m=None)]
    lines=['# H1-v3 장면 및 J0 선별 준비',table([v]),table(values),
        f"같은 Topomap polyline의 y={b['center_xy_m'][1]:.2f} 교점으로 돌발 상자 중심만 옮겼다. 벽·정적 상자와 겹침 없음, 우측 통과 폭≥0.28m 확인. (2.4,0.9) 모서리와 겹치지 않아 y=0.65 조정은 사용하지 않았다(조정{p['requested_target']['adjustments']}회). 크기·yaw·벽·정적 상자·Topomap·reference는 H1-v2와 동일하며 기존 코드·결과를 변경하지 않았다.",
        'Spawn은 원 H1-v2 monitor를 그대로 사용한다. 로봇 중심을 노드 polyline에 투영한 호장이 상자 앞면 첫 교점 호장−1.0m 이상인 첫72Hz tick에1회 생성한다. 그림의 spawn 점은 경로 위 기준점이며 실제 spawn pose를 미리 정한 것은 아니다.',
        '![H1-v3 preview](figures/h1v3_scene_preview.png)',
        '점선 보라 상자는 기존 H1-v2(y=1.10), 주황 상자는 H1-v3다. 측면 폭과 AfterCorner 표면 간 거리는 정적 기하 수치이며, 실제 우회·복귀 주행 성공을 주장하지 않는다.',
        '선별은 J0의 OURS-noEC 하나만 사용: Phase18 PP/CURV·0.3m 참위치 도착·공식 NoMaD closest/subgoal·1s 만료·depth SAFE 최장 선택+동결 ClearanceGraph·ENDPOINT latch. EC·HMM/NET·회복·STOP_WAIT 특수처리 없음. 장면별 SDF 등록 범위 수정도 동일하게 재사용한다.',
        '4회 순서: D000 seed221 → D000 seed222 → D750 seed221 → D750 seed222. 기준은 0s 성공2/2 AND 0.75s checkpoint 시간 평균>0s 평균. 두 seed가 양 조건에서 모두 checkpoint를 기록해야 하며 결측 대체 없음. checkpoint는 돌발 상자 +y 먼 면+0.30m를 중심이 처음 넘는72Hz 시점이다.',
        '실행은 미실행. 완료 시 docs/H1V3_J0_RESULTS.md와 research/results/h1v3_j0/를 자동 생성·commit·push한다. 별도 브랜치 feat/h1-v3-screening, 새 run-root h1v3_j0_01. J0의 잠금·재개·기술 실패1attempt·cache정리·디스크30GB하한을 그대로 사용한다.',
        '진행 확인: `'+status+'`','로그: `../artifacts/isaac6/h1v3_j0_01.log`','미실행 명령:','`'+command+'`']
    (ROOT/'docs/H1V3_SCENE_PREP.md').write_text('\n\n'.join(lines)+'\n')
    atomic_json(OUT/'preparation/commands.json',dict(campaign=command,status=status,executed=False))

def main():
    freeze();folder=OUT/'preparation';folder.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MPLCONFIGDIR='/tmp/nomad-h1v3-mpl')
    tests=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_h1v3.test_scene','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    (folder/'tests.txt').write_text(tests.stdout+tests.stderr);assert tests.returncode==0,tests.stderr[-6000:]
    dry=json.loads(subprocess.check_output(['/usr/bin/python3','-m','nomad_h1v3.campaign','--dry-run'],cwd=ROOT,env=env,text=True))
    launches=[json.loads(subprocess.check_output([*j['argv'],'--dry-run'],cwd=ROOT,env=env,text=True)) for j in dry['jobs']]
    assert len(launches)==4 and all(x['simulations_started']==0 for x in launches)
    atomic_json(folder/'dry_run.json',dict(campaign=dry,launches=launches))
    p=load_spec();preview(p)
    v=dict(status=p['status'],tests=int(re.search(r'Ran (\d+) tests',tests.stderr).group(1)),launcher_dry_runs=4,
        simulations=0,renders=0,protocol_sha256=sha256_file(HERE/'protocol.json'),topomap_sha256=p['topomap_sha256'])
    atomic_json(folder/'validation.json',v);document(p,v)
    from .report import generate
    generate();print(json.dumps(v))

if __name__=='__main__':main()
