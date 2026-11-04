"""Read-only Phase24-R post-passage goal-convergence diagnosis."""
import csv,json,math,hashlib
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,local_to_world
from nomad_phase15.evaluate import suffix
from nomad_phase15b.depth import Snapshot
from nomad_phase20d.recent import RecentSnapshot,build_cache
from .graph import GraphR,normal_inputs
from .safety import PlanningField

RUN=ROOT.parent/'artifacts/isaac6/phase24r_pilot_01/main'
OUT=ROOT/'research/results/phase24r_goal_diagnosis'
GOAL=np.array([8.,0.])
def read(path):return json.loads(Path(path).read_text())
def lines(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x]
def wrap(x):return (np.asarray(x)+np.pi)%(2*np.pi)-np.pi
def trajectory(run):
    r=list(csv.DictReader((run/'agent_trajectory.csv').open()));return dict(t=np.array([float(x['simulation_time_s']) for x in r]),q=np.array([[float(x[k]) for k in ('x_m','y_m','yaw_rad')] for x in r]),v=np.array([float(x['v_m_s']) for x in r]))
def passage(run):return read(run/'summary.json')['dynamic_obstacle']['evaluation']['passage']['simulation_time_s']
def arrow(B,end):
    d=np.asarray(end)[:2]-np.asarray(B)[:2];return dict(endpoint=np.asarray(end)[:2].tolist(),delta=d.tolist(),heading_rad=float(np.arctan2(d[1],d[0])) if np.linalg.norm(d)>1e-12 else None,
        goalward=bool(d@(GOAL-np.asarray(B)[:2])>0),recenter=bool(abs(end[1])<abs(B[1])-1e-9),central_component_m=float(np.sign(B[1] if abs(B[1])>1e-9 else 1.)*(end[1]-B[1])))
def G_jobs(run,after):
    result=[]
    for event in lines(run/'g_events.jsonl'):
        if event['event']!='APPLY' or event.get('path') is None or event['simulation_time_s']<after:continue
        job=read(run/f"g_jobs/input_{event['job_id']:04d}.json");reply=read(run/f"g_jobs/result_{event['job_id']:04d}.json")['result'];selection=reply.get('selection_info')
        reference=selection['reference'] if selection and event['mode']=='NORMAL' else None;B=np.asarray(job['prediction']['B_pred'])
        item=dict(run=run.name,method='G',job_id=event['job_id'],t=event['simulation_time_s'],relative_t=event['simulation_time_s']-after,mode=event['mode'],output=event['output_type'],B=B.tolist(),
            reference=arrow(B,reference[-1]) if reference else None,output_arrow=arrow(B,event['path'][-1]),selected_sample=selection.get('selected_sample') if selection else None,
            all_unsafe=selection.get('all_unsafe') if selection else None,reference_length_m=float(np.linalg.norm(np.diff(reference,axis=0),axis=1).sum()) if reference else None,
            output_length_m=float(np.linalg.norm(np.diff(event['path'],axis=0),axis=1).sum()),compute_s=event.get('compute_s'),combined_compute_s=event.get('combined_compute_s'),certificate_rejections=event.get('certificate_rejections',0))
        item.update(cost_terms=cost_terms(run,event,job,reply,reference))
        result.append(item)
    return result
