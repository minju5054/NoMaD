"""Exactly the existing factors/Jacobians, with bounded per-iterate reuse."""
import types
import numpy as np
from .graph import UnifiedGraph,solve_start as original_solve_start

def vectorized_menger(points):
    u=points[1:-1]-points[:-2];v=points[2:]-points[1:-1];w=u+v
    norm=lambda x:np.sqrt(np.sum(x*x,axis=-1)+1e-24)
    lu,lv,lw=norm(u),norm(v),norm(w);cross=u[:,0]*v[:,1]-u[:,1]*v[:,0];den=lu*lv*lw;k=2*cross/den
    gu=2*np.column_stack([v[:,1],-v[:,0]])/den[:,None]-k[:,None]*(u/lu[:,None]**2+w/lw[:,None]**2)
    gv=2*np.column_stack([-u[:,1],u[:,0]])/den[:,None]-k[:,None]*(v/lv[:,None]**2+w/lw[:,None]**2)
    derivative=np.zeros((len(k),len(points),2),dtype=np.result_type(points,float));i=np.arange(len(k))
    derivative[i,i]=-gu;derivative[i,i+1]=gu-gv;derivative[i,i+2]=gv
    return k,derivative

class OptimizedGraph(UnifiedGraph):
    _objective_kernel=types.FunctionType(UnifiedGraph.objective.__code__,dict(UnifiedGraph.objective.__globals__,menger=vectorized_menger))
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.objective_cache=None;self.constraint_cache=None;self.query_cache=None;self.constraint_kernel_calls=0
        self.query_jacobian=np.concatenate([self.jp,(self.jp[:-1]+self.jp[1:])/2])
        self.low=self.field.origin+1e-8;self.high=self.field.origin+(np.array(self.field.values.shape[::-1])-1)*self.field.h-1e-8
        cb=float(self.field.query(self.B[None,:2])[0][0]);self.start_margin=min(.025,max(0.,cb-.005))
    def objective(self,x):
        self.check()
        if self.objective_cache is None or not np.array_equal(x,self.objective_cache[0]):self.objective_cache=(np.array(x,copy=True),self._objective_kernel(x))
        return self.objective_cache[1]
    def constraints(self,x):
        self.check()
        if self.constraint_cache is None or not np.array_equal(x,self.constraint_cache[0]):
            self.constraint_kernel_calls+=1;self.constraint_cache=(np.array(x,copy=True),super().constraints(x))
        return self.constraint_cache[1]
    def queries(self,p):
        self.check()
        if self.query_cache is not None and np.array_equal(p,self.query_cache[0]):return self.query_cache[1]
        q=np.vstack([p,(p[:-1]+p[1:])/2]);world=q@self.R.T+self.B[:2];clipped=np.clip(world,self.low,self.high)
        distance,gradient=self.field.query(clipped);delta=world-clipped;outside=np.linalg.norm(delta,axis=1);mask=outside>0
        distance[mask]=-outside[mask]-self.field.radius;gradient[mask]=-delta[mask]/outside[mask,None]
        jd=np.einsum('qi,qij->qj',gradient@self.R,self.query_jacobian)
        lengths=np.linalg.norm(np.diff(p,axis=0),axis=1);s=np.r_[0.,np.cumsum(lengths)];sq=np.r_[s,(s[:-1]+s[1:])/2]
        margin=np.where(sq<=.3+1e-12,self.start_margin,.025)
        value=(distance,jd,margin);self.query_cache=(p.copy(),value);return value

# Only the graph implementation binding differs; SLSQP options, constraints,
# selection, deadlines and objective formula bytecode remain the same.
solve_start=types.FunctionType(original_solve_start.__code__,dict(original_solve_start.__globals__,UnifiedGraph=OptimizedGraph),argdefs=original_solve_start.__defaults__)
