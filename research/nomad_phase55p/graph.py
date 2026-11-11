"""Only the requested signed-speed lower bound differs from frozen U-Graph."""
import numpy as np
from nomad_ugraph.graph import Graph as FrozenGraph,solve_start
from nomad_ugraph.dynamics import N,DT,step
class Graph(FrozenGraph):
    def values(self,z):
        r=super().values(z)
        if not r.get('_forward_only'):
            # Frozen inequalities: .3-v[26], .3+v[26], SDF, domain.
            # Replace .3+v>=0 by v>=0. Its analytical Jacobian is unchanged.
            r['inequalities'][N+1:2*(N+1)]-=.3;r['_forward_only']=True
        return r
    def initial_controls(self,index):
        u=super().initial_controls(index).reshape(N,2);q=self.x0.copy()
        for k in range(N):
            u[k,0]=np.clip(u[k,0],max(-.5,-q[3]/DT),.5)
            q=step(q,u[k])[0]
        return u.ravel()
