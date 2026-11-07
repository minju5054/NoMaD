"""G18X: only hard curvature and curvature-dependent SDF rows change.

The frozen objectives, initializers, solvers, exact certificates and EC remain
inherited. Tangent extension is used only outside the admissible |k|<=2 domain
to keep infeasible SLSQP iterates finite; every accepted point uses exact e(k).
"""
import numpy as np
from nomad_phase0.graph_v4 import menger
from nomad_phase17.graph import ClearanceGraph as FrozenNormal
from nomad_phase20.repair import RepairGraphR2 as FrozenRepair
from nomad_phase20c.detour_known import KnownDetourGraph as FrozenDetour

CURVATURE_LIMIT=2.0
LOOKAHEAD=.25

def sagitta(k):
    """Stable R-sqrt(R^2-L^2), with an analytic active-branch derivative."""
    k=np.asarray(k,dtype=float);a=np.abs(k);z=np.minimum(a,CURVATURE_LIMIT)
    root=np.sqrt(1-(LOOKAHEAD*z)**2)
    value=LOOKAHEAD**2*z/(1+root)
    derivative=LOOKAHEAD**2/(1+root)+LOOKAHEAD**4*z*z/(root*(1+root)**2)
    value=value+derivative*np.maximum(0.,a-CURVATURE_LIMIT)
    return value,derivative*np.sign(k)

def segment_margin(k,jk,node_count):
    """Endpoint curvature copies its nearest internal Menger curvature.

Each segment uses the greater absolute endpoint curvature. At ties the first
endpoint wins; zero curvature uses the zero subgradient of the absolute value.
"""
    node=np.clip(np.arange(node_count)-1,0,node_count-3)
    left,right=node[:-1],node[1:]
    selected=np.where(np.abs(k[left])>=np.abs(k[right]),left,right)
    value,derivative=sagitta(k[selected])
    return value,derivative[:,None]*jk[selected],selected

class NormalGraph(FrozenNormal):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.p=dict(self.p,curvature_limit_m_inv=CURVATURE_LIMIT)
        if abs(self.kappa_before)>CURVATURE_LIMIT:
            raise ValueError('Previous curvature exceeds Phase33 hard limit 2 m^-1')
    def sdf_rows(self,x):
        g,j=super().sdf_rows(x);xy=x.reshape(8,3)[:,:2];k,jxy=menger(xy)
        jk=np.zeros((6,24));jk[:,0::3]=jxy[:,:,0];jk[:,1::3]=jxy[:,:,1]
        e,je,_=segment_margin(k,jk,8);scale=self.p['safety_constraint_scale_m']
        return g-e[self.segment_ids]/scale,j-je[self.segment_ids]/scale

class RepairGraph(FrozenRepair):
    def constraints(self,x):
        g,j=super().constraints(x);g=g.copy();j=j.copy()
        k=8-g[63:69];jk=-j[63:69]
        e,je,_=segment_margin(k,jk,8)
        g[:63]-=e[self.segment_ids];j[:63]-=je[self.segment_ids]
        g[63:75]-=8-CURVATURE_LIMIT
        return g,j

class DetourGraph(FrozenDetour):
    def constraints(self,x):
        g,j=super().constraints(x);g=g.copy();j=j.copy()
        k=4-g[90:99];jk=-j[90:99]
        e,je,_=segment_margin(k,jk,11)
        g[:90]-=e[self.segment_ids];j[:90]-=je[self.segment_ids]
        g[90:108]-=4-CURVATURE_LIMIT
        return g,j
