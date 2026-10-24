"""Fixed pose/geometry heuristic. No predictions or future outcomes in placement."""
import numpy as np
from nomad_phase2.config import place,triggered

def intention(config,pose):
    box=next((b for b in config['obstacles'] if b['id']=='DynamicObstacle'),None)
    if box is None:return None
    x,y=box['center_xy_m'];hx,hy=np.array(box['size_xyz_m'][:2])/2
    if pose[0]>x+hx+.30:return None
    gap_left=config['corridor']['half_width']-y-hy
    gap_right=y-hy+config['corridor']['half_width']
    side=1 if gap_left>=gap_right else -1
    v=np.array([x,y+side*(hy+config['agent_radius_m']+.15)])
    return dict(side=side,V=v.tolist(),E=[x+hx+.30,float(v[1])],left_gap_m=gap_left,right_gap_m=gap_right)

def hermite(a,b,ta,tb,t):
    t=np.asarray(t)[...,None]
    return (2*t**3-3*t**2+1)*a+(t**3-2*t**2+t)*ta+(-2*t**3+3*t**2)*b+(t**3-t**2)*tb

def tangents(boundary,intent):
    b=np.asarray(boundary);v=np.array(intent['V']);e=np.array(intent['E']);l=np.linalg.norm(v-b[:2]);r=np.linalg.norm(e-v)
    direction=e-b[:2];n=np.linalg.norm(direction)
    if min(l,r,n)<1e-9:raise ValueError('Degenerate Hermite geometry')
    return l*np.array([np.cos(b[2]),np.sin(b[2])]),direction/n*min(l,r),np.array([r,0.])

def splice(boundary,intent):
    b=np.asarray(boundary);v=np.array(intent['V']);e=np.array(intent['E']);tb,tv,te=tangents(b,intent)
    t=np.linspace(0,1,33)
    return np.vstack([hermite(b[:2],v,tb,tv,t),hermite(v,e,tv,te,t)[1:]])
