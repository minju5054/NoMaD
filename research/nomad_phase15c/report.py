"""Report saved offline diagnostics; never performs a Graph solve."""
import json
import csv
import subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase15b.depth import Snapshot

DOC=ROOT/'docs/PHASE15C_DIAGNOSIS.md'


def table(rows, keys=None):
    if not rows:return 'None.'
    keys=keys or list(rows[0])
    def fmt(x):
        if isinstance(x,float):return f'{x:.6g}'
        if isinstance(x,(dict,list)):return json.dumps(x,ensure_ascii=False)
        return '—' if x is None else str(x).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(keys)+' |','| '+' | '.join(['---']*len(keys))+' |']+
                     ['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])


def figures(out,data,summary,dispersion,walls):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from .diagnose import DEPTH,GF
    def scene(ax,c):
        for box in c['obstacles']:
            x,y=box['center_xy_m'];w,h=box['size_xyz_m'][:2]
            ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='.45',alpha=.5))
        ax.axhline(c['corridor']['half_width'],color='black',ls='--',label='Oracle wall (evaluation)')
        ax.axhline(-c['corridor']['half_width'],color='black',ls='--')
        ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
    for index in (47,49):
        d=data[DEPTH,index];rows=[r for r in walls if r['index']==index];last=next(r for r in rows if r['is_final_active'])
        field=Snapshot.load(last['snapshot_file']);fig,ax=plt.subplots(figsize=(10,6))
        y,x=np.nonzero(field.occupied);points=field.origin+np.column_stack([x,y])*field.h
        ax.scatter(points[:,0],points[:,1],s=1,c='.75',label='Depth occupancy at final path application')
        scene(ax,d['config']);p=d['poses'];start=min(r['application_tick'] for r in rows)
        ax.plot(p[:,0],p[:,1],color='black',lw=1,label='Actual motion')
        ax.plot(p[start:,0],p[start:,1],color='black',lw=2.5)
        for i,r in enumerate(rows):
            xy=np.array(r['raw_world_xy']);ax.plot(xy[:,0],xy[:,1],marker='.',ls='-' if r['kind']=='GRAPH' else '--',label=f"F{r['id']} {r['kind']} t={r['application_time_s']:.2f}")
            a=d['poses'][r['application_tick']];ax.scatter(*a[:2],marker='x',s=25)
        ax.scatter(*p[-1,:2],marker='X',c='red',s=80,label='Footprint stop')
        ax.add_patch(plt.Circle(p[-1,:2],.09,color='red',fill=False))
        ax.set_xlim(min(p[start:,0].min(),min(np.array(r['raw_world_xy'])[:,0].min() for r in rows))-.3,max(p[start:,0].max(),max(np.array(r['raw_world_xy'])[:,0].max() for r in rows))+.3)
        ax.set_ylim(min(p[start:,1].min()-.4,1.),1.65)
        ax.set_title(f"GRAPH-depth seed {index}: {last['run_cause']}");ax.legend(fontsize=7,loc='best');fig.tight_layout();fig.savefig(out/f'wall_{index}.png',dpi=150);plt.close(fig)
    for r in summary['detour_comparisons']:
        fig,ax=plt.subplots(figsize=(10,5));scene(ax,data[GF,r['index']]['config'])
        for m,color,label in ((GF,'tab:blue','SAFE+GRAPH-GF'),(DEPTH,'tab:orange','SAFE+GRAPH-depth')):
            p=data[m,r['index']]['poses'];ax.plot(p[:,0],p[:,1],c=color,label=label)
            ax.scatter(*p[-1,:2],c=color,marker='x')
        p=data[GF,r['index']]['poses'];tick=round(r['detour_start_s']*72)
        ax.scatter(*p[tick,:2],c='red',marker='o',label=f"GF detour onset {tick/72:.2f}s")
        a=max(0,tick-360);b=min(len(p),tick+361);ax.plot(p[a:b,0],p[a:b,1],color='tab:blue',lw=3)
        ax.set_title(f"Seed {r['index']}: {r['cause']} (different closed-loop observations)");ax.legend(fontsize=8)
        fig.tight_layout();fig.savefig(out/f"detour_{r['index']}.png",dpi=150);plt.close(fig)
    rows=summary['sigma_summary'][1:];fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    x=np.arange(len(rows));axes[0].bar(x,[r['acceptance_change_pp'] for r in rows]);axes[0].axhline(5,c='red',ls='--');axes[0].axhline(-5,c='red',ls='--');axes[0].set_ylabel('Acceptance change (pp)')
    axes[1].bar(x,[100*r['path_difference_median_m'] if r['path_difference_median_m'] is not None else np.nan for r in rows]);axes[1].axhline(2,c='red',ls='--');axes[1].set_ylabel('Median path change (cm)');axes[1].set_xticks(x,[r['sigma'] for r in rows],rotation=25)
    axes[0].set_title('Frozen sigma sensitivity; all returned paired iterates (including rejected)');fig.tight_layout();fig.savefig(out/'sigma_sensitivity.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4));summary_rows=[]
    for m,color in ((DEPTH,'tab:orange'),(GF,'tab:blue')):
        med=[];lo=[];hi=[]
        for i in range(8):
            rr=[r for r in dispersion if r['source_method']==m and r['waypoint']==i]
            v=np.array([r['rms_axis_std_m'] for r in rr]);q=np.quantile(v,[.1,.5,.9]);lo.append(q[0]);med.append(q[1]);hi.append(q[2])
            summary_rows.append(dict(source_method=m,waypoint=i,n=len(rr),median_m=float(q[1]),p10_m=float(q[0]),p90_m=float(q[2]),fixed_sigma_m=.1))
        ax.plot(range(8),med,marker='o',color=color,label=m);ax.fill_between(range(8),lo,hi,color=color,alpha=.15)
    ax.axhline(.1,color='black',ls='--',label='Fixed per-axis prior sigma 0.10m');ax.set_xlabel('Waypoint index');ax.set_ylabel('RMS per-axis sample std (m)');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/'dispersion.png',dpi=150);plt.close(fig)
    from .diagnose import write_csv
    write_csv(out/'dispersion_summary.csv',summary_rows)
    return summary_rows


