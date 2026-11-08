"""Two geometric side routes. Connected-component labeling, no path search."""
import numpy as np
from scipy.ndimage import label

RADIUS=1.6
OFFSET=.09+.05

def via_path(B,via,u):
    """Closed-form interval allocation; via is an actual vertex of B+10."""
    B=np.asarray(B,float)[:2];via=np.asarray(via,float);u=np.asarray(u,float)
    delta=via-B;length=float(np.linalg.norm(delta));side=np.array([-u[1],u[0]])
    forward=float(delta@u);lateral=float(delta@side)
    if length>RADIUS+1e-12:return None,'VIA_OUTSIDE_DISK'
    lower=max(1,int(np.ceil(length/.2-1e-12)));upper=min(9,int(np.floor(length/.1+1e-12)))
    if lower>upper:return None,'VIA_SPACING_INFEASIBLE'
    n1=int(np.clip(np.floor(length/.15+.5),lower,upper));n2=10-n1
    room=float(np.sqrt(max(0.,RADIUS**2-lateral**2))-forward)
    lo=.1*n2;hi=min(.2*n2,room)
    if hi<lo-1e-12:return None,'FORWARD_SPACING_OR_DISK_INFEASIBLE'
    distance=float(np.clip(1.2-forward,lo,hi))
    p=np.vstack([np.linspace(B,via,n1+1),np.linspace(via,via+distance*u,n2+1)[1:]])
    lengths=np.linalg.norm(np.diff(p,axis=0),axis=1)
    assert p.shape==(11,2) and np.max(np.linalg.norm(p-B,axis=1))<=RADIUS+1e-10
    assert lengths.min()>=.1-1e-10 and lengths.max()<=.2+1e-10
    return p,dict(reason='GENERATED',via_index=n1,minimum_segment_m=float(lengths.min()),maximum_segment_m=float(lengths.max()),endpoint_progress_m=float((p[-1]-B)@u))

def obstacle_initializations(field,B,u):
    """Label the entire strict blocked map, choose first strip intersection,
    then clip that component to the B-centered disk before measuring sides.
    Grid cells are closed squares for the disk-boundary touch test.
    """
    B=np.asarray(B,float)[:2];u=np.asarray(u,float);np.testing.assert_allclose(np.linalg.norm(u),1.,atol=1e-12,rtol=0)
    side=np.array([-u[1],u[0]]);labels,n=label(field.occupied,np.ones((3,3),np.uint8))
    yy,xx=np.nonzero(field.occupied);xy=field.origin+np.c_[xx,yy]*field.h;delta=xy-B
    s=delta@u;lateral=delta@side;strip=(s>=0)&(s<=1.6)&(np.abs(lateral)<=.09+1e-12)
    empty=lambda reason:dict(component=None,sides=[dict(source=x,reason=reason,generated=False) for x in ('OBSTACLE_LEFT','OBSTACLE_RIGHT')])
    if not strip.any():return [],empty('NO_COMPONENT_IN_STRIP')
    identity=labels[yy,xx];possible=np.unique(identity[strip]);first=min(possible,key=lambda k:(float(s[strip&(identity==k)].min()),int(k)))
    member=identity==first;disk=np.linalg.norm(delta,axis=1)<=RADIUS+1e-12;clipped=member&disk
    if not clipped.any():return [],empty('COMPONENT_OUTSIDE_DISK')
    indices=np.flatnonzero(clipped);sides=[];extra=[]
    details=dict(component=int(first),full_cells=int(member.sum()),clipped_cells=int(clipped.sum()),first_forward_m=float(s[strip&member].min()),
        lateral_min_m=float(lateral[clipped].min()),lateral_max_m=float(lateral[clipped].max()),connectivity=8,component_domain='FULL_STRICT_MAP_THEN_DISK_CLIP')
    for sign,name in ((1,'OBSTACLE_LEFT'),(-1,'OBSTACLE_RIGHT')):
        edge=float((sign*lateral[indices]).max());ends=indices[sign*lateral[indices]>=edge-1e-10]
        # Any tied side-extremum square touching the circle has no certified
        # side exit inside the permitted disk; do not seek another waypoint.
        far_corner=np.abs(delta[ends])+field.h/2
        touches=bool(np.any(np.linalg.norm(far_corner,axis=1)>=RADIUS-1e-12))
        # Also catch a cut crossing the neighboring cell whose center lies
        # just outside the disk (cell-center clipping must not hide a wall).
        if not touches:
            for dy,dx in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
                nx=xx[ends]+dx;ny=yy[ends]+dy;valid=(nx>=0)&(ny>=0)&(nx<labels.shape[1])&(ny<labels.shape[0])
                nx=nx[valid];ny=ny[valid];q=field.origin+np.c_[nx,ny]*field.h-B
                if np.any((labels[ny,nx]==first)&(np.linalg.norm(q,axis=1)>RADIUS+1e-12)):touches=True;break
        chosen=min(ends,key=lambda i:(float(delta[i]@delta[i]),int(yy[i]),int(xx[i])))
        via=xy[chosen]+sign*OFFSET*side
        row=dict(source=name,side_extreme_m=sign*edge,edge_world=xy[chosen].tolist(),via_world=via.tolist(),boundary_touch=touches,generated=False)
        if touches:row['reason']='SIDE_TOUCHES_DISK_BOUNDARY'
        else:
            cell=np.rint((via-field.origin)/field.h).astype(int);shape=field.occupied.shape
            if cell[0]<0 or cell[1]<0 or cell[0]>=shape[1] or cell[1]>=shape[0]:row['reason']='VIA_OUT_OF_MAP'
            elif field.occupied[cell[1],cell[0]]:row['reason']='VIA_BLOCKED'
            else:
                path,detail=via_path(B,via,u)
                if path is None:row['reason']=detail
                else:
                    row.update(detail,generated=True);extra.append(dict(source=name,path=path.tolist(),via=via.tolist()))
        sides.append(row)
    return extra,dict(details,sides=sides)
