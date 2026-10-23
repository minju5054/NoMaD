"""Saved Phase3 logs only: summary, D0 reproduction, and exactly two figures."""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,write_json,sha256_file
from nomad_isaac.async_report import rows,stats
from nomad_phase0.chunk_report import trace
from nomad_phase0.s0_batch_metrics import wilson,write_csv,extract_run
from nomad_phase3.config import protocol


def d0_comparison(new):
    old=ROOT.parent/f"artifacts/isaac6/s0_paired_n10_01/{new['run_id']}/PP"
    run=Path(new['output']);legacy=extract_run(old,'PP',new['run_id'],new['seed_offset'])
    _,a=trace(old);_,b=trace(run);n=min(len(a),len(b));error=np.abs(a[:n]-b[:n]).max(axis=1)
    different=np.flatnonzero(error>1e-12)
    ro,rn=rows(old/'received.jsonl'),rows(run/'received.jsonl');common=min(len(ro),len(rn))
    inputs=[];outputs=[];same_input=[]
    for x,y in zip(ro,rn):
        assert x['seed']==y['seed'] and x['ddpm_seed']==y['ddpm_seed']
        equal=all(x[k]==y[k] for k in ('history_sha256','goal_sha256','seed','ddpm_seed'))
        if not equal:inputs.append(x['id'])
        with np.load(old/f"model/derived/{x['id']:04d}.npz") as da,np.load(run/f"model/derived/{y['id']:04d}.npz") as db:
            e=float(np.max(np.abs(da['metric']-db['metric'])))
        if e:outputs.append(x['id'])
        if equal:same_input.append({'id':x['id'],'metric_max_abs_error_m':e})
    from PIL import Image
    oo={r['observation_id']:r for r in rows(old/'observations.jsonl')}
    on={r['observation_id']:r for r in rows(run/'observations.jsonl')}
    rgb_old=np.stack([np.asarray(Image.open(old/oo[i]['rgb_file'])) for i in ro[0]['history_observation_ids']]).astype(float)
    rgb_new=np.stack([np.asarray(Image.open(run/on[i]['rgb_file'])) for i in rn[0]['history_observation_ids']]).astype(float)
    return {'first_request_observation_pose_old':ro[0]['observation_pose'],
        'first_request_observation_pose_new':rn[0]['observation_pose'],
        'first_request_same_subgoal':ro[0]['goal_sha256']==rn[0]['goal_sha256'],
        'first_history_rgb_mae_255':float(np.abs(rgb_old-rgb_new).mean()),
        'first_history_rgb_max_error_255':float(np.abs(rgb_old-rgb_new).max()),
        'run_id':new['run_id'],'old_classification':legacy['classification'],'new_classification':new['classification'],
        'old_goal_time_s':legacy['goal_time_s'],'new_goal_time_s':new.get('goal_time_s'),
        'old_duration_s':legacy['duration_s'],'new_duration_s':new.get('duration_s'),
        'old_requests':len(ro),'new_requests':len(rn),'common_request_count':common,
        'all_common_seeds_match':True,'first_different_input_request':inputs[0] if inputs else None,
        'same_input_requests':same_input,'first_different_metric_request':outputs[0] if outputs else None,
        'first_pose_difference_tick':int(different[0]) if len(different) else None,
        'first_pose_difference_sim_s':float(different[0]/72) if len(different) else None,
        'max_pose_difference_at_equal_sim_tick':float(error.max()),
        'identical_full_pose_trace':len(a)==len(b) and not len(different),
        'note':'Equal simulation ticks test deterministic reproduction only, not physical path correspondence; old60s/new90s ceiling.'}


