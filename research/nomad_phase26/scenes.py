"""Spawn/evaluation-only geometry. Never passed to a method's planner."""
import copy,json,time
import numpy as np
from nomad_isaac.common import write_json
from nomad_isaac.clearance import ObstacleMonitor,single_obstacle_config,point_clearance,configured_obstacles
from nomad_phase16.geometry import rect

def triggered(c,pose,number,first_passed=False):
    if c['phase16_scene']=='H1':return number==0 and 1.2<=pose[1]<=1.3
    if number==0:return 2.0<=pose[0]<=2.1
    return number==1 and first_passed and 5.0<=pose[0]<=5.1

def place(c,pose,number):
    scene=c['phase16_scene'];axis=1 if scene=='H1' else 0
    box=copy.deepcopy(c['dynamic_obstacle']);box['id']='DynamicObstacle' if number==0 else 'DynamicObstacle2'
    h=np.asarray(box['size_xyz_m'][:2])/2;r=c['agent_radius_m']
    # Same 1m front-surface-to-footprint convention as frozen L2 placement.
    center=np.asarray(pose[:2],float).copy();center[axis]+=r+1.+h[axis]
    center[1-axis]=c['phase26_spawn']['cross_axis_center_m'] if scene=='H1' else (.3 if number==0 else -.3)
    center+=np.asarray(c['phase26_spawn'].get('geometry_adjustment_xy',[0.,0.]))
    box['center_xy_m']=center.tolist();lo,hi=center-h,center+h
    xmin,xmax,ymin,ymax=rect(c);wall=min(lo[0]-xmin,xmax-hi[0],lo[1]-ymin,ymax-hi[1])
    gap=point_clearance(pose[:2],lo,hi,r);reasons=[]
    for fixed in configured_obstacles(c):
        fc=np.array(fixed['center_xy_m']);fh=np.array(fixed['size_xyz_m'][:2])/2
        if np.all(hi>fc-fh+1e-9) and np.all(fc+fh>lo+1e-9):reasons.append('static_overlap:'+fixed['id'])
    if wall<0:reasons.append('outside_corridor')
    if gap<=0:reasons.append('spawn_overlap')
    return dict(status='PLACED' if not reasons else 'PLACEMENT_INVALID',reasons=reasons,obstacle=box,
                spawn_pose=list(pose),axis=axis,box_number=number+1,footprint_clearance_m=float(gap),wall_clearance_m=float(wall),
                distance_definition='1m between forward robot footprint support and box near face')

class AxisMonitor(ObstacleMonitor):
    def __init__(self,c,out,axis):super().__init__(c,out);self.axis=axis
    def observe_interval(self,start,end,v,w,time_start,duration):
        old=self.crossing;r=super().observe_interval(start,end,v,w,time_start,duration)
        if self.axis==1:
            self.crossing=old
            if old is None and start[1]<self.upper[1]+self.radius<=end[1]:
                self.crossing=dict(side='+X' if end[0]>self.config['obstacle']['center_xy_m'][0] else '-X',simulation_time_s=time_start+duration,pose=list(end))
        return r

class MultiSuddenMonitor:
    """Same tick/swept evaluator, with persistent per-box render and passage."""
    def __init__(self,c,out):
        self.config=c;self.output=out/'dynamic';self.output.mkdir();self.adaptive=True
        self.activation=(self.output/'activation.jsonl').open('x');self.children=[];self.placement=None;self.spawn=None
        self.last_tick=-1;self.active_checks=0;self.target=1 if c['phase16_scene']=='H1' else 2
    @property
    def obstacle(self):
        return dict(self.children[0]['box'],phase26_boxes=[dict(v['box']) for v in self.children]) if self.children else None
    @property
    def stop_reason(self):
        if self.placement and self.placement['status']!='PLACED':return 'placement_invalid'
        return next((v['monitor'].stop_reason for v in self.children if v['monitor'].stop_reason),None)
    def observe_tick(self,tick,previous,pose,v,w,old_id,old_valid,monotonic_ns,old_received_ns=None):
        assert tick==self.last_tick+1;self.last_tick=tick
        for child in self.children:
            child['monitor'].observe_interval(previous,pose,v,w,(tick-1)/72,1/72)
        number=len(self.children);first_passed=bool(self.children and self.children[0]['monitor'].crossing)
        if number<self.target and triggered(self.config,pose,number,first_passed) and not self.stop_reason:
            placement=place(self.config,pose,number);placement.update(decision_tick=tick,decision_sim_s=tick/72)
            self.placement=placement;folder=self.output/f'box_{number+1}';folder.mkdir()
            write_json(folder/'placement.json',placement)
            if placement['status']=='PLACED':
                box=placement['obstacle'];box['spawn_tick']=tick
                monitor=AxisMonitor(single_obstacle_config(self.config,box),folder,placement['axis'])
                check=monitor.observe_interval(pose,pose,v,w,tick/72,0.)
                spawn=dict(tick=tick,simulation_time_s=tick/72,pose=list(pose),old_id=old_id,old_command_valid=old_valid,
                           obstacle=box,footprint_clearance_m=check['lower_m'])
                self.children.append(dict(box=box,monitor=monitor,spawn=spawn,placement=placement))
                write_json(folder/'spawn.json',spawn)
                if self.spawn is None:
                    self.spawn=spawn;write_json(self.output/'spawn.json',spawn);write_json(self.output/'placement.json',placement)
        self.active_checks+=bool(self.children)
        row=dict(tick=tick,simulation_time_s=tick/72,active=bool(self.children),collision_checked=bool(self.children),
                 active_boxes=len(self.children),first_passed=first_passed,monotonic_ns=monotonic_ns)
        self.activation.write(json.dumps(row)+'\n');self.activation.flush();return row
    def finish(self,goal_entry):
        self.activation.close();results=[]
        for v in self.children:
            results.append(dict(spawn=v['spawn'],placement=v['placement'],evaluation=v['monitor'].finish(goal_entry)))
        evaluations=[r['evaluation'] for r in results]
        agg=dict(geometric_overlap=any(r['geometric_overlap'] for r in evaluations),
                 corridor_containment_certified=all(r['corridor_containment_certified'] for r in evaluations),passage=None,
                 avoidance_success=bool(goal_entry and len(results)==self.target and all(r['avoidance_success'] for r in evaluations)))
        for key in ('minimum_swept_clearance_lower_m','minimum_swept_clearance_upper_m','minimum_corridor_clearance_lower_m'):
            values=[r[key] for r in evaluations if r.get(key) is not None];agg[key]=min(values) if values else None
        if len(results)==self.target and all(r['evaluation'].get('passage') for r in results):agg['passage']=results[-1]['evaluation']['passage']
        return dict(status='SPAWNED' if results else 'NOT_TRIGGERED',spawn=self.spawn,placement=self.placement,
                    evaluation=agg,active_checks=self.active_checks,boxes=results,expected_boxes=self.target)
