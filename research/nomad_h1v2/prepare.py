"""Static geometry-only preparation: no renderer, solver or navigation."""
import json,hashlib,subprocess,os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Polygon,Circle
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.config import runtime_config
from nomad_phase26.scenes import place as old_place
from nomad_phase38.scenes import gap_check
from .scene import HERE,SIZE,polyline,target,nearest_nonoverlap,box_front,at,overlap_reasons,return_gap_check

def save(path,value):path.parent.mkdir(exist_ok=True,parents=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def build():
    c=runtime_config('C0',201,90,'H1');manifest=Path(c['topomap_manifest']);m=json.loads(manifest.read_text());points=np.array([n['world_pose'][:2] for n in m['nodes']])
    desired,s_desired=target(points,1.10);center,s_center,adjusted=desired,s_desired,False
    previous,previous_s=target(points,1.5)
    front_s,front=box_front(points,center);spawn_s=front_s-1.
    if spawn_s<0:raise ValueError('Box front is less than1m from reference start; cannot define requested trigger')
    spawn,i=at(points,spawn_s);delta=points[i+1]-points[i];yaw=float(np.arctan2(delta[1],delta[0]))
    box=dict(id='DynamicObstacle',center_xy_m=center.tolist(),size_xyz_m=list(SIZE))
    gap=gap_check(c,box,1);return_gap=return_gap_check(c,box);overlaps=overlap_reasons(c,center)
    previous_box=dict(id='PreviousH1v2',center_xy_m=previous.tolist(),size_xyz_m=list(SIZE))
    old_robot,_=target(points,1.2);old=old_place(c,[*old_robot,np.pi/2],0)
    assert old['status']=='PLACED'
    sources=[ROOT/'research/nomad_isaac/scenarios/phase16_lc.json',ROOT/'research/nomad_phase26/config.py',ROOT/'research/nomad_phase26/scenes.py',ROOT/'research/nomad_phase26/rendering.py',ROOT/'research/nomad_phase26/protocol.json',ROOT/'research/nomad_phase38/scenes.py',manifest]
    refs=[]
    for n in m['nodes']:
        f=manifest.parent/n['rgb_file'];assert sha256_file(f)==n['png_sha256'];refs.append(f)
    hashes={os.path.relpath(f,ROOT):sha256_file(f) for f in sources+refs}
    spec=dict(scene='H1-v2',status='GEOMETRY_PREPARED' if gap['passed'] and return_gap['passed'] and not overlaps else 'GEOMETRY_CHECK_FAIL',simulations=0,renders=0,
        frozen_geometry={k:c[k] for k in ('corridor','obstacles','start_pose','goal_pose','agent_radius_m')},
        topomap_manifest=str(manifest),topomap_sha256=sha256_file(manifest),topomap_nodes_xy_m=points.tolist(),
        source_sha256=hashes,requested_target=dict(x_hint_m=2.5,y_m=1.10,position_xy_m=desired.tolist(),arc_m=s_desired),
        box=dict(box,arc_m=s_center,yaw_rad=0.),position_adjusted_for_overlap=adjusted,
        nearest_position_rule='Fixed polyline y=1.10;no relocation on overlap,gap or return-gap failure.',
        static_overlap_reasons=overlaps,return_gap_check=return_gap,
        previous_h1v2_preview=dict(box=previous_box,arc_m=previous_s,source_commit='88fd53a',return_gap_check=return_gap_check(c,previous_box)),
        box_front=dict(position_xy_m=front.tolist(),arc_m=front_s,definition='first intersection of forward topomap node polyline with closed box footprint'),
        spawn=dict(position_xy_m=spawn.tolist(),heading_rad=yaw,arc_m=spawn_s,lead_arc_m=1.,
            rule='First72Hz tick with projected robot-center arc>=box_front_arc-1.0m,once only;projection onto stored node polyline,no actual tick/time predetermined'),
        gap_check=dict(gap,left_m=gap['gaps_m'][0],right_m=gap['gaps_m'][1],left_definition='-x (looking along+y)',right_definition='+x (looking along+y)'),
        existing_h1_preview=dict(box=old['obstacle'],spawn_pose=[*old_robot.tolist(),float(np.pi/2)],
            assumption='Zero jitter;canonical original first trigger y=1.2m. Actual H1 box y depends on actual spawn y in[1.2,1.3],so center y spans[2.49,2.59]. Existing results untouched.'),
        size_axes='world x,y,z;matches static AfterCorner0.5x0.4x0.8;no yaw/jitter;fixed position independent of seed and actual spawn pose')
    save(HERE/'scene.json',spec);return spec

def preview(p):
    c=p['frozen_geometry'];co=c['corridor'];x0,x1=co['xmin'],co['xmax'];y0,y1=co.get('ymin',-co['half_width']),co.get('ymax',co['half_width'])
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(10,8));fig.subplots_adjust(left=.09,right=.76,top=.91,bottom=.13)
    for x,y,w,h in [(x0-.1,y0-.1,.1,y1-y0+.2),(x1,y0-.1,.1,y1-y0+.2),(x0,y0-.1,x1-x0,.1),(x0,y1,x1-x0,.1)]:ax.add_patch(Rectangle((x,y),w,h,fc='#AFAFAF',ec='#737373',lw=.6))
    for o in c['obstacles']:
        center=np.asarray(o['center_xy_m']);half=np.asarray(o['size_xyz_m'][:2])/2
        ax.add_patch(Rectangle(center-half,*2*half,fc='#D2D2D2',ec='#777777',lw=1))
        ax.text(*center,o['id'],ha='center',va='center',fontsize=9,color='#555555')
    points=np.asarray(p['topomap_nodes_xy_m']);ax.plot(*points.T,'o-',ms=4,color='#0072B2',lw=1.3,label='Unchanged topomap nodes')
    for i,point in enumerate(points):ax.annotate(str(i),point,xytext=(-12,6),textcoords='offset points',color='#0072B2',fontsize=7)
    old=p['existing_h1_preview']['box'];cc=np.array(old['center_xy_m']);hh=np.array(old['size_xyz_m'][:2])/2
    ax.add_patch(Rectangle(cc-hh,*2*hh,fc='#A58ABA',ec='#6A4387',ls='--',lw=1.3,alpha=.35,label='Original H1 (nominal)'))
    previous=p['previous_h1v2_preview']['box'];pc=np.asarray(previous['center_xy_m']);ph=np.asarray(previous['size_xyz_m'][:2])/2
    ax.add_patch(Rectangle(pc-ph,*2*ph,fc='none',ec='#56B4E9',ls='--',lw=1.6,label='Previous H1-v2 (y=1.50)'))
    center=np.asarray(p['box']['center_xy_m']);half=np.asarray(SIZE[:2])/2
    ax.add_patch(Rectangle(center-half,*2*half,fc='#E69F00',ec='#A76B00',alpha=.6,lw=1.4,label='H1-v2 fixed box (y=1.10)'))
    spawn=np.asarray(p['spawn']['position_xy_m']);front=np.asarray(p['box_front']['position_xy_m'])
    ax.scatter(*spawn,marker='D',s=70,c='#D55E00',ec='white',lw=.6,zorder=8,label='Spawn arc threshold')
    ax.scatter(*front,marker='s',s=24,c='#6E4A00',zorder=8,label='Box front on polyline')
    arc=polyline(points)[1];ss=p['spawn']['arc_m'];fs=p['box_front']['arc_m']
    leg=np.vstack([spawn,points[(arc>ss)&(arc<fs)],front]);ax.plot(*leg.T,color='#D55E00',lw=3,alpha=.8,label='Exactly1.00m along path')
    ax.annotate(f"spawn ({spawn[0]:.3f}, {spawn[1]:.3f})\ns={ss:.3f}m",spawn,xytext=(1.0,-.45),arrowprops=dict(arrowstyle='->',color='#D55E00'),color='#A54100',fontsize=9)
    left,right=p['gap_check']['gaps_m'];xl=center[0]-half[0]-left;xr=center[0]+half[0]+right
    for a,b in [(xl,center[0]-half[0]),(center[0]+half[0],xr)]:ax.annotate('',xy=(a,center[1]),xytext=(b,center[1]),arrowprops=dict(arrowstyle='<->',lw=1.5,color='#009E73'))
    ax.annotate(f'left {left:.3f}m',xy=((xl+center[0]-half[0])/2,center[1]),xytext=(1.55,1.04),color='#007958',fontsize=9,
        arrowprops=dict(arrowstyle='-',color='#009E73'),bbox=dict(fc='white',ec='none',alpha=.8))
    ax.text((center[0]+half[0]+xr)/2,center[1]-.14,f'right {right:.3f}m',color='#007958',ha='center',fontsize=9)
    back=p['return_gap_check'];qa=np.asarray(back['closest_box_point_xy_m']);qb=np.asarray(back['closest_aftercorner_point_xy_m'])
    ax.annotate('',xy=qa,xytext=qb,arrowprops=dict(arrowstyle='<->',lw=1.6,color='#B04A7E'))
    ax.annotate(f"diagonal {back['diagonal_minimum_m']:.3f}m",xy=(qa+qb)/2,xytext=(3.55,1.40),ha='left',color='#963E6D',fontsize=8,
        arrowprops=dict(arrowstyle='-',color='#B04A7E'),bbox=dict(fc='white',ec='none',alpha=.85,pad=1))
    vertical_x=3.90
    ax.annotate('',xy=(vertical_x,back['top_surface_y_m']),xytext=(vertical_x,back['aftercorner_bottom_y_m']),arrowprops=dict(arrowstyle='<->',color='#B04A7E',lw=1.4))
    ax.plot([qa[0],vertical_x],[back['top_surface_y_m']]*2,':',color='#B04A7E',lw=.7)
    ax.plot([qb[0],vertical_x],[back['aftercorner_bottom_y_m']]*2,':',color='#B04A7E',lw=.7)
    ax.scatter(*c['start_pose'][:2],s=90,marker='^',c='#111111',label='Start');ax.scatter(*c['goal_pose'][:2],s=150,marker='*',c='#009E73',label='Goal')
    ax.set(xlim=(x0-.15,x1+.15),ylim=(y0-.15,y1+.15),xlabel='World x (m)',ylabel='World y (m)');ax.set_aspect('equal');ax.grid(alpha=.18)
    ax.legend(loc='upper left',bbox_to_anchor=(1.01,1.),frameon=False,fontsize=9)
    ax.text(1.01,.44,f"SIDE GAPS: {p['gap_check']['reason']}\nRequired: {p['gap_check']['required_gap_m']:.2f}m\nLeft / right: {left:.3f} / {right:.3f}m\n\nRETURN GAPS: {back['reason']}\nTop-to-AfterCorner: {back['top_to_aftercorner_m']:.3f}m\nDiagonal minimum: {back['diagonal_minimum_m']:.3f}m\n\nNew center:\n({center[0]:.6f}, {center[1]:.6f})m\nSize:0.50 x0.40 x0.80m\n\nNo simulation / render\nNo topomap regeneration",transform=ax.transAxes,va='top',fontsize=8.5)
    fig.suptitle('H1-v2 | fixed box on unchanged topomap polyline',fontsize=14)
    fig.text(.1,.035,'Original H1 dashed box: zero-jitter nominal placement at first trigger y=1.2m, not a saved run.\nSpawn marker is a reference-path coordinate; actual spawn is the first tick crossing its projected arc.',fontsize=9,color='#555555')
    path=ROOT/'docs/figures/h1v2_scene_preview.png';path.parent.mkdir(exist_ok=True);fig.savefig(path,dpi=150);plt.close(fig);return path

