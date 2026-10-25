"""Automatic Phase10B report and pooled Phase9/10B C6 diagnostics; logs only."""
import argparse
import json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import stats
from nomad_phase0.chunk_report import trace
from nomad_phase4.report import write_csv
from nomad_phase8.batch import completion
from nomad_phase8.report import markdown_table
from .config import protocol
from .metrics import route_metrics,graph_calls


def valid(r):return r.get('technical_validation')=='PASS'


def load(root):
    p=protocol();plan=json.loads((root/'plan.json').read_text());state=completion(root)
    assert state['state']=='COMPLETE' and state['completed']==state['expected']==16,'Batch incomplete'
    assert plan['protocol']==p
    for path,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(path))==h,'Frozen input changed: '+path
    old=json.loads((ROOT/p['phase9_results']).read_text());oldhash=json.loads((ROOT/p['phase9_hashes']).read_text())
    records=[];inputs={}
    for j in plan['jobs']:
        r=json.loads((root/'metrics'/f"{j['key']}.json").read_text())
        assert all(r[k]==j[k] for k in ('key','method','index','delay_s','output'))
        if valid(r):
            assert r['execution_git_sha']==plan['git_sha'] and r['phase10b_no_obstacle']
            for name,h in r['input_log_sha256'].items():assert sha256_file(Path(r['output'])/name)==h,name
        inputs['10B/'+r['key']]=r.get('input_log_sha256');r=dict(r,dataset='10B');records.append(r)
    names=('agent_trajectory.csv','controller.jsonl','stage2_graph.jsonl','requests.jsonl','events.jsonl','model/inference.jsonl')
    for raw in old:
        if raw['method'] not in ('CURV','GRAPH-v6') or (raw['method']=='CURV' and raw['index']>4):continue
        r=dict(raw,dataset='9');hashes={};run=Path(r['output'])
        if valid(r):
            for name in names:
                expected=oldhash[r['key']][name];actual=sha256_file(run/name);assert expected==actual,name;hashes[name]=actual
            r['route']=route_metrics(run,r['success'])
        inputs['9/'+r['key']]=hashes;records.append(r)
    assert len(records)==36 and len({(r['dataset'],r['key']) for r in records})==36
    calls=[]
    for r in records:
        if valid(r) and r['method']=='GRAPH-v6':
            js=graph_calls(Path(r['output']),r,r['dataset'])
            assert len(js)==r['graph']['calls']
            assert sum(x['nonconverged'] for x in js)==r['graph']['independent_nonconverged']
            calls.extend(js)
    return records,calls,plan,state,inputs


def summarize(records,dataset,delay,method):
    rs=[r for r in records if r['dataset']==dataset and r['delay_s']==delay and r['method']==method and r['index']<=4]
    vs=[r for r in rs if valid(r)];ss=[r for r in vs if r['success']]
    def median(values):return float(np.median(values)) if values else None
    return dict(dataset=dataset,delay_ms=round(delay*1000),method=method,planned=4,attempted=len(rs),valid=len(vs),
        success=len(ss),failures=sum(not r['success'] for r in vs),
        corridor=sum(bool(r.get('corridor_violation')) for r in vs),
        collision=sum(bool(r.get('geometric_overlap')) for r in vs),timeout=sum(r['classification']=='STUCK' for r in vs),
        other_stop=sum(r['classification']=='CONSERVATIVE_CONTACT_STOP' for r in vs),technical=len(rs)-len(vs),
        goal_time_median_s=median([r['goal_time_s'] for r in ss]),mean_speed_m_s=float(np.mean([r['mean_speed_m_s'] for r in vs])) if vs else None,
        backtracking_events=sum(r['route']['backtracking_count'] for r in vs),
        near_goal_max_abs_y_m=max([r['route']['near_goal_max_abs_y_m'] for r in vs if r['route']['near_goal_max_abs_y_m'] is not None],default=None),
        near_goal_left_time_mean_s=float(np.mean([r['route']['near_goal_left_time_s'] for r in vs])) if vs else None,
        closest_backwards=sum(r['route']['closest_backwards'] for r in vs),subgoal_backwards=sum(r['route']['subgoal_backwards'] for r in vs),
        curv_slow_fraction_mean=float(np.mean([r['route']['curv_slow_fraction'] for r in vs if r['route']['curv_slow_fraction'] is not None])) if any(r['route']['curv_slow_fraction'] is not None for r in vs) else None,
        endpoint_clamp_fraction_mean=float(np.mean([r['route']['endpoint_clamp_fraction'] for r in vs if r['route']['endpoint_clamp_fraction'] is not None])) if any(r['route']['endpoint_clamp_fraction'] is not None for r in vs) else None)


