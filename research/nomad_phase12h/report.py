"""Append-only Phase12-H report; saved Phase12 is a different-commit reference."""
import argparse
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,write_json,sha256_file
from nomad_phase4.report import write_csv
from nomad_phase8.report import mechanism_table,markdown_table
from nomad_phase12.config import METHODS
from nomad_phase12.report import tables,valid
from .config import protocol,references
from .batch import completion


def load(root):
    p=protocol();state=completion(root);assert state['state'] in ('COMPLETE','TECHNICAL_GATE_ABORTED')
    plan=json.loads((root/'plan.json').read_text());assert plan['protocol']==p
    for name,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(name))==h,name
    records=references();hashes={}
    for j in plan['jobs']:
        path=root/'metrics'/f"{j['key']}.json";r=json.loads(path.read_text());assert all(r[k]==j[k] for k in ('key','method','index','output','seed_offset'))
        if valid(r):
            assert r['execution_git_sha']==plan['git_sha']
            for name,h in r['input_log_sha256'].items():assert sha256_file(Path(r['output'])/name)==h,name
        records.append(dict(r,reused=False,source_phase='12-H'));hashes[j['key']]=r.get('input_log_sha256',{})
    assert len(records)==len({(r['method'],r['index']) for r in records})==70
    return records,plan,state,hashes


def comparisons(records):
    out=[]
    for ref in ('FRESHEST+GRAPH-GF','SELECT+GRAPH'):
        a={r['index']:r for r in records if r['method']==ref and valid(r)}
        b={r['index']:r for r in records if r['method']=='HERMITE-SPLICE' and valid(r)}
        sa=sum(r['success'] for r in a.values());sb=sum(r['success'] for r in b.values());eligible=len(a)>=9 and len(b)>=9
        ids=sorted(i for i in set(a)&set(b) if a[i]['success'] and b[i]['success'])
        diff=np.array([a[i]['mean_speed_m_s']-b[i]['mean_speed_m_s'] for i in ids]);ci=None
        if len(diff):
            rng=np.random.default_rng(20261026);means=diff[rng.integers(0,len(diff),(20000,len(diff)))].mean(axis=1)
            ci=np.quantile(means,[.025,.975]).tolist()
        beats='INCONCLUSIVE' if not eligible else 'PASS' if sa>=sb+3 else 'FAIL'
        speed='INCONCLUSIVE' if not eligible or len(ids)<5 else 'FASTER' if ci[0]>0 else 'SLOWER' if ci[1]<0 else 'NOT_SHOWN'
        out.append(dict(reference=ref,role='main oracle-free' if ref=='FRESHEST+GRAPH-GF' else 'privileged reference only',
            reference_valid=len(a),hermite_valid=len(b),reference_success=sa,hermite_success=sb,BEATS_HERMITE_SPLICE=beats,
            SPEED_VS_HERMITE_SPLICE=speed,paired_indices=ids,paired_n=len(ids),mean_speed_difference_m_s=float(diff.mean()) if len(diff) else None,
            bootstrap95=ci,paired_differences_m_s=diff.tolist()))
    return out


def figure(table,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(12,4));x=np.arange(len(table))
    ax.bar(x,[g['success'] for g in table],color=['#d99132' if g['method']=='SELECT+GRAPH' else '#4378a8' for g in table])
    for i,g in enumerate(table):
        if g['success_wilson95']:
            lo,hi=np.array(g['success_wilson95'])*g['valid']
            ax.errorbar(i,g['success'],yerr=[[max(0.,g['success']-lo)],[max(0.,hi-g['success'])]],fmt='none',ecolor='black',capsize=4)
    ax.set(xticks=x,xticklabels=[g['method']+(' (privileged)' if g['method']=='SELECT+GRAPH' else '') for g in table],ylim=(0,10.6),ylabel='Success count /10 planned',title='HERMITE: Phase12-H; other methods: saved Phase12 (different commit/time)')
    ax.tick_params(axis='x',labelrotation=16);fig.tight_layout();fig.savefig(out/'success.png',dpi=160);plt.close(fig)


