"""Individual paired patterns; recorded paths only, no counterfactual solve."""
from pathlib import Path
import csv,json
import numpy as np
from nomad_isaac.async_report import rows
from nomad_isaac.common import local_to_world,write_json

def analyze(root,aggregate,out):
    out.mkdir(exist_ok=False)
    cases=json.loads((aggregate/'individual_cases.json').read_text())
    for case in cases:
        for method,item in case['actual_runs'].items():
            run=Path(item['executed_trace']).parent;events=rows(run/'events.jsonl');clearance=rows(run/'dynamic/clearance.jsonl')
            with (run/'agent_trajectory.csv').open() as f:trace=list(csv.DictReader(f))
            poses=np.array([[float(r[k]) for k in ('x_m','y_m','yaw_rad')] for r in trace]);duration=(len(poses)-1)/72
            intervals=[]
            for i,e in enumerate(events):
                start=e['application_sim_s'];end=events[i+1]['application_sim_s'] if i+1<len(events) else duration
                swept=[r for r in clearance if r['end_sim_s']>start+1e-10 and r['end_sim_s']<=end+1e-10]
                intervals.append({'id':e['id'],'start_s':start,'end_s':end,'selected_sample':e['phase2']['selected_sample'],
                    'graph_applied':e['phase2']['graph_applied'],'B':e['agent_pose_at_switch'],
                    'first_command':[e['applied_v_m_s'],e['applied_w_rad_s']],
                    'minimum_swept_clearance_m':min((r['lower_m'] for r in swept),default=None),
                    'geometric_overlap':any(r['geometric_overlap'] for r in swept),
                    'trajectory':e['phase2']['world_xy_m'],
                    'distance_m':float(np.linalg.norm(np.diff(poses[round(start*72):round(end*72)+1,:2],axis=0),axis=1).sum())})
            violation=next((r for r in clearance if r['lower_m']<.02),None)
            first=None
            if violation:
                t=violation['end_sim_s'];active=next((r for r in reversed(intervals) if r['start_s']<t),None)
                first={'time_s':t,'pose':violation['end_pose'],'clearance_m':violation['lower_m'],'active_interval':active}
            item.update(first_margin_violation=first,actual_intervals=intervals,terminal_interval=intervals[-1],
                        graph_applied_count=sum(e['phase2']['graph_applied'] for e in events),
                        actual_selection_count=sum(e['phase2']['selected_sample']!=0 for e in events))
        case['graph_actually_applied_in_M5']=case['actual_runs']['M5']['graph_applied_count']>0
        case['causal_limit']='Different observations and spawn Y despite matched seed. Pattern alone does not establish Graph necessity or intervention harm.'
    write_json(out/'case_analysis.json',cases)
    if not cases:return
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,axes=plt.subplots(len(cases),2,figsize=(15,4*len(cases)),squeeze=False)
    colors={'M0':'#303030','M3':'#2379b5','M5':'#cd583a'}
    for row,case in enumerate(cases):
        for col,ax in enumerate(axes[row]):
            for method,item in case['actual_runs'].items():
                with Path(item['executed_trace']).open() as f:tr=list(csv.DictReader(f))
                xy=np.array([[float(r[k]) for k in ('x_m','y_m')] for r in tr]);c=colors[method]
                ax.plot(xy[:,0],xy[:,1],color=c,lw=1.5,label=f'{method}: {item["classification"]}')
                box=item['spawn']['obstacle'];center=np.array(box['center_xy_m']);sz=np.array(box['size_xyz_m'][:2]);lo=center-sz/2
                ax.add_patch(Rectangle(lo,*sz,facecolor=c,alpha=.12,edgecolor=c))
                ax.plot(*xy[-1],marker='x',color=c)
                for e in item['interventions']:
                    B=e['B'];ax.plot(B[0],B[1],marker='*' if e['graph_applied'] else 'o',ms=7 if e['graph_applied'] else 4,color=c)
                    if col==1:
                        ax.annotate(str(e['id']),(B[0],B[1]),fontsize=7,xytext=(2,4),textcoords='offset points',color=c)
                        if e['graph_applied']:
                            path=np.array(e['world_xy_m']);ax.plot(path[:,0],path[:,1],'--',color=c,alpha=.6,lw=.9)
            ax.axhline(1.5,color='gray');ax.axhline(-1.5,color='gray');ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.2)
            ax.set(xlabel='World X [m]',ylabel='World Y [m]')
            if col==0:ax.set_xlim(-.1,8.35);ax.set_ylim(-1.6,1.6);ax.scatter([0,8],[0,0],marker='+',color='black');ax.legend(fontsize=7)
            else:ax.set_xlim(1.8,4.0);ax.set_ylim(-1.1,1.1)
            pair=case['pair'];ax.set_title(f'd={pair["d_m"]} m, D={pair["D_s"]*1000:.0f} ms, index={pair["index"]} | {pair["category"]}',fontsize=9)
    fig.suptitle('Recorded closed-loop paths; circles=sample replacement, stars=applied Graph\nDashed lines=corrected chunks, boxes=method-specific actual placements; exploratory association',fontsize=11)
    fig.tight_layout(rect=(0,0,1,.95));fig.savefig(out/'individual_paths.png',dpi=180);plt.close(fig)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--aggregate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.root,a.aggregate,a.output)
