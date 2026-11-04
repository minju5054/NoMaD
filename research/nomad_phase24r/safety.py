"""C0 R3 map/certificate semantics, also applied to NORMAL G outputs."""
import numpy as np
from nomad_phase20d.recent import CachedField,build_cache,load_cache,local_certificate
from nomad_phase20.repair import split_arclength

def certificate(path,B,base,strict):
    p=np.asarray(path,dtype=float);B=np.asarray(B,dtype=float)
    if p.ndim!=2 or p.shape[1]!=2 or len(p)<2 or not np.isfinite(p).all():return dict(passed=False,reason='INVALID_PATH')
    cb=float(base.query(B[None,:2])[0][0])-base.error_bound
    if cb<0:return dict(passed=False,reason='NEGATIVE_CONSERVATIVE_B',conservative_B_m=cb)
    threshold=min(.025,max(0.,cb-.005));length=np.linalg.norm(np.diff(p,axis=0),axis=1);f=np.linspace(0,1,9)
    q=(p[:-1,None,:]*(1-f[None,:,None])+p[1:,None,:]*f[None,:,None]).reshape(-1,2)
    s=(np.r_[0,np.cumsum(length)[:-1]][:,None]+length[:,None]*f).ravel();near=s<=.3
    distance=np.empty(len(q))
    for mask,field in ((near,base),(~near,strict)):
        if mask.any():distance[mask]=field.query(q[mask])[0]
    slack=distance-base.error_bound-np.repeat(length,9)/16-np.where(near,threshold,.025)
    if float(slack.min()) < -1e-7:return dict(passed=False,reason='NINE_POINT_MARGIN',minimum_slack_m=float(slack.min()),conservative_B_m=cb)
    a,b=split_arclength(p)
    # CachedField accelerates the identical occupied-site segment distance.
    fast=object.__new__(CachedField);fast.__dict__.update(base.__dict__)
    nc=float(fast.exact_clearance(a));fc=float(strict.exact_clearance(b)) if b is not None else None
    ok=nc>=threshold and (fc is None or fc>=.025)
    return dict(passed=bool(ok),reason='PASS' if ok else 'EXACT_DISTANCE',minimum_slack_m=float(slack.min()),near_exact_m=nc,far_exact_m=fc,conservative_B_m=cb,start_threshold_m=threshold)

class PlanningField:
    def __init__(self,base,strict):
        self.__dict__.update(base.__dict__);self.base=base;self.strict=strict
    def query(self,p):return self.base.query(p)
    @classmethod
    def load(cls,file):return cls(*load_cache(file))
