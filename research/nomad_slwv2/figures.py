"""Saved 72Hz XY only: geometry, trajectory, sudden boxes, endpoint. No replay."""
import csv
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.storage import atomic_json

def plot_run(run,metric,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Polygon
    run=Path(run);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not (run/'summary.json').exists() or not (run/'agent_trajectory.csv').exists():
        fig,ax=plt.subplots(figsize=(8,6));ax.axis('off')
        ax.text(.5,.5,'TECHNICAL_FAILURE (no data)',ha='center',va='center',transform=ax.transAxes)
        ax.set_title(f"{metric['scene']} | D{round(metric['delay']*1000):03d} | seed {metric['index']}")
        fig.savefig(path,dpi=150);plt.close(fig)
        return dict(file=str(path.relative_to(ROOT)),run=str(run),classification=metric['classification'],input_sha256={},
                    no_data=True,png_sha256=sha256_file(path))
    summary=json.loads((run/'summary.json').read_text());c=summary['scenario']
    with (run/'agent_trajectory.csv').open() as f:rows=list(csv.DictReader(f))
    xy=np.array([[float(r['x_m']),float(r['y_m'])] for r in rows]);assert len(xy)>0
    co=c['corridor'];x0,x1=co['xmin'],co['xmax'];y0,y1=co.get('ymin',-co['half_width']),co.get('ymax',co['half_width'])
    fig,ax=plt.subplots(figsize=(8,6));fig.subplots_adjust(left=.10,right=.97,bottom=.12,top=.88)
    for x,y,w,h in [(x0-.1,y0-.1,.1,y1-y0+.2),(x1,y0-.1,.1,y1-y0+.2),(x0,y0-.1,x1-x0,.1),(x0,y1,x1-x0,.1)]:
        ax.add_patch(Rectangle((x,y),w,h,fc='#B5B5B5',ec='#777777',lw=.7))
    def box(b,color,label=None):
        center=np.array(b['center_xy_m']);a,bhalf=np.array(b['size_xyz_m'][:2])/2
        yaw=float(b.get('yaw_rad',np.deg2rad(b.get('yaw_deg',0.))))
        points=np.array([[-a,-bhalf],[a,-bhalf],[a,bhalf],[-a,bhalf]])
        rot=np.array([[np.cos(yaw),-np.sin(yaw)],[np.sin(yaw),np.cos(yaw)]])
        ax.add_patch(Polygon(points@rot.T+center,fc=color,ec='#555555',alpha=.7,label=label))
    for n,b in enumerate(c.get('obstacles',[])):
        color=b['color_rgb'] if c.get('scene_variant')=='SLW-v2' else '#BBBBBB'
        box(b,color,'Static boxes' if n==0 else None)
    dynamic=summary.get('dynamic_obstacle') or {};boxes=dynamic.get('boxes',[])
    if not boxes and dynamic.get('spawn'):boxes=[dynamic]
    for n,record in enumerate(boxes):box(record['spawn']['obstacle'],'#AA4499','Sudden box' if n==0 else None)
    ax.plot(*xy.T,color='#0072B2',lw=1.6,label='Recorded 72Hz trajectory')
    ax.scatter(*xy[0],s=48,c='#009E73',marker='^',zorder=6,label='Start')
    ax.scatter(*c['goal_pose'][:2],s=90,c='#009E73',marker='*',zorder=6,label='Goal')
    marker='o' if metric.get('success') else 'X' if metric.get('collision') or metric.get('wall_intrusion') else 's'
    ax.scatter(*xy[-1],s=75,c='#222222',marker=marker,ec='white',lw=.7,zorder=7,label='End')
    ax.set(xlim=(x0-.2,x1+.2),ylim=(y0-.2,y1+.2),xlabel='World x (m)',ylabel='World y (m)')
    ax.set_aspect('equal');ax.grid(alpha=.15);ax.legend(loc='best',fontsize=8)
    ax.set_title(f"{metric['scene']} | D{round(metric['delay']*1000):03d} | seed {metric['index']}\n{metric['classification']}",fontsize=11)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=150);plt.close(fig)
    return dict(file=str(path.relative_to(ROOT)),run=str(run),classification=metric['classification'],
                input_sha256={f:sha256_file(run/f) for f in ('summary.json','agent_trajectory.csv')},png_sha256=sha256_file(path))

def run_figures(records,prefix):
    result=[]
    for r in records:
        run=Path(r['output'])
        filename=f"{prefix}_D{round(r['delay']*1000):03d}_{r['index']}.png"
        result.append(plot_run(run,r,ROOT/'docs/figures'/filename))
    return result

def add_h1v3():
    root=ROOT.parent/'artifacts/isaac6/h1v3_j0_01'
    records=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    assert len(records)==4 and {(r['index'],r['delay']) for r in records}=={(i,d) for i in (221,222) for d in (0.,.75)}
    pictures=run_figures(records,'h1v3_j0');assert len(pictures)==4
    out=ROOT/'research/results/h1v3_j0/trajectory_figures.json';atomic_json(out,dict(simulations=0,replays=0,figures=pictures))
    doc=ROOT/'docs/H1V3_J0_RESULTS.md';marker='\n## 저장 궤적 그림\n';content=doc.read_text().split(marker)[0]
    section=['기존 4회 저장 72Hz 궤적·summary의 장면/상자/종료 위치만 그렸다. 시뮬레이션·solver·평가기 재실행 없음.']
    for r,p in zip(records,pictures):section.extend([f"D{round(r['delay']*1000):03d}, seed{r['index']}: {r['classification']}",f"![saved drive](figures/{Path(p['file']).name})"])
    doc.write_text(content+marker+'\n'+'\n\n'.join(section)+'\n')
    return pictures
