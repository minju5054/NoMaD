"""Read-only diagnosis report; two figures, no inference/navigation."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from nomad_isaac.async_report import rows,stats
from nomad_isaac.common import write_json,sha256_file
from nomad_isaac.old_rollout_placement import magenta_mask
from nomad_diagnostic.data import csv_write
from nomad_diagnostic.config import protocol


def report(root,out):
    out.mkdir(parents=True,exist_ok=False)
    p=protocol();metrics=[json.loads(f.read_text()) for f in sorted((root/'metrics').glob('*.json'))]
    assert len(metrics)==12 and all(m['technical_validation']=='PASS' for m in metrics)
    journal=rows(root/'journal.jsonl');assert len([r for r in journal if r['event']=='START'])==12
    assert len({r['key'] for r in journal if r['event']=='START'})==12
    c0=json.loads((root/'c0/summary.json').read_text());pairs=rows(root/'c0/observations.jsonl')
    totals=c0['total'];write_json(out/'c0_summary.json',{k:v for k,v in c0.items() if k!='coverage'})
    runrows=[];freshrows=[];sample_rows=[];mode_rows=[];all_pacing=[];rgb_count=0;max_snapshot_error=0.
    for m in metrics:
        run=Path(m['output']);trace=np.genfromtxt(run/'agent_trajectory.csv',delimiter=',',names=True)
        poses=np.column_stack([trace[k] for k in ('x_m','y_m','yaw_rad')])
        all_pacing.extend(abs(trace['pacing_error_s']))
        obs=[o for o in rows(run/'observations.jsonl') if 'observation_id' in o]
        public=rows(run/'phase2_oracle.jsonl');req=rows(run/'requests.jsonl');events=rows(run/'events.jsonl')
        eventby={e['id']:e for e in events}
        inferenceby={n['id']:n for n in rows(run/'model/inference.jsonl')}
        for o in obs:
            d=o.get('dynamic')
            if d:
                mask=magenta_mask(np.array(Image.open(run/o['rgb_file'])))
                assert int(mask.sum())==d['magenta_pixels']
                assert hashlib.sha256(mask.tobytes()).hexdigest()==d['mask_sha256']
                assert d['visible']==bool(d['active'] and mask.sum()>=20)
                rgb_count+=1
            if 'diagnostic_mode' in o:
                mode=o['diagnostic_mode'];err=float(abs(poses[mode['decision_tick']]-mode['decision_pose']).max());max_snapshot_error=max(max_snapshot_error,err)
                assert err<1e-12
        for r in req:
            mode=r['diagnostic_mode'];e=eventby.get(r['id'])
            if mode['goal_mask']:
                assert public and r['request_submit_monotonic_ns']>=public[0]['publication_monotonic_ns']
            mode_rows.append({'run':m['key'],'id':r['id'],'observation_id':r['observation_id'],'t_obs':r['observation_sim_s'],
                'goal_mask':mode['goal_mask'],'switch_s':e['application_sim_s'] if e else None,
                'closest_node':inferenceby[r['id']]['topomap']['closest_node'],
                'subgoal':inferenceby[r['id']]['topomap']['selected_subgoal_id']})
        for r in json.loads((run/'diagnostic_audit/fresh.json').read_text()):
            freshrows.append({'run':m['key'],**{k:v for k,v in r.items() if k!='samples'}})
            for s in r['samples']:
                sample_rows.append({'run':m['key'],'id':r['id'],'sample':s['sample'],'safe':s['safe'],
                    'clearance_m':s['minimum_clearance_m'],'corridor_m':s['corridor_clearance_m'],
                    'lateral':s['lateral'],'offset_m':s['crossing_offset_m']})
        r={k:m[k] for k in ('key','condition','d_m','index','offset','classification','goal_entry','duration_s','stop_s',
             'geometric_overlap','corridor_intrusion','minimum_clearance_m','margin_violation_s','max_abs_y_m','distance_m',
             'requests','switches','waypoint_timeouts')}
        r.update(passed=m['passage'] is not None,passage=json.dumps(m['passage']),
            masked_requests=len(m['masked_request_ids']),masked_switches=sum(e['diagnostic_mode']['goal_mask'] for e in events),
            any_safe_fraction=m['fresh_summary']['any_safe_fraction'],sample0_safe_fraction=m['fresh_summary']['sample0_safe_fraction'],
            all_unsafe_observations=m['fresh_summary']['observations']-m['fresh_summary']['any_safe_observations'],
            scoped_observations=m['fresh_summary']['observations'],busy_skips=m['scope_busy_skips'],
            terminal_x_m=float(poses[-1,0]),terminal_y_m=float(poses[-1,1]),
            first_masked_id=m['masked_request_ids'][0] if m['masked_request_ids'] else None,
            first_conditioned_after_mask=next((n['id'] for n in req if m['masked_request_ids'] and n['id']>m['masked_request_ids'][0] and n['diagnostic_mode']['goal_mask']==0),None))
        runrows.append(r)
    csv_write(out/'runs.csv',runrows);csv_write(out/'fresh.csv',freshrows);csv_write(out/'samples.csv',sample_rows);csv_write(out/'modes.csv',mode_rows)
    c0rows=[];c0samples=[]
    for r in pairs:
        for mode in ('conditioned','masked'):
            c0rows.append({'run':r['run'],'id':r['id'],'mode':mode,**{k:v for k,v in r[mode].items() if k!='samples'}})
            for s in r[mode]['samples']:
                c0samples.append({'run':r['run'],'id':r['id'],'mode':mode,'sample':s['sample'],
                    'safe':s['safe'],'clearance_m':s['minimum_clearance_m'],'corridor_m':s['corridor_clearance_m'],
                    'lateral':s['lateral'],'offset_m':s['crossing_offset_m']})
    csv_write(out/'c0_observations.csv',c0rows);csv_write(out/'c0_samples.csv',c0samples)
    csv_write(out/'c0_runs.csv',[{'run':r['run'],'mode':mode,'busy_skips':r['busy_skips'],**{k:v for k,v in r[mode].items() if k!='lateral_counts'},**r[mode]['lateral_counts']} for r in c0['runs'] for mode in ('conditioned','masked')])
    grouped=[]
    for cond,d in [('C1',.8),('C1',1.2),('C2',1.),('C3',1.)]:
        rr=[r for r in runrows if r['condition']==cond and r['d_m']==d]
        grouped.append({'condition':cond,'d_m':d,'n':len(rr),'successes':sum(r['classification']=='SUCCESS' for r in rr),
            'collisions':sum(r['geometric_overlap'] for r in rr),'corridor_intrusions':sum(r['corridor_intrusion'] for r in rr),
            'passed':sum(r['passed'] for r in rr),'timeouts':sum(r['classification']=='STUCK' for r in rr)})
    validation={'RGB_frames_recomputed':rgb_count,'mode_snapshot_max_error':max_snapshot_error,
        'max_errors':{k:max(m['validation'][k] for m in metrics) for k in ('pose_error','pp_command_error','command_trace_error')},
        'pacing_error_s':stats(all_pacing),'protected_hashes_unchanged':all(sha256_file(Path(f))==h for f,h in p['protected_sha256'].items()),
        'C0_input_hashes_unchanged':all(sha256_file(Path(f))==h for f,h in json.loads((root/'c0/input_hashes.json').read_text()).items()),
        'graph_calls':sum(m['graph']['calls'] for m in metrics),'sample_replacements':sum(m['actual_replacement_count'] for m in metrics),
        'additional_delay_s':0,'observed_packet_release_s':{m['key']:m['packet_release_s'] for m in metrics},
        'inference_ms':{m['key']:m['warm_inference_ms'] for m in metrics}}
    summary={'scope':p['scope'],'execution_sha':c0['execution']['git_sha'],'C0':totals,'conditions':grouped,'validation':validation,
        'C0_pair_change':dict(Counter((bool(r['conditioned']['safe_count']),bool(r['masked']['safe_count'])) for r in pairs))}
    summary['C0_pair_change']={str(k):v for k,v in summary['C0_pair_change'].items()}
    lengths={m:[] for m in ('conditioned','masked')};differences=[]
    for r in pairs:
        arrays={m:np.load(root/'c0'/r['run']/f"{r['id']:04d}_{m}.npz")['metric'] for m in lengths}
        differences.append(float(abs(arrays['conditioned']-arrays['masked']).max()))
        for mode,a in arrays.items():lengths[mode].extend(np.linalg.norm(np.diff(a,axis=1),axis=2).sum(axis=1).tolist())
    unsafe_applied=unsafe_unapplied=0;decision_inputs={}
    for r in pairs:
        source=Path(p['source_root'])/r['run']/'phase2_decisions.jsonl'
        if str(source) not in decision_inputs:decision_inputs[str(source)]={d['id']:d for d in rows(source) if 'all_unsafe' in d}
        ds=decision_inputs[str(source)]
        if r['id'] in ds:assert ds[r['id']]['all_unsafe']==r['conditioned']['all_unsafe']
        if r['conditioned']['all_unsafe']:
            if r['id'] in ds:unsafe_applied+=1
            else:unsafe_unapplied+=1
    summary['C0_conditioned_ALL_UNSAFE']={'applied':unsafe_applied,'terminal_unapplied':unsafe_unapplied,'agrees_with_saved_decisions':True}
    summary['C0_source_decision_hashes']={f:sha256_file(Path(f)) for f in decision_inputs}
    summary['C0_native_length_m']={m:stats(v) for m,v in lengths.items()}
    summary['C0_mask_changes_max_absolute_metric_m']=stats(differences)
    summary['C0_safe_crossing_runs']={m:sorted({r['run'] for r in pairs if r[m]['safe_crossing_count']}) for m in lengths}
    summary['input_hashes']={str(f):sha256_file(f) for f in [root/'c0/summary.json',root/'c0/observations.jsonl',root/'journal.jsonl',*(root/'metrics').glob('*.json')]}
    write_json(out/'summary.json',summary)
    # Exactly one actual-path figure, containing all 12 runs.
    fig,axes=plt.subplots(4,3,figsize=(15,12),sharex=True,sharey=True,layout='constrained')
    for m,ax in zip(metrics,axes.flat):
        t=np.genfromtxt(Path(m['output'])/'agent_trajectory.csv',delimiter=',',names=True)
        ax.plot([0,8],[0,0],':',color='.7',lw=1,label='centerline')
        ax.plot(t['x_m'],t['y_m'],color='#1864ab',lw=1.8,label='executed')
        b=m['spawn']['obstacle'];cx,cy=b['center_xy_m'];sx,sy=b['size_xyz_m'][:2]
        ax.add_patch(Rectangle((cx-sx/2,cy-sy/2),sx,sy,color='#b139a8',alpha=.7))
        ax.add_patch(Rectangle((cx-sx/2-.11,cy-sy/2-.11),sx+.22,sy+.22,fill=False,ls=':',ec='#b139a8'))
        ax.scatter(*m['spawn']['pose'][:2],marker='o',s=20,color='#f08c00',zorder=4)
        ax.scatter(t['x_m'][-1],t['y_m'][-1],marker='x',s=35,color='#d9480f')
        ax.scatter(8,0,marker='*',s=60,color='#2b8a3e');ax.axhline(1.5,color='.3');ax.axhline(-1.5,color='.3')
        ax.set_title(f"{m['key']} | {m['classification']}\nclearance {m['minimum_clearance_m']*100:.2f} cm; {m['duration_s']:.2f} s",fontsize=9)
        ax.set_xlim(-.2,8.3);ax.set_ylim(-1.6,1.6);ax.set_aspect('equal');ax.grid(alpha=.15)
        ax.set_xlabel('world X (m)');ax.set_ylabel('world Y (m)')
    fig.suptitle('D0 M0 diagnosis: actual closed-loop paths | N=3 per condition\nMagenta: actual box; dotted: conservative footprint + 2cm envelope; orange: spawn pose',fontsize=13)
    fig.savefig(out/'navigation_paths.png',dpi=170);plt.close(fig)
    # Exactly one C0 sample-distribution figure.
    fig,axes=plt.subplots(1,3,figsize=(15,6),layout='constrained',gridspec_kw={'width_ratios':[1.3,1,1]})
    x=np.arange(len(c0['runs']));labels=[r['run'].replace('s2a_','').replace('_M0','') for r in c0['runs']]
    for mode,delta,color in [('conditioned',-.17,'#1971c2'),('masked',.17,'#d9480f')]:
        axes[0].barh(x+delta,[100*r[mode]['any_safe_fraction'] for r in c0['runs']],height=.32,label=mode,color=color)
    axes[0].axvline(10,color='.5',ls=':',lw=1);axes[0].axvline(30,color='.5',ls=':',lw=1)
    axes[0].set_yticks(x,labels,fontsize=8);axes[0].set_xlim(0,100);axes[0].set_xlabel('Observations with >=1 native-safe sample (%)');axes[0].legend();axes[0].invert_yaxis()
    categories=['LEFT','RIGHT','FRONT','NOT_REACHED'];colors=['#2b8a3e','#e67700','#e03131','#adb5bd']
    bottom=np.zeros(2)
    for cat,color in zip(categories,colors):
        vals=np.array([totals[m]['lateral_counts'][cat] for m in ('conditioned','masked')])
        axes[1].bar(['conditioned','masked'],vals,bottom=bottom,color=color,label=cat)
        bottom+=vals
    axes[1].set_ylabel('Samples (127 observations x 8)');axes[1].set_title('At obstacle center world X\nNo extrapolation');axes[1].legend(fontsize=8)
    for mode,color in [('conditioned','#1971c2'),('masked','#d9480f')]:
        values=[s['crossing_offset_m'] for r in pairs for s in r[mode]['samples'] if s['crossing_offset_m'] is not None]
        axes[2].hist(values,bins=np.linspace(-.6,1.,25),histtype='step',lw=2,color=color,label=f'{mode} (n={len(values)})')
    axes[2].axvspan(-.285,.285,color='#e03131',alpha=.08,label='box + radius + 2cm')
    axes[2].set_xlabel('Signed Y offset from box center (m)');axes[2].set_ylabel('Crossing samples only');axes[2].legend(fontsize=8)
    fig.suptitle('C0 paired goal-mask diagnosis | 127 saved inference observations\nNative-safe fraction includes short paths; safety is not executed avoidance',fontsize=13)
    fig.savefig(out/'c0_sample_distribution.png',dpi=170);plt.close(fig)
    print(json.dumps({'conditions':grouped,'C0':totals,'validation':validation['max_errors']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();report(a.root,a.output)
