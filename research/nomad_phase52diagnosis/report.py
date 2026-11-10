"""Saved 72Hz geometry + recorded EC decisions. No solver/rollout/inference."""
import argparse,csv,hashlib,json,math,time
from collections import Counter,defaultdict,OrderedDict
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.clearance import configured_obstacles,segment_clearance
from nomad_phase16.geometry import rect
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase15b.depth import Snapshot
from nomad_phase33p.storage import load_snapshot
from nomad_phase32o.evaluate import save,csvout
from nomad_phase31p.report import table

OUT=ROOT/'research/results/phase52p_contact';DOC=ROOT/'docs/PHASE52P_CONTACT_DIAGNOSIS.md'
TARGET=('phase52p','L2_D075',221,'GRAPH-REC')
LABELS=('A_UNCHECKED_COMMAND','B_UNOBSERVED_MAP','C_PREDICTION_EXECUTION','D_GRAPH_PATH','E_OTHER')
HASHES={}

def register(path):
    p=Path(path)
    if str(p) not in HASHES:HASHES[str(p)]=sha256_file(p)
    return p

def read(path):return json.loads(register(path).read_text())
def lines(path):return [json.loads(s) for s in register(path).read_text().splitlines() if s] if Path(path).exists() else []
def path_hash(path):return hashlib.sha256(np.asarray(path,dtype=np.float64).tobytes()).hexdigest()

def dynamic_boxes(summary):
    dynamic=summary.get('dynamic_obstacle') or {};out=[]
    for d in dynamic.get('boxes',[dynamic]):
        if not d.get('spawn'):continue
        spawn=d['spawn'];out.append(dict(spawn['obstacle'],active_s=spawn['simulation_time_s'],dynamic=True))
    return out

def geometries(c,summary):
    return [dict(b,active_s=0.,dynamic=False) for b in configured_obstacles(c)]+dynamic_boxes(summary)

def actual_geometry(poses,t,c,boxes):
    """Instantaneous circle/AABB and circle/half-plane clearance at saved poses."""
    xy=np.asarray(poses)[:,:2];xmin,xmax,ymin,ymax=rect(c);radius=c['agent_radius_m']
    distances=np.c_[xy[:,0]-xmin,xmax-xy[:,0],xy[:,1]-ymin,ymax-xy[:,1]]-radius
    walls=('StartWall','EndWall','RightWall','LeftWall');best=np.argmin(distances,axis=1);minimum=np.min(distances,axis=1)
    identities=np.array([walls[i] for i in best],dtype=object);surface=xy.copy()
    for k,val in enumerate((xmin,xmax,ymin,ymax)):
        mask=best==k;surface[mask,0 if k<2 else 1]=val
    for box in boxes:
        center=np.asarray(box['center_xy_m']);half=np.asarray(box['size_xyz_m'][:2])/2;lo,hi=center-half,center+half
        nearest=np.clip(xy,lo,hi);d=np.linalg.norm(xy-nearest,axis=1)-radius
        active=t>=box['active_s']-1e-10;lower=active&(d<minimum)
        minimum[lower]=d[lower];identities[lower]=box['id'];surface[lower]=nearest[lower]
    return minimum,identities,surface

def oracle_polyline(path,t,c,boxes):
    p=np.asarray(path);xmin,xmax,ymin,ymax=rect(c);r=c['agent_radius_m']
    minimum=float(np.min(np.c_[p[:,0]-xmin,xmax-p[:,0],p[:,1]-ymin,ymax-p[:,1]]))-r
    for box in boxes:
        if box['active_s']>t+1e-10:continue
        center=np.asarray(box['center_xy_m']);half=np.asarray(box['size_xyz_m'][:2])/2
        minimum=min(minimum,min(segment_clearance(a,b,center-half,center+half,r)[0] for a,b in zip(p[:-1],p[1:])))
    return float(minimum)