def call_summary(js):
    n=len(js);sol=sum(j['solver_ran'] for j in js);nc=sum(j['nonconverged'] for j in js)
    return dict(calls=n,solver_calls=sol,nonconverged=nc,nonconverged_rate=nc/n if n else None,
        solver_only_nonconverged_rate=nc/sol if sol else None,accepted=sum(j['accepted'] for j in js),
        acceptance_rate=sum(j['accepted'] for j in js)/n if n else None,
        initialization_rejected=sum(j['initialization_rejected'] for j in js),
        terminal_unapplied=sum(j['disposition']=='TERMINAL_UNAPPLIED' for j in js),
        dispositions=dict(Counter(j['disposition'] for j in js)),length_m=stats([j['fresh_length_m'] for j in js]),
        progress_cost=stats([j['progress_cost'] for j in js if j['progress_cost'] is not None]),
        endpoint_edit_forward_m=stats([j['endpoint_edit_forward_m'] for j in js if j['endpoint_edit_forward_m'] is not None]),
        accepted_endpoint_edit_forward_m=stats([j['endpoint_edit_forward_m'] for j in js if j['accepted'] and j['endpoint_edit_forward_m'] is not None]))


def c6_failure_windows(records,calls):
    output=[]
    for r in records:
        if r['method']!='GRAPH-v6' or not valid(r) or r['success']:continue
        js=[j for j in calls if j['dataset']==r['dataset'] and j['key']==r['key'] and j['failure_last10']]
        n=len(js);short=sum(j['short'] for j in js)
        output.append(dict(dataset=r['dataset'],key=r['key'],index=r['index'],delay_s=r['delay_s'],termination=r['termination_reason'],
            failure_time_s=r['duration_s'],window_start_s=max(0,r['duration_s']-10),calls=n,short_calls=short,
            short_fraction=short/n if n else None,short_majority=short>n/2 if n else False))
    return output


def decide(records,calls):
    groups=[summarize(records,'10B',d,m) for d in (0.,.75) for m in ('CURV','GRAPH-v6')]
    eligible=all(g['valid']>=3 for g in groups)
    def outcome(ok,usable):return 'INCONCLUSIVE' if not usable else 'SUPPORTED' if ok else 'NOT_SUPPORTED'
    route=outcome(any(g['failures']>=2 for g in groups),eligible)
    by={(g['delay_ms'],g['method']):g for g in groups}
    specific=outcome(any(by[d,'GRAPH-v6']['failures']>=by[d,'CURV']['failures']+2 for d in (0,750)),eligible)
    cgroups=[]
    for data in ('9','10B'):
        for d in (0.,.75):
            rs=[r for r in records if r['dataset']==data and r['delay_s']==d and r['method']=='GRAPH-v6']
            cgroups.append(dict(dataset=data,delay_s=d,valid=sum(valid(r) for r in rs)))
    short=call_summary([j for j in calls if j['short']]);long=call_summary([j for j in calls if not j['short']])
    windows=c6_failure_windows(records,calls);a=None
    if short['calls'] and long['calls']:
        a=short['nonconverged_rate']>=2*long['nonconverged_rate'] and short['nonconverged_rate']>0
    b=sum(w['short_majority'] for w in windows)*2>=len(windows) if windows else None
    usable=all(g['valid']>=3 for g in cgroups) and a is not None and b is not None
    return dict(ROUTE_FAILURE_WITHOUT_OBSTACLE=dict(verdict=route,groups=groups),
        GRAPH_SPECIFIC_ROUTE_FAILURE=dict(verdict=specific,groups=groups),
        C6_SHORT_CHUNK_CONFLICT=dict(verdict=outcome(bool(a and b),usable),condition_a=a,condition_b=b,
            short=short,long=long,valid_groups=cgroups,failed_graph_runs=len(windows),short_majority_failures=sum(w['short_majority'] for w in windows),
            rate_ratio=short['nonconverged_rate']/long['nonconverged_rate'] if long['nonconverged_rate'] and short['nonconverged_rate'] is not None else 'INF' if short['nonconverged_rate'] else None))


