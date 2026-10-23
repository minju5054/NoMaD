"""Read-only final analysis; never launches inference, navigation, or Graph solves."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import numpy as np
from nomad_isaac.common import ROOT, sha256_file, write_json
from nomad_isaac.async_report import rows, stats, wrapped
from nomad_phase0.chunk_report import trace
from nomad_phase0.s0_batch_metrics import write_csv, wilson
from .config import protocol

METHODS = ('RAW', 'CURV-SPEED', 'HORIZON-SPEED', 'GRAPH')


def average(values):
    a = [v for v in values if v is not None]
    return float(np.mean(a)) if a else None


def load(root):
    plan = json.loads((root/'plan.json').read_text())
    assert plan['protocol'] == protocol()
    for name, digest in plan['fixed_input_sha256'].items():
        assert sha256_file(Path(name)) == digest, name
    evidence = {str(root/'plan.json'):sha256_file(root/'plan.json')}
    for phase, jobs in [('pilots',plan['jobs'][:3]), ('remaining',plan['jobs'][3:])]:
        completed = json.loads((root/f'{phase}_complete.json').read_text())
        journal = rows(root/f'{phase}_execution.jsonl')
        assert completed['attempts'] == completed['technical_passes'] == len(jobs)
        assert completed['retries'] == 0 and completed['keys'] == [j['key'] for j in jobs]
        assert len(journal) == 2*len(jobs)
        for i,j in enumerate(jobs):
            start,end = journal[2*i:2*i+2]
            assert (start['event'],end['event']) == ('START','END')
            assert start['key'] == end['key'] == j['key']
            assert start['monotonic_ns'] < end['monotonic_ns']
            if i: assert journal[2*i-1]['monotonic_ns'] < start['monotonic_ns']
        for name in (f'{phase}_complete.json',f'{phase}_execution.jsonl'):
            evidence[str(root/name)] = sha256_file(root/name)
    records=[]
    for j in plan['jobs']:
        path = root/'metrics'/f"{j['key']}.json"
        r=json.loads(path.read_text());r['metric_path']=str(path)
        assert r['technical_validation']=='PASS' and r['execution_git_sha'] in (
            plan['git_sha'], json.loads((root/'remaining_complete.json').read_text())['git_sha'])
        records.append(r)
    baseline=ROOT.parent/protocol()['raw_reference']
    for d,indices in [(750,range(1,5)),(0,range(1,4))]:
        for i in indices:
            path=baseline/'metrics'/f'S0_{i:02d}_D{d:03d}.json'
            r=json.loads(path.read_text());r.update(method='RAW',metric_path=str(path))
            records.append(r)
    for r in records:
        assert r['technical_validation']=='PASS'
        run=Path(r['output']);evidence[r['metric_path']]=sha256_file(Path(r['metric_path']))
        for name,digest in r['input_log_sha256'].items():
            assert sha256_file(run/name)==digest
            evidence[str(run/name)]=digest
        requests=rows(run/'requests.jsonl')
        for i,q in enumerate(requests):
            assert q['id']==i and q['seed']==101+r['index']*10000+2*i
            assert q['seed_offset']==r['index']*10000
        for name in ('summary.json','observations.jsonl','stage2_graph.jsonl','model/environment.json'):
            if (run/name).exists():evidence[str(run/name)]=sha256_file(run/name)
    assert len(records)==22
    return records,evidence,plan


def enrich(r):
    """Use actual applied commands. Common curvature denominator for every method."""
    run=Path(r['output']);control=rows(run/'controller.jsonl')
    received=rows(run/'received.jsonl');events=rows(run/'events.jsonl')
    rec,poses=trace(run)
    kappa=[];clipped=[];clamp=[]
    for c in control:
        d=c['pure_pursuit'];x=d.get('target_local_x_m');y=d.get('target_local_y_m')
        active=c['valid'] and d.get('stop_reason') is None
        k=2*y/(x*x+y*y) if active and x*x+y*y>1e-24 else 0.
        kappa.append(k)
        clipped.append(bool(active and abs(c['applied_w_rad_s']-c['applied_v_m_s']*k)>1e-12))
        clamp.append(bool(d.get('endpoint_clamped')))
    n=len(control);actual=np.array([[c['applied_v_m_s'],c['applied_w_rad_s']] for c in control])
    r.update(mean_speed_m_s=r['distance_m']/r['duration_s'],control_ticks=n,
        mean_curvature_above8_fraction=float(np.mean(np.abs(kappa)>8)),
        actual_omega_clipped_fraction=float(np.mean(clipped)),
        endpoint_clamp_fraction_common=float(np.mean(clamp)),
        minimum_obstacle_clearance_m=min(r[f'StaticObstacle{i}_minimum_clearance_m'] for i in (1,2)),
        all_control_abs_dw=stats(np.abs(np.diff(actual[:,1]))),
        all_control_sign_reversals=int(np.sum(actual[1:,1]*actual[:-1,1]<0)),
        received_interval_wall_s=stats(np.diff([x['received_monotonic_ns'] for x in received])/1e9))
    graph=[]
    if r['method']=='GRAPH':
        logs=rows(run/'stage2_graph.jsonl');jobs={x['job_id']:x for x in logs if x['event']=='SUBMIT'}
        results={x['job_id']:x for x in logs if x['event']=='RESULT'}
        terminal={x['job_id'] for x in logs if x['event']=='TERMINAL_UNAPPLIED'}
        assert len(jobs)==len(events) and set(jobs)==set(results)|terminal and not set(results)&terminal
        times=np.array([int(x['monotonic_ns']) for x in rec],dtype=np.int64)
        distance=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1))]
        for job_id,j in jobs.items():
            x=results.get(job_id);g={'key':r['key'],'D_ms':round(r['delay_s']*1000),'index':r['index'],
                'job_id':job_id,'fresh_id':j['id'],'B':j['boundary'],'switch_sim_s':j['switch_sim_s']}
            if x is None:g.update(disposition='TERMINAL_UNAPPLIED');graph.append(g);continue
            g.update(disposition=x['disposition'],initialization_error=x.get('error'),
                solver_s=x.get('solver',{}).get('solver_wall_s'),processing_s=x['processing_wall_s'],
                queue_wait_s=x['queue_wait_s'],stale_flag=x['stale_flag'],
                solver_success=x.get('solver',{}).get('success'),
                constraint_pass=x.get('solver',{}).get('constraints_satisfied'),
                exact_certificate_pass=x.get('solver',{}).get('exact_certificate_pass'),
                dispatch_to_application_m=x['movement_since_dispatch_m'],
                dispatch_to_application_yaw_rad=x['yaw_since_dispatch_rad'],
                edit_rms_m=x.get('edit_rms_m'))
            # Actual logged state at each clock boundary; <=1/72 s endpoint resolution.
            a=max(0,int(np.searchsorted(times,x['worker_start_ns'],side='right')-1))
            b=min(len(times)-1,int(np.searchsorted(times,x['worker_end_ns'],side='right')-1))
            g.update(processing_window_m=float(distance[b]-distance[a]),
                processing_window_yaw_rad=float(wrapped(poses[b,2]-poses[a,2])),
                processing_start_pose_tick=a,processing_end_pose_tick=b)
            if x['disposition']=='ACCEPTED':
                t=x['applied_tick'];c=control[t//8]
                assert c['stage2']['graph_applied_job']==job_id
                assert c['waypoint_id']==j['id'] and c['valid']
                assert all(g[k] for k in ('solver_success','constraint_pass','exact_certificate_pass'))
                assert g['processing_s']<=.5
                before=actual[t//8-1] if t else np.zeros(2);after=actual[t//8]
                g.update(applied_sim_s=t/72,before_vw=before.tolist(),after_vw=after.tolist(),
                    correction_abs_dw=float(abs(after[1]-before[1])),
                    correction_command_changed=bool(np.max(np.abs(after-before))>1e-12))
            graph.append(g)
    return graph


def summarize(group):
    handoffs=[h for r in group for h in r['handoffs']]
    goals=[r['goal_time_s'] for r in group if r['success']]
    result={'D_ms':round(group[0]['delay_s']*1000),'method':group[0]['method'],'N':len(group),
        'success':sum(r['success'] for r in group),'success_wilson95':wilson([r['success'] for r in group]),
        'collision':sum(r['geometric_overlap'] for r in group),'corridor':sum(r['corridor_violation'] for r in group),
        'timeout':sum(r['classification']=='STUCK' for r in group),
        'goal_time_success_s':stats(goals),'goal_time_success_mean_s':average(goals),
        'mean_run_speed_m_s':average([r['mean_speed_m_s'] for r in group]),
        'mean_run_stop_s':average([r['stop_time_s'] for r in group]),
        'minimum_obstacle_clearance_m':min(r['minimum_obstacle_clearance_m'] for r in group),
        'margin_violation_total_s':sum(r['margin_violation_s'] for r in group),
        'margin_violation_runs':sum(r['margin_violation_s']>0 for r in group),
        'handoff_n':len(handoffs),'switch_sign_reversals_sum':sum(h['w_sign_flip'] for h in handoffs),
        'endpoint_clamp_mean_run_fraction':average([r['endpoint_clamp_fraction_common'] for r in group]),
        'curvature_above8_mean_run_fraction':average([r['mean_curvature_above8_fraction'] for r in group]),
        'actual_w_clipped_mean_run_fraction':average([r['actual_omega_clipped_fraction'] for r in group]),
        'received_interval_mean_run_median_s':average([r['received_interval_wall_s'].get('median') for r in group]),
        'all_tick_dw_mean_run_median':average([r['all_control_abs_dw']['median'] for r in group])}
    for k in ('staleness','A_B_distance_m','A_B_abs_yaw_rad','abs_dw','observation_to_switch_wall_s'):
        result[k+'_pooled']=stats([h[k] for h in handoffs if h[k] is not None])
        result[k+'_mean_run_median']=average([r['handoff_statistics'][k].get('median') for r in group])
    return result


def graph_summary(graph,records,d):
    g=[x for x in graph if x['D_ms']==d];r=[x for x in records if x['method']=='GRAPH' and round(x['delay_s']*1000)==d]
    completed=[x for x in g if x['disposition']!='TERMINAL_UNAPPLIED']
    return {'D_ms':d,'calls':len(g),'dispositions':dict(Counter(x['disposition'] for x in g)),
        'independent_nonconverged':sum(x.get('solver_success') is False for x in g),
        'independent_constraint_failure':sum(x.get('constraint_pass') is False or x.get('exact_certificate_pass') is False for x in g),
        'stale_flags':sum(x.get('stale_flag',False) for x in g),
        'solve_time_s':stats([x['solver_s'] for x in completed if x['solver_s'] is not None]),
        'processing_time_s':stats([x['processing_s'] for x in completed]),
        'queue_wait_s':stats([x['queue_wait_s'] for x in completed]),
        'processing_window_m':stats([x['processing_window_m'] for x in completed]),
        'dispatch_to_application_m':stats([x['dispatch_to_application_m'] for x in completed]),
        'accepted_edit_rms_m':stats([x['edit_rms_m'] for x in completed if x['edit_rms_m'] is not None]),
        'correction_abs_dw':stats([x['correction_abs_dw'] for x in completed if 'correction_abs_dw' in x]),
        'changed_command_applications':sum(x.get('correction_command_changed',False) for x in g),
        'corrected_valid_tick_fraction':sum(x['graph']['corrected_control_ticks'] for x in r)/sum(x['valid_pp_control_ticks'] for x in r),
        'accepted_fresh_fraction':sum(x['disposition']=='ACCEPTED' for x in g)/len(g)}


def plot(out,records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    from matplotlib.lines import Line2D
    c=json.loads((ROOT/protocol()['scenario']).read_text())
    colors={'RAW':'#777777','CURV-SPEED':'#0072B2','HORIZON-SPEED':'#E69F00','GRAPH':'#CC3377'}
    styles={'RAW':'--','CURV-SPEED':'-','HORIZON-SPEED':'-.','GRAPH':'-'}
    fig,axs=plt.subplots(2,1,figsize=(12,9),sharex=True,sharey=True)
    for ax,i in zip(axs,(1,2)):
        for b in c['obstacles']:
            x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2]
            ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc='#a8c79e',ec='#486643',lw=1.2))
            # Radius + required 2cm: diagnostic envelope, not additional geometry.
            ax.add_patch(Rectangle((x-w/2-.11,y-h/2-.11),w+.22,h+.22,fc='none',ec='#76936b',ls=':',lw=.9))
            ax.text(x,y,b['id'].replace('StaticObstacle','S'),ha='center',va='center',fontsize=10)
        ax.add_patch(Rectangle((-2,-1.5),8,3,fc='none',ec='#323232',lw=1.5))
        ax.axhline(1.41,color='#b0b0b0',ls=':',lw=.8);ax.axhline(-1.41,color='#b0b0b0',ls=':',lw=.8)
        ax.add_patch(Circle((4.5,0),.3,fc='#d8eee8',ec='#478474',alpha=.6))
        ax.plot(0,0,'ks',ms=5);ax.text(-.08,-.22,'Start',ha='right',fontsize=9)
        ax.text(4.5,-.45,'Goal (r=0.30 m)',ha='center',fontsize=9)
        titles=[]
        for method in METHODS:
            r=next(x for x in records if x['delay_s']==.75 and x['index']==i and x['method']==method)
            _,xy=trace(Path(r['output']))
            ax.plot(xy[:,0],xy[:,1],color=colors[method],ls=styles[method],lw=1.5 if method=='RAW' else 2,alpha=.9)
            ax.plot(*xy[-1,:2],marker='o' if r['success'] else 'X',color=colors[method],ms=7)
            if not r['success']:
                ax.annotate(f"{method}: {r['classification']} at {r['duration_s']:.1f}s",xy[-1,:2],
                    xytext=(.3,-1.05),textcoords='data',fontsize=9,color=colors[method],
                    arrowprops={'arrowstyle':'->','color':colors[method]})
            titles.append(f"{method} {r['goal_time_s']:.1f}s" if r['success'] else f"{method} timeout {r['duration_s']:.0f}s")
        ax.set(title=f"D750 / index {i} / seed offset {i*10000}\n"+'  |  '.join(titles),
            xlabel='World X (m)',ylabel='World Y (m)',xlim=(-2.1,6.1),ylim=(-1.65,1.65))
        ax.set_aspect('equal');ax.grid(alpha=.13)
    fig.legend(handles=[Line2D([0],[0],color=colors[m],ls=styles[m],lw=2,label=m) for m in METHODS],
        loc='lower center',bbox_to_anchor=(.5,.055),ncol=4,frameon=False)
    fig.suptitle('Actual executed center paths | S0 D750 | indices 1–2',fontsize=14)
    fig.text(.5,.018,'Oracle geometry / SE(2) kinematic Isaac Sim. RAW reused from Stage 1; independent closed-loop RGB.\n'
        'Dotted obstacle envelopes: robot radius + 2 cm. Circles: goal entry. X: failed termination.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.1,1,.95));fig.savefig(out/'d750_index1_2_paths.png',dpi=170);plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args();records,evidence,plan=load(a.run_root)
    graph=[]
    for r in records:graph.extend(enrich(r))
    conditions=[summarize([r for r in records if r['delay_s']==d and r['method']==m])
        for d,methods in ((.75,METHODS),(0.,('RAW','GRAPH'))) for m in methods]
    cs={(c['D_ms'],c['method']):c for c in conditions}
    g=cs[750,'GRAPH'];speed=[cs[750,m] for m in ('CURV-SPEED','HORIZON-SPEED')]
    fastest=min(c['goal_time_success_s']['median'] for c in speed if c['success']) if any(c['success'] for c in speed) else None
    checks={'success_count':g['success']>=max(c['success'] for c in speed)+2,
        'goal_time':g['goal_time_success_s'].get('median',float('inf'))<=1.2*fastest if fastest else None,
        'D0_success':cs[0,'GRAPH']['success']>=cs[0,'RAW']['success']}
    paired=[]
    for d,indices,methods in ((750,range(1,5),METHODS),(0,range(1,4),('RAW','GRAPH'))):
        for i in indices:
            row={'D_ms':d,'index':i,'seed_offset':i*10000}
            for m in methods:
                r=next(r for r in records if round(r['delay_s']*1000)==d and r['index']==i and r['method']==m)
                for k in ('classification','goal_time_s','mean_speed_m_s','minimum_obstacle_clearance_m','margin_violation_s'):
                    row[m+'_'+k]=r[k]
            for m in methods:
                if m=='GRAPH':continue
                gt=row['GRAPH_goal_time_s'];mt=row[m+'_goal_time_s']
                row['GRAPH_minus_'+m+'_success']=int(row['GRAPH_classification']=='SUCCESS')-int(row[m+'_classification']=='SUCCESS')
                row['GRAPH_minus_'+m+'_goal_s']=gt-mt if gt is not None and mt is not None else None
            paired.append(row)
    summary={'scope':protocol()['scope_label'],'pilot_attempts':3,'remaining_attempts':12,'technical_passes':15,'retries':0,
        'raw_reused_runs':7,'conditions':conditions,'graph_statistics':[graph_summary(graph,records,d) for d in (750,0)],
        'candidate_rule':protocol()['candidate_rule'],'candidate_checks':checks,
        'decision':'GRAPH_ADVANTAGE_CANDIDATE' if all(v is True for v in checks.values()) else 'NO_GRAPH_ADVANTAGE_CANDIDATE',
        'candidate_numbers':{'graph_successes':g['success'],'required_successes':max(c['success'] for c in speed)+2,
            'graph_goal_median_s':g['goal_time_success_s'].get('median'),'fastest_speed_goal_median_s':fastest,
            'goal_time_limit_s':1.2*fastest if fastest else None},
        'execution_git_shas':sorted(set(r['execution_git_sha'] for r in records if r['method']!='RAW')),
        'analysis_base_git_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'analysis_source_sha256':sha256_file(Path(__file__)),'frozen_input_hash_count':len(plan['fixed_input_sha256']),
        'max_replay_errors':{k:max(r[k] for r in records if r['method']!='RAW') for k in
            ('max_pose_replay_error','max_pp_command_replay_error','max_swept_clearance_replay_error')},
        'limitations':['N=4 exploratory; D0 N=3; Wilson intervals descriptive only',
            'Paired seed offsets, not identical closed-loop RGB/FRESH predictions; RAW historical reference',
            'SUCCESS excludes overlap/corridor intrusion but 2cm margin is an independent metric',
            'Staleness uses original observation-anchored FRESH at initial RAW switch, not later corrected path',
            'Handoff distributions pool events; clamp/curvature/clipping summaries average per-run fractions',
            'Common curvature flag abs(kappa)>8 for all methods; original Stage1 RAW >2 flag not mixed in',
            'Graph processing-window motion uses logged72Hz poses: up to one integration tick resolution at each clock boundary',
            'Graph total processing time includes setup/certificate; dispatch-to-application includes controller wait',
            'D0 success-count non-harm criterion does not establish no effect on travel time or all other metrics']}
    out=a.out;out.mkdir(parents=True,exist_ok=False)
    compact=[{k:v for k,v in r.items() if k not in ('request_seeds','handoffs','first_switch','last_three_fresh','input_log_sha256')} for r in records]
    write_json(out/'summary.json',summary);write_json(out/'runs.json',compact)
    write_csv(out/'runs.csv',[{k:r.get(k) for k in ('key','method','index','delay_s','classification','goal_time_s','duration_s',
        'mean_speed_m_s','distance_m','stop_time_s','minimum_obstacle_clearance_m','margin_violation_s','failure',
        'endpoint_clamp_fraction_common','mean_curvature_above8_fraction','actual_omega_clipped_fraction','switch_sign_reversals')} for r in records])
    write_csv(out/'conditions.csv',conditions);write_csv(out/'paired.csv',paired);write_csv(out/'graph_jobs.csv',graph)
    write_json(out/'input_hashes.json',evidence)
    plot(out,records)
    print(json.dumps({'decision':summary['decision'],'checks':checks,'conditions':[{k:c[k] for k in ('D_ms','method','N','success','collision','corridor','timeout')} for c in conditions]},indent=2))

if __name__=='__main__':main()
