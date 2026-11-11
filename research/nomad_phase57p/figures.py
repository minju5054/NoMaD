"""Reuse saved-log top-down renderer; RAW intentionally has no EC log."""
from pathlib import Path
from nomad_run_plots import Inputs as FrozenInputs,load_run,topdown,extent,COLORS
from .config import ROOT

def generate(runs,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    output=Path(output);output.mkdir(parents=True,exist_ok=True);files=[]
    for r in runs:
        class Inputs(FrozenInputs):
            def rows(self,p,required=False):
                if r['method']=='NOMAD_RAW' and Path(p).name=='exec_cert.jsonl' and not Path(p).exists():return []
                return super().rows(p,required)
        inputs=Inputs();f=output/(r['key']+'.png');fig,ax=plt.subplots(figsize=(9,8));fig.subplots_adjust(bottom=.18)
        if r['technical_validation']!='PASS':
            ax.text(.5,.5,'TECHNICAL_FAILURE (no validated data)',ha='center',transform=ax.transAxes);ax.set_axis_off()
        else:
            data=load_run(r,inputs);lo,hi=extent([data]);topdown(ax,data,lo,hi)
            states=set(data['states']);handles=[Line2D([],[],color=COLORS[s],lw=2,label=s) for s in COLORS if s in states]
            if handles:fig.legend(handles=handles,loc='lower center',ncol=4,frameon=False,fontsize=8)
        fig.suptitle(f"Phase57-P | {r['scene']} | seed {r['index']} | {r['method']}")
        fig.savefig(f,dpi=150);plt.close(fig);inputs.unchanged();files.append(str(f))
    return files
