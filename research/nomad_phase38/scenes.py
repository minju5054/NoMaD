"""Seed-fixed lateral box perturbation; placement/evaluation plumbing only."""
import copy,inspect
from types import FunctionType
import numpy as np
from nomad_phase26 import scenes as frozen
from nomad_phase20b.config import place as l2_place
from nomad_phase16.geometry import rect
from nomad_isaac.clearance import configured_obstacles

source=inspect.getsource(frozen.place)
line="    center+=np.asarray(c['phase26_spawn'].get('geometry_adjustment_xy',[0.,0.]))"
assert source.count(line)==1
scope=dict(frozen.place.__globals__)
exec(source.replace(line,"    center[1-axis]+=c['phase38_jitter'][number]['offset_m']\n"+line),scope)
multi_place=scope['place']

class JitterMonitor(frozen.MultiSuddenMonitor):
    observe_tick=FunctionType(frozen.MultiSuddenMonitor.observe_tick.__code__,
        dict(frozen.MultiSuddenMonitor.observe_tick.__globals__,place=multi_place),
        frozen.MultiSuddenMonitor.observe_tick.__name__,frozen.MultiSuddenMonitor.observe_tick.__defaults__,
        frozen.MultiSuddenMonitor.observe_tick.__closure__)

def straight_place(c,pose):
    shifted=copy.deepcopy(c);shifted['blockage_center_y_m']+=c['phase38_jitter'][0]['offset_m']
    result=l2_place(shifted,pose);result['phase38_lateral_offset_m']=c['phase38_jitter'][0]['offset_m'];return result

def gap_check(c,box,axis):
    lo=np.asarray(box['center_xy_m'])-np.asarray(box['size_xyz_m'][:2])/2
    hi=np.asarray(box['center_xy_m'])+np.asarray(box['size_xyz_m'][:2])/2
    xmin,xmax,ymin,ymax=rect(c);bounds=((xmin,xmax),(ymin,ymax));lat=1-axis;lower,upper=bounds[lat]
    for obstacle in configured_obstacles(c):
        a=np.asarray(obstacle['center_xy_m'])-np.asarray(obstacle['size_xyz_m'][:2])/2
        b=np.asarray(obstacle['center_xy_m'])+np.asarray(obstacle['size_xyz_m'][:2])/2
        if b[axis]<=lo[axis] or a[axis]>=hi[axis]:continue
        if b[lat]<=lo[lat]:lower=max(lower,b[lat])
        elif a[lat]>=hi[lat]:upper=min(upper,a[lat])
        else:return dict(passed=False,reason='STATIC_OVERLAP',gaps_m=[0.,0.])
    gaps=[float(lo[lat]-lower),float(upper-hi[lat])]
    inside=all(bounds[k][0]<=lo[k] and hi[k]<=bounds[k][1] for k in (0,1))
    passed=inside and min(gaps)>=0 and max(gaps)>=2*c['agent_radius_m']+.1
    return dict(passed=bool(passed),reason='PASS' if passed else 'OVERLAP_OR_NO_PASSABLE_GAP',gaps_m=gaps,
        required_gap_m=float(2*c['agent_radius_m']+.1))

def registered_jitter(scene,index):
    if scene not in ('L2','H1','H2'):return []
    from nomad_phase35.config import runtime_config
    c=runtime_config('OURS',95 if index==95 else 212,90,scene);out=[]
    for number in range(2 if scene=='H2' else 1):
        rng=np.random.default_rng(np.random.SeedSequence([20261111,index,('L2','H1','H2').index(scene),number]))
        pose=[3.3,1.25,np.pi/2] if scene=='H1' else [5.05 if number else 2.05,0.,0.]
        for attempt in range(10000):
            offset=float(rng.uniform(-.2,.2));c['phase38_jitter']=out+[dict(offset_m=offset)]
            result=straight_place(c,pose) if scene=='L2' else multi_place(c,pose,number)
            check=gap_check(c,result['obstacle'],1 if scene=='H1' else 0)
            if result['status']=='PLACED' and check['passed']:
                out.append(dict(offset_m=offset,draw=attempt+1,geometry=check,canonical_pose=pose,canonical_box=result['obstacle']));break
        else:raise ValueError('No valid registered lateral placement')
    return out

def install(c):
    if c['phase16_scene']=='L2':
        import nomad_phase2.config as placement
        placement.place=straight_place
    elif c['phase16_scene'] in ('H1','H2'):
        import nomad_isaac.sudden_obstacle as sudden
        sudden.SuddenObstacleMonitor=JitterMonitor
