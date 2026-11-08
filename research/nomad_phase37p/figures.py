"""Phase35-style saved-trajectory overlays; no simulator or planner imports."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Polygon,Circle,Patch
from matplotlib.lines import Line2D
from matplotlib import patheffects as pe
from matplotlib.ticker import MultipleLocator
from nomad_phase37.geometry import polygon

COLORS={'OURS':'#0072B2','OURS+PROV':'#D55E00'}
STYLES={'OURS':'solid','OURS+PROV':(0,(5,2))}

def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x] if Path(p).exists() else []

def data(row):
    p=Path(row.get('output','/nonexistent'))
    if row.get('technical_validation')!='PASS' or not all((p/f).exists() for f in ('agent_trajectory.csv','scenario.json','summary.json','geometry_check.json')):return None
    with (p/'agent_trajectory.csv').open() as f:tr=list(csv.DictReader(f))
    if not tr:return None
    t=np.array([float(r['simulation_time_s']) for r in tr]);xy=np.array([[float(r[k]) for k in ('x_m','y_m')] for r in tr]);c=read(p/'scenario.json');s=read(p/'summary.json')
    active={};intervals=[]
    for e in lines(p/'detour.jsonl'):
        if e['event']=='APPLIED':active[e['job_id']]=e['simulation_time_s']
        elif e['event']=='END' and e['job_id'] in active:intervals.append((active.pop(e['job_id']),e['simulation_time_s']))
    intervals.extend((a,t[-1]) for a in active.values())
    dynamic=s.get('dynamic_obstacle') or {};items=dynamic.get('boxes') or ([dynamic] if dynamic.get('spawn') else [])
    boxes=[polygon(item['spawn']['obstacle']) for item in items]
    return dict(row=row,t=t,xy=xy,config=c,geometry=read(p/'geometry_check.json'),intervals=intervals,boxes=boxes)

def outcome(row):
    if row.get('technical_validation')!='PASS':return 'TECHNICAL_FAILURE (no data)',None
    if row.get('success'):return 'GOAL','o'
    if row.get('collision'):return 'COLLISION','x'
    if row.get('termination')=='simulation_timeout':return 'TIMEOUT','s'
    return 'BOUNDARY / OTHER STOP','D'

def pair_plot(rows,scene,index,path,methods=('OURS','OURS+PROV')):
    by={r['method']:r for r in rows};datasets={m:data(by[m]) if m in by else None for m in methods}
    valid=[d for d in datasets.values() if d is not None]
    if not valid:return dict(scene=scene,index=index,skipped=True,reason='Both methods missing required run data')
    square=scene in ('LC','H1');fig=plt.figure(figsize=(12.6,8.2) if square else (15.2,5.8));ax=fig.add_axes([.065,.12,.62,.76] if square else [.052,.15,.69,.70])
    first=valid[0];cfg=first['config'];bounds=[]
    for lo,hi in first['geometry']['bounds'].values():
        lo=np.asarray(lo[:2]);hi=np.asarray(hi[:2]);bounds.extend([lo,hi]);ax.add_patch(Rectangle(lo,*(hi-lo),fc='#9AA0A6',ec='#6F7781',lw=.7))
    for b in cfg['obstacles']:
        points=polygon(b);bounds.extend(points);ax.add_patch(Polygon(points,fc='#D1D5DA',ec='#9198A1',lw=.8))
    seen=set()
    for d in valid:
        assert d['config']['obstacles']==cfg['obstacles'] and d['geometry']['bounds']==first['geometry']['bounds']
        for points in d['boxes']:
            key=tuple(points.ravel())
            if key in seen:continue
            seen.add(key);bounds.extend(points);ax.add_patch(Polygon(points,fc='#87509A',ec='#87509A',alpha=.18,lw=.7))
    handles=[]
    for m in methods:
        d=datasets[m];r=by.get(m,{});label,marker=outcome(r);time=f"{r['goal_time_s']:.2f}s" if r.get('success') else '—'
        if d is None:label='TECHNICAL_FAILURE\n(no data)';time='—'
        handles.append(Line2D([0],[0],color=COLORS[m],ls=STYLES[m],lw=2.3,label=f'{m}\n{label} · arrival {time}'))
        if d is None:continue
        xy=d['xy'];bounds.extend([xy.min(axis=0),xy.max(axis=0)]);ax.plot(xy[:,0],xy[:,1],color=COLORS[m],ls=STYLES[m],lw=1.7,zorder=4)
        for a,b in d['intervals']:
            tt=np.r_[a,d['t'][(d['t']>a)&(d['t']<b)],b];q=np.c_[np.interp(tt,d['t'],xy[:,0]),np.interp(tt,d['t'],xy[:,1])]
            ax.plot(q[:,0],q[:,1],color=COLORS[m],lw=4.1,zorder=6,path_effects=[pe.Stroke(linewidth=5.1,foreground='white'),pe.Normal()])
        if marker=='x':ax.scatter(*xy[-1],marker='x',color=COLORS[m],s=85,lw=2,zorder=9)
        else:ax.scatter(*xy[-1],marker=marker,facecolor='white',edgecolor=COLORS[m],s=65,lw=1.8,zorder=9)
    start=np.asarray(cfg['start_pose'][:2]);goal=np.asarray(cfg['goal_pose'][:2]);ax.add_patch(Circle(goal,cfg['goal_tolerance_m'],fill=False,ec='#59636E',ls='--',lw=.8))
    ax.scatter(*start,marker='^',c='#17222E',s=75,zorder=8);ax.scatter(*goal,marker='*',c='#17222E',s=150,zorder=8)
    for p,label,offset in ((start,'START',[-.18,-.27]),(goal,'GOAL',[.10,.29])):ax.annotate(label,p,xytext=p+offset,textcoords='data',fontsize=9,fontweight='bold',bbox=dict(fc='white',ec='none',alpha=.8,pad=1),zorder=10)
    b=np.array(bounds);ax.set_xlim(b[:,0].min()-.22,b[:,0].max()+.22);ax.set_ylim(b[:,1].min()-.22,b[:,1].max()+.22);ax.set_aspect('equal',adjustable='box')
    ax.set_xlabel('x (m)');ax.set_ylabel('y (m)');ax.xaxis.set_major_locator(MultipleLocator(1));ax.yaxis.set_major_locator(MultipleLocator(.5 if scene=='SLW' else 1));ax.grid(alpha=.2);ax.set_axisbelow(True)
    x=.72 if square else .765;fig.text(.06,.95,f'Phase 37-P | {scene} · seed {index}',fontsize=18,fontweight='bold',va='top');fig.text(.06,.898 if square else .875,'Recorded trajectories · thick segments = applied R3 detours',fontsize=10,color='#536070')
    fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(x,.85),frameon=False,handlelength=2.7,labelspacing=1.1,fontsize=10)
    symbols=[Patch(fc='#D1D5DA',ec='#9198A1',label='Walls / fixed obstacles'),Patch(fc='#87509A',alpha=.35,label='Spawned sudden box'),
        Line2D([0],[0],marker='^',color='none',markerfacecolor='#17222E',label='Start'),Line2D([0],[0],marker='*',color='none',markerfacecolor='#17222E',label='Goal (0.30m ring)'),
        Line2D([0],[0],marker='o',color='none',markeredgecolor='#46515E',label='End: goal'),Line2D([0],[0],marker='x',color='none',markeredgecolor='#46515E',label='End: collision'),
        Line2D([0],[0],marker='s',color='none',markeredgecolor='#46515E',label='End: timeout'),Line2D([0],[0],color='#46515E',lw=4.1,label='R3 execution')]
    fig.legend(handles=symbols,loc='lower left',bbox_to_anchor=(x,.12),frameon=False,fontsize=9.5)
    fig.text(.06,.035,'Saved geometry only; actual per-run sudden box positions are overlaid.',fontsize=9,color='#66707B')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=150);plt.close(fig)
    return dict(scene=scene,index=index,skipped=False,file=str(path),missing_methods=[m for m in methods if datasets[m] is None],dpi=150)
