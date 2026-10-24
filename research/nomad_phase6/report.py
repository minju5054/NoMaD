"""Read-only Phase6 report: frozen references, technical validation, three separate decisions."""
import argparse
import json
from pathlib import Path
import traceback
import numpy as np
from scipy.stats import fisher_exact
from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_isaac.async_report import rows
from nomad_phase4.report import write_csv
from nomad_phase4c.report import summarize
from .batch import matrix, references, completion
from .config import protocol
from .metrics import mechanisms


def wilson(k,n):
    if not n:return [None,None]
    z=1.959963984540054;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(mid-half),float(mid+half)]


def load(root):
    state,done=completion(root);assert done,f'All56 attempts must finish: {state}'
    plan=json.loads((root/'plan.json').read_text());p=protocol()
    assert plan['jobs']==matrix(root) and plan['references']==references() and plan['protocol']==p
    for name,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(name))==h,'Frozen input changed: '+name
    journal=rows(root/'execution.jsonl');starts=[r for r in journal if r['event']=='START'];ends=[r for r in journal if r['event']=='END']
    assert all(r['git_sha']==plan['git_sha'] for r in journal)
    assert all(ends[i-1]['monotonic_ns']<starts[i]['monotonic_ns'] for i in range(1,len(starts)))
    baseline=json.loads((ROOT/p['reference_results']).read_text())
    records=[]
    for j in plan['references']+plan['jobs']:
        try:
            if j['reused']:
                saved=next(r for r in baseline if r['index']==j['index'] and r['method']==j['method'])
                old=json.loads((Path(p['reference_root'])/'metrics'/f"{j['run_id']}_{j['method']}.json").read_text())
                assert old['classification']==saved['classification'] and old['success']==saved['success']
            else:
                old=json.loads((root/'metrics'/f"{j['key']}.json").read_text())
                assert old.get('execution_git_sha')==plan['git_sha'] or old['technical_validation']!='PASS'
            if old.get('launcher_exit_code')!=0 or old.get('technical_validation')!='PASS':
                raise RuntimeError(old.get('error','Execution/audit failed'))
            assert old['index']==j['index'] and old['method']==j['method'] and old['delay_s']==j['delay_s']
            for name,h in old['input_log_sha256'].items():assert sha256_file(Path(j['output'])/name)==h,'Run input changed: '+name
            r=dict(old)
            r['mechanisms']=mechanisms(Path(j['output']),bool(r['success']))
        except Exception as exc:
            r=dict(classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False,error=repr(exc),traceback=traceback.format_exc())
        r.update({k:v for k,v in j.items() if k not in ('argv','shell_command')})
        records.append(r)
    assert len(records)==80 and len({r['key'] for r in records})==80
    return records,plan


def group(records,delay,method):
    rs=[r for r in records if r['delay_s']==delay and r['method']==method]
    g=summarize(rs,'inf',method);g['delay_ms']=round(delay*1000)
    g['success_wilson95_valid']=wilson(g['success'],g['valid'])
    g['valid_success_rate']=g['success']/g['valid'] if g['valid'] else None
    return g


def decide(records):
    gs={(d,m):group(records,d,m) for d in (0.,.25,.5,.75) for m in ('CURV','GRAPH')}
    delta={str(round(d*1000)):gs[d,'GRAPH']['success']-gs[d,'CURV']['success'] for d in (0.,.25,.5,.75)}
    g,c=gs[0.,'GRAPH'],gs[0.,'CURV'];gm,cm=g['goal_time_median_s'],c['goal_time_median_s']
    d0=(g['success']>=c['success']-1 and gm<=1.1*cm) if gm is not None and cm is not None else None
    trend=delta['750']>=delta['500']-1>=delta['250']-2 and delta['750']>=delta['0']+2
    select=group(records,.75,'SELECT');beats=gs[.75,'GRAPH']['success']>=select['success']+2
    fisher={}
    for d in (0.,.25,.5,.75):
        a,b=gs[d,'GRAPH'],gs[d,'CURV']
        fisher[str(round(d*1000))]=float(fisher_exact([[a['success'],a['valid']-a['success']],
            [b['success'],b['valid']-b['success']]]).pvalue) if a['valid'] and b['valid'] else None
    g=gs[.75,'GRAPH'];fisher['750_GRAPH_SELECT']=float(fisher_exact([[g['success'],g['valid']-g['success']],
        [select['success'],select['valid']-select['success']]]).pvalue) if g['valid'] and select['valid'] else None
    return dict(D0_NO_HARM=d0,TREND_SUPPORTED=trend,BEATS_SELECT=beats,delta_success_counts=delta,
        fisher_two_sided_descriptive=fisher,technical_failures=sum(r.get('technical_validation')!='PASS' for r in records),
        complete_technical_evidence=all(r.get('technical_validation')=='PASS' for r in records),
        reference_success_counts={m:gs[.75,m]['success'] for m in ('CURV','GRAPH')})