def document(p,test_count):
    def xy(q):return f'({q[0]:.6f}, {q[1]:.6f})'
    old=p['existing_h1_preview']['box'];new=p['box'];front=p['box_front'];spawn=p['spawn'];gap=p['gap_check'];back=p['return_gap_check'];prev=p['previous_h1v2_preview']
    table='\n'.join(['| 항목 | 좌표 / 값 | 경로 호장 s (m) |','|---|---|---:|',
        f"| H1-v2 새 중심(y=1.10) | {xy(new['center_xy_m'])} m | {new['arc_m']:.6f} |",
        '| 상자 크기 / yaw | 0.5 × 0.4 × 0.8 m (world x/y/z), 0 rad; 변경 없음 | — |',
        f"| 상자 앞면·polyline 교점 | {xy(front['position_xy_m'])} m | {front['arc_m']:.6f} |",
        f"| spawn 기준점 | {xy(spawn['position_xy_m'])} m; tangent {np.degrees(spawn['heading_rad']):.3f}° | {spawn['arc_m']:.6f} |",
        f"| 이전 H1-v2 중심(y=1.50, 점선) | {xy(prev['box']['center_xy_m'])} m | {prev['arc_m']:.6f} |",
        f"| 원 H1 기준 상자 중심 | {xy(old['center_xy_m'])} m; 1.0 × 0.4 × 0.8 m | — |",
        f"| 좌측 틈(진행 +y 기준 −x) | {gap['left_m']:.6f} m | — |",
        f"| 우측 틈(진행 +y 기준 +x) | {gap['right_m']:.6f} m | — |",
        f"| 최소 통과 폭 | 2 × 0.09 + 0.1 = {gap['required_gap_m']:.2f} m | — |"])
    comparison='\n'.join(['| 복귀 통로 검사 | 이전 y=1.50 | 새 y=1.10 | 기준 / 판정 |','|---|---:|---:|---|',
        f"| 상자 윗면 → AfterCorner 아랫면의 y 간격 | {prev['return_gap_check']['top_to_aftercorner_m']:.6f} m | {back['top_to_aftercorner_m']:.6f} m | ≥0.28m / {'PASS' if back['checks']['top_to_aftercorner'] else 'FAIL'} |",
        f"| 두 상자 표면의 최단 유클리드 거리(대각선) | {prev['return_gap_check']['diagonal_minimum_m']:.6f} m | {back['diagonal_minimum_m']:.6f} m | ≥0.28m / {'PASS' if back['checks']['diagonal_minimum'] else 'FAIL'} |",
        f"| 위 두 검사 모두 만족 | {prev['return_gap_check']['reason']} | {back['reason']} | 위치 재조정 없음 |"])
    text=f'''# H1-v2 장면 준비 — y=1.10 수정

**측면 gap {gap['reason']} / 복귀 통로 {back['reason']}.** 정적 좌표 검증만 수행했다. 시뮬레이션·depth 렌더·Topomap 재생성 0회. 기존 H1 및 다른 장면·방법 코드는 변경하지 않았다.

{table}

같은 Topomap 노드 polyline의 **y=1.10m 교점**에 중심을 고정했다. 크기·yaw·경로 호장 1.0m 전 spawn 규칙은 그대로다. 벽·정적 상자와 겹침은 없으며, overlap·gap·복귀 통로 검사 실패를 이유로 추가 위치를 찾거나 옮기지 않는다. 좌우 gap은 동결 `nomad_phase38.scenes.gap_check(axis=1)`을 직접 호출했다. 좌측은0.28m 미만이지만 우측이 기준을 만족한다.

{comparison}

복귀 통로 수치는 world 좌표의 물체 **표면 사이 폭**이다. 새 상자 윗면은 y={back['top_surface_y_m']:.3f}m, AfterCorner 아랫면은 y={back['aftercorner_bottom_y_m']:.3f}m이므로 y 간격은{back['top_to_aftercorner_m']:.3f}m이다. 두 사각형은 x방향으로도{back['horizontal_separation_m']:.6f}m 떨어져 있다. 따라서 정확한 표면 최소 거리는 `sqrt(Δx²+Δy²)`={back['diagonal_minimum_m']:.6f}m이며, 최근접 점은 새 상자 우상단{xy(back['closest_box_point_xy_m'])} ↔ AfterCorner 좌하단{xy(back['closest_aftercorner_point_xy_m'])}이다. 두 값 모두0.28m와 비교했다. 이는 우측 통과 후 복귀 구간의 **국소 정적 기하 검사**이며, PP 추종·전체 경로 완주를 시뮬레이션으로 검증한 결과는 아니다.

Spawn은 로봇 중심의 실제 pose를 동일 polyline에 투영한 호장이 `s_front−1.0m` 이상이 되는 첫72Hz tick, 단1회다. 앞면은 진행 순서상 polyline이 상자 footprint에 처음 들어가는 교점이다. 별도 반경 보정은 없다. 실제 tick·시각·pose는 미정이며 그림의 spawn 점은 경로 위 기준점이다.

![H1-v2 updated geometry preview](figures/h1v2_scene_preview.png)

주황 실선 상자는 새 위치, 하늘색 점선은 이전 H1-v2(y=1.50, 커밋 `88fd53a`), 보라 점선은 원 H1의 jitter0·기존 trigger y=1.2 기준 상자다. 원 H1 중심 `(3.6,2.49)`는 비교용 기준 배치이며 실제 과거 run 위치로 해석하지 않는다. 이전 H1-v2 좌표·복귀 검사 수치도 `scene.json`에 함께 남겼다.

구현: `research/nomad_h1v2/scene.py`, 좌표·hash: `research/nomad_h1v2/scene.json`. 기존 명시적 `configure(h1_config)` → 원 방법 초기화 → `install_environment(config)` 연결 방식은 동일하다. 복귀 검사는 보고용이며 실행기·평가기·spawn 로직을 바꾸지 않는다. 본 준비는 campaign에 연결하거나 실행하지 않는다.

기하 단위테스트 **{test_count}개 PASS**. 기존 H1 scene·Topomap15개 이미지·manifest 및 참조 코드 hash 재확인. Topomap SHA256: `{p['topomap_sha256']}`. 재생성 명령(시뮬레이션 없음): `PYTHONPATH=research /usr/bin/python3 -m nomad_h1v2.prepare`.
'''
    (ROOT/'docs/H1V2_SCENE_PREP.md').write_text(text)

def main():
    p=build();env=dict(os.environ,PYTHONPATH='research',OPENBLAS_NUM_THREADS='1')
    r=subprocess.run(['/usr/bin/python3','-m','unittest','nomad_h1v2.test_scene','-v'],cwd=ROOT,env=env,text=True,capture_output=True)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    import re
    n=int(re.search(r'Ran (\d+) tests',r.stderr).group(1));preview(p);document(p,n)
    from .scene import load_spec
    load_spec();save(HERE/'validation.json',dict(tests_passed=n,simulations=0,renders=0,original_sources_unchanged=True,gap_check=p['gap_check'],return_gap_check=p['return_gap_check'],
        source_sha256={f.name:sha256_file(f) for f in HERE.glob('*.py')},scene_sha256=sha256_file(HERE/'scene.json')))
    print(json.dumps(dict(status=p['status'],center=p['box']['center_xy_m'],spawn=p['spawn']['position_xy_m'],gaps=p['gap_check']['gaps_m'],tests=n,simulations=0)))
if __name__=='__main__':main()
