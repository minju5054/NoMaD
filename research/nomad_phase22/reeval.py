"""22-O2: saved plans only; fix rollout stopping, preserve frozen decisions/weights."""
import argparse,hashlib,json,math,subprocess,time
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,integrate_se2
from nomad_isaac.clearance import configured_obstacles,obstacle_bounds,single_obstacle_config,point_clearance,segment_clearance
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase16.geometry import centered,shifted
from nomad_phase20.execution import SPAlignment
from nomad_phase20d.recent import RecentSnapshot,build_cache
from nomad_phase19r.evaluate import clean,csv_write
from nomad_phase17.report import table
from .rollout import evaluate
from .metrics import decision,side_choice
from .refine import RefineGraph
COLORS={'P0':'tab:blue','P1':'tab:orange','P2':'purple','P3':'tab:green'}

SOURCE=ROOT/'research/results/phase22o';OUT=ROOT/'research/results/phase22o2';HERE=Path(__file__).parent
DT=1/72


def stop_reason(pose,endpoint,progress,length,elapsed,alignment_s):
    if np.linalg.norm(np.asarray(pose)[:2]-endpoint)<=.10:return 'ENDPOINT_0P10'
    if progress>=length:return 'PROJECTED_END'
    if elapsed>length/.05+alignment_s:return 'TIMEOUT'
    return None


def simulate(B,path,previous_v):
    ctl=SPAlignment();ctl.replace_path(path,B,previous_v);poly=XYPath(path);length=float(poly.s[-1]);pose=np.asarray(B,dtype=float).copy()
    poses=[pose.copy()];commands=[];vel=[];omega=[];errors=[];previous=float(previous_v);progress=poly.project(pose[:2])[0];alignment_ticks=0;tick=0
    guard=length/.05+np.pi/.4+.3/.5+2.  # Numerical guard only; not a completion rule.
    while True:
        progress=max(progress,poly.project(pose[:2])[0]);reason=stop_reason(pose,poly.points[-1],progress,length,tick/72,alignment_ticks/72)
        if reason is not None:break
        if tick/72>guard:raise RuntimeError('Alignment/controller exceeded its analytic time bound')
        if tick%8==0:
            (v,w),diag=ctl.control(pose,previous)
            if diag['completed']:raise AssertionError('The new0.10m check must precede the old0.01m endpoint stop')
            previous=v;commands.append(dict(tick=tick,v=v,w=w,mode=diag['mode']))
        pose=integrate_se2(pose,v,w,DT);poses.append(pose.copy());vel.append(v);omega.append(w);errors.append(poly.project(pose[:2])[1])
        alignment_ticks+=ctl.mode in ('BRAKE','ROTATE');tick+=1
    ww=np.array([r['w'] for r in commands]);jerk=np.diff(ww,n=2)*81
    return dict(poses=np.array(poses),commands=commands,speeds=vel,omegas=omega,completed=True,completion_time_s=len(vel)/72,duration_s=len(vel)/72,
        jerk_rms=float(np.sqrt(np.mean(jerk**2))) if len(jerk) else 0.,omega_saturation_fraction=float(np.mean(np.abs(omega)>=.399)) if omega else 0.,
        tracking_rms=float(np.sqrt(np.mean(np.square(errors)))) if errors else 0.,tracking_max=max(errors,default=0.),distance_m=float(np.sum(np.abs(vel))/72),
        termination=reason,TIMEOUT=reason=='TIMEOUT',alignment=ctl.trigger_S,alignment_time_s=alignment_ticks/72,path_length_m=length,terminal_projection_m=progress,
        endpoint_distance_m=float(np.linalg.norm(pose[:2]-poly.points[-1])),time_limit_s=length/.05+alignment_ticks/72)


