"""Read-only automatic rate-limited plant report; no model/Graph execution."""
import argparse
from collections import Counter
import json
from pathlib import Path
import traceback
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_isaac.async_report import rows,stats
from nomad_phase0.chunk_report import trace
from nomad_phase4.report import write_csv
from nomad_phase4.metrics import audit as audit_reference
from .metrics import audit
from .config import protocol,METHODS
from .batch import matrix


def decide(records):
    count=lambda a,m:sum(r.get('technical_validation')=='PASS' and r.get('success',False) for r in records if r['alpha']==a and r['method']==m)
    checks={'alpha1':count('1.0','GRAPH')>=max(count('1.0','CURV'),count('1.0','CURV+ACC'))+1,
        'alpha2':count('2.0','GRAPH')>=max(count('2.0','CURV'),count('2.0','CURV+ACC')),
        'alpha_inf':count('inf','GRAPH')>=count('inf','CURV'),
        'complete_valid_24':len(records)==24 and len({r['key'] for r in records})==24 and all(r.get('technical_validation')=='PASS' for r in records)}
    return {'verdict':'ACCEL_ADVANTAGE_CANDIDATE' if all(checks.values()) else 'STOP_AND_REPORT','checks':checks}


def load(root):
    plan=json.loads((root/'plan.json').read_text());errors=[]
    jobs,references=matrix(root)
    if jobs!=plan['jobs'] or references!=plan['references'] or plan['protocol']!=protocol():errors.append('Frozen protocol/matrix changed')
    for name,h in plan['fixed_input_sha256'].items():
        if not Path(name).exists() or sha256_file(Path(name))!=h:errors.append('Frozen input changed: '+name)
    journal=rows(root/'execution.jsonl') if (root/'execution.jsonl').exists() else []
    starts=[x for x in journal if x['event']=='START'];ends=[x for x in journal if x['event']=='END']
    expected=[j['key'] for j in jobs]
    if [x['key'] for x in starts]!=expected or [x['key'] for x in ends]!=expected:errors.append('Incomplete/duplicate execution journal')
    for i in range(1,len(starts)):
        if i-1<len(ends) and ends[i-1]['monotonic_ns']>=starts[i]['monotonic_ns']:errors.append('Concurrent execution detected')
    records=[]
    for j in references+jobs:
        try:
            if errors:raise ValueError('; '.join(errors))
            if j['reused']:
                r=audit_reference(Path(j['output']),j['run_id'],j['seed_offset'],.75)
                r.update(omega_tracking_rms_rad_s=0.,omega_tracking_max_rad_s=0.,plant_intervals=0)
            else:
                old=json.loads((root/'metrics'/f"{j['key']}.json").read_text())
                if old.get('launcher_exit_code')!=0:raise RuntimeError(old.get('error','Launcher failed'))
                r=audit(Path(j['output']),j['run_id'],j['seed_offset'],.75)
                assert r['execution_git_sha']==plan['git_sha']
                for name,h in old.get('input_log_sha256',{}).items():assert sha256_file(Path(j['output'])/name)==h
        except Exception as e:r={'technical_validation':'FAIL','classification':'TECHNICAL_FAILURE','success':False,'error':repr(e),'traceback':traceback.format_exc()}
        r.update({k:v for k,v in j.items() if k not in ('argv','shell_command')});records.append(r)
    return records,plan,errors


def summarize(records,alpha,method):
    group=[r for r in records if r['alpha']==alpha and r['method']==method]
    valid=[r for r in group if r.get('technical_validation')=='PASS'];success=[r for r in valid if r['success']]
    n=sum(r.get('plant_intervals',0) for r in valid);graph=Counter()
    for r in valid:graph.update(r['graph']['dispositions'])
    calls=sum(r['graph']['calls'] for r in valid)
    return {'alpha':alpha,'method':method,'attempts':len(group),'valid':len(valid),'reused':sum(r['reused'] for r in group),
        'success':len(success),'collision':sum(r['geometric_overlap'] for r in valid),
        'corridor':sum(r['corridor_violation'] for r in valid),'timeout':sum(r['classification']=='STUCK' for r in valid),
        'technical_failure':len(group)-len(valid),'other':sum(r['classification'] not in ('SUCCESS','SAFETY_FAILURE','STUCK') for r in valid),
        'goal_time_median_s':float(np.median([r['goal_time_s'] for r in success])) if success else None,
        'mean_speed_m_s':float(np.mean([r['mean_speed_m_s'] for r in valid])) if valid else None,
        'minimum_clearance_m':min((r[f'StaticObstacle{i}_minimum_clearance_m'] for r in valid for i in (1,2)),default=None),
        'tracking_rms_rad_s':float(np.sqrt(sum(r['omega_tracking_rms_rad_s']**2*r.get('plant_intervals',0) for r in valid)/n)) if n else (0. if valid and alpha=='inf' else None),
        'tracking_max_rad_s':max((r['omega_tracking_max_rad_s'] for r in valid),default=None),
        'graph_calls':calls,'graph_accepted':graph['ACCEPTED'],'graph_acceptance_fraction':graph['ACCEPTED']/calls if calls else None,
        'graph_dispositions':dict(graph)}


