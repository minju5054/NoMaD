"""Automatic Phase11 comparison; saved results only, no solver or navigation."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import stats
from nomad_phase0.chunk_report import trace
from nomad_phase4.report import write_csv
from nomad_phase8.batch import completion
from nomad_phase8.report import markdown_table
from nomad_phase10b.report import call_summary
from .config import protocol
from .metrics import enrich,graph_calls


def valid(r):
    return r.get('technical_validation')=='PASS' and r.get('classification')!='PLACEMENT_INVALID'


def load(root):
    p=protocol();plan=json.loads((root/'plan.json').read_text());state=completion(root)
    assert state['state']=='COMPLETE' and state['completed']==state['expected']==20,'Batch incomplete'
    assert plan['protocol']==p
    for path,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(path))==h,'Frozen input changed: '+path
    records=[];inputs={}
    for j in plan['jobs']:
        r=json.loads((root/'metrics'/f"{j['key']}.json").read_text())
        assert all(r[k]==j[k] for k in ('key','method','scene','index','delay_s','output'))
        if r.get('technical_validation')=='PASS':
            assert r['execution_git_sha']==plan['git_sha'] and r['phase11_v61']
            for name,h in r['input_log_sha256'].items():assert sha256_file(Path(r['output'])/name)==h,name
        inputs['11/'+r['key']]=r.get('input_log_sha256',{});records.append(dict(r,dataset='11'))
    names=('scenario.json','agent_trajectory.csv','controller.jsonl','requests.jsonl','events.jsonl','model/inference.jsonl','stage2_graph.jsonl','summary.json')
    for dataset,ref in p['reference_sets'].items():
        old=json.loads((ROOT/ref['results']).read_text());hashes=json.loads((ROOT/ref['hashes']).read_text())
        for original in old:
            if dataset=='10B' and original['dataset']!='10B':continue
            r=dict(original,dataset=dataset,scene='sudden' if dataset=='9' else 'noobs');run=Path(r['output'])
            key=r['key'] if dataset=='9' else '10B/'+r['key'];saved=hashes[key];used={}
            if r.get('technical_validation')=='PASS':
                check=list(names)
                if r.get('spawn'):check+=['dynamic/spawn.json','dynamic/clearance.jsonl']
                for name in check:
                    h=sha256_file(run/name);assert saved[name]==h,(dataset,key,name);used[name]=h
                # Revalidate metadata used by enrichment, without solving or replaying inference.
                summary=json.loads((run/'summary.json').read_text())
                assert bool(summary['goal_entry'])==r['goal_entry']
                if r.get('spawn'):assert json.loads((run/'dynamic/spawn.json').read_text())==r['spawn']
                enrich(run,r)
            inputs[dataset+'/'+r['key']]=used;records.append(r)
    assert len(records)==76 and len({(r['dataset'],r['key']) for r in records})==76
    calls=[]
    for r in records:
        if valid(r) and r['method'] in ('GRAPH-v6','GRAPH-v6.1'):
            js=graph_calls(Path(r['output']),r,r['dataset'])
            assert len(js)==r['graph']['calls'] and sum(j['nonconverged'] for j in js)==r['graph']['independent_nonconverged']
            calls+=js
    return records,calls,plan,state,inputs


def groups(records):
    out=[]
    for dataset,scene,method,delays in [('11','sudden','GRAPH-v6.1',(.75,0.)),('11','noobs','GRAPH-v6.1',(.75,0.)),
        ('9','sudden','CURV',(.75,0.)),('9','sudden','SELECT',(.75,)),('9','sudden','INTENT-SPLICE',(.75,)),('9','sudden','GRAPH-v6',(.75,0.)),
        ('10B','noobs','CURV',(.75,0.)),('10B','noobs','GRAPH-v6',(.75,0.))]:
        for d in delays:
            n=8 if scene=='sudden' and d==.75 else 4
            out.append(summarize([r for r in records if (r['dataset'],r['scene'],r['method'],r['delay_s'])==(dataset,scene,method,d)],
                                 dict(dataset=dataset,scene=scene,method=method,delay_ms=round(d*1000)),n))
    return out


def summarize(rs,meta,n):
    vs=[r for r in rs if valid(r)];ss=[r for r in vs if r['success']]
    def mean(values):return float(np.mean(values)) if values else None
    def minimum(values):return min(values) if values else None
    return dict(**meta,planned=n,attempts=len(rs),valid=len(vs),required_valid=math.ceil(.875*n),
        success=len(ss),safe_passage=sum(r.get('passage',{}).get('safe_passage') is True for r in vs) if meta['scene']=='sudden' else None,
        collision=sum(bool(r.get('geometric_overlap')) for r in vs),corridor=sum(bool(r.get('corridor_violation')) for r in vs),
        timeout=sum(r['classification']=='STUCK' for r in vs),other_stop=sum(r['classification']=='CONSERVATIVE_CONTACT_STOP' for r in vs),
        technical=sum(r.get('technical_validation')!='PASS' for r in rs),placement_invalid=sum(r['classification']=='PLACEMENT_INVALID' for r in rs),
        dynamic_minimum_clearance_m=minimum([r['passage']['dynamic_minimum_clearance_m'] for r in vs if r.get('passage',{}).get('dynamic_minimum_clearance_m') is not None]),
        goal_time_median_s=float(np.median([r['goal_time_s'] for r in ss])) if ss else None,
        mean_speed_m_s=mean([r['mean_speed_m_s'] for r in vs]),
        backtracking_events=sum(r['route']['backtracking_count'] for r in vs),
        near_goal_max_abs_y_m=max([r['route']['near_goal_max_abs_y_m'] for r in vs if r['route']['near_goal_max_abs_y_m'] is not None],default=None),
        near_goal_left_time_mean_s=mean([r['route']['near_goal_left_time_s'] for r in vs]))


def decide(records,calls):
    gs=groups(records);by={(g['scene'],g['method'],g['delay_ms']):g for g in gs}
    def get(scene,method,delays=(750,0)):return [by[scene,method,d] for d in delays]
    sudden=get('sudden','GRAPH-v6.1');old=get('sudden','GRAPH-v6');splice=get('sudden','INTENT-SPLICE',(750,));noobs=get('noobs','GRAPH-v6.1')
    oldno=get('noobs','GRAPH-v6');short=[j for j in calls if j['method']=='GRAPH-v6.1' and j['short']]
    short_rate=sum(j['nonconverged'] for j in short)/len(short) if short else None
    def verdict(test,relevant,evidence=True,**measurements):
        eligible=all(g['valid']>=g['required_valid'] for g in relevant) and evidence
        return dict(verdict='INCONCLUSIVE' if not eligible else 'SUPPORTED' if test else 'NOT_SUPPORTED',
                    valid_groups=[{k:g[k] for k in ('scene','method','delay_ms','planned','valid','required_valid')} for g in relevant],**measurements)
    return dict(
        V61_SAFE_PASSAGE=verdict(sum(g['safe_passage'] for g in sudden)>=11,sudden,actual=sum(g['safe_passage'] for g in sudden),target=11,planned=12),
        V61_GOAL_IMPROVES=verdict(sum(g['success'] for g in sudden)>=sum(g['success'] for g in old)+3,sudden+old,
                                actual=sum(g['success'] for g in sudden),reference=sum(g['success'] for g in old),required_increment=3),
        V61_VS_SPLICE=verdict(sudden[0]['success']>=splice[0]['success']+2,[sudden[0]]+splice,
                            actual=sudden[0]['success'],reference=splice[0]['success'],required_increment=2),
        C6_FIXED=verdict(short_rate is not None and short_rate<=.305,sudden+noobs+old+oldno,bool(short),
                        short_calls=len(short),short_nonconverged=sum(j['nonconverged'] for j in short),short_rate=short_rate,fixed_reference=.61,threshold=.305),
        NO_HARM_NOOBS=verdict(sum(g['success'] for g in noobs)>=7,noobs,actual=sum(g['success'] for g in noobs),target=7,planned=8))


def figures(records,calls,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for i,ax in enumerate(axes,1):
        rs=[r for r in records if r['scene']=='sudden' and r['delay_s']==.75 and r['index']==i and r['method'] in ('GRAPH-v6','GRAPH-v6.1')]
        for r in rs:
            if not valid(r):continue
            _,pose=trace(Path(r['output']));color='tab:blue' if r['method']=='GRAPH-v6' else 'tab:orange'
            ax.plot(pose[:,0],pose[:,1],color=color,label=f"{r['method']} {r['classification']}");ax.plot(*pose[-1,:2],'x',color=color)
            if r.get('spawn'):
                box=r['spawn']['obstacle'];x,y=box['center_xy_m'];sx,sy=box['size_xyz_m'][:2]
                ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,color=color,alpha=.18))
        for y in (-1.5,1.5):ax.axhline(y,color='k',lw=.7)
        ax.plot(8,0,'g*');ax.set(xlabel='World x (m)',ylabel='World y (m)',title=f'D750 index {i}; each run has its own box')
        if ax.lines:ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(out/'sudden_paths.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    bins=('0–2','2–4','4–6','6–8')
    for scene,ax in zip(('sudden','noobs'),axes):
        for method in ('GRAPH-v6','GRAPH-v6.1'):
            ys=[];ns=[]
            for b in bins:
                js=[j for j in calls if j['scene']==scene and j['method']==method and j['x_bin']==b]
                ns.append(len(js));ys.append(sum(j['accepted'] for j in js)/len(js) if js else np.nan)
            ax.plot(range(4),ys,'o-',label=f'{method}, n={ns}')
        ax.set(xticks=range(4),xticklabels=bins,ylim=(-.04,1.04),xlabel='Dispatch B world x (m)',ylabel='Accepted / submitted calls',title=scene)
        ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(out/'acceptance_by_x.png',dpi=160);plt.close(fig)


def generate(root,out=None,doc=None):
    p=protocol();out=Path(out or ROOT/p['results']);doc=Path(doc or ROOT/p['report'])
    assert not out.exists() and not doc.exists(),'Existing report/results preserved'
    records,calls,plan,state,inputs=load(root);decision=decide(records,calls);table=groups(records)
    sides=[];lengths=[];bins=[];topomap=[];runflat=[];series=[]
    for g in table:
        subset=[r for r in records if (r['dataset'],r['scene'],r['method'],round(r['delay_s']*1000))==(g['dataset'],g['scene'],g['method'],g['delay_ms'])]
        if g['scene']=='sudden':
            for sign in (1,-1):
                sides.append(summarize([r for r in subset if (1 if r['index']%2 else -1)==sign],
                    {k:g[k] for k in ('dataset','scene','method','delay_ms')}|dict(placement_s=sign),g['planned']//2))
        for stage in ('intent_active','other'):
            rs=[r for r in subset if valid(r)]
            topomap.append({k:g[k] for k in ('dataset','scene','method','delay_ms','valid','planned')}|dict(intent_stage=stage,
                observations=sum(r['topomap_by_intent'][stage]['observations'] for r in rs),
                closest_backwards=sum(r['topomap_by_intent'][stage]['closest'] for r in rs),
                subgoal_backwards=sum(r['topomap_by_intent'][stage]['subgoal'] for r in rs)))
    for method in ('GRAPH-v6','GRAPH-v6.1'):
        for scene in ('sudden','noobs','POOLED'):
            js=[j for j in calls if j['method']==method and (scene=='POOLED' or j['scene']==scene)]
            for short in (True,False):
                subset=[j for j in js if j['short']==short]
                lengths.append(dict(method=method,scene=scene,length_class='<0.25' if short else '>=0.25',**call_summary(subset),
                                    p_native_m=stats([j['p_native_m'] for j in subset]),progress_target_m=stats([j['progress_target_m'] for j in subset]),disabled_progress=sum(not j['progress_enabled'] for j in subset)))
            for b in ('0–2','2–4','4–6','6–8','OUTSIDE'):
                bins.append(dict(method=method,scene=scene,x_bin=b,**call_summary([j for j in js if j['x_bin']==b])))
    for r in records:
        meta={k:r[k] for k in ('dataset','scene','key','method','index','delay_s')}
        runflat.append(meta|{k:r.get(k) for k in ('classification','technical_validation','success','goal_time_s','duration_s','mean_speed_m_s','termination_reason','error')}|
            r.get('passage',{})|{k:v for k,v in r.get('route',{}).items() if k not in ('topomap_series','topomap_failure_last10','backtracking_events')})
        series += [meta|s for s in r.get('route',{}).get('topomap_series',[])]
    out.mkdir(parents=True,exist_ok=False)
    for name,data in [('runs',runflat),('groups',table),('sides',sides),('length_classes',lengths),('x_bins',bins),('graph_calls',calls),('topomap_stages',topomap),('topomap',series)]:write_csv(out/f'{name}.csv',data)
    figures(records,calls,out)
    write_json(out/'runs.json',[{k:v for k,v in r.items() if k not in ('input_log_sha256','mechanisms','traceback')} for r in records])
    write_json(out/'input_hashes.json',inputs)
    summary=dict(execution_git_sha=plan['git_sha'],state=state,protocol=p,decisions=decision,groups=table,length_classes=lengths,x_bins=bins)
    write_json(out/'summary.json',summary)
    columns=['delay_ms','method','planned','valid','safe_passage','success','collision','corridor','timeout','other_stop','technical','placement_invalid','dynamic_minimum_clearance_m','backtracking_events','goal_time_median_s','mean_speed_m_s']
    lines=['# Phase 11 — Graph-v6.1 adaptive progress','',f"Execution commit: `{plan['git_sha']}`; {state['state']}, {state['completed']}/20 attempts.",p['scope'],'',
        'Only endpoint progress changes: p_native=(native FRESH endpoint−B.xy)·B-forward; target=min(0.25,0.9·max(p_native,0)). Target=0 removes that residual. The original 0.25m normalization, all other weights, initialization, constraints, solver, worker timing and CURV fallback are preserved. Observation anchoring is unchanged.','',
        '## Table 1 — sudden obstacle comparisons','']
    lines+=markdown_table([g for g in table if g['scene']=='sudden'],columns)
    lines+=['','Safe passage means footprint rear clears box rear with no dynamic geometric overlap through that tick; later corridor failure does not erase passage. It does not imply 2cm margin or goal success. Conservative contact stops are reported separately.','',
            '## Table 2 — placement side (+1 odd / −1 even)','']+markdown_table(sides,['delay_ms','method','placement_s','planned','valid','safe_passage','success','collision','corridor','timeout'])
    lines+=['','## Table 3 — obstacle-free controls','']+markdown_table([g for g in table if g['scene']=='noobs'],[c for c in columns if c not in ('safe_passage','dynamic_minimum_clearance_m')]+['near_goal_max_abs_y_m','near_goal_left_time_mean_s'])
    lines+=['','## Table 4 — native chunk length diagnostics','']+markdown_table(lengths,['scene','method','length_class','calls','solver_calls','nonconverged','nonconverged_rate','solver_only_nonconverged_rate','accepted','acceptance_rate','initialization_rejected','terminal_unapplied','disabled_progress','progress_cost'])
    lines+=['','Native length and forward endpoint projection are different quantities. Nonconvergence uses independent solver success over all submitted calls (matching Phase10B); solver-only rates and initialization failures remain separate. Disabled progress has cost0 only when a solver result exists. C6_FIXED uses the preregistered 61%/2=30.5% threshold, not a fitted threshold.','',
        '## Table 5 — Topomap backward transitions','']+markdown_table(topomap,['scene','delay_ms','method','valid','intent_stage','observations','closest_backwards','subgoal_backwards'])
    lines+=['',p['metrics']['topomap_phase']+'. Phase10B backtracking (yaw≥150° for≥2s), near-goal diagnostics, passage time/side and all call p_native/targets are saved in CSV/JSON.','',
        '## Independent preregistered decisions','']+markdown_table([dict(name=k,**v) for k,v in decision.items()],['name','verdict','actual','target','reference','required_increment','short_rate','threshold'])
    lines+=['','Each involved scene×delay×method group requires ceil(87.5% of planned) valid runs: 7/8 and 4/4. Technical and PLACEMENT_INVALID runs are excluded from valid denominators; no retry. Missing short calls make C6 INCONCLUSIVE. Original Phase9 and Phase10B results are reused read-only, with input hashes verified.','',
        '![D750 paired routes](../research/results/phase11/sudden_paths.png)','',
        '![Acceptance by dispatch x](../research/results/phase11/acceptance_by_x.png)','',
        'Counts are exploratory; same seed does not guarantee identical RGB or obstacle placement. A reduction in short-chunk nonconvergence alone does not establish causality or navigation improvement. No method tuning or automatic further experiments.','']
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(lines))
    return {k:v['verdict'] for k,v in decision.items()}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',required=True,type=Path);a=ap.parse_args()
    print(json.dumps(generate(a.run_root.resolve())))


if __name__=='__main__':main()
