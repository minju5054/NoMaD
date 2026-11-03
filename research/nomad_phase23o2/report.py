"""Preserve old labels; U2 decisions use only the registered primary cohorts."""
import json
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase23.report import summaries as old_summaries,decision,csv_write
from nomad_phase17.report import table
from nomad_phase16.geometry import centered,shifted
from nomad_phase22.drive_geometry import rotation,bounds,corners
from nomad_isaac.clearance import configured_obstacles,segment_clearance
from .inputs import HERE,OUT,read,write

DEFINITION=r'''
## Input/output and the three changes

Input: current8NoMaD candidates, saved delivered native candidate sets in the last2s (current plus at most7past sets), current pose/speed and installed OLD path, source depth V1 snapshot. Output:11SE(2)poses and10time intervals, then frozen PP graph-speed execution. No A*, u_ref, trigger, progress history, new-obstacle classifier or Topomap input enters U2. Oracle is evaluation-only.

U2 subclasses the frozen cached U graph. All other F2-F6 formulas, solver options,8current-candidate+available left/right starts,4workers,500ms anytime delivery and computation-window motion are unchanged. Historical components do not add extra starts or change side-initialization geometry.

For each component j, transform its observed world XY path into the predicted application-B frame after the same protected B-suffix projection. Current short-candidate supplementation is unchanged; historical components contain only native NoMaD geometry, never applied OLD/A* paths. All candidates are retained. The base sigma_p is the original clipped dispersion of the current8candidates at B; history does not redefine that dispersion.

Let tau_j be dispatch time minus actual post-delay arrival time (received_sim_s; application_sim_s only if absent). Keep at most7strictly earlier arrivals with tau<=2s; retain the current set. No future arrival during the0.5s computation window is used. sigma_j=sigma_p(1+tau_j/T_m), -log(w_j)=tau_j/T_m. F1 component cost is

$$C_j=\sum_{i=1}^{10}c^2\log(1+\|p_i-\hat p_{ji}\|^2/(c^2\sigma_j^2))+\tau_j/T_m.$$

Choose the minimum robust+age cost (ties: current first, then newest historical set, lower sample index). F5 uses the same active component endpoint. Its active-region gradient is $\sum_i2(p_i-\hat p_{ji})/(\sigma_j^2+\|p_i-\hat p_{ji}\|^2/c^2)$. The age constant has zero position gradient.

Frozen initial acceleration $a_0=(v_0-v_{actual})/dt_0$, and subsequent $a_i=2(v_i-v_{i-1})/(dt_i+dt_{i-1})$ now contribute $\sum_i[\max(0,|a_i|-.5)/.05]^2$, including the initial-speed boundary. Only those20upper/lower acceleration inequalities are removed. Speed<=0.3, |omega|<=0.4, dt in[0.05,1] and all depth constraints remain hard. Execution still enforces acceleration0.5: making the plan penalty soft does not relax the robot limit.

Fixed weights: time1.0, goal1.0, curvature0.01. Only c in{1,2,4} × T_m in{0.5,1,2}s is tuned. Selection order is the frozen23-O order: p95<=0.5s eligibility; then collision count, planning failure fraction, summed within-group progress median ranks, p50. If every setting exceeds the deadline, select minimum p95 and flag. SLSQP maxiter100, ftol1e-8; analytic derivatives.

## Dataset and interpretation

Training:242unchanged snapshot inputs, augmented only with earlier saved native sets. Actual held-out static set difference is524: original795minus271shared with the reduced454. The reduced5uniform samples were independently chosen from raw events, not a subset of the original10; subtracting795-454=341 was therefore not the held-out count. All524unused original static snapshots are HELDOUT_STATIC. The34sudden snapshots are reused and labeled SEEN_SUDDEN. SLW ES0078 and LC ES0172 are seen illustration-only cases, excluded from every tuning/decision denominator. L2A ED0473 and two additional sudden examples are fixed by event order before new results.

New U2 solves run on all evaluation cases. Frozen U/C0 are computed on new static cases; U/C0/C1 saved results are reused on seen sudden and illustration-only cases. Their inputs and paths are unchanged. The old23-O UNIFIED_NOT_READY label is preserved. The new label is a U2 offline result, not confirmation on the seen sudden set.

All methods retain the23-O computation-motion rules. U/U2 applies exactly0.5s after snapshot while following OLD; C0/C1 retain original switch B for safe selection and measured R2/R3/A* computation up to1s. Post-delay motion is included in safety/progress. No next FRESH, new inference, depth update or closed-loop reaction is simulated.

Historical-active and prior-departure fractions use accepted U2plans as denominator. Departure means at least one of10future nodes differs from its active prior by>=0.30m; mean and maximum displacement are also recorded. Failure constraints refer to the latest received iterate; deadline-pending starts are censored. Time bounds are listed separately from obstacle and speed/angular constraints. Report both collision-free planned box-passage paths and actual fixed-path rollout passage; neither is a goal-success claim.
'''

