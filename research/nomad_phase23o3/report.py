"""Training-only U3 selection evidence and the registered online gate."""
import json
from collections import Counter
import numpy as np
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase23.report import csv_write
from nomad_phase17.report import table
from nomad_phase23o2.inputs import read,write
from nomad_phase23o2.report import plan_passage

HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase23o3'
DEFINITION=r'''
## U3 definition

U3 preserves frozen U2 factors, Cauchy c=1, acceleration sigma0.05, and time/goal/curvature weights1/1/0.01. Only F7 and the specified output policy are added. Eight current policy starts plus available depth-side starts,4workers, SLSQP maxiter100/ftol1e-8,500ms anytime and the frozen computation-window rollout remain unchanged. No A*, u_ref, odometry history, trigger, Topomap or new-obstacle classifier enters U3.

For each current/memory component j, use its B-frame endpoint displacement e_j. Exclude only from the F7 direction average those with |e_j|<0.05m. Direction is the unit vector of sum_j exp(-tau_j/T_m) e_j/|e_j|. No valid endpoint, or an exactly canceled mean (numerical norm<=1e-12), leaves direction mathematically undefined and F7 inactive. No substitute heading is introduced. The original mixture still retains all candidates.

$$F_7=w_7[\max(0,1.2-(p_{10}-p_0)\cdot\hat d)/0.10]^2.$$

Direction is fixed from observed inputs during each solve, so its active derivative is $-2w_7r\hat d^T(J_{p10}-J_{p0})/0.10$. Grid:w7 in{0.5,1,2} × T_m in{0.5,1,2}s; c=1fixed. No other tuning.

Output first selects the lowest-cost strict feasible iterate received within500ms, as before. Only if none exists, it considers the last available iterate from each start: every F2 node/midpoint inequality must have nonnegative slack; v<=0.33, |omega|<=0.44 and dt in[0.045,1.10]. It picks the lowest-cost qualified last iterate. A later unsafe iterate invalidates that start's earlier tolerated iterate. These are output tolerances only: the optimizer's original hard bounds and constraints are unchanged. All late messages are discarded. FEASIBLE / KINEMATIC_TOLERATED / STOP are recorded. The frozen executor still clips v<=0.3, |omega|<=0.4 and acceleration<=0.5. STOP brakes only after the fixed0.5s computation prefix.

Selection uses only the unchanged242training snapshots(216static,26sudden): timing p95<=0.5s, then minimum rollout collisions, maximum collision-free planned box-passage fraction on26sudden inputs, minimum STOP fraction, maximum static progress median, minimum p50 (fixed grid index only breaks exact ties). As in the prior protocol, if no timing-eligible setting exists, minimum p95 is retained for diagnosis and timing necessarily fails the gate. No evaluation-set snapshot is solved.

U2 uses its frozen selected training outputs. C0 is computed on the same242inputs, and C1 on the same26sudden inputs. They retain frozen23-O timing and rollout. For the comparators, the FEASIBLE column denotes their original accepted-path output, not an added U3 certificate; C1's ALL row contains only26sudden inputs. The path-passage metric is unchanged from23-O2: an output path reaches beyond the box rear with its footprint and has no oracle box/wall overlap. Rollout passage is also shown separately. All output failures remain in denominators.

Gate GO_ONLINE requires: U3 sudden planned-passage fraction>=0.8*C0, total U3 rollout collisions<=C0 across242inputs, total STOP fraction<=10%, and total compute p95<=0.5s. Otherwise NO_GO. These are training-set diagnostics used for selection, not held-out performance or closed-loop evidence.
'''

def scores(records,grid):
    out=[]
    for i,setting in enumerate(grid):
        rr=[r['methods'][f'U3_{i:02d}']['row'] for r in records];sudden=[r for r in rr if r['group']=='sudden'];static=[r for r in rr if r['group']=='static']
        out.append(dict(index=i,settings=setting,n=len(rr),collisions=sum(r['oracle_collision'] for r in rr),sudden_planned_passage_fraction=float(np.mean([bool(r['planned_box_passage']) for r in sudden])),stop_fraction=float(np.mean([r['output_type']=='STOP' for r in rr])),
            static_progress_median=float(np.median([r['progress'] for r in static])),p95=float(np.quantile([r['compute_s'] for r in rr],.95)),p50=float(np.median([r['compute_s'] for r in rr]))))
    return out