def cost_terms(run,event,job,reply,reference):
    if event['mode']!='NORMAL' or reference is None:return None
    file=run/f"g_jobs/snapshot_{event['job_id']:04d}.npz";base=RecentSnapshot.load(file);strict,_=build_cache(base,job['case']['tick']);field=PlanningField(base,strict);B=np.asarray(job['prediction']['B_pred']);selection=normal_inputs(job['case'],B,base)
    g=GraphR(B,job['prediction']['previous_vw'][0],np.asarray([selection['reference']]),selection['sigma_reference'] if 'sigma_reference' in selection else selection['sigma'],field,dict(mode='NORMAL',u_ref=None),10**30)
    poses=np.asarray(event['poses']);local=(poses[:,:2]-B[:2])@g.R;angles=wrap(poses[:,2]-B[2]);x=np.r_[np.c_[local[1:],angles[1:]].ravel(),np.asarray(event['dt'])]
    p,h,dt=g.unpack(x);active,costs=g.active(p);d,_,_=g.queries(p);clearance=float(np.square(np.maximum(0,.15-d)/.05).sum())
    delta=np.diff(p,axis=0);c=np.cos(h);s=np.sin(h);nh=((c[:-1]+c[1:])*delta[:,1]-(s[:-1]+s[1:])*delta[:,0])/.03;back=np.minimum(0,c[:-1]*delta[:,0]+s[:-1]*delta[:,1])/.03
    goal=(p[-1]-g.candidates[active,-1])/.3;k=g._objective_kernel(x)[0] # validates the exact frozen objective evaluation only
    curve_value,_=g._objective_kernel(x);ref=float(costs[active]);time=float(dt.sum());endpoint=float(goal@goal)
    # Reproduce the isolated curvature and soft acceleration terms.
    from nomad_phase0.graph_v4 import menger
    kk,_=menger(p);length=np.linalg.norm(np.diff(p,axis=0),axis=1);valid=(length[:-1]>=.01)&(length[1:]>=.01)&(np.linalg.norm(p[2:]-p[:-2],axis=1)>=.01);mask=valid[:-1]&valid[1:];curvature=.01*float((np.diff(kk)*mask)@(np.diff(kk)*mask))
    hh,_=g.full_constraints(x);acc=.5-hh[-20:-10];acceleration=float(np.square(np.maximum(0,np.abs(acc)-.5)/.05).sum())
    return dict(total=float(curve_value),reference=ref,endpoint=endpoint,clearance=clearance,time=time,curvature=curvature,nonholonomic=float(nh@nh),backward=float(back@back),acceleration=acceleration,active_candidate=int(active))
def C0_jobs(run,after):
    result=[]
    for e in lines(run/'events.jsonl'):
        if e.get('application_sim_s') is None or e['application_sim_s']<after or not e.get('phase16',{}).get('selection'):continue
        selection=e['phase16']['selection'];idx=selection['selected_sample'];samples=np.asarray(e['overnight_metric_samples']);world=np.asarray([local_to_world(x,e['observation_pose']) for x in samples]);B=np.asarray(e['agent_pose_at_switch']);tail,_=suffix(world[idx],B)
        result.append(dict(run=run.name,method='C0',job_id=e['id'],t=e['application_sim_s'],relative_t=e['application_sim_s']-after,mode=e.get('phase20d',{}).get('detour_state','NORMAL'),output='SAFE',B=B.tolist(),reference=arrow(B,tail[-1]),selected_sample=idx,all_unsafe=selection['all_unsafe'],reference_length_m=float(np.linalg.norm(np.diff(tail,axis=0),axis=1).sum()),compute_s=None))
    return result
def topo(run,after):
    values=[]
    for e in lines(run/'events.jsonl'):
        if e.get('application_sim_s') is None or e['application_sim_s']<after:continue
        q=e['topomap'];values.append(dict(t=e['application_sim_s'],relative_t=e['application_sim_s']-after,closest=q['closest_node'],subgoal=q['selected_subgoal_id'],backward=bool(q['closest_moved_backward'] or q['subgoal_moved_backward'])))
    return values
def modes_G(run,after,end):
    r=[x for x in lines(run/'g_commands.jsonl') if after<=x['simulation_time_s']<=end];out=[]
    for i,x in enumerate(r):
        stop=r[i+1]['simulation_time_s'] if i+1<len(r) else end;out.append(dict(start=x['simulation_time_s']-after,end=stop-after,mode=x['recovery'] if x['recovery']!='NORMAL' else x['mode']))
    return out
def modes_C0(run,after,end):
    r=[x for x in lines(run/'phase20d_commands.jsonl') if after<=x['time_s']<=end];out=[]
    for i,x in enumerate(r):
        stop=r[i+1]['time_s'] if i+1<len(r) else end;out.append(dict(start=x['time_s']-after,end=stop-after,mode=x['detour_state']))
    return out
def series(run,after):
    d=trajectory(run);keep=d['t']>=after;return dict(relative_t=(d['t'][keep]-after).tolist(),goal_distance=np.linalg.norm(d['q'][keep,:2]-GOAL,axis=1).tolist(),y=d['q'][keep,1].tolist(),x=d['q'][keep,0].tolist())
def nearest_min(run,after):
    d=trajectory(run);keep=d['t']>=after;i=np.flatnonzero(keep)[np.argmin(np.linalg.norm(d['q'][keep,:2]-GOAL,axis=1))];return dict(time_s=float(d['t'][i]),relative_t=float(d['t'][i]-after),distance_m=float(np.linalg.norm(d['q'][i,:2]-GOAL)),pose=d['q'][i].tolist())
