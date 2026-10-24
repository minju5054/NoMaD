"""Automatic frozen Phase8/9 reports; invalid denominators never yield PASS/FAIL."""
import argparse
import json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,write_json,sha256_file
from nomad_isaac.async_report import rows,stats
from nomad_phase4.report import write_csv
from nomad_phase6.metrics import mechanisms
from .config import protocol
from .batch import completion

def valid(r):return r.get('technical_validation')=='PASS'
def clearance(r):
    if 'minimum_obstacle_clearance_m' in r:return r['minimum_obstacle_clearance_m']
    values=[v for k,v in r.items() if k.endswith('_minimum_clearance_m') and v is not None]
    return min(values) if values else None

def load(root,phase):
    state=completion(root);assert state['state'] in ('COMPLETE','PHASE9_ABORTED'),state
    plan=json.loads((root/'plan.json').read_text());assert plan['protocol']==protocol(phase)
    for name,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(name))==h,'Input changed: '+name
    records=[];hashes={}
    if phase==8:
        provenance=json.loads((ROOT/'research/results/phase7/input_hashes.json').read_text())
        for old in plan['references']:
            r=dict(old);run=Path(r['output']);h=provenance[r['key']].get('audit')
            if valid(r):
                assert h,'Missing audited provenance'
                for name,digest in h.items():assert sha256_file(run/name)==digest
                r['mechanisms']=mechanisms(run,r['success'])
                if r['method']=='SELECT':
                    selections=[e['phase6_selection'] for e in rows(run/'events.jsonl')]
                    r['selection']=dict(switches=len(selections),replacements=sum(e['selected_sample']!=0 for e in selections),all_unsafe=sum(e['all_unsafe'] for e in selections),sample_index_counts=dict(Counter(e['selected_sample'] for e in selections)))
            hashes[r['key']]=h;records.append(r)
    for job in plan['jobs'][:state['completed']]:
        r=json.loads((root/'metrics'/f"{job['key']}.json").read_text());assert all(r[k]==job[k] for k in ('key','method','index','delay_s','output'))
        if valid(r):
            assert r['execution_git_sha']==plan['git_sha']
            for name,h in r['input_log_sha256'].items():assert sha256_file(Path(r['output'])/name)==h
        hashes[r['key']]=r.get('input_log_sha256');records.append(r)
    assert len(records)==len({r['key'] for r in records})
    return records,plan,state,hashes

def summarize(records,method,indices,delay=.75):
    rs=[r for r in records if r['method']==method and r['index'] in indices and r['delay_s']==delay];v=[r for r in rs if valid(r)];success=[r for r in v if r['success']]
    def median(values):return float(np.median(values)) if values else None
    gap=[clearance(r) for r in v if clearance(r) is not None]
    prefix=[r['rtc_prefix_error_m']['median'] for r in v if r.get('rtc_prefix_error_m',{}).get('median') is not None]
    selection=[r['selection'] for r in v if r.get('selection')];counts=Counter()
    for s in selection:counts.update({str(k):n for k,n in s.get('sample_index_counts',{}).items()})
    graph=[r['graph'] for r in v if r.get('graph')];dispositions=Counter()
    for g in graph:dispositions.update(g['dispositions'])
    calls=sum(g['calls'] for g in graph)
    return dict(method=method,delay_ms=round(delay*1000),planned=len(indices),attempted=len(rs),not_attempted=len(indices)-len(rs),valid=len(v),success=len(success),collision=sum(bool(r.get('geometric_overlap')) for r in v),corridor=sum(bool(r.get('corridor_violation')) for r in v),timeout=sum(r['classification']=='STUCK' for r in v),technical=len(rs)-len(v),placement_invalid=sum(r['classification']=='PLACEMENT_INVALID' for r in v),conservative_contact=sum(r['classification']=='CONSERVATIVE_CONTACT_STOP' for r in v),goal_time_median_s=median([r['goal_time_s'] for r in success]),mean_speed_m_s=float(np.mean([r['mean_speed_m_s'] for r in v])) if v else None,clearance_median_m=median(gap),clearance_p10_m=float(np.percentile(gap,10)) if gap else None,clearance_min_m=min(gap) if gap else None,inference_median_ms=median([r['inference_ms']['median'] for r in v if r.get('inference_ms',{}).get('median') is not None]),rtc_prefix_median_m=median(prefix),selection_switches=sum(s['switches'] for s in selection),selection_replacements=sum(s['replacements'] for s in selection),selection_replacement_ratio=sum(s['replacements'] for s in selection)/sum(s['switches'] for s in selection) if sum(s['switches'] for s in selection) else None,all_unsafe=sum(s['all_unsafe'] for s in selection),selected_index_counts=dict(counts),graph_calls=calls,graph_accepted=dispositions['ACCEPTED'],graph_nonconverged=sum(g.get('independent_nonconverged',g['dispositions'].get('NONCONVERGED',0)) for g in graph),graph_dispositions=dict(dispositions),graph_acceptance_rate=dispositions['ACCEPTED']/calls if calls else None,graph_solve_pooled_s=stats([x for g in graph for x in g.get('solver_samples_s',[])]),corrected_distance_fraction_mean=float(np.mean([g['corrected_distance_fraction'] for g in graph if g.get('corrected_distance_fraction') is not None])) if any(g.get('corrected_distance_fraction') is not None for g in graph) else None,graph_solve_run_median_s=median([g['solver_time_s']['median'] for g in graph if g['solver_time_s'].get('median') is not None]),corrected_run_fraction_mean=float(np.mean([g['corrected_valid_tick_fraction'] for g in graph if g.get('corrected_valid_tick_fraction') is not None])) if any(g.get('corrected_valid_tick_fraction') is not None for g in graph) else None,dynamic_passage_counts=dict(Counter(r.get('dynamic_passage_side') or 'NOT_PASSED' for r in v)))

