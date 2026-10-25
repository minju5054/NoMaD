"""Automatic Phase12 results, paired statistics and two figures. Logs only."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.stats import fisher_exact
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_phase4.report import write_csv
from nomad_phase8.report import summarize,mechanism_table,markdown_table
from nomad_phase0.chunk_report import trace
from .config import protocol,METHODS
from .batch import completion


def valid(r):return r.get('technical_validation')=='PASS'
def wilson(k,n):
    if not n:return None
    z=1.959963984540054;p=k/n;den=1+z*z/n;c=(p+z*z/(2*n))/den;w=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(c-w),float(c+w)]


def load(root):
    p=protocol();plan=json.loads((root/'plan.json').read_text());state=completion(root)
    assert state['state']=='COMPLETE' and state['finished_slots']==70
    assert plan['protocol']==p
    for name,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(name))==h,name
    records=[];hashes={}
    for j in plan['jobs']:
        r=json.loads((root/'metrics'/f"{j['key']}.json").read_text());assert all(r[k]==j[k] for k in ('key','method','index','delay_s','output'))
        if valid(r):
            assert r['execution_git_sha']==plan['git_sha']
            for name,h in r['input_log_sha256'].items():assert sha256_file(Path(r['output'])/name)==h,name
        hashes[r['key']]=r.get('input_log_sha256',{});records.append(r)
    assert len(records)==len({r['key'] for r in records})==70
    return records,plan,state,hashes


def tables(records):
    table=[]
    for method in METHODS:
        rs=[r for r in records if r['method']==method];attempted=[r for r in rs if r['classification']!='SKIPPED_TECHNICAL_GATE']
        g=summarize(attempted,method,range(25,35));g['role']='privileged reference' if method=='SELECT+GRAPH' else 'main (oracle-free)';g['skipped']=len(rs)-len(attempted);g['success_wilson95']=wilson(g['success'],g['valid'])
        vs=[r for r in rs if valid(r)]
        def mean(key):
            vals=[r[key] for r in vs if r.get(key) is not None];return float(np.mean(vals)) if vals else None
        g['curv_slow_time_fraction']=mean('curv_slow_time_fraction');g['endpoint_clamp_fraction']=mean('endpoint_clamp_fraction');g['ensemble_mean_chunks']=mean('ensemble_mean_chunks')
        table.append(g)
    return table


def decide(records):
    gs={g['method']:g for g in tables(records)};a=gs['FRESHEST+GRAPH-GF'];out={};pairs=[]
    for m in METHODS[:5]:
        b=gs[m];eligible=a['valid']>=9 and b['valid']>=9
        out['BEATS_'+m]='INCONCLUSIVE' if not eligible else 'PASS' if a['success']>=b['success']+3 else 'FAIL'
        ar={r['index']:r for r in records if r['method']=='FRESHEST+GRAPH-GF' and valid(r) and r['success']}
        br={r['index']:r for r in records if r['method']==m and valid(r) and r['success']}
        ids=sorted(set(ar)&set(br));diff=np.array([ar[i]['mean_speed_m_s']-br[i]['mean_speed_m_s'] for i in ids]);ci=None
        if len(diff):
            rng=np.random.default_rng(20261026);samples=diff[rng.integers(0,len(diff),(20000,len(diff)))].mean(axis=1);ci=np.quantile(samples,[.025,.975]).tolist()
        decision='INCONCLUSIVE' if not eligible or len(diff)<5 else 'FASTER' if ci[0]>0 else 'SLOWER' if ci[1]<0 else 'NOT_SHOWN'
        out['SPEED_VS_'+m]=decision
        fisher=float(fisher_exact([[a['success'],a['valid']-a['success']],[b['success'],b['valid']-b['success']]]).pvalue) if a['valid'] and b['valid'] else None
        pairs.append(dict(comparator=m,paired_indices=ids,n=len(ids),mean_speed_difference_m_s=float(diff.mean()) if len(diff) else None,
            bootstrap95=ci,paired_differences_m_s=diff.tolist(),speed_verdict=decision,fisher_exact_p_reference_only=fisher))
    return out,pairs



def oracle_gap(records):
    a={r['index']:r for r in records if r['method']=='SELECT+GRAPH' and valid(r)}
    b={r['index']:r for r in records if r['method']=='FRESHEST+GRAPH-GF' and valid(r)}
    ids=sorted(i for i in set(a)&set(b) if a[i]['success'] and b[i]['success'])
    diff=[a[i]['mean_speed_m_s']-b[i]['mean_speed_m_s'] for i in ids]
    return dict(role='descriptive only',privileged_valid=len(a),oracle_free_valid=len(b),
        success_count_difference=sum(r['success'] for r in a.values())-sum(r['success'] for r in b.values()),
        both_success_indices=ids,paired_n=len(ids),paired_mean_speed_difference_m_s=float(np.mean(diff)) if diff else None)


def figures(records,table,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(12,4));x=np.arange(len(table));ax.bar(x,[g['success'] for g in table],color=['#d99132' if g['method']=='SELECT+GRAPH' else '#4378a8' for g in table])
    for i,g in enumerate(table):
        if g['success_wilson95']:
            lo,hi=np.array(g['success_wilson95'])*g['valid'];ax.errorbar(i,g['success'],yerr=[[max(0.,g['success']-lo)],[max(0.,hi-g['success'])]],fmt='none',ecolor='black',capsize=4)
    ax.set(xticks=x,xticklabels=[g['method']+(' (privileged)' if g['method']=='SELECT+GRAPH' else '') for g in table],ylim=(0,10.6),ylabel='Success count (Wilson95 scaled by valid N)',title='Planned10/method; technical failures and skipped slots excluded from CI')
    ax.tick_params(axis='x',labelrotation=16);fig.tight_layout();fig.savefig(out/'success.png',dpi=160);plt.close(fig)
    lookup={(r['method'],r['index']):r for r in records};indices=[i for i in range(25,35) if valid(lookup['CURV',i]) and not lookup['CURV',i]['success'] and valid(lookup['FRESHEST+GRAPH-GF',i]) and lookup['FRESHEST+GRAPH-GF',i]['success']]
    chosen=min(indices) if indices else None;fig,ax=plt.subplots(figsize=(10,4))
    if chosen is None:ax.text(.05,.5,'No valid CURV-failure / FRESHEST+GRAPH-GF-success pair',transform=ax.transAxes)
    else:
        scene=json.loads((ROOT/protocol()['scenario']).read_text())
        for m in METHODS:
            r=lookup[m,chosen]
            if not valid(r):continue
            _,pose=trace(Path(r['output']));line=ax.plot(pose[:,0],pose[:,1],label=f'{m}: {r["classification"]}')[0];ax.plot(*pose[-1,:2],'x',color=line.get_color())
        for box in scene['obstacles']:
            x,y=box['center_xy_m'];sx,sy=box['size_xyz_m'][:2];ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,color='gray',alpha=.4))
        for y in (-scene['corridor']['half_width'],scene['corridor']['half_width']):ax.axhline(y,color='k',lw=.7)
        ax.set(title=f'D750 index {chosen}; actual recorded paths',xlabel='World X (m)',ylabel='World Y (m)');ax.legend(fontsize=7);ax.set_aspect('equal')
    fig.tight_layout();fig.savefig(out/'paths.png',dpi=160);plt.close(fig)
    return chosen


def generate(root,out=None,doc=None):
    p=protocol();out=Path(out or ROOT/p['results']);doc=Path(doc or ROOT/p['report']);assert not out.exists() and not doc.exists(),'Preserve existing reports'
    records,plan,state,hashes=load(root);table=tables(records);decision,pairs=decide(records);gap=oracle_gap(records);mechanisms=mechanism_table(records)
    paired=[]
    for i in range(25,35):paired.append(dict(index=i,**{m:next(r['classification'] for r in records if r['index']==i and r['method']==m) for m in METHODS}))
    method_stats=[{k:g[k] for k in ('method','valid','selection_switches','selection_replacements','selection_replacement_ratio','ensemble_mean_chunks','inference_median_ms','graph_calls','graph_accepted','graph_nonconverged','graph_dispositions','graph_solve_pooled_s','corrected_run_fraction_mean','corrected_distance_fraction_mean')} for g in table]
    flat=[{k:v for k,v in r.items() if k not in ('input_log_sha256','mechanisms','traceback')} for r in records]
    out.mkdir(parents=True,exist_ok=False);chosen=figures(records,table,out)
    for name,data in [('methods',table),('paired',paired),('mechanisms',mechanisms),('method_stats',method_stats),('paired_speed',pairs)]:write_csv(out/f'{name}.csv',data)
    write_json(out/'runs.json',flat);write_json(out/'input_hashes.json',hashes)
    write_json(out/'summary.json',dict(execution_git_sha=plan['git_sha'],state=state,protocol=p,tables=table,decisions=decision,paired_speed=pairs,oracle_gap=gap,overlay_index=chosen))
    lines=['# Phase12 — oracle-free chunk transition baselines','', '## Fairness principles','',*[f'{i}. {t}' for i,t in enumerate(p['fairness'],1)],'',f"Execution commit: `{plan['git_sha']}`; {state['state']}; attempted {state['attempted']}, skipped {state['skipped']} /70 slots.",p['scope'],'',
        'All methods: S0 D750, PP lookahead0.25m + unchanged CURV speed, vmax0.3, 4/9/72Hz, 1s timeout, 90s limit. Seeds25–34. No retries. Success is goal entry without geometric overlap or corridor intrusion. Conservative contact stops remain separate; 2cm margin violations do not automatically count as collisions.','',
        'HERMITE uses B heading and original FRESH tangent at the0.30m-ahead join; analytic cubic C1 continuity, sampled every2cm approximately in arclength. TEMPORAL-ENSEMBLE is **ACT temporal ensembling (spatial adaptation)**, not native action-time ensembling. BID is **BID backward-coherence only**, without forward contrast. RTC-hard is **RTC hard-masking ablation (DDPM adaptation)**. FRESHEST+GRAPH-GF selects the longest remaining path without safety filtering and retains v4 geometry-free factors/constraints. SDF, corridor constraints and exact certificate are disabled; obstacle-side residuals have no labels. SELECT+GRAPH retains original Phase8 selection and Graph v4 as a **privileged reference**, excluded from main decisions.','',
        '## Table1 — results','']
    lines+=markdown_table(table,['method','role','planned','attempted','valid','success','collision','corridor','timeout','technical','skipped','conservative_contact','goal_time_median_s','mean_speed_m_s','clearance_min_m','success_wilson95','curv_slow_time_fraction','endpoint_clamp_fraction'])
    lines+=['','## Table2 — paired index results','']+markdown_table(paired,['index',*METHODS])
    lines+=['','## Table3 — mechanisms (run means, success/failure separate)','']+markdown_table(mechanisms,list(mechanisms[0]) if mechanisms else ['method','outcome'])
    lines+=['','Temporal ensemble has no unique applied polyline. Its switch cross-track and heading errors use weighted per-component Phase6 projections; heading is valid only when every component has a valid20mm tangent. This adaptation is not a fictitious averaged path. Other methods use the unchanged Phase6 metrics.','',
        '## Table4 — method statistics','']+markdown_table(method_stats,list(method_stats[0]))
    lines+=['','BID/FRESHEST sample replacement rate uses switched FRESH. Mean ensemble chunk count uses valid control ticks with live paths; endpoint clamp is any live component clamp. RTC inference is median of run medians. Original methods, weights, normalization, timing and raw data are preserved.','',
        '## Independent preregistered decisions','']+markdown_table([dict(name=k,verdict=v) for k,v in decision.items()],['name','verdict'])
    lines+=['','## Paired speed differences (FRESHEST+GRAPH-GF minus comparator)','']+markdown_table(pairs,['comparator','n','mean_speed_difference_m_s','bootstrap95','speed_verdict','fisher_exact_p_reference_only'])
    lines+=['','Each method requires≥9 valid runs; speed also requires≥5 both-success pairs. Paired bootstrap:20,000 replicates, seed20261026, run-index resampling. Missing goal times are not imputed. Fisher/Wilson are reference only. Same seed does not imply identical closed-loop RGB or predictions.','',
        '![Success](../research/results/phase12/success.png)','', '![Selected paired routes](../research/results/phase12/paths.png)','']
    lines+=['','## ORACLE_GAP — report only','', 'SELECT+GRAPH (privileged) minus FRESHEST+GRAPH-GF; not a main verdict.','']+markdown_table([gap],list(gap))
    failures=[dict(key=r['key'],classification=r['classification'],error=r.get('error')) for r in records if not valid(r)]
    if failures:lines+=['## Technical failures and gated skips','']+markdown_table(failures,['key','classification','error'])
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(lines)+'\n');return decision


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',required=True,type=Path);a=ap.parse_args();print(json.dumps(generate(a.run_root.resolve())))
if __name__=='__main__':main()
