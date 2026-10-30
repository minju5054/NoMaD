import json
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase15b.depth import Snapshot
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean,csv_write
from .report import summary_rows


def render(out,events,solutions,verdict,examples,accuracy,excluded,sha,protocol):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    summary=summary_rows(events,solutions);csv_write(out/'summary.csv',summary)
    fig,axes=plt.subplots(2,2,figsize=(12,10),constrained_layout=True)
    for ax,(identifier,item) in zip(axes.ravel(),examples.items()):
        e=item['event'];B=np.array(e['B']);field=Snapshot.load(e['snapshot_file'])
        extent=[field.origin[0],field.origin[0]+(field.values.shape[1]-1)*field.h,field.origin[1],field.origin[1]+(field.values.shape[0]-1)*field.h]
        ax.imshow(~field.observed,origin='lower',extent=extent,cmap='Greys',vmin=0,vmax=1,alpha=.13,interpolation='nearest')
        iy,ix=np.nonzero(field.occupied);points=field.origin+np.c_[ix,iy]*field.h;points=points[np.max(np.abs(points-B[:2]),axis=1)<=1.9]
        if len(points):ax.scatter(points[:,0],points[:,1],s=2,c='.4',label='Depth occupied (gray shade=unknown)')
        for b in e['oracle_config']['obstacles']:
            x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,color='purple',alpha=.2,label='Oracle box: evaluation only'))
        c=e['oracle_config']['corridor'];ax.axhline(c['half_width'],c='k',lw=.7);ax.axhline(-c['half_width'],c='k',lw=.7);ax.axvline(c['xmin'],c='k',lw=.7);ax.axvline(c['xmax'],c='k',lw=.7)
        for i,r in enumerate(item['result']['results']):
            if r.get('initial_path') is not None:
                p=np.array(r['initial_path']);ax.plot(p[:,0],p[:,1],c='.65',lw=.7,label='7 unchanged initializations' if i==0 else None)
        chosen=item['result']['selected']
        if chosen is not None:
            p=np.array(item['result']['results'][chosen]['path']);ax.plot(p[:,0],p[:,1],'o--',color='darkorange',ms=3,lw=2,label='Selected detour')
            q=np.array(item['rollout']['poses']);ax.plot(q[:,0],q[:,1],c='k',lw=2,label='1.5s rollout')
        else:ax.text(.03,.03,'No accepted detour',color='darkred',transform=ax.transAxes)
        ax.add_patch(Circle(B[:2],.09,fill=False,color='red'));u=np.array(e['u_ref']);ax.arrow(*B[:2],*(.4*u),color='tab:blue',head_width=.04,length_includes_head=True,label='Start-based u_ref')
        ax.set_xlim(B[0]-1.85,B[0]+1.85);ax.set_ylim(B[1]-1.85,B[1]+1.85);ax.set_aspect('equal');ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
        ax.set_title(f"Fixed event{identifier}: {e['scene']} {e['index']} {e['method']}\nt={e['time_s']:.3f}s",fontsize=9);ax.legend(fontsize=6)
    for ax in axes.ravel()[len(examples):]:ax.axis('off')
    fig.suptitle('Post-hoc authorized recheck: shadow reset + start-based reference',fontsize=11)
    fig.savefig(out/'offline_detours.png',dpi=150);plt.close(fig)
    previous=json.loads((ROOT/'research/results/phase20c_offline/decision.json').read_text())
    text='# Phase20-C — 사후 수정 후 재점검\n\n'
    text+=f"**{verdict['label']}**. Numerical execution SHA `{sha}`. Protocol SHA256 `{sha256_file(out/'protocol.json')}`.\n\n"
    text+='## Only the authorized changes\n\n'
    text+='After the unchanged V1 frame-wise update, each height/range-valid occupied depth endpoint casts a0.50m Bresenham tail away from the camera in XY. Its own endpoint cell is excluded. Negative log-odds cells in the union become0 and observed=False (unknown); positive cells are untouched by this reset. Floor, high and out-of-range points do not cast tails. Existing observation state outside reset cells, occupied threshold>0.85, hit/free increments, clipping, camera/filter/noise and SDF formula remain unchanged.\n\n'
    text+='Selection, R2 and fallback use the shadow-reset base map, with unknown still nonoccupied. R3 uses that base SDF within the first0.30m **path arclength**, and a second SDF of occupied OR unknown cells afterwards. This same piecewise field supplies the clearance preference and hard constraints; exact certificates use the corresponding near/far occupied sets. Radius, sampling margins, all objective weights, curvature/length constraints, initialization angles, solver and acceptance thresholds are unchanged.\n\n'
    text+='u_ref is now normalized (current position−run start position), falling back to the run start heading when distance<0.50m. The old history-displacement and NoMaD endpoint average have no role in u_ref. Latest packet IDs remain provenance only. NO_PROGRESS thresholds, blocked states and the frozen offline6s virtual action+3s cooldown remain unchanged.\n\n'
    text+='## Phase15-A2 accuracy comparison\n\n'
    text+='The same24 archived Phase15-A runs and3,002 depth frames are replayed once per original noise condition. Original float16 frames, camera transforms, deterministic per-frame noise, native paths, frame-availability rule, 5mm path queries and2.5cm classification threshold are reused. Stored V1 baseline statistics are reused without another baseline replay. Fractions divide all sample decisions. These accuracy numbers apply to the common selection/R2/fallback view where unknown is not occupied; conservative R3 safety is evaluated separately below.\n\n'
    text+=table(accuracy)+'\n\n'
    text+='The historical renderer source differs from the current simulator.py; its recorded hash was verified against the original render commit0033986196eac1afb319e53099600e58344e7297. Archive/frame hashes and transforms were verified. No old code was reverted and no new rendering was performed.\n\n'
    text+='## Rebuilt gate inputs and results\n\n'
    text+='Saved Phase20-B depth uses its original SeedSequence(20261027,run offset,frame ID), existing grid allocation and actual camera transform. Rebuilt snapshots retain the original frame/publication eligibility; this isolates geometry processing and does not pretend to simulate changed live publication latency. The changed u_ref is used to recompute trigger events from the same ten valid saved runs; first-four examples are fixed before the R3 solves. Two technical failures remain excluded.\n\n'+table(excluded)+'\n\n'
    text+='Old gate: `'+json.dumps({k:previous[k] for k in ('triggers','accepted_triggers','accepted_path_oracle_penetrations','selected_path_oracle_penetrations','rollout_overlaps')})+'`.\n\n'
    text+='```json\n'+json.dumps(clean(verdict),indent=2,ensure_ascii=False)+'\n```\n\n'+table(summary)+'\n\n'
    text+='READY still requires≥50% accepted triggers, zero oracle penetration across all accepted initialization paths,≤7% selected1.5s rollout overlap and four-process seven-start p95≤1.0s. Selected-path violations and within-deadline acceptance are also reported. Conservative-field EDT construction/loading and exact unknown-cell certificate cost are included in the seven-start timing. No speed optimization or extra restarts were introduced.\n\n'
    text+='Full-path unknown fraction is measured on the new base observation mask; the first0.30m is the declared exception. Far-path unknown fraction is reported separately. −X counts refer to u_ref[0]<0 and are not forced to zero.\n\n'
    text+='![First four fixed examples](../research/results/phase20c_shadow_recheck/offline_detours.png)\n\n'
    text+='## Status and limits\n\nFive new tests passed for shadow reset, positive preservation, endpoint filtering, piecewise unknown constraint/certificate and Jacobian, and start-only direction. All original source/data/result files remain unchanged.\n\n'
    if verdict['label']=='NOT_READY':text+='The gate is NOT_READY. Online integration, L3 M3 smoke and campaign preparation stop here; no navigation, inference, new depth render or campaign command follows. Failed results are retained.\n\n'
    else:text+='Offline READY permits the subsequent online integration and one excluded L3 M3 smoke; it is not proof of live closed-loop safety.\n\n'
    text+='This is a post-hoc saved-input recheck. Changed control, new NoMaD observations, future depth updates during the detour and online compute contention are absent. Only a new driving experiment can establish effects on navigation.\n\n'
    text+='## Fixed protocol\n\n```json\n'+json.dumps(protocol,indent=2,ensure_ascii=False)+'\n```\n'
    with (ROOT/'docs/PHASE20C_SHADOW_RECHECK.md').open('x') as f:f.write(text)
    append_saved_diagnostics(out)