def summarize(records):
    conditions=[];failures=[];last=[];handoffs=[]
    for r in records:
        for h in r.get('handoffs',[]):handoffs.append({'key':r['key'],'run_id':r['run_id'],'delay_ms':round(r['delay_s']*1000),**h})
        if r['classification']!='SUCCESS':
            f=r.get('failure') or {};causes=f.get('causes',[])
            pattern=('left_wall_after_Static1' if 'left_wall_positive_y' in causes and r.get('StaticObstacle1_not_passed')==0 and r.get('StaticObstacle2_not_passed')==1
                     else 'left_wall_after_Static2' if 'left_wall_positive_y' in causes and r.get('StaticObstacle2_not_passed')==0
                     else 'static_obstacle_collision' if any(s.startswith('Static') for s in causes)
                     else 'other_corridor' if r.get('corridor_violation') else 'timeout' if r.get('timeout')
                     else 'technical' if r.get('technical_failure') else 'other_termination')
            failures.append({'key':r['key'],'delay_ms':round(r['delay_s']*1000),'classification':r['classification'],
                'reason':r.get('termination_reason',r.get('error')),'pattern':pattern,'time_s':f.get('simulation_time_s',r.get('duration_s')),
                'x_m':f.get('pose',r.get('final_pose',[None]))[0],'pose':f.get('pose',r.get('final_pose')),'causes':causes,
                'location_semantics':'first confirmed breach' if f else 'termination pose; no confirmed geometric breach',
                'causal_status':'Observed mechanism/pattern only; single N5 closed-loop sample does not isolate latency causality'})
            last += [{'key':r['key'],'delay_ms':round(r['delay_s']*1000),**h} for h in r.get('last_three_fresh',[])]
    for d in protocol()['delays_s']:
        group=[r for r in records if r['delay_s']==d];valid=[r for r in group if r.get('technical_validation')=='PASS']
        pooled=[h for r in valid for h in r['handoffs']]
        summary={'D_ms':round(d*1000),'attempted':len(group),'valid_n':len(valid),'technical_failures':len(group)-len(valid),
            'success':sum(r['success'] for r in group),'success_wilson':wilson([r['success'] for r in group]),
            'collision':sum(r['geometric_overlap'] for r in valid),'corridor':sum(r['corridor_violation'] for r in valid),
            'timeout':sum(r['timeout'] for r in valid),'other_termination':sum(r['classification']=='OTHER_TERMINATION' for r in valid),
            'classifications':dict(Counter(r['classification'] for r in group)),
            'margin_violating_runs':sum(r['margin_violation_s']>0 for r in valid),
            'margin_violation_s_total':sum(r['margin_violation_s'] for r in valid),
            'handoffs':len(pooled),'handoff_invalid_paths':sum(not h['path_valid'] for h in pooled),
            'pooled_handoffs':{key:stats([h[key] for h in pooled if h[key] is not None]) for key in
                ('A_B_distance_m','A_B_abs_yaw_rad','staleness','abs_dw','observation_to_switch_wall_s')},
            'run_summary':{key:stats([r[key] for r in valid if r.get(key) is not None]) for key in
                ('goal_time_s','duration_s','stop_time_s','distance_m','max_abs_y_m','margin_violation_s',
                 'endpoint_clamp_fraction','endpoint_clamp_valid_fraction','curvature_saturated_fraction',
                 'switch_sign_reversals','busy_skips','waypoint_timeout_episodes','wall_simulation_ratio',
                 'StaticObstacle1_minimum_clearance_m','StaticObstacle2_minimum_clearance_m')},
            'receive_interval_median_s_by_run':[r['received_interval_wall_s']['median'] for r in valid],
            'delivery_delay_s_by_run':[r['actual_delivery_delay_s'] for r in valid],
            'pacing_by_run':[r['pacing_error_s'] for r in valid]}
        conditions.append(summary)
    eligible=[c['D_ms'] for c in conditions if c['D_ms']>0 and c['success']<=3]
    robust=all(c['success']>=4 for c in conditions if c['D_ms']>0)
    return {'scope':protocol()['scope_label'],'protocol':protocol(),'conditions':conditions,
        'stage2_delays_ms':eligible[:2],'decision':'ROBUST_THROUGH_750MS_NO_HANDOFF_NEED_SHOWN' if robust else 'STAGE2_DELAY_RANGE_SELECTED',
        'technical_caveat':any(c['technical_failures'] for c in conditions),'navigation_retries':0},failures,last,handoffs


