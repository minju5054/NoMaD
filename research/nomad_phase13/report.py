"""Reproducible report and explicit --publish: only Phase13 report/results are committed."""
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_phase4.report import write_csv
from nomad_phase8.report import markdown_table
from nomad_phase12.report import wilson
from nomad_phase0.chunk_report import trace
from .config import protocol
from .methods import METHODS, GF
from .batch import completion


def valid(r):
    return r.get('technical_validation') == 'PASS'


def load(root):
    state = completion(root)
    assert state['state'] == 'COMPLETE' and state['completed'] == 48
    plan = json.loads((root/'plan.json').read_text())
    assert plan['protocol'] == protocol()
    for name, h in plan['fixed_input_sha256'].items():
        assert sha256_file(Path(name)) == h, name
    records = []
    for j in plan['jobs']:
        r = json.loads((root/'metrics'/f"{j['key']}.json").read_text())
        assert all(r[k] == j[k] for k in ('key','method','index','seed_offset','delay_s','output'))
        if valid(r):
            assert r['execution_git_sha'] == plan['git_sha']
            for name, h in r['input_log_sha256'].items():
                assert sha256_file(Path(r['output'])/name) == h, name
        records.append(r)
    return records, plan


def paired(records, a, b):
    def eligible(m):
        return {r['index']:r for r in records if r['method']==m and valid(r) and r.get('checkpoint_time_s') is not None}
    aa, bb = eligible(a), eligible(b)
    ids = sorted(set(aa)&set(bb))
    diff = np.array([aa[i]['checkpoint_time_s']-bb[i]['checkpoint_time_s'] for i in ids])
    p = protocol()['decisions']
    ci = None
    if len(diff):
        rng = np.random.default_rng(p['bootstrap_seed'])
        boot = diff[rng.integers(0,len(diff),(p['bootstrap_replicates'],len(diff)))].mean(axis=1)
        ci = np.quantile(boot,[.025,.975]).tolist()
    verdict = 'INCONCLUSIVE' if len(diff)<8 else 'FASTER' if ci[1]<0 else 'SLOWER' if ci[0]>0 else 'INCONCLUSIVE'
    successes = lambda m: sum(bool(r['success']) for r in records if r['method']==m and valid(r))
    return dict(method=a, comparator=b, n=len(ids), paired_indices=ids,
        mean_difference_s=float(diff.mean()) if len(diff) else None, ci95_s=ci, verdict=verdict,
        noninferior='NONINFERIOR' if successes(a)>=successes(b)-2 else 'NOT_NONINFERIOR', differences_s=diff.tolist())


