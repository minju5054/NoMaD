"""Saved top-down run figures only; raw candidates and applied R2/R3/HO paths."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from nomad_run_plots import Inputs,load_run,topdown,extent,COLORS,CUT,GRAPH,REJECT
from nomad_h1v2_trial.figures import candidates
from .config import ROOT,EXP

def generate(runs):
    out=ROOT/'docs/figures';out.mkdir(exist_ok=True);inputs=Inputs();files=[]
    for r in runs:
        f=out/f"night20261111_{EXP}_{r['key']}.png";fig,ax=plt.subplots(figsize=(9,8));fig.subplots_adjust(left=.1,right=.95,top=.88,bottom=.2)
        if r['technical_validation']!='PASS':
            ax.text(.5,.5,'TECHNICAL_FAILURE (no validated data)',transform=ax.transAxes,ha='center');ax.set_axis_off()
        else:
            d=load_run(r,inputs);native,info=candidates(d,inputs)
            for path in native:ax.plot(*np.asarray(path).T,color='#777F9C',lw=.5,alpha=.05,zorder=3)
            applications=[e for e in inputs.rows(d['root']/'repair.jsonl') if e['event']=='PATH_APPLIED']
            assert len(applications)==len(d['plans'])
            repairs=[];detours=[];normal=[]
            for p,a in zip(d['plans'],applications):
                if a['kind']=='DETOUR':detours.append(p)
                elif a['kind']=='REPAIR':repairs.append(p)
                else:normal.append(p)
            lo,hi=extent([d]);display=dict(d,plans=normal);topdown(ax,display,lo,hi)
            for p in repairs:ax.plot(*p['points'].T,color='#7E57A1',ls=':',lw=1.2,alpha=.55,zorder=5)
            for p in detours:ax.plot(*p['points'].T,color='#1565C0',ls='-',lw=1.4,alpha=.65,zorder=5)
            ax.text(.01,.97,f"R2 {len(repairs)} / R3 {len(detours)} | raw {info['candidates']} paths",transform=ax.transAxes,va='top',fontsize=8)
            states=set(d['states']);handles=[Line2D([],[],color=COLORS.get(s,COLORS['OTHER']),lw=2.5,label=s) for s in COLORS if s in states]
            handles += [Line2D([],[],color=CUT,ls=':',label='CUT installed'),Line2D([],[],color=GRAPH,ls='--',label='GRAPH handoff'),
                Line2D([],[],color='#1565C0',label='R3 detour'),Line2D([],[],color='#7E57A1',ls=':',label='R2 repair'),
                Line2D([],[],color='#777F9C',alpha=.3,label='raw8 candidates'),Line2D([],[],color=REJECT,marker='x',ls='',label='EC REJECT')]
            fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.03),ncol=4,frameon=False,fontsize=8)
        fig.suptitle(f"{EXP} | {r['scene']} | seed{r['index']}",fontsize=13);fig.savefig(f,dpi=150);plt.close(fig);files.append(str(f))
    inputs.unchanged();return dict(files=files,input_files=inputs.files,simulations=0,reevaluation=0)
