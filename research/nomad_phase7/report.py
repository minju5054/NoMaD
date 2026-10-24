"""Automatic Phase7 report, including NOT_READY RTC-style (DDPM adaptation) rows."""
import argparse
import json
from pathlib import Path
import traceback
import numpy as np
from scipy.stats import fisher_exact
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import rows,stats
from nomad_phase4.report import write_csv
from nomad_phase6.report import group,flat_mechanism,aggregate_mechanisms
from nomad_phase6.metrics import mechanisms
from .config import protocol,readiness
from .batch import matrix,references,completion


def load(root):
    state,done=completion(root);assert done,f'Incomplete Phase7: {state}'
    plan=json.loads((root/'plan.json').read_text());p=protocol()
    assert plan['jobs']==matrix(root) and plan['references']==references() and plan['protocol']==p
    assert plan['rtc_readiness']==readiness()
    for name,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(name))==h,'Frozen input changed: '+name
    journal=rows(root/'execution.jsonl');starts=[r for r in journal if r['event']=='START'];ends=[r for r in journal if r['event']=='END']
    assert all(r['git_sha']==plan['git_sha'] for r in journal)
    assert all(ends[i-1]['monotonic_ns']<starts[i]['monotonic_ns'] for i in range(1,len(starts)))
    records=[]
    for j in plan['references']+plan['jobs']:
        try:
            run=Path(j['output'])
            key=f"{j['run_id']}_{j['method']}" if j.get('source_phase')==5 else j['key']
            path=(run.parent if j['reused'] else root)/'metrics'/f'{key}.json'
            old=json.loads(path.read_text())
            if old.get('launcher_exit_code')!=0 or old.get('technical_validation')!='PASS':raise RuntimeError(old.get('error','Execution/audit failed'))
            if not j['reused']:assert old['execution_git_sha']==plan['git_sha']
            assert old['index']==j['index'] and old['method']==j['method'] and old['delay_s']==j['delay_s']
            for name,h in old['input_log_sha256'].items():assert sha256_file(run/name)==h,'Run input changed: '+name
            r=dict(old);r['mechanisms']=mechanisms(run,r['success'])
            inference=rows(run/'model/inference.jsonl')
            r['inference_ms']=stats([m['inference_ms'] for m in inference[1:]])
        except Exception as exc:
            r=dict(classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False,error=repr(exc),traceback=traceback.format_exc())
        r.update({k:v for k,v in j.items() if k not in ('argv','shell_command')});records.append(r)
    assert len(records)==96 and len({r['key'] for r in records})==96
    return records,plan


def comparison(records,method):
    g=group(records,.75,method)
    valid=[r for r in records if r['method']==method and r['delay_s']==.75 and r.get('technical_validation')=='PASS']
    med=[r['inference_ms']['median'] for r in valid if r.get('inference_ms',{}).get('median') is not None]
    g['inference_run_median_ms']=float(np.median(med)) if med else None
    g['execution_status']='RTC_NOT_READY_NOT_RUN' if method.startswith('RTC') and not valid else 'ATTEMPTED'
    return g


def verdict(a,b,minimum=7):
    return 'INCONCLUSIVE' if min(a['valid'],b['valid'])<minimum else 'PASS' if a['success']>=b['success']+2 else 'FAIL'


def decide(records):
    g={m:comparison(records,m) for m in ('GRAPH','SELECT','RTC','RTC+GRAPH')}
    pvalues={}
    for name,a,b in (('BEATS_SELECT','GRAPH','SELECT'),('BEATS_RTC','GRAPH','RTC'),('GRAPH_ADDS_TO_RTC','RTC+GRAPH','RTC')):
        x,y=g[a],g[b]
        pvalues[name]=float(fisher_exact([[x['success'],x['valid']-x['success']],[y['success'],y['valid']-y['success']]]).pvalue) if min(x['valid'],y['valid']) else None
    delta={str(round(d*1000)):group(records,d,'GRAPH')['success']-group(records,d,'CURV')['success'] for d in (0.,.25,.5,.625,.75)}
    return dict(BEATS_SELECT=verdict(g['GRAPH'],g['SELECT']),BEATS_RTC=verdict(g['GRAPH'],g['RTC']),
        GRAPH_ADDS_TO_RTC=verdict(g['RTC+GRAPH'],g['RTC']),delta_success_counts=delta,
        fisher_two_sided_reference=pvalues,rtc_readiness=readiness()['verdict'],
        technical_failures=sum(r.get('technical_validation')!='PASS' for r in records))