def plan_passage(record,value):
    c=record['case'];path=value['plan'].get('path')
    if c['group']!='sudden' or not c.get('spawn') or path is None:return None
    q=np.asarray(path);cfg=c['oracle_config'];radius=cfg['agent_radius_m'];minimum=float('inf')
    for box in configured_obstacles(cfg):
        local=(q-np.asarray(box['center_xy_m']))@rotation(box);half=np.asarray(box['size_xyz_m'][:2])/2
        minimum=min(minimum,min(segment_clearance(a,b,-half,half,radius)[0] for a,b in zip(local[:-1],local[1:])))
    cc,offset=centered(cfg);z=shifted(q,offset);co=cc['corridor']
    wall=min(float(np.min(z[:,0]-co['xmin'])),float(np.min(co['xmax']-z[:,0])),float(np.min(co['half_width']-np.abs(z[:,1]))))-radius
    minimum=min(minimum,wall);_,hi=bounds(c['spawn']['obstacle'])
    return bool(minimum>=0 and np.any(q[:,0]-radius>hi[0]))

def summary(rows):
    out=[]
    for method in ('U2','U','C0','C1'):
        selected=[dict(r,method='U' if method=='U2' else method) for r in rows if r['method']==method]
        for result in old_summaries(selected):
            if result['method']!=('U' if method=='U2' else method):continue
            result['method']=method;rr=[r for r in rows if r['method']==method and r['group']==result['group']];ok=[r for r in rr if r['accepted']]
            def quant(key,q=.5):
                a=[r[key] for r in ok if r.get(key) is not None];return float(np.quantile(a,q)) if a else None
            result.update(stratum='HELDOUT_STATIC' if result['group']=='static' else 'SEEN_SUDDEN',
                active_history_fraction=float(np.mean([r['active_history'] for r in ok])) if method=='U2' and ok else None,
                history_age_median_s=float(np.median([r['active_age_s'] for r in ok if r.get('active_history')])) if any(r.get('active_history') for r in ok) else None,
                history_age_p95_s=float(np.quantile([r['active_age_s'] for r in ok if r.get('active_history')],.95)) if any(r.get('active_history') for r in ok) else None,
                prior_departure_030_fraction=float(np.mean([r['prior_departure_030'] for r in ok])) if method=='U2' and ok else None,
                prior_deviation_max_median_m=quant('prior_deviation_max_m'),prior_deviation_mean_median_m=quant('prior_deviation_mean_m'),
                planned_box_passage_fraction=sum(bool(r.get('planned_box_passage')) for r in rr)/len(rr) if result['group']=='sudden' else None,
                failed_snapshots_dt_active=sum((r.get('failure_dt_active') or 0)>0 for r in rr) if method in ('U2','U') else None)
            out.append(result)
    return out

def selection_report(p):
    text='# Phase23-O2 — frozen tuning selection; evaluation pending\n\n'+DEFINITION+'\n## Selection evidence\n\n'+table(p['selection_evidence']['table'])+'\n\nSelected: '+str(p['selected'])+'\n\nEvaluation label: NOT_EVALUATED.\n'
    (ROOT/'docs/PHASE23O2_UNIFIED.md').write_text(text)

