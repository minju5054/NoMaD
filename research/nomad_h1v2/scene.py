"""Fixed path-centered box and arc-length spawn; old H1 remains untouched."""
import copy,json
from pathlib import Path
from types import FunctionType
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_isaac.clearance import configured_obstacles,point_clearance
from nomad_phase16.geometry import rect
from nomad_phase26 import scenes as frozen
from nomad_phase38.scenes import gap_check

HERE=Path(__file__).parent
SIZE=(.5,.4,.8)

def polyline(points):
    xy=np.asarray(points,float)
    lengths=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    assert xy.ndim==2 and xy.shape[1]==2 and len(xy)>1 and np.all(lengths>1e-12)
    return xy,np.r_[0.,np.cumsum(lengths)]

def at(points,s):
    xy,arc=polyline(points);s=float(np.clip(s,0,arc[-1]));i=min(int(np.searchsorted(arc,s,side='right')-1),len(xy)-2)
    u=(s-arc[i])/(arc[i+1]-arc[i]);return xy[i]+u*(xy[i+1]-xy[i]),i

def project(points,pose):
    xy,arc=polyline(points);a=xy[:-1];delta=np.diff(xy,axis=0)
    u=np.clip(np.einsum('ij,ij->i',np.asarray(pose)[:2]-a,delta)/np.einsum('ij,ij->i',delta,delta),0,1)
    q=a+u[:,None]*delta;i=int(np.argmin(np.sum((q-np.asarray(pose)[:2])**2,axis=1)))
    return float(arc[i]+u[i]*(arc[i+1]-arc[i])),q[i]

def target(points,y=1.10,x_hint=2.5):
    xy,arc=polyline(points);found=[]
    for i,(a,b) in enumerate(zip(xy[:-1],xy[1:])):
        if abs(b[1]-a[1])<1e-12:
            if abs(a[1]-y)>1e-12:continue
            u=float(np.clip((x_hint-a[0])/(b[0]-a[0]),0,1))
        else:u=(y-a[1])/(b[1]-a[1])
        if 0<=u<=1:
            q=a+u*(b-a);s=arc[i]+u*(arc[i+1]-arc[i]);found.append((abs(q[0]-x_hint),float(s),q))
    if not found:raise ValueError(f'Topomap polyline does not intersect y={y}m')
    _,s,q=min(found,key=lambda item:(item[0],item[1]));return q,s

def overlap_reasons(c,center,size=SIZE):
    center=np.asarray(center);half=np.asarray(size[:2])/2;lo,hi=center-half,center+half
    xmin,xmax,ymin,ymax=rect(c);reasons=[]
    if lo[0]<xmin-1e-9 or hi[0]>xmax+1e-9 or lo[1]<ymin-1e-9 or hi[1]>ymax+1e-9:reasons.append('outside_corridor')
    for o in configured_obstacles(c):
        oc=np.asarray(o['center_xy_m']);oh=np.asarray(o['size_xyz_m'][:2])/2
        # Same open-interior overlap tolerance as frozen H1 placement.
        if np.all(hi>oc-oh+1e-9) and np.all(oc+oh>lo+1e-9):reasons.append('static_overlap:'+o['id'])
    return reasons