def plan_oracle(path,config):
    """Exact existing point/segment-AABB geometry, plus rectangular wall distances."""
    points=np.asarray(path);radius=config['agent_radius_m'];boxes=[obstacle_bounds(single_obstacle_config(config,b)) for b in configured_obstacles(config)]
    point_gap=min([point_clearance(p,lo,hi,radius) for p in points for lo,hi in boxes],default=float('inf'))
    segment_gap=min([segment_clearance(a,b,lo,hi,radius)[0] for a,b in zip(points[:-1],points[1:]) for lo,hi in boxes],default=float('inf'))
    cc,offset=centered(config);q=shifted(points,offset);c=cc['corridor']
    wall=float(min(np.min(q[:,0]-c['xmin']),np.min(c['xmax']-q[:,0]),np.min(c['half_width']-np.abs(q[:,1])))-radius)
    point_gap=min(point_gap,wall);segment_gap=min(segment_gap,wall)
    return dict(plan_oracle_point_clearance_m=point_gap,plan_oracle_segment_clearance_m=segment_gap,plan_oracle_point_collision=point_gap<0,plan_oracle_segment_collision=segment_gap<0)


def heading_error(path,u):
    d=np.asarray(path)[-1]-np.asarray(path)[-2];return abs(float((np.arctan2(d[1],d[0])-np.arctan2(u[1],u[0])+np.pi)%(2*np.pi)-np.pi))


def heading_diagnostic(record,settings):
    c=record['case'];p0=record['plans']['P0'];p2=record['plans']['P2']
    if not(p0['accepted'] and p2['accepted']):return dict(case_id=c['case_id'],available=False)
    base=RecentSnapshot.load(c['snapshot_file']);strict,_=build_cache(base,c['tick'])
    g=RefineGraph(c['B'],c['u_ref'],base,strict,p0['path'],c['anchor_xy'],settings,time.monotonic_ns()+10_000_000_000)
    final=np.asarray(p2['path']);initial=np.asarray(p2['initial_path']);x=final[1:].ravel();r,j=g.residual_jacobian(x);ri,_=g.residual_jacobian(initial[1:].ravel())
    constraints,cj=g.constraints(x)
    groups={'progress':slice(0,1),'smoothness':slice(1,19),'clearance':slice(19,109),'start_heading':slice(109,110),'executability':slice(110,119),'curvature_change':slice(119,127),'terminal_heading':slice(127,128),'terminal_lateral':slice(128,129)}
    costs={k:.5*float(r[s]@r[s]) for k,s in groups.items()};old_costs={k:.5*float(ri[s]@ri[s]) for k,s in groups.items()};grad={k:j[s].T@r[s] for k,s in groups.items()}
    norms={k:float(np.linalg.norm(v)) for k,v in grad.items()};hg=grad['terminal_heading'];norm=float(np.linalg.norm(hg));direction=-hg/norm if norm>1e-12 else np.zeros(20)
    derivatives={k:float(v@direction) for k,v in grad.items()};active=constraints<=1e-5;blocked=np.flatnonzero(active&(cj@direction < -1e-8))
    categories=[]
    for i in blocked:
        categories.append('SDF' if i<90 else 'curvature' if i<108 else 'segment_lower' if i<118 else 'segment_upper' if i<128 else 'disk' if i<138 else 'P0_tube')
    lb=g.bounds.lb;ub=g.bounds.ub
    if np.any((x-lb<=1e-5)&(direction<0)) or np.any((ub-x<=1e-5)&(direction>0)):categories.append('coordinate_bound')
    p0e=heading_error(p0['path'],c['u_ref']);ie=heading_error(initial,c['u_ref']);fe=heading_error(final,c['u_ref'])
    return dict(case_id=c['case_id'],available=True,scene=c['scene'],index=c['index'],sigma_heading=settings['sigma_heading'],P0_heading_rad=p0e,initial_heading_rad=ie,P2_heading_rad=fe,
        delta_resampling_rad=ie-p0e,delta_optimization_rad=fe-ie,delta_P2_P0_rad=fe-p0e,worsened_vs_P0=fe>p0e,
        costs=costs,initial_costs=old_costs,cost_deltas={k:costs[k]-old_costs[k] for k in costs},heading_cost_fraction=costs['terminal_heading']/sum(costs.values()) if sum(costs.values()) else 0.,
        gradient_norms=norms,heading_gradient_share=norm/sum(norms.values()) if sum(norms.values()) else 0.,heading_descent_directional_costs=derivatives,
        other_cost_directional_derivative=sum(v for k,v in derivatives.items() if k!='terminal_heading'),total_directional_derivative=sum(derivatives.values()),
        active_constraint_blockers=sorted(set(categories)),active_constraint_count=int(active.sum()),minimum_constraint_slack=float(constraints.min()))


