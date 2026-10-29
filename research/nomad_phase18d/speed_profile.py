"""Geometry-only, fixed backward braking then forward acceleration pass."""
import numpy as np
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase0.graph_v4 import menger

def node_curvature(xy):
    p=XYPath(xy)
    k=menger(p.points)[0] if len(p.points)>=3 else np.empty(0)
    return p,np.r_[k[0],k,k[-1]] if len(k) else np.zeros(len(p.points))

def curvature_after(xy,B):
    p=XYPath(xy);s,_=p.project(np.asarray(B)[:2])
    k=menger(p.points)[0] if len(p.points)>=3 else np.empty(0)
    indices=np.flatnonzero(p.s[1:-1]>=s-1e-12)
    if not len(indices):return dict(max_abs=None,dominant_sign=None,turn=False,projected_s_m=s,curvatures=k.tolist(),indices=[])
    i=int(indices[np.argmax(np.abs(k[indices]))]);maximum=float(abs(k[i]))
    return dict(max_abs=maximum,dominant_sign=int(np.sign(k[i])),turn=maximum>=2.,projected_s_m=s,curvatures=k.tolist(),indices=indices.tolist())

def make_profile(xy):
    path,k=node_curvature(xy)
    limit=np.minimum(.3,.4/np.maximum(np.abs(k),1e-15));v=limit.copy()
    for i in range(len(v)-2,-1,-1):v[i]=min(v[i],np.sqrt(v[i+1]**2+path.lengths[i]))
    for i in range(1,len(v)):v[i]=min(v[i],np.sqrt(v[i-1]**2+path.lengths[i-1]))
    return dict(s_m=path.s.tolist(),v_m_s=v.tolist(),v_limit_m_s=limit.tolist(),kappa_m_inv=k.tolist(),
                definition='a=.5; endpoints copy nearest interior Menger curvature; no terminal stop-speed constraint; execution floor .05 applied after interpolation')
