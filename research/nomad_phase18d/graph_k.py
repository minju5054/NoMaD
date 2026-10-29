"""Frozen analytic residual variants; inherited constraints/certificate untouched."""
import time
import numpy as np
from nomad_phase17.graph import ClearanceGraph
from nomad_phase0.graph_v4 import menger
from .speed_profile import curvature_after

VARIANTS=('CLR','NO_PROGRESS','NO_CLEARANCE','NO_BOTH','K','KP')

class CurvatureGraph(ClearanceGraph):
    def __init__(self,xy,B,previous_command,field,previous_xy=None,variant='K'):
        assert variant in VARIANTS
        super().__init__(xy,B,previous_command,field,previous_xy)
        self.variant=variant;self.native_kappa=menger(self.xy)[0]
        self.after=curvature_after(self.xy,self.boundary)
        self.remove_progress=variant in ('NO_PROGRESS','NO_BOTH') or variant=='KP' and self.after['turn']
        self.remove_clearance=variant in ('NO_CLEARANCE','NO_BOTH')

    def curvature_residual(self,x):
        xy=x.reshape(8,3)[:,:2];k,jxy=menger(xy)
        deficit=np.abs(self.native_kappa)-np.abs(k);active=deficit>0
        r=np.maximum(0.,deficit)/.5;j=np.zeros((6,24))
        j[:,0::3]=-np.sign(k)[:,None]*active[:,None]*jxy[:,:,0]/.5
        j[:,1::3]=-np.sign(k)[:,None]*active[:,None]*jxy[:,:,1]/.5
        return r,j

    def residual_jacobian(self,x):
        r,j,names,sizes=super().residual_jacobian(x)
        removed=set()
        if self.remove_progress:removed.add('endpoint_progress')
        if self.remove_clearance:removed.add('depth_clearance_preference')
        mask=np.concatenate([np.full(size,name not in removed) for name,size in zip(names,sizes)])
        n=[name for name in names if name not in removed];s=[size for name,size in zip(names,sizes) if name not in removed]
        r,j=r[mask],j[mask]
        if self.variant in ('K','KP'):
            c,cj=self.curvature_residual(x);r=np.r_[r,c];j=np.vstack([j,cj]);n+=['one_sided_curvature_preservation'];s+=[6]
        return r,j,n,s

def solve(job,field,variant):
    start=time.perf_counter()
    try:
        g=CurvatureGraph(job['world_xy'],job['boundary'],job['previous_command'],field,job['previous_xy'],variant)
        poses,solver=g.solve()
        return dict(accepted=bool(solver['feasible']),disposition='NONCONVERGED' if not solver['success'] else 'ACCEPTED' if solver['feasible'] else 'CONSTRAINT_FAILED',
                    poses=poses.tolist(),solver=solver,solve_wall_s=time.perf_counter()-start,progress_removed=g.remove_progress)
    except ValueError as e:
        return dict(accepted=False,disposition='INITIALIZATION_REJECTED',poses=None,error=str(e),solve_wall_s=time.perf_counter()-start)