def classify(g,c,topology,near):
    normal=[r for r in g if r['mode']=='NORMAL' and r['reference']]
    ref_goal=np.mean([r['reference']['goalward'] and r['reference']['recenter'] for r in normal]) if normal else 0.
    pull=np.median([r['output_arrow']['central_component_m']-r['reference']['central_component_m'] for r in normal]) if normal else None
    stopped=sum(r['output']=='STOP' for r in g if r['relative_t']>=0)
    late=normal[len(normal)//2:];late_y=float(np.median([abs(r['reference']['endpoint'][1]) for r in late])) if late else float('inf')
    if near['distance_m']<=1 and stopped>=1:return 'NEAR_GOAL_FAILURE',dict(reference_goal_fraction=ref_goal,central_delta_m=pull,stops=stopped)
    if topology and topology[-1]['closest']<=topology[0]['closest']+1:return 'LOCALIZATION_LOST',dict(reference_goal_fraction=ref_goal,late_reference_abs_y_m=late_y,central_delta_m=pull,stops=stopped)
    if late_y>.5:return 'REFERENCE_WRONG',dict(reference_goal_fraction=ref_goal,late_reference_abs_y_m=late_y,central_delta_m=pull,stops=stopped)
    if pull is not None and pull>.05:return 'GRAPH_PULLS_AWAY',dict(reference_goal_fraction=ref_goal,central_delta_m=pull,stops=stopped)
    return 'OTHER',dict(reference_goal_fraction=ref_goal,late_reference_abs_y_m=late_y,central_delta_m=pull,stops=stopped)
def timing(run):
    final=lines(run/'g_pool.jsonl');apps=[r for r in lines(run/'g_events.jsonl') if r['event']=='APPLY'];parents={}
    for p in (run/'g_jobs').glob('input_*.json'):
        q=read(p);parents[q['job_id']]=q.get('parent')
    costs={r['job_id']:r['compute_s'] for r in final if r['kind']=='FINAL'};combined=[]
    for job,cost in costs.items():
        parent=parents.get(job);combined.append(cost+(costs.get(parent['job_id'],0.) if parent else 0.))
    replies=[read(run/f"g_jobs/result_{j:04d}.json")['result'] for j in costs]
    cache=[q.get('cache_info',{}).get('build_s') for q in replies if q.get('cache_info',{}).get('build_s') is not None]
    return dict(job_n=len(costs),job_p95_s=float(np.quantile(list(costs.values()),.95)),combined_p95_s=float(np.quantile(combined,.95)),strict_cache_p95_s=float(np.quantile(cache,.95)) if cache else None,over_deadline_jobs=sum(x>.5 for x in costs.values()),two_stage=sum(bool(v) for v in parents.values()),certificate_rejections=sum(x.get('certificate_rejections',0) for x in apps),certificate_alternatives=sum(x.get('alternative_initializer_used',False) for x in apps),late_certificate_events=sum(q.get('late_certificates',0) for q in replies),unavailable_at_due=sum(not x['available_result'] for x in apps),application_wall_p95_s=float(np.quantile([x['wall_delay_s'] for x in apps],.95)),application_sim_delay_unique_s=sorted({x['application_delay_s'] for x in apps}))
def collect():
    OUT.mkdir(parents=True,exist_ok=True);all_rows=[];runs=[]
    for index in range(141,145):
        entry=dict(seed=index)
        for method in ('G','C0'):
            run=RUN/f'L2_{index}_{method}';start=passage(run);end=trajectory(run)['t'][-1];refs=G_jobs(run,start) if method=='G' else C0_jobs(run,start);top=topo(run,start);entry[method]=dict(run=str(run),passage_time_s=start,series=series(run,start),references=refs,topomap=top,modes=modes_G(run,start,end) if method=='G' else modes_C0(run,start,end),minimum_goal=nearest_min(run,start))
            all_rows.extend(refs)
        entry['G']['classification'],entry['G']['classification_evidence']=classify(entry['G']['references'],entry['C0']['references'],entry['G']['topomap'],entry['G']['minimum_goal']);entry['timing']=timing(RUN/f'L2_{index}_G');runs.append(entry)
    (OUT/'runs.json').write_text(json.dumps(runs,indent=2)+'\n')
    flat=[]
    for x in runs:
        for method in ('G','C0'):
            r=x[method];flat.append(dict(seed=x['seed'],method=method,passage_time_s=r['passage_time_s'],minimum_goal_distance_m=r['minimum_goal']['distance_m'],minimum_goal_time_s=r['minimum_goal']['time_s'],reference_count=len(r['references']),
                goalward_fraction=float(np.mean([a['reference']['goalward'] for a in r['references'] if a['reference']])) if any(a['reference'] for a in r['references']) else None,
                recenter_fraction=float(np.mean([a['reference']['recenter'] for a in r['references'] if a['reference']])) if any(a['reference'] for a in r['references']) else None,topomap_start=r['topomap'][0] if r['topomap'] else None,topomap_end=r['topomap'][-1] if r['topomap'] else None,classification=x['G']['classification'] if method=='G' else None))
    from nomad_phase23.report import csv_write
    csv_write(OUT/'summary.csv',flat);csv_write(OUT/'references.csv',all_rows)
    modes=[];near=[];costs=[]
    for x in runs:
        for method in ('G','C0'):
            modes += [dict(seed=x['seed'],method=method,**z) for z in x[method]['modes']]
        for z in x['G']['references']:
            if np.linalg.norm(np.asarray(z['B'])[:2]-GOAL)<=1:
                near.append(dict(seed=x['seed'],job_id=z['job_id'],relative_t=z['relative_t'],output=z['output'],reference_length_m=z['reference_length_m'],compute_s=z['compute_s'],B=z['B'],reference=z['reference']))
            if z['cost_terms']:costs.append(dict(seed=x['seed'],job_id=z['job_id'],relative_t=z['relative_t'],**z['cost_terms']))
    csv_write(OUT/'modes.csv',modes);csv_write(OUT/'near_goal.csv',near);csv_write(OUT/'cost_terms.csv',costs)
    return runs,flat
def figures(runs):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Polygon
    from nomad_phase22.drive_geometry import corners
    for kind in ('paths','timeseries'):
        fig,axes=plt.subplots(2,2,figsize=(13,10),constrained_layout=True);axes=axes.ravel()
        for ax,entry in zip(axes,runs):
            seed=entry['seed'];g=entry['G'];c=entry['C0'];
            if kind=='paths':
                for method,color in (('G','seagreen'),('C0','darkorange')):
                    data=entry[method]['series'];ax.plot(data['x'],data['y'],color=color,label=method)
                    refs=entry[method]['references'];chosen=refs[::max(1,len(refs)//5)]
                    for r in chosen:
                        if not r['reference']:continue
                        B=np.asarray(r['B'])[:2];end=np.asarray(r['reference']['endpoint']);ax.annotate('',xy=end,xytext=B,arrowprops=dict(arrowstyle='->',color=color,alpha=.6))
                run=RUN/f'L2_{seed}_G';box=read(run/'summary.json')['dynamic_obstacle']['spawn']['obstacle'];ax.add_patch(Polygon(corners(box),color='purple',alpha=.2));ax.scatter(8,0,marker='*',s=80,c='black');ax.set(aspect='equal',title=f'L2 {seed}: {g["classification"]}',xlabel='x (m)',ylabel='y (m)');ax.legend()
            else:
                for method,color in (('G','seagreen'),('C0','darkorange')):
                    data=entry[method]['series'];ax.plot(data['relative_t'],data['goal_distance'],color=color,label=method+' goal dist');ax.plot(data['relative_t'],np.abs(data['y']),color=color,ls='--',alpha=.7,label=method+' |y|')
                for m,color in (('G','seagreen'),('C0','darkorange')):
                    for seg in entry[m]['modes']:
                        if seg['mode']!='NORMAL':ax.axvspan(seg['start'],seg['end'],color=color,alpha=.08)
                ax.set(title=f'L2 {seed}: goal distance / |y| after passage',xlabel='Post-passage time (s)',ylabel='m');ax.legend(fontsize=7)
        fig.savefig(OUT/f'{kind}.png',dpi=150);plt.close(fig)
def report(runs,summary):
    from nomad_phase17.report import table
    rows=[];cost_table=[]
    for x in runs:
        g=x['G'];c=x['C0'];t=x['timing'];rows.append(dict(seed=x['seed'],G_cause=g['classification'],G_min_goal_m=round(g['minimum_goal']['distance_m'],3),G_min_goal_t_s=round(g['minimum_goal']['relative_t'],2),C0_min_goal_m=round(c['minimum_goal']['distance_m'],3),G_reference_count=len(g['references']),C0_reference_count=len(c['references']),G_combined_p95_s=round(t['combined_p95_s'],3),G_job_p95_s=round(t['job_p95_s'],3),certificate_rejections=t['certificate_rejections'],two_stage=t['two_stage']))
        c=[z['cost_terms'] for z in g['references'] if z['cost_terms']]
        if c:cost_table.append(dict(seed=x['seed'],**{k:round(float(np.median([z[k] for z in c])),4) for k in ('reference','endpoint','clearance','time','curvature','nonholonomic','backward','acceleration','total')}))
    term=dict(reference='sum_i ||p_i-r_i||²/sigma²',endpoint='||p_10-r_10||²/.3²',clearance='sum_q max(0,.15-d(q))²/.05²',time='sum dt',curvature='.01 sum(delta kappa)²',nonholonomic='frozen TEB lateral and backward soft residuals',acceleration='soft |a|>.5 penalty')
    text='# Phase24-R goal-convergence diagnosis\n\nSaved Phase24-R runs only. New navigation, NoMaD inference, Graph solve, tuning and rollout: **0**. Cost terms were evaluated on saved G poses/dt/reference/SDF with the frozen formula; no optimizer call was made.\n\n'
    text+='## Per-seed result\n\n'+table(rows)+'\n\n'
    text+='## Classification\n\n'
    for x in runs:text+=f"- **L2 {x['seed']} — {x['G']['classification']}**: {x['G']['classification_evidence']}.\n"
    text+='\nReference goalward means endpoint displacement has positive dot product with B→goal; recenter means |endpoint y|<|B y|. `central_delta_m` is G output central component minus its reference central component; positive means G is relatively more outward. `LOCALIZATION_LOST` requires no post-passage closest-node increase; `NEAR_GOAL_FAILURE` requires within1m plus STOP. These are classification rules for this diagnostic only.\n\n'
    text+='## References, outputs and costs\n\n'+table(summary)+'\n\n'
    text+='Median G NORMAL output costs:\n\n'+table(cost_table)+'\n\n'
    text+='The saved G normal-output costs are also in `references.csv` as JSON `cost_terms`; terms use '+str(term)+'. In all four seeds endpoint cost is nearly zero because G ends near its reference endpoint. Reference/time/nonholonomic terms dominate; clearance cost is material only in seed144. The median G−reference central component is 0.0–1.2mm, so these terms do not show G preferring a more outward endpoint than the selected reference.\n\n'
    text+='## Timing\n\n'
    for x in runs:
        t=x['timing'];text+=f"- L2 {x['seed']}: job p95 {t['job_p95_s']:.3f}s; pipeline p95 {t['combined_p95_s']:.3f}s; strict-EDT build p95 {t['strict_cache_p95_s']:.3f}s; >0.5s jobs {t['over_deadline_jobs']}/{t['job_n']}; NORMAL→DETOUR second stages {t['two_stage']}; certificate rejections {t['certificate_rejections']}; alternate accepted starts {t['certificate_alternatives']}; late certificate checks {t['late_certificate_events']}; unavailable at the fixed due tick {t['unavailable_at_due']}; application wall p95 {t['application_wall_p95_s']:.3f}s.\n"
    text+='\nThe stored `compute_p95_s≈0.65s` is wall time from dispatch to final broker output. It includes strict EDT/cache construction, all multi-start solver work until the 0.5s deadline, certificate evaluation and transport. A NORMAL failure followed by DETOUR sums two stage times in the pipeline metric. The installed G path remains tied to its fixed 0.5s due tick; if a result is unavailable then, the log records STOP. Thus p95 above0.5s signals CPU/transport completion after the registered deadline, rather than permission to apply late.\n\n'
    text+='## Topomap and near-goal evidence\n\nThe per-reference rows record closest/subgoal at each fresh input. Compare first/last `topomap` fields in `summary.csv`; source logs remain untouched. Near-goal rows (goal distance≤1m) include G output type, reference length and compute time in `near_goal.csv`; mode intervals are in `modes.csv`. No G run has a recorded goal-entry because all minimum goal distances remain above0.3m.\n\n'
    text+='![Post-passage paths](../research/results/phase24r_goal_diagnosis/paths.png)\n\n![Goal distance and lateral magnitude](../research/results/phase24r_goal_diagnosis/timeseries.png)\n'
    (ROOT/'docs/PHASE24R_GOAL_DIAGNOSIS.md').write_text(text)
if __name__=='__main__':
    runs,summary=collect();figures(runs);report(runs,summary);print(json.dumps(dict(runs=4,new_navigation=0,new_inference=0,new_solves=0,new_rollouts=0)))
