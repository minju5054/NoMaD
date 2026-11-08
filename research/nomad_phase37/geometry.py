"""Oracle/reference geometry for evaluation only, never imported by TRIG."""
import numpy as np
from nomad_phase0.pure_pursuit import XYPath


def polygon(box):
    center=np.asarray(box['center_xy_m']);size=np.asarray(box['size_xyz_m'][:2])
    theta=np.deg2rad(box.get('yaw_deg',0.));c,s=np.cos(theta),np.sin(theta);rotation=np.array([[c,-s],[s,c]])
    return (np.array([[-1,-1],[1,-1],[1,1],[-1,1]])*size/2)@rotation.T+center

def rectangle(pose,u):
    p=np.asarray(pose)[:2];u=np.asarray(u);side=np.array([-u[1],u[0]])
    return np.array([p-.2*side,p+u-.2*side,p+u+.2*side,p+.2*side])

def intersects(a,b):
    for poly in (a,b):
        for delta in np.roll(poly,-1,axis=0)-poly:
            axis=np.array([-delta[1],delta[0]]);x=a@axis;y=b@axis
            if x.max()<y.min()-1e-12 or y.max()<x.min()-1e-12:return False
    return True

def classify(pose,u,time_s,static,boxes):
    query=rectangle(pose,u);spawned=[b for b in boxes if b['spawn_s']<=time_s+1e-9]
    unpassed=[b for b in spawned if b['passage_s'] is None or b['passage_s']>time_s+1e-9]
    ahead=[b['id'] for b in unpassed if intersects(query,b['polygon'])]
    if ahead:return 'BOX_AHEAD',ahead
    fixed=[name for name,p in static if intersects(query,p)]
    if fixed:return 'STATIC_AHEAD',fixed
    def outside_or_passed(b):
        if b['passage_s'] is not None and b['passage_s']<=time_s+1e-9:return True
        delta=b['polygon']-np.asarray(pose)[:2];along=delta@np.asarray(u);side=delta@np.array([-u[1],u[0]])
        return along.max()<=0 or side.min()>.2 or side.max()<-.2
    if spawned and all(outside_or_passed(b) for b in spawned):
        return 'PASSED_BOX',[b['id'] for b in spawned]
    return 'NOTHING_AHEAD',[]


class Reference:
    def __init__(self,nodes):
        self.nodes=np.asarray(nodes);self.path=XYPath(self.nodes[:,:2])
        self.node_s=np.array([self.path.project(p[:2])[0] for p in self.nodes])

    def pose_metrics(self,pose):
        s,d=self.path.project(np.asarray(pose)[:2]);i=min(len(self.path.points)-2,max(0,int(np.searchsorted(self.path.s,s,side='right')-1)))
        v=self.path.points[i+1]-self.path.points[i];v=v/np.linalg.norm(v)
        nearest=int(np.argmin(np.linalg.norm(self.nodes[:,:2]-np.asarray(pose)[:2],axis=1)))
        return float(s),float(d),v,nearest

    def angle(self,pose,u):
        _,_,v,_=self.pose_metrics(pose);u=np.asarray(u)
        return float(np.degrees(abs(np.arctan2(u[0]*v[1]-u[1]*v[0],u@v))))
