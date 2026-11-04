"""Read-only Phase24 pilot diagnosis. No solver, rollout, inference or renderer."""
import csv,json,re,hashlib
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from nomad_isaac.common import ROOT
from nomad_isaac.clearance import segment_clearance,configured_obstacles
from nomad_phase22.drive_geometry import point_gap,local_pose,corners
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase15b.depth import Snapshot
from nomad_phase24.graph import normal_inputs,fan_paths
from nomad_phase20c.detour import ANGLES
from nomad_phase23.report import csv_write
from nomad_phase17.report import table

RUN=ROOT.parent/'artifacts/isaac6/phase24_pilot_01/main'
OUT=ROOT/'research/results/phase24_diagnosis'
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s]
def wrap(x):return (np.asarray(x)+np.pi)%(2*np.pi)-np.pi
def trajectory(run):
    rows=list(csv.DictReader((run/'agent_trajectory.csv').open()))
    return dict(t=np.array([float(r['simulation_time_s']) for r in rows]),q=np.array([[float(r[k]) for k in ('x_m','y_m','yaw_rad')] for r in rows]),
        v=np.array([float(r['v_m_s']) for r in rows]),w=np.array([float(r['w_rad_s']) for r in rows]),ns=np.array([int(r['monotonic_ns']) for r in rows]))
def oracle_points(q,config,box=None):
    co=config['corridor'];r=config['agent_radius_m'];q=np.asarray(q);wall=np.minimum.reduce([q[:,0]-co['xmin'],co['xmax']-q[:,0],q[:,1]+co['half_width'],co['half_width']-q[:,1]])-r
    boxes=configured_obstacles(config)+([box] if box else [])
    obstacle=np.min([[point_gap(p,b,r) for p in q] for b in boxes],axis=0) if boxes else np.full(len(q),np.inf)
    return np.minimum(wall,obstacle)
def oracle_path(p,config,box=None):
    boxes=configured_obstacles(config)+([box] if box else []);gap=float(oracle_points(p,config,box).min())
    for b in boxes:
        local=np.array([local_pose(np.r_[q,0.],b)[:2] for q in p]);half=np.array(b['size_xyz_m'][:2])/2
        gap=min(gap,min(segment_clearance(a,z,-half,half,config['agent_radius_m'])[0] for a,z in zip(local[:-1],local[1:])))
    return gap
def query_points(p):return np.vstack([p,(p[:-1]+p[1:])/2])
def dense_path(p,step=.005):return np.vstack([np.linspace(a,b,max(2,int(np.ceil(np.linalg.norm(b-a)/step))+1)) for a,b in zip(p[:-1],p[1:])])
def cell_fraction(field,p,mask):
    ij,ok=field.cells(p);return float(np.mean(mask[ij[ok,1],ij[ok,0]])) if ok.any() else None
def matching_candidate(result,app):
    if app['path'] is None:return None
    p=np.asarray(app['path']);possible=[]
    for message in result['anytime_messages']:
        for value in (message,message.get('last_candidate') or {}):
            if value.get('path') is not None and np.array_equal(np.asarray(value['path']),p):possible.append(dict(value,index=message['index']))
    chosen=result.get('selected')
    if chosen and np.array_equal(np.asarray(chosen['path']),p):possible.append(chosen)
    assert possible,'Applied path must match a saved received solver candidate'
    return max(possible,key=lambda r:r.get('ready_ns',0))

def application(run,app,full=False):
    j=app['job_id'];job=read(run/f'g_jobs/input_{j:04d}.json');result=read(run/f'g_jobs/result_{j:04d}.json')['result'];field=Snapshot.load(run/f'g_jobs/snapshot_{j:04d}.npz');B=np.asarray(job['prediction']['B_pred'])
    selected=matching_candidate(result,app);normal=normal_inputs(job['case'],B,field) if job['mode']=='NORMAL' else None
    starts=normal['starts'] if normal else fan_paths(B,job['u_ref']);names=normal['names'] if normal else ['FAN_'+str(a) for a in ANGLES]
    data=trajectory(run);tick=app['tick'];assert np.linalg.norm(data['q'][tick,:2]-np.asarray(app['pose'])[:2])<1e-10
    error=float(np.linalg.norm(np.asarray(app['pose'])[:2]-B[:2]));assert abs(error-app['prediction_error_m'])<1e-10
    m={r['id']:r for r in lines(run/'model/inference.jsonl')};topo=m[job['fresh_id']]['topomap'];summary=read(run/'summary.json');config=summary['scenario'];spawn=summary.get('dynamic_obstacle',{}).get('spawn');box=spawn['obstacle'] if spawn else None
    row=dict(run=run.name,job=j,t=app['simulation_time_s'],dispatch_t=job['dispatch_tick']/72,mode=job['mode'],reason=job['reason'],output=app['output_type'],prediction_error_m=error,prediction_yaw_error_deg=float(abs(wrap(app['pose'][2]-B[2]))*180/np.pi),map_frame=field.metadata['frame_id'],map_age_at_dispatch_s=job['dispatch_tick']/72-field.metadata['sim_s'],
        fresh_id=job['fresh_id'],closest=topo['closest_node'],subgoal=topo['selected_subgoal_id'],selected_sample=normal['selected_sample'] if normal else None,all_unsafe=normal['all_unsafe'] if normal else None,
        reference_endpoint=normal['reference'][-1].tolist() if normal else None,reference_dx=float(normal['reference'][-1,0]-B[0]) if normal else None,
        native_endpoint=np.asarray(job['case']['samples_world'])[normal['selected_sample'],-1].tolist() if normal else None,initialization=names[selected['index']] if selected else None,
        starts=names,reference_path=normal['reference'].tolist() if normal else None,selected_initial_path=np.asarray(starts[selected['index']]).tolist() if selected else None,apply_pose=app['pose'],predicted_pose=B.tolist(),u_ref=job['u_ref'])
    if app['path'] is not None:
        p=np.asarray(app['path']);poses=np.asarray(app['poses']);dt=np.asarray(app['dt']);q=query_points(p);length=np.linalg.norm(np.diff(p,axis=0),axis=1);s=np.r_[0,np.cumsum(length)];sq=np.r_[s,(s[:-1]+s[1:])/2]
        depth=field.query(q)[0];cb=float(field.query(B[None,:2])[0][0]);margin=np.where(sq<=.3+1e-12,min(.025,max(0.,cb-.005)),.025);v=length/dt;w=wrap(np.diff(poses[:,2]))/dt;slack=depth-margin
        row.update(path_length_m=float(length.sum()),path_endpoint=p[-1].tolist(),path_dx=float(p[-1,0]-B[0]),distance_to_endpoint_at_apply_m=float(np.linalg.norm(np.asarray(app['pose'])[:2]-p[-1])),depth_node_mid_min_m=float(depth.min()),depth_f2_min_slack_m=float(slack.min()),depth_start_margin_m=float(margin[0]),
            oracle_node_min_m=float(oracle_points(p,config,box).min()),oracle_mid_min_m=float(oracle_points((p[:-1]+p[1:])/2,config,box).min()),oracle_node_mid_min_m=float(oracle_points(q,config,box).min()),oracle_segment_min_m=oracle_path(p,config,box),
            depth_continuous_min_m=float(field.exact_clearance(p)),unknown_path_fraction=cell_fraction(field,dense_path(p),~field.observed),v_max=float(v.max()),omega_max=float(abs(w).max()),dt_min=float(dt.min()),dt_max=float(dt.max()),
            active_obstacle=int(np.sum(abs(slack)<=1e-5)),active_speed=int(np.sum(abs(v-.3)<=1e-5)),active_omega=int(np.sum(abs(abs(w)-.4)<=1e-5)),active_dt=int(np.sum((abs(dt-.05)<=1e-5)|(abs(dt-1)<=1e-5))),
            initial_chord_heading_error_deg=float(abs(wrap(np.arctan2(*(p[1]-p[0])[::-1])-app['pose'][2]))*180/np.pi))
    latest={}
    for msg in result['anytime_messages']:latest[msg['index']]={**latest.get(msg['index'],{}),**msg}
    row['last_iterate_constraints']=[dict(initialization=names[i],**{k:v.get(k) for k in ('active_obstacle','violated_obstacle','active_kinematic','violated_kinematic','active_dt_bound','message')}) for i,v in sorted(latest.items())]
    if full:return row,dict(field=field,job=job,result=result,normal=normal,starts=starts,app=app,config=config,box=box)
    return row