def paired_table(records):
    output=[]
    for i in range(1,5):
        for d in (0.,.75):
            for m in ('CURV','GRAPH-v6'):
                row=dict(index=i,delay_ms=round(d*1000),method=m)
                for dataset,label in (('9','obstacle'),('10B','no_obstacle')):
                    r=next((r for r in records if (r['dataset'],r['index'],r['delay_s'],r['method'])==(dataset,i,d,m)),None)
                    row[label+'_result']=r['classification'] if r else 'MISSING'
                    row[label+'_goal_s']=r.get('goal_time_s') if r and valid(r) and r['success'] else None
                    row[label+'_backtracking']=r.get('route',{}).get('backtracking_count') if r else None
                output.append(row)
    return output


def figures(records,calls,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    candidates=sorted([r for r in records if valid(r) and r['method']=='GRAPH-v6'],key=lambda r:(r['dataset']!='10B',r['delay_s'],r['index']))
    selected=next((r for r in candidates if not r['success']),candidates[0] if candidates else None)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    if selected:
        _,pose=trace(Path(selected['output']));ax=axes[0];ax.plot(pose[:,0],pose[:,1],lw=1.3);ax.plot(pose[-1,0],pose[-1,1],'rx')
        for y in (-1.5,1.5):ax.axhline(y,c='k',lw=.7)
        spawn=selected.get('spawn')
        if spawn:
            box=spawn['obstacle'];x,y=box['center_xy_m'];sx,sy=box['size_xyz_m'][:2];ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,color='magenta',alpha=.35))
        ax.set(xlim=(-.3,8.8),ylim=(-1.6,1.6),xlabel='World x (m)',ylabel='World y (m)',title=f"Phase{selected['dataset']} {selected['key']}")
        js=[j for j in calls if (j['dataset'],j['key'])==(selected['dataset'],selected['key'])];ax=axes[1]
        ax.plot([j['time_s'] for j in js],[j['fresh_length_m'] for j in js],'.-',lw=.8,label='Native FRESH length')
        bad=[j for j in js if j['nonconverged']];ax.scatter([j['time_s'] for j in bad],[j['fresh_length_m'] for j in bad],c='red',s=10,label='Nonconverged')
        ax.axhline(.25,color='gray',ls='--',label='0.25 m');ax.axvline(selected['duration_s'],c='black',ls=':')
        ax.set(xlabel='Simulation time (s)',ylabel='Native path length (m)',title=selected['classification']);ax.legend(fontsize=8)
    else:
        for ax in axes:ax.text(.1,.5,'INCONCLUSIVE — no valid recorded Graph run',transform=ax.transAxes)
    fig.tight_layout();fig.savefig(out/'failure_path_length.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4));labels=[];values=[]
    for binname in ('0–2','2–4','4–6','6–8'):
        for dataset in ('9','10B'):
            vals=[j['fresh_length_m'] for j in calls if j['dataset']==dataset and j['x_bin']==binname]
            if vals:labels.append(f'{binname}\nP{dataset}');values.append(vals)
    if values:ax.boxplot(values,labels=labels,showfliers=False)
    else:ax.text(.1,.5,'No calls available',transform=ax.transAxes)
    ax.axhline(.25,color='gray',ls='--');ax.set(xlabel='Boundary x bin (m); calls pooled per dataset',ylabel='Native FRESH path length (m)',title=f"Outside [0,8] retained separately: {sum(j['x_bin']=='OUTSIDE' for j in calls)} calls")
    fig.tight_layout();fig.savefig(out/'length_by_x.png',dpi=160);plt.close(fig)
    return None if selected is None else {'dataset':selected['dataset'],'key':selected['key']}


def generate(root,out=None,doc=None):
    p=protocol();out=Path(out or ROOT/p['results']);doc=Path(doc or ROOT/p['report'])
    assert not out.exists() and not doc.exists(),'Previous report/results preserved'
    records,calls,plan,state,inputs=load(root);decision=decide(records,calls)
    table1=[summarize(records,'10B',d,m) for d in (0.,.75) for m in ('CURV','GRAPH-v6')];paired=paired_table(records)
    bins=[];shortlong=[]
    for dataset in ('9','10B','POOLED'):
        subset=[j for j in calls if dataset=='POOLED' or j['dataset']==dataset]
        for b in ('0–2','2–4','4–6','6–8','OUTSIDE'):
            bins.append(dict(dataset=dataset,x_bin=b,**call_summary([j for j in subset if j['x_bin']==b])))
        for short in (True,False):shortlong.append(dict(dataset=dataset,length_class='<0.25' if short else '>=0.25',**call_summary([j for j in subset if j['short']==short])))
    windows=c6_failure_windows(records,calls);topomap=[];last10map=[];runflat=[];backtracking=[]
    for r in records:
        route=r.get('route',{});meta={k:r[k] for k in ('dataset','key','method','index','delay_s')}
        topomap += [{**meta,**x} for x in route.get('topomap_series',[])]
        last10map += [{**meta,**x} for x in route.get('topomap_failure_last10',[])]
        backtracking += [{**meta,**x} for x in route.get('backtracking_events',[])]
        runflat.append({**meta,**{k:r.get(k) for k in ('classification','technical_validation','success','goal_time_s','duration_s','mean_speed_m_s','termination_reason','error')},
                        **{k:v for k,v in route.items() if k not in ('topomap_series','topomap_failure_last10','backtracking_events')}})
    out.mkdir(parents=True,exist_ok=False)
    for name,data in [('runs',runflat),('methods',table1),('paired',paired),('c6_length_classes',shortlong),('c6_x_bins',bins),('graph_calls',calls),
                      ('failure_last10_graph',[j for j in calls if j['failure_last10']]),('c6_failure_windows',windows),
                      ('topomap',topomap),('failure_last10_topomap',last10map),('backtracking',backtracking)]:write_csv(out/f'{name}.csv',data)
    selected=figures(records,calls,out)
    write_json(out/'runs.json',[{k:v for k,v in r.items() if k not in ('input_log_sha256','mechanisms','traceback')} for r in records])
    summary=dict(execution_git_sha=plan['git_sha'],protocol=p,state=state,decisions=decision,tables=dict(methods=table1,paired=paired,c6=shortlong,x_bins=bins),failure_figure=selected)
    write_json(out/'summary.json',summary);write_json(out/'input_hashes.json',inputs)
    lines=['# Phase 10B — S1-v2 obstacle-free control','',f"Execution commit: `{plan['git_sha']}`; {state['state']}, {state['completed']}/16 attempts.",p['scope'],'',
        '## Fixed conditions and technical validation','',
        'Only `--phase10b-no-obstacle` changes Phase9 runtime configuration: no spawn trigger, placement, dynamic monitor, oracle publication or heuristic intent. Original Graph-v6 / v4 factors, weights, worker, CURV fallback and timing remain unchanged. No obstacle means the unchanged worker chooses FreeField. **Phase9 after intent deactivation still retains its obstacle SDF; that geometry difference is part of this control.**',
        '21-node Topomap, D0/D750, offsets10000×index1–4, vmax0.3, unchanged NoMaD scaling0.05, 4/9/72Hz, 1s timeout, 90s limit. Batch performs original command/pose/clearance/RGB/seed replay plus absence-of-obstacle checks. Technical failures are excluded and never retried.','',
        '## Table 1 — no-obstacle results','']
    lines+=markdown_table(table1,['delay_ms','method','valid','success','corridor','collision','timeout','other_stop','technical','backtracking_events','near_goal_max_abs_y_m','near_goal_left_time_mean_s','goal_time_median_s','mean_speed_m_s','curv_slow_fraction_mean','endpoint_clamp_fraction_mean'])
    lines+=['','Failure count = valid navigation non-success. Conservative contact stop is retained separately and is not relabeled as geometric collision. Goal times use successful runs only. Curvature slowdown is CURV target<0.2 over valid non-endpoint PP duration; actual v<0.2 is separately saved.','',
        '## Table 2 — matched indices, obstacle vs no obstacle','']
    lines+=markdown_table(paired,['index','delay_ms','method','obstacle_result','no_obstacle_result','obstacle_goal_s','no_obstacle_goal_s','obstacle_backtracking','no_obstacle_backtracking'])
    lines+=['','Paired seeds do not imply identical RGB, chunks or placement. Phase9 indices5–8 are included only in the full C6 Graph population.','',
        '## Route and Topomap failures','']
    lines+=markdown_table([r for r in runflat if r['dataset']=='10B'],['key','classification','failure_time_s','failure_pose','backtracking_count','near_goal_max_abs_y_m','near_goal_left_time_s','closest_backwards','subgoal_backwards'])
    lines+=['','Backtracking = |wrapped yaw from +x|≥150° for ≥2s; use recorded72Hz intervals with final sample excluded. Start time/x and full intervals: backtracking.csv. Near goal uses x>6.5; left-wall diagnostic is y>1.0, not the actual corridor collision threshold.',
        'All inference closest/subgoal indices (observation and actual switch time) are in topomap.csv; failure-last10s indices in failure_last10_topomap.csv. Empty windows are reported, not synthesized.','',
        '## Table 3 — short-chunk diagnostics','']
    lines+=markdown_table(shortlong,['dataset','length_class','calls','solver_calls','nonconverged','nonconverged_rate','solver_only_nonconverged_rate','accepted','acceptance_rate','initialization_rejected','terminal_unapplied','progress_cost','endpoint_edit_forward_m'])
    lines+=['','Nonconvergence uses independent solver success, regardless of final ACCEPTED/SUPERSEDED/STALE disposition. Primary denominator is all submitted calls, matching Phase10A. Initialization rejection and terminal-unapplied are separate. Endpoint displacement is `(corrected−native)·B_forward`, available for returned solver output even if rejected; accepted-only distribution is also saved.',
        'The 0.25m endpoint progress term is a **soft residual**, not a hard requirement. Native polyline length and endpoint progress from B are different quantities. C6 is descriptive association, not proof of causal conflict. No solve or inference is performed by this report.','',
        '### Length distribution by actual dispatch B x','']
    lines+=markdown_table(bins,['dataset','x_bin','calls','length_m','nonconverged_rate','acceptance_rate'])
    lines+=['','Intervals [0,2),[2,4),[4,6),[6,8]; OUTSIDE calls are preserved in pooled C6. Full call-level native length, solver result, progress cost and endpoint change: graph_calls.csv. Failure-last10s: failure_last10_graph.csv.','',
        '### Failure window majority','']+markdown_table(windows,['dataset','key','termination','window_start_s','calls','short_calls','short_fraction','short_majority'])
    lines+=['','## Preregistered independent decisions','']
    lines+=markdown_table([dict(name=k,verdict=v['verdict']) for k,v in decision.items()],['name','verdict'])
    c6=decision['C6_SHORT_CHUNK_CONFLICT']
    lines += ['',f"C6: a={c6['condition_a']}, short/long nonconvergence ratio={c6['rate_ratio']}; b={c6['condition_b']}, {c6['short_majority_failures']}/{c6['failed_graph_runs']} failed Graph runs have >50% short calls in last10s.",
        'Route verdicts require ≥3 valid runs in every relevant method×delay group. C6 requires ≥3 valid Graph runs per source×delay, both length classes, and at least one failed Graph run; otherwise INCONCLUSIVE. No-call failure windows do not satisfy majority. Missing/technical runs are not zero-valued scientific samples.','',
        '![Failure path and native length](../research/results/phase10b/failure_path_length.png)','',
        '![Length by x](../research/results/phase10b/length_by_x.png)','',
        'N=4 exploratory controls. Success does not imply ≥2cm margin; original margin measurements remain in runs.json. No recovery, parameter tuning, method changes or retries.','']
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(lines))
    return {k:v['verdict'] for k,v in decision.items()}


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,required=True);a=p.parse_args()
    print(json.dumps(generate(a.run_root.resolve())))


if __name__=='__main__':main()
