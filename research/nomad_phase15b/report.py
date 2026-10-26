"""Generate PILOT tables/figures and publish only Phase15B report artifacts."""
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,write_json
from nomad_phase4.report import write_csv
from nomad_phase8.report import markdown_table as _table

def markdown_table(data):
    return "\n".join(_table(data,list(data[0]))) if data else "None."
from nomad_phase12.report import wilson
from nomad_phase0.chunk_report import trace
from .config import METHODS,SAFE,protocol
from .batch import completion
OUT=ROOT/'research/results/phase15b'
DOC=ROOT/'docs/PHASE15B_DEPTH_PILOT.md'

def valid(r):return r.get('technical_validation')=='PASS'
def paired(records):
    aa={r['index']:r for r in records if r['method']==SAFE[2] and valid(r) and r.get('checkpoint_time_s') is not None}
    bb={r['index']:r for r in records if r['method']==SAFE[0] and valid(r) and r.get('checkpoint_time_s') is not None}
    ids=sorted(set(aa)&set(bb));d=np.array([aa[i]['checkpoint_time_s']-bb[i]['checkpoint_time_s'] for i in ids])
    ci=None
    if len(d):
        rng=np.random.default_rng(20261027);boot=d[rng.integers(0,len(d),(20000,len(d)))].mean(axis=1);ci=np.quantile(boot,[.025,.975]).tolist()
    return dict(method=SAFE[2],comparator=SAFE[0],n=len(ids),indices=ids,mean_difference_s=float(d.mean()) if len(d) else None,ci95_s=ci,negative_pairs=int(sum(d<0)))

def tables(records):
    groups=[]
    for m in METHODS:
        attempted=[r for r in records if r['method']==m];rs=[r for r in attempted if valid(r)]
        def avg(k):
            vals=[r[k] for r in rs if r.get(k) is not None];return float(np.mean(vals)) if vals else None
        def med(k):
            vals=[r[k] for r in rs if r.get(k) is not None];return float(np.median(vals)) if vals else None
        def nested_mean(section,key,stat='median'):
            vals=[r.get(section,{}).get(key,{}).get(stat) for r in rs];vals=[v for v in vals if v is not None];return float(np.mean(vals)) if vals else None
        g=[r.get('graph',{}) for r in rs];solves=[s for x in g for s in x.get('solver_samples_s',[])];calls=sum(x.get('calls',0) for x in g)
        counts={k:sum(x.get('dispositions',{}).get(k,0) for x in g) for k in ('ACCEPTED','NONCONVERGED','CONSTRAINT_FAILED','INITIALIZATION_REJECTED','STALE','SUPERSEDED','WAYPOINT_EXPIRED')}
        total=sum(r.get('depth',{}).get('decision_count',0) for r in rs);agree=sum(r.get('depth',{}).get('agreement_count',0) for r in rs);danger=sum(r.get('depth',{}).get('dangerous_false_safe',0) for r in rs)
        groups.append(dict(method=m,planned=8,attempted=len(attempted),valid=len(rs),technical=len(attempted)-len(rs),success=sum(r['success'] for r in rs),collision=sum(bool(r.get('geometric_overlap')) for r in rs),corridor=sum(bool(r.get('corridor_violation')) for r in rs),safety_failures=sum(bool(r.get('geometric_overlap') or r.get('corridor_violation')) for r in rs),stuck=sum(r.get('classification')=='STUCK' for r in rs),other=sum(r.get('classification')=='CONSERVATIVE_CONTACT_STOP' for r in rs),success_wilson95=wilson(sum(r['success'] for r in rs),len(rs)),goal_time_median_s=med('goal_time_s'),checkpoint_median_s=med('checkpoint_time_s'),checkpoint_mean_speed_m_s=avg('checkpoint_mean_speed_m_s'),curv_slow_time_fraction=avg('curv_slow_time_fraction'),minimum_clearance_m=min((r['minimum_obstacle_clearance_m'] for r in rs),default=None),all_unsafe=sum(r.get('all_unsafe',0) for r in rs),fallback_cap_time_fraction=avg('fallback_cap_time_fraction'),graph_calls=calls,graph_acceptance=counts['ACCEPTED']/calls if calls else None,graph_dispositions=counts,nonconverged=sum(x.get('independent_nonconverged',0) for x in g),solve_median_s=float(np.median(solves)) if solves else None,solve_p95_s=float(np.quantile(solves,.95)) if solves else None,sdf_active_fraction=float(np.mean([x['accepted_sdf_active_fraction'] for x in g if x.get('accepted_sdf_active_fraction') is not None])) if any(x.get('accepted_sdf_active_fraction') is not None for x in g) else None,depth_update_median_ms=nested_mean('depth','update_ms'),depth_update_p95_ms=nested_mean('depth','update_ms','p95'),snapshot_age_median_s=nested_mean('depth','snapshot_age_s'),snapshot_age_p95_s=nested_mean('depth','snapshot_age_s','p95'),depth_agreement=agree/total if total else None,depth_dangerous_count=danger,depth_sample_count=total,unknown_fraction=nested_mean('depth','selected_unknown_fraction'),inference_median_ms=float(np.mean([r['inference_ms']['median'] for r in rs])) if rs else None,inference_p95_ms=float(np.mean([r['inference_ms']['p95'] for r in rs])) if rs else None))
    lookup={g['method']:g for g in groups};a,b=lookup[SAFE[2]],lookup[SAFE[0]];raw=lookup[METHODS[0]]
    f1='PILOT_INCONCLUSIVE' if min(raw['valid'],b['valid'])<8 else 'PILOT_FILTER_REMOVES_COLLISIONS' if b['collision']==0 and b['collision']<=raw['collision'] else 'PILOT_FILTER_REMOVES_COLLISIONS_NOT_SHOWN'
    label='PILOT_INCONCLUSIVE' if min(a['valid'],b['valid'])<8 else 'PILOT_GRAPH_DEPTH_BETTER' if a['success']>=b['success']+2 and a['safety_failures']<=b['safety_failures'] else 'PILOT_GRAPH_DEPTH_WORSE' if a['success']<=b['success']-2 or a['safety_failures']>=b['safety_failures']+2 else 'PILOT_GRAPH_DEPTH_EQUAL'
    labels=dict(F1=f1,G=label,depth_vs_gf_collision_counts=[a['collision'],lookup[SAFE[1]]['collision']],depth_vs_temporal_success_counts=[a['success'],lookup[METHODS[4]]['success']],scope='PILOT; auxiliary counts are descriptive, incomplete groups are not efficacy evidence')
    return groups,[paired(records)],labels

