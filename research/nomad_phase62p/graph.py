"""Exactly one new soft factor over the frozen nonnegative-speed U-Graph."""
import numpy as np
from nomad_phase55p.graph import Graph as FrozenGraph,solve_start
GOAL_SIGMA_M=.3

class Graph(FrozenGraph):
    def __init__(self,*args,goal_xy,**kw):
        self.goal_xy=np.asarray(goal_xy,float)
        if self.goal_xy.shape!=(2,) or not np.isfinite(self.goal_xy).all():raise ValueError('Invalid goal node position')
        super().__init__(*args,**kw)
    def values(self,z):
        r=super().values(z)
        if not r.get('_ug_goal_added'):
            delta=r['states'][-1,:2]-self.goal_xy
            cost=float(delta@delta/GOAL_SIGMA_M**2)
            r['costs']['goal']=cost;r['objective']+=cost
            r['gradient']=r['gradient']+2*delta@r['sensitivity'][-1,:2]/GOAL_SIGMA_M**2
            r['_ug_goal_added']=True
        return r