def tables(records):
    groups = []
    for m in METHODS:
        attempted = [r for r in records if r['method']==m]
        rs = [r for r in attempted if valid(r)]
        def avg(key, data=None):
            vals = [r[key] for r in (rs if data is None else data) if r.get(key) is not None]
            return float(np.mean(vals)) if vals else None
        def med(key, data=None):
            vals = [r[key] for r in (rs if data is None else data) if r.get(key) is not None]
            return float(np.median(vals)) if vals else None
        successes = [r for r in rs if r['success']]
        calls = sum(r.get('graph',{}).get('calls',0) for r in rs)
        accepted = sum(r.get('graph',{}).get('dispositions',{}).get('ACCEPTED',0) for r in rs)
        solve = [v for r in rs for v in r.get('graph',{}).get('solver_samples_s',[])]
        groups.append(dict(method=m,planned=12,attempted=len(attempted),valid=len(rs),technical=len(attempted)-len(rs),
            success=len(successes),success_wilson95=wilson(len(successes),len(rs)),
            checkpoint_count=sum(r.get('checkpoint_time_s') is not None for r in rs),
            checkpoint_median_s=med('checkpoint_time_s'),goal_time_median_s=med('goal_time_s',successes),
            checkpoint_mean_speed_m_s=avg('checkpoint_mean_speed_m_s'),curv_slow_time_fraction=avg('curv_slow_time_fraction'),
            endpoint_clamp_fraction=avg('endpoint_clamp_fraction'),
            minimum_clearance_m=min((r['minimum_obstacle_clearance_m'] for r in rs if r.get('minimum_obstacle_clearance_m') is not None),default=None),
            graph_calls=calls,graph_accepted=accepted,graph_acceptance=accepted/calls if calls else None,
            solve_median_s=float(np.median(solve)) if solve else None,solve_p95_s=float(np.quantile(solve,.95)) if solve else None,
            nonconverged=sum(r.get('graph',{}).get('independent_nonconverged',0) for r in rs)))
    pairs = [paired(records,a,b) for a,b in protocol()['decisions']['pairs']]
    lookup = {(r['method'],r['comparator']):r for r in pairs}
    a,b,c = lookup[GF,METHODS[0]],lookup[GF,METHODS[1]],lookup[METHODS[0],METHODS[3]]
    if a['verdict']==b['verdict']=='FASTER' and a['noninferior']==b['noninferior']=='NONINFERIOR':
        label = 'SPEED_FROM_GRAPH'
    elif a['verdict']!='FASTER' and c['verdict']=='FASTER':
        label = 'SPEED_FROM_SELECTION'
    elif b['verdict']!='FASTER' and lookup[METHODS[1],METHODS[0]]['verdict']=='FASTER':
        label = 'SMOOTHING_SUFFICES'
    else:
        label = 'MIXED'
    return groups,pairs,label


def figures(records, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    lookup = {(r['index'],r['method']):r for r in records}
    colors = ['#4477AA','#EEAA33','#228833','#AA3377']
    fig,ax = plt.subplots(figsize=(11,4))
    for k,m in enumerate(METHODS):
        rs = sorted((r for r in records if r['method']==m),key=lambda r:r['index'])
        vals = []
        for r in rs:
            x = k+(r['index']-40.5)*.035
            t = r.get('checkpoint_time_s') if valid(r) else None
            if t is None:
                ax.scatter(x,0,facecolors='none',edgecolors=colors[k],marker='o')
            else:
                vals.append(t)
                ax.scatter(x,t,facecolors=colors[k] if r['success'] else 'none',edgecolors=colors[k],s=23)
        if vals:
            ax.plot([k-.22,k+.22],[np.median(vals)]*2,color='black',lw=3)
    ax.set(xticks=range(4),xticklabels=METHODS,ylabel='Checkpoint time (s)',title='Filled: goal success; open: failed run; open at 0: missing checkpoint (not zero time)')
    fig.tight_layout();fig.savefig(out/'checkpoint_time.png',dpi=160);plt.close(fig)
    fig,axes = plt.subplots(1,3,figsize=(12,4),sharey=True)
    for ax,m in zip(axes,(METHODS[0],METHODS[1],METHODS[3])):
        n=0
        for i in protocol()['indices']:
            a,b=lookup.get((i,GF)),lookup.get((i,m))
            if not a or not b or not valid(a) or not valid(b) or a.get('checkpoint_time_s') is None or b.get('checkpoint_time_s') is None:continue
            ax.plot([0,1],[b['checkpoint_time_s'],a['checkpoint_time_s']],'-o',alpha=.7,ms=3,label=str(i));n+=1
        ax.set(xticks=[0,1],xticklabels=[m,'GF'],title=f'Both-checkpoint pairs: {n}')
        ax.tick_params(axis='x',labelsize=8)
    axes[0].set_ylabel('Checkpoint time (s)');fig.tight_layout();fig.savefig(out/'paired_lines.png',dpi=160);plt.close(fig)
    candidates=[i for i in protocol()['indices'] if all((i,m) in lookup and valid(lookup[i,m]) and lookup[i,m].get('checkpoint_time_s') is not None for m in METHODS)]
    chosen=min(candidates) if candidates else None
    fig,ax=plt.subplots(figsize=(10,4))
    if chosen is None:
        ax.text(.05,.5,'No seed with all four observed checkpoints',transform=ax.transAxes)
    else:
        for m,color in zip(METHODS,colors):
            r=lookup[chosen,m]
            if 'plot_xy' in r:xy=np.asarray(r['plot_xy'])  # Synthetic report fixture only.
            else:_,xy=trace(Path(r['output']))
            ax.plot(xy[:,0],xy[:,1],label=m,color=color)
        scene=json.loads((ROOT/protocol()['scenario']).read_text())
        for box in scene['obstacles']:
            x,y=box['center_xy_m'];sx,sy=box['size_xyz_m'][:2]
            ax.add_patch(Rectangle((x-sx/2,y-sy/2),sx,sy,color='gray',alpha=.35))
        for y in (-scene['corridor']['half_width'],scene['corridor']['half_width']):ax.axhline(y,color='black',lw=.7)
        ax.axvline(lookup[chosen,GF]['checkpoint_x_m'],color='black',ls=':',label='Checkpoint')
        ax.set(xlabel='World X (m)',ylabel='World Y (m)',title=f'Seed index {chosen}: actual recorded paths')
        ax.set_aspect('equal');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'paths.png',dpi=160);plt.close(fig)
    return chosen