def plot(out,delays,alternatives):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,4.5))
    for method,color in (('CURV','#777777'),('GRAPH','#176ca4')):
        gs=[g for g in delays if g['method']==method and g['valid_success_rate'] is not None]
        x=[g['delay_ms'] for g in gs];y=np.array([g['valid_success_rate'] for g in gs])
        low=np.array([g['success_wilson95_valid'][0] for g in gs]);high=np.array([g['success_wilson95_valid'][1] for g in gs])
        if gs:ax.errorbar(x,y,yerr=np.maximum(0,np.stack([y-low,high-y])),marker='o',capsize=4,color=color,label=method)
    ax.set(xlabel='Post-packet delivery delay (ms)',ylabel='Success fraction (valid runs)',ylim=(-.05,1.05),xticks=[0,250,500,625,750],title='S0 paired indices9–16; Wilson95 descriptive')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(out/'delay_success.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4.5))
    for i,g in enumerate(alternatives):
        if g['attempts']:
            ax.bar(i,g['success'],color='#176ca4');ax.text(i,g['success']+.12,f"{g['success']}/{g['attempts']}",ha='center')
        else:ax.text(i,.3,'NOT RUN\nRTC_NOT_READY',ha='center',fontsize=8)
    labels=[g['method'].replace('RIGID-ENTRY','RIGID').replace('RTC','RTC-style\n(DDPM adaptation)') for g in alternatives]
    ax.set(xticks=range(len(labels)),xticklabels=labels,ylabel='Success count',ylim=(0,8.8),title='D750; unavailable RTC conditions are not zero successes')
    fig.tight_layout();fig.savefig(out/'d750_success.png',dpi=160);plt.close(fig)


def generate(root,out,doc):
    assert not out.exists() and not doc.exists(),'Existing report preserved'
    records,plan=load(root);p=protocol();offline=json.loads((ROOT/p['readiness_results']).read_text())
    alternatives=[comparison(records,m) for m in ('CURV','RIGID-ENTRY','SELECT','RTC','GRAPH','RTC+GRAPH')]
    delays=[group(records,d,m) for d in (0.,.25,.5,.625,.75) for m in ('CURV','GRAPH')]
    flat=[]
    for r in records:
        if r.get('technical_validation')!='PASS':continue
        for window in ('full','last3s'):
            value=flat_mechanism(r,window)
            if value is not None:flat.append(value)
    mech=aggregate_mechanisms(flat,delay_values=(0.,.25,.5,.625,.75));decision=decide(records)
    out.mkdir(parents=True,exist_ok=False);plot(out,delays,alternatives)
    write_json(out/'summary.json',dict(execution_git_sha=plan['git_sha'],protocol=p,alternatives=alternatives,delays=delays,decisions=decision,mechanisms=mech,rtc_offline=offline))
    write_json(out/'runs.json',[{k:v for k,v in r.items() if k not in ('request_seeds','input_log_sha256','handoffs','mechanisms','traceback')} for r in records])
    write_json(out/'input_hashes.json',{r['key']:dict(execution_git_sha=r.get('execution_git_sha'),audit=r.get('input_log_sha256'),mechanisms=r.get('mechanisms',{}).get('input_sha256')) for r in records})
    write_csv(out/'d750_comparison.csv',alternatives);write_csv(out/'delay_comparison.csv',delays)
    write_csv(out/'mechanisms_runs.csv',flat);write_csv(out/'mechanisms_groups.csv',mech)
    f=lambda x:'N/A' if x is None else f'{x:.4f}'
    text=['# Phase7 Results','',f"Execution SHA: `{plan['git_sha']}`. Oracle geometry; SE(2) kinematic Isaac Sim; N8 paired exploratory conditions.",
        '24 new attempts: SELECT D750×8 and CURV/GRAPH D625×8 each. 72 historical records reused once. RTC-style (DDPM adaptation) and RTC-style (DDPM adaptation)+GRAPH were NOT RUN because readiness failed.',
        '', 'Table 1 — D750','', '|Method|Success/attempts|Collision|Corridor|Timeout|Technical|Goal median s|Mean speed m/s|Min clearance m|Inference median ms|',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for g in alternatives:
        name=g['method'].replace('RTC','RTC-style (DDPM adaptation)')
        if not g['attempts']:text.append(f'|{name}|NOT RUN|N/A|N/A|N/A|N/A|N/A|N/A|N/A|N/A|');continue
        text.append(f"|{name}|{g['success']}/{g['attempts']}|{g['collision']}|{g['corridor']}|{g['timeout']}|{g['technical_failure']}|{f(g['goal_time_median_s'])}|{f(g['mean_speed_m_s'])}|{f(g['minimum_clearance_m'])}|{f(g['inference_run_median_ms'])}|")
    text+=['','Table 2 — delay sweep','','|D ms|Method|Success/attempts|Valid|Collision|Corridor|Timeout|Technical|Wilson95|','|---:|---|---|---:|---:|---:|---:|---:|---|']
    for g in delays:
        ci=g['success_wilson95_valid'];text.append(f"|{g['delay_ms']}|{g['method']}|{g['success']}/{g['attempts']}|{g['valid']}|{g['collision']}|{g['corridor']}|{g['timeout']}|{g['technical_failure']}|{f(ci[0])}–{f(ci[1])}|")
    text+=['','Table 3 — mechanism run summaries (pooled delays, same Phase6 definitions)','','|Method|Outcome|Window|Runs|Heading median/p95 rad|Cross-track median/p95 m|Time abs(y)>1 s|Min wall clearance m|',
        '|---|---|---|---:|---|---|---:|---:|']
    for g in mech:
        if g['delay_ms']!='pooled':continue
        text.append(f"|{g['method']}|{g['outcome']}|{g['window']}|{g['runs']}|{f(g['heading_abs_rad_median_run_mean'])}/{f(g['heading_abs_rad_p95_run_mean'])}|{f(g['cross_track_m_median_run_mean'])}/{f(g['cross_track_m_p95_run_mean'])}|{f(g['time_abs_y_over1_s_run_mean'])}|{f(g['minimum_wall_footprint_clearance_lower_m_run_mean'])}|")
    text+=['','|Independent criterion|Result|','|---|---|']
    for key in ('BEATS_SELECT','BEATS_RTC','GRAPH_ADDS_TO_RTC'):text.append(f'|{key}|{decision[key]}|')
    text+=['',f"Δ(0,250,500,625,750): `{decision['delta_success_counts']}`.",f"Fisher p (reference only): `{decision['fisher_two_sided_reference']}`.",
        'Any involved method with fewer than7 valid runs yields INCONCLUSIVE. Historical Phase6 BEATS_SELECT is corrected to INCONCLUSIVE in the separate addendum; original artifacts were preserved. New SELECT runs are not replaced by the repaired historical audit.',
        'Goal times use successful runs only. Inference is the median of per-run warm medians (first inference excluded). Wilson/Fisher use valid denominators, are descriptive only, and do not account for paired dependence. Identical seeds do not imply identical closed-loop RGB.',
        'Mechanism tables average per-run statistics; short projected segments (<20mm) have invalid heading rather than invented yaw. Failure last3s windows can have no switches (null). Wall clearance is a swept footprint lower bound; |y|>1 duration uses72Hz end poses. Detail and valid denominators are in CSV.',
        '', 'RTC-style (DDPM adaptation) offline validation:',
        f"50 frozen inputs, W0 maximum error={offline['max_off_error']:.6g}; fixed sample0 prefix median={offline['frozen_sample0_median_m']:.6f}m; overlap RMSE improved {offline['overlap_improved_inputs']}/50. Verdict: **{offline['verdict']}**.",
        f"RAW latency median/p95={f(offline['timing_ms']['off']['median'])}/{f(offline['timing_ms']['off']['p95'])}ms; guided={f(offline['timing_ms']['on']['median'])}/{f(offline['timing_ms']['on']['p95'])}ms. No tuning/restart or RTC navigation was performed.",
        '[RTC paper Appendix A.4](https://arxiv.org/html/2506.07339v1#A1.SS4) confirms beta5. The preregistered variance-preconditioned DDPM VJP is an adaptation, not the paper’s flow integration; no hard prefix overwrite. This readiness failure is not evidence that the original RTC algorithm fails.',
        '', '![Delay](../research/results/phase7/delay_success.png)', '', '![D750](../research/results/phase7/d750_success.png)']
    failures=[r for r in records if r.get('technical_validation')!='PASS']
    if failures:
        text+=['','|Technical failure|Error|','|---|---|']
        for r in failures:text.append(f"|{r['key']}|{r.get('error')}|")
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(text)+'\n');return decision


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'research/results/phase7')
    p.add_argument('--document',type=Path,default=ROOT/'docs/PHASE7_RESULTS.md')
    a=p.parse_args();print(json.dumps(generate(a.run_root.resolve(),a.output,a.document)))


if __name__=='__main__':main()
