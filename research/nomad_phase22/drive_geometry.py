"""Oriented-box placement/evaluation adapters; oracle never enters a planner."""
import json,math
import numpy as np
from nomad_isaac.clearance import (ObstacleMonitor,point_clearance,segment_clearance,swept_clearance,
    corridor_clearance,first_contact_bracket)
from nomad_isaac.common import write_json


def rotation(box):
    a=math.radians(box.get('yaw_deg',0.));return np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
def corners(box):
    half=np.asarray(box['size_xyz_m'][:2])/2
    return np.asarray(box['center_xy_m'])+np.array([[-1,-1],[1,-1],[1,1],[-1,1]])*half@rotation(box).T

def bounds(box):
    q=corners(box);return q.min(axis=0),q.max(axis=0)
def local_pose(pose,box):
    p=np.asarray(pose,dtype=float).copy();p[:2]=(p[:2]-box['center_xy_m'])@rotation(box);p[2]-=math.radians(box.get('yaw_deg',0.));return p
def world_pose(pose,box):
    p=np.asarray(pose,dtype=float).copy();p[:2]=p[:2]@rotation(box).T+box['center_xy_m'];p[2]+=math.radians(box.get('yaw_deg',0.));return p
def point_gap(point,box,radius):
    q=(np.asarray(point)-box['center_xy_m'])@rotation(box);half=np.array(box['size_xyz_m'][:2])/2
    return point_clearance(q,-half,half,radius)
def swept_gap(pose,v,w,dt,box,radius,threshold=.02):
    half=np.array(box['size_xyz_m'][:2])/2;r=swept_clearance(local_pose(pose,box),v,w,dt,-half,half,radius,threshold)
    if 'witness_pose' in r:r['witness_pose']=world_pose(r['witness_pose'],box).tolist()
    return r

def ray_distance(pose,box,radius):
    """World+X forward ray surface distance, diagnostic in addition to support gap."""
    R=rotation(box);q=(np.asarray(pose)[:2]-box['center_xy_m'])@R;d=np.array([1.,0.])@R;half=np.asarray(box['size_xyz_m'][:2])/2;low=0.;high=float('inf')
    for a in range(2):
        if abs(d[a])<1e-12:
            if abs(q[a])>half[a]:return None
        else:
            x=(-half[a]-q[a])/d[a];y=(half[a]-q[a])/d[a];low=max(low,min(x,y));high=min(high,max(x,y))
    return float(low-radius) if low<=high and high>=0 else None

class OrientedMonitor(ObstacleMonitor):
    def __init__(self,config,out):
        super().__init__(config,out);self.box=config['obstacle'];self.lower,self.upper=bounds(self.box)
        write_json(out/'obstacle_geometry.json',dict(**self.box,world_corners=corners(self.box).tolist(),world_aabb=[self.lower.tolist(),self.upper.tolist()],collision='Exact OBB via rigid transform and existing swept AABB evaluator',agent_radius_m=self.radius))
    def observe_interval(self,start,end,v,w,time_start,duration):
        gap=swept_gap(start,v,w,duration,self.box,self.radius,self.config['required_clearance_m']);wall=corridor_clearance(start,end,v,w,duration,self.config['corridor'],self.radius)
        self.minimum=min(self.minimum,gap['lower_m']);self.minimum_upper=min(self.minimum_upper,gap['upper_m']);self.corridor_minimum=min(self.corridor_minimum,wall)
        self.overlap|=gap['geometric_overlap'];self.margin_met&=gap['lower_m']>=self.config['required_clearance_m']
        if gap['lower_m']<=0 and self.first_contact is None:
            half=np.array(self.box['size_xyz_m'][:2])/2;bracket=first_contact_bracket(local_pose(start,self.box),v,w,duration,-half,half,self.radius)
            bracket['pose_at_bracket_end']=world_pose(bracket['pose_at_bracket_end'],self.box).tolist()
            self.first_contact=dict(interval_start_s=time_start,detected_sim_s=time_start+duration,detected_pose=list(end),**gap,**bracket)
            self.stop_reason='geometric_collision' if gap['geometric_overlap'] else 'conservative_contact_stop'
        elif wall<=0:self.stop_reason='corridor_footprint_stop'
        if self.crossing is None and start[0]<self.upper[0]+self.radius<=end[0]:self.crossing=dict(side='+Y' if end[1]>self.box['center_xy_m'][1] else '-Y',simulation_time_s=time_start+duration,pose=list(end))
        row=dict(start_sim_s=time_start,end_sim_s=time_start+duration,start_pose=list(start),end_pose=list(end),v=v,w=w,corridor_lower_m=wall,**gap)
        self.log.write(json.dumps(row)+'\n');self.log.flush();return row

def monitor(config,out):
    return OrientedMonitor(config,out) if config['obstacle'].get('yaw_deg',0) else ObstacleMonitor(config,out)
