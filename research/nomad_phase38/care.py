"""CARE equations on current-frame points; no occupancy map or SAFE filter."""
import numpy as np
from nomad_phase28.telemetry import builtin
from nomad_phase15.depth_sdf import backproject,intrinsics,camera_to_world

RANGE=1.0
BINS=32
ROTATION_CLIP=np.pi/4
SAFE_FOV=np.pi/6
EPS=1e-9  # Numerical singularity guard only.

def nearest_bins(camera_xyz,world_xyz,bins=BINS):
    """Uniform camera-X bins spanning valid X min/max, right edge inclusive."""
    points=np.asarray(camera_xyz,float).reshape(-1,3);world=np.asarray(world_xyz,float).reshape(-1,3)
    assert len(points)==len(world) and bins==BINS
    if not len(points):return np.empty((0,2)),dict(bin_ids=[],point_indices=[],lateral_span_m=None)
    left,right=float(points[:,0].min()),float(points[:,0].max())
    ids=np.zeros(len(points),int) if right==left else np.minimum(bins-1,np.floor((points[:,0]-left)/(right-left)*bins).astype(int))
    chosen=[];used=[]
    for b in range(bins):
        members=np.flatnonzero(ids==b)
        if len(members):used.append(b);chosen.append(int(members[np.argmin(points[members,2])]))
    return world[chosen,:2].copy(),dict(bin_ids=used,point_indices=chosen,lateral_span_m=[left,right])

def frame_obstacles(depth,camera,pose,offset,frame,noise=True):
    """Same camera/backprojection/noise/height filter, axial Z<=1m, no history."""
    k=intrinsics(camera,width=np.shape(depth)[1],height=np.shape(depth)[0])
    transform=camera_to_world(pose,camera['height_m'])
    rng=np.random.default_rng(np.random.SeedSequence([20261027,int(offset),int(frame)]))
    world,_,measured=backproject(depth,k,transform,noise,rng)
    valid=np.isfinite(measured)&(measured>0);v,u=np.nonzero(valid);z=measured[v,u]
    xyz=np.c_[(u+.5-k[2])*z/k[0],-(v+.5-k[3])*z/k[1],z]
    keep=(z>0)&(z<=RANGE)&(world[:,2]>.03)&(world[:,2]<=.6)
    points,detail=nearest_bins(xyz[keep],world[keep])
    return points,builtin(dict(detail,backprojected_points=len(world),filtered_points=int(keep.sum()),
        obstacle_points=len(points),bins=BINS,axial_range_m=RANGE,height_filter_m=[.03,.6],noise_enabled=bool(noise)))

def correct(path,pose,points):
    path=np.asarray(path,float);pose=np.asarray(pose,float);points=np.asarray(points,float).reshape(-1,2)
    c,s=np.cos(pose[2]),np.sin(pose[2]);rotation=np.array([[c,-s],[s,c]])
    local=(path-pose[:2])@rotation;obs=(points-pose[:2])@rotation
    if not len(obs):return path.copy(),dict(obstacles=0,rotation_rad=0.,selected_waypoint=None,desired_heading_rad=None,safe_fov=False)
    delta=local[:,None,:]-obs[None,:,:];distance=np.linalg.norm(delta,axis=2)
    # User-fixed robot-plane sign: away from the obstacle. The vector norm
    # of each term is1/d^3 because the numerator has length d.
    forces=(delta/np.maximum(distance[...,None],EPS)**4).sum(axis=1)
    strength=np.linalg.norm(forces,axis=1);selected=int(np.argmax(strength))
    theta=float(np.clip(np.arctan2(forces[selected,1],forces[selected,0]),-ROTATION_CLIP,ROTATION_CLIP)) if strength[selected]>0 else 0.
    c,s=np.cos(theta),np.sin(theta);adjusted=local@np.array([[c,s],[-s,c]])
    desired=float(np.arctan2(adjusted[selected,1],adjusted[selected,0]))
    return adjusted@rotation.T+pose[:2],builtin(dict(obstacles=len(obs),rotation_rad=theta,selected_waypoint=selected,
        forces=forces.tolist(),desired_heading_rad=desired,safe_fov=abs(desired)>SAFE_FOV,coincident_pairs=int((distance<EPS).sum())))
