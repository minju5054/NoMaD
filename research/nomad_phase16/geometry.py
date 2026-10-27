"""Deterministic offline scene preparation and rectangular-frame adapters."""
import copy
import heapq
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import ROOT, integrate_se2
from nomad_isaac.clearance import corridor_clearance as _corridor, segment_clearance, obstacle_bounds, single_obstacle_config
from nomad_isaac.handoff_audit import path_safety as _safety

SCENES=ROOT/'research/nomad_isaac/scenarios'
GRID=.02
REFERENCE_TARGET=.25
REFERENCE_COST_WEIGHT=1.
REFERENCE_SMOOTH_PASSES=20


def rect(c):
    a=c['corridor'];return a['xmin'],a['xmax'],a.get('ymin',-a['half_width']),a.get('ymax',a['half_width'])


def centered(c):
    c=copy.deepcopy(c);_,_,lo,hi=rect(c);offset=(lo+hi)/2
    c['corridor'].update(half_width=(hi-lo)/2);c['corridor'].pop('ymin',None);c['corridor'].pop('ymax',None)
    for b in c['obstacles']:b['center_xy_m'][1]-=offset
    for name in ('start_pose','goal_pose'):c[name][1]-=offset
    return c,offset


def shifted(x,offset):
    a=np.array(x,dtype=float,copy=True);a[...,1]-=offset;return a


def corridor_clearance(a,b,v,w,dt,c,r):
    lo=c.get('ymin',-c['half_width']);hi=c.get('ymax',c['half_width']);offset=(lo+hi)/2
    return _corridor(shifted(a,offset),shifted(b,offset),v,w,dt,{**c,'half_width':(hi-lo)/2},r)


def path_safety(xy,c):
    cc,off=centered(c);return _safety(shifted(xy,off),cc)


def point_box_distance(points,box):
    xy=np.asarray(points);center=np.array(box['center_xy_m']);half=np.array(box['size_xyz_m'][:2])/2
    q=np.abs(xy-center)-half
    return np.linalg.norm(np.maximum(q,0),axis=-1)+np.minimum(np.max(q,axis=-1),0)


def grid_path(c,obstacle_center_margin=.11,wall_center_margin=.11):
    """8-connected A*, no diagonal corner cuts; 2cm lattice, goal center."""
    xmin,xmax,ymin,ymax=rect(c);xs=np.arange(xmin,xmax+GRID/2,GRID);ys=np.arange(ymin,ymax+GRID/2,GRID)
    xx,yy=np.meshgrid(xs,ys);points=np.stack([xx,yy],axis=-1)
    safe=(xx>=xmin+wall_center_margin)&(xx<=xmax-wall_center_margin)&(yy>=ymin+wall_center_margin)&(yy<=ymax-wall_center_margin)
    for box in c['obstacles']:safe &= point_box_distance(points,box)>=obstacle_center_margin-1e-12
    def cell(p):return (int(round((p[1]-ymin)/GRID)),int(round((p[0]-xmin)/GRID)))
    start,goal=cell(c['start_pose']),cell(c['goal_pose']);assert safe[start] and safe[goal]
    queue=[(0.,0.,start)];cost={start:0.};parent={};expanded=0
    while queue:
        _,g,u=heapq.heappop(queue)
        if g!=cost[u]:continue
        expanded+=1
        if u==goal:break
        for dy,dx in ((0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)):
            v=(u[0]+dy,u[1]+dx)
            if not (0<=v[0]<len(ys) and 0<=v[1]<len(xs) and safe[v]):continue
            if dx and dy and not (safe[u[0],v[1]] and safe[v[0],u[1]]):continue
            ng=g+GRID*np.hypot(dx,dy)
            if ng>=cost.get(v,float('inf'))-1e-12:continue
            cost[v]=ng;parent[v]=u;h=GRID*np.hypot(v[0]-goal[0],v[1]-goal[1]);heapq.heappush(queue,(ng+h,ng,v))
    else:raise ValueError('NO_GRID_PATH: fixed geometry/margins, no retry')
    cells=[goal]
    while cells[-1]!=start:cells.append(parent[cells[-1]])
    p=np.array([[xs[x],ys[y]] for y,x in reversed(cells)]);p[0]=c['start_pose'][:2];p[-1]=c['goal_pose'][:2]
    return p,dict(grid_m=GRID,connectivity=8,no_corner_cut=True,expanded=expanded,length_m=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),goal='exact center; no terminal yaw',obstacle_center_margin_m=obstacle_center_margin,wall_center_margin_m=wall_center_margin)


