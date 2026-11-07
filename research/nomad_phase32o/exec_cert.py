"""Frozen NA PP/SP rollout and continuous circular-footprint depth certificate.

No oracle/configuration/goal argument enters this API. Occupied cell centers and
radius match the existing V1 SDF definition. Queries use immutable input maps.
"""
import math
import time
import numpy as np
from nomad_phase28.alignment import NoAlignment
from nomad_isaac.common import integrate_se2

HZ=72
CONTROL_TICKS=8
HORIZON_S=2.
RADIUS_M=.09
MARGIN_M=.025


def rollout(pose,vw,path,speed_cap=None):
    """9Hz controls, exact72Hz unicycle intervals, existing endpoint tolerance.

    No FRESH, timeout clock, recovery, or future map update is invented. A cap
    is only for the explicitly requested0.10m/s alternative: deceleration is
    limited to0.5m/s² at9Hz, and steering retains the same PP curvature.
    """
    if speed_cap not in (None,.1):raise ValueError('Only fixed alternative cap .1')
    q=np.asarray(pose,dtype=float).copy();previous_v=float(vw[0]);ctl=NoAlignment()
    ctl.replace_path(np.asarray(path,dtype=float),q,previous_v)
    qs=[q.copy()];commands=[];diagnostics=[];v=w=0.;ended=False
    for tick in range(round(HORIZON_S*HZ)):
        if tick%CONTROL_TICKS==0:
            (v,w),diag=ctl.control(q,previous_v)
            if diag['completed']:ended=True;break
            if speed_cap is not None and diag['mode']=='GO':
                v=max(previous_v-.5/9,min(v,speed_cap))
                w=float(np.clip(v*diag['kappa'],-.4,.4))
            previous_v=float(v);diagnostics.append(dict(tick=tick,**diag))
        q=integrate_se2(q,v,w,1/HZ);qs.append(q.copy());commands.append([v,w])
    return dict(poses=np.array(qs),commands=np.asarray(commands).reshape(-1,2),diagnostics=diagnostics,
                duration_s=len(commands)/HZ,endpoint_reached=ended,alignment=bool(ctl.trigger_S))


def swept_clearance(field,poses,commands):
    """Exact arcs against depth occupied cell centers (minus footprint radius).

    Very small arcs use a conservative chord lower bound with analytic sagitta
    (<1e-10m here); no grid-spacing margin is added to the final clearance.
    EDT interpolation error is used only to prune candidates, not in verdict.
    """
    if abs(float(field.radius)-RADIUS_M)>1e-12:raise ValueError('Unexpected footprint')
    points=np.asarray(poses,dtype=float);xy=points[:,:2];shape=np.array(field.occupied.shape[::-1])
    cell=(xy-field.origin)/field.h
    if np.any(cell<0) or np.any(cell>shape-1):return dict(clearance_m=None,reason='MAP_OUT_OF_BOUNDS',passed=False)
    upper=max(RADIUS_M+MARGIN_M,float(field.query(xy)[0].min())+RADIUS_M+field.error_bound)+1e-10
    lo=np.maximum(0,np.floor((xy.min(axis=0)-upper-field.origin)/field.h).astype(int)-1)
    hi=np.minimum(shape,np.ceil((xy.max(axis=0)+upper-field.origin)/field.h).astype(int)+2)
    yy,xx=np.nonzero(field.occupied[lo[1]:hi[1],lo[0]:hi[0]])
    if not len(xx):return dict(clearance_m=upper-RADIUS_M,reason='NO_SITE_WITHIN_SEARCH_BOUND',passed=True,lower_bound_only=True)
    sites=field.origin+np.c_[xx+lo[0],yy+lo[1]]*field.h
    if len(xy)==1:gap=float(np.linalg.norm(sites-xy[0],axis=1).min())-RADIUS_M
    else:
        a=xy[:-1];b=xy[1:];delta=b-a;den=np.sum(delta*delta,axis=1)
        vw=np.asarray(commands);turn=vw[:,1]/HZ
        # The nonzero curved branch excludes numerically tiny angles.
        curved=(np.abs(turn)>=1e-7)&(np.abs(vw[:,0])>1e-12)
        signed_r=np.divide(vw[:,0],vw[:,1],out=np.zeros(len(vw)),where=np.abs(vw[:,1])>1e-15)
        center=a+np.c_[-np.sin(points[:-1,2]),np.cos(points[:-1,2])]*signed_r[:,None]
        start=np.arctan2(a[:,1]-center[:,1],a[:,0]-center[:,0])
        best=math.inf
        for chunk in np.array_split(sites,max(1,math.ceil(len(sites)/512))):
            rel=chunk[None,:,:]-a[:,None,:]
            f=np.divide(np.sum(rel*delta[:,None,:],axis=2),den[:,None],out=np.zeros(rel.shape[:2]),where=den[:,None]>1e-24)
            f=np.clip(f,0,1);d=np.linalg.norm(rel-f[:,:,None]*delta[:,None,:],axis=2)
            # Conservative bound for almost-straight arcs, including stopped
            # rotation (zero center translation). Avoid cancellation in1-cos.
            sagitta=np.abs(signed_r)*2*np.sin(turn/4)**2
            d-=np.where(curved,0,sagitta)[:,None]
            if np.any(curved):
                ids=np.flatnonzero(curved);relc=chunk[None,:,:]-center[ids,None,:]
                phi=np.arctan2(relc[:,:,1],relc[:,:,0]);angular=np.mod((phi-start[ids,None])*np.sign(turn[ids,None]),2*np.pi)
                onarc=angular<=np.abs(turn[ids,None])+1e-12
                radial=np.abs(np.linalg.norm(relc,axis=2)-np.abs(signed_r[ids,None]))
                endmin=np.minimum(np.linalg.norm(chunk[None,:,:]-a[ids,None,:],axis=2),np.linalg.norm(chunk[None,:,:]-b[ids,None,:],axis=2))
                d[ids]=np.where(onarc,radial,endmin)
            best=min(best,float(d.min()))
        gap=best-RADIUS_M
    return dict(clearance_m=gap,reason='PASS' if gap>=MARGIN_M else 'DEPTH_SWEEP_UNSAFE',passed=bool(gap>=MARGIN_M),lower_bound_only=False)


def certify(pose,vw,path,field,speed_cap=None,return_trace=False):
    start=time.perf_counter()
    try:
        trajectory=rollout(pose,vw,path,speed_cap);after_rollout=time.perf_counter()
        cert=swept_clearance(field,trajectory['poses'],trajectory['commands'])
    except (ValueError,FloatingPointError) as exc:
        return dict(passed=False,reason='INVALID_INPUT',error=str(exc),compute_s=time.perf_counter()-start)
    result=dict(**cert,compute_s=time.perf_counter()-start,rollout_s=after_rollout-start,
                duration_s=trajectory['duration_s'],endpoint_reached=trajectory['endpoint_reached'],alignment=trajectory['alignment'])
    result['sweep_s']=result['compute_s']-result['rollout_s']
    if return_trace:result['trajectory']=trajectory
    return result
