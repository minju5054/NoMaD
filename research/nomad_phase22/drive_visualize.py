"""Saved-trace figures only; retain technical failures as labelled empty panels."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon
from nomad_phase21.visualize import load, walls, blank_panel
from .drive_config import METHODS, protocol
from .drive_geometry import corners

SHORT=('P0 A*','P1 Graph','P2F A*+Graph')
COLORS=('steelblue','darkorange','purple')


def generate(records,summary,paired,included,out):
    out=Path(out);fig,axes=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
    for row,scene in enumerate(('L2','L2B')):
        for col,key in enumerate(('goal','passage')):
            ax=axes[row,col];data=[next(r for r in summary if r['scene']==scene and r['method']==m) for m in METHODS]
            bars=ax.bar(range(3),[r[key] for r in data],color=COLORS)
            for bar,r in zip(bars,data):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.05,f"{r[key]}/{r['n']}",ha='center')
            ax.set_xticks(range(3),SHORT);ax.set_ylim(0,len(protocol()['indices'])+1)
            ax.set_title(f'{scene}: {key}');ax.set_ylabel('Count / valid paired N')
    fig.savefig(out/'outcomes.png',dpi=140);plt.close(fig)
    # Fixed seed is chosen before results; never replace it with a successful seed.
    seed=min(protocol()['indices']);selected={r['method']:load(r) for r in records if r['scene']=='L2B' and r['index']==seed}
    fig,axes=plt.subplots(3,1,figsize=(13,9),constrained_layout=True);norm=Normalize(0,90)
    for ax,method,short in zip(axes,METHODS,SHORT):
        d=selected.get(method)
        if d is None:blank_panel(ax,short);continue
        walls(ax)
        if d['spawn']:ax.add_patch(Polygon(corners(d['spawn']['obstacle']),color='purple',alpha=.25,label='Oracle box (evaluation)'))
        points=d['poses'][:,:2];segments=np.stack([points[:-1],points[1:]],axis=1)
        line=LineCollection(segments,cmap='viridis',norm=norm,linewidth=2);line.set_array(d['t'][1:]);ax.add_collection(line)
        for r in d['detours']:
            if r['event']=='TRIGGER':ax.scatter(*r['B'][:2],marker='D',c='darkorange',s=20)
            if r['event']=='APPLIED':
                q=np.array(r['path']);ax.plot(q[:,0],q[:,1],'--',c='darkorange',lw=1)
        r=d['record'];flag='; GRAPH_FALLBACK executed' if r.get('GRAPH_FALLBACK_used') else ''
        ax.set_title(f"{short}: {r.get('classification')} · goal {r.get('goal_time_s')}s · passage {r.get('box_passage_time_s')}s{flag}",fontsize=10)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=axes.tolist(),orientation='horizontal',fraction=.025,label='Simulation time (s)')
    fig.suptitle(f'L2B seed {seed}: actual trajectory; dashed = applied detour; diamonds = triggers')
    fig.savefig(out/'heldout_paths.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    metrics=(('detour_minimum_clearance_m','Minimum swept oracle clearance (m)'),('detour_execution_jerk_rms','Angular jerk RMS (rad/s³)'))
    for row,scene in enumerate(('L2','L2B')):
        for col,(key,label) in enumerate(metrics):
            ax=axes[row,col];lookup={(r['index'],r['method']):r for r in records if r['scene']==scene and (scene,r['index']) in included}
            for i,(method,color) in enumerate(zip(METHODS,COLORS)):
                rr=[r for (index,m),r in lookup.items() if m==method and r.get(key) is not None]
                ax.scatter(np.full(len(rr),i),[r[key] for r in rr],color=color)
                if rr:ax.plot([i-.15,i+.15],[np.median([r[key] for r in rr])]*2,color=color,lw=3)
                for r in rr:ax.annotate(str(r['index']),(i,r[key]),xytext=(5,0),textcoords='offset points',fontsize=8)
            for index in protocol()['indices']:
                a,b=[lookup.get((index,m),{}) for m in ('P0_ASTAR','P2F_ASTAR_GRAPH')]
                if a.get(key) is not None and b.get(key) is not None:ax.plot([0,2],[a[key],b[key]],color='.7',lw=.6,zorder=0)
            ax.set_xticks(range(3),SHORT);ax.set_xlim(-.3,2.5);ax.set_ylabel(label);ax.set_title(scene)
            if not lookup:ax.text(.5,.5,'No valid paired data',transform=ax.transAxes,ha='center')
    fig.savefig(out/'clearance_jerk.png',dpi=140);plt.close(fig)