def nearest_nonoverlap(c,points,desired,desired_s,size=SIZE):
    """Exact piecewise-linear candidate positions; no grid/planner/simulation.

    Minimize Euclidean center displacement on the node polyline. Ties minimize
    arc displacement, then arc position. Only overlap can invoke this function;
    a failed gap check never moves the selected box.
    """
    if not overlap_reasons(c,desired,size):return np.asarray(desired),float(desired_s),False
    xy,arc=polyline(points);half=np.asarray(size[:2])/2;x0,x1,y0,y1=rect(c)
    boundaries=[(0,x0+half[0]),(0,x1-half[0]),(1,y0+half[1]),(1,y1-half[1])]
    for o in configured_obstacles(c):
        cc=np.asarray(o['center_xy_m']);hh=np.asarray(o['size_xyz_m'][:2])/2+half
        boundaries.extend((axis,float(value)) for axis in (0,1) for value in (cc[axis]-hh[axis],cc[axis]+hh[axis]))
    choices=[]
    for i,(a,b) in enumerate(zip(xy[:-1],xy[1:])):
        delta=b-a;cuts={0.,1.}
        for axis,value in boundaries:
            if abs(delta[axis])>1e-12:
                u=(value-a[axis])/delta[axis]
                if 0<=u<=1:cuts.add(float(u))
        cuts=sorted(cuts);candidates=set(cuts);u_near=float((np.asarray(desired)-a)@delta/(delta@delta))
        for l,h in zip(cuts[:-1],cuts[1:]):
            if not overlap_reasons(c,a+((l+h)/2)*delta,size):candidates.add(float(np.clip(u_near,l,h)))
        for u in candidates:
            q=a+u*delta;s=float(arc[i]+u*(arc[i+1]-arc[i]))
            if not overlap_reasons(c,q,size):choices.append((float(np.linalg.norm(q-desired)),abs(s-desired_s),s,q))
    if not choices:raise ValueError('No non-overlapping box center on existing topomap polyline')
    _,_,s,q=min(choices,key=lambda v:v[:3]);return q,s,True

def box_front(points,center,size=SIZE):
    """First polyline entry into the closed, world-axis-aligned box footprint."""
    xy,arc=polyline(points);lo=np.asarray(center)-np.asarray(size[:2])/2;hi=np.asarray(center)+np.asarray(size[:2])/2
    hits=[]
    for i,(a,b) in enumerate(zip(xy[:-1],xy[1:])):
        delta=b-a;left,right=0.,1.
        for axis in (0,1):
            if abs(delta[axis])<1e-12:
                if a[axis]<lo[axis] or a[axis]>hi[axis]:left,right=1.,0.;break
            else:
                l,h=sorted(((lo[axis]-a[axis])/delta[axis],(hi[axis]-a[axis])/delta[axis]));left=max(left,l);right=min(right,h)
        if left<=right:hits.append((float(arc[i]+left*(arc[i+1]-arc[i])),a+left*delta))
    if not hits:raise ValueError('Selected box does not intersect topomap polyline')
    return min(hits,key=lambda x:x[0])

def return_gap_check(c,box):
    """Report-only, exact static AABB surface gaps to AfterCorner.

    Both physical widths are compared with2r+.1. No relocation, controller
    change or navigation feasibility claim follows from this local check.
    """
    after=next(o for o in configured_obstacles(c) if o['id']=='AfterCorner')
    lo=np.asarray(box['center_xy_m'])-np.asarray(box['size_xyz_m'][:2])/2
    hi=np.asarray(box['center_xy_m'])+np.asarray(box['size_xyz_m'][:2])/2
    a=np.asarray(after['center_xy_m'])-np.asarray(after['size_xyz_m'][:2])/2
    b=np.asarray(after['center_xy_m'])+np.asarray(after['size_xyz_m'][:2])/2
    sep=np.maximum(np.maximum(a-hi,lo-b),0.)
    vertical=float(a[1]-hi[1]);distance=float(np.linalg.norm(sep));required=float(2*c['agent_radius_m']+.1)
    first=np.clip((a+b)/2,lo,hi);second=np.clip(first,a,b);first=np.clip(second,lo,hi)
    checks=dict(top_to_aftercorner=bool(vertical>=required),diagonal_minimum=bool(distance>=required))
    return dict(passed=all(checks.values()),reason='PASS' if all(checks.values()) else 'RETURN_GAP_FAIL',required_gap_m=required,
        top_surface_y_m=float(hi[1]),aftercorner_bottom_y_m=float(a[1]),top_to_aftercorner_m=vertical,
        horizontal_separation_m=float(sep[0]),diagonal_minimum_m=distance,
        closest_box_point_xy_m=first.tolist(),closest_aftercorner_point_xy_m=second.tolist(),checks=checks,
        definition='top/bottom signed y gap and exact minimum Euclidean surface distance between world-axis-aligned boxes;physical width,not footprint clearance',
        scope='Static local geometry only;no rollout or claim that PP can complete the return maneuver')

