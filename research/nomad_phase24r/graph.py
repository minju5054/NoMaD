"""Phase24 factors/hard points unchanged; DETOUR queries the C0 split map."""
import types
import numpy as np
from nomad_phase24.graph import GraphG,normal_inputs,fan_paths
from nomad_phase23o3 import graph as frozen_worker
from .safety import PlanningField

class GraphR(GraphG):
    def queries(self,p):
        self.check()
        if self.query_cache is not None and np.array_equal(p,self.query_cache[0]):return self.query_cache[1]
        q=np.vstack([p,(p[:-1]+p[1:])/2]);world=q@self.R.T+self.B[:2];clipped=np.clip(world,self.low,self.high)
        length=np.linalg.norm(np.diff(p,axis=0),axis=1);s=np.r_[0.,np.cumsum(length)];sq=np.r_[s,(s[:-1]+s[1:])/2]
        near=(sq<=.3+1e-12) if self.mode=='DETOUR' else np.ones(len(q),bool)
        distance=np.empty(len(q));gradient=np.empty_like(q)
        for mask,field in ((near,self.field.base),(~near,self.field.strict)):
            if mask.any():distance[mask],gradient[mask]=field.query(clipped[mask])
        delta=world-clipped;outside=np.linalg.norm(delta,axis=1);mask=outside>0
        distance[mask]=-outside[mask]-self.field.radius;gradient[mask]=-delta[mask]/outside[mask,None]
        jd=np.einsum('qi,qij->qj',gradient@self.R,self.query_jacobian);margin=np.where(sq<=.3+1e-12,self.start_margin,.025)
        value=(distance,jd,margin);self.query_cache=(p.copy(),value);return value

_worker=types.FunctionType(frozen_worker.worker.__code__,dict(frozen_worker.worker.__globals__,U3Graph=GraphR,Snapshot=PlanningField),argdefs=frozen_worker.worker.__defaults__)
def worker(payload,channel):return _worker(payload,channel)
