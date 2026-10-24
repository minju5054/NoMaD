"""NumPy-only mirror of v2 fixed_entry/heading_chords/entry_pose for Isaac."""
import numpy as np
from nomad_phase0.pure_pursuit import XYPath


def rigid_entry(xy,boundary,minimum=.02):
    xy=np.asarray(xy,dtype=float);b=np.asarray(boundary,dtype=float)
    path=XYPath(xy);s,distance=path.project(b[:2])
    i=min(int(np.searchsorted(path.s,s,side='right')-1),len(path.delta)-1)
    kept=np.flatnonzero(np.r_[True,np.linalg.norm(np.diff(xy,axis=0),axis=1)>1e-12])
    a,z=int(kept[i]),int(kept[i+1]);u=float((s-path.s[i])/path.lengths[i])
    chords=[]
    for j in range(len(xy)):
        outgoing=[k for k in range(j+1,len(xy)) if np.linalg.norm(xy[k]-xy[j])>=minimum]
        incoming=[k for k in range(j-1,-1,-1) if np.linalg.norm(xy[j]-xy[k])>=minimum]
        if outgoing:chords.append((j,outgoing[0]))
        elif incoming:chords.append((incoming[0],j))
        else:raise ValueError(f'Node{j}: no meaningful chord >={minimum}m')
    delta=np.array([xy[k]-xy[j] for j,k in chords]);heading=np.arctan2(delta[:,1],delta[:,0])
    wrap=lambda x:(x+np.pi)%(2*np.pi)-np.pi
    yaw=heading[a]+u*wrap(heading[z]-heading[a]);entry=(1-u)*xy[a]+u*xy[z]
    turn=wrap(b[2]-yaw);c,t=np.cos(turn),np.sin(turn);rotation=np.array([[c,-t],[t,c]])
    corrected=(xy-entry)@rotation.T+b[:2]
    return corrected,dict(entry_world_xy=entry.tolist(),entry_heading_rad=float(yaw),entry_a=a,entry_b=z,
        entry_fraction=u,raw_arclength_m=float(s),raw_distance_m=float(distance),chords=chords,
        rotation_rad=float(turn),translation_m=(b[:2]-rotation@entry).tolist(),
        edit_rms_m=float(np.sqrt(np.mean(np.sum((corrected-xy)**2,axis=1)))))