def span_rows(run,start,end):
    apps=[e for e in lines(run/'g_events.jsonl') if e['event']=='APPLY'];last=[e for e in apps if e['simulation_time_s']<start]
    return [application(run,e) for e in (last[-1:]+[e for e in apps if start<=e['simulation_time_s']<=end])]
def intervals(mask,t):
    edges=np.diff(np.r_[False,mask,False].astype(int));return [(int(a),int(b-1)) for a,b in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1))]

def wall_geometry(file):
    text=Path(file).read_text();result={}
    for name in ('LeftWall','RightWall'):
        part=text.split('def Cube "'+name+'"',1)[1].split('}',1)[0]
        values={key:np.fromstring(re.search(r'xformOp:'+key+r' = \(([^)]+)\)',part).group(1),sep=',') for key in ('translate','scale')}
        result[name]=dict(center=values['translate'].tolist(),scale=values['scale'].tolist(),inner_y=float(values['translate'][1]+(-1 if name=='LeftWall' else 1)*values['scale'][1]/2))
    return result

def failure_map(run,data):
    updates=lines(run/'depth/updates.jsonl');eligible=[r for r in updates if r['publication_monotonic_ns']<=int(data['ns'][-1])];latest=max(eligible,key=lambda r:r['publication_monotonic_ns']);choices=[]
    for r in eligible:
        f=run/'depth'/Path(r['file']).name
        if f.exists():choices.append((r['publication_monotonic_ns'],f,r))
    final=run/'depth/final.npz'
    if final.exists():
        f=Snapshot.load(final);r=dict(f.metadata)
        if r['publication_monotonic_ns']<=int(data['ns'][-1]):choices.append((r['publication_monotonic_ns'],final,r))
    _,file,meta=max(choices,key=lambda r:r[0]);return Snapshot.load(file),dict(file=str(file),exact_latest_published_at_failure=meta['frame_id']==latest['frame_id'],frame=meta['frame_id'],age_s=float(data['t'][-1]-meta['sim_s']))

def boundary_row(run):
    data=trajectory(run);config=read(run/'scenario.json');q=data['q'][-1];field,info=failure_map(run,data);edge=np.array([q[0],np.sign(q[1])*config['corridor']['half_width']]);h=field.h
    lo=np.maximum(0,np.floor((edge-[.10,.03]-field.origin)/h).astype(int));hi=np.minimum(np.array(field.occupied.shape[::-1]),np.ceil((edge+[.10,.03]-field.origin)/h).astype(int)+1)
    area=np.s_[lo[1]:hi[1],lo[0]:hi[0]];geometry=wall_geometry(run/'scene.usda')
    return dict(run=run.name,method=config['phase24_method'],time_s=float(data['t'][-1]),x=float(q[0]),y=float(q[1]),virtual_wall_y=float(edge[1]),rendered_wall_y=geometry['LeftWall' if q[1]>0 else 'RightWall']['inner_y'],
        boundary_occupied_cells=int(field.occupied[area].sum()),boundary_cells=int(field.occupied[area].size),boundary_observed_fraction=float(field.observed[area].mean()),depth_clearance_at_stop_m=float(field.query(q[None,:2])[0][0]),oracle_wall_clearance_m=float(config['corridor']['half_width']-abs(q[1])-config['agent_radius_m']),
        label='SCENE_BOUNDARY_NOT_PERCEIVABLE' if abs(abs(geometry['LeftWall']['inner_y'])-config['corridor']['half_width'])>1e-6 else 'RENDERED_BOUNDARY_MATCHES',**info)