def load(root):
    state=completion(root);assert state['state']=='COMPLETE'
    plan=json.loads((root/'plan.json').read_text());assert plan['protocol']==protocol()
    for f,h in plan['fixed_input_sha256'].items():assert sha256_file(Path(f))==h,f
    records=[]
    for j in plan['jobs']:
        r=json.loads((root/'metrics'/f"{j['key']}.json").read_text())
        assert all(r[k]==j[k] for k in ('key','method','index','seed_offset','output'))
        if valid(r):
            assert r['execution_git_sha']==plan['git_sha']
            for f,h in r['input_log_sha256'].items():assert sha256_file(Path(r['output'])/f)==h,f
        records.append(r)
    return records,plan

def figures(records,groups,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    colors=plt.get_cmap('tab10').colors
    fig,ax=plt.subplots(figsize=(11,4));ax.bar(range(6),[g['success'] for g in groups],color=[colors[i] if i<5 else '.65' for i in range(6)])
    ax.set_xticks(range(6),METHODS,rotation=18,ha='right');ax.set_ylim(0,8.8);ax.set_ylabel('PILOT successes / 8');fig.tight_layout();fig.savefig(out/'success.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4));alltimes=[r['checkpoint_time_s'] for r in records if valid(r) and r.get('checkpoint_time_s') is not None];missing_y=max(alltimes,default=0)+5
    for j,m in enumerate(METHODS):
        rs=[r for r in records if r['method']==m];values=[]
        for k,r in enumerate(rs):
            t=r.get('checkpoint_time_s') if valid(r) else None;x=j+(k-3.5)*.025
            ax.scatter(x,t if t is not None else missing_y,facecolors=colors[j] if t is not None else 'none',edgecolors=colors[j]);
            if t is not None:values.append(t)
        if values:ax.hlines(np.median(values),j-.22,j+.22,color='black',linewidth=2)
    ax.text(0,missing_y+1,'Open circles: no checkpoint / technical failure; height is not an imputed time',fontsize=8)
    ax.set_xticks(range(6),METHODS,rotation=18,ha='right');ax.set_ylabel('Checkpoint time (s)');fig.tight_layout();fig.savefig(out/'checkpoint_time.png',dpi=150);plt.close(fig)
    def path_plot(rs,name):
        fig,ax=plt.subplots(figsize=(10,5))
        for r in rs:
            if not (Path(r['output'])/'agent_trajectory.csv').exists():continue
            _,poses=trace(Path(r['output']));j=METHODS.index(r['method']);ax.plot(poses[:,0],poses[:,1],color=colors[j],label=r['method'],linewidth=1.4)
            final=Path(r['output'])/'depth/final.npz'
            if final.exists():
                with np.load(final) as z:
                    y,x=np.nonzero(z['occupied']);xy=z['origin']+np.column_stack([x,y])*float(z['h']);ax.scatter(xy[:,0],xy[:,1],s=.3,color='.65',alpha=.18)
        scenes=[Path(r['output'])/'scenario.json' for r in rs if (Path(r['output'])/'scenario.json').exists()]
        if scenes:
            scene=json.loads(scenes[0].read_text())
            for b in scene['obstacles']:
                x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='.35',alpha=.5))
            ax.axhline(scene['corridor']['half_width'],color='black');ax.axhline(-scene['corridor']['half_width'],color='black')
        ax.set_aspect('equal');ax.set_xlim(-.3,4.8);ax.set_ylim(-1.7,1.7);ax.legend(fontsize=7);ax.set_title('Posthoc oracle geometry; gray = final depth occupancy');fig.tight_layout();fig.savefig(out/name,dpi=160);plt.close(fig)
    eligible=[i for i in range(47,55) if sum(valid(r) and r['success'] for r in records if r['index']==i)>=4]
    if eligible:path_plot([r for r in records if r['index']==eligible[0]],'paths.png')
    for r in records:
        if valid(r) and r.get('geometric_overlap'):path_plot([r],f"collision_{r['method']}_{r['index']}.png")