def center_clearance(points,c):
    xy=np.asarray(points);xmin,xmax,ymin,ymax=rect(c)
    d=np.minimum.reduce([xy[...,0]-xmin,xmax-xy[...,0],xy[...,1]-ymin,ymax-xy[...,1]])
    for b in c['obstacles']:d=np.minimum(d,point_box_distance(xy,b))
    return d


def _narrow_centers(points,c):
    """Opposing nearest surfaces define a local sub-0.5m passage centerline.

    Used only if no >=0.25m connected grid path exists. Two nearest surface
    normals must oppose (dot <= -0.9); centerline grid tolerance is one cell.
    Grid witnesses below .25m are projected to the exact surface midpoint.
    """
    p=np.asarray(points);xmin,xmax,ymin,ymax=rect(c);surfaces=[]
    for axis,value in ((0,xmin),(0,xmax),(1,ymin),(1,ymax)):
        s=p.copy();s[...,axis]=value;surfaces.append(s)
    for b in c['obstacles']:
        center=np.array(b['center_xy_m']);half=np.array(b['size_xyz_m'][:2])/2
        surfaces.append(np.clip(p,center-half,center+half))
    surfaces=np.stack(surfaces,axis=-2);vectors=surfaces-p[...,None,:];dist=np.linalg.norm(vectors,axis=-1)
    ids=np.argsort(dist,axis=-1)[...,:2];nearest=np.take_along_axis(surfaces,ids[...,None],axis=-2)
    v=nearest-p[...,None,:];d=np.linalg.norm(v,axis=-1)
    dot=np.sum(v[...,0,:]*v[...,1,:],axis=-1)/np.maximum(d[...,0]*d[...,1],1e-20)
    narrow=(d.sum(axis=-1)<2*REFERENCE_TARGET-1e-10)&(dot<=-.9)&(np.abs(d[...,0]-d[...,1])<=GRID+1e-10)
    return narrow,nearest.mean(axis=-2)