def generate(root,out=None,doc=None):
    p=protocol();out=Path(out or ROOT/p['results']);doc=Path(doc or ROOT/p['report'])
    assert not out.exists() and not doc.exists(),'Preserve reports; no overwrite'
    records,plan,state,hashes=load(root);table=tables(records);comp=comparisons(records);mechanisms=mechanism_table(records)
    for g in table:g['source_phase']='12-H (new)' if g['method']=='HERMITE-SPLICE' else '12 (reused)'
    h=[g for g in table if g['method']=='HERMITE-SPLICE']
    paired=[dict(index=i,**{m:next(r['classification'] for r in records if r['index']==i and r['method']==m) for m in METHODS}) for i in range(25,35)]
    decisions={k:comp[0][v] for k,v in [('BEATS_HERMITE-SPLICE','BEATS_HERMITE_SPLICE'),('SPEED_VS_HERMITE-SPLICE','SPEED_VS_HERMITE_SPLICE')]}
    out.mkdir(parents=True,exist_ok=False);figure(table,out)
    for name,data in [('hermite',h),('combined',table),('paired',paired),('mechanisms',mechanisms),('comparisons',comp)]:write_csv(out/f'{name}.csv',data)
    write_json(out/'summary.json',dict(execution_git_sha=plan['git_sha'],reference_execution_git_sha=p['reference_execution_sha'],state=state,protocol=p,tables=table,comparisons=comp,decisions=decisions))
    write_json(out/'runs.json',[{k:v for k,v in r.items() if k not in ('input_log_sha256','mechanisms','traceback')} for r in records])
    write_json(out/'input_hashes.json',dict(new_runs=hashes,reference_files=p['reference_sha256']))
    cols=['method','source_phase','planned','valid','success','collision','corridor','timeout','technical','skipped','conservative_contact','goal_time_median_s','mean_speed_m_s','clearance_min_m','curv_slow_time_fraction','endpoint_clamp_fraction']
    lines=['# Phase12-H — HERMITE-SPLICE follow-up','',f"HERMITE execution commit: `{plan['git_sha']}`; saved Phase12 reference commit: `{p['reference_execution_sha']}`.",
        '**These runs use a different commit and execution time from Phase12.** Same paired seed indices25–34 do not imply identical RGB, NoMaD predictions or asynchronous timing. Only the Hermite metadata bool serialization was fixed; the path definition and PP + CURV were not changed.',
        'Original Phase12 HERMITE technical failure and9 gated skips remain preserved; they are not counted as new Phase12-H attempts. The combined table uses the new HERMITE row and60 saved non-HERMITE rows.','',
        f"State: {state['state']}; attempts {state['attempted']}, skipped {state['skipped']}. No automatic retry or parameter changes.",
        'S0 D750, vmax0.3, alpha inf, PP lookahead0.25m, 4/9/72Hz, 1s waypoint timeout,90s navigation limit. Oracle geometry is evaluation-only for main methods; SELECT+GRAPH is a privileged reference.',
        'Success = goal entry without geometric overlap or corridor intrusion. Margin violations and conservative contact stops are reported separately; missing goal times are not imputed.','',
        '## Table1 — HERMITE','']+markdown_table(h,cols)
    lines+=['','## Table2 — combined seven methods','']+markdown_table(table,cols)
    lines+=['','## Table3 — paired outcomes','']+markdown_table(paired,['index',*METHODS])
    lines+=['','## Mechanisms — unchanged Phase6 definitions','']+markdown_table(mechanisms,list(mechanisms[0]) if mechanisms else ['method','outcome'])
    lines+=['','Switch heading/cross-track summarize run medians/p95; |y|>1 time and wall footprint clearance use the original Phase6 evaluator. No new paths are inferred for skipped runs.','',
        '## Preregistered comparisons','']+markdown_table(comp,['reference','role','reference_valid','hermite_valid','reference_success','hermite_success','BEATS_HERMITE_SPLICE','SPEED_VS_HERMITE_SPLICE','paired_n','mean_speed_difference_m_s','bootstrap95'])
    lines+=['','Each method needs≥9 valid runs; speed also requires≥5 both-success pairs. Paired bootstrap20,000 replicates, seed20261026, run-index resampling. SELECT+GRAPH comparisons are reference-only. Wilson bars are descriptive.','',
        '![Success counts](../research/results/phase12h/success.png)','']
    errors=[dict(key=r['key'],classification=r['classification'],error=r.get('error')) for r in records if r['method']=='HERMITE-SPLICE' and not valid(r)]
    if errors:lines+=['## Technical failures and gated skips','']+markdown_table(errors,['key','classification','error'])
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(lines)+'\n');return decisions


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',required=True,type=Path);a=ap.parse_args();print(json.dumps(generate(a.run_root.resolve())))
if __name__=='__main__':main()