def select(table_rows):
    eligible=[r for r in table_rows if r['p95']<=.5]
    winner=min(eligible,key=lambda r:(r['collisions'],-r['sudden_planned_passage_fraction'],r['stop_fraction'],-r['static_progress_median'],r['p50'],r['index'])) if eligible else min(table_rows,key=lambda r:(r['p95'],r['index']))
    for row in table_rows:row.update(timing_eligible=row['p95']<=.5,selected=row['index']==winner['index'])
    return winner,dict(all_over_time=not eligible,table=table_rows)

def summaries(rows):
    result=[]
    for group in ('static','sudden','ALL'):
        for method in ('U3','U2','C0','C1'):
            rr=[r for r in rows if r['method']==method and (group=='ALL' or r['group']==group)]
            if not rr:continue
            median=lambda k:float(np.median([r[k] for r in rr if r.get(k) is not None])) if any(r.get(k) is not None for r in rr) else None
            sudden=[r for r in rr if r['group']=='sudden'];counts=Counter(r['output_type'] for r in rr)
            result.append(dict(group=group,method=method,n=len(rr),collisions=sum(r['oracle_collision'] for r in rr),outputs=dict(counts),
                feasible_fraction=counts['FEASIBLE']/len(rr),tolerated_fraction=counts['KINEMATIC_TOLERATED']/len(rr),stop_fraction=counts['STOP']/len(rr),
                planned_box_passage=sum(bool(r['planned_box_passage']) for r in sudden),sudden_n=len(sudden),planned_box_passage_fraction=float(np.mean([bool(r['planned_box_passage']) for r in sudden])) if sudden else None,
                rollout_box_passage=sum(r['box_passage'] for r in sudden),progress_median=median('progress'),omega_saturation_median=median('omega_saturation_fraction'),compute_p50_s=median('compute_s'),compute_p95_s=float(np.quantile([r['compute_s'] for r in rr],.95)),
                f7_enabled_fraction=float(np.mean([r['f7_enabled'] for r in rr])) if method=='U3' else None,
                f7_positive_residual_fraction=float(np.mean([r['f7_positive_residual'] for r in rr if r.get('f7_positive_residual') is not None])) if any(r.get('f7_positive_residual') is not None for r in rr) else None,
                prior_departure_030_fraction=float(np.mean([r['prior_departure_030'] for r in rr if r.get('prior_departure_030') is not None])) if any(r.get('prior_departure_030') is not None for r in rr) else None))
    return result

def gate(summary):
    get=lambda g,m:next(r for r in summary if r['group']==g and r['method']==m)
    u,b=get('ALL','U3'),get('ALL','C0');us,bs=get('sudden','U3'),get('sudden','C0')
    flags=dict(planned_passage=us['planned_box_passage_fraction']>=.8*bs['planned_box_passage_fraction'],collision=u['collisions']<=b['collisions'],stop=u['stop_fraction']<=.10,timing=u['compute_p95_s']<=.5)
    return dict(label='GO_ONLINE' if all(flags.values()) else 'NO_GO',conditions=flags,failed=[k for k,v in flags.items() if not v],U3=u,C0=b,sudden_U3=us,sudden_C0=bs)

def selection_report(p):
    (ROOT/'docs/PHASE23O3_UNIFIED.md').write_text('# Phase23-O3 — frozen training selection\n\n'+DEFINITION+'\n## Selection evidence\n\n'+table(p['selection_evidence']['table'])+f"\n\nSelected: {p['selected']}. Gate report pending; no online run authorized by this file.\n")

