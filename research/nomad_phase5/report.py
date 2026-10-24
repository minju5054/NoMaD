"""Preregistered Phase5 result/mechanism tables and exactly two figures."""
import argparse
import json
from pathlib import Path
import traceback
import numpy as np
from scipy.stats import fisher_exact
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import rows,stats
from nomad_phase0.chunk_report import trace
from nomad_phase4.report import write_csv
from nomad_phase4c.report import summarize
from .batch import matrix,completion
from .config import METHODS,protocol
from .metrics import audit


def load(root):
    state,done=completion(root);assert done,f'All48 attempts must finish: {state}'
    plan=json.loads((root/'plan.json').read_text());assert plan['jobs']==matrix(root) and plan['protocol']==protocol()
    for name,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(name))==h,'Frozen input changed: '+name
    journal=rows(root/'execution.jsonl');starts=[r for r in journal if r['event']=='START'];ends=[r for r in journal if r['event']=='END']
    assert all(r['git_sha']==plan['git_sha'] for r in journal)
    assert all(ends[i-1]['monotonic_ns']<starts[i]['monotonic_ns'] for i in range(1,len(starts)))
    records=[]
    for j in plan['jobs']:
        try:
            old=json.loads((root/'metrics'/f"{j['key']}.json").read_text())
            if old.get('launcher_exit_code')!=0:raise RuntimeError(old.get('error','Launcher failed'))
            r=audit(Path(j['output']),j['run_id'],j['seed_offset'],.75)
            assert r['execution_git_sha']==plan['git_sha']
            for name,h in old.get('input_log_sha256',{}).items():assert sha256_file(Path(j['output'])/name)==h
        except Exception as e:r=dict(classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False,error=repr(e),traceback=traceback.format_exc())
        r.update({k:v for k,v in j.items() if k not in ('argv','shell_command')});records.append(r)
    return records,plan


def decide(records):
    valid=[r for r in records if r.get('technical_validation')=='PASS']
    counts={m:sum(bool(r.get('success')) for r in valid if r['method']==m) for m in METHODS}
    c1=counts['GRAPH']>=counts['CURV']+3;c2=counts['GRAPH']>=counts['RIGID-ENTRY']+2
    c3={}
    for m in METHODS[3:]:
        d=counts['GRAPH']-counts[m]
        c3[m]={'difference':d,'verdict':'CONTRIBUTES' if d>=2 else 'NOT_SHOWN' if d>=0 else 'ABLATION_BETTER'}
    fisher={}
    for m in METHODS:
        if m=='GRAPH':continue
        table=[[counts[k],sum(r['method']==k for r in valid)-counts[k]] for k in ('GRAPH',m)]
        fisher[m]=float(fisher_exact(table,alternative='two-sided').pvalue) if all(sum(row) for row in table) else None
    return dict(success_counts=counts,C1=c1,C2=c2,C3=c3,
        verdict='GRAPH_SUPPORTED' if c1 and c2 else 'RIGID_SUFFICIENT_POSSIBLE' if c1 else 'NOT_REPLICATED',
        fisher_exact_two_sided_p=fisher,complete_technical_evidence=len(valid)==48,
        technical_failure_count=len(records)-len(valid))


def mechanisms(records,method):
    group=[r for r in records if r['method']==method and r.get('technical_validation')=='PASS']
    n=sum(r['control_count'] for r in group);v=sum(r['valid_pp_control_ticks'] for r in group)
    cat=lambda name:[x for r in group for x in r.get(name,[])]
    return dict(method=method,valid=len(group),endpoint_clamp_fraction=sum(r['endpoint_clamped_ticks'] for r in group)/n if n else None,
        curvature_saturated_fraction=sum(r['curvature_saturated_ticks'] for r in group)/n if n else None,
        circling_runs=sum(r['circling']['exists'] for r in group),
        cumulative_abs_yaw_rad=stats([r['circling']['cumulative_abs_heading_rad'] for r in group]),
        executed_path_staleness=stats(cat('applied_staleness_samples')),corrected_path_staleness=stats(cat('corrected_staleness_samples')),
        switch_abs_dw=stats([h['abs_dw'] for r in group for h in r['handoffs']]),
        margin_violation_mean_s=float(np.mean([r['margin_violation_s'] for r in group])) if group else None,
        graph_calls=sum(r['graph']['calls'] for r in group),graph_accepted=sum(r['graph']['dispositions'].get('ACCEPTED',0) for r in group),
        graph_nonconverged=sum(r['graph']['independent_nonconverged'] for r in group),
        graph_constraint_failure=sum(r['graph']['independent_constraint_failure'] for r in group),
        graph_superseded=sum(r['graph']['dispositions'].get('SUPERSEDED',0) for r in group),
        graph_stale=sum(r['graph']['dispositions'].get('STALE',0) for r in group),
        graph_initialization_rejected=sum(r['graph']['dispositions'].get('INITIALIZATION_REJECTED',0) for r in group),
        graph_terminal_unapplied=sum(r['graph']['terminal_unapplied'] for r in group),
        graph_solve_wall_s=stats(cat('solver_wall_samples_s')),
        graph_corrected_control_fraction=sum(r['graph']['corrected_control_ticks'] for r in group)/v if v else None,
        rigid_applied=sum(r['rigid_applied'] for r in group),rigid_rejected=sum(r['rigid_rejected'] for r in group))