def load_spec():
    p=json.loads((HERE/'scene.json').read_text())
    for file,digest in p['source_sha256'].items():assert sha256_file(ROOT/file)==digest,file
    return p

def configure(h1):
    """Apply to an H1 method config; keep all control/geometry/topomap fields."""
    assert h1['phase16_scene']=='H1','Only H1 may opt into H1-v2'
    p=load_spec();c=copy.deepcopy(h1)
    assert {k:c[k] for k in ('corridor','obstacles','start_pose','goal_pose','agent_radius_m')}==p['frozen_geometry']
    assert sha256_file(c['topomap_manifest'])==p['topomap_sha256']
    c['scene_variant']='H1-v2';c['h1v2']=p
    c['dynamic_obstacle']=dict(c['dynamic_obstacle'],size_xyz_m=list(SIZE),center_xy_m=p['box']['center_xy_m'],placement={'mode':'h1v2_fixed_topomap_arc'})
    # phase16_scene intentionally stays H1: frozen H1 rendering/evaluation and
    # static-corner handling remain valid. The explicit scene_variant names it.
    return c

def triggered(c,pose,number,first_passed=False):
    if not c.get('h1v2'):return frozen.triggered(c,pose,number,first_passed)
    return bool(number==0 and project(c['h1v2']['topomap_nodes_xy_m'],pose)[0]>=c['h1v2']['spawn']['arc_m'])

def place(c,pose,number):
    if not c.get('h1v2'):return frozen.place(c,pose,number)
    assert number==0
    p=c['h1v2'];box=copy.deepcopy(c['dynamic_obstacle']);center=np.asarray(box['center_xy_m']);half=np.asarray(box['size_xyz_m'][:2])/2
    reasons=overlap_reasons(c,center,box['size_xyz_m']);check=gap_check(c,box,1)
    if not check['passed']:reasons.append('gap_check:'+check['reason'])
    clearance=point_clearance(pose[:2],center-half,center+half,c['agent_radius_m'])
    if clearance<=0:reasons.append('spawn_overlap')
    x0,x1,y0,y1=rect(c);lo,hi=center-half,center+half
    s,_=project(p['topomap_nodes_xy_m'],pose)
    return dict(status='PLACED' if not reasons else 'PLACEMENT_INVALID',reasons=reasons,obstacle=box,spawn_pose=list(pose),axis=1,box_number=1,
        footprint_clearance_m=float(clearance),wall_clearance_m=float(min(lo[0]-x0,x1-hi[0],lo[1]-y0,y1-hi[1])),
        distance_definition='robot-center projected polyline arc = box front arc minus1.0m; first tick at/above threshold',
        projected_robot_arc_m=s,spawn_threshold_arc_m=p['spawn']['arc_m'],box_front_arc_m=p['box_front']['arc_m'],phase38_gap_check=check)

class Monitor(frozen.MultiSuddenMonitor):
    observe_tick=FunctionType(frozen.MultiSuddenMonitor.observe_tick.__code__,dict(frozen.MultiSuddenMonitor.observe_tick.__globals__,triggered=triggered,place=place),
        frozen.MultiSuddenMonitor.observe_tick.__name__,frozen.MultiSuddenMonitor.observe_tick.__defaults__,frozen.MultiSuddenMonitor.observe_tick.__closure__)

def install_environment(c):
    """Explicit opt-in, AFTER the chosen frozen method's environment installer."""
    if not c.get('h1v2'):return
    assert c['h1v2']['gap_check']['passed'],'Gap check failed; no automatic repositioning'
    import nomad_isaac.sudden_obstacle as sudden
    previous=sudden.SuddenObstacleMonitor
    def factory(config,out):return Monitor(config,out) if config.get('h1v2') else previous(config,out)
    sudden.SuddenObstacleMonitor=factory