class Maps:
    def __init__(self,root):self.root=root;self.cache=OrderedDict();self.missing=set()
    def get(self,check):
        if check is None:return None,'NO_APPLICABLE_EC'
        metadata=check.get('snapshot') or {};file=metadata.get('file')
        if not file or not Path(file).exists():
            if file:self.missing.add(file)
            return None,'EXACT_SNAPSHOT_NOT_RETAINED'
        if file not in self.cache:
            field=load_snapshot(Snapshot,register(file));stored=dict(field.metadata)
            assert stored.get('frame_id')==metadata.get('frame_id') and abs(stored.get('sim_s',0)-metadata.get('sim_s',0))<1e-9
            self.cache[file]=field
            while len(self.cache)>3:self.cache.popitem(last=False)
        else:self.cache.move_to_end(file)
        return self.cache[file],'EXACT_EC_SNAPSHOT'
    def state(self,check,point):
        field,status=self.get(check)
        if field is None:return dict(surface_cell=status,patch_occupied=None,patch_all_unknown=None,map_available=False)
        cell=np.rint((np.asarray(point)-field.origin)/field.h).astype(int);x,y=cell
        if not (0<=y<field.occupied.shape[0] and 0<=x<field.occupied.shape[1]):return dict(surface_cell='OUTSIDE_MAP',patch_occupied=None,patch_all_unknown=None,map_available=True)
        occupied=field.occupied[max(0,y-1):y+2,max(0,x-1):x+2];observed=field.observed[max(0,y-1):y+2,max(0,x-1):x+2]
        state='OCCUPIED' if field.occupied[y,x] else 'FREE' if field.observed[y,x] else 'UNKNOWN'
        return dict(surface_cell=state,cell_xy=cell.tolist(),patch_occupied=int(occupied.sum()),
            patch_all_unknown=bool(not observed.any() and not occupied.any()),map_available=True)

def classify(*,has_ec,app,last_check,last_pass,endpoint_tail,pass_state,in_horizon,following,path_clearance,depth_path_clearance,cross_track):
    """Mutually exclusive evidence labels; unidentifiable causes remain OTHER."""
    if not has_ec:return 'E_OTHER','NO_EC_BY_DESIGN'
    if endpoint_tail and path_clearance is not None and path_clearance>=.025:return 'C_PREDICTION_EXECUTION','EC_ENDPOINT_TRUNCATES_BRAKING'
    if last_pass is not None and pass_state.get('patch_all_unknown') is True:return 'B_UNOBSERVED_MAP','SURFACE_AND_3X3_PATCH_UNOBSERVED_AT_LAST_PASS'
    if last_pass is None:return 'A_UNCHECKED_COMMAND','NO_PASS_FOR_INSTALLED_PATH'
    if last_check is not None and not last_check['passed'] and not following:return 'A_UNCHECKED_COMMAND','POST_REJECT_STOP_OR_RECOVERY_COMMAND_NOT_CERTIFIED'
    if not in_horizon:return 'A_UNCHECKED_COMMAND','OUTSIDE_RECORDED_PASS_HORIZON'
    if not pass_state.get('map_available'):return 'E_OTHER','EXACT_EC_MAP_MISSING'
    if (app is not None and app['kind']=='GRAPH_REC' and path_clearance is not None and path_clearance<.025
        and depth_path_clearance is not None and depth_path_clearance<.025 and pass_state.get('surface_cell')=='OCCUPIED'
        and cross_track is not None and cross_track<=.01):return 'D_GRAPH_PATH','GRAPH_POLYLINE_UNSAFE_IN_ORACLE_AND_CHECK_MAP_WITH_CLOSE_TRACKING'
    if pass_state.get('surface_cell') in ('FREE','UNKNOWN','OUTSIDE_MAP'):return 'E_OTHER','MAP_GEOMETRY_OR_PARTIAL_OBSERVATION_AMBIGUITY'
    return 'E_OTHER','INSUFFICIENT_SAVED_PREDICTION_TRACE_FOR_UNIQUE_ATTRIBUTION'

def nearest_event(events,t,minimum=-math.inf):
    candidates=[e for e in events if minimum-1e-10<=e['simulation_time_s']<=t+1e-10]
    return candidates[-1] if candidates else None