def overlay_index(records):
    valid={(r['index'],r['method']):r for r in records if r.get('technical_validation')=='PASS'}
    return next((i for i in range(9,17) if (i,'CURV') in valid and (i,'GRAPH') in valid and
        not valid[i,'CURV']['success'] and valid[i,'GRAPH']['success']),None)


def plot(out,records,decision):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    labels=[protocol()['display_names'].get(m,m) for m in METHODS]
    fig,ax=plt.subplots(figsize=(10,4));ax.bar(labels,[decision['success_counts'][m] for m in METHODS])
    ax.set(ylabel='Successful runs /8',ylim=(0,8.5),title='Phase5 D750 / alpha infinity / indices9–16');ax.tick_params(axis='x',labelrotation=15)
    fig.tight_layout();fig.savefig(out/'success_counts.png',dpi=160);plt.close(fig)
    index=overlay_index(records);fig,ax=plt.subplots(figsize=(10,5))
    if index is None:
        ax.text(.5,.5,'No technically valid CURV-failure / GRAPH-success index',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off()
    else:
        c=json.loads((ROOT/protocol()['scenario']).read_text());corr=c['corridor']
        for b in c['obstacles']:
            x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='green',alpha=.3))
        ax.axhline(corr['half_width'],color='black');ax.axhline(-corr['half_width'],color='black')
        ax.add_patch(Circle(c['goal_pose'][:2],c['goal_tolerance_m'],fill=False,linestyle='--'))
        for method in METHODS:
            r=next(r for r in records if r['index']==index and r['method']==method)
            if not (Path(r['output'])/'agent_trajectory.csv').exists():continue
            _,poses=trace(Path(r['output']));ax.plot(poses[:,0],poses[:,1],label=f"{method}: {r['classification']}")
            ax.scatter(*poses[-1,:2],marker='o' if r.get('success') else 'x')
        ax.set(xlabel='World X (m)',ylabel='World Y (m)',title=f'Actual paths, index{index}',xlim=(corr['xmin'],corr['xmax']),ylim=(-corr['half_width']-.1,corr['half_width']+.1))
        ax.set_aspect('equal');ax.legend(fontsize=7);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(out/'paired_paths.png',dpi=160);plt.close(fig)
    return index