def verdict(groups,test):
    return 'INCONCLUSIVE' if any(g['valid']<.875*g['planned'] for g in groups) else ('PASS' if test else 'FAIL')

def paired_margin(records,a,b):
    values={m:{r['index']:clearance(r) for r in records if r['method']==m and r['delay_s']==.75 and 9<=r['index']<=24 and valid(r) and clearance(r) is not None} for m in (a,b)}
    ids=sorted(set(values[a])&set(values[b]));dif=np.array([values[a][i]-values[b][i] for i in ids]);ci=None
    if len(dif):
        rng=np.random.default_rng(20261025);samples=dif[rng.integers(0,len(dif),(20000,len(dif)))].mean(axis=1);ci=np.quantile(samples,[.025,.975]).tolist()
    usable=min(len(values[a]),len(values[b]))>=14 and len(ids)>=14
    return dict(pair=f'{a} minus {b}',indices=ids,paired_differences_m=dif.tolist(),mean_difference_m=float(dif.mean()) if len(dif) else None,bootstrap95_mean=ci,replicates=20000,seed=20261025,verdict='INCONCLUSIVE' if not usable else 'PASS' if ci[0]>0 else 'FAIL')

def decide(records,phase):
    if phase==8:
        g={m:summarize(records,m,range(9,25)) for m in ('CURV','SELECT','GRAPH','SELECT+GRAPH')};a,b,c=g['GRAPH'],g['SELECT'],g['SELECT+GRAPH']
        supported=verdict([a,b,c],c['success']>=max(a['success'],b['success'])+2)
        base={m:summarize(records,m,range(9,17)) for m in ('GRAPH','RTC-soft','RTC-hard')}
        return dict(BEATS_SELECT=verdict([a,b],a['success']>=b['success']+3),COMBO_SUPPORTED=supported,COMBO_NO_WORSE='NOT_EVALUATED_SUPPORTED' if supported=='PASS' else verdict([a,b,c],c['success']>=max(a['success'],b['success'])),MARGIN_ADVANTAGE=[paired_margin(records,m,'SELECT') for m in ('GRAPH','SELECT+GRAPH')],BEATS_RTC_SOFT=verdict([base['GRAPH'],base['RTC-soft']],base['GRAPH']['success']>=base['RTC-soft']['success']+2),BEATS_RTC_HARD=verdict([base['GRAPH'],base['RTC-hard']],base['GRAPH']['success']>=base['RTC-hard']['success']+2))
    g={m:summarize(records,m,range(1,9)) for m in ('CURV','SELECT','INTENT-SPLICE','GRAPH-v6')};a,b,c,d=[g[m] for m in ('CURV','SELECT','INTENT-SPLICE','GRAPH-v6')]
    return dict(INTENT_NEEDED=verdict([a,c,d],max(c['success'],d['success'])>=a['success']+3),V6_BEATS_SPLICE=verdict([c,d],d['success']>=c['success']+2),V6_BEATS_SELECT=verdict([b,d],d['success']>=b['success']+2))

