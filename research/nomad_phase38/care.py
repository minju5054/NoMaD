"""Registered inverse-square CARE adaptation; depth-only obstacle input."""
import numpy as np
from nomad_phase28.telemetry import builtin

RANGE=1.0
ROTATION_CLIP=np.pi/4
SAFE_FOV=np.pi/6
EPS=1e-9  # Numerical denominator only, not a safety/planning parameter.

def obstacles(field,pose):
    yy,xx=np.nonzero(field.occupied&field.observed)
    xy=field.origin+np.c_[xx,yy]*field.h
    return xy[np.linalg.norm(xy-np.asarray(pose)[:2],axis=1)<=RANGE]

def correct(path,pose,points):
    path=np.asarray(path,float);pose=np.asarray(pose,float);points=np.asarray(points,float).reshape(-1,2)
    c,s=np.cos(pose[2]),np.sin(pose[2]);rotation=np.array([[c,-s],[s,c]])
    local=(path-pose[:2])@rotation;obs=(points-pose[:2])@rotation
    if not len(obs):return path.copy(),dict(obstacles=0,rotation_rad=0.,selected_waypoint=None,desired_heading_rad=None,safe_fov=False)
    delta=local[:,None,:]-obs[None,:,:];distance=np.linalg.norm(delta,axis=2)
    # Unit away direction times inverse squared distance; exact coincidence
    # has no unique direction and deterministically points backward.
    unit=delta/np.maximum(distance[...,None],EPS);unit[distance<EPS]=[-1.,0.]
    forces=(unit/np.maximum(distance[...,None],EPS)**2).sum(axis=1)
    strength=np.linalg.norm(forces,axis=1);selected=int(np.argmax(strength))
    theta=float(np.clip(np.arctan2(forces[selected,1],forces[selected,0]),-ROTATION_CLIP,ROTATION_CLIP)) if strength[selected]>0 else 0.
    c,s=np.cos(theta),np.sin(theta);adjusted=local@np.array([[c,s],[-s,c]])
    desired=float(np.arctan2(adjusted[selected,1],adjusted[selected,0]))
    return adjusted@rotation.T+pose[:2],builtin(dict(obstacles=len(obs),rotation_rad=theta,selected_waypoint=selected,
        forces=forces.tolist(),desired_heading_rad=desired,safe_fov=abs(desired)>SAFE_FOV,coincident_pairs=int((distance<EPS).sum())))
