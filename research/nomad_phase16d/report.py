"""Tables/figures from the one offline diagnostic pass; narrow publication scope."""
import json,subprocess
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,local_to_world
from nomad_phase15b.depth import Snapshot,evaluate_samples
from nomad_phase15.evaluate import suffix
from nomad_phase16.geometry import rect
DOC=ROOT/'docs/PHASE16D_DEADLOCK.md'

def table(rows,keys=None):
    if not rows:return 'None.'
    keys=keys or list(rows[0])
    def fmt(v):
        if isinstance(v,float):return f'{v:.6g}'
        if v is None:return '—'
        if isinstance(v,(dict,list)):return json.dumps(v,ensure_ascii=False)
        return str(v).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(keys)+' |','| '+' | '.join(['---']*len(keys))+' |']+['| '+' | '.join(fmt(r.get(k)) for k in keys)+' |' for r in rows])

def figures(out,summary,runs,events,data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    from .diagnose import DEPTH,SAFE,GF,clearance
    def obstacles(ax,c):
        for box in c['obstacles']:
            x,y=box['center_xy_m'];w,h=box['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,facecolor='.6',edgecolor='black',alpha=.4))
        x0,x1,y0,y1=rect(c);ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor='black'))
        ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
    labels={r['run']:r['cause'] for r in runs}
    for item in summary['plot_records']:
        d=data[item['split'],item['scene'],item['index'],item['method']];e=next(x for x in d['events'] if x['id']==item['representative_id']);B=np.array(e['agent_pose_at_switch'])
        meta=e.get('phase16',{}).get('selection',{}).get('snapshot',e['depth_snapshot']);field=Snapshot.load(meta['file'])
        worlds=np.array([local_to_world(np.array(x),e['observation_pose']) for x in e['overnight_metric_samples']]);_,decision=evaluate_samples(worlds,B,field)
        paths=[suffix(x,B)[0] for x in worlds];allxy=np.vstack(paths)
        half=np.maximum(.45,np.max(np.abs(allxy-B[:2]),axis=0)+.15);lower=B[:2]-half;upper=B[:2]+half
        lo=np.maximum(0,np.floor((lower-field.origin)/field.h).astype(int));hi=np.minimum(field.values.shape[::-1],np.ceil((upper-field.origin)/field.h).astype(int)+1)
        xs=field.origin[0]+np.arange(lo[0],hi[0])*field.h;ys=field.origin[1]+np.arange(lo[1],hi[1])*field.h
        z=field.values[lo[1]:hi[1],lo[0]:hi[0]]-field.error_bound
        fig,ax=plt.subplots(figsize=(10,6));obstacles(ax,d['config'])
        yy,xx=np.nonzero(field.occupied);points=field.origin+np.column_stack([xx,yy])*field.h;inside=np.all((points>=lower)&(points<=upper),axis=1)
        ax.scatter(points[inside,0],points[inside,1],s=1,c='black',alpha=.5,label='Depth occupied cells')
        if z.size and z.min()<=.025<=z.max():ax.contour(xs,ys,z,levels=[.025],colors=['darkorange'],linewidths=1)
        for i,(path,candidate) in enumerate(zip(paths,decision['candidates'])):
            oc=clearance(path,d['config']);ax.plot(path[:,0],path[:,1],marker='.',lw=1.2,label=f"s{i}: depth {100*candidate['clearance_m']:.1f}, oracle {100*oc:.1f} cm")
        ax.plot(d['poses'][:,0],d['poses'][:,1],color='.25',lw=1,alpha=.65)
        ax.scatter(*B[:2],c='red',s=70,marker='x',label=f"B, F{e['id']}, t={e['application_sim_s']:.2f}s")
        ax.add_patch(Circle(B[:2],.09,fill=False,color='red'));ax.add_patch(Circle(B[:2],.115,fill=False,color='red',ls=':'))
        ax.set_xlim(lower[0],upper[0]);ax.set_ylim(lower[1],upper[1])
        label=labels.get(item['run'],'OUTSIDE A: plot only')
        ax.set_title(f"{item['scene']} {item['index']} | {label}\n{item['method']} | depth pass threshold = 2.5 cm; orange = conservative point contour",fontsize=10)
        ax.legend(fontsize=7,loc='upper left',bbox_to_anchor=(1.01,1.));fig.tight_layout();fig.savefig(out/f"deadlock_{item['scene']}_{item['method']}_{item['index']}.png",dpi=150);plt.close(fig)
    for b in summary['B_details']:
        fig,ax=plt.subplots(figsize=(11,5));d=data['main','CL',b['index'],DEPTH];obstacles(ax,d['config']);B=np.array(b['B'])
        for method,color,name in ((DEPTH,'tab:orange','GRAPH-depth'),(SAFE,'tab:blue','SAFE'),(GF,'tab:green','GRAPH-GF')):
            p=data['main','CL',b['index'],method]['poses'];ax.plot(p[:,0],p[:,1],color=color,label=name)
        ax.scatter(*B[:2],c='red',marker='x',s=80,label='GRAPH-depth first STOP_WAIT');ax.add_patch(Circle(B[:2],.3,fill=False,color='red',ls='--'))
        for comp in b['comparisons']:
            if comp['entered_radius']:
                ax.scatter(*np.array(comp['entry_pose'])[:2],marker='o',facecolors='none',edgecolors='black')
                ax.scatter(*np.array(comp['closest_pose'])[:2],marker='^',facecolors='none',edgecolors='black')
        x0,x1,y0,y1=rect(d['config']);ax.set_xlim(x0-.1,x1+.1);ax.set_ylim(y0-.1,y1+.1);ax.legend(fontsize=8)
        ax.set_title(f"CL seed {b['index']}: {b['cause']} | circles: first neighborhood entry, triangles: nearest pose")
        fig.tight_layout();fig.savefig(out/f"approach_CL_{b['index']}.png",dpi=150);plt.close(fig)


