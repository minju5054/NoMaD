"""Saved-only offline gate presentation; no solver or navigation calls."""
import json
from collections import Counter
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase15b.depth import Snapshot
from nomad_phase17.report import table
from nomad_phase19r.evaluate import clean,csv_write


def summary_rows(events,solutions):
    result=[]
    groups=[('ALL','ALL',events)]+[(scene,phase,[e for e in events if e['scene']==scene and e['phase']==phase])
        for scene in ('L2','L3') for phase in ('PRE_SPAWN','BEFORE_BOX_PASSAGE','AFTER_BOX_PASSAGE')]
    for scene,phase,rr in groups:
        chosen=[e for e in rr if e['accepted']];ids={e['event_id'] for e in rr};ss=[r for r in solutions if r['event_id'] in ids and r['accepted']]
        result.append(dict(scene=scene,phase=phase,triggers=len(rr),accepted=len(chosen),acceptance=len(chosen)/len(rr) if rr else None,
            accepted_initializations=len(ss),all_accepted_penetrations=sum(r['oracle_clearance_m']<0 for r in ss),
            selected_penetrations=sum(e['selected_oracle_clearance_m']<0 for e in chosen),rollout_overlap=sum(e['rollout_overlap'] for e in chosen),
            rollout_count=len(chosen),unknown_median=float(np.median([e['selected_unknown_fraction'] for e in chosen])) if chosen else None,
            relative_progress_median=float(np.median([e['selected_progress_m'] for e in chosen])) if chosen else None,
            gap_direction=sum(bool(e.get('gap_direction')) for e in chosen),gap_applicable=sum(e.get('gap_direction') is not None for e in chosen),
            seven_solve_p95_s=float(np.quantile([e['seven_wall_s'] for e in rr],.95)) if rr else None,
            u_ref_negative_world_x=sum(e['u_ref'][0]<0 for e in rr)))
    return result