def render(out,data,summary,ablation,sensitivity,dispersion,walls,detours):
    from .diagnose import RULES,DEPTH,GF
    if DOC.exists():raise FileExistsError(DOC)
    ds=figures(out,data,summary,dispersion,walls)
    reg=json.loads((out/'input_manifest.json').read_text());comparable=summary['regression_comparable'];mismatch=summary['regression_mismatches']
    text='# Phase 15-C — depth Graph offline diagnosis\n\n'
    text+='Offline path-level mechanism validation only. No navigation, NoMaD inference, rendering, controller rollout, tuning, or retries. Oracle boxes/walls are used only after solving, for evaluation and attribution. Actual historical execution remains distinct from counterfactual paths.\n\n'
    text+=f"Execution Git SHA: `{reg['git_sha']}`. Graph-depth 209 jobs and Graph-GF 460 jobs; {summary['solve_attempts']} single attempts. Each A variant solved once; D baseline reuses A FULL. Original selected sample, B, previous actual command, previous accepted path, and immutable snapshot are retained; no hypothetical prior propagation.\n\n"
    text+='## Replay and measurement scope\n\n'
    text+=f"Comparable saved worker results: {comparable}; mismatches: {mismatch}/{comparable} ({100*mismatch/comparable:.3f}%); unavailable: {summary['regression_unavailable']} terminal-unapplied job without a saved worker result. Compare XY maximum point error ≤1e−6 m, numerical disposition, and logged disposition under the saved scheduling conditions. New offline solve times do not replace historical STALE/SUPERSEDED decisions. All comparisons carry regression flags; none are silently omitted. Full poses, solver diagnostics and errors are preserved in `solve_results.jsonl`.\n\n"
    text+='CERT_ONLY changes only acceptance of the GF solution. CONSTRAINT_ONLY removes only the post-solve exact certificate; FULL is original DepthGraph. Sigma variants change only XY/yaw residual scales after unchanged native initialization. SLSQP, analytic derivatives, tolerances, constraints and all other weights are unchanged.\n\n'
    text+='## A — constraint versus certificate\n\n'
    text+=f"**{summary['A']}**. Fewer than five dangerous NEITHER corrections has priority and yields NO_DANGEROUS_CORRECTIONS. A dangerous correction is accepted NEITHER with full-path oracle clearance <0.025m, including walls.\n\n"
    text+=table(summary['ablation_summary'],['source_method','variant','jobs','accepted','oracle_unsafe_accepted','dangerous_neither','CERT_ONLY_rejected','CERT_ONLY_unsafe_accepted','CONSTRAINT_ONLY_safe','FULL_safe','label'])+'\n\n'
    text+='`ablation_jobs.csv` records every dangerous transfer (rejected, safe accepted, unsafe accepted), depth/oracle clearance, edit, curvature, endpoint progress and solve time. Failed final iterates are diagnostic only; accepted_* fields are empty for rejected solutions. These counts do not establish safer closed-loop navigation.\n\n'
    text+='## B — wall stops\n\n'
    text+='`nomad_isaac/clearance.py:115–120,153–169`: corridor lower bound = minimum endpoint distance to xmin/xmax/±half_width minus robot radius 0.09m, arc sagitta, and 1e−12m. `corridor_footprint_stop` occurs at bound ≤0, not at 2cm or 2.5cm. The 2cm required obstacle clearance is recorded separately and is not this stop threshold. Thus the evaluator does not require a larger wall margin than Graph-depth’s 0.025m constraint. A conservative lower bound can stop before exact overlap; it is not automatically a physical wall collision.\n\n'
    text+='Rows cover the last three FRESH switches and all actual Graph replacements within them. Path metrics use the B-projected suffix; full-path depth clearance is also retained. Depth wall-site distance is an attribution diagnostic using occupied sites within 0.10m of the oracle wall, not a solver input. Unknown classification uses the exact nearest wall grid cell in the latest map published before stop; its 5×5 neighborhood is reported to expose discretization sensitivity.\n\n'
    text+=table(walls,['index','id','application_time_s','kind','is_final_active','all_unsafe','depth_clearance_m','depth_wall_sites_clearance_m','oracle_wall_clearance_m','path_unknown_fraction','wall_observed','wall_neighborhood_observed','actual_corridor_lower_m','path_minus_actual_wall_clearance_m','max_cross_track_m','run_cause'])+'\n\n'
    for index,label in summary['B'].items():
        a=next(r for r in walls if str(r['index'])==index and r['is_final_active'])
        text+=f"- Seed {index}: **{label}**, final active {a['kind']} F{a['id']}; depth {a['depth_clearance_m']:.4f}m, oracle wall {a['oracle_wall_clearance_m']:.4f}m, actual corridor lower bound {a['actual_corridor_lower_m']:.4f}m.\n"
    text+='\nSame-seed methods at the nearest spatial position (not temporal or prediction correspondence):\n\n'+table(summary['wall_comparisons'],['index','method','classification','nearest_time_s','nearest_pose','distance_to_diagnostic_location_m','minimum_corridor_clearance_m'])+'\n\n'
    text+='## C — GF detours\n\n'
    text+='Onset is first 0.30m backtrack from running maximum x, otherwise first accumulated absolute yaw change >2π. The ±5s window uses actual FRESH switches; consecutive tests operate on consecutive switches in this window. ALL_UNSAFE includes the 0.10m/s target cap and takes precedence. Rejected solver iterates are explicitly not executed paths. Labels are temporal associations under the requested priority, not proven causes.\n\n'
    text+=table(summary['detour_comparisons'])+'\n\n'
    text+=table(detours,['index','id','switch_time_s','disposition','previous_v','all_unsafe','remaining_length_m','endpoint_clamp_fraction','corrected_actually_applied','corrected_depth_clearance_m','corrected_oracle_clearance_m','endpoint_direction_change_deg','run_cause'])+'\n\n'
    for r in summary['detour_comparisons']:
        text+=f"- Seed {r['index']}: **{r['cause']}** at {r['detour_start_s']:.3f}s; GF distance {r['gf_distance_m']:.2f}m, same-seed depth {r['depth_result']} / {r['depth_distance_m']:.2f}m. Observations and timings differ across runs.\n"
    text+='\n## D — sigma sensitivity\n\n'
    text+=f"**{summary['D']}**. Single-family settings exceeding a threshold: {', '.join(summary['sigma_exceeded']) or 'none'}. Acceptance denominator is all 209 jobs. Path differences use every pair of returned finite iterates (including rejected candidates); no path is invented for initialization rejection. Accepted-both subset is also shown. ROBUST requires all six single-family changes ≤5 percentage points and median per-job median point difference ≤0.02m. Combined-family settings are descriptive.\n\n"
    text+=table(summary['sigma_summary'])+'\n\n'
    text+='Sample dispersion uses all actual FRESH switches of these 16 Graph runs, eight native samples per observation anchored to the same observation pose; ddof=0. RMS per-axis std = sqrt((std_x²+std_y²)/2), compared to per-axis sigma 0.10m. Radial std and separate x/y are in sample_dispersion.csv. This is preparation for a later adaptive-sigma design, not an adaptive policy.\n\n'+table(ds)+'\n\n'
    text+='## Figures\n\n'
    for image in sorted(out.glob('*.png')):text+=f'![{image.stem}](../research/results/phase15c/{image.name})\n\n'
    text+='## Frozen measurement rules\n\n```json\n'+json.dumps(RULES,indent=2)+'\n```\n\n'
    text+='Labels: '+json.dumps({k:summary[k] for k in ('A','B','C','D')})+'\n'
    DOC.write_text(text)
    add_interpretation_notes(out)