def verify_registration():
    p=json.loads((HERE/'reeval_protocol.json').read_text());assert p['status']=='FROZEN'
    for f,h in p['frozen_files'].items():assert sha256_file(ROOT/f)==h,f
    for f,h in p['input_hashes'].items():assert sha256_file(ROOT/f)==h,f
    for f in p['frozen_files']:
        if f.startswith('research/nomad_phase22/') and not f.endswith('reeval_protocol.json'):
            assert (ROOT/f).read_bytes()==subprocess.check_output(['git','show','6250433:'+f],cwd=ROOT),f
    assert not subprocess.check_output(['git','diff','--name-only','--',str(HERE.relative_to(ROOT))],cwd=ROOT,text=True).strip(),'Commit reevaluation code before looking at results'
    return p


def run():
    registration=verify_registration();OUT.mkdir(exist_ok=False);records=[];rows=[];pair_rows=[];diagnostics=[]
    frozen=json.loads((HERE/'protocol.json').read_text());inputs=sorted((SOURCE/'evaluation').glob('E*.json'));assert len(inputs)==24
    for file in inputs:
        old=json.loads(file.read_text());case=old['case'];new=dict(case=case,plans=old['plans'],rows=[],traces={})
        old_rows={r['method']:r for r in old['rows']}
        for method,plan in old['plans'].items():
            row=dict(old_rows[method])
            if plan.get('path') is not None:row.update(plan_oracle(plan['path'],case['oracle_config']))
            if plan['accepted']:
                result=evaluate(simulate(case['B'],plan['path'],case['previous_vw'][0]),case['oracle_config'])
                for k in ('completed','completion_time_s','duration_s','jerk_rms','omega_saturation_fraction','tracking_rms','tracking_max','distance_m','termination','oracle_minimum_clearance_m','oracle_collision','oracle_conservative_negative','safe_completion','TIMEOUT','alignment_time_s','path_length_m','terminal_projection_m','endpoint_distance_m','time_limit_s'):row[k]=result[k]
                row['executed_side']=side_choice(result['poses'][:,:2],case,True)['side'];end=result['poses'][-1];u=np.asarray(case['u_ref']);normal=np.array([-u[1],u[0]])
                row['actual_end_heading_error_rad']=abs(float((end[2]-np.arctan2(u[1],u[0])+np.pi)%(2*np.pi)-np.pi));row['actual_end_lateral_error_m']=abs(float((end[:2]-np.asarray(case['anchor_xy']))@normal))
                new['traces'][method]=dict(poses=result['poses'].tolist(),commands=result['commands'])
                row.update(old_oracle_collision=old_rows[method]['oracle_collision'],old_oracle_minimum_clearance_m=old_rows[method]['oracle_minimum_clearance_m'],old_completion_time_s=old_rows[method]['completion_time_s'],old_duration_s=old_rows[method]['duration_s'],old_termination=old_rows[method]['termination'])
                # Verify the changed evaluator only truncates the frozen controller trace.
                prior=old['traces'][method]['poses'];n=min(len(prior),len(result['poses']));error=float(np.max(np.abs(np.asarray(prior[:n])-result['poses'][:n])))
                assert error==0.,(case['case_id'],method,error);row['prefix_pose_error']=error
            new['rows'].append(row);rows.append(row)
        diagnostics.append(heading_diagnostic(old,frozen['selected']['p2_settings']));records.append(new)
        b={r['method']:r for r in new['rows']};a,c=b['P0'],b['P2'];pair=dict(case_id=case['case_id'],scene=case['scene'],P0_accepted=a['accepted'],P2_accepted=c['accepted'])
        for key in ('jerk_rms','completion_time_s','heading_error_rad'):
            pair['P0_'+key]=a.get(key);pair['P2_'+key]=c.get(key);pair['delta_'+key]=c[key]-a[key] if a.get(key) is not None and c.get(key) is not None else None
        pair['both_safe_completed']=bool(a.get('safe_completion') and c.get('safe_completion'));pair_rows.append(pair)
        print(f"[reevaluate] {case['case_id']}",flush=True)
    verdict=decision(rows);verdict['LOW_N']=bool(verdict['LOW_N'] or verdict['common_completion_n']<10);verdict['LOW_N_reason']='common safe-completion subset<10' if verdict['common_completion_n']<10 else None
    old_verdict=json.loads((SOURCE/'decision.json').read_text());verdict.update(original_label=old_verdict['label'],original_assessment_status='EVALUATION_DEFECT',frozen_commit='6250433')
    write(OUT/'decision.json',verdict);write(OUT/'heading_diagnostics.json',diagnostics);write(OUT/'records.json',records)
    for name,data in [('snapshots',rows),('paired_P2_P0',pair_rows),('heading_diagnostics',diagnostics)]:csv_write(OUT/f'{name}.csv',data)
    generate_report(records,rows,pair_rows,diagnostics,verdict,old_verdict)
    write(OUT/'provenance.json',dict(registration=registration,execution_git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),original_data_reused=True,new_graph_solves=0,new_navigation=0))
    print(json.dumps(verdict,ensure_ascii=False))


