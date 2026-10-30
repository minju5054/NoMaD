"""R3 unchanged except its far-path depth field treats unknown as occupied."""
import time
import numpy as np
from nomad_phase0.graph_v4 import norm
from nomad_phase20.repair import split_arclength
from .detour import DetourGraph


class PiecewiseField:
    def __init__(self,base,strict):
        self.base=base;self.strict=strict;self.error_bound=base.error_bound;self.near=None
    def configure(self,p):
        length=norm(np.diff(p,axis=0))
        s=(np.r_[0.,np.cumsum(length)[:-1]][:,None]+length[:,None]*np.linspace(0,1,9)).ravel()
        self.near=s<=.30
    def query(self,q):
        assert self.near is not None and len(q)==90
        value=np.empty(90);grad=np.empty((90,2))
        for mask,field in ((self.near,self.base),(~self.near,self.strict)):
            if mask.any():value[mask],grad[mask]=field.query(q[mask])
        return value,grad
    def unknown_fraction(self,q):return self.base.unknown_fraction(q)


class KnownDetourGraph(DetourGraph):
    def __init__(self,B,u_ref,base,strict,angle):
        super().__init__(B,u_ref,base,angle)
        self.base_field=base;self.strict_field=strict;self.field=PiecewiseField(base,strict)
    def residual_jacobian(self,x):
        self.field.configure(self.points(x));return super().residual_jacobian(x)
    def constraints(self,x):
        self.field.configure(self.points(x));return super().constraints(x)
    def certificate(self,p):
        near,far=split_arclength(p)
        a=float(self.base_field.exact_clearance(near));b=float(self.strict_field.exact_clearance(far)) if far is not None else None
        return dict(certificate_pass=bool(a>=self.near_threshold and (b is None or b>=.025)),near_clearance_m=a,far_clearance_m=b,
                    depth_clearance_m=min(a,b) if b is not None else a)


def solve_initialization(B,u_ref,base,strict,angle):
    start=time.perf_counter()
    try:
        result=KnownDetourGraph(B,u_ref,base,strict,angle).solve();result['total_attempt_s']=time.perf_counter()-start;return result
    except ValueError as exc:return dict(accepted=False,disposition='INITIALIZATION_REJECTED',path=None,initial_path=None,solver_started=False,error=str(exc),total_attempt_s=time.perf_counter()-start)


def radial_reference(poses,tick,_unused_samples=None):
    p=np.asarray(poses);delta=p[tick,:2]-p[0,:2];length=float(np.linalg.norm(delta))
    if length<.5:return np.array([np.cos(p[0,2]),np.sin(p[0,2])]),dict(source='START_HEADING',distance_from_start_m=length)
    return delta/length,dict(source='START_TO_CURRENT_POSITION',distance_from_start_m=length)