def add_interpretation_notes(out):
    """Explain recorded failure/fallback semantics without any new solve or label change."""
    marker='## Interpretation limits from the recorded execution'
    text=DOC.read_text()
    if marker in text:return
    summary=json.loads((out/'summary.json').read_text())
    walls=list(csv.DictReader((out/'wall_failures.csv').open()))
    notes=marker+'\n\n'
    a=summary['ablation_summary'][0]
    notes+=f"A contains {a['dangerous_neither']} dangerous accepted NEITHER paths, not zero. The <5 evidence rule controls the label. CERT_ONLY rejects {a.get('CERT_ONLY_rejected',0)}; constraints recover {a.get('CONSTRAINT_ONLY_safe',0)}; this sample is too small for CONSTRAINT_MATTERS under the frozen rule.\n\n"
    for r in walls:
        if r['is_final_active']!='True':continue
        notes+=f"Seed {r['index']}: the final active path is **{r['kind']} F{r['id']}**, not an accepted Graph replacement; ALL_UNSAFE={r['all_unsafe']}. "
        if r['run_cause']=='EXECUTION':
            notes+=f"Path-to-motion maximum cross-track is {float(r['max_cross_track_m']):.3f}m. Path safety therefore does not certify the actual PP arc or its connection from the current robot pose. "
        if r['run_cause']=='DEPTH_ERROR' and float(r['depth_clearance_m'])<.025:
            notes+='The depth map already marks this path unsafe: this is **not a depth-only-safe false acceptance**. ALL_UNSAFE still executes the least-unsafe original sample under its speed cap. In addition, occupied-site distance is not signed penetration into a solid wall: its minimum is bounded below by −robot_radius, whereas oracle half-plane clearance continues decreasing outside the corridor. The requested DEPTH_ERROR label includes this representation discrepancy and does not isolate sensor noise as the cause. '
        notes+='\n\n'
    notes+='C labels follow the requested priority in the ±5s onset window. OTHER does not establish that Graph was uninvolved; no causal intervention was run.\n\n'
    combined=[r for r in summary['sigma_summary'] if r['sigma'].startswith('all_') and not r['within_threshold']]
    notes+='D ROBUST refers only to the six single-family settings and the specified aggregate median. '
    if combined:notes+='Combined changes exceeding a descriptive threshold: '+', '.join(f"{r['sigma']} ({r['acceptance_change_pp']:.2f}pp acceptance)" for r in combined)+'. '
    notes+='Individual path tails and combined perturbations are not guaranteed robust.\n\n'
    # Preserve all existing tables, numerical output and final label line.
    before,labels=text.rsplit('Labels: ',1)
    DOC.write_text(before+notes+'Labels: '+labels)


def publish():
    add_interpretation_notes(ROOT/'research/results/phase15c')
    paths=['research/nomad_phase15c','research/results/phase15c','docs/PHASE15C_DIAGNOSIS.md']
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    png=list((ROOT/'research/results/phase15c').glob('*.png'))
    if png:subprocess.run(['git','add','-f','--',*[str(p.relative_to(ROOT)) for p in png]],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():
        subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase 15C depth Graph ablations, failures and sigma sensitivity'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