def render(out,summary,runs,events,brows,gates,escapes,data):
    from .diagnose import RULES
    assert not DOC.exists(),'Existing report preserved'
    figures(out,summary,runs,events,data)
    import matplotlib.pyplot as plt
    ss=[r for r in escapes if r['split']=='ALL'];fig,axes=plt.subplots(1,2,figsize=(10,4));names=[r['candidate'] for r in ss]
    colors=['tab:green' if r['penetrating_selections']==0 else 'tab:red' for r in ss]
    axes[0].bar(names,[r['escape_fraction']*100 for r in ss],color=colors);axes[0].axhline(50,color='black',ls='--');axes[0].set_ylabel('Path-selection escape (%)');axes[0].set_ylim(0,105)
    axes[1].bar(names,[r['penetrating_selections'] for r in ss],color=colors);axes[1].set_ylabel('Oracle-negative selected paths')
    fig.suptitle('Offline decisions only; no rollout. Green = zero penetrating selections.');fig.tight_layout();fig.savefig(out/'escape_summary.png',dpi=150);plt.close(fig)
    text='# Phase 16-D — STOP_WAIT deadlock diagnosis and offline rule selection\n\n'
    text+='Saved inputs only: no simulation, NoMaD inference, rendering, Graph solve, controller execution, or rollout. Oracle boxes/walls enter only the evaluator. Candidate selection functions receive only depth clearances, remaining lengths and B depth clearance. All native paths remain observation-pose anchored.\n\n'
    manifest=json.loads((out/'input_manifest.json').read_text())
    text+=f"Analysis Git SHA: `{manifest['execution_git_sha']}`. Inventory: 72 main runs + 6 gate runs. A/D include {summary['main_selected']} main runs with STOP_WAIT time fraction strictly >20%, plus {summary['gate_selected']} SL gates: {summary['stop_events']} STOP_WAIT events. Other runs remain in inventory.csv.\n\n"
    text+='## A — run causes and persistence\n\n'
    text+='STOP_WAIT is a controller decision, not proof that velocity is already zero: deceleration may still be in progress. B values and actual speed are recorded at the applied FRESH boundary. Depth clearance uses the existing selector’s conservative h/√2 bound; the B point has no segment-spacing allowance. B nominal/exact-site/oracle values are also retained. “Best oracle sample” means the maximum exact oracle clearance across all eight; the oracle value of the depth-best sample is separate.\n\n'
    text+=table(runs,['split','scene','index','method','stop_events','cause','marginal_fraction','true_block_fraction','near_start_fraction','depth_false_close_fraction','max_consecutive_STOP_WAIT','longest_chain_event_span_s','sample_change_consecutive_median_m','robot_movement_consecutive_median_m','active_path_short_rejections'])+'\n\n'
    text+='Sample changes are mean distances between same-index 8×8 arrays in world coordinates, not physical trajectory correspondences. Consecutive medians exclude intervening NORMAL/KEEP_ACTIVE decisions; all-stop-pair and stationary-pair medians are retained in runs.csv. Near/far risk uses Euclidean radius 0.30m from B and can occur in both regions.\n\n'
    text+='NEAR_START_POSE is a depth-map diagnosis, not automatically true physical proximity: depth_false_close_fraction reports events where depth B <2.5cm while oracle B ≥2.5cm. TRUE_BLOCK refers to the eight saved predictions, not geometric impossibility of the scene. MARGINAL_DEADLOCK establishes native nonpenetration, not a 2.5cm safety margin or safe PP execution.\n\n'
    for r in runs:
        text+=f"- {r['run']} ({r['split']}): **{r['cause']}**, {r['stop_events']} stop decisions, longest consecutive chain {r['max_consecutive_STOP_WAIT']}; consecutive sample-change median {r['sample_change_consecutive_median_m']}m, movement median {r['robot_movement_consecutive_median_m']}m.\n"
    text+='\nThe current Phase16 implementation does not dispatch a new Graph job for ALL_UNSAFE/STOP_WAIT. Graph-dispatch counts during these stop events are recorded rather than assuming the optimizer attempted recovery. Short safe active suffixes (<0.25m) can also rule out KEEP_ACTIVE; these are reported separately without changing the requested label priority.\n\n'
    text+='## B — CL matched-seed comparison\n\n'
    text+='The first entry into the 0.30m neighborhood and the closest recorded pose are both logged. GRAPH_APPROACH_CLOSER uses the closest SAFE pose within that neighborhood, requires that the immediately preceding active path lineage was corrected, and compares point oracle footprint clearance at the actual first-stop B. Entry-only and nearest-point differences are both reported. This is a spatial diagnostic across different closed-loop observations, not an identical-state intervention.\n\n'
    text+=table([r for r in brows if r['row_type']=='run_summary'],['index','cause','first_stop_id','first_stop_time_s','B','prior_active_path_kind','B_oracle_clearance_m','B_depth_clearance_m','safe_closest_minus_graph_B_m','safe_entry_minus_graph_B_m','certificate_revert'])+'\n\n'
    text+=table([r for r in brows if r['row_type']=='comparator'],['index','comparator_method','comparator_result','entered_radius','entry_time_s','entry_pose','entry_oracle_clearance_m','entry_depth_clearance_m','closest_time_s','closest_pose','closest_distance_to_B_m','closest_oracle_clearance_m','closest_depth_clearance_m'])+'\n\n'
    text+='Three preceding FRESH switches (original selection versus solver path; non-applied final iterates are diagnostic only):\n\n'
    text+=table([r for r in brows if r['row_type']=='preceding_switch'],['index','id','switch_time_s','actual_path_kinds','graph_disposition','corrected_actually_applied','raw_suffix_oracle_clearance_m','corrected_suffix_oracle_clearance_m','delta_oracle_clearance_m','delta_obstacle_clearance_m','corrected_execution_min_oracle_clearance_m','exact_certificate_pass','sole_certificate_rejection'])+'\n\n'
    text+='CERTIFICATE_REVERT requires a converged, constraint-satisfied candidate rejected solely by exact depth certification and an original path active at first stop. A nonconverged solve with a failing certificate, a constraint failure, or a stale result alone does not establish certificate-caused reversion. Corrected/raw path changes use the same job B suffix; actual execution clearance uses the saved 72Hz swept intervals only after real application.\n\n'
    for r in summary['B_details']:text+=f"- CL {r['index']}: **{r['cause']}**, first stop F{r['first_stop_id']} at {r['first_stop_time_s']:.3f}s; prior path {r['prior_active_path_kind']}.\n"
    text+='\n## C — SL D0 gate\n\n'+table(gates,['index','stop_events','cause','gate_cause','nonpenetrating_sample_available_events','nonpenetrating_sample_available_fraction','max_consecutive_STOP_WAIT','sample_change_consecutive_median_m'])+'\n\n'
    text+='The gate labels are restricted to these saved D0 runs. Oracle-nonpenetrating sample availability is evaluated at every STOP_WAIT event, not assumed from a new search.\n\n'
    text+='## D — fixed escape candidates\n\n'
    text+='E1 uses min(0.025, c_B−0.005) literally, including negative thresholds. E1/E2 choose the longest eligible remaining suffix, ties by lower sample index. E3 chooses maximum depth clearance, ties by lower index, matching Phase15B. E0 never selects a path. The hypothetical 0.10m/s cap is recorded but not executed or validated; B→path connection, braking and PP swept motion are not evaluated here.\n\n'
    text+=table(escapes,['split','candidate','events','selected','escape_fraction','penetrating_selections','near_selections','margin_met_selections'])+'\n\n'
    text+='Selection uses the pooled ALL rows, including higher-rate D0 gates; main/gate strata are descriptive only. A longer stop episode contributes more events. Zero oracle-negative paths is weaker than preserving the original 2.5cm safety margin. The explicit tie order is E1 > E2 > E3 > E0 (E0 is the zero-escape fallback).\n\n'
    text+='```json\n'+json.dumps(summary['selection'],indent=2)+'\n```\n\n'
    text+='This is rule selection and evaluation on the **same stored data**, with no holdout. Effectiveness must be judged in a later closed-loop experiment with new seeds. If INSUFFICIENT, in-place rotation is a next-study candidate, not implemented or evaluated here.\n\n'
    text+='## Figures\n\n'
    text+='Every main STUCK run and both SL gates have a plot. Plot-only cases outside A are explicitly marked and do not enter A labels or D selection. Within A, the middle event of the earliest longest STOP_WAIT chain is used. The orange depth contour is the conservative pointwise 2.5cm threshold; native segment tests additionally subtract the sampling-spacing bound. Red circles show radius 0.09m and radius+0.025m.\n\n'
    for p in sorted(out.glob('*.png')):text+=f'![{p.stem}](../research/results/phase16d/{p.name})\n\n'
    text+='## Frozen measurement rules\n\n```json\n'+json.dumps(RULES,indent=2)+'\n```\n'
    DOC.write_text(text)

def publish():
    paths=['research/nomad_phase16d','research/results/phase16d','docs/PHASE16D_DEADLOCK.md'];out=ROOT/paths[1]
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','add','--',*paths],cwd=ROOT,check=True)
    images=[str(p.relative_to(ROOT)) for p in out.glob('*.png')]
    if images:subprocess.run(['git','add','-f','--',*images],cwd=ROOT,check=True)
    if subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip():subprocess.run(['git','-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m','Report Phase16D STOP_WAIT diagnosis and offline escape selection'],cwd=ROOT,check=True)
    subprocess.run(['git','push','origin','HEAD:research/phase0-infrastructure'],cwd=ROOT,check=True)