def offline_report(out,events,solutions,verdict,examples,excluded,sha,protocol):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    summary=summary_rows(events,solutions);csv_write(out/'summary.csv',summary)
    fig,axes=plt.subplots(2,2,figsize=(12,10),constrained_layout=True)
    for ax,(identifier,item) in zip(axes.ravel(),examples.items()):
        e=item['event'];B=np.array(e['B']);field=Snapshot.load(e['snapshot_file']);iy,ix=np.nonzero(field.occupied)
        cloud=field.origin+np.c_[ix,iy]*field.h;cloud=cloud[np.max(np.abs(cloud-B[:2]),axis=1)<=1.9]
        if len(cloud):ax.scatter(cloud[:,0],cloud[:,1],s=2,c='.7',alpha=.6,label='Saved depth occupancy')
        for b in e['oracle_config']['obstacles']:
            x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,facecolor='purple',edgecolor='purple',alpha=.2,label='Oracle box (evaluation)'))
        corridor=e['oracle_config']['corridor'];ax.axhline(corridor['half_width'],c='.4');ax.axhline(-corridor['half_width'],c='.4')
        ax.axvline(corridor['xmin'],c='.4');ax.axvline(corridor['xmax'],c='.4')
        for i,r in enumerate(item['result']['results']):
            if r['initial_path'] is not None:
                p=np.array(r['initial_path']);ax.plot(p[:,0],p[:,1],c='.65',lw=.8,label='7 fixed straight initializations' if i==0 else None)
        selected=item['result']['selected']
        if selected is not None:
            r=item['result']['results'][selected];p=np.array(r['path']);ax.plot(p[:,0],p[:,1],'o--',c='darkorange',ms=3,lw=2,label='Selected detour')
            pose=np.array(item['rollout']['poses']);ax.plot(pose[:,0],pose[:,1],c='k',lw=2,label='1.5s SP + alignment')
        else:ax.text(.03,.03,'No accepted detour',transform=ax.transAxes,color='darkred')
        ax.add_patch(Circle(B[:2],.09,fill=False,color='red'));ax.scatter(*B[:2],c='red',s=25,label='Fixed B')
        u=np.array(e['u_ref']);ax.arrow(*B[:2],*(.4*u),head_width=.04,color='tab:blue',length_includes_head=True,label='u_ref (pose/sample only)')
        ax.set_xlim(B[0]-1.85,B[0]+1.85);ax.set_ylim(B[1]-1.85,B[1]+1.85);ax.set_aspect('equal')
        ax.set_xlabel('World x (m)');ax.set_ylabel('World y (m)')
        ax.set_title(f"Fixed event {identifier}: {e['scene']} {e['index']} {e['method']}\nt={e['time_s']:.3f}s, {e['reference_source']['source']}",fontsize=8)
        ax.legend(fontsize=6,loc='upper left')
    for ax in axes.ravel()[len(examples):]:ax.axis('off')
    fig.suptitle('First four trigger events, fixed before solving; no new rendering/inference',fontsize=11)
    fig.savefig(out/'offline_detours.png',dpi=150);plt.close(fig)
    counts=dict(Counter(r['disposition'] for r in solutions));run_rows=[]
    for key in dict.fromkeys(e['run'] for e in events):
        rr=[e for e in events if e['run']==key];selected=[e for e in rr if e['accepted']]
        run_rows.append(dict(run=key,triggers=len(rr),accepted=len(selected),selected_penetrations=sum(e['selected_oracle_clearance_m']<0 for e in selected),
                             rollout_overlaps=sum(e['rollout_overlap'] for e in selected)))
    text='# Phase 20-C — R3 depth detour offline gate / 파일럿\n\n'
    text+=f"**{verdict['label']}**. Execution SHA `{sha}`; protocol SHA256 `{sha256_file(out/'protocol.json')}`. No new Isaac navigation, NoMaD inference or depth/RGB rendering.\n\n"
    text+='## Frozen R3\n\n'
    text+='B is fixed; ten editable XY points follow it. Seven straight1.5m initializations use0,+30,−30,+60,−60,+90,−90 degrees relative to u_ref. No native yaw or waypoint timing is inferred. SLSQP uses analytic derivatives, maxiter100, ftol1e−8, one attempt per initialization.\n\n'
    text+=r'\[E=\tfrac12\big[(\max(0,1.2-(p_{10}-b)\cdot u_{ref})/0.10)^2+\sum_{i=1}^{9}\|(p_{i+1}-2p_i+p_{i-1})/0.03\|^2+\sum_q(\max(0,0.15-d_{depth}(q))/0.05)^2+(2\sin((\operatorname{atan2}(p_1-b)-\theta_B)/2)/(\pi/6))^2\big].\]'+'\n\n'
    text+='Each of ten segments has nine inspection points. Safety is d_depth−h/√2−L/16≥min(0.025,max(0,c_B−0.005)) within0.30m along the current optimized path and≥0.025 thereafter. c_B is SDF(B)−h/√2; negative c_B rejects the solve. Exact occupied-cell-site distance certificates split the continuous path at0.30m. The zone boundary is nonsmooth; derivatives are analytic within each zone, unchanged from R2.\n\n'
    text+='All nine Menger curvatures have |κ|≤4m⁻¹; ten segment lengths are0.10–0.20m; editable points lie inside the1.6m disk around B. Redundant coordinate bounds B±1.6m implement the same disk bounding box. Acceptance needs solver success, violation≤1e−7, exact depth certificate and relative progress≥0.5m. Selection maximizes relative progress, then minimizes path length, then uses initialization index for an exact tie. No oracle geometry enters solve or selection.\n\n'
    text+='## Trigger inventory and limitations\n\n'
    text+='Ten technically valid L2/L3 Phase20-B runs are included; the two technical failures below are excluded as requested. Frozen Phase20-B main_order followed by9Hz controller tick order defines event IDs. At each tick, the latest latched NoMaD packet and latest actually published depth snapshot are used; future outputs/snapshots are excluded. Metric samples remain anchored at their observation pose.\n\n'
    text+='u_ref uses displacement from t−8s to t−3s if its length≥0.30m. Otherwise it uses the normalized mean world endpoint minus current robot position. Before eight seconds, incomplete history uses this sample fallback; no pre-start pose is invented. The trigger requires a complete recent3s window and signed projected displacement<0.20m. A zero mean direction or absent samples is explicitly skipped. Rotation, departure-alignment braking/rotation and an outstanding R2 repair wait block the trigger.\n\n'
    text+='The saved runs contain no R3 end event. Before solving, the offline inventory therefore uses a fixed virtual6s detour window followed by the prescribed3s cooldown; earliest recheck is9s after the trigger. Saved poses continue unchanged throughout that window. This convention, offered for clarification and fixed before results, is not a reconstruction of actual detour execution or variable solve latency. Online cooldown would start at the actual detour end.\n\n'
    text+='Post-box and pre-spawn triggers are retained, with phases reported separately. Relative progress may point in −X if recent motion or NoMaD endpoints do; no goal/oracle axis is substituted. “Endpoint beyond box front or in a side gap” is descriptive and not part of READY. It is not a proof of box passage, especially for events already past the box.\n\n'
    text+=table(excluded)+'\n\n'+table(run_rows)+'\n\n'
    text+='## Gate\n\n```json\n'+json.dumps(clean(verdict),indent=2,ensure_ascii=False)+'\n```\n\n'
    text+='Penetration is checked across **all accepted initialization paths**, with selected-path penetrations separately reported. One SP+revised-start-alignment rollout per accepted event uses actual recorded speed/yaw, max1.5s, and oracle only for passive clearance evaluation. Its clock includes braking and rotation. Empty-obstacle/pre-spawn evaluation uses the same corridor function without inventing an obstacle.\n\n'
    text+='Seven-start timing includes four-process dispatch, snapshot loading, solving, certificate and result transfer; pool initialization and oracle evaluation are excluded. Acceptance before the1s online cutoff is separately recorded. No solve is restarted or tuned.\n\n'
    text+=table(summary)+'\n\nDispositions: `'+json.dumps(counts)+'`.\n\n![Fixed offline examples](../research/results/phase20c_offline/offline_detours.png)\n\n'
    text+='## Validation and next stage\n\nFour completed unit tests passed: analytic residual/constraint Jacobians versus finite differences≤1e−5, free straight path, blocked synthetic gap detour, and NO_PROGRESS/busy/end-time cooldown. They were not repeated after the capacity interruption.\n\n'
    if verdict['label']=='NOT_READY':text+='The mandatory gate failed. Smoke and online campaign preparation stop here; no smoke/main navigation was run and no campaign command is supplied. The failed candidates and original saved data remain preserved.\n\n'
    else:text+='Offline READY permits the next online integration and one excluded60s L3 M3 smoke; it does not itself validate live detour execution.\n\n'
    text+='This is post-hoc offline analysis of correlated saved events, not a driving comparison. Future FRESH responses, changed depth maps, motion during a live solve and subsequent closed-loop behavior are absent.\n\n'
    text+='## Preregistered protocol\n\n```json\n'+json.dumps(protocol,indent=2,ensure_ascii=False)+'\n```\n'
    with (ROOT/'docs/PHASE20C_DETOUR.md').open('x') as f:f.write(text)
    append_saved_diagnostics(out)