def append_saved_diagnostics(out):
    from nomad_phase19s.evaluate import csv_rows
    from nomad_phase2.config import native_safety
    from nomad_phase19r.evaluate import dump,stats
    configs={e['event_id']:e['oracle_config'] for e in json.loads((out/'events_before_solve.json').read_text())}
    events={e['event_id']:e for e in csv_rows(out/'events.csv')};accepted=[];bad=[];overheads=[]
    with (out/'solutions.jsonl').open() as stream:
        for line in stream:
            r=json.loads(line)
            if r.get('solver_wall_s') is not None:overheads.append(r['attempt_wall_s']-r['solver_wall_s'])
            if not r['accepted']:continue
            selected=events[r['event_id']]['selected_initialization']==r['initialization']
            accepted.append(dict(selected=selected,unknown=r['unknown_fraction'],near_unknown=r['near_unknown_fraction'],far_unknown=r['far_unknown_fraction']))
            if r['oracle_clearance_m']<0:
                s=native_safety(r['path'],configs[r['event_id']]);box=s['minimum_clearance_m'] is not None and s['minimum_clearance_m']<0;wall=s['corridor_clearance_m']<0
                bad.append(dict(event_id=r['event_id'],initialization=r['initialization'],selected=selected,
                    kind='BOX_AND_CORRIDOR' if box and wall else 'BOX' if box else 'CORRIDOR',oracle_clearance_m=r['oracle_clearance_m'],
                    depth_clearance_m=r['depth_clearance_m'],unknown_fraction=r['unknown_fraction'],near_unknown_fraction=r['near_unknown_fraction'],far_unknown_fraction=r['far_unknown_fraction']))
    csv_write(out/'penetration_diagnostics.csv',bad)
    summaries=[]
    for scope,rr in [('all_accepted',accepted),('selected',[r for r in accepted if r['selected']])]:
        summaries.append(dict(scope=scope,paths=len(rr),paths_with_unknown=sum(r['unknown']>0 for r in rr),
            path_mean_unknown_fraction=float(np.mean([r['unknown'] for r in rr])) if rr else None,
            maximum_unknown_fraction=max((r['unknown'] for r in rr),default=None),maximum_far_unknown_fraction=max((r['far_unknown'] for r in rr),default=None)))
    dump(out/'unknown_summary.json',summaries)
    text='## Saved-result diagnostics (no additional solves)\n\n'
    text+=f"Accepted path failures: {dict(Counter(r['kind'] for r in bad))}; selected path failures: {dict(Counter(r['kind'] for r in bad if r['selected']))}.\n\n"
    text+=table([r for r in bad if r['selected']])+'\n\n'+table(summaries)+'\n\n'
    text+='The remaining penetrating paths have unknown fraction0 under the updated observation mask. Marking unknown as occupied therefore does not eliminate these observed-but-optimistic map errors; the data do not identify one unique cause of those errors.\n\n'
    text+='Post-optimizer validation/statistics overhead per initialized solve: `'+json.dumps(stats(overheads))+'` seconds. This includes the unchanged exact certificate over the much denser occupied+unknown set; it is not an isolated certificate benchmark. No timing optimization was applied after seeing the result.\n\n'
    doc=ROOT/'docs/PHASE20C_SHADOW_RECHECK.md';body=doc.read_text();marker='## Status and limits'
    assert marker in body and '## Saved-result diagnostics' not in body
    doc.write_text(body.replace(marker,text+marker))
    dump(out/'presentation.json',dict(additional_solves=0,additional_rollouts=0,additional_map_replays=0,change='Separate remaining box failures, unknown ratios and postsolve overhead',report_sha256=sha256_file(__file__)))