def generate():
    p=read(HERE/'protocol.json');m=read(OUT/'manifest.json');records=[read(OUT/'evaluation'/(c['case_id']+'.json')) for c in m['evaluation']];rows=[]
    for record in records:
        for value in record['methods'].values():
            row=dict(value['row'],planned_box_passage=plan_passage(record,value))
            if row['method']=='U' and not row['accepted']:
                latest={}
                for item in value['plan'].get('anytime_messages',[]):latest[item['index']]={**latest.get(item['index'],{}),**item}
                row['failure_dt_active']=sum(item.get('active_dt_bound',0) for item in latest.values())
            rows.append(row)
    ss=summary(rows);judgement=[dict(r,method='U' if r['method']=='U2' else r['method']) for r in ss if r['method'] in ('U2','C0')];verdict=decision(judgement)
    verdict.update(version='U2',static_label='HELDOUT_STATIC',sudden_label='SEEN_SUDDEN',old_U_label='UNIFIED_NOT_READY')
    csv_write(OUT/'snapshots.csv',rows);csv_write(OUT/'summary.csv',ss);write(OUT/'decision.json',verdict)
    pairs=[]
    for r in records:
        a,b=r['methods']['U2']['row'],r['methods']['U']['row'];pairs.append(dict(case_id=r['case']['case_id'],stratum=r['case']['stratum'],U2_collision=a['oracle_collision'],U_collision=b['oracle_collision'],progress_delta=a['progress']-b['progress'],compute_delta_s=a['compute_s']-b['compute_s']))
    csv_write(OUT/'paired.csv',pairs)
    examples=records+[read(OUT/'examples_only'/(c['case_id']+'.json')) for c in m['examples_only']];figures=plots(examples,m['figures'])
    text='# Phase23-O2 — offline U2 validation\n\n'+DEFINITION+f"\nProtocol SHA256 `{sha256_file(HERE/'protocol.json')}`; selected `{p['selected']}`.\n\n"
    overview=('group','method','stratum','n','oracle_collisions','planning_failure_fraction','progress_median','compute_p50_s','compute_p95_s','planned_box_passage_fraction','passage_fraction')
    memory=('group','active_history_fraction','history_age_median_s','history_age_p95_s','prior_departure_030_fraction','prior_deviation_max_median_m','prior_deviation_mean_median_m')
    failure=('group','method','failed_snapshots_obstacle_active','failed_snapshots_kinematic_active','failed_snapshots_dt_active','pending_initializations')
    text+='## Tuning evidence\n\n'+table(p['selection_evidence']['table'])+'\n\n## Group comparisons\n\n'+table([{k:r[k] for k in overview} for r in ss])
    text+='\n\n## U2 memory and prior deviation\n\n'+table([{k:r[k] for k in memory} for r in ss if r['method']=='U2'])+'\n\n## Failed-plan active constraints\n\n'+table([{k:r[k] for k in failure} for r in ss if r['method'] in ('U','U2')])
    text+='\n\n## Registered U2 vs C0 decision\n\n'+table([dict(group=g,**v) for g,v in verdict['groups'].items()])+f"\n\n**{verdict['label']}**. Old U: UNIFIED_NOT_READY (unchanged).\n\n"
    for file in figures:text+=f'![{file}](../research/results/phase23o2/{file})\n\n'
    if verdict['label'] in ('UNIFIED_READY','UNIFIED_PARTIAL'):
        text+='## Draft only — not executed\n\nL2+SLW ×4new seeds×U2/C0/C1=24runs. C1 on SLW is a reference only. Freeze common sensing, computation-time motion and executors; report goal/collision and paired passage/checkpoint time per scene. Pre-register no increased collisions, goal success at least C0, planning failure within5%p, and p95<=0.5s for U2; do not claim unseen-sudden generalization from this offline dataset. This is an unexecuted pilot proposal.\n'
    (ROOT/'docs/PHASE23O2_UNIFIED.md').write_text(text);return verdict

def plots(records,identities):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from .graph import mixture
    indexed={r['case']['case_id']:r for r in records};files=[];colors=dict(U='purple',U2='seagreen',C0='darkorange',C1='steelblue')
    for identity in identities:
        r=indexed[identity];c=r['case'];B=r['methods']['U2']['plan']['B_pred'];candidates,_,_,meta,_=mixture(c,B)
        fig,ax=plt.subplots(figsize=(7,6),constrained_layout=True)
        for i,path in enumerate(candidates):ax.plot(*path.T,color='.65' if meta[i]['set_index']==0 else 'deepskyblue',alpha=.5,lw=.8,label=('Current candidates' if i==0 else 'Past candidates' if i==8 else None))
        for box in configured_obstacles(c['oracle_config']):ax.add_patch(Polygon(corners(box),color='.3',alpha=.3))
        cfg,offset=centered(c['oracle_config']);co=cfg['corridor'];wall=np.array([[co['xmin'],-co['half_width']],[co['xmax'],-co['half_width']],[co['xmax'],co['half_width']],[co['xmin'],co['half_width']],[co['xmin'],-co['half_width']]])+np.array([0.,offset])
        ax.plot(*wall.T,c='.35',lw=1.)
        for name,v in r['methods'].items():
            if v['plan'].get('path') is not None:q=np.asarray(v['plan']['path']);ax.plot(*q.T,'--',color=colors[name],lw=1.6)
            q=np.asarray(v['trace']);ax.plot(q[:,0],q[:,1],color=colors[name],lw=1.5,label=name+' rollout')
        ax.scatter(*c['B'][:2],c='black',marker='x',label='Snapshot B');ax.scatter(*B[:2],c=colors['U2'],marker='+',label='Application B')
        ax.set_aspect('equal');ax.set_title(c['scene']+' '+c.get('origin_phase23_case_id',identity)+' — '+c['stratum']);ax.legend(fontsize=8);ax.set_xlabel('World x(m)');ax.set_ylabel('World y(m)')
        file='example_'+identity+'.png';fig.savefig(OUT/file,dpi=140);plt.close(fig);files.append(file)
    return files