def mechanism_table(records):
    table=[]
    for m in sorted(set(r['method'] for r in records)):
        for outcome in (True,False):
            rs=[r for r in records if r['method']==m and valid(r) and r['success']==outcome and r.get('mechanisms')]
            if not rs:continue
            row=dict(method=m,outcome='SUCCESS' if outcome else 'NON_SUCCESS',runs=len(rs))
            for key in ('heading_abs_rad','cross_track_m'):
                for stat in ('median','p95'):
                    values=[r['mechanisms']['full'][key][stat] for r in rs if r['mechanisms']['full'][key].get(stat) is not None]
                    row[key+'_'+stat+'_run_mean']=float(np.mean(values)) if values else None
            for key in ('time_abs_y_over1_s','minimum_wall_footprint_clearance_lower_m'):
                values=[r['mechanisms']['full'][key] for r in rs if r['mechanisms']['full'].get(key) is not None];row[key]=float(np.mean(values)) if values else None
            table.append(row)
    return table

def figures(records,tables,out,phase):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if phase==8:
        gs=tables['n16'];fig,ax=plt.subplots(figsize=(8,4));ax.bar([g['method'] for g in gs],[g['success'] for g in gs]);ax.set(ylabel='Success count /16 planned',ylim=(0,17),title='Phase8: technical failures retained');fig.tight_layout();fig.savefig(out/'success.png',dpi=150);plt.close(fig)
        data=[];labels=[]
        for g in gs:
            v=[clearance(r) for r in records if r['method']==g['method'] and valid(r) and clearance(r) is not None]
            if v:data.append(v);labels.append(g['method'])
        fig,ax=plt.subplots(figsize=(8,4))
        if data:ax.boxplot(data,labels=labels,showmeans=True)
        ax.axhline(.02,color='red',linestyle='--');ax.set(ylabel='Run minimum obstacle clearance (m)',title='All valid runs, including failures');fig.tight_layout();fig.savefig(out/'clearance.png',dpi=150);plt.close(fig)
    else:
        from nomad_phase0.chunk_report import trace
        from matplotlib.patches import Rectangle
        for i in (1,2):
            fig,ax=plt.subplots(figsize=(10,3.5));found=False
            for r in records:
                if r['index']!=i or r['delay_s']!=.75:continue
                path=Path(r['output'])/'agent_trajectory.csv'
                if not path.exists():continue
                try:_,poses=trace(Path(r['output']))
                except (ValueError,KeyError,IndexError):continue
                found=True;line=ax.plot(poses[:,0],poses[:,1],label=r['method'])[0]
                spawn=r.get('spawn')
                if spawn:
                    x,y=spawn['obstacle']['center_xy_m'];ax.add_patch(Rectangle((x-.175,y-.175),.35,.35,fill=False,edgecolor=line.get_color()))
            ax.axhline(1.5,color='k');ax.axhline(-1.5,color='k');ax.set(xlim=(-.2,8.4),ylim=(-1.6,1.6),xlabel='World X (m)',ylabel='World Y (m)',title=f'D750 index{i}, s={"+1" if i%2 else "−1"}; boxes colored per realized run')
            if found:ax.legend(fontsize=8)
            else:ax.text(3,0,'NOT RUN — technical gate aborted')
            ax.set_aspect('equal');fig.tight_layout();fig.savefig(out/f'paths_index{i}.png',dpi=150);plt.close(fig)

def markdown_table(data,columns):
    def f(x):
        if x is None:return 'N/A'
        if isinstance(x,float):return f'{x:.4f}'
        return str(x)
    return ['|'+'|'.join(columns)+'|','|'+'|'.join('---' for _ in columns)+'|']+['|'+'|'.join(f(r.get(k)) for k in columns)+'|' for r in data]