def flat_mechanism(r,window):
    d=r['mechanisms']['full' if window=='full' else 'failure_last3s']
    if d is None:return None
    row={k:r[k] for k in ('key','index','method','delay_s','success','classification','reused')}
    row.update(window=window)
    for k,v in d.items():
        if isinstance(v,dict):
            for field in ('median','p95'):row[k+'_'+field]=v.get(field)
        else:row[k]=v
    return row


METRICS=('heading_abs_rad_median','heading_abs_rad_p95','cross_track_m_median','cross_track_m_p95',
         'abs_kappa_m_inv_median','abs_kappa_m_inv_p95','kappa_over2_fraction','max_abs_y_m',
         'time_abs_y_over1_s','minimum_wall_footprint_clearance_lower_m')


def aggregate_mechanisms(flat):
    groups=[]
    for delay in (None,0.,.25,.5,.75):
        for method in ('CURV','RIGID-ENTRY','SELECT','GRAPH'):
            for success in (True,False):
                for window in ('full','last3s'):
                    rs=[r for r in flat if r['method']==method and r['success']==success and r['window']==window
                        and (delay is None or r['delay_s']==delay)]
                    if not rs:continue
                    g=dict(delay_ms='pooled' if delay is None else round(delay*1000),method=method,
                        outcome='SUCCESS' if success else 'FAILURE',window=window,runs=len(rs),
                        invalid_heading_events=sum(r['heading_invalid_count'] for r in rs))
                    for k in METRICS:
                        values=[r[k] for r in rs if r.get(k) is not None]
                        g[k+'_run_mean']=float(np.mean(values)) if values else None
                        g[k+'_valid_runs']=len(values)
                    groups.append(g)
    return groups