def reference_path(c):
    """Frozen clearance-weighted grid planning plus certified smoothing.

    First search is constrained to .25m from boxes AND outer walls. Only when
    disconnected, use the prescribed narrow-passage centerline exception.
    This deterministic feasibility branch is not a navigation retry or tuning.
    """
    xmin,xmax,ymin,ymax=rect(c);xs=np.arange(xmin,xmax+GRID/2,GRID);ys=np.arange(ymin,ymax+GRID/2,GRID)
    xx,yy=np.meshgrid(xs,ys);points=np.stack([xx,yy],axis=-1);distance=center_clearance(points,c)
    start=(round((c['start_pose'][1]-ymin)/GRID),round((c['start_pose'][0]-xmin)/GRID));goal=(round((c['goal_pose'][1]-ymin)/GRID),round((c['goal_pose'][0]-xmin)/GRID))
    narrow,midpoints=_narrow_centers(points,c);expanded_total=0
    for use_narrow in (False,True):
        safe=distance>=REFERENCE_TARGET-1e-10
        if use_narrow:safe |= narrow & (distance>=c['agent_radius_m']+c['required_clearance_m'])
        if not (safe[start] and safe[goal]):continue
        queue=[(0.,0.,start)];cost={start:0.};parent={};found=False
        while queue:
            _,g,u=heapq.heappop(queue)
            if g!=cost[u]:continue
            expanded_total+=1
            if u==goal:found=True;break
            for dy,dx in ((0,1),(1,0),(0,-1),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)):
                v=(u[0]+dy,u[1]+dx)
                if not (0<=v[0]<len(ys) and 0<=v[1]<len(xs) and safe[v]):continue
                if dx and dy and not (safe[u[0],v[1]] and safe[v[0],u[1]]):continue
                penalty=1+REFERENCE_COST_WEIGHT*(REFERENCE_TARGET/max(min(distance[u],distance[v]),.11))**2
                ng=g+GRID*np.hypot(dx,dy)*penalty
                if ng>=cost.get(v,float('inf'))-1e-12:continue
                cost[v]=ng;parent[v]=u;h=GRID*np.hypot(v[0]-goal[0],v[1]-goal[1]);heapq.heappush(queue,(ng+h,ng,v))
        if found:break
    if not found:raise ValueError('REFERENCE_INFEASIBLE: no fixed clearance/centerline witness')
    cells=[goal]
    while cells[-1]!=start:cells.append(parent[cells[-1]])
    cells=list(reversed(cells));path=np.array([points[cell] for cell in cells]);pinned=np.array([distance[cell]<REFERENCE_TARGET-1e-10 for cell in cells])
    if use_narrow:
        for i,cell in enumerate(cells):
            if pinned[i]:path[i]=midpoints[cell]
    path[0]=c['start_pose'][:2];path[-1]=c['goal_pose'][:2]
    # Ten-millimetre certification samples with Lipschitz allowance first; use
    # the existing exact polyline evaluator for full final certification.
    radius_free=copy.deepcopy(c);radius_free['agent_radius_m']=0.
    for _ in range(REFERENCE_SMOOTH_PASSES):
        old=path.copy();candidate=.25*old[:-2]+.5*old[1:-1]+.25*old[2:]
        for i,p in enumerate(candidate,1):
            if pinned[i] or pinned[i-1] or pinned[i+1]:continue
            local=np.array([path[i-1],p,old[i+1]])
            # Do not sacrifice existing local clearance merely to smooth a corner.
            baseline=path_safety(np.array([path[i-1],old[i],old[i+1]]),radius_free)
            minimum=max(REFERENCE_TARGET,min(baseline['obstacle_clearance_m'],baseline['corridor_clearance_m'])-1e-10)
            s=path_safety(local,radius_free)
            if min(s['obstacle_clearance_m'],s['corridor_clearance_m'])>=minimum-1e-10:path[i]=p
    path=path[np.r_[True,np.linalg.norm(np.diff(path,axis=0),axis=1)>1e-12]]
    safety=path_safety(path,c);center_min=min(safety['obstacle_clearance_m'],safety['corridor_clearance_m'])+c['agent_radius_m']
    if not use_narrow:assert center_min>=REFERENCE_TARGET-1e-8
    assert min(safety['obstacle_clearance_m'],safety['corridor_clearance_m'])>=.02-1e-9
    return path,dict(grid_m=GRID,cost='edge_length*(1+(.25/min(endpoint_center_clearance))^2)',cost_weight=REFERENCE_COST_WEIGHT,
        target_center_distance_m=REFERENCE_TARGET,obstacles_and_outer_walls=True,expanded=expanded_total,smoothing_passes=REFERENCE_SMOOTH_PASSES,
        narrow_centerline_used=use_narrow,narrow_grid_nodes=int(pinned.sum()),reference_length_m=float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum()),
        minimum_center_distance_m=center_min,minimum_footprint_clearance_m=center_min-c['agent_radius_m'],
        minimum_box_center_distance_m=safety['obstacle_clearance_m']+c['agent_radius_m'],minimum_wall_center_distance_m=safety['corridor_clearance_m']+c['agent_radius_m'])


def simplify(path,c,center_margin,wall_margin=.11):
    """Greedy farthest line-of-sight pruning; fixed margins, no retuning."""
    cc=copy.deepcopy(c);cc['agent_radius_m']=0
    keep=[0]
    while keep[-1]<len(path)-1:
        a=keep[-1]
        for b in range(len(path)-1,a,-1):
            s=path_safety(path[[a,b]],cc)
            if s['obstacle_clearance_m']>=center_margin-1e-10 and s['corridor_clearance_m']>=wall_margin-1e-10:break
        else:raise ValueError('No safe reference simplification')
        keep.append(b)
    # Densify the polyline to <=2cm; there are no intrinsic waypoint timestamps.
    pts=[]
    for a,b in zip(path[keep][:-1],path[keep][1:]):
        n=max(1,int(np.ceil(np.linalg.norm(b-a)/.02)));pts.extend(np.linspace(a,b,n+1)[:-1])
    return np.vstack([pts,path[-1]])