def plots(out,records,summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    plt.rcParams.update({'font.size':10,'figure.dpi':130})
    cs=summary['conditions']; fig,ax=plt.subplots(figsize=(7,4))
    y=np.array([c['success']/5 for c in cs]);lo=np.array([c['success_wilson']['ci95'][0] for c in cs]);hi=np.array([c['success_wilson']['ci95'][1] for c in cs])
    ax.errorbar(range(4),y,yerr=[y-lo,hi-y],fmt='o-',capsize=6,color='#225c93')
    for i,c in enumerate(cs):ax.annotate(f"{c['success']}/5",(i,y[i]),xytext=(8,8),textcoords='offset points')
    ax.axhline(.6,color='gray',ls=':',lw=1,label='Stage 2 count threshold: 3/5')
    ax.set(xticks=range(4),xticklabels=[c['D_ms'] for c in cs],ylim=(-.03,1.12),xlabel='Post-packet delivery delay (ms)',ylabel='Goal success without overlap/corridor intrusion',title='S0 RAW + Pure Pursuit | N=5 exploratory per delay')
    ax.legend(loc='lower left');ax.grid(alpha=.2);fig.text(.5,.01,'Wilson 95% intervals are descriptive; not evidence of causal or statistical superiority.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(out/'success_by_delay.png');plt.close(fig)
    scenario=json.loads((ROOT/protocol()['scenario']).read_text()); fig,axs=plt.subplots(2,2,figsize=(12,6.6),sharex=True,sharey=True)
    for ax,d in zip(axs.ravel(),protocol()['delays_s']):
        for b in scenario['obstacles']:
            x,y=b['center_xy_m'];w,h=b['size_xyz_m'][:2]
            ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,fc='#7bb27c',ec='#38683d',alpha=.7))
            ax.text(x,y,b['id'].replace('StaticObstacle','S'),ha='center',va='center',fontsize=8)
        ax.axhline(1.5,c='black',lw=2);ax.axhline(-1.5,c='black',lw=2)
        ax.axvline(-2,c='black',lw=2);ax.axvline(6,c='black',lw=2)
        ax.axvline(-1.91,c='gray',lw=.7,ls=':');ax.axvline(5.91,c='gray',lw=.7,ls=':')
        ax.axhline(1.41,c='gray',lw=.7,ls=':');ax.axhline(-1.41,c='gray',lw=.7,ls=':')
        ax.add_patch(Circle((4.5,0),.3,fc='none',ec='gray',ls='--'));ax.plot(0,0,'ks',ms=4)
        for r in [r for r in records if r['delay_s']==d]:
            f=Path(r['output'])/'agent_trajectory.csv'
            if not f.exists():continue
            _,poses=trace(f.parent);color=f"C{r['index']-1}"
            ax.plot(poses[:,0],poses[:,1],c=color,lw=1.4,label=f"{r['run_id']} {r['classification']}")
            ax.plot(*poses[-1,:2],marker='o' if r['success'] else 'x',ms=7,color=color)
        ax.set(title=f'D={round(d*1000)} ms',xlim=(-2.1,6.1),ylim=(-1.6,1.6),xlabel='World X (m)',ylabel='World Y (m)');ax.set_aspect('equal');ax.grid(alpha=.15)

    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([0],[0],color=f'C{i-1}',label=f'S0_{i:02d}') for i in range(1,6)],loc='lower center',ncol=5,frameon=False)
    fig.suptitle('Actual executed center paths | S0 RAW+PP | x = failed termination, o = success',fontsize=12)
    fig.tight_layout(rect=(0,.05,1,.96));fig.savefig(out/'executed_paths_by_delay.png');plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    complete=json.loads((a.run_root/'complete.json').read_text());assert complete['attempts']==20 and complete['reference_preservation']
    plan=json.loads((a.run_root/'plan.json').read_text());records=[json.loads((a.run_root/'metrics'/f"{j['key']}.json").read_text()) for j in plan['jobs']]
    amendments=[]
    for i,r in enumerate(records):
        path=a.run_root/'analysis_amendments'/f"{r['key']}.json"
        if path.exists():
            records[i]=json.loads(path.read_text());amendments.append({'key':r['key'],'sha256':sha256_file(path),'original_causes':(r.get('failure') or {}).get('causes'),'corrected_causes':records[i]['failure']['causes']})
    assert len(records)==20
    a.out.mkdir(parents=True,exist_ok=False)
    summary,failures,last,handoffs=summarize(records)
    summary.update(execution_git_sha=complete['git_sha'],complete=complete,input_plan_sha256=sha256_file(a.run_root/'plan.json'),analysis_amendments=amendments,analysis_source_sha256={'research/nomad_phase3/report.py':sha256_file(Path(__file__)), 'research/nomad_phase3/metrics.py':sha256_file(ROOT/'research/nomad_phase3/metrics.py')})
    write_json(a.out/'summary.json',summary)
    compact=[{k:v for k,v in r.items() if k not in ('request_seeds','handoffs','first_switch','last_three_fresh','input_log_sha256')} for r in records]
    write_json(a.out/'runs.json',compact);write_csv(a.out/'runs.csv',compact)
    write_csv(a.out/'handoffs.csv',handoffs);write_csv(a.out/'failures.csv',failures);write_csv(a.out/'failure_last_three_fresh.csv',last)
    write_csv(a.out/'conditions.csv',[{k:v for k,v in c.items() if k not in ('delivery_delay_s_by_run','pacing_by_run')} for c in summary['conditions']])
    comparison=[d0_comparison(r) for r in records if r['delay_s']==0 and r.get('technical_validation')=='PASS']
    write_json(a.out/'d0_reproduction.json',comparison);write_csv(a.out/'d0_reproduction.csv',comparison)
    plots(a.out,records,summary)
    print(json.dumps({'stage2_delays_ms':summary['stage2_delays_ms'],'conditions':[{k:c[k] for k in ('D_ms','success','collision','corridor','timeout','technical_failures')} for c in summary['conditions']]}))

if __name__=='__main__':main()