def load_run(row,phase):
    root=Path(row['output']);summary=read(root/'summary.json');c=read(root/'scenario.json')
    with register(root/'agent_trajectory.csv').open() as stream:tr=list(csv.DictReader(stream))
    t=np.array([float(r['simulation_time_s']) for r in tr]);pose=np.array([[float(r[k]) for k in ('x_m','y_m','yaw_rad')] for r in tr]);vw=np.array([[float(r[k]) for k in ('v_m_s','w_rad_s')] for r in tr])
    np.testing.assert_allclose(t,np.arange(len(t))/72,atol=1e-9,rtol=0)
    boxes=geometries(c,summary);gap,obstacle,surface=actual_geometry(pose,t,c,boxes)
    saved=np.full(len(t),np.inf)
    files=[root/'clearance.jsonl',*sorted((root/'dynamic').glob('**/clearance.jsonl'))]
    for file in files:
        for e in lines(file):
            index=round(e['end_sim_s']*72)
            if not 0<=index<len(t):continue
            values=[e.get(k) for k in ('lower_m','corridor_lower_m') if e.get(k) is not None]
            if values:saved[index]=min(saved[index],*values)
    assert np.isfinite(saved).all()
    assert np.all(saved<=gap+1e-7),'Instantaneous clearance must exceed stored swept lower bound'
    assert abs(float(saved.min())-row['minimum_clearance_m'])<1e-9,'Frozen report minimum does not match raw logs'
    repair=lines(root/'repair.jsonl');apps=[dict(e,path_hash=path_hash(e['path_world']),app_index=i) for i,e in enumerate(repair) if e['event']=='PATH_APPLIED']
    commands=lines(root/'phase20_commands.jsonl');checks=[e for e in lines(root/'exec_cert.jsonl') if e['event']=='CHECK'];byhash=defaultdict(list)
    for e in checks:byhash[e['path_sha256']].append(e)
    rec=lines(root/'reconstruction.jsonl');maps=Maps(root);risk=(gap<.025);risk[0]=False
    uid=f"{phase}/{row['scene']}/{row['index']}/{row['method']}";is_target=(phase,row['scene'],row['index'],row['method'])==TARGET
    points=[];timeline=[];app_cache={};depth_cache={};app_cursor=cmd_cursor=-1;episode=0;prior_risk=False
    for i in range(1,len(t)):
        if risk[i] and not prior_risk:episode+=1
        prior_risk=bool(risk[i])
        begin=t[i-1]
        while app_cursor+1<len(apps) and apps[app_cursor+1]['simulation_time_s']<=begin+1e-10:app_cursor+=1
        while cmd_cursor+1<len(commands) and commands[cmd_cursor+1]['time_s']<=begin+1e-10:cmd_cursor+=1
        app=apps[app_cursor] if app_cursor>=0 else None;command=commands[cmd_cursor] if cmd_cursor>=0 else None
        if not (risk[i] or is_target and begin>=t[-1]-3-1e-10):continue
        source=command['source'] if command else 'INITIAL_INFERENCE_WAIT';following=source in ('NORMAL','KEEP_ACTIVE','ALIGN_ROTATE','ALIGN_BRAKE','REPAIR','ENDPOINT')
        current_id=command.get('path_source_id') if command else None
        relevant=byhash[app['path_hash']] if app else []
        last_check=nearest_event(relevant,begin,app['simulation_time_s']) if app else None
        last_pass=nearest_event([e for e in relevant if e['passed']],begin,app['simulation_time_s']) if app else None
        path_clear=None;cross_track=None;depth_path=None;endpoint=None
        if app:
            cachekey=(app['app_index'],tuple(b['id'] for b in boxes if b['active_s']<=t[i]))
            if cachekey not in app_cache:app_cache[cachekey]=oracle_polyline(app['path_world'],t[i],c,boxes)
            path_clear=app_cache[cachekey];cross_track=XYPath(app['path_world']).project(pose[i,:2])[1]
            endpoint=next((e for e in commands if app['simulation_time_s']<=e['time_s']<=begin+1e-10 and e['source']=='ENDPOINT'),None)
        horizon_end=last_pass['simulation_time_s']+last_pass['duration_s'] if last_pass else None
        in_horizon=last_pass is not None and t[i]<=horizon_end+1e-10
        endpoint_tail=bool(last_pass and last_pass.get('endpoint_reached') and endpoint and
            abs(endpoint['time_s']-horizon_end)<=1/9+1e-8 and t[i]>horizon_end+1e-10 and source in ('ENDPOINT','STOP_WAIT','KEEP_ACTIVE')
            and cross_track is not None and cross_track>.01)
        pass_state=maps.state(last_pass,surface[i]) if risk[i] else {}
        current_state=maps.state(last_check,surface[i]) if risk[i] else {}
        if app and last_pass and app['kind']=='GRAPH_REC' and path_clear<.025 and pass_state.get('surface_cell')=='OCCUPIED':
            key=(app['path_hash'],last_pass['snapshot']['file'])
            if key not in depth_cache:
                field,_=maps.get(last_pass);depth_cache[key]=field.exact_clearance(np.asarray(app['path_world'])) if field else None
            depth_path=depth_cache[key]
        label,reason=classify(has_ec=bool(checks),app=app,last_check=last_check,last_pass=last_pass,endpoint_tail=endpoint_tail,
            pass_state=pass_state,in_horizon=in_horizon,following=following,path_clearance=path_clear,depth_path_clearance=depth_path,cross_track=cross_track) if risk[i] else (None,None)
        record=dict(uid=uid,phase=phase,scene=c['phase16_scene'],condition=row.get('condition','D075'),method=row['method'],seed=row['index'],
            tick=i,time_s=float(t[i]),interval_start_s=float(begin),x_m=float(pose[i,0]),y_m=float(pose[i,1]),yaw_rad=float(pose[i,2]),
            actual_v_m_s=float(vw[i,0]),actual_w_rad_s=float(vw[i,1]),command_source=source,active_path_id=current_id,
            last_installed_kind=('GRAPH_REC' if app and app['kind']=='GRAPH_REC' else 'CUT' if app else None),last_installed_raw_kind=app['kind'] if app else None,
            last_installed_id=app['id'] if app else None,installed_s=app['simulation_time_s'] if app else None,path_hash=app['path_hash'] if app else None,
            actual_clearance_m=float(gap[i]),saved_swept_lower_m=float(saved[i]),nearest_obstacle=str(obstacle[i]),nearest_surface_xy=surface[i].tolist(),
            path_oracle_clearance_m=path_clear,path_check_map_clearance_m=depth_path,cross_track_to_last_path_m=cross_track,
            last_ec_check_id=last_check['check_id'] if last_check else None,last_ec_s=last_check['simulation_time_s'] if last_check else None,
            last_ec_passed=last_check['passed'] if last_check else None,last_ec_predicted_clearance_m=last_check.get('clearance_m') if last_check else None,
            last_pass_check_id=last_pass['check_id'] if last_pass else None,last_pass_horizon_end_s=horizon_end,
            last_pass_endpoint=last_pass.get('endpoint_reached') if last_pass else None,endpoint_command_s=endpoint['time_s'] if endpoint else None,
            last_check_surface_state=current_state.get('surface_cell'),last_pass_surface_state=pass_state.get('surface_cell'),
            last_pass_patch_occupied=pass_state.get('patch_occupied'),last_pass_map_available=pass_state.get('map_available'),
            primary_label=label,classification_reason=reason,risk_episode=episode if risk[i] else None)
        if risk[i]:points.append(record)
        if is_target and begin>=t[-1]-3-1e-10:timeline.append(record)
    summary_row=dict(uid=uid,phase=phase,scene=c['phase16_scene'],condition=row.get('condition','D075'),method=row['method'],seed=row['index'],output=str(root),
        duration_s=float(t[-1]),ticks=len(t)-1,low_clearance_ticks=int(risk.sum()),low_clearance_s=float(risk.sum()/72),
        low_swept_intervals=int(np.count_nonzero(saved[1:]<.025)),episodes=episode,minimum_actual_clearance_m=float(gap.min()),minimum_saved_swept_m=float(saved.min()),
        collisions=bool(row['collision']),ec_supported=bool(checks),missing_exact_ec_maps=len(maps.missing),
        **{label:sum(p['primary_label']==label for p in points) for label in LABELS})
    detail=None
    if is_target:
        detail=target_detail(root,c,summary,boxes,t,pose,vw,apps,commands,checks,rec,maps,timeline)
    return summary_row,points,timeline,detail

