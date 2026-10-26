"""Depth/oracle comparison using saved predictions only; no inference or solve."""
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_isaac.common import local_to_world, sha256_file, write_json
from nomad_isaac.handoff_audit import path_safety
from nomad_isaac.clearance import configured_obstacles, obstacle_bounds, single_obstacle_config
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase0.graph_v4 import SignedDistanceField
from nomad_phase4.report import write_csv
from .depth_sdf import DepthSDF, bounds_from_config
from .replay_render import jsonl, git_sha


def suffix(xy, boundary):
    xy=np.asarray(xy)
    if np.max(np.linalg.norm(xy-xy[0],axis=1))<=1e-12:
        return np.repeat(xy[:1],2,axis=0),0.
    path=XYPath(xy); s,_=path.project(np.asarray(boundary)[:2])
    points=np.vstack([path.at(s),path.points[path.s>s+1e-12]])
    if len(points)==1: points=np.repeat(points,2,axis=0)
    return points,float(path.s[-1]-s)


def sample_path(points, step=.005):
    queries=[]; max_step=0.
    for a,b in zip(points,points[1:]):
        length=float(np.linalg.norm(b-a)); n=max(1,int(np.ceil(length/step)))
        queries.extend(np.linspace(a,b,n+1)); max_step=max(max_step,length/n)
    return np.asarray(queries),max_step


def oracle_clearance(points, config):
    safety=path_safety(points,config)
    return min(safety['obstacle_clearance_m'],safety['corridor_clearance_m'])


def oracle_values(points, field, config):
    obstacle=field.query(points)[0]; c=config['corridor'];r=config['agent_radius_m']
    wall=np.minimum.reduce([points[:,0]-c['xmin'],c['xmax']-points[:,0],c['half_width']-np.abs(points[:,1])])-r
    return np.minimum(obstacle,wall)


def choose(clearances, lengths, threshold=.025):
    candidates=[i for i,c in enumerate(clearances) if c>=threshold]
    return min(candidates,key=lambda i:(-lengths[i],i)) if candidates else None


def attribution(points, depth_field, oracle_field, config):
    # Locate the approximate limiting centerline point, then exact nearest
    # oracle box/wall surface. This is evaluated AFTER depth-only classification.
    point=points[int(np.argmin(oracle_values(points,oracle_field,config)))]
    candidates=[]
    for box in configured_obstacles(config):
        lo,hi=obstacle_bounds(single_obstacle_config(config,box))
        surface=np.clip(point,lo,hi)
        if np.all(point>=lo) and np.all(point<=hi):
            distances=np.r_[point-lo,hi-point];j=int(np.argmin(distances))
            surface=point.copy();surface[j%2]=(lo if j<2 else hi)[j%2]
        candidates.append((float(np.linalg.norm(point-surface)),surface))
    c=config['corridor']
    for axis,value in ((0,c['xmin']),(0,c['xmax']),(1,-c['half_width']),(1,c['half_width'])):
        surface=point.copy();surface[axis]=value
        candidates.append((abs(point[axis]-value),surface))
    _,surface=min(candidates,key=lambda t:t[0]);cells,ok=depth_field.cells(surface[None])
    if not ok[0]: return 'UNKNOWN',dict(unknown=True,height_filter=False,range_exceeded=False)
    x,y=cells[0];sl=np.s_[max(0,y-2):y+3,max(0,x-2):x+3]
    flags=dict(unknown=not bool(depth_field.observed[y,x]),
        height_filter=bool(depth_field.height_rejected[sl].any()),
        range_exceeded=bool(depth_field.range_rejected[sl].any()))
    cause='HEIGHT_FILTER' if flags['height_filter'] else 'RANGE_EXCEEDED' if flags['range_exceeded'] else 'UNKNOWN' if flags['unknown'] else 'OTHER'
    return cause,flags


def distribution(values):
    a=np.asarray(values,dtype=float)
    if not len(a): return dict(n=0,median=None,p5=None,p95=None,min=None,max=None)
    return dict(n=len(a),median=float(np.median(a)),p5=float(np.percentile(a,5)),p95=float(np.percentile(a,95)),min=float(a.min()),max=float(a.max()))


def decision(dangerous, conservative, p95):
    if dangerous>.02: return 'DEPTH_NOT_READY'
    if p95>50: return 'TIMING_NOT_READY'
    if conservative>.20: return 'DEPTH_CONSERVATIVE'
    return 'DEPTH_READY'


