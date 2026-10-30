"""Depth-only8-connected A* core; no runtime/scene or tuning defaults here."""
import heapq,time,math
import numpy as np
from nomad_phase0.graph_v4 import menger
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase20.repair import split_arclength

NEIGHBORS=((-1,0),(0,-1),(0,1),(1,0),(-1,-1),(-1,1),(1,-1),(1,1))

class Deadline(Exception):pass


def certificate(path,B,u,base,strict):
    p=np.asarray(path);lengths=np.linalg.norm(np.diff(p,axis=0),axis=1);cB=float(base.query(np.asarray(B)[None,:2])[0][0])-base.error_bound
    threshold=min(.025,max(0.,cB-.005));s=np.r_[0,np.cumsum(lengths)];q=(p[:-1,None,:]+np.linspace(0,1,9)[None,:,None]*np.diff(p,axis=0)[:,None,:]).reshape(-1,2)
    arc=(s[:-1,None]+lengths[:,None]*np.linspace(0,1,9)).ravel();near=arc<=.3;values=np.empty(len(q))
    for mask,field in ((near,base),(~near,strict)):
        if mask.any():values[mask]=field.query(q[mask])[0]-field.error_bound
    slack=values-np.repeat(lengths,9)/16-np.where(near,threshold,.025)
    first,last=split_arclength(p);a=base.exact_clearance(first);b=strict.exact_clearance(last) if last is not None else a
    progress=float((p[-1]-np.asarray(B)[:2])@u);k=menger(p)[0]
    return dict(certificate_pass=bool(cB>=0 and a>=threshold and (last is None or b>=.025) and slack.min()>=-1e-7),depth_clearance_m=min(a,b),
        sdf_slack_m=float(slack.min()),progress_m=progress,maximum_abs_curvature_m_inv=float(np.max(np.abs(k))),
        curvature_rms_m_inv=float(np.sqrt(np.mean(k*k))),minimum_segment_m=float(lengths.min()),maximum_segment_m=float(lengths.max()),
        maximum_radius_m=float(np.linalg.norm(p-np.asarray(B)[:2],axis=1).max()),length_m=float(lengths.sum()))


