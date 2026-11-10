"""Wide-box environment plumbing; no method/renderer/evaluator changes."""
import inspect,copy
from types import FunctionType
import numpy as np
from nomad_phase26 import scenes as base
from nomad_phase20b.config import place as straight_place
from nomad_isaac.clearance import configured_obstacles
from nomad_phase16.geometry import rect

REQUIRED=.18+2*.025+.1

def canonical_poses(scene):
    if scene=='H1':return [(0,[3.3,y,np.pi/2]) for y in (1.2,1.25,1.3)]
    return [(n,[x,0.,0.]) for n in range(2 if scene=='H2' else 1) for x in ((2.,2.05,2.1) if n==0 else (5.,5.05,5.1))]

def free_lateral_bounds(c,forward_lo,forward_hi,axis,nominal_center):
    xmin,xmax,ymin,ymax=rect(c);lat=1-axis;lo,hi=((xmin,xmax),(ymin,ymax))[lat]
    for box in configured_obstacles(c):
        center=np.asarray(box['center_xy_m']);half=np.asarray(box['size_xyz_m'][:2])/2;a,b=center-half,center+half
        if b[axis]<=forward_lo or a[axis]>=forward_hi:continue
        if b[lat]<=nominal_center:lo=max(lo,float(b[lat]))
        elif a[lat]>=nominal_center:hi=min(hi,float(a[lat]))
        else:raise ValueError('Static obstacle blocks intended corridor cross-section')
    return lo,hi

def spec(c):
    s=c['phase16_scene']
    if 'dynamic_obstacle' not in c:return dict(scene=s,applies=False,reason='NO_SUDDEN_BOX_STATIC_SCENE_UNCHANGED')
    axis=1 if s=='H1' else 0;lat=1-axis;base_width=c['dynamic_obstacle']['size_xyz_m'][lat]
    forward_size=c['dynamic_obstacle']['size_xyz_m'][axis];nominal=3.3 if s=='H1' else 0.;bounds=[]
    for number,pose in canonical_poses(s):
        lower=pose[axis]+c['agent_radius_m']+1.;bounds.append(free_lateral_bounds(c,lower,lower+forward_size,axis,nominal))
    lo=max(b[0] for b in bounds);hi=min(b[1] for b in bounds);middle=(lo+hi)/2
    maximum=(hi-lo-2*REQUIRED)/base_width;factor=min(1.5,maximum);assert factor>0
    width=base_width*factor;gaps=[middle-width/2-lo,hi-middle-width/2]
    return dict(scene=s,applies=True,forward_axis=axis,lateral_axis=lat,centerline_m=middle,available_bounds_m=[lo,hi],
        original_width_m=base_width,requested_multiplier=1.5,maximum_feasible_multiplier=maximum,applied_multiplier=factor,
        applied_width_m=width,reduced=factor<1.5,required_passage_m=REQUIRED,side_gaps_m=gaps,
        width_definition='Cross-direction only;forward thickness,height,spawn timing and surface offset frozen',
        center_definition='Midpoint of static free corridor cross-section;H1 inner-corner wall included')

source=inspect.getsource(base.place)
old="    center[1-axis]=c['phase26_spawn']['cross_axis_center_m'] if scene=='H1' else (.3 if number==0 else -.3)"
assert source.count(old)==1
ns=dict(base.place.__globals__)
exec(compile(source.replace(old,"    center[1-axis]=c['phase51p_wide']['centerline_m']"),__file__,'exec'),ns)
wide_place=ns['place']

def validate_placement(c,result):
    assert result['status']=='PLACED',result['reasons'];specification=c['phase51p_wide'];axis=specification['forward_axis'];lat=1-axis
    box=result['obstacle'];center=np.asarray(box['center_xy_m']);half=np.asarray(box['size_xyz_m'][:2])/2
    lo,hi=free_lateral_bounds(c,center[axis]-half[axis],center[axis]+half[axis],axis,center[lat])
    gaps=[float(center[lat]-half[lat]-lo),float(hi-center[lat]-half[lat])]
    assert min(gaps)>=-1e-9 and max(gaps)>=REQUIRED-1e-9
    return dict(status='PASS',side_gaps_m=gaps,required_m=REQUIRED,centerline_m=float(center[lat]),box=box)

def checked_place(c,pose,number):
    r=wide_place(c,pose,number);r['phase51p_width_check']=validate_placement(c,r);return r

def checked_straight(c,pose):
    r=straight_place(c,pose);r['phase51p_width_check']=validate_placement(c,r);return r

class WideMonitor(base.MultiSuddenMonitor):
    observe_tick=FunctionType(base.MultiSuddenMonitor.observe_tick.__code__,dict(base.MultiSuddenMonitor.observe_tick.__globals__,place=checked_place),
        base.MultiSuddenMonitor.observe_tick.__name__,base.MultiSuddenMonitor.observe_tick.__defaults__,base.MultiSuddenMonitor.observe_tick.__closure__)

def install(c):
    if c['phase51p_condition']!='WIDE' or 'dynamic_obstacle' not in c:return
    if c['phase16_scene']=='L2':
        import nomad_phase2.config as placement
        placement.place=checked_straight
    else:
        import nomad_isaac.sudden_obstacle as sudden
        sudden.SuddenObstacleMonitor=WideMonitor
