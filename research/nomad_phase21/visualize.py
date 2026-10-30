"""Small saved-result figures; technical failures remain empty labelled panels."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from nomad_phase0.chunk_report import trace
from nomad_phase20.metrics import rows
from nomad_phase20f.visualize import walls,draw_box,blank_panel
from .config import METHODS,protocol

SHORT=('RAW(ref)','SAFE_TE','SAFE_RTC','M1','ASTAR','GRAPH')

def load(record):
    root=Path(record['output'])
    if not all((root/f).is_file() for f in ('summary.json','agent_trajectory.csv','phase20_commands.jsonl','observations.jsonl')):return None
    try:
        rr,poses=trace(root)
        if not len(rr):return None
        return dict(record=record,poses=poses,t=np.array([float(r['simulation_time_s']) for r in rr]),spawn=json.loads((root/'dynamic/spawn.json').read_text()) if (root/'dynamic/spawn.json').exists() else None,
            detours=rows(root/'detour.jsonl'),repairs=rows(root/'repair.jsonl'))
    except (OSError,ValueError,KeyError):return None

def generate(records,summary,out,included):
    out=Path(out);fig,axes=plt.subplots(2,2,figsize=(14,8),constrained_layout=True)
    for row,scene in enumerate(('L2','L2A')):
        for col,key in enumerate(('goal','passed')):
            ax=axes[row,col];data=[next(r for r in summary if r['scene']==scene and r['method']==m) for m in METHODS]
            bars=ax.bar(np.arange(6),[r[key] for r in data],color=['.65','steelblue','steelblue','steelblue','darkorange','purple'])
            for bar,r in zip(bars,data):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.05,f"{r[key]}/{r['n']}",ha='center',fontsize=8)
            ax.set_xticks(range(6),SHORT,rotation=20);ax.set_ylim(0,len(protocol()['indices'])+1);ax.set_ylabel('Count / valid matched N');ax.set_title(scene+(' goal' if key=='goal' else ' box passage'))
    fig.savefig(out/'outcomes.png',dpi=140);plt.close(fig)
    seed=min(protocol()['indices']);selected={r['method']:load(r) for r in records if r['scene']=='L2A' and r['index']==seed}
    fig,axes=plt.subplots(3,2,figsize=(15,12),constrained_layout=True);norm=Normalize(0,90)
    for ax,method in zip(axes.ravel(),METHODS):
        d=selected.get(method)
        if d is None:blank_panel(ax,method);continue
        walls(ax)
        if d['spawn']:draw_box(ax,d['spawn']['obstacle'],color='purple',alpha=.25)
        segments=np.stack([d['poses'][:-1,:2],d['poses'][1:,:2]],axis=1);line=LineCollection(segments,cmap='viridis',norm=norm,linewidth=2);line.set_array(d['t'][1:]);ax.add_collection(line)
        for r in d['detours']:
            if r['event']=='TRIGGER':ax.scatter(*r['B'][:2],marker='D',c='darkorange',s=25)
            if r['event']=='APPLIED':q=np.array(r['path']);ax.plot(q[:,0],q[:,1],'--',c='darkorange',lw=1)
        ax.set_title(f"{method}: {d['record'].get('classification')} · goal {d['record'].get('goal_time_s')} · pass {d['record'].get('box_passage_time_s')}",fontsize=9)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=axes.ravel().tolist(),orientation='horizontal',fraction=.025,label='Simulation seconds')
    fig.suptitle(f'L2A seed{seed}: fixed before results; valid traces remain shown even if another method excludes the pair')
    fig.savefig(out/'heldout_seed.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
    for ax,scene in zip(axes,('L2','L2A')):
        for i,method in enumerate(('B4_ASTAR','M3_GRAPH')):
            rr=[r for r in records if r['scene']==scene and r['method']==method and (scene,r['index']) in included and r.get('curvature_rms') is not None]
            if rr:ax.scatter(np.full(len(rr),i),[r['curvature_rms'] for r in rr],label=method)
            for r in rr:ax.annotate(str(r['index']),(i,r['curvature_rms']),xytext=(5,0),textcoords='offset points',fontsize=8)
        lookup={(r['index'],r['method']):r for r in records if r['scene']==scene and (scene,r['index']) in included}
        for index in protocol()['indices']:
            a,b=[lookup.get((index,m),{}) for m in ('B4_ASTAR','M3_GRAPH')]
            if a.get('curvature_rms') is not None and b.get('curvature_rms') is not None:ax.plot([0,1],[a['curvature_rms'],b['curvature_rms']],c='.7',lw=.7)
        ax.set_xticks([0,1],['ASTAR','GRAPH']);ax.set_xlim(-.3,1.3);ax.set_title(scene);ax.set_ylabel('Applied repair/detour path Menger RMS (1/m)')
    fig.savefig(out/'curvature.png',dpi=140);plt.close(fig)
