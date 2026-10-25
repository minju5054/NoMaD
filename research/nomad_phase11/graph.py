"""Graph-v6.1 changes only endpoint-progress target; no new solver/weights."""
import numpy as np
from nomad_phase9.graph import GraphV6


def progress_metadata(xy, boundary):
    xy=np.asarray(xy);b=np.asarray(boundary)
    p=float((xy[-1]-b[:2])@np.array([np.cos(b[2]),np.sin(b[2])]))
    target=min(.25,.9*max(p,0.))
    return dict(p_native_m=p,progress_target_m=target,progress_enabled=target>0,
                progress_normalization_m=.25,graph_variant='v6.1')


class GraphV61(GraphV6):
    def __init__(self,xy,boundary,previous_command,config,protocol,field,previous_xy=None):
        self.progress=progress_metadata(xy,boundary)
        assert protocol['progress_target_m']==.25
        super().__init__(xy,boundary,previous_command,config,protocol,field,previous_xy)

    def residual_jacobian(self,x):
        r,j,names,sizes=super().residual_jacobian(x)
        assert names.count('endpoint_progress')==1
        i=names.index('endpoint_progress');start=sum(sizes[:i]);assert sizes[i]==1
        if not self.progress['progress_enabled']:
            keep=np.arange(len(r))!=start
            return r[keep],j[keep],names[:i]+names[i+1:],sizes[:i]+sizes[i+1:]
        # Keep the original 0.25m scale: changing the denominator would reweight
        # this factor. Only its hinge target changes, fixed before optimization.
        r=r.copy();j=j.copy();j[start]=0
        deficit=self.progress['progress_target_m']-(x.reshape(8,3)[-1,:2]-self.boundary[:2])@self.forward
        r[start]=deficit/.25 if deficit.real>0 else 0.*deficit
        if deficit.real>0:j[start,-3:-1]=-self.forward/.25
        return r,j,names,sizes

    def solve(self):
        poses,solver=super().solve()
        solver.update(self.progress)
        return poses,solver