def plot(out,records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    c=json.loads((ROOT/protocol()['scenario']).read_text());fig,ax=plt.subplots(figsize=(10,4.5))
    for b in c['obstacles']:
        x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='#509d55',alpha=.45))
    corridor=c['corridor'];ax.axhline(corridor['half_width'],color='black');ax.axhline(-corridor['half_width'],color='black')
    ax.add_patch(Circle(c['goal_pose'][:2],c['goal_tolerance_m'],fill=False,linestyle='--',color='black'))
    colors={'CURV':'#777777','CURV+ACC':'#d6860d','GRAPH':'#176ca4'}
    for r in records:
        if r['alpha']!='1.0' or r['index']!=1 or not (Path(r['output'])/'agent_trajectory.csv').exists():continue
        try:_,p=trace(Path(r['output']))
        except Exception:continue
        ax.plot(p[:,0],p[:,1],color=colors[r['method']],label=f"{r['method']}: {r['classification']}")
        ax.scatter(*p[-1,:2],marker='o' if r.get('success') else 'x',color=colors[r['method']])
    ax.set(xlabel='World X (m)',ylabel='World Y (m)',title='alpha = 1.0 rad/s² / D750 / index 1',xlim=(corridor['xmin'],corridor['xmax']),ylim=(-corridor['half_width']-.15,corridor['half_width']+.15))
    ax.set_aspect('equal');ax.grid(alpha=.15)
    if ax.lines:ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'alpha1_index1_paths.png',dpi=160);plt.close(fig)


def generate(root,out,doc):
    assert not out.exists() and not doc.exists(),'Existing report preserved; no overwrite'
    records,plan,errors=load(root)
    groups=[summarize(records,a,m) for a,methods in (('inf',('CURV','GRAPH')),('2.0',METHODS),('1.0',METHODS)) for m in methods]
    verdict=decide(records);out.mkdir(parents=True,exist_ok=False)
    write_json(out/'summary.json',{'execution_git_sha':plan['git_sha'],'protocol':protocol(),'decision':verdict,'conditions':groups,'technical_errors':errors})
    write_json(out/'runs.json',records);write_csv(out/'conditions.csv',groups)
    write_csv(out/'runs.csv',[{k:v for k,v in r.items() if k not in ('handoffs','request_seeds','input_log_sha256','traceback')} for r in records])
    paired=[]
    for a in ('inf','2.0','1.0'):
        for i in range(1,4):
            row={'alpha':a,'index':i,'seed_offset':i*10000}
            for m in METHODS:
                found=next((r for r in records if r['alpha']==a and r['index']==i and r['method']==m),None)
                row[m]=found['classification'] if found else 'IDENTICAL_TO_CURV_NOT_RERUN'
                row[m+'_goal_time_s']=found.get('goal_time_s') if found else None
            paired.append(row)
    write_csv(out/'paired.csv',paired);plot(out,records)
    f=lambda v:'N/A' if v is None else f'{v:.4f}'
    text=['# Phase 4c Angular Acceleration Limit', '',f"Git SHA: `{plan['git_sha']}`; Oracle geometry; SE(2) kinematic Isaac Sim.",
        '','|α|Method|Success/N|Collision|Corridor|Timeout|Technical|Goal median s|Mean v m/s|Min clearance m|ω error RMS/max rad/s|Graph accepted/calls|',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for g in groups:text.append(f"|{g['alpha']}|{g['method']}|{g['success']}/{g['attempts']}|{g['collision']}|{g['corridor']}|{g['timeout']}|{g['technical_failure']}|{f(g['goal_time_median_s'])}|{f(g['mean_speed_m_s'])}|{f(g['minimum_clearance_m'])}|{f(g['tracking_rms_rad_s'])}/{f(g['tracking_max_rad_s'])}|{g['graph_accepted']}/{g['graph_calls']}|")
    text+=['','α=∞ CURV: reused v5 pilot indices 1–3. CURV+ACC is identical and was not rerun. Goal median uses successful runs only. RMS is weighted over positive-duration72Hz intervals. Minimum clearance is the smallest obstacle swept lower bound.',
        '','|α|Index|CURV|CURV+ACC|GRAPH|','|---|---:|---|---|---|']
    for r in paired:text.append(f"|{r['alpha']}|{r['index']}|{r['CURV']}|{r['CURV+ACC']}|{r['GRAPH']}|")
    text+=['',f"`{verdict['verdict']}`",'',f"Checks: `{json.dumps(verdict['checks'],sort_keys=True)}`",'',
        '![alpha1 index1 actual paths](../research/results/phase4c/alpha1_index1_paths.png)']
    if any(r.get('error') for r in records):
        text+=['','|Technical failure|Recorded error|','|---|---|']
        for r in records:
            if r.get('error'):text.append(f"|{r['key']}|{r['error']}|")
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(text)+'\n');return verdict


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'research/results/phase4c');p.add_argument('--document',type=Path,default=ROOT/'docs/PHASE4C_ACCEL_LIMIT.md')
    a=p.parse_args();print(generate(a.run_root.resolve(),a.output,a.document)['verdict'])

if __name__=='__main__':main()