def write(path,value):Path(path).write_text(json.dumps(clean(value),indent=2,ensure_ascii=False)+'\n')


def summaries(rows):
    result=[]
    for scene in ('L2','L2A','ALL'):
        for method in COLORS:
            rr=[r for r in rows if r['method']==method and (scene=='ALL' or r['scene']==scene)];valid=[r for r in rr if r['accepted']]
            def median(key):
                a=[r[key] for r in valid if r.get(key) is not None];return float(np.median(a)) if a else None
            result.append(dict(scene=scene,method=method,n=len(rr),plan_success=sum(r['accepted'] for r in rr),plan_success_rate=sum(r['accepted'] for r in rr)/len(rr) if rr else None,
                plan_point_collisions=sum(r.get('plan_oracle_point_collision',False) for r in rr),plan_segment_collisions=sum(r.get('plan_oracle_segment_collision',False) for r in rr),
                old_rollout_collisions=sum(r.get('old_oracle_collision',False) for r in rr),new_rollout_collisions=sum(r.get('oracle_collision',False) for r in rr),safe_completed=sum(r.get('safe_completion',False) for r in rr),
                endpoint_0p10=sum(r.get('termination')=='ENDPOINT_0P10' for r in rr),projected_end=sum(r.get('termination')=='PROJECTED_END' for r in rr),TIMEOUT=sum(r.get('TIMEOUT',False) for r in rr),
                minimum_clearance_m=min([r['oracle_minimum_clearance_m'] for r in valid],default=None),time_median_s=median('completion_time_s'),jerk_median=median('jerk_rms'),heading_median_rad=median('heading_error_rad'),lateral_median_m=median('lateral_error_m')))
    return result