def target_detail(root,c,summary,boxes,t,pose,vw,apps,commands,checks,rec,maps,timeline):
    gap,ids,surfaces=actual_geometry(pose,t,c,boxes);contact=float(t[-1]);point=surfaces[-1]
    paths={a['path_hash']:dict(kind='GRAPH_REC' if a['kind']=='GRAPH_REC' else 'CUT',id=a['id'],path=a['path_world']) for a in apps}
    from nomad_isaac.common import local_to_world
    for e in lines(root/'events.jsonl'):
        if not e.get('overnight_metric_samples'):continue
        for i,sample in enumerate(e['overnight_metric_samples']):
            world=local_to_world(sample,e['observation_pose']);paths.setdefault(path_hash(world),dict(kind='CUT_CANDIDATE',id=e['id'],sample=i,path=world.tolist()))
    for e in rec:
        if e['event']!='RESULT' or not e.get('numeric_result'):continue
        for i,r in enumerate(e['numeric_result'].get('results',[])):
            if r.get('path') is not None:paths.setdefault(path_hash(r['path']),dict(kind='GRAPH_CANDIDATE',id=e['id'],job_id=e['job_id'],sample=i,path=r['path']))
    ec=[]
    for check in checks:
        if not contact-3-1e-10<=check['simulation_time_s']<=contact:continue
        path=paths.get(check['path_sha256'],{});state=maps.state(check,point)
        ec.append(dict(check_id=check['check_id'],time_s=check['simulation_time_s'],scope=check['scope'],kind=path.get('kind','UNRESOLVED_CANDIDATE'),
            chunk_id=path.get('id'),sample=path.get('sample'),path_hash=check['path_sha256'],passed=check['passed'],predicted_min_clearance_m=check.get('clearance_m'),
            horizon_duration_s=check['duration_s'],horizon_end_s=check['simulation_time_s']+check['duration_s'],endpoint_reached=check['endpoint_reached'],
            speed_cap_m_s=check['speed_cap_m_s'],snapshot_frame=check['snapshot']['frame_id'],snapshot_sim_s=check['snapshot']['sim_s'],
            snapshot_age_s=check['simulation_time_s']-check['snapshot']['sim_s'],snapshot_file=check['snapshot']['file'],contact_surface_xy=point.tolist(),**state))
    last_graph=next((a for a in reversed(apps) if a['kind']=='GRAPH_REC'),None)
    selected=next((e for e in reversed(rec) if e['event']=='RESULT' and e.get('applied')),None)
    after=[];info=None
    if last_graph:
        start=round(last_graph['simulation_time_s']*72)
        for i in range(start,len(t)):after.append(dict(tick=i,time_s=float(t[i]),x_m=float(pose[i,0]),y_m=float(pose[i,1]),yaw_rad=float(pose[i,2]),
            v_m_s=float(vw[i,0]),w_rad_s=float(vw[i,1]),oracle_clearance_m=float(gap[i])))
        path=last_graph['path_world'];ends=[cmd for cmd in commands if cmd['time_s']>=last_graph['simulation_time_s'] and cmd['source']=='ENDPOINT']
        end=ends[0] if ends else None;end_index=round(end['time_s']*72) if end else None
        dispatch=next((e for e in rec if selected and e['event']=='DISPATCH' and e['job_id']==selected['job_id']),None)
        info=dict(job_id=selected['job_id'] if selected else None,chunk_id=last_graph['id'],apply_s=last_graph['simulation_time_s'],path=path,
            predicted_B=dispatch['B'] if dispatch else None,actual_apply_pose=last_graph['pose'],
            B_prediction_error_m=selected.get('prediction_error_m') if selected else None,B_prediction_heading_error_rad=selected.get('prediction_yaw_error_rad') if selected else None,
            path_length_m=float(np.linalg.norm(np.diff(np.asarray(path),axis=0),axis=1).sum()),
            path_oracle_clearance_m=oracle_polyline(path,contact,c,boxes),path_endpoint_xy=path[-1],
            actual_post_graph_distance_m=float(np.linalg.norm(np.diff(pose[start:,:2],axis=0),axis=1).sum()),
            first_endpoint_command_s=end['time_s'] if end else None,first_endpoint_command_vw=end['command'] if end else None,
            endpoint_actual_clearance_m=float(gap[end_index]) if end else None,
            endpoint_to_contact_travel_m=float(np.linalg.norm(np.diff(pose[end_index:,:2],axis=0),axis=1).sum()) if end else None,
            contact_to_path_endpoint_distance_m=float(np.linalg.norm(pose[-1,:2]-path[-1])),
            contact_pose=pose[-1].tolist(),contact_s=contact,contact_surface_xy=point.tolist(),nearest_obstacle=str(ids[-1]))
    return dict(info=info,ec=ec,trajectory=after,timeline=timeline,boxes=boxes,config=c,
        target_label=timeline[-1]['primary_label'],target_reason=timeline[-1]['classification_reason'])

