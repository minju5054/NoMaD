"""Phase35's Phase20 R2 numerical solver plus exactly one old-path factor."""
from types import FunctionType
import numpy as np
from nomad_phase20 import repair as frozen
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase15.evaluate import suffix

class ReconstructionGraph(frozen.RepairGraphR2):
    def __init__(self,q,B,field,old_path):
        super().__init__(q,B,field);self.old_targets=np.zeros((8,2));self.old_weights=np.zeros(8);self.old_remaining=0.
        if old_path is not None:
            tail,remaining=suffix(np.asarray(old_path,float),B);self.old_remaining=float(remaining)
            if remaining>1e-10:
                old=XYPath(tail);s=np.r_[0.,np.cumsum(self.lengths)];eligible=s<=min(.5,remaining)+1e-12
                self.old_weights=np.where(eligible,np.maximum(0.,1-s/.5),0.)
                self.old_targets=np.array([old.at(t) for t in s])
        self.old_jac=np.zeros((16,14));self.old_jac[2:]=np.diag(np.repeat(np.sqrt(self.old_weights[1:]),2))
    def residual_jacobian(self,x):
        residual,jac=super().residual_jacobian(x)
        extra=((self.points(x)-self.old_targets)*np.sqrt(self.old_weights)[:,None]).ravel()
        return np.r_[residual,extra],np.vstack([jac,self.old_jac])
    def solve(self):
        path,result=super().solve()
        extra=(path-self.old_targets)*np.sqrt(self.old_weights)[:,None]
        result['factor_costs']['previous_path']=.5*float(np.sum(extra**2))
        result.update(old_remaining_m=self.old_remaining,old_factor_weights=self.old_weights.tolist(),old_factor_targets=self.old_targets.tolist())
        return path,result

def solve_sample(native,B,field,old_path):
    fn=frozen.solve_sample
    factory=lambda q,b,f:ReconstructionGraph(q,b,f,old_path)
    return FunctionType(fn.__code__,dict(fn.__globals__,RepairGraphR2=factory),fn.__name__,fn.__defaults__,fn.__closure__)(native,B,field)

def select(results,allowed=None):
    indices=[i for i,r in enumerate(results) if r.get('accepted') and (allowed is None or i in allowed)]
    return min(indices,key=lambda i:(results[i]['objective'],i)) if indices else None
