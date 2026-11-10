"""Top-down saved-log plots only; no timeline, solver or EC recomputation."""
import hashlib,io,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from nomad_isaac.common import local_to_world
from nomad_run_plots import Inputs,load_run,topdown,extent,COLORS,CUT,GRAPH,REJECT
from .config import ROOT,OUT,CONDITIONS,METHODS

def candidates(d,inputs):
    records=inputs.rows(d['root']/'received.jsonl',True);paths=[];missing=[];seen=set()
    for e in records:
        if e.get('terminal_unapplied') or e.get('latched_sim_s') is None or e['latched_sim_s']>d['t'][-1]+1e-9:continue
        if e['id'] in seen:continue
        seen.add(e['id']);p=d['root']/'model/derived'/f"{e['id']:04d}.npz"
        if not p.exists():missing.append(e['id']);continue
        raw=p.read_bytes();st=p.stat();inputs.files[str(p)]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=st.st_size,mtime_ns=st.st_mtime_ns)
        with np.load(io.BytesIO(raw),allow_pickle=False) as z:metric=z['metric'].copy()
        assert metric.ndim==3 and metric.shape[0]==8 and metric.shape[2]==2
        paths.extend(local_to_world(p,e['observation_pose']) for p in metric)
    return paths,dict(chunks=len(seen),candidates=len(paths),missing_chunk_ids=missing)

def panel(ax,d,lo,hi):
    for path in d['native_candidates']:ax.plot(*np.asarray(path).T,color='#777F9C',lw=.5,alpha=.065,zorder=3)
    nodes=np.asarray(d['topomap_nodes']);ax.plot(*nodes.T,ls=':',marker='o',ms=3,mfc='white',mec='#2C6897',color='#2C6897',alpha=.7,lw=.7,zorder=3.5)
    topdown(ax,d,lo,hi)
    if not d['boxes']:
        box=d['cfg']['h1v2']['box'];center=np.array(box['center_xy_m']);half=np.array(box['size_xyz_m'][:2])/2
        ax.add_patch(Rectangle(center-half,*2*half,fill=False,ec='#9566AE',ls='--',lw=1.2,zorder=3))
        ax.annotate('box NOT SPAWNED',center,xytext=(5,6),textcoords='offset points',fontsize=7,color='#663780')
    else:
        for b in d['boxes']:
            if b.get('pose') is not None:ax.scatter(*b['pose'][:2],marker='D',s=35,fc='#9566AE',ec='white',lw=.5,zorder=10)
    info=d['candidate_info']
    ax.text(.01,.96,f"raw candidates: {info['candidates']} / {info['chunks']} chunks"+(f"; missing {len(info['missing_chunk_ids'])}" if info['missing_chunk_ids'] else ''),
        transform=ax.transAxes,va='top',fontsize=7,bbox=dict(fc='white',ec='none',alpha=.85),zorder=15)

def legends(fig,data,y=.025,ncol=5):
    states={s for d in data for s in d['states']}
    handles=[Line2D([],[],color=COLORS.get(s,COLORS['OTHER']),lw=2.5,label=s) for s in COLORS if s in states]
    handles.extend([Line2D([],[],color=CUT,ls=':',label='installed CUT'),Line2D([],[],color=GRAPH,ls='--',label='installed GRAPH'),
        Line2D([],[],color='#777F9C',lw=.7,alpha=.4,label='raw8 candidates / chunk'),Line2D([],[],color='#2C6897',marker='o',mfc='white',ms=3,ls=':',label='topomap nodes'),
        Line2D([],[],color=REJECT,ls='',marker='x',label='EC REJECT'),Line2D([],[],color='#9566AE',ls='',marker='D',label='robot at box spawn')])
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,y),ncol=ncol,frameon=False,fontsize=8)

def generate(runs,output=None):
    output=Path(output) if output else ROOT/'docs/figures';output.mkdir(exist_ok=True,parents=True)
    inputs=Inputs();data=[];by={};paths=[];details=[]
    for r in runs:
        if r['technical_validation']!='PASS':continue
        d=load_run(r,inputs);d['native_candidates'],d['candidate_info']=candidates(d,inputs)
        manifest=inputs.json(Path(d['cfg']['topomap_manifest']));d['topomap_nodes']=[n['world_pose'][:2] for n in manifest['nodes']]
        data.append(d);by[(r['condition'],r['method'])]=d
        details.append(dict(key=r['key'],**d['candidate_info'],installed_paths=len(d['plans']),graph_paths=sum(p['graph'] for p in d['plans'])))
    if not runs:return dict(files=[],details=[],input_files={})
    if data:lo,hi=extent(data)
    else:lo,hi=np.array([-1.2,-1.2]),np.array([4.4,4.4])
    for r in runs:
        fig,ax=plt.subplots(figsize=(8.5,8.5));fig.subplots_adjust(left=.10,right=.94,top=.88,bottom=.20)
        d=by.get((r.get('condition',r['scene'].rsplit('_',1)[1]),r['method']))
        if d:panel(ax,d,lo,hi);legends(fig,[d],ncol=4)
        else:ax.text(.5,.5,'TECHNICAL_FAILURE (no validated data)',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off()
        fig.suptitle(f"H1-v2 trial | {r['scene'].rsplit('_',1)[1]} | seed221",fontsize=13)
        f=output/f"h1v2_trial_{r['key']}.png";fig.savefig(f,dpi=150);plt.close(fig);paths.append(f)
    fig,axes=plt.subplots(2,2,figsize=(15,14));fig.subplots_adjust(left=.06,right=.97,top=.91,bottom=.14,wspace=.22,hspace=.26)
    for row,condition in enumerate(CONDITIONS):
        for col,method in enumerate(METHODS):
            ax=axes[row,col];d=by.get((condition,method))
            if d:panel(ax,d,lo,hi);ax.set_title(condition+' | '+ax.get_title(),fontsize=10)
            else:
                failed=any(r['method']==method and r['scene'].endswith(condition) for r in runs)
                ax.text(.5,.5,'TECHNICAL_FAILURE (no validated data)' if failed else 'NOT_RUN',ha='center',va='center',transform=ax.transAxes);ax.set_title(condition+' | '+method);ax.set_axis_off()
    fig.suptitle('H1-v2 trial | unchanged Phase53-P CUT / GRAPH-HO | seed221',fontsize=15)
    legends(fig,data,y=.035,ncol=6)
    f=output/'h1v2_trial_all.png';fig.savefig(f,dpi=150);plt.close(fig);paths.append(f)
    inputs.unchanged();return dict(files=[str(p) for p in paths],details=details,input_files=inputs.files)