def reference_rollout(c,path):
    from nomad_phase0.pure_pursuit import PurePursuit
    from nomad_phase0.chunk_execution import protocol
    follower=PurePursuit(path,protocol()['follower']);pose=np.array(c['start_pose']);poses=[pose.copy()];cmds=[]
    reason='REFERENCE_TIMEOUT';minimum=float('inf');wall_min=float('inf');command=(0.,0.)
    for tick in range(120*72):
        if tick%8==0:command,_=follower.control(pose);cmds.append(dict(tick=tick,v=command[0],w=command[1]))
        nxt=integrate_se2(pose,*command,1/72);s=path_safety(np.array([pose[:2],nxt[:2]]),c);minimum=min(minimum,s['obstacle_clearance_m'])
        wall_min=min(wall_min,s['corridor_clearance_m']);pose=nxt;poses.append(pose.copy())
        if s['obstacle_clearance_m']<.02 or s['corridor_clearance_m']<=0:reason='REFERENCE_TRACKING_SAFETY_FAILURE';break
        if np.linalg.norm(pose[:2]-c['goal_pose'][:2])<=.3:reason='goal_entry';break
    return np.array(poses),cmds,dict(reason=reason,minimum_obstacle_clearance_m=minimum,minimum_wall_clearance_m=wall_min,
        minimum_center_distance_m=min(minimum,wall_min)+c['agent_radius_m'],minimum_footprint_clearance_m=min(minimum,wall_min),
        duration_s=(len(poses)-1)/72,goal=reason=='goal_entry',execution_distance_m=float(np.linalg.norm(np.diff(np.array(poses)[:,:2],axis=0),axis=1).sum()))


def box(name,center,size,height=.8):
    return dict(id=name,center_xy_m=list(center),size_xyz_m=[*size,height],color_rgb=[.04,.65,.04])


def build_scenes():
    base=json.loads((ROOT/'research/nomad_isaac/two_obstacles_wide_wall_scenario.json').read_text());output={}
    for name in ('SL','LC','CL'):
        c=copy.deepcopy(base);c.update(name=f'phase16_{name}',phase16_scene=name,timeout_sim_s=90.,synchronous=False)
        c['corridor'].update(xmin=-1.,xmax=6.,half_width=.9 if name=='SL' else 1.5)
        c['goal_pose']=[5.,0.,0.]
        if name=='SL':c['obstacles']=[box(f'Slalom{i+1}',[x,y],[.4,1.2]) for i,(x,y) in enumerate(((1.3,.3),(2.7,-.3),(4.1,.3)))];c['checkpoint']=dict(axis=0,threshold_m=4.6,meaning='last box far X face + 0.30m')
        elif name=='LC':
            c['corridor'].update(xmax=4.2,ymin=-1.,ymax=4.2,half_width=2.6)
            c['goal_pose']=[3.3,3.2,0.]
            c['obstacles']=[box('InnerCorner',[.7,2.55],[3.4,3.3],1.),box('AfterCorner',[3.6,1.9],[.5,.4])]
            c['checkpoint']=dict(axis=1,threshold_m=2.4,meaning='after-corner obstacle far Y face + 0.30m')
        else:
            rng=np.random.default_rng(20261028);boxes=[];trials=0
            while len(boxes)<5 and trials<10000:
                trials+=1;size=rng.uniform(.3,.6,2);center=[rng.uniform(1.,4.),rng.uniform(-1.5+size[1]/2+.45,1.5-size[1]/2-.45)]
                b=box(f'Clutter{len(boxes)+1}',center,size.tolist())
                if any(point_box_distance(np.array(p[:2]),b)<.8 for p in (c['start_pose'],c['goal_pose'])):continue
                if any(np.linalg.norm(np.maximum(np.abs(np.array(center)-a['center_xy_m'])-(np.array(size)+a['size_xyz_m'][:2])/2,0))<.45 for a in boxes):continue
                boxes.append(b)
            assert len(boxes)==5
            c['obstacles']=boxes;c['placement']=dict(seed=20261028,trials=trials,size_uniform_m=[.3,.6],center_x_uniform_m=[1.,4.],minimum_box_and_wall_gap_m=.45,start_goal_surface_exclusion_m=.8)
            c['checkpoint']=dict(axis=0,threshold_m=max(b['center_xy_m'][0]+b['size_xyz_m'][0]/2 for b in boxes)+.30,meaning='last box far X face + 0.30m')
        path,diag=grid_path(c);c['reference_length_m']=diag['length_m'];c['grid_feasibility']=diag
        output[name]=c
    return output