def render(records,plan,out,doc,make_figures=True):
    out.mkdir(parents=True,exist_ok=False);doc.parent.mkdir(parents=True,exist_ok=True);assert not doc.exists()
    groups,pairs,labels=tables(records)
    write_json(out/'runs.json',records);write_csv(out/'summary.csv',groups);write_csv(out/'paired.csv',pairs);write_json(out/'decisions.json',labels)
    if make_figures:figures(records,groups,out)
    failures=[dict(index=r['index'],method=r['method'],error=r.get('error')) for r in records if not valid(r)]
    depth=[{k:g[k] for k in ('method','depth_update_median_ms','depth_update_p95_ms','snapshot_age_median_s','snapshot_age_p95_s','depth_agreement','depth_dangerous_count','depth_sample_count','unknown_fraction','inference_median_ms','inference_p95_ms')} for g in groups]
    text='# Phase 15-B depth pilot\n\nPILOT only. Isaac RGB closed-loop SE(2) kinematic navigation. Exact simulator odometry; no odometry error. NoMaD receives RGB only. Methods 1–5 receive no oracle geometry; SELECT+GRAPH is an oracle reference excluded from decisions.\n\n'
    text+='Noise enabled: σ=0.01d². V1 one update/cell/frame; occupied priority; unknown is not occupied. Depth certificate covers occupied lattice sites, not unobserved physical geometry. Map allocation bounds encode no walls. Every captured observation is integrated in FIFO order, independently of control. Snapshot age uses capture simulation timestamp; publication time is separately logged. ALL_UNSAFE caps the CURV target at 0.10m/s, with existing acceleration limits.\n\n'
    text+='Execution SHA: `'+str(plan.get('git_sha'))+'`. All methods include depth rendering/map CPU load. Timing tables average run-level median/p95 (not pooled percentiles).\n\n'
    text+=markdown_table([{k:g[k] for k in ('method','valid','technical','success','collision','corridor','stuck','goal_time_median_s','checkpoint_median_s','checkpoint_mean_speed_m_s','curv_slow_time_fraction','minimum_clearance_m','all_unsafe','fallback_cap_time_fraction')} for g in groups])+'\n\nSeed × method\n\n'+markdown_table([{k:r.get(k) for k in ('index','method','classification','checkpoint_time_s','goal_time_s','minimum_obstacle_clearance_m')} for r in records])+'\n\nDepth measurements\n\n'+markdown_table(depth)+'\n\nPreregistered pilot decisions\n\n```json\n'+json.dumps(labels,indent=2)+'\n```\n\n'
    text+='Graph measurements\n\n'+markdown_table([{k:g[k] for k in ('method','graph_calls','graph_acceptance','graph_dispositions','nonconverged','solve_median_s','solve_p95_s','sdf_active_fraction')} for g in groups])+'\n\n'
    text+=markdown_table(pairs)+'\n\nPaired checkpoint comparison uses only jointly observed checkpoint times, 20,000 bootstrap replicates, seed 20261027. Missing times are never replaced by timeout. Wilson intervals are descriptive.\n\nTechnical failures\n\n'+(markdown_table(failures) if failures else 'None.')+'\n\n'
    for img in sorted(out.glob('*.png')):text+=f'![{img.stem}](../research/results/phase15b/{img.name})\n\n'
    if make_figures and not (out/'paths.png').exists():text+='No seed had at least four successful methods; paths.png omitted by the preregistered criterion.\n'
    doc.write_text(text)

def publish():
    paths=[str(OUT.relative_to(ROOT)),str(DOC.relative_to(ROOT))]
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip(),'Unrelated staged files preserved; unstage before publish'
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    png=[str(p.relative_to(ROOT)) for p in OUT.glob('*.png')]
    if png:subprocess.run(['git','add','-f','--',*png],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase15B depth safety and Graph pilot'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--publish',action='store_true');a=ap.parse_args()
    records,plan=load(a.run_root.resolve())
    if not OUT.exists():render(records,plan,OUT,DOC)
    else:
        assert DOC.exists() and json.loads((OUT/'runs.json').read_text())==records,'Existing different results preserved'
    if a.publish:publish()
    print(json.dumps(tables(records)[2]))
if __name__=='__main__':main()