def generate(records, plan, out, doc, synthetic=False):
    assert not out.exists() and not doc.exists(), 'Existing report/results preserved'
    assert len(records)==48 and len({(r['index'],r['method']) for r in records})==48
    groups,pairs,label=tables(records)
    out.mkdir(parents=True,exist_ok=False)
    chosen=figures(records,out)
    flat=[{k:v for k,v in r.items() if k not in ('input_log_sha256','mechanisms','traceback')} for r in records]
    write_json(out/'runs.json',flat)
    write_csv(out/'summary.csv',groups);write_csv(out/'paired.csv',pairs)
    write_json(out/'summary.json',dict(execution_git_sha=plan['git_sha'],protocol=protocol(),groups=groups,pairs=pairs,label=label,overlay_index=chosen,synthetic=synthetic))
    write_json(out/'input_hashes.json',{r['key']:r.get('input_log_sha256',{}) for r in records})
    paired_rows=[dict(index=i,**{m:next(r['classification'] for r in records if r['index']==i and r['method']==m) for m in METHODS}) for i in protocol()['indices']]
    failures=[dict(key=r['key'],error=r.get('error','')) for r in records if not valid(r)]
    lines=['# Phase 13 — oracle-free speed decomposition','',f"Execution SHA: `{plan['git_sha']}`. {'SYNTHETIC TEST ONLY' if synthetic else '48 serial attempts, 12 per method; no retries or skipped technical gates.'}",'',
        'Same S0, D750, vmax0.3, alpha infinity, PP+CURV, 4/9/72Hz, 1s timeout, 90s limit. No obstacle or wall coordinates enter any controller. Oracle geometry is evaluation-only. GF and ACT temporal ensembling (spatial adaptation) reuse the unchanged Phase12 implementations.', '',
        'Checkpoint: first recorded72Hz robot x >= StaticObstacle2 center_x + size_x/2 +0.30m, read from the scenario. Missing checkpoint/goal times are never replaced by timeout. Checkpoint average speed includes initial waiting. Curvature slowdown is the duration-weighted fraction of moving control intervals with target speed<0.2. Endpoint clamp retains the Phase12 control-tick definition. Minimum obstacle clearance includes the robot footprint.','',
        '## Method summary','']
    lines+=markdown_table(groups,list(groups[0]))
    lines+=['','## Seed × method','']+markdown_table(paired_rows,['index',*METHODS])
    lines+=['','## Paired checkpoint difference','', 'Difference = first method minus comparator, seconds. Both-checkpoint pairs only; 20,000 paired bootstrap replicates, seed20261026. FASTER: n>=8 and upper CI<0; SLOWER: n>=8 and lower CI>0; otherwise INCONCLUSIVE. NONINFERIOR is only the preregistered success-count tolerance, not a statistical noninferiority test. Wilson intervals describe valid-run success; technical failures are separate.','']
    lines+=markdown_table(pairs,['method','comparator','n','mean_difference_s','ci95_s','verdict','noninferior'])
    lines+=['','## Preregistered conclusion','',f'`{label}`','', 'Rules are evaluated in protocol order: GRAPH, SELECTION, SMOOTHING, otherwise MIXED. Matching seeds do not imply matching closed-loop RGB/predictions. These component comparisons are limited to this scene and seed set.','', '## Technical failures','']
    lines+=markdown_table(failures,['key','error']) if failures else ['None.']
    for name in ('checkpoint_time','paired_lines','paths'):
        lines+=['',f'![{name}](../research/results/phase13/{name}.png)']
    doc.parent.mkdir(parents=True,exist_ok=True);doc.write_text('\n'.join(lines)+'\n')
    return label


