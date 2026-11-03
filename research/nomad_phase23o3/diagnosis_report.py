"""Diagnostic-only conclusions; retain the registered GO_ONLINE artifact."""
import json
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase17.report import table
from nomad_phase23o2.inputs import read,write
from .diagnose import OUT,SOURCE,input_stage

WARNING='이미 상자를 지난 snapshot 8건으로 충족, 통과 전 입력에서 U3 0/16(C0 2/16, C1 3/16)이라 회피 경로 생성 개선으로 해석 불가'

def generate(protocol,records,costs,pairs,availability,sets,summary,rejudge):
    images=plots(protocol,records)
    original=ROOT/'docs/PHASE23O3_UNIFIED.md';archive=OUT/'original_registered_report.md'
    if not archive.exists():archive.write_text(original.read_text())
    rows=[];m=read(SOURCE/'manifest.json');p=read(ROOT/'research/nomad_phase23o3/protocol.json')
    for group in ('PRE_SPAWN','PRE_PASSAGE','ALREADY_PASSED'):
        cc=[c for c in m['training'] if c['group']=='sudden' and input_stage(c)==group];counts={name:0 for name in ('U2','U3','C0','C1')}
        for c in cc:
            methods=read(SOURCE/'comparators'/(c['case_id']+'.json'))['methods'];methods['U3']=read(SOURCE/'training'/(c['case_id']+'.json'))['methods'][f"U3_{p['selected_index']:02d}"]
            for name,value in methods.items():counts[name]+=bool(value['row']['planned_box_passage'])
        rows.append(dict(input_stage=group,n=len(cc),**counts))
    write(OUT/'input_stage_counts.json',rows)
    marker='\n## Pre-passage correction and online hold\n'
    historical=original.read_text().split(marker)[0];title,body=historical.split('\n',1)
    text=title+'\n\n> **Correction: PRE_PASSAGE_NO_GO.** '+WARNING+'. Original GO_ONLINE is preserved below; online preparation is held.\n'+body+marker+'\n**'+WARNING+'**.\n\nOriginal registered label **GO_ONLINE** and gate.json are unchanged. Separate rejudgement: **PRE_PASSAGE_NO_GO**. Online preparation is on hold; no U3smoke or main campaign was executed. C0/C1smokes completed before this hold remain excluded artifacts.\n\n'+table(rows)+'\n\nSee [the frozen-weight diagnosis](PHASE23O3_DIAGNOSIS.md).\n'
    original.write_text(text)
    cost_view=[{k:r[k] for k in ('case_id','reference_method','trajectory','F1','F2','F3','F4','F5','F6','F7','total','strict_feasible')} for r in costs]
    soft_view=[{k:r[k] for k in ('case_id','reference_method','trajectory','F1_age','F3_nonholonomic','F3_backward','F3_acceleration','max_abs_acceleration','F2_minimum_slack_m','v_max','omega_max','dt_min','dt_max')} for r in costs]
    comparison=[{k:r[k] for k in ('case_id','method','reference_cost','U3_cost','cost_delta_vs_U3','cost_label','largest_term_delta','largest_term_delta_value','reference_strict_feasible','reference_heading_lag_max_deg','reference_planned_passage')} for r in pairs]
    init_view=[{k:r[k] for k in ('case_id','method','extra_solver_success','extra_iterations','extra_accepted','extra_strict_feasible','extra_passage','extra_cost','selected_initializer','selected_passage','selected_cost','wall_s')} for r in pairs]
    direction=[dict(case_id=i,angle_to_oracle_positive_x_deg=r['direction_angle_deg'],wrong_45_deg=r['direction_angle_deg'] is not None and r['direction_angle_deg']>=45) for i,r in records.items()]
    conclusions=[]
    cheap=[r for r in pairs if r['cost_label']=='INIT_LIMITED'];expensive=[r for r in pairs if r['cost_label']=='OBJECTIVE_LIMITED']
    improved=[r for r in pairs if r['extra_passage'] and r.get('extra_strict_feasible') and r.get('extra_cost',float('inf'))<r['U3_cost']]
    if cheap or improved:conclusions.append('INIT_LIMITED: '+str(len(cheap))+'/5converted detours have lower cost than saved U3; '+str(len(improved))+'/5extra-start outputs are strictly feasible passage paths cheaper than saved U3. This is same-input diagnostic evidence, not a proposed initialization change.')
    if expensive:
        f7_count=sum(r.get('largest_term_delta')=='F7' for r in pairs);selected=sum(r['selected_passage'] for r in pairs)
        conclusions.append('OBJECTIVE_LIMITED: '+str(len(expensive))+'/5converted detours have higher frozen U3 cost; F7 is the largest increasing term in'+str(f7_count)+'/5pairs. Seeded multistart selects a passage path in'+str(selected)+'/5cases. This compares these particular feasible-heading/time embeddings, not every possible SE(2)timing for the polyline.')
    if summary['direction_wrong']:conclusions.append('DIRECTION_WRONG: '+str(summary['direction_wrong_count'])+'/16intent directions differ from evaluation-only+x by at least45degrees, exceeding half.')
    summary['conclusions']=conclusions;write(OUT/'summary.json',summary)
    converged=sum(r['extra_solver_success'] is True for r in pairs);converged_pass=sum(r['extra_solver_success'] is True and r['extra_passage'] for r in pairs)
    text='# Phase23-O3 — frozen-weight pre-passage diagnosis\n\n**PRE_PASSAGE_NO_GO**. Original **GO_ONLINE** is preserved at commit `a2ce323` and in `research/results/phase23o3/gate.json`.\n\n'+WARNING+'。\n\n'+table(rows)+'\n\n'
    text+='## Scope and fixed conversion\n\nOnly the16pre-passage training snapshots are used. The5passing comparator paths belong to3snapshots (twoC0and threeC1paths). No tuning, evaluation-set rerun, navigation, inference or rendering was performed for this diagnosis. U3weights remain w7=0.5, T_m=2s, c=1, time/goal/curvature=1/1/0.01.\n\n'
    text+='Every reference is projected and re-sampled to11positions from the saved U3predicted application pose. Native comparator XY has no yaw/timestamps. Chord-heading targets are sequentially projected onto the existing0.4rad per1s limit; dt=max(0.05,segment_length/0.3,abs(delta_heading)/0.4). Unmodified chord headings would require dt>1s in4/5paths, so heading lag is explicitly reported and its nonholonomic soft cost is included. Positions are not optimized during conversion. The test uses the U3hard motion constraints; acceleration remains the unchanged soft penalty. Hard depth feasibility is checked independently, never assumed from the source path.\n\n'
    text+='Factor sums reproduce the exact frozen objective; saved U3costs are checked against the recorded values. F1includes Cauchy+age cost; F2is clearance preference; F3includes nonholonomic/backward and soft acceleration; F4time; F5active-candidate goal; F6curvature change; F7intent progress.\n\n'
    text+='## Cost comparison\n\n'+table(comparison)+'\n\n'+table(cost_view)+'\n\n## Soft penalties and constraint checks\n\n'+table(soft_view)+'\n\n'
    text+='## Additional initialization experiment (diagnostic only)\n\nOne run per reference pair, no retries. The additional converted state is scheduled first, followed by the unchanged8current starts and available left/right starts. Four workers, shared0.5s, maxiter100, ftol1e-8, frozen output policy. Extra-first scheduling is diagnostic-only and is not installed in U3. Extra-start convergence/output and the whole multistart selection are separate columns. Pending-at-deadline convergence is unknown, not declared successful.\n\n'+table(init_view)+f'\n\nExtra-start solver success:{converged}/5; converged passage outputs:{converged_pass}/5. The3feasible passage candidates retained by extra starts are not converged passage solutions (two remain at their initial path). All5overall selections are non-passage paths.\n\n'
    text+='## Left/right initialization availability\n\n'+table(availability)+'\n\nReasons are the existing initializer metadata; absence of a candidate-intersecting depth component is not evidence that a geometric detour does not exist.\n\n'
    text+='## F7 direction and memory\n\n+x is evaluation-only. Angles refer to the actual F7mean of unit endpoint directions, with the same age weights. Candidate-level signed/absolute angles, lengths, eligibility and supplementation are preserved in candidate_directions.csv; set-level distributions are below.\n\n'+table(direction)+'\n\n'+table(sets)+'\n\n'
    text+='## Representative snapshots\n\nThe three snapshots with passing references plus the first other pre-passage input were fixed before the new solves. The fourth has no passing reference and therefore no extra-initialization solve. Thin candidate curves: current gray/history cyan; comparator paths dashed; extra-start best and multistart-selected outputs are distinct when different.\n\n'
    for image in images:text+=f'![{image}](../research/results/phase23o3_diagnosis/{image})\n\n'
    text+='## Conclusions\n\n'+'\n'.join('- '+c for c in conclusions)+'\n'
    (ROOT/'docs/PHASE23O3_DIAGNOSIS.md').write_text(text)