def prior_boundaries():
    rows=[]
    groups={'Phase16_SL_gate':list((ROOT.parent/'artifacts/isaac6/phase16_multiscene_01/gate').glob('SL_*/scene.usda'))}
    for phase in ('phase17','phase18'):
        groups[phase+'_SLW']=[Path(r['output'])/'scene.usda' for r in read(ROOT/f'research/results/{phase}/runs.json') if r.get('scene')=='SLW']
    for group,files in groups.items():
        for f in files:
            c=read(f.parent/'scenario.json');g=wall_geometry(f);rows.append(dict(group=group,run=f.parent.name,half_width=c['corridor']['half_width'],positive_inner_y=g['LeftWall']['inner_y'],negative_inner_y=g['RightWall']['inner_y'],matches=abs(g['LeftWall']['inner_y']-c['corridor']['half_width'])<1e-6 and abs(g['RightWall']['inner_y']+c['corridor']['half_width'])<1e-6,usd_sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    return rows

def collect():
    OUT.mkdir(parents=True,exist_ok=True)
    run=RUN/'L2_132_G';data=trajectory(run);end=float(data['t'][-1]);collision=span_rows(run,end-3,end);last=collision[-1];app=next(e for e in lines(run/'g_events.jsonl') if e['event']=='APPLY' and e['job_id']==last['job']);p=np.asarray(app['path']);poly=XYPath(p);chosen=data['t']>=app['simulation_time_s'];xt=[poly.project(q[:2])[1] for q in data['q'][chosen]]
    # Verify the frozen XYPath returns metric distance, then report measured deviation.
    detail=dict(last_job=last['job'],collision_time_s=end,actual_final_pose=data['q'][-1].tolist(),actual_minimum_clearance_m=read(run/'summary.json')['dynamic_obstacle']['evaluation']['minimum_swept_clearance_lower_m'],max_cross_track_m=float(max(xt)),last_cross_track_m=float(xt[-1]),last_command_v=float(data['v'][-1]),last_command_w=float(data['w'][-1]),primary='OTHER',mechanism='EXECUTION_WITH_RELAXED_START_MARGIN')
    first=np.asarray(app['poses']);delta=first[1,:2]-first[0,:2]
    detail.update(first_segment_m=float(np.linalg.norm(delta)),first_dt_s=app['dt'][0],first_speed_m_s=float(np.linalg.norm(delta)/app['dt'][0]),first_chord_forward_projection_m=float(delta@np.array([np.cos(first[0,2]),np.sin(first[0,2])])),first_chord_heading_error_deg=last['initial_chord_heading_error_deg'])
    entries=[e for e in lines(run/'g_events.jsonl') if e['event']=='MODE_ENTER' and e.get('reason')=='TRIGGER_B'];entry=entries[-1]
    detail.update(previous_detour_trigger_s=entry['simulation_time_s'],component_birth_s=entry['direction']['component']['t_new_tick']/72,component_new_window_expires_s=entry['direction']['component']['t_new_tick']/72+10.)
    assert last['oracle_segment_min_m']>0 and detail['actual_minimum_clearance_m']<0 and last['prediction_error_m']<1e-10
    run=RUN/'L2_131_G';data=trajectory(run);x=data['q'][:,0];peak=np.maximum.accumulate(x);end_i=int(np.argmax(peak-x));start_i=int(np.argmax(x[:end_i+1]));reverse=span_rows(run,float(data['t'][start_i]),float(data['t'][end_i]));events=lines(run/'g_events.jsonl');selected=[e for e in events if data['t'][start_i]<=e.get('simulation_time_s',-1)<=data['t'][end_i]]
    commands=[r for r in lines(run/'g_commands.jsonl') if data['t'][start_i]<=r['simulation_time_s']<=data['t'][end_i]]
    reverse_summary=dict(start_s=float(data['t'][start_i]),end_s=float(data['t'][end_i]),peak_x=float(x[start_i]),minimum_x=float(x[end_i]),backtrack_m=float(x[start_i]-x[end_i]),mode_counts=dict(Counter(r['mode'] for r in commands)),trigger_conditions=dict(Counter(r['reason'] for r in selected if r['event']=='NEW_OBSTACLE_CONDITION')),
        mode_entries=[r for r in selected if r['event']=='MODE_ENTER'],mode_exits=[r for r in selected if r['event']=='MODE_EXIT'],C0_metrics=read(ROOT.parent/'artifacts/isaac6/phase24_pilot_01/metrics/L2_131_C0.json'))
    reverse_summary['earlier_B_entries']=[dict(time_s=e['simulation_time_s'],component_birth_s=e['direction']['component']['t_new_tick']/72) for e in events if e['event']=='MODE_ENTER' and e.get('reason')=='TRIGGER_B']
    run=RUN/'L2_133_G';data=trajectory(run);mask=(data['q'][:,0]>6.5)&(abs(data['v'])<.01);spans=[(a,b) for a,b in intervals(mask,data['t']) if data['t'][b]-data['t'][a]>=2.]
    stops=[dict(start_s=float(data['t'][a]),end_s=float(data['t'][b]),duration_s=float(data['t'][b]-data['t'][a]),pose=data['q'][a].tolist()) for a,b in spans]
    start=max(0.,float(data['t'][spans[-1][0]])-1.) if spans else 80.;goal_rows=span_rows(run,start,90.);commands=[r for r in lines(run/'g_commands.jsonl') if r['simulation_time_s']>=start]
    goal=dict(stop_intervals=stops,window_start_s=start,final_pose=data['q'][-1].tolist(),goal_distance_m=float(np.linalg.norm(data['q'][-1,:2]-[8,0])),stop_reasons=dict(Counter(r['diag']['mode'] for r in commands)),mode_counts=dict(Counter(r['mode'] for r in commands)),output_counts=dict(Counter(r['output'] for r in goal_rows)))
    if stops:
        stop=stops[-1];cc=[r for r in commands if stop['start_s']<=r['simulation_time_s']<=stop['end_s']]
        goal['stationary_command_reasons']=dict(Counter(r['diag']['mode'] for r in cc))
    goal.update(final_command=commands[-1]['command'],final_command_mode=commands[-1]['diag']['mode'])
    boundaries=[boundary_row(RUN/f'SLW_{seed}_{method}') for seed in range(131,135) for method in ('C0','C1','G')];prior=prior_boundaries()
    value=dict(collision=collision,collision_detail=detail,reverse=reverse,reverse_summary=reverse_summary,goal=goal,goal_rows=goal_rows,boundaries=boundaries,prior_boundaries=prior,new_navigation=0,new_inference=0,new_solves=0,new_rollouts=0)
    from nomad_phase19r.evaluate import clean
    value=clean(value);(OUT/'evidence.json').write_text(json.dumps(value,indent=2)+'\n')
    for name in ('collision','reverse','goal_rows','boundaries','prior_boundaries'):
        file=OUT/(name+'.csv');csv_write(file,value[name]);file.write_bytes(file.read_bytes().replace(b'\r\n',b'\n'))
    return value

def show_map(ax,field,bounds):
    lo=np.maximum(0,np.floor((np.array(bounds)[[0,2]]-field.origin)/field.h).astype(int));hi=np.minimum(np.array(field.values.shape[::-1]),np.ceil((np.array(bounds)[[1,3]]-field.origin)/field.h).astype(int)+1)
    area=np.s_[lo[1]:hi[1],lo[0]:hi[0]];y,x=np.nonzero(field.occupied[area]);q=field.origin+np.c_[x+lo[0],y+lo[1]]*field.h
    ax.scatter(q[:,0],q[:,1],s=2,c='.3',alpha=.45,label='Depth occupied',rasterized=True)
def scene(ax,config,box=None,physical=False):
    from matplotlib.patches import Polygon
    for b in configured_obstacles(config)+([box] if box else []):ax.add_patch(Polygon(corners(b),facecolor='mediumpurple',edgecolor='purple',alpha=.25))
    h=config['corridor']['half_width']
    for y in (-h,h):ax.axhline(y,c='firebrick' if physical else '.25',ls='--' if physical else '-',lw=1,label='Evaluation boundary' if y==h else None)
def path_trace(ax,data,start=None,end=None,label='Actual',color=None):
    from matplotlib.collections import LineCollection
    mask=np.ones(len(data['t']),bool)
    if start is not None:mask&=data['t']>=start
    if end is not None:mask&=data['t']<=end
    q=data['q'][mask,:2];t=data['t'][mask]
    if color:ax.plot(*q.T,c=color,lw=2,label=label);return
    lc=LineCollection(np.stack([q[:-1],q[1:]],axis=1),cmap='viridis',linewidth=2,label=label);lc.set_array(t[1:]);ax.add_collection(lc);return lc
def figures(value):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle,Polygon
    plt.rcParams.update({'font.size':9})
    run=RUN/'L2_132_G';data=trajectory(run);events=lines(run/'g_events.jsonl');app=next(e for e in events if e['event']=='APPLY' and e['job_id']==26);row,details=application(run,app,True);p=np.asarray(app['path']);field=details['field'];box=details['box'];config=details['config'];B=np.array(app['pose']);end=data['q'][-1]
    fig,axes=plt.subplots(1,3,figsize=(16,5),constrained_layout=True);bounds=(2.6,4.4,-1.5,.85);scene(axes[0],config,box);show_map(axes[0],field,bounds)
    for r in value['collision']:
        a=next(e for e in events if e['event']=='APPLY' and e['job_id']==r['job'])
        if a['path'] is not None:q=np.array(a['path']);axes[0].plot(*q.T,'--',label=f"j{r['job']} {r['output']}")
    reference=details['normal']['reference'];axes[0].plot(*reference.T,':',c='black',lw=1.5,label='j26 reference = initial (sample2)')
    lc=path_trace(axes[0],data,data['t'][-1]-3);axes[0].scatter(*end[:2],marker='x',s=60,c='red',label='Collision');axes[0].set(xlim=bounds[:2],ylim=bounds[2:],aspect='equal',title='L2 132 G: last 3 seconds');axes[0].legend(fontsize=7);fig.colorbar(lc,ax=axes[0],label='Time (s)',shrink=.7)
    ax=axes[1];ax.add_patch(Polygon(corners(box),facecolor='.8',edgecolor='.4'));ax.plot(*p[:2].T,'o--',c='seagreen',label='Planned first segment');path_trace(ax,data,app['simulation_time_s'],color='black');ax.add_patch(Circle(end[:2],.09,fill=False,color='red',label='Footprint at collision'));ax.add_patch(Circle(B[:2],.09,fill=False,color='seagreen',ls=':'))
    ax.arrow(B[0],B[1],.05*np.cos(B[2]),.05*np.sin(B[2]),width=.0008,color='black',label='Heading direction');ax.set(xlim=(2.9,3.12),ylim=(.08,.3),aspect='equal',title='Safe polyline; forward motion hits the front');ax.legend(fontsize=7)
    ax=axes[2];q=dense_path(p);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))];ax.plot(s,field.query(q)[0]*100,label='Depth SDF');ax.plot(s,oracle_points(q,config,box)*100,label='Oracle footprint');ax.axhline(0,c='red');ax.axhline(2.5,c='.4',ls=':',label='2.5 cm nominal margin');ax.axvspan(0,.3,color='gold',alpha=.15,label='Relaxed start');ax.set(xlabel='Path arclength (m)',ylabel='Clearance (cm)',title='j26: node/mid and exact segment both safe');ax.legend(fontsize=8)
    fig.savefig(OUT/'L2_132.png',dpi=160);plt.close(fig)

    run=RUN/'L2_131_G';g=trajectory(run);c=trajectory(RUN/'L2_131_C0');summary=read(run/'summary.json');box=summary['dynamic_obstacle']['spawn']['obstacle'];r=value['reverse_summary'];fig,axes=plt.subplots(3,1,figsize=(12,11),constrained_layout=True)
    ax=axes[0];scene(ax,summary['scenario'],box);path_trace(ax,c,label='C0',color='darkorange');path_trace(ax,g,label='G',color='seagreen')
    for job in (34,40,50):
        row=next(x for x in value['reverse'] if x['job']==job);B=np.array(row['predicted_pose']);target=np.array(row['reference_endpoint']);ax.annotate('',xy=target,xytext=B[:2],arrowprops=dict(arrowstyle='->',color='crimson'));ax.text(*B[:2],f'j{job}/s{row["selected_sample"]}',fontsize=7)
    other_box=read(RUN/'L2_131_C0'/'summary.json')['dynamic_obstacle']['spawn']['obstacle'];ax.add_patch(Polygon(corners(other_box),fill=False,edgecolor='darkorange',ls=':',label='C0 box'))
    ax.set(xlim=(-.2,8.4),ylim=(-1.6,1.6),aspect='equal',title='L2 131: backward NoMaD references in NORMAL');ax.legend()
    ax=axes[1];ax.plot(g['t'],g['q'][:,0],label='G',c='seagreen');ax.plot(c['t'],c['q'][:,0],label='C0',c='darkorange');ax.axvspan(r['start_s'],r['end_s'],color='red',alpha=.10,label='Largest backtrack');ax.scatter([x['t'] for x in value['reverse'] if x['reference_endpoint']],[x['reference_endpoint'][0] for x in value['reverse'] if x['reference_endpoint']],s=12,c='crimson',label='G reference endpoint x');ax.set(xlabel='Time (s)',ylabel='x (m)',title=f"Backtrack {r['backtrack_m']:.3f} m; 209 NO_NEW_OBSTACLE_AHEAD denials");ax.legend()
    ax=axes[2]
    for key,color in [('L2_131_G','seagreen'),('L2_131_C0','darkorange')]:
        inference=lines(RUN/key/'model/inference.jsonl');ax.step([x['observation_sim_s'] for x in inference],[x['topomap']['selected_subgoal_id'] for x in inference],where='post',label=key,color=color)
    ax.set(xlabel='Observation time (s)',ylabel='Subgoal index',title='Saved Topomap choices (not a relocalization rerun)');ax.legend();fig.savefig(OUT/'L2_131.png',dpi=150);plt.close(fig)

    run=RUN/'L2_133_G';g=trajectory(run);s=value['goal']['stop_intervals'][-1];fig,axes=plt.subplots(1,3,figsize=(16,5),constrained_layout=True);ax=axes[0];lc=path_trace(ax,g,60);ax.add_patch(Circle((8,0),.3,color='seagreen',alpha=.15,label='Goal tolerance'));ax.scatter(8,0,marker='*',c='seagreen',s=90);ax.scatter(s['pose'][0],s['pose'][1],marker='s',c='red',label='Stationary window');ax.axvline(9,color='black',label='Rendered end wall')
    for job,color in ((61,'orange'),(64,'steelblue'),(67,'purple')):
        app=next(e for e in lines(run/'g_events.jsonl') if e['event']=='APPLY' and e['job_id']==job);p=np.array(app['path']);ax.plot(*p.T,'--',color=color,label=f'j{job} FEASIBLE')
    ax.set(xlim=(6.4,9.15),ylim=(-.35,1.55),aspect='equal',title='L2 133: goal overshoot, then stop/rotation');ax.legend(fontsize=7);fig.colorbar(lc,ax=ax,label='Time (s)',shrink=.65)
    ax=axes[1];mask=g['t']>=60;ax.plot(g['t'][mask],g['v'][mask]);ax.axvspan(s['start_s'],s['end_s'],color='red',alpha=.12);ax.set(xlabel='Time (s)',ylabel='Actual speed (m/s)',title='2.99 s stationary; moving again before timeout')
    ax=axes[2];levels={'STOP':0,'KINEMATIC_TOLERATED':1,'FEASIBLE':2};rr=value['goal_rows'];ax.scatter([x['t'] for x in rr],[levels[x['output']] for x in rr],c=['crimson' if x['mode']=='DETOUR' else 'steelblue' for x in rr]);ax.axvspan(s['start_s'],s['end_s'],color='red',alpha=.1);ax.set(yticks=[0,1,2],yticklabels=list(levels),xlabel='Apply time (s)',title='Blue NORMAL / red DETOUR outputs');fig.savefig(OUT/'L2_133.png',dpi=160);plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(16,6),constrained_layout=True)
    for ax,method in zip(axes,('C0','C1','G')):
        run=RUN/f'SLW_131_{method}';data=trajectory(run);config=read(run/'scenario.json');field,info=failure_map(run,data);geom=wall_geometry(run/'scene.usda');scene(ax,config,physical=True);show_map(ax,field,(0,3.4,-1.65,1.65))
        for name in ('LeftWall','RightWall'):ax.axhline(geom[name]['inner_y'],c='black',lw=3,label='Rendered wall' if name=='LeftWall' else None)
        path_trace(ax,data,color='steelblue');q=data['q'][-1];ax.add_patch(Circle(q[:2],.09,fill=False,color='red'));ax.scatter(*q[:2],marker='x',c='red');r=next(x for x in value['boundaries'] if x['run']==run.name)
        ax.set(xlim=(0,3.4),ylim=(-1.65,1.65),aspect='equal',title=f"{method}: virtual wall cells occupied = 0\nmap age {info['age_s']:.3f}s; depth clearance {r['depth_clearance_at_stop_m']:.3f}m");ax.legend(fontsize=7,loc='upper left')
    fig.suptitle('Phase24 SLW: evaluation y=+/-0.9 m, rendered walls y=+/-1.5 m');fig.savefig(OUT/'SLW_131.png',dpi=160);plt.close(fig)