def publish(out,doc):
    """Explicit user-authorized normal push; no broad staging or history rewrite."""
    assert out.resolve()==(ROOT/protocol()['results']).resolve() and doc.resolve()==(ROOT/protocol()['report']).resolve()
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    assert git('branch','--show-current')=='research/phase0-infrastructure'
    assert git('remote','get-url','origin') in ('https://github.com/minju5054/NoMaD.git','git@github.com:minju5054/NoMaD.git')
    assert not git('diff','--cached','--name-only'), 'Unrelated staged changes must not be committed'
    intended={str(doc.relative_to(ROOT)),*(str(f.relative_to(ROOT)) for f in out.iterdir() if f.is_file())}
    for name in git('diff','--name-only').splitlines():assert name in intended, 'Unrelated tracked edit: '+name
    git('add','--',str(doc.relative_to(ROOT)),str(out.relative_to(ROOT)))
    git('add','-f','--',*[str(f.relative_to(ROOT)) for f in sorted(out.glob('*.png'))])
    staged=set(git('diff','--cached','--name-only').splitlines())
    assert staged<=intended
    if staged:
        git('-c','core.whitespace=cr-at-eol','diff','--cached','--check')
        git('-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Record Phase 13 speed decomposition results')
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
    return git('rev-parse','--short','HEAD')


def main():
    ap=argparse.ArgumentParser();src=ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--run-root',type=Path);src.add_argument('--runs-json',type=Path,help='Synthetic fixture only; cannot publish')
    ap.add_argument('--out',type=Path);ap.add_argument('--doc',type=Path);ap.add_argument('--publish',action='store_true')
    a=ap.parse_args();out=a.out or ROOT/protocol()['results'];doc=a.doc or ROOT/protocol()['report']
    if a.runs_json:
        assert not a.publish and a.out and a.doc
        records=json.loads(a.runs_json.read_text());plan=dict(git_sha='SYNTHETIC')
    else:records,plan=load(a.run_root.resolve())
    manifest=out/'report_files.json'
    if out.exists() or doc.exists():
        # Allows a failed network push to be retried without rewriting results.
        assert a.publish and manifest.exists(), 'Existing report preserved'
        lock=json.loads(manifest.read_text());assert lock['execution_git_sha']==plan['git_sha']
        assert lock['run_root']==str(a.run_root.resolve())
        for name,h in lock['sha256'].items():assert sha256_file(ROOT/name)==h,name
        label=json.loads((out/'summary.json').read_text())['label']
    else:
        label=generate(records,plan,out,doc,synthetic=bool(a.runs_json))
        if not a.runs_json:
            write_json(manifest,dict(execution_git_sha=plan['git_sha'],run_root=str(a.run_root.resolve()),
                sha256={str(f.relative_to(ROOT)):sha256_file(f) for f in [doc,*sorted(out.iterdir())] if f.is_file()}))
    sha=publish(out,doc) if a.publish else None
    print(json.dumps(dict(label=label,commit=sha,report=str(doc))))


if __name__=='__main__':main()