def plot(out,conditions,flat):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,4.5))
    for method,color in (('CURV','#777777'),('GRAPH','#176ca4')):
        gs=[g for g in conditions if g['method']==method and g['valid_success_rate'] is not None]
        x=np.array([g['delay_ms'] for g in gs]);y=np.array([g['valid_success_rate'] for g in gs])
        low=np.array([g['success_wilson95_valid'][0] for g in gs]);hi=np.array([g['success_wilson95_valid'][1] for g in gs])
        if len(gs):ax.errorbar(x,y,yerr=np.maximum(0,np.stack([y-low,hi-y])),marker='o',capsize=4,label=method,color=color)
    ax.set(xlabel='Post-packet delivery delay (ms)',ylabel='Success fraction (valid runs)',ylim=(-.05,1.05),xticks=[0,250,500,750],
           title='Phase6 S0, N=8 attempts per condition; Wilson 95% descriptive')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(out/'delay_success.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,key,label in zip(axes,('cross_track_m_median','heading_abs_rad_median'),('Switch cross-track (m)','Switch heading error (rad)')):
        data=[];labels=[]
        for m in ('CURV','RIGID-ENTRY','SELECT','GRAPH'):
            for outcome in (True,False):
                vals=[r[key] for r in flat if r['window']=='full' and r['method']==m and r['success']==outcome and r.get(key) is not None]
                if vals:data.append(vals);labels.append(m+'\n'+('success' if outcome else 'failure'))
        if data:ax.boxplot(data,labels=labels,showfliers=True)
        else:ax.text(.5,.5,'No valid run metrics',ha='center',transform=ax.transAxes)
        ax.set_ylabel(label);ax.set_title('Run medians; delays pooled, each run once');ax.tick_params(axis='x',labelrotation=35);ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(out/'mechanisms.png',dpi=160);plt.close(fig)


def generate(root,out,doc):
    assert not out.exists() and not doc.exists(),'Existing report preserved'
    records,plan=load(root)
    conditions=[group(records,d,m) for d in (0.,.25,.5,.75) for m in ('CURV','GRAPH')]
    compare=[group(records,.75,m) for m in ('CURV','RIGID-ENTRY','SELECT','GRAPH')]
    flat=[]
    for r in records:
        if r.get('technical_validation')!='PASS':continue
        for window in ('full','last3s'):
            f=flat_mechanism(r,window)
            if f is not None:flat.append(f)
    mechanism=aggregate_mechanisms(flat);decision=decide(records)
    out.mkdir(parents=True,exist_ok=False)
    plot(out,conditions,flat)
    small=[{k:v for k,v in r.items() if k not in ('request_seeds','input_log_sha256','handoffs','mechanisms','traceback')} for r in records]
    write_json(out/'summary.json',dict(execution_git_sha=plan['git_sha'],protocol=protocol(),conditions=conditions,
        d750_comparison=compare,decisions=decision,mechanisms=mechanism))
    write_json(out/'runs.json',small)
    write_json(out/'input_hashes.json',{r['key']:dict(execution_git_sha=r.get('execution_git_sha'),
        audit=r.get('input_log_sha256',{}),mechanisms=r.get('mechanisms',{}).get('input_sha256',{})) for r in records})
    write_csv(out/'conditions.csv',conditions);write_csv(out/'d750_comparison.csv',compare)
    write_csv(out/'mechanisms_runs.csv',flat);write_csv(out/'mechanisms_groups.csv',mechanism)
    failures=[r for r in flat if r['window']=='last3s']
    if failures:write_csv(out/'failure_precursors.csv',failures)
    else:(out/'failure_precursors.csv').write_text('key,window\n')
    f=lambda x:'N/A' if x is None else f'{x:.4f}'
    text=['# Phase6 Static Completion','',f"Execution Git SHA: `{plan['git_sha']}`.",
        'Oracle geometry; SE(2) kinematic Isaac Sim. N=8 exploratory attempts per condition. 56 new attempts; 24 Phase5 references used once. D750 CURV/GRAPH/RIGID are reused, never rerun.', '']
    def table(title,gs):
        text.extend([title,'','|D ms|Method|Success/attempts|Collision|Corridor|Timeout|Technical|Goal median s|Mean speed m/s|Min clearance m|Wilson 95% (valid)|',
            '|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|'])
        for g in gs:
            ci=g['success_wilson95_valid'];text.append(f"|{g['delay_ms']}|{g['method']}|{g['success']}/{g['attempts']}|{g['collision']}|{g['corridor']}|{g['timeout']}|{g['technical_failure']}|{f(g['goal_time_median_s'])}|{f(g['mean_speed_m_s'])}|{f(g['minimum_clearance_m'])}|{f(ci[0])}–{f(ci[1])}|")
        text.append('')
    table('Table 1 — delay sweep',conditions);table('Table 2 — D750 alternatives',compare)
    text+=['Table 3 — equally weighted run summaries, success/failure split','',
        '|D ms|Method|Outcome|Window|Runs|Heading median/p95 rad|Cross-track median/p95 m|Curvature median/p95 /m|κ>2 fraction|max abs(y) m|Time abs(y)>1 s|Min wall clearance m|',
        '|---|---|---|---|---:|---|---|---|---:|---:|---:|---:|']
    for g in mechanism:
        if g['delay_ms']!='pooled':continue
        text.append(f"|pooled|{g['method']}|{g['outcome']}|{g['window']}|{g['runs']}|{f(g['heading_abs_rad_median_run_mean'])}/{f(g['heading_abs_rad_p95_run_mean'])}|{f(g['cross_track_m_median_run_mean'])}/{f(g['cross_track_m_p95_run_mean'])}|{f(g['abs_kappa_m_inv_median_run_mean'])}/{f(g['abs_kappa_m_inv_p95_run_mean'])}|{f(g['kappa_over2_fraction_run_mean'])}|{f(g['max_abs_y_m_run_mean'])}|{f(g['time_abs_y_over1_s_run_mean'])}|{f(g['minimum_wall_footprint_clearance_lower_m_run_mean'])}|")
    text+=['','Per-run and delay-stratified metrics, valid denominators and last3s failure precursors are in the companion CSV files. Table3 values are means of run statistics; distributions are not pooled across controller ticks. RIGID/SELECT have D750 only.',
        '', '|Independent preregistered criterion|Result|','|---|---|']
    for key in ('D0_NO_HARM','TREND_SUPPORTED','BEATS_SELECT'):
        text.append(f"|{key}|{'INSUFFICIENT_EVIDENCE' if decision[key] is None else 'PASS' if decision[key] else 'FAIL'}|")
    text += ['',f"Δ(D), GRAPH−CURV success counts: `{decision['delta_success_counts']}`.",
        'TREND uses the literal preregistered chained inequality Δ750 ≥ Δ500−1 ≥ Δ250−2 and Δ750 ≥ Δ0+2. No combined verdict.',
        f"Technical evidence complete: `{decision['complete_technical_evidence']}`; technical failures: {decision['technical_failures']}.",
        f"Fisher two-sided p, descriptive only: `{decision['fisher_two_sided_descriptive']}`.",
        'Goal-time medians use successful runs only; failed times are not replaced with90s. Collision/corridor can co-occur. A2cm margin violation is separate from SUCCESS. Technical failures are not collisions or timeouts; Wilson and Fisher exclude them.',
        'Switches include RAW/SELECT/RIGID applications and accepted GRAPH replacements. Heading uses the actual projected segment tangent only when length≥20mm. Invalid headings and empty last3s event windows remain missing. Wall distance is footprint swept lower bound; |y|>1 duration uses72Hz interval end poses.',
        'Mechanism associations are descriptive, not causal. Same seed offset does not give identical closed-loop RGB; Phase5 references were recorded earlier. No navigation is generated by this report.',
        '', '![Delay success](../research/results/phase6/delay_success.png)', '', '![Mechanisms](../research/results/phase6/mechanisms.png)']
    failed=[r for r in records if r.get('technical_validation')!='PASS']
    if failed:
        text+=['','|Technical failure|Reason|','|---|---|']
        for r in failed:text.append(f"|{r['key']}|{r.get('error')}|")
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(text)+'\n')
    return decision


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'research/results/phase6')
    p.add_argument('--document',type=Path,default=ROOT/'docs/PHASE6_STATIC_COMPLETION.md')
    a=p.parse_args();print(json.dumps(generate(a.run_root.resolve(),a.output,a.document)))


if __name__=='__main__':main()