def generate(p,m):
    rows=[];examples={};index=p['selected_index']
    for c in m['training']:
        training=read(OUT/'training'/(c['case_id']+'.json'));base=read(OUT/'comparators'/(c['case_id']+'.json'));methods=dict(base['methods']);methods['U3']=training['methods'][f'U3_{index:02d}']
        for name,value in methods.items():rows.append(dict(value['row'],method=name))
        if c['case_id'] in m['figures']:examples[c['case_id']]=dict(case=c,methods=methods)
    summary=summaries(rows);verdict=gate(summary);csv_write(OUT/'snapshots.csv',rows);csv_write(OUT/'summary.csv',summary);write(OUT/'gate.json',verdict)
    images=plots(examples,m['figures']);overview=('group','method','n','collisions','feasible_fraction','tolerated_fraction','stop_fraction','planned_box_passage','sudden_n','planned_box_passage_fraction','rollout_box_passage','progress_median','omega_saturation_median','compute_p50_s','compute_p95_s')
    extra=('group','method','f7_enabled_fraction','f7_positive_residual_fraction','prior_departure_030_fraction')
    text='# Phase23-O3 — training-only offline check\n\n'+DEFINITION+f"\nProtocol SHA256 `{sha256_file(HERE/'protocol.json')}`; selected `{p['selected']}`.\n\n"
    text+='## Tuning evidence\n\n'+table(p['selection_evidence']['table'])+'\n\n## Same-input comparisons\n\n'+table([{k:r[k] for k in overview} for r in summary])+'\n\n## F7 and prior deviation\n\n'+table([{k:r[k] for k in extra} for r in summary if r['method'] in ('U3','U2')])
    text+='\n\n## Online gate\n\n'+table([dict(condition=k,passed=v) for k,v in verdict['conditions'].items()])+f"\n\n**{verdict['label']}**; failed criteria: {verdict['failed']}.\n\n"
    for image in images:text+=f'![{image}](../research/results/phase23o3/{image})\n\n'
    text+='No23-O/23-O2 evaluation case was rerun. No new inference, rendering or closed-loop experiment was part of this offline check. '
    text+='Online pilot preparation is gated off; no online or smoke run was launched.\n' if verdict['label']=='NO_GO' else 'GO_ONLINE permits the requested pilot preparation and smoke only; the main campaign remains user-run.\n'
    (ROOT/'docs/PHASE23O3_UNIFIED.md').write_text(text);return verdict

def plots(records,order):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from nomad_phase23o2.graph import mixture
    from nomad_phase22.drive_geometry import corners
    from nomad_isaac.clearance import configured_obstacles
    from nomad_phase16.geometry import centered
    result=[];colors=dict(U3='seagreen',U2='purple',C0='darkorange',C1='steelblue')
    for identity in order:
        record=records[identity];c=record['case'];plan=record['methods']['U3']['plan'];B=plan['B_pred'];q,_,_,meta,_=mixture(c,B)
        fig,ax=plt.subplots(figsize=(7,6),constrained_layout=True)
        for i,path in enumerate(q):ax.plot(*path.T,c='.65' if not meta[i]['set_index'] else 'deepskyblue',lw=.7,alpha=.5,label='Current candidates' if i==0 else 'Past candidates' if i==8 else None)
        for box in configured_obstacles(c['oracle_config']):ax.add_patch(Polygon(corners(box),color='.3',alpha=.3))
        cfg,offset=centered(c['oracle_config']);co=cfg['corridor'];wall=np.array([[co['xmin'],-co['half_width']],[co['xmax'],-co['half_width']],[co['xmax'],co['half_width']],[co['xmin'],co['half_width']],[co['xmin'],-co['half_width']]])+[0,offset];ax.plot(*wall.T,c='.35')
        for name,value in record['methods'].items():
            if value['plan'].get('path') is not None:path=np.asarray(value['plan']['path']);ax.plot(*path.T,'--',c=colors[name],lw=1.4)
            path=np.asarray(value['trace']);ax.plot(path[:,0],path[:,1],c=colors[name],label=name+' rollout')
        ax.scatter(*c['B'][:2],marker='x',c='black',label='Snapshot B');d=np.asarray(plan['direction_world'])*.6
        if plan['direction_info']['enabled']:ax.quiver(B[0],B[1],d[0],d[1],angles='xy',scale_units='xy',scale=1,color='crimson',label='Intent direction')
        ax.set_aspect('equal');ax.set_title(c['scene']+' '+identity+' — training only');ax.legend(fontsize=8);ax.set_xlabel('World x(m)');ax.set_ylabel('World y(m)')
        name='example_'+identity+'.png';fig.savefig(OUT/name,dpi=140);plt.close(fig);result.append(name)
    return result
