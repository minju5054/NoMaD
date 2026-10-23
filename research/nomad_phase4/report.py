"""Automatic read-only pilot audit, decision, table and exactly one XY figure."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import traceback
import numpy as np
from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_isaac.async_report import rows, stats
from nomad_phase0.chunk_report import trace
from nomad_phase0.s0_batch_metrics import wilson
from .config import protocol, METHODS
from .batch import matrix
from .metrics import audit


def median(x):
    a=[v for v in x if v is not None]
    return float(np.median(a)) if a else None


def decision(records):
    groups={m:[r for r in records if r['delay_s']==.75 and r['method']==m] for m in METHODS}
    graph,curv=groups['GRAPH-v5'],groups['CURV-SPEED']
    d0=[r for r in records if r['delay_s']==0 and r['method']=='GRAPH-v5']
    good=lambda r:r.get('technical_validation')=='PASS' and r.get('success',False)
    gm=median([r.get('goal_time_s') for r in graph if good(r)])
    cm=median([r.get('goal_time_s') for r in curv if good(r)])
    checks={'all_14_technical_PASS':len(records)==14 and all(r.get('technical_validation')=='PASS' for r in records),
        'D750_graph_success_ge_curv':len(graph)==len(curv)==4 and sum(map(good,graph))>=sum(map(good,curv)),
        'D750_graph_goal_median_le_90pct_curv':gm is not None and cm is not None and gm<=.9*cm,
        'D0_graph_2_of_2_success':len(d0)==2 and all(map(good,d0))}
    return {'verdict':'PROCEED_TO_PARETO' if all(checks.values()) else 'STOP_AND_REPORT',
        'checks':checks,'D750_graph_goal_median_s':gm,'D750_curv_goal_median_s':cm,
        'scope':'Pilot only; undefined successful goal median fails. No automatic extension.'}


def summarize(records,method,delay):
    group=[r for r in records if r['method']==method and r['delay_s']==delay]
    valid=[r for r in group if r.get('technical_validation')=='PASS']
    success=[r for r in valid if r['success']]
    gstats=[r['graph'] for r in valid]
    counts=Counter()
    for g in gstats:counts.update(g['dispositions'])
    switches=[h['abs_dw'] for r in valid for h in r['handoffs']]
    return {'method':method,'delay_ms':round(delay*1000),'attempts':len(group),'valid':len(valid),
        'success':len(success),'success_wilson95':wilson([r['success'] for r in valid]) if valid else None,
        'collision':sum(r['geometric_overlap'] for r in valid),'corridor':sum(r['corridor_violation'] for r in valid),
        'timeout':sum(r['classification']=='STUCK' for r in valid),'technical_failure':len(group)-len(valid),
        'other_termination':sum(r['classification'] not in ('SUCCESS','SAFETY_FAILURE','STUCK') for r in valid),
        'goal_time_median_s':median([r['goal_time_s'] for r in success]),
        'mean_speed_m_s':float(np.mean([r['mean_speed_m_s'] for r in valid])) if valid else None,
        'minimum_clearance_m':min((r[f'StaticObstacle{i}_minimum_clearance_m'] for r in valid for i in (1,2)),default=None),
        'margin_violation_total_s':sum(r['margin_violation_s'] for r in valid),
        'stop_total_s':sum(r['stop_time_s'] for r in valid),'switch_abs_dw':stats(switches),
        'graph_calls':sum(g['calls'] for g in gstats),'graph_dispositions':dict(counts),
        'graph_corrected_ticks':sum(g['corrected_control_ticks'] for g in gstats),
        'graph_corrected_valid_fraction':sum(g['corrected_control_ticks'] for g in gstats)/sum(r['valid_pp_control_ticks'] for r in valid) if sum(r['valid_pp_control_ticks'] for r in valid) else None,
        'graph_independent_nonconverged':sum(g['independent_nonconverged'] for g in gstats),
        'graph_independent_constraint_failure':sum(g['independent_constraint_failure'] for g in gstats),
        'graph_terminal_unapplied':sum(g['terminal_unapplied'] for g in gstats),
        'temporal_acceleration_exceedance_ticks':sum(g['temporal_acceleration_exceedance_ticks'] for g in gstats)}


def load(root):
    plan=json.loads((root/'plan.json').read_text());global_errors=[]
    if plan['protocol']!=protocol():global_errors.append('Frozen protocol changed')
    if plan['jobs']!=matrix(root):global_errors.append('Frozen 14-job matrix changed')
    for name,digest in plan['fixed_input_sha256'].items():
        if not Path(name).is_file() or sha256_file(Path(name))!=digest:global_errors.append('Frozen input changed: '+name)
    journal=rows(root/'pilot_execution.jsonl') if (root/'pilot_execution.jsonl').exists() else []
    starts=[x for x in journal if x['event']=='START'];ends=[x for x in journal if x['event']=='END']
    expected=[j['key'] for j in plan['jobs']]
    if [x['key'] for x in starts]!=expected or [x['key'] for x in ends]!=expected:global_errors.append('Incomplete or duplicate execution journal')
    for i in range(1,len(starts)):
        if i-1<len(ends) and ends[i-1]['monotonic_ns']>=starts[i]['monotonic_ns']:global_errors.append('Non-serial journal')
    records=[];evidence={str(root/'plan.json'):sha256_file(root/'plan.json')}
    for job in plan['jobs']:
        metric_path=root/'metrics'/f"{job['key']}.json"
        try:
            if global_errors:raise ValueError('; '.join(global_errors))
            old=json.loads(metric_path.read_text())
            if old.get('launcher_exit_code')!=0:raise RuntimeError(f"Launcher failure: {old.get('error')}")
            metric=audit(Path(job['output']),job['run_id'],job['seed_offset'],job['delay_s'])
            if metric['execution_git_sha']!=plan['git_sha']:raise ValueError('Execution SHA differs from plan')
            for name,digest in old.get('input_log_sha256',{}).items():
                if sha256_file(Path(job['output'])/name)!=digest:raise ValueError('Log changed since first audit: '+name)
            evidence[str(metric_path)]=sha256_file(metric_path)
        except Exception as e:
            metric={'classification':'TECHNICAL_FAILURE','technical_validation':'FAIL','success':False,
                'error':repr(e),'traceback':traceback.format_exc()}
        metric.update({k:v for k,v in job.items() if k not in ('argv','shell_command')})
        records.append(metric)
    return records,plan,evidence,global_errors


def plot(out,records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    c=json.loads((ROOT/protocol()['scenario']).read_text())
    fig,axes=plt.subplots(1,2,figsize=(11,4.2),sharex=True,sharey=True)
    colors={'RAW':'#777777','CURV-SPEED':'#d6860d','GRAPH-v5':'#176ca4'}
    for index,ax in enumerate(axes,1):
        for box in c['obstacles']:
            x,y=box['center_xy_m'];w,h=box['size_xyz_m'][:2]
            ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='#509d55',alpha=.45))
        corridor=c['corridor'];ax.axhline(corridor['half_width'],color='black');ax.axhline(-corridor['half_width'],color='black')
        goal=c['goal_pose'];ax.add_patch(Circle(goal[:2],c['goal_tolerance_m'],fill=False,linestyle='--',color='black'))
        for r in records:
            if r['delay_s']!=.75 or r['index']!=index:continue
            path=Path(r['output'])/'agent_trajectory.csv'
            if not path.exists():continue
            _,poses=trace(Path(r['output']))
            ax.plot(poses[:,0],poses[:,1],color=colors[r['method']],label=f"{r['method']}: {r['classification']}")
            ax.scatter(*poses[-1,:2],marker='o' if r.get('success') else 'x',color=colors[r['method']],s=35)
        ax.set_title(f'D750 / paired index {index}');ax.set_aspect('equal');ax.set_xlabel('World X (m)');ax.grid(alpha=.15);ax.legend(fontsize=7)
        ax.set_xlim(corridor['xmin'],c['corridor']['xmax']);ax.set_ylim(-corridor['half_width']-.15,corridor['half_width']+.15)
    axes[0].set_ylabel('World Y (m)');fig.suptitle('Actual SE(2) trajectories; oracle geometry; no counterfactual replay')
    fig.tight_layout();fig.savefig(out/'d750_paths.png',dpi=160);plt.close(fig)


def write_csv(path,records):
    keys=list(dict.fromkeys(k for r in records for k in r))
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for r in records:writer.writerow({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()})


def generate(root,out,doc):
    assert not out.exists() and not doc.exists(),'Existing report/results are preserved; choose a new destination explicitly'
    records,plan,evidence,errors=load(root)
    groups=[summarize(records,m,d) for d,methods in ((.75,METHODS),(0.,('GRAPH-v5',))) for m in methods]
    graphrows=[]
    for r in records:
        if r['method']!='GRAPH-v5' or not (Path(r['output'])/'stage2_graph.jsonl').exists():continue
        for x in rows(Path(r['output'])/'stage2_graph.jsonl'):
            if x['event']=='RESULT':graphrows.append({'run':r['key'],'delay_s':r['delay_s'],**x})
    for g in groups:
        rr=[x for x in graphrows if x['delay_s']==g['delay_ms']/1000] if g['method']=='GRAPH-v5' else []
        g['graph_solve_time_s']=stats([x['solver']['solver_wall_s'] for x in rr if 'solver' in x])
        g['graph_processing_time_s']=stats([x['processing_wall_s'] for x in rr])
        g['graph_wait_movement_m']=stats([x['movement_since_dispatch_m'] for x in rr])
        g['graph_correction_abs_dw']=stats([abs(x['after_vw'][1]-x['before_vw'][1]) for r in records if r['method']==g['method'] and r['delay_s']==g['delay_ms']/1000 and (Path(r['output'])/'stage2_graph.jsonl').exists() for x in rows(Path(r['output'])/'stage2_graph.jsonl') if x['event']=='APPLIED_COMMAND'])
    verdict=decision(records);out.mkdir(parents=True,exist_ok=False)
    write_json(out/'summary.json',{'protocol':protocol(),'execution_git_sha':plan['git_sha'],
        'technical_errors':errors,'decision':verdict,'groups':groups,'input_sha256':evidence})
    write_json(out/'runs.json',records);write_csv(out/'runs.csv',[{k:v for k,v in r.items() if k not in ('handoffs','request_seeds','input_log_sha256','traceback')} for r in records])
    write_csv(out/'conditions.csv',groups);plot(out,records)
    def f(x):return 'N/A' if x is None else f'{x:.4f}'
    text=['# Phase 4 Graph v5 pilot',f"Execution SHA: `{plan['git_sha']}`. `{verdict['verdict']}`.",
        protocol()['scope']+'. RAW/CURV execution cap 0.3m/s; NoMaD metric scaling unchanged.',
        'Technical validation: '+str(sum(r['technical_validation']=='PASS' for r in records))+'/14 PASS. Original RGB histories, Topomap, seeds, delay clocks, actual commands, 72Hz poses and swept clearance re-audited.',
        'Success = goal entry without overlap/corridor breach. 2cm margin violations are independent. Missing successful goal times are never replaced by timeout.',
        '|D ms|Method|Success/attempts|Collision|Corridor|Timeout|Technical|Goal median s|Mean speed m/s|Switch abs dw median|Graph calls/accepted|',
        '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for g in groups:text.append(f"|{g['delay_ms']}|{g['method']}|{g['success']}/{g['attempts']}|{g['collision']}|{g['corridor']}|{g['timeout']}|{g['technical_failure']}|{f(g['goal_time_median_s'])}|{f(g['mean_speed_m_s'])}|{f(g['switch_abs_dw'].get('median'))}|{g['graph_calls']}/{g['graph_dispositions'].get('ACCEPTED',0)}|")
    text+=['','## Preregistered decision',json.dumps(verdict,indent=2),'','## Run outcomes',
        '|Run|Result|Goal s|Mean speed m/s|Margin violation s|','|---|---|---:|---:|---:|']
    for r in records:text.append(f"|{r['key']}|{r['classification']}|{f(r.get('goal_time_s'))}|{f(r.get('mean_speed_m_s'))}|{f(r.get('margin_violation_s'))}|")
    text+=['','## Graph processing and limitations']
    for g in groups:
        if g['method']=='GRAPH-v5':text.append(f"D{g['delay_ms']}: dispositions `{g['graph_dispositions']}`; solve median/p95/max `{g['graph_solve_time_s']}` s; processing `{g['graph_processing_time_s']}` s; corrected valid ticks fraction {f(g['graph_corrected_valid_fraction'])}; correction abs dw `{g['graph_correction_abs_dw']}`; movement while waiting `{g['graph_wait_movement_m']}` m; temporal acceleration exceedance ticks {g['temporal_acceleration_exceedance_ticks']}.")
    text+=['The unchanged v4 full-path certificate does not certify a PP arc. Spatial node-speed acceleration constraints do not guarantee temporal acceleration at path replacement. Exact profile interpolation is logged separately from clipping. B_app predicts two control ticks, while application uses the first eligible tick: fast results can be APP_MISMATCH. STALE is worker processing >0.3s; queue time is separate.',
        'N=4/N=2 exploratory pilot; paired offsets do not imply identical RGB or predictions. Goal-time comparisons condition on success. No automatic follow-up, tuning or retries.',
        '',f'![D750 actual trajectories](../research/results/phase4_pilot/d750_paths.png)',
        '', '## Technical failures']
    text += [f"- {r['key']}: {r.get('error')}" for r in records if r['technical_validation']!='PASS'] or ['None.']
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(text)+'\n')
    return verdict


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'research/results/phase4_pilot')
    p.add_argument('--document',type=Path,default=ROOT/'docs/PHASE4_GRAPH_V5_PILOT.md')
    a=p.parse_args();result=generate(a.run_root.resolve(),a.output,a.document)
    print(result['verdict'])

if __name__=='__main__':main()