def available(frame, event):
    return frame['capture_end_monotonic_ns']<=event['application_monotonic_ns']


def evaluate(run_root, destination, noise_conditions=('none','gaussian')):
    run_root=Path(run_root);destination=Path(destination)
    if destination.exists(): raise FileExistsError(f'Refusing to overwrite results: {destination}')
    complete=json.loads((run_root/'render_complete.json').read_text())
    plan=json.loads((run_root/'plan.json').read_text())
    assert complete['plan_sha256']==sha256_file(run_root/'plan.json')
    assert complete['camera_sha256']==sha256_file(run_root/'camera.json')
    assert len(complete['runs'])==24 and len(plan['runs'])==24
    for path,digest in plan['input_hashes'].items():
        assert sha256_file(path)==digest,f'Source changed: {path}'
    # Frozen producer semantics; a later report-only commit is allowed.
    here=Path(__file__).parent
    assert sha256_file(here/'protocol.json')==plan['protocol_sha256']
    for path,digest in plan['producer_hashes'].items():
        assert sha256_file(Path(__file__).parents[2]/path)==digest,f'Producer/evaluator changed: {path}'
    destination.mkdir(parents=True)
    write_json(destination/'started.json',dict(report_git_sha=git_sha(),render_git_sha=plan['execution_git_sha'],noise_conditions=noise_conditions))
    camera=json.loads((run_root/'camera.json').read_text()); k=np.array(camera['intrinsics'])
    archive_index={r['key']:r for r in complete['runs']}; records=[];timings=[];selections=[]; collisions=[]
    snapshot=None
    for source in plan['runs']:
        start=time.perf_counter(); name=source['key'];run=Path(source['output']);config=source['scenario']
        arc=archive_index[name]; archive=run_root/name/'depth.npz'; meta=run_root/name/'frames.json'
        assert sha256_file(archive)==arc['sha256'] and sha256_file(meta)==arc['metadata_sha256']
        frames=json.loads(meta.read_text());events=jsonl(run/'events.jsonl')
        assert len(frames)==len(source['frames'])==arc['frames']
        assert all(all(frame[key]==original[key] for key in original) for frame,original in zip(frames,source['frames']))
        oracle=SignedDistanceField(config,.01,2.)
        active_id=None
        if source['method']=='FRESHEST+GRAPH-GF' and source['index'] in (39,45):
            active_id=jsonl(run/'phase6_applications.jsonl')[-1]['id']
        with np.load(archive) as stored:
            depth=stored['depth'];transforms=stored['camera_to_world']
        assert depth.shape==(len(frames),240,320) and depth.dtype==np.float16
        for image,frame in zip(depth,frames):
            assert hashlib.sha256(image.tobytes()).hexdigest()==frame['depth_sha256']
        for noise in noise_conditions:
            field=DepthSDF(bounds_from_config(config)); cursor=0
            for event in events:
                while cursor<len(frames) and available(frames[cursor],event):
                    # Same seeded noise for a particular run/frame regardless of
                    # evaluation order, partial job, or switch count.
                    key_seed=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
                    rng=np.random.default_rng(np.random.SeedSequence([20261026,key_seed,frames[cursor]['observation_id']]))
                    result=field.update(depth[cursor],k,transforms[cursor],noise=='gaussian',rng)
                    timings.append(dict(run=name,noise=noise,observation_id=frames[cursor]['observation_id'],**result))
                    cursor+=1
                assert cursor>0, 'Switch without a completed camera frame'
                B=np.array(event['agent_pose_at_switch']);A=event['observation_pose']
                with np.load(run/f"model/derived/{event['id']:04d}.npz") as data:metric=data['metric']
                assert metric.shape==(8,8,2) and np.isfinite(metric).all()
                world=np.array([local_to_world(sample,A) for sample in metric])
                lengths=[];oc=[];dc=[];local=[]
                for sample,xy in enumerate(world):
                    path,length=suffix(xy,B);queries,ds=sample_path(path)
                    oval=oracle_clearance(path,config)
                    nominal=float(field.query(queries)[0].min())
                    dval=nominal-field.error_bound-ds/2
                    osafe=oval>=.025;dsafe=dval>=.025
                    cell='both_safe' if osafe and dsafe else 'both_unsafe' if not osafe and not dsafe else 'depth_only_safe' if dsafe else 'depth_only_unsafe'
                    cause=None;flags={}
                    if cell=='depth_only_safe':cause,flags=attribution(queries,field,oracle,config)
                    row=dict(run=name,method=source['method'],index=source['index'],noise=noise,
                        fresh_id=event['id'],sample=sample,switch_sim_s=event['application_sim_s'],
                        observation_pose=A,boundary=B.tolist(),last_depth_observation=frames[cursor-1]['observation_id'],
                        last_depth_capture_ns=frames[cursor-1]['capture_end_monotonic_ns'],switch_ns=event['application_monotonic_ns'],
                        depth_frames_available=cursor,remaining_length_m=length,
                        depth_clearance_m=dval,depth_nominal_sampled_m=nominal,oracle_clearance_m=oval,
                        clearance_error_m=dval-oval,oracle_safe=osafe,depth_safe=dsafe,confusion=cell,
                        path_unknown_fraction=field.unknown_fraction(queries),unknown_grid_fraction=float((~field.observed).mean()),
                        cause=cause,**flags)
                    lengths.append(length);oc.append(oval);dc.append(dval);local.append(row)
                di=choose(dc,lengths);oi=choose(oc,lengths)
                selection=dict(run=name,index=source['index'],method=source['method'],noise=noise,fresh_id=event['id'],
                    depth_selected=di,oracle_selected=oi,same=di==oi,
                    depth_selection_oracle_clearance_m=None if di is None else oc[di],
                    oracle_selection_clearance_m=None if oi is None else oc[oi],
                    depth_all_unsafe=di is None,oracle_all_unsafe=oi is None)
                selections.append(selection)
                for row in local:row.update(selection);records.append(row)
                if event['id']==active_id:collisions.append(selection.copy())
                # Deterministic display: first GF index35 switch B.x>=1.0,
                # noiseless. No result-based selection of an attractive map.
                if snapshot is None and noise==noise_conditions[0] and source['index']==35 and source['method']=='FRESHEST+GRAPH-GF' and B[0]>=1.:
                    xx,yy=np.meshgrid(field.origin[0]+np.arange(field.values.shape[1])*field.h,
                                      field.origin[1]+np.arange(field.values.shape[0])*field.h)
                    c=config['corridor']; walls=np.minimum.reduce([xx-c['xmin'],c['xmax']-xx,c['half_width']-np.abs(yy)])-.09
                    snapshot=dict(depth=field.values.copy(),oracle=np.minimum(oracle.values,walls),
                        unknown=~field.observed.copy(),origin=field.origin.copy(),h=field.h,boundary=B,run=name,fresh_id=event['id'],noise=noise)
            # Include every observation in timing even if after the final switch.
            while cursor<len(frames):
                key_seed=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
                rng=np.random.default_rng(np.random.SeedSequence([20261026,key_seed,frames[cursor]['observation_id']]))
                result=field.update(depth[cursor],k,transforms[cursor],noise=='gaussian',rng)
                timings.append(dict(run=name,noise=noise,observation_id=frames[cursor]['observation_id'],**result));cursor+=1
        print(f'EVALUATED {name} ({time.perf_counter()-start:.1f}s)',flush=True)
    summaries={};confusion=[]
    for noise in noise_conditions:
        rr=[r for r in records if r['noise']==noise];tt=[t for t in timings if t['noise']==noise]; ss=[s for s in selections if s['noise']==noise]
        counts=Counter(r['confusion'] for r in rr);n=len(rr)
        danger=counts['depth_only_safe']/n; conservative=counts['depth_only_unsafe']/n
        timing={key:distribution([t[key] for t in tt]) for key in ('update_ms','pointcloud_ms','accumulate_ms','sdf_ms','points','obstacle_points','unknown_fraction')}
        selected=[s['depth_selection_oracle_clearance_m'] for s in ss if s['depth_selected'] is not None]
        summaries[noise]=dict(samples=n,switches=len(ss),confusion=dict(counts),dangerous_fraction=danger,
            conservative_fraction=conservative,agreement_fraction=(counts['both_safe']+counts['both_unsafe'])/n,
            clearance_error_m=distribution([r['clearance_error_m'] for r in rr]),
            dangerous_oracle_clearance_m=distribution([r['oracle_clearance_m'] for r in rr if r['confusion']=='depth_only_safe']),
            error_causes=dict(Counter(r['cause'] for r in rr if r['cause'])),timing=timing,
            selection_agreement_fraction=sum(s['same'] for s in ss)/len(ss),
            selection_both_null=sum(s['depth_selected'] is None and s['oracle_selected'] is None for s in ss),
            depth_selection_oracle_clearance_m=distribution(selected),
            selected_unsafe=sum(v<.025 for v in selected),selected_count=len(selected))
        for cell in ('both_safe','both_unsafe','depth_only_safe','depth_only_unsafe'):
            confusion.append(dict(noise=noise,cell=cell,count=counts[cell],fraction=counts[cell]/n))
    noisy=summaries.get('gaussian')
    label=decision(noisy['dangerous_fraction'],noisy['conservative_fraction'],noisy['timing']['update_ms']['p95']) if noisy else 'INCOMPLETE_NO_NOISY_EVALUATION'
    summary=dict(label=label,conditions=summaries,collision_counterfactuals=collisions,
        render_git_sha=plan['execution_git_sha'],report_git_sha=git_sha(),protocol_sha256=plan['protocol_sha256'],
        frames=complete['frames'],runs=len(plan['runs']),oracle_usage='Evaluation only',odometry='Exact simulator pose; no odometry error',
        render_root=str(run_root),render_complete_sha256=sha256_file(run_root/'render_complete.json'),
        input_hashes=plan['input_hashes'],producer_hashes=plan['producer_hashes'],scope='Offline saved-pose depth replay, no navigation/inference/Graph solve')
    write_csv(destination/'switches.csv',records);write_csv(destination/'confusion.csv',confusion)
    write_csv(destination/'updates.csv',timings)
    write_json(destination/'summary.json',summary)
    make_figures(destination,records,snapshot)
    return summary