def aggregate(runs,points,groups):
    buckets=defaultdict(list)
    for r in runs:buckets[tuple(r[k] for k in groups)].append(r)
    out=[]
    for key,rs in sorted(buckets.items()):
        row=dict(zip(groups,key));ticks=sum(r['ticks'] for r in rs);low=sum(r['low_clearance_ticks'] for r in rs)
        row.update(runs=len(rs),ticks=ticks,low_clearance_ticks=low,low_clearance_seconds=low/72,low_rate=low/ticks if ticks else None,
            low_swept_intervals=sum(r['low_swept_intervals'] for r in rs),episodes=sum(r['episodes'] for r in rs),affected_runs=sum(r['low_clearance_ticks']>0 for r in rs),
            **{label:sum(r[label] for r in rs) for label in LABELS})
        assert sum(row[x] for x in LABELS)==low;out.append(row)
    return out

def figures(detail):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle,Circle
    info=detail['info'];pose=np.array([[r['x_m'],r['y_m']] for r in detail['trajectory']]);path=np.asarray(info['path'])
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    ax=axes[0]
    for b in detail['boxes']:
        center=np.asarray(b['center_xy_m']);half=np.asarray(b['size_xyz_m'][:2])/2
        ax.add_patch(Rectangle(center-half,*2*half,color='purple' if b['dynamic'] else '.6',alpha=.3))
    ax.plot(path[:,0],path[:,1],'o--',label='Applied GRAPH_REC',color='#E69F00')
    ax.plot(pose[:,0],pose[:,1],label='Recorded 72 Hz pose',color='#0072B2');ax.scatter(*path[-1],marker='s',color='#E69F00',label='Path endpoint')
    ax.add_patch(Circle(pose[-1],.09,fill=False,color='red'));ax.scatter(*info['contact_surface_xy'],marker='x',color='red',label='Contact surface')
    ax.set_xlim(path[0,0]-.12,info['contact_surface_xy'][0]+.2);ax.set_ylim(min(path[:,1])-.2,max(path[:,1])+.2)
    ax.set_aspect('equal');ax.set_xlabel('x (m)');ax.set_ylabel('y (m)');ax.legend(fontsize=7)
    ax=axes[1];rows=detail['timeline'];times=[r['time_s'] for r in rows]
    ax.plot(times,[r['actual_clearance_m'] for r in rows],label='Actual footprint clearance',color='#0072B2')
    marked=set()
    for e in detail['ec']:
        if e['kind']=='GRAPH_REC':
            label='EC PASS predicted min' if e['passed'] else 'EC REJECT predicted min'
            ax.scatter(e['time_s'],e['predicted_min_clearance_m'],marker='o' if e['passed'] else 'x',color='#D55E00',label=label if label not in marked else None)
            marked.add(label)
    ax.axhline(.025,ls='--',color='.4',label='0.025 m');ax.axhline(0,color='black',lw=.5)
    ax.axvline(info['first_endpoint_command_s'],ls=':',color='#009E73',label='ENDPOINT command')
    ax.set_xlabel('Time (s)');ax.set_ylabel('Clearance (m)');ax.legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'contact_evidence.png',dpi=150);plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True);started=time.perf_counter();runs=[];points=[];detail=None;target_timeline=[]
    datasets=[]
    for phase,n in (('phase52p',40),('phase47c',60)):
        rows=read(ROOT/f'research/results/{phase}/runs.json');assert len(rows)==n and all(r['technical_validation']=='PASS' for r in rows)
        datasets.extend((phase,r) for r in rows)
    for i,(phase,r) in enumerate(datasets,1):
        summary,low,timeline,d=load_run(r,phase);runs.append(summary);points.extend(low)
        if d is not None:detail=d;target_timeline=timeline
        if i%10==0:print(f'[logs] {i}/100; low ticks {len(points)}; elapsed {time.perf_counter()-started:.1f}s',flush=True)
    assert detail is not None
    phase_stats=aggregate(runs,points,('phase',));method_stats=aggregate(runs,points,('phase','condition','method'));scene_stats=aggregate(runs,points,('phase','condition','method','scene'))
    reasons=Counter((r['phase'],r['method'],r['primary_label'],r['classification_reason']) for r in points)
    reason_rows=[dict(phase=p,method=m,label=l,reason=reason,ticks=n) for (p,m,l,reason),n in sorted(reasons.items())]
    episodes=[]
    grouped=defaultdict(list)
    for r in points:grouped[(r['uid'],r['risk_episode'])].append(r)
    for (uid,episode),rr in sorted(grouped.items()):
        counts=Counter(r['primary_label'] for r in rr);episodes.append(dict(uid=uid,episode=episode,start_s=rr[0]['time_s'],end_s=rr[-1]['time_s'],ticks=len(rr),minimum_m=min(r['actual_clearance_m'] for r in rr),labels=dict(counts)))
    for name,data in [('runs',runs),('low_clearance_ticks',points),('episodes',episodes),('phase_summary',phase_stats),('method_summary',method_stats),('scene_summary',scene_stats),
        ('reasons',reason_rows),('target_timeline_72hz',target_timeline),('target_ec_checks',detail['ec']),('target_post_graph_trajectory',detail['trajectory'])]:csvout(OUT/(name+'.csv'),data)
    save(OUT/'target.json',detail);save(OUT/'input_hashes.json',HASHES)
    decision=dict(label=detail['target_label'],reason=detail['target_reason'],target_run='/'.join(map(str,TARGET)),runs=100,
        low_ticks=len(points),elapsed_s=time.perf_counter()-started,simulations=0,new_inference=0,new_rollouts=0,new_graph_solves=0,
        exact_map_files=len([x for x in HASHES if x.endswith('.npz')]),maps_missing=sum(r['missing_exact_ec_maps'] for r in runs))
    decision['source_sha256']={str(f.relative_to(ROOT)):sha256_file(f) for f in Path(__file__).parent.glob('*.py')}
    for name in ('nomad_phase32/policy.py','nomad_phase32o/exec_cert.py','nomad_phase20/runtime.py','nomad_phase16/execution.py'):
        register(ROOT/'research'/name)
    save(OUT/'input_hashes.json',HASHES)
    save(OUT/'analysis.json',decision);figures(detail)
    rules=[dict(label='(c) C_PREDICTION_EXECUTION',rule='우선: 같은 설치 경로의 EC PASS가 endpoint에서 종료되고 실제 ENDPOINT/STOP_WAIT 감속 이동이 그 지평선 뒤로 이어지며 경로 자체 oracle clearance>=0.025. 실제 위치가 경로 끝/선에서1cm 이상 벗어남. B 오차와 EC 종료모델 차이를 구분'),
        dict(label='(b) B_UNOBSERVED_MAP',rule='마지막 실행 허용 PASS 지도에서 위험 표면 셀과3×3 이웃 모두 unobserved,occupied 없음. 부분 관측/관측된 free 오차는 기타'),
        dict(label='(a) A_UNCHECKED_COMMAND',rule='설치 경로를 허용한 PASS가 없거나, EC REJECT 후 미검증 STOP/RECOVER 명령이 실행되거나, 저장된 PASS 지평선 밖. (c)의 명확한 endpoint 모델 차이를 먼저 분리'),
        dict(label='(d) D_GRAPH_PATH',rule='지평선 안에서 GRAPH_REC 자체가 oracle와 동일 EC 지도 exact 모두0.025 미만이고, 위험 표면이 occupied이며 실제 추종오차<=1cm. 위험경로와 지도 오차를 분리할 수 없는 경우 기타'),
        dict(label='(e) E_OTHER',rule='원래 EC 없는 NOMAD_RAW,정확 지도 미보존,관측된 free/부분 unknown의 지도-기하 차이,나머지 근거 부족. RAW는 검사의 구멍으로 해석하지 않음')]
    limitations=[dict(item='집계 단위',definition='선택된 최종 분석 run만:Phase52 40회와Phase47-C60회. 제외 attempt2는 미사용. t=0 제외 각72Hz 저장 pose의 circle/AABB·wall 최소 footprint clearance<0.025를1순간으로 센다. 근접 장애물이 여러개여도 중복 없음'),
        dict(item='연속 구간 보조',definition='원시 clearance.jsonl의 swept lower bound<0.025 구간도 별도 열. 순간 수는 독립 충돌/독립 표본 수가 아니며 연속 저여유 episode와 영향 run 수도 표시'),
        dict(item='타임라인 시각',definition='행 시각은72Hz 구간 끝. 명령/경로/EC는 해당 구간 시작까지 알려진 기록만 사용해 같은 tick 뒤의 새 설치/검사를 소급하지 않음. 마지막 설치 경로와 실제 활성 path id를 분리'),
        dict(item='접촉 셀',definition='로봇 중심 셀이 아니라 최근접 oracle 장애물 표면점을 V1 rint 셀로 조회. occupied 우선,observed면서 비점유면free,둘 다 아니면unknown.3×3 관측도 함께 표시'),
        dict(item='지도',definition='검사가 사용한 정확한 snapshot만 STORAGE_RETROFIT 로더로 복원. 과거 지도 대체 없음;미보존은 기타+가용률로 기록. 제어에 oracle 미사용'),
        dict(item='분류 한계',definition='저장된 EC scalar/horizon과 실제 명령을 이용한 근거 분류. EC의 전체 예측 trajectory가 저장되지 않은 경우 일반 위치 예측 오차는 식별 불가. 원인 확정용 주행·반사실 rollout은 하지 않음'),
        dict(item='비교 한계',definition='Phase52는2방법×2지연×221/222,Phase47은3방법×221–224이다. 시간 노출과방법 구성이 달라 순간 수의 크기를 그대로 우열로 해석하지 않음')]
    info=detail['info'];target_low=[r for r in points if r['uid']==decision['target_run']]
    assert decision['label']=='C_PREDICTION_EXECUTION' and info['B_prediction_error_m']==0 and info['B_prediction_heading_error_rad']==0
    assert all(e['surface_cell']=='OCCUPIED' for e in detail['ec'])
    assert len(target_timeline)==216
    highlights=[dict(contact_s=info['contact_s'],classification='(c) 예측-실제 차이: EC 끝점 종료와 실제 감속 이동의 불일치',
        graph_apply_s=info['apply_s'],B_error_m=info['B_prediction_error_m'],B_heading_error_rad=info['B_prediction_heading_error_rad'],
        graph_path_oracle_clearance_m=info['path_oracle_clearance_m'],endpoint_command_s=info['first_endpoint_command_s'],
        endpoint_command_v_m_s=info['first_endpoint_command_vw'][0],endpoint_actual_clearance_m=info['endpoint_actual_clearance_m'],
        endpoint_to_contact_travel_m=info['endpoint_to_contact_travel_m'],target_low_ticks=len(target_low))]
    ec_table=[{k:e[k] for k in ('check_id','time_s','scope','kind','chunk_id','sample','passed','predicted_min_clearance_m','horizon_end_s','endpoint_reached','snapshot_frame','snapshot_age_s','surface_cell','patch_occupied')} for e in detail['ec']]
    doc='# Phase52-P L2 GRAPH-REC 접촉 및 전체 저여유 순간 진단\n\n'+table(highlights)+'\n\n'
    doc+='접촉은 **19.027778s**다. 마지막 Graph 교체의 B 예측 위치·heading 오차는0이며, 적용 경로 자체 oracle 최소 여유는2.5cm보다 크다. 마지막 허용 EC는 경로 끝에 도달하면 검사를 끝내지만, 실제 실행기는 선속도를 가속 제한 안에서 줄이므로 끝점 뒤로 계속 이동했다. 접촉 표면은 관련 EC 지도에 occupied로 기록되어 있다. 따라서 이 사례는 지도 미관측이나 Graph 경로 자체 관통으로 분류하지 않는다.\n\n'
    doc+='구체적으로 18.666667s EC #48은 18.777778s 끝점 도달까지 0.111111s만 검사하고 최소 여유 0.049105m로 PASS했다. 실제 18.777778s ENDPOINT 명령은 즉시 정지하지 않고 v=0.242256m/s였고, 그때 실제 여유0.051289m 이후 접촉까지0.051305m 이동했다. 18.888889s에는 기존 경로 EC #67도 REJECT되고 STOP_WAIT로 전환됐지만 이미 진행 중인 감속 이동은 계속됐다. 즉 (a)의 미검사 감속 꼬리도 관찰되지만, 중복 집계를 피하려고 명확한 EC 종료 모델 차이인 (c)를 주 분류로 사용한다.\n\n'
    doc+='## 마지막 EC와 경로 교체\n\n'+table(ec_table)+'\n\n'+table([info])+'\n\n![저장 경로와 실제 궤적·여유 비교](../research/results/phase52p_contact/contact_evidence.png)\n\n'
    doc+='원래 EC는 [`continuation_certificate`](../research/nomad_phase32/policy.py) 및 [`rollout`](../research/nomad_phase32o/exec_cert.py)에서 `completed`이면 적분을 종료한다. 실제 [`Execution.apply`](../research/nomad_phase20/runtime.py)는 끝점에서 [`stop_command`](../research/nomad_phase16/execution.py)를 사용해 매 제어 tick 최대0.5/9 m/s씩 감속한다. 이 코드는 수정하지 않았다.\n\n'
    doc+='## 접촉 전3초 72Hz 전체 타임라인\n\n'+table([{k:r[k] for k in ('tick','time_s','last_installed_kind','last_installed_id','active_path_id','command_source','actual_v_m_s','actual_w_rad_s','actual_clearance_m','saved_swept_lower_m')} for r in target_timeline])+'\n\n'
    doc+='[216구간 타임라인 CSV](../research/results/phase52p_contact/target_timeline_72hz.csv) · [Graph 교체 후 실제99개 pose](../research/results/phase52p_contact/target_post_graph_trajectory.csv) · [전체 저여유 순간 CSV](../research/results/phase52p_contact/low_clearance_ticks.csv) · [run별 집계](../research/results/phase52p_contact/runs.csv)\n\n'
    doc+='## 전체100회: 순간 수와 분류\n\n'+table(phase_stats)+'\n\n'+table(method_stats)+'\n\n'+table(scene_stats)+'\n\n'+table(reason_rows)+'\n\n'
    doc+='## 분류 기준과 범위\n\n'+table(rules)+'\n\n'+table(limitations)+'\n\n'+table([decision])+'\n'
    DOC.write_text(doc)
    print(json.dumps(decision),flush=True)

if __name__=='__main__':main()