def solve(B,u_ref,base,strict,clearance_weight,smoothing_iterations,point_count,deadline_ns,reference=None):
    """deadline includes caller cache/serialization; λ and iterations supplied by registration."""
    start=time.monotonic_ns();B=np.asarray(B,dtype=float);u=np.asarray(u_ref,dtype=float);u=u/np.linalg.norm(u);expansions=0;repair=reference is not None;reference=np.asarray(reference) if repair else None
    def check():
        if time.monotonic_ns()>=deadline_ns:raise Deadline()
    def finish(status,path=None,**kw):
        return dict(accepted=status=='ACCEPTED',disposition=status,path=None if path is None else np.asarray(path).tolist(),expansions=expansions,total_attempt_s=(time.monotonic_ns()-start)/1e9,**kw)
    def point_safe(q,arc,margin=0.):
        field=base if arc<=.3 else strict;threshold=near_threshold if arc<=.3 else .025
        return float(field.query(np.asarray(q)[None])[0][0])-field.error_bound-margin>=threshold
    def resample_preserving_vertices(points,count):
        curve=XYPath(points);p=curve.points;L=curve.lengths;minimum=np.ceil(L/.20-1e-10).astype(int);maximum=np.floor(L/.10+1e-10).astype(int)
        if np.any(maximum<minimum) or minimum.sum()>count-1 or maximum.sum()<count-1:return None
        n=minimum.copy()
        while n.sum()<count-1:
            choices=np.flatnonzero(n<maximum);i=max(choices,key=lambda k:(L[k]/n[k],-k));n[i]+=1
        return np.vstack([p[:1],*[np.linspace(a,b,k+1)[1:] for a,b,k in zip(p[:-1],p[1:],n)]])
    try:
        check();cB=float(base.query(B[None,:2])[0][0])-base.error_bound
        if cB<0:return finish('NEGATIVE_DEPTH_AT_B')
        near_threshold=min(.025,max(0.,cB-.005));h=base.h;origin=base.origin;shape=np.array(base.values.shape[::-1]);start_cell=np.rint((B[:2]-origin)/h).astype(int)
        def world(cell):return origin+np.asarray(cell)*h
        def grid_safe(cell,arc):
            field=base if arc<=.3 else strict;threshold=near_threshold if arc<=.3 else .025
            return float(field.values[cell[1],cell[0]])-field.error_bound-.20/16>=threshold
        root=tuple(start_cell);initial_length=float(np.linalg.norm(world(root)-B[:2]))
        if not point_safe(world(root),initial_length):return finish('START_GRID_UNSAFE')
        target=None
        if repair:
            last=reference[-1];cell=np.rint((last-origin)/h).astype(int);options=[]
            radius=int(np.ceil(.2/h))
            for dy in range(-radius,radius+1):
                for dx in range(-radius,radius+1):
                    v=(int(cell[0]+dx),int(cell[1]+dy))
                    if min(v)<0 or v[0]>=shape[0]-1 or v[1]>=shape[1]-1:continue
                    dist=float(np.linalg.norm(world(v)-last))
                    if dist<=.2+1e-12 and grid_safe(v,float('inf')):options.append((dist,v[1],v[0]))
            if not options:return finish('NO_FREE_TARGET_WITHIN_0P2')
            _,y,x=min(options);target=(x,y)
        def heuristic(q):return float(np.linalg.norm(q-world(target))) if repair else max(0.,1.2-float((q-B[:2])@u))
        # Distance-to-target half-plane is admissible because penalty is nonnegative.
        heap=[(heuristic(world(root)),0.,root)];cost={root:0.};length={root:initial_length};parent={};closed=set();best=None;goal=None
        while heap:
            check();_,g,cell=heapq.heappop(heap)
            if cell in closed or g!=cost[cell]:continue
            closed.add(cell);expansions+=1;p=world(cell);progress=float((p-B[:2])@u)
            if progress>=.5 and (best is None or (progress,-g)>best[:2]):best=(progress,-g,cell)
            if (repair and cell==target) or (not repair and progress>=1.2):goal=cell;break
            for dx,dy in NEIGHBORS:
                nxt=(cell[0]+dx,cell[1]+dy)
                if nxt in closed or min(nxt)<0 or nxt[0]>=shape[0]-1 or nxt[1]>=shape[1]-1:continue
                q=world(nxt)
                if repair:
                    if np.min(np.max(np.abs(reference-q),axis=1))>.75:continue
                elif float(np.linalg.norm(q-B[:2]))>1.6:continue
                edge=h*math.hypot(dx,dy);arc=length[cell]+edge
                if not grid_safe(nxt,arc):continue
                if dx and dy and (not grid_safe((cell[0]+dx,cell[1]),arc) or not grid_safe((cell[0],cell[1]+dy),arc)):continue
                field=base if arc<=.3 else strict;d=float(field.values[nxt[1],nxt[0]]);ng=g+edge*(1+clearance_weight*max(0.,.15-d)/.05)
                if ng>=cost.get(nxt,float('inf')):continue
                cost[nxt]=ng;length[nxt]=arc;parent[nxt]=cell;heapq.heappush(heap,(ng+heuristic(q),ng,nxt))
        check()
        if goal is None:goal=best[2] if best and not repair else None
        if goal is None:return finish('NO_PATH')
        cells=[goal]
        while cells[-1]!=root:cells.append(parent[cells[-1]])
        path=np.vstack([B[:2],np.array([world(c) for c in cells[::-1]])]);path=XYPath(path).points
        # Greedy farthest safe line-of-sight; no curve/endpoint extension.
        shortcut=[path[0]];i=0;prefix=0.
        while i<len(path)-1:
            check();found=i+1
            for j in range(len(path)-1,i,-1):
                check();a,b=path[i],path[j];L=float(np.linalg.norm(b-a));n=max(2,int(np.ceil(L/(h/2)))+1);q=np.linspace(a,b,n);arcs=prefix+np.linspace(0,L,n);ok=True
                for mask,field in ((arcs<=.3,base),(arcs>.3,strict)):
                    if mask.any():
                        limit=near_threshold if np.all(arcs[mask]<=.3) else .025
                        if float(field.query(q[mask])[0].min())-field.error_bound-L/(n-1)/2-.20/16<limit:ok=False;break
                if ok:found=j;break
            prefix+=float(np.linalg.norm(path[found]-shortcut[-1]));shortcut.append(path[found]);i=found
        if repair:
            curve=XYPath(shortcut);output=np.array([curve.at(s) for s in np.linspace(0,curve.s[-1],8)])
            minimum_lengths=.5*np.linalg.norm(np.diff(reference,axis=0),axis=1)
            def geometry_ok(q,c):
                lengths=np.linalg.norm(np.diff(q,axis=0),axis=1)
                return c['certificate_pass'] and np.max(np.abs(q-reference))<=.75+1e-7 and np.all(lengths>=minimum_lengths-1e-7) and lengths.sum()>=.7*np.linalg.norm(np.diff(reference,axis=0),axis=1).sum()-1e-7
            before=output.copy();steps=0
            for iteration in range(smoothing_iterations):
                check();k=menger(output)[0]
                if np.max(np.abs(k))<=4:break
                proposal=output.copy();active=np.flatnonzero(np.abs(k)>4)+1;proposal[active]=.25*output[active-1]+.5*output[active]+.25*output[active+1]
                c=certificate(proposal,B,u,base,strict)
                if geometry_ok(proposal,c):output=proposal
                steps+=1
            c=certificate(output,B,u,base,strict);check();edits=np.linalg.norm(output-reference,axis=1)
            return finish('ACCEPTED' if geometry_ok(output,c) else 'CERTIFICATE_OR_TRUST_FAILED',output,**c,reference=reference.tolist(),mean_edit_m=float(edits.mean()),max_edit_m=float(edits.max()),
                curvature_flag=c['maximum_abs_curvature_m_inv']>4,smoothing_iterations=steps,target_world=world(target).tolist(),unsmoothed_path=before.tolist())
        curve=XYPath(shortcut);maximum=(point_count-1)*.20;extent=min(curve.s[-1],maximum)
        if extent<(point_count-1)*.10:return finish('SHORT_PATH',shortcut)
        clipped=[p for p,s in zip(curve.points,curve.s) if s<extent];clipped.append(curve.at(extent))
        output=resample_preserving_vertices(clipped,point_count)
        if output is None:return finish('RESAMPLING_FAILED',clipped)
        before=output.copy();steps=0
        for iteration in range(smoothing_iterations):
            check();k=menger(output)[0]
            if np.max(np.abs(k))<=4:break
            proposal=output.copy();active=np.flatnonzero(np.abs(k)>4)+1
            proposal[active]=.25*output[active-1]+.5*output[active]+.25*output[active+1]
            c=certificate(proposal,B,u,base,strict)
            if c['certificate_pass'] and c['minimum_segment_m']>=.10-1e-7 and c['maximum_segment_m']<=.20+1e-7 and c['maximum_radius_m']<=1.6+1e-7:output=proposal
            steps+=1
        check();c=certificate(output,B,u,base,strict);check();curvature_failed=c['maximum_abs_curvature_m_inv']>4
        valid=c['certificate_pass'] and c['progress_m']>=.5 and c['minimum_segment_m']>=.10-1e-7 and c['maximum_segment_m']<=.20+1e-7 and c['maximum_radius_m']<=1.6+1e-7
        return finish('ACCEPTED' if valid else 'CERTIFICATE_OR_GEOMETRY_FAILED',output,**c,curvature_flag=curvature_failed,smoothing_iterations=steps,unsmoothed_path=before.tolist())
    except Deadline:return finish('TIMEOUT')
    except ValueError as exc:return finish('INVALID_GEOMETRY',error=str(exc))


def solve_repair(native,B,field,clearance_weight,smoothing_iterations,deadline_ns):
    from nomad_phase19r.repair import initialize
    reference,info=initialize(native,B)
    if reference is None:return dict(accepted=False,path=None,**info,total_attempt_s=0.)
    u=reference[-1]-np.asarray(B)[:2];n=np.linalg.norm(u);u=u/n if n>1e-12 else np.array([np.cos(B[2]),np.sin(B[2])])
    return solve(B,u,field,field,clearance_weight,smoothing_iterations,8,deadline_ns,reference=reference)