def plots(records,rows,pairs,common):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    by={r['case']['case_id']:r for r in records};examples=json.loads((HERE/'reeval_protocol.json').read_text())['figures']['cases']
    fig,axes=plt.subplots(len(examples),2,figsize=(15,11),constrained_layout=True)
    for i,identity in enumerate(examples):
        new=by[identity];old=json.loads((SOURCE/'evaluation'/f'{identity}.json').read_text());case=new['case'];cfg=case['oracle_config'];half=cfg['corridor']['half_width']
        for ax,record,title in zip(axes[i],(old,new),('Original defective evaluator','Corrected handover termination')):
            extent=[np.array(case['B'])[None,:2]];ax.axhline(half,c='.4');ax.axhline(-half,c='.4');ax.axvline(cfg['corridor']['xmin'],c='.4');ax.axvline(cfg['corridor']['xmax'],c='.4')
            for box in cfg['obstacles']:
                center=np.array(box['center_xy_m']);size=np.array(box['size_xyz_m'][:2]);ax.add_patch(Rectangle(center-size/2,*size,color='.5',alpha=.3))
            rr={r['method']:r for r in record['rows']}
            for method,color in COLORS.items():
                plan=record['plans'][method]
                if plan.get('path') is not None:
                    p=np.array(plan['path']);extent.append(p);ax.plot(p[:,0],p[:,1],':',c=color,alpha=.6)
                trace=record['traces'].get(method)
                if trace:
                    p=np.array(trace['poses']);extent.append(p[:,:2]);ax.plot(p[:,0],p[:,1],c=color,lw=1.4,label=f"{method}: {rr[method].get('duration_s',0):.2f}s / {rr[method].get('termination')}");ax.scatter(*p[-1,:2],marker='s',c=color,s=20)
                else:ax.plot([],[],c=color,label=method+' planning failed')
            points=np.concatenate(extent);ax.set_xlim(min(cfg['corridor']['xmin']-.2,points[:,0].min()-.2),max(cfg['corridor']['xmax']+.2,points[:,0].max()+.2));ax.set_ylim(min(-half-.2,points[:,1].min()-.2),max(half+.2,points[:,1].max()+.2))
            ax.scatter(*case['B'][:2],marker='^',c='black',s=30);ax.set_aspect('equal');ax.legend(fontsize=6);ax.set_title(f'{identity} / {title}',fontsize=9)
    fig.suptitle('Same saved plans and command prefixes; axis limits include every executed pose')
    fig.savefig(OUT/'before_after.png',dpi=140);plt.close(fig)
    keys=('completion_time_s','jerk_rms','heading_error_rad','lateral_error_m','oracle_minimum_clearance_m','plan_oracle_segment_clearance_m')
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    for ax,key in zip(axes.ravel(),keys):
        data=[];positions=[]
        for i,method in enumerate(COLORS):
            a=[r[key] for r in rows if r['method']==method and r.get(key) is not None]
            if a:data.append(a);positions.append(i);ax.scatter(i+np.linspace(-.1,.1,len(a)),a,s=12,c=COLORS[method],alpha=.65)
        if data:ax.boxplot(data,positions=positions,widths=.4,showfliers=False)
        ax.set_xticks(range(4),list(COLORS));ax.set_title(key);ax.grid(alpha=.15)
    fig.suptitle('All available values; registered comparison uses the common safe-completion subset')
    fig.savefig(OUT/'metric_distributions.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,5),constrained_layout=True)
    for ax,key in zip(axes,('jerk_rms','completion_time_s','heading_error_rad')):
        for p in pairs:
            a,b=p['P0_'+key],p['P2_'+key]
            if a is not None and b is not None:
                in_common=p['case_id'] in common;ax.plot([0,1],[a,b],'.-',alpha=.8 if in_common else .25,lw=1.3 if in_common else .6,c='purple' if in_common else '.5')
        ax.set_xticks([0,1],['P0','P2']);ax.set_title(key)
    fig.suptitle('Each line is one snapshot; purple = registered common P0/P2/P3 safe-completion subset')
    fig.savefig(OUT/'paired_P2_P0.png',dpi=140);plt.close(fig)


def generate_report(records,rows,pairs,diagnostics,verdict,original):
    stats=summaries(rows);(OUT/'summary.csv').unlink(missing_ok=True);csv_write(OUT/'summary.csv',stats);plots(records,rows,pairs,verdict['common_ids'])
    available=[r for r in diagnostics if r['available']];worse=[r for r in available if r['worsened_vs_P0']]
    def med(rr,key):return float(np.median([r[key] for r in rr])) if rr else None
    diagnosis=dict(accepted_pairs=len(available),heading_worsened_pairs=len(worse),heading_gradient_share_median=med(worse,'heading_gradient_share'),heading_cost_fraction_median=med(worse,'heading_cost_fraction'),
        heading_descent_blocked_pairs=sum(bool(r['active_constraint_blockers']) for r in worse),other_cost_opposes_heading_descent_pairs=sum(r['other_cost_directional_derivative']>0 for r in worse),
        resampling_worsened_pairs=sum(r['delta_resampling_rad']>1e-8 for r in worse),optimization_worsened_pairs=sum(r['delta_optimization_rad']>1e-8 for r in worse),
        conclusion='Stored-solution factor/constraint trade-off only. The causal claim that sigma0.52 alone is too weak cannot be established without a forbidden changed-weight counterfactual solve.')
    from collections import Counter
    diagnosis['dominant_opposing_factors']=dict(Counter(max(((k,v) for k,v in r['heading_descent_directional_costs'].items() if k!='terminal_heading'),key=lambda item:item[1])[0] for r in worse))
    write(OUT/'heading_summary.json',diagnosis)
    text='# Phase22-O2 — evaluator correction and reevaluation\n\n'
    text+=f"Original label: **{original['label']} — EVALUATION_DEFECT**. Original report, numeric results and trajectories are retained. Corrected label: **{verdict['label']}**"+(' **LOW_N**' if verdict['LOW_N'] else '')+'.\n\n'
    text+='Frozen method/weight/criterion commit: `6250433`. All24 saved evaluation snapshots and all planned paths/dispositions/timings were reused unchanged. No Graph solve, retuning, Isaac, rendering or inference was performed.\n\n'
    text+='## Registered evaluator correction\n\nAt every72Hz pose, stop at the first of: endpoint distance≤0.10m; monotone nearest-polyline projected progress≥path length; elapsed time>path length/0.05+actual accumulated initial alignment time (braking+rotation). All three set completed=True; the last also sets TIMEOUT=True. Priority for simultaneous conditions is endpoint, projection, timeout. Only intervals before this cutoff are evaluated for collision/clearance. This is a handover proxy, not a simulated next NoMaD prediction.\n\n'
    text+='Commands/integration are unchanged: every corrected trajectory is an exact prefix of its saved original trajectory (maximum prefix pose error0). TIMEOUT and PROJECTED_END completions are kept in the existing common-completion calculation as explicitly requested; their counts and endpoint distances remain visible.\n\n'
    text+='## Plan success and geometric safety (P1 included)\n\n'+table(stats)+'\n\nPoint clearance tests vertices; segment clearance uses the existing exact segment/AABB distance and wall geometry, including the0.09m footprint. Plan collision columns are descriptive and were not added to frozen criterion(i).\n\n'
    text+='## Unchanged criteria(i–v) and new LOW_N rule\n\n'+table([dict(original_label=original['label'],original_status='EVALUATION_DEFECT',new_label=verdict['label'],LOW_N=verdict['LOW_N'],snapshot_n=verdict['snapshot_n'],common_completed_n=verdict['common_completion_n'],side_n=verdict['side_n'],same_side=verdict['same_side'],**verdict['criteria'])])+'\n\n'
    text+='Criterion computation is the byte-identical6250433 decision function. The sole label annotation change is LOW_N when the corrected common safe-completion subset has fewer than10 snapshots (the prior snapshot-N<15 check is also retained). Plans and planned endpoint heading/lateral errors do not change. A changed common subset can change their comparison medians.\n\n'
    text+=table([dict(method=m,**v) for m,v in verdict['medians'].items()])+'\n\n'
    text+='## Snapshot-wise P2−P0 reference pairs\n\n'+table(pairs)+'\n\n'
    text+='## Why terminal heading worsens: diagnostic only\n\n'+table([diagnosis])+'\n\n'
    text+='Planned heading errors are unchanged snapshot by snapshot. The old common subset had'+str(original['common_completion_n'])+' snapshots; the corrected subset has'+str(verdict['common_completion_n'])+'. Thus the changed heading median is solely a conditioning/subset effect, not a changed path or weight. The earlier group-level degradation does not by itself establish that sigma0.52 is too weak.\n\n'
    text+=table([dict(evaluation='original defective',method=m,heading_median_rad=v['heading_error_rad']) for m,v in original['medians'].items()]+[dict(evaluation='corrected',method=m,heading_median_rad=v['heading_error_rad']) for m,v in verdict['medians'].items()])+'\n\n'
    if worse:
        text+=f"Individual heading worsens in{len(worse)}/{len(available)} accepted P0/P2 pairs. In those cases, terminal-heading cost share median={100*diagnosis['heading_cost_fraction_median']:.2f}%, gradient share median={100*diagnosis['heading_gradient_share_median']:.2f}%. Other terms oppose heading descent in{diagnosis['other_cost_opposes_heading_descent_pairs']}/{len(worse)}; direct active-constraint blockers occur in{diagnosis['heading_descent_blocked_pairs']}/{len(worse)}. Dominant opposing terms: {diagnosis['dominant_opposing_factors']}. This supports a soft-objective trade-off at the existing weights, not a causal demonstration that changing sigma would improve the complete criterion set.\n\n"
    text+='The terminal heading factor is soft: r=2sin(error/2)/0.52, cost=r²/2. At30° its cost is about0.495; it is neither a hard heading tolerance nor a guarantee of improvement over P0. The table separates initialization resampling from optimization and compares heading cost/gradient contribution with other factors. At the saved solution, negative heading-gradient directions are checked against active frozen constraints (slack≤1e−5). No sigma was changed and no alternative optimum was computed.\n\n'
    text+=table(available,['case_id','P0_heading_rad','initial_heading_rad','P2_heading_rad','delta_resampling_rad','delta_optimization_rad','heading_cost_fraction','heading_gradient_share','other_cost_directional_derivative','total_directional_derivative','active_constraint_blockers'])+'\n\n'
    text+='Full factor costs, cost changes, gradients and blockers are in heading_diagnostics.csv/json. These can support a relative soft-objective trade-off or a constraint conflict, but cannot isolate sigma0.52 as a sufficient causal explanation.\n\n'
    text+='## Corrected snapshot records\n\n'+table(rows,['case_id','method','accepted','termination','TIMEOUT','completed','duration_s','endpoint_distance_m','old_oracle_collision','oracle_collision','old_oracle_minimum_clearance_m','oracle_minimum_clearance_m','plan_oracle_point_collision','plan_oracle_segment_collision'])+'\n\n'
    for name in ('before_after.png','metric_distributions.png','paired_P2_P0.png'):text+=f'![{name}](../research/results/phase22o2/{name})\n\n'
    text+='This remains post-hoc offline mechanism validation on the same snapshots. The defect correction removes post-path collision counting; it does not validate closed-loop navigation, future depth updates, NoMaD reaction or3D contact physics.\n\n'
    text+=verdict['label']+(' / LOW_N' if verdict['LOW_N'] else '')+'\n'
    (ROOT/'docs/PHASE22O2_REEVAL.md').write_text(text)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');ap.add_argument('--report-only',action='store_true');a=ap.parse_args()
    if a.report_only:
        import csv
        records=json.loads((OUT/'records.json').read_text());rows=[r for record in records for r in record['rows']];pairs=[]
        for raw in csv.DictReader((OUT/'paired_P2_P0.csv').read_text().splitlines()):
            row={}
            for k,v in raw.items():
                if v=='':row[k]=None
                elif v in ('True','False'):row[k]=v=='True'
                else:
                    try:row[k]=float(v)
                    except ValueError:row[k]=v
            pairs.append(row)
        diagnostics=json.loads((OUT/'heading_diagnostics.json').read_text());verdict=json.loads((OUT/'decision.json').read_text());original=json.loads((SOURCE/'decision.json').read_text())
        generate_report(records,rows,pairs,diagnostics,verdict,original)
        if not (OUT/'provenance.json').exists():
            execution_sha=subprocess.check_output(['git','log','-1','--format=%H','--',str(HERE.relative_to(ROOT)/'reeval_protocol.json')],cwd=ROOT,text=True).strip()
            write(OUT/'provenance.json',dict(registration=json.loads((HERE/'reeval_protocol.json').read_text()),execution_git_sha=execution_sha,original_data_reused=True,new_graph_solves=0,new_navigation=0,report_only_regenerated=True))
        print(json.dumps(verdict,ensure_ascii=False))
    else:run()
    if a.publish:
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
        subprocess.run(['git','add','--',str(OUT.relative_to(ROOT)),'docs/PHASE22O2_REEVAL.md'],cwd=ROOT,check=True)
        subprocess.run(['git','add','-f','--',*[str(p.relative_to(ROOT)) for p in OUT.glob('*.png')]],cwd=ROOT,check=True)
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase22O2 corrected termination reevaluation'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
        subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
if __name__=='__main__':main()