def generate(root,out,doc):
    assert not out.exists() and not doc.exists(),'Existing report preserved'
    records,plan=load(root);assert len(records)==48 and len({r['key'] for r in records})==48
    groups=[summarize(records,'inf',m) for m in METHODS];mech=[mechanisms(records,m) for m in METHODS];decision=decide(records)
    paired=[]
    for i in range(9,17):
        row={'index':i,'seed_offset':i*10000}
        for m in METHODS:row[m]=next(r['classification'] for r in records if r['index']==i and r['method']==m)
        paired.append(row)
    out.mkdir(parents=True,exist_ok=False);index=plot(out,records,decision)
    write_json(out/'summary.json',dict(execution_git_sha=plan['git_sha'],protocol=protocol(),conditions=groups,mechanisms=mech,decision=decision,overlay_index=index))
    write_json(out/'runs.json',[{k:v for k,v in r.items() if k not in ('handoffs','request_seeds','input_log_sha256')} for r in records])
    write_csv(out/'conditions.csv',groups);write_csv(out/'mechanisms.csv',mech);write_csv(out/'paired.csv',paired)
    f=lambda x:'N/A' if x is None else f'{x:.4f}'
    text=['# Phase5 Baseline and Ablation','',f"Git SHA: `{plan['git_sha']}`. Oracle geometry; SE(2) kinematic Isaac Sim. N=8 per method; D750, alpha infinity, v_max0.3.",'',
        '|Method|Success/8|Collision|Corridor|Timeout|Technical|Goal median s|Mean speed m/s|Min clearance m|','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for g in groups:text.append(f"|{g['method']}|{g['success']}/8|{g['collision']}|{g['corridor']}|{g['timeout']}|{g['technical_failure']}|{f(g['goal_time_median_s'])}|{f(g['mean_speed_m_s'])}|{f(g['minimum_clearance_m'])}|")
    text+=['','|Method|Clamp fraction|Curvature saturation|Yaw variation ≥2π runs|Applied staleness median/p95|Corrected staleness median|Switch Δω median/max|Mean margin violation s|','|---|---:|---:|---:|---|---:|---|---:|']
    for g in mech:text.append(f"|{g['method']}|{f(g['endpoint_clamp_fraction'])}|{f(g['curvature_saturated_fraction'])}|{g['circling_runs']}|{f(g['executed_path_staleness'].get('median'))}/{f(g['executed_path_staleness'].get('p95'))}|{f(g['corrected_path_staleness'].get('median'))}|{f(g['switch_abs_dw'].get('median'))}/{f(g['switch_abs_dw'].get('max'))}|{f(g['margin_violation_mean_s'])}|")
    text+=['','|Method|Calls|Accepted|Nonconverged|Constraint failed|Superseded|Stale|Init rejected|Terminal pending|Solve median/p95/max s|Corrected control fraction|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|']
    for g in mech:
        t=g['graph_solve_wall_s'];text.append(f"|{g['method']}|{g['graph_calls']}|{g['graph_accepted']}|{g['graph_nonconverged']}|{g['graph_constraint_failure']}|{g['graph_superseded']}|{g['graph_stale']}|{g['graph_initialization_rejected']}|{g['graph_terminal_unapplied']}|{f(t.get('median'))}/{f(t.get('p95'))}/{f(t.get('max'))}|{f(g['graph_corrected_control_fraction'])}|")
    text+=['','|Index|'+'|'.join(METHODS)+'|','|---|'+'---|'*6]
    for r in paired:text.append('|'+str(r['index'])+'|'+'|'.join(r[m] for m in METHODS)+'|')
    text+=['',f"C1: `{decision['C1']}`; C2: `{decision['C2']}`; overall: **{decision['verdict']}**.",'','|Ablation|GRAPH−ablation success count|C3|','|---|---:|---|']
    for m,d in decision['C3'].items():text.append(f"|{m}|{d['difference']}|{d['verdict']}|")
    text+=['','|GRAPH versus|Fisher exact two-sided p (reference only)|','|---|---:|']
    for m,p in decision['fisher_exact_two_sided_p'].items():text.append(f'|{m}|{f(p)}|')
    text+=['',f"Complete technical evidence: `{decision['complete_technical_evidence']}`. Technical failures are separate and have no imputed goal time. Goal medians use successful runs only. Nonconvergence and constraint-failure diagnostics can overlap.",
        'Applied staleness pools native immediate switches, RIGID replacements, and accepted Graph replacements; corrected-only excludes RAW. Clamp/saturation use all9Hz ticks. Corrected control fraction uses valid PP ticks.',
        'The yaw-variation flag is the literal cumulative absolute heading criterion. Oscillations also count; it is not proof of a spatial loop. NO-SDF retains corridor checks and actual collision monitoring but has no native obstacle acceptance certificate.',
        protocol()['seed_provenance'],'Paired seeds do not ensure identical closed-loop RGB. Fisher p is descriptive and is not used for C1/C2/C3.',
        '', '![Success counts](../research/results/phase5/success_counts.png)', '', '![Paired actual paths](../research/results/phase5/paired_paths.png)']
    failed=[r for r in records if r.get('technical_validation')!='PASS']
    if failed:
        text+=['','|Technical failure|Error|','|---|---|']
        for r in failed:text.append(f"|{r['key']}|{r.get('error')}|")
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(text)+'\n');return decision


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'research/results/phase5');p.add_argument('--document',type=Path,default=ROOT/'docs/PHASE5_ABLATION.md')
    a=p.parse_args();print(generate(a.run_root.resolve(),a.output,a.document)['verdict'])


if __name__=='__main__':main()