def append_saved_diagnostics(out):
    """Attribute the already evaluated failures; no new solve or rollout."""
    from nomad_phase19s.evaluate import csv_rows
    from nomad_phase2.config import native_safety
    from nomad_phase19r.evaluate import dump
    before={e['event_id']:e for e in json.loads((out/'events_before_solve.json').read_text())}
    events={e['event_id']:e for e in csv_rows(out/'events.csv')};failures=[]
    with (out/'solutions.jsonl').open() as stream:
        for line in stream:
            r=json.loads(line)
            if not r['accepted'] or r['oracle_clearance_m']>=0:continue
            safety=native_safety(r['path'],before[r['event_id']]['oracle_config'])
            box=safety['minimum_clearance_m'] is not None and safety['minimum_clearance_m']<0;wall=safety['corridor_clearance_m']<0
            failures.append(dict(event_id=r['event_id'],initialization=r['initialization'],
                selected=events[r['event_id']]['selected_initialization']==r['initialization'],
                kind='BOX_AND_CORRIDOR' if box and wall else 'BOX' if box else 'CORRIDOR',
                oracle_clearance_m=r['oracle_clearance_m'],depth_clearance_m=r['depth_clearance_m'],unknown_fraction=r['unknown_fraction'],
                phase=before[r['event_id']]['phase']))
    csv_write(out/'penetration_diagnostics.csv',failures)
    selected=[e for e in events.values() if e['accepted']]
    text='## Saved-path failure detail\n\n'
    text+=f"All accepted negative-clearance paths: {dict(Counter(r['kind'] for r in failures))}. Selected negative-clearance paths: {dict(Counter(r['kind'] for r in failures if r['selected']))}.\n\n"
    text+=table([r for r in failures if r['selected']])+'\n\n'
    if selected:
        text+=f"The selected1.5s rollouts travelled a median {np.median([r['rollout_distance_m'] for r in selected]):.4f}m; {sum(r['rollout_distance_m']<=.01 for r in selected)}/{len(selected)} travelled≤1cm and {sum(r['rollout_alignment'] for r in selected)} triggered alignment. Zero short-horizon rollout overlap therefore does not establish safety of the entire detour.\n\n"
    text+='Some oracle-penetrating selected paths have unknown fraction0. Unknown denotes cell observation coverage, not a proof that free/occupied classification or the whole solid obstacle is correct; these data do not support attributing all failures solely to unseen cells.\n\n'
    doc=ROOT/'docs/PHASE20C_DETOUR.md';body=doc.read_text();marker='## Validation and next stage'
    assert marker in body and '## Saved-path failure detail' not in body
    doc.write_text(body.replace(marker,text+marker))
    dump(out/'presentation.json',dict(additional_solves=0,additional_rollouts=0,change='Separate box penetration from corridor intrusion and expose short-horizon coverage',report_sha256=sha256_file(__file__)))