def plots(protocol,records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    from nomad_phase23o2.graph import mixture
    from nomad_phase22.drive_geometry import corners
    from nomad_phase16.geometry import centered
    from nomad_isaac.clearance import configured_obstacles
    images=[]
    for identity in protocol['figures']:
        r=records[identity];c=r['case'];B=np.asarray(r['original']['plan']['B_pred']);q,_,_,meta,_=mixture(c,B);allpoints=[B[None,:2],*list(q)]
        fig,ax=plt.subplots(figsize=(10,6),constrained_layout=True)
        for i,path in enumerate(q):ax.plot(*path.T,color='.6' if meta[i]['set_index']==0 else 'skyblue',lw=.7,alpha=.5,label='Current candidates' if i==0 else 'Memory candidates' if i==8 else None)
        for box in configured_obstacles(c['oracle_config']):
            polygon=corners(box);allpoints.append(polygon);ax.add_patch(Polygon(polygon,color='.3',alpha=.3))
        cfg,offset=centered(c['oracle_config']);co=cfg['corridor'];wall=np.array([[co['xmin'],-co['half_width']],[co['xmax'],-co['half_width']],[co['xmax'],co['half_width']],[co['xmin'],co['half_width']],[co['xmin'],-co['half_width']]])+[0,offset];ax.plot(*wall.T,c='.4')
        path=r['original']['plan'].get('path')
        if path is not None:path=np.asarray(path);allpoints.append(path);ax.plot(*path.T,color='seagreen',lw=2.2,zorder=5,label='Saved U3')
        for method,color in (('C0','darkorange'),('C1','steelblue')):
            path=r['base'][method]['plan'].get('path')
            if path is not None:path=np.asarray(path);allpoints.append(path);ax.plot(*path.T,'--',color=color,lw=1.5,label=method+' reference')
        for method,color in (('C0','magenta'),('C1','saddlebrown')):
            extra=r['extra'].get(method)
            if not extra:continue
            outcome=extra['outcome'];best=outcome['starts'][0];selected=outcome['selected']
            if best.get('path') is not None:
                path=np.asarray(best['path']);allpoints.append(path);ax.plot(*path.T,':',color=color,lw=2,label=method+' extra-start best')
            if selected.get('path') is not None:
                path=np.asarray(selected['path']);allpoints.append(path);ax.plot(*path.T,'-.',color=color,lw=1.2,zorder=4,label=method+' seeded multistart output')
        d=np.asarray(r['direction_world'])*.55;ax.quiver(B[0],B[1],d[0],d[1],angles='xy',scale_units='xy',scale=1,color='crimson',label='F7 intent direction')
        ax.quiver(B[0],B[1],.55,0,angles='xy',scale_units='xy',scale=1,color='black',alpha=.5,label='Evaluation +x')
        ax.scatter(*B[:2],marker='x',c='black',label='U3 application B');points=np.concatenate(allpoints);lo=points.min(axis=0)-.35;hi=points.max(axis=0)+.35
        if hi[1]-lo[1]<1.2:mid=(hi[1]+lo[1])/2;lo[1]=mid-.6;hi[1]=mid+.6
        ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_aspect('equal');ax.set_xlabel('World x(m)');ax.set_ylabel('World y(m)')
        ax.set_title(c['scene']+' '+identity+f" — F7 vs+x: {r['direction_angle_deg']:.1f}deg");ax.legend(loc='upper left',bbox_to_anchor=(1.01,1.),fontsize=8)
        name='diagnosis_'+identity+'.png';fig.savefig(OUT/name,dpi=150);plt.close(fig);images.append(name)
    return images