def make_figures(destination,records,snapshot):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if snapshot is None: raise RuntimeError('Pre-registered SDF display frame absent')
    fig,axes=plt.subplots(1,4,figsize=(16,4),layout='constrained')
    s=snapshot;ny,nx=s['depth'].shape;origin=s['origin'];h=s['h']
    extent=[origin[0],origin[0]+(nx-1)*h,origin[1],origin[1]+(ny-1)*h]
    for ax,data,title,cmap,vmin,vmax in zip(axes,[s['oracle'],s['depth'],s['depth']-s['oracle'],s['unknown']],
            ['Oracle (evaluation)','Depth surface field','Depth − oracle','Unknown'],
            ['viridis','viridis','coolwarm','Greys'],[-.1,-.1,-.2,0],[.5,.5,.2,1]):
        im=ax.imshow(data,origin='lower',extent=extent,cmap=cmap,vmin=vmin,vmax=vmax,interpolation='nearest')
        ax.plot(*s['boundary'][:2],'r+',ms=8);ax.set(xlim=(-.5,5),ylim=(-1.8,1.8),title=title,xlabel='World x (m)',ylabel='World y (m)')
        fig.colorbar(im,ax=ax,shrink=.6)
    fig.suptitle(f"{s['run']} F{s['fresh_id']} — noise={s['noise']}, accumulated only through switch")
    fig.savefig(destination/'sdf_compare.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    for ax,noise in zip(axes,('none','gaussian')):
        rr=[r for r in records if r['noise']==noise]
        if not rr:ax.set_title(f'{noise}: not evaluated');continue
        x=np.array([r['oracle_clearance_m'] for r in rr]);y=np.array([r['depth_clearance_m'] for r in rr])
        bad=np.array([r['confusion']=='depth_only_safe' for r in rr])
        ax.scatter(x[~bad],y[~bad],s=4,alpha=.25);ax.scatter(x[bad],y[bad],s=5,c='red',alpha=.5,label='Depth-only safe')
        lo=min(x.min(),y.min())-.02;hi=max(x.max(),y.max())+.02
        ax.plot([lo,hi],[lo,hi],'k:',lw=1);ax.axvline(.025,c='orange');ax.axhline(.025,c='orange')
        ax.set(xlabel='Exact oracle clearance (m)',ylabel='Depth clearance lower bound (m)',title=noise);ax.legend()
    fig.savefig(destination/'clearance_scatter.png',dpi=160);plt.close(fig)