def report(value):
    def compact(rows,keys):
        out=[]
        for r in rows:
            d={k:r.get(k) for k in keys}
            for k,v in d.items():
                if isinstance(v,float):d[k]=round(v,6)
                if isinstance(v,list) and all(isinstance(x,(float,int)) for x in v):d[k]=[round(x,4) for x in v]
            out.append(d)
        return table(out)
    c=value['collision_detail'];last=value['collision'][-1];r=value['reverse_summary'];g=value['goal'];pre=value['prior_boundaries'];b=value['boundaries']
    groups=[dict(phase=key,runs=sum(x['group']==key for x in pre),rendered_matches=sum(x['matches'] for x in pre if x['group']==key)) for key in sorted({x['group'] for x in pre})]
    causal=[dict(candidate='MAP_OPTIMISTIC',assessment='NOT_SUPPORTED',evidence='j26 depth min4.983mm < oracle6.742mm; unknown fraction0'),dict(candidate='SEGMENT_CHECK',assessment='NOT_SUPPORTED',evidence='node/midpoint and continuous oracle minima both+6.742mm'),dict(candidate='TOLERATED_OUTPUT',assessment='PRESENT; causal attribution NOT_ESTABLISHED',evidence='vmax0.300598 vs0.3; actual v0.056599,omega0.4. Obstacle hard condition still satisfied.'),dict(candidate='PREDICTION_ERROR',assessment='NOT_SUPPORTED',evidence='All last3s outputs: position/yaw prediction errors0'),dict(candidate='OTHER',assessment='SUPPORTED',evidence='Relaxed start margin0 + backward first chord164deg + forward-only PP execution:9.316mm cross-track exceeds6.742mm path margin')]
    text='''# Phase24 온라인 파일럿 진단

저장된 pose·명령·G job 입력/출력·SDF·USD만 분석했다. 새 주행, 렌더, NoMaD 추론, Graph 풀이, rollout, 튜닝은 **0회**다. 방법·판정 함수·기존 결과는 수정하지 않았다. 아래 원인 판정은 사후 진단이며, 정책을 바꿨을 때의 인과효과를 재실험한 결과가 아니다.

| 대상 | 진단 |
|---|---|
| L2_132_G | **OTHER**: 시작 구간 여유 완화 + 뒤쪽 첫 chord를 양의 속도 PP로 실행하면서 충돌 |
| L2_131_G | NORMAL에서 NoMaD/Topomap의 뒤쪽 참조를 따라 역주행; B 트리거는 새 장애물 부재로 차단 |
| L2_133_G | 목표를 지난 위치에서 NORMAL 운동학 실패와 DETOUR 실패·제자리 회전이 반복. 영구 정지는 아니며 이후 다시 이동했지만 goal tolerance 밖에서 timeout |
| Phase24 SLW | **SCENE_BOUNDARY_NOT_PERCEIVABLE**: 평가 경계±0.9m는 가상 경계, 렌더 벽은±1.5m |

## 1. L2_132_G 충돌

'''
    text+=f"충돌은 {c['collision_time_s']:.6f}s, pose {np.round(c['actual_final_pose'],6).tolist()}에서 발생했다. 아래 표는 직전3초와 그 구간 시작에 이미 실행 중이던 job23을 포함한다. 참조·초기값은 저장된8samples, job의 예측 B, OLD, SDF에 **동결된 준비 함수만** 적용하여 복원했다. 최적화는 하지 않았고, 실제 APPLY 경로는 저장 solver message와 정확히 대조했다.\n\n"
    text+=compact(value['collision'],['job','t','mode','output','selected_sample','all_unsafe','reference_endpoint','initialization','starts','depth_node_mid_min_m','oracle_node_mid_min_m','oracle_segment_min_m','depth_start_margin_m','map_frame','map_age_at_dispatch_s','prediction_error_m','prediction_yaw_error_deg'])+'\n\n'
    text+='j25는29.611s에 적용되었고29.667s에 NO_NEW_OBSTACLE_AHEAD로 우회가 끝났다. 선택 component의 t_new는19.486s라10초 새 장애물 창이29.486s에 끝났다(즉 적용 전에 만료). 이후 실행기는 STOP 상태로 넘어갔으며,30.722s에 j26이 NORMAL/KINEMATIC_TOLERATED로 적용됐다. j26은 REFERENCE 초기값(sample2)에서 나온 해다. 이 FRESH의8개 native suffix는 모두 unsafe였으며, 등록된 규칙에 따라 전체 후보 중 FRESHEST인 sample2를 참조로 사용했다.\n\n'
    text+='G가 읽은 것은 **base V1 SDF**다. unknown은 점유가 아니며,20F의0.5mshadow reset은 지도에 포함되지만 R3용 unknown/recency 차단 EDT는 G에 전달하지 않는다. g_jobs snapshot은 values/occupied/observed만 저장하며 최근 free 시각 배열도 없다. 따라서 G의 NORMAL/DETOUR 양쪽 계획 지도는 C0/C1의 R3 지도와 다르다.\n\n'
    text+=f"j26의 node/midpoint depth 최소는 {last['depth_node_mid_min_m']*1000:.3f}mm, 기존 depth exact_clearance(점유 셀 중심 기준)는 {last['depth_continuous_min_m']*1000:.3f}mm다. Oracle node/midpoint 및 **연속 선분** 최소는 모두 {last['oracle_segment_min_m']*1000:.3f}mm로 양수다. 시작 B의 depth clearance가5mm보다 작아 첫0.30m의 hard margin은 **0mm**로 완화됐다. unknown 경로 점 비율은0%다.\n\n"
    text+=f"반면 실제 궤적 최소 oracle clearance는 {c['actual_minimum_clearance_m']*1000:.3f}mm, 경로 대비 최대 cross-track은 {c['max_cross_track_m']*1000:.3f}mm다. 첫 선분 길이는 {c['first_segment_m']:.6f}m, dt는 {c['first_dt_s']:.6f}s이며, chord가 현재 heading과 {c['first_chord_heading_error_deg']:.3f}° 어긋난다(전방 투영 {c['first_chord_forward_projection_m']:.6f}m). 저장된 실행 명령은 양의 v={c['last_command_v']:.6f}m/s, omega={c['last_command_w']:.3f}rad/s였다.\n\n"
    text+='G는 선분 길이/dt를 양의 속도로 정의하고 비홀로노믹·뒤쪽 이동 정합은 soft residual로만 둔다. 이 해의 첫 선분 속도는0.056599m/s라 회전 구간 기준(v<0.01)에 해당하지 않는다. 따라서 실행기는 뒤쪽 chord를 즉시 따라가는 대신 현재 heading으로 전진하면서 회전했다. 이것이 안전한 polyline과 실제 footprint 충돌의 차이를 설명한다. 마지막 출력의 tolerated 표식 자체는 사실이지만, 작은 속도 초과(약0.2%)가 충돌을 일으켰다는 반사실 근거는 없다.\n\n'+table(causal)+'\n\n![L2 collision](../research/results/phase24_diagnosis/L2_132.png)\n\n'
    text+='## 2. L2_131_G 역주행\n\n'
    text+=f"가장 큰 역주행 구간은 {r['start_s']:.3f}–{r['end_s']:.3f}s: x={r['peak_x']:.3f}→{r['minimum_x']:.3f}m, 감소량 {r['backtrack_m']:.3f}m다. 구간 시작의 활성 경로를 포함한 NORMAL33개 중27개의 참조 끝점이 B보다 −x쪽이다. 실행 제어 로그는 NORMAL281회, DETOUR12회이며, NO_NEW_OBSTACLE_AHEAD로 B 조건이209회 차단됐다.\n\n"
    text+='39.944s의 sample5,40.833s의 sample1,41.833s·42.833s의 sample2는 native 끝점부터 뒤쪽을 가리키며, 이때 closest/subgoal은 모두0이다. 즉 이 구간에서 G가 따르는 원래 NoMaD/Topomap 참조 자체가 출발 쪽이다. 짧은 OLD 보충만으로 생긴 방향이라는 해석은 이 사례들에 맞지 않는다.\n\n'
    text+='앞서 B 트리거가 사용한 component의 t_new는19.486s이고 새 장애물 창은29.486s까지다. 역주행 시작36.208s에는 이 창을 이미 지났다. NO_NEW_OBSTACLE_AHEAD는 실제 상자가 사라졌다는 뜻이 아니라,10초 창과 앞쪽 직사각형을 만족하는 새 component가 없다는 뜻이다.\n\n'
    text+='NORMAL_NO_OUTPUT으로 들어간 우회는47.722,52.611,67.389s의3회이고, 각 해는 적용 직후 PATH_BECAME_UNSAFE로 종료됐다. 저장된 native 참조와 모드별 결과 전체는 아래 표/CSV에 있다.\n\n'
    text+=compact(value['reverse'],['job','t','mode','output','selected_sample','closest','subgoal','reference_dx','path_dx','initialization'])+'\n\n'
    co=r['C0_metrics'];text+=f"같은 seed의 C0는19.444s에 B 트리거,20.000s에 우회 적용,23.333s에 NO_NEW_OBSTACLE_AHEAD로 정상 주행에 복귀했다. 상자 통과는 생성 후 {co['box_passage_from_spawn_s']:.3f}s, 목표 도착은 {co['goal_time_s']:.3f}s다. G는 상자를 통과하지 못했다. 같은 seed라도 폐루프 궤적·RGB 입력은 달라지므로 이 비교를 동일 관측에 대한 planner 단독 인과효과로 해석하지 않는다.\n\n![L2 reverse](../research/results/phase24_diagnosis/L2_131.png)\n\n"
    text+='## 3. L2_133_G 목표 근처 정지\n\n'
    text+=f"연속 |v|<0.01m/s 정지는 {g['stop_intervals'][0]['start_s']:.3f}–{g['stop_intervals'][0]['end_s']:.3f}s({g['stop_intervals'][0]['duration_s']:.3f}s), pose≈{np.round(g['stop_intervals'][0]['pose'],4).tolist()}에서 확인된다. 해당 제어 구간의 원인은 {g['stationary_command_reasons']}다.\n\n"
    first=[x for x in value['goal_rows'] if x['t']<=74];text+=compact(first,['job','t','mode','output','selected_sample','closest','subgoal','reference_endpoint','active_obstacle','active_speed','active_omega','active_dt'])+'\n\n'
    failed=[]
    for row in first:
        if row['output']=='STOP':
            for init in row['last_iterate_constraints']:failed.append(dict(job=row['job'],mode=row['mode'],**init))
    text+='STOP에는 수락된 해가 없으므로 아래는 **초기값별 마지막으로 저장된 iterate**의 제약 상태다. active=여유절댓값≤1e−5, violated=여유<−1e−7이며 active와 violated는 다르다. kinematic은v/omega hard 제약의 합계이며 STOP 로그에서는 둘을 개별 분리할 수 없다. soft 가속도 항은 이 hard 제약 개수에 포함되지 않는다. 기록되지 않은 상태를0으로 대체하지 않았다.\n\n'+table(failed)+'\n\n'
    text+='NORMAL j62/j65는 모든 초기값에서 장애물 active/violation이0이지만 운동학 위반이 남고100회 반복 한도에 도달했다. 따라서 이 두 STOP의 직접적인 출력 실패는 운동학 쪽이다. 뒤이은 DETOUR j63/j66은 장애물과 운동학 위반이 함께 남는다. component가 없는 우회는 승인된 start→current 방향을 사용하며, 이 위치는 이미 goal x=8m를 지나 렌더 end wall x=9m 앞이다.\n\n'
    text+=f"중간 FEASIBLE j64는 omega10개·dt5개가 활성이고 회전 실행이 정지 시간에 포함된다. 이후 다시 이동했으므로90초 내내 붙박이로 정지한 것은 아니다. 최종 명령은 {np.round(g['final_command'],6).tolist()} ({g['final_command_mode']}), 최종 goal 거리는 {g['goal_distance_m']:.3f}m로 tolerance0.3m 밖이다. 마지막 j87은 NORMAL/FEASIBLE이며 장애물 활성0, 속도7·omega9개 활성이다. 초기 정지와 최종 timeout을 구분해야 한다.\n\n![L2 goal stop](../research/results/phase24_diagnosis/L2_133.png)\n\n"
    text+='## 4. SLW 경계 검증\n\n'
    text+='Phase24의12개 저장 scene.usda 모두 LeftWall center y=1.55, thickness0.1, RightWall center y=−1.55다. 실제 안쪽 면은±1.5m다. 반면 scenario.json의 half_width는0.9이며, footprint 정지는 |y|+0.09≥0.9에서 발생한다. ±0.9에 연속 렌더 벽은 없다. 따라서 Phase24 SLW를 **SCENE_BOUNDARY_NOT_PERCEIVABLE**로 표시한다. 기존 CORRIDOR 결과12건과 원 report의 라벨은 기록에 유지한다. 이 장면 결과로 알고리즘 간 안전 우열을 판단할 수 없다.\n\n'
    text+='실패 x위치의 가상 벽 주변(x±0.10m,y±0.03m)에서 보존 지도 모두 점유0칸·observed100%였다. 실제 정지 pose의 depth clearance는0.482–0.579m인데 oracle 가상 벽 clearance는음수다.8/12는 정지 순간 최신 발행 snapshot을 직접 확인했다.4/12는 저장 축소 때문에 해당 최신 프레임이 없어서 마지막 보존 pre-failure map을 사용했으며, 아래 exact=False와 나이를 명시했다. 그4건의 정지 tick 최신 지도 점유를 직접 확인했다고 주장하지 않는다. 렌더 geometry 결함은12개 USD에서 별도로 확정된다.\n\n'
    text+=compact(b,['run','time_s','x','y','virtual_wall_y','rendered_wall_y','boundary_occupied_cells','boundary_observed_fraction','depth_clearance_at_stop_m','oracle_wall_clearance_m','exact_latest_published_at_failure','age_s'])+'\n\n'
    text+='Phase24 wrapper는 Phase21 renderer의 base.build_scene을 직접 사용한다. 이 함수는 벽 y를±1.55로 고정하며 config.corridor.half_width를 반영하지 않는다. Phase16·17은 그 뒤 set_box로 벽을 실제 장면 경계에 맞추고, Phase18은 Phase17 renderer를 재사용한다. 저장 USD 확인 결과는 다음과 같다. Phase16에는 SLW가 없으므로 그 전신인 SL gate2건을 확인했다.\n\n'+table(groups)+'\n\n'
    text+='Phase16 SL2/2, Phase17 SLW35/35, Phase18 SLW48/48에서 실제 벽 면이 평가 경계±0.9m와 일치한다. 따라서 동일 문제가 Phase16–18에도 있었다는 근거는 없으며, 확인한 저장 run에서는 이 불일치가 없다. 개별 USD hash는 prior_boundaries.csv에 남겼다.\n\n![SLW boundary](../research/results/phase24_diagnosis/SLW_131.png)\n\n'
    text+='''## 5. 우회 지도·안전 검사 비교

| 항목 | G | C0 (Phase21 M3) | C1 (Phase21 B4 A*) |
|---|---|---|---|
| 공통 depth 원본 | V1 log-odds, noise .01d², .5mshadow reset, exact odometry | 동일 | 동일 |
| 평소 native 선택 | base V1, unknown free. 안전 후보 없으면 전체 FRESHEST를 G참조로 허용 | base V1 SAFE; 모두 위험하면 R2→R3 | base V1 SAFE; 모두 위험하면 A*repair→A*detour |
| R2 자리 | 없음 | base V1, unknown free, 시작.3m완화 및 정확 certificate | base V1, unknown free인 repair 자리; 정확 certificate |
| 우회 계획 지도 | **base V1만**, unknown free; recency 차단 없음 | 첫.3m base; 이후 occupied/unknown/last-free>2s를 막힌 셀로 합친 EDT | C0의 R3와 같은 base/strict 분할 |
| 계획 안전 샘플 | 11nodes+10midpoints. 연속 certificate 없음, h/√2 보정 없음 | 구간당9점; h/√2+L/16여유; 연속 정확 거리 certificate | 8연결 grid·코너절단 금지, LOS/후처리 뒤 sample slack 및 연속 정확 certificate |
| 시작 완화 | raw d(B)로 min(.025,max(0,d(B)−.005)) | d(B)−h/√2 기준; 음수 B는 거부 | C0와 같은 보수적 B 기준 |
| 출력 수락 | FEASIBLE 또는 F2완전만족+운동학10%허용; NORMAL에는 별도 exact검증 없음 | R3 solver/제약/certificate 통과 | 탐색/후처리 certificate 통과 |
| 적용 후 최신 depth 재검사 | **DETOUR에만** frozen20F certificate(시작완화+far unknown/recency blocked),9Hz. NORMAL에는 이 검사가 없음 | 우회 수락·실행 중 같은 최신 certificate | C0와 동일 |
| 실행 | PP방향+graph속도, graph회전 구간. 비홀로노믹 정합은 soft | PP+SP+출발 정렬 | PP+SP+출발 정렬 |
| 평가용 가상 경계 입력 | 없음 | 없음 | 없음 |

G의 우회 **계획 지도와 실행 중 certificate 지도가 서로 다르다**. 이 때문에 base-map feasible 경로가 적용 직후 PATH_BECAME_UNSAFE로 종료될 수 있으며 L2_131_G에서 실제로3회 관찰됐다. 다만 L2_132_G의 최종 충돌은 NORMAL 경로이고 unknown0%, 계획 polyline은 oracle상 안전했으므로 그 충돌을 unknown 처리 차이로 단정하지 않는다.

## 근거와 한계

- 원본 결과: `artifacts/isaac6/phase24_pilot_01/main`, 각 run의 g_events.jsonl/g_commands.jsonl/g_jobs, agent_trajectory.csv, depth, scene.usda, summary.json. 본 진단은 별도 phase24_diagnosis 폴더에만 산출한다.
- [G factor/참조 준비](../research/nomad_phase24/graph.py), [node/midpoint 제약](../research/nomad_phase23/graph.py#L88), [G 실행/모드 전환](../research/nomad_phase24/live.py), [G 입력 지도 저장](../research/nomad_phase24/online_worker.py).
- [strict recency map과 certificate](../research/nomad_phase20d/recent.py), [R3 base/strict 분할](../research/nomad_phase20c/detour_known.py), [A* 입력 지도 선택](../research/nomad_phase21/pool.py).
- [고정 폭 base renderer](../research/nomad_isaac/simulator.py#L109), [Phase17 벽 재배치](../research/nomad_phase17/simulator.py#L36), [Phase18 renderer 재사용](../research/nomad_phase18/simulator.py), [Phase24 renderer wrapper](../research/nomad_phase24/online_simulator.py).
- planned path의 oracle 최소는 기존 exact segment/AABB 함수(회전 box는 기존 rigid transform)를 재사용했다. 실제 충돌 수치는 기존 swept evaluator 저장값이다. 초기값·참조 복원은 deterministic preparation이며 새 solve가 아니다.
- 수락된 해의 활성 제약은 저장 pose/dt와 SDF로 계산했고, STOP의 활성/위반은 마지막 저장 worker message를 사용했다. snapshot timestamp와 그림용 경로 사이 미래 정보는 planner에 재입력하지 않았다.
- 수정안 구현, 재실행, 새 튜닝 또는 새 rollout은 수행하지 않았다.
'''
    (ROOT/'docs/PHASE24_PILOT_DIAGNOSIS.md').write_text(text)
    (OUT/'assessment.json').write_text(json.dumps(dict(L2_132='OTHER',L2_131='BACKWARD_NATIVE_REFERENCE_IN_NORMAL',L2_133='KINEMATIC_STOP_AND_ROTATION_NEAR_OVERSHOT_GOAL',SLW='SCENE_BOUNDARY_NOT_PERCEIVABLE',prior_scene_mismatch=False),indent=2)+'\n')

if __name__=='__main__':
    value=collect();figures(value);report(value);print(json.dumps(dict(report='docs/PHASE24_PILOT_DIAGNOSIS.md',figures=4,collision=value['collision_detail']['primary'],SLW='SCENE_BOUNDARY_NOT_PERCEIVABLE',new_solves=0,new_navigation=0)))