def generate(root,phase):
    p=protocol(phase);out=ROOT/p['results'];doc=ROOT/p['report'];assert not out.exists() and not doc.exists(),'Preserve previous reports'
    records,plan,state,hashes=load(root,phase);decision=decide(records,phase)
    if phase==8:
        tables=dict(n16=[summarize(records,m,range(9,25)) for m in ('CURV','SELECT','GRAPH','SELECT+GRAPH')],n8=[summarize(records,m,range(9,17)) for m in ('CURV','RIGID-ENTRY','SELECT','GRAPH','SELECT+GRAPH','RTC-soft','RTC-hard')])
        tables['selection']=[g for group in tables.values() for g in group if g['method'] in ('SELECT','SELECT+GRAPH')]
    else:
        tables=dict(method_delay=[summarize(records,m,range(1,9) if d else range(1,5),d) for d in (.75,0.) for m in (p['methods'] if d else ('CURV','GRAPH-v6'))],sides=[dict(side='+1' if odd else '-1',**summarize(records,m,[i for i in range(1,9) if i%2==odd])) for odd in (1,0) for m in p['methods']])
    tables['mechanisms']=mechanism_table(records)
    out.mkdir(parents=True,exist_ok=False);figures(records,tables,out,phase)
    write_json(out/'summary.json',dict(execution_git_sha=plan['git_sha'],scope=p['scope'],state=state,protocol=p,tables=tables,decisions=decision,rtc_hard_included=plan['rtc_hard']))
    write_json(out/'runs.json',[{k:v for k,v in r.items() if k not in ('input_log_sha256','mechanisms','traceback','request_seeds','handoffs')} for r in records]);write_json(out/'input_hashes.json',hashes)
    for key,table in tables.items():write_csv(out/f'{key}.csv',table)
    text=[f'# Phase{phase} Results','',f"Execution commit: `{plan['git_sha']}`; state: `{state['state']}`.",p['scope'],'All failures retained; no retries or parameter tuning. Success = goal + no geometric overlap + corridor containment; 2cm margin is reported separately. Conservative contact stop is not geometric collision. Missing goal times are not imputed.','']
    for key,data in tables.items():
        text += [f'## {key}','']
        columns=list(data[0]) if key=='mechanisms' and data else ['method','delay_ms','planned','valid','success','collision','corridor','timeout','technical','placement_invalid','goal_time_median_s','mean_speed_m_s','clearance_median_m','clearance_p10_m','clearance_min_m','inference_median_ms','rtc_prefix_median_m']
        if phase==9 and key!='mechanisms':columns+=['dynamic_passage_counts']
        if key=='sides':columns=['side']+columns
        if key=='selection':columns=['method','planned','selection_switches','selection_replacements','selection_replacement_ratio','all_unsafe','selected_index_counts']
        text+=markdown_table(data,columns)+['']
    if phase==9:
        text+=['## Graph statistics','']+markdown_table(tables['method_delay'],['method','delay_ms','graph_calls','graph_accepted','graph_nonconverged','graph_solve_pooled_s','corrected_run_fraction_mean','corrected_distance_fraction_mean','dynamic_passage_counts'])+['']
    text+=['## Preregistered decisions','','```json',json.dumps(decision,indent=2),'```','', 'Criteria involving <87.5% valid planned runs are INCONCLUSIVE. Paired margin bootstrap uses all valid pairs, the mean difference, 20,000 replicates and seed20261025; at least14 pairs required. Runtime latency/prefix values in tables are medians of run medians. Exact distributions and per-run mechanism values are in JSON/CSV.','']
    if phase==8:
        text+=['RTC-soft is **RTC-style (DDPM adaptation)**, unchanged Phase7 beta5/VJP. Prefix accuracy is diagnostic only. RTC-hard is **RTC hard-masking ablation (DDPM adaptation)**; exact prefix copying is an ablation, not the original flow-policy RTC. Both retain observation-time anchors.','']
        for n in ('success','clearance'):text += [f'![{n}](../research/results/phase8/{n}.png)','']
    else:
        text+=['Oracle geometry is available only after the next completed RGB capture following first visibility; physical collision evaluation includes the obstacle from spawn. Intent is a geometry heuristic. Each colored box is the realized run placement; paired seeds do not fix trajectories. Graph-v6 can reject inputs (including zero previous speed); fallback remains CURV.','']
        for i in (1,2):text+=[f'![D750 index{i}](../research/results/phase9/paths_index{i}.png)','']
    failures=[dict(key=r['key'],error=r.get('error')) for r in records if not valid(r)]
    if failures:text+=['## Technical failures','']+markdown_table(failures,['key','error'])
    doc.write_text('\n'.join(text)+'\n');return decision

def main(phase=8):
    p=argparse.ArgumentParser();p.add_argument('--run-root',required=True,type=Path);a=p.parse_args();print(json.dumps(generate(a.run_root.resolve(),phase)))
if __name__=='__main__':main()
