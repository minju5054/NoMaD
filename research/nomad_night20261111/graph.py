"""Phase54: remove ONLY boundary curvature equality under registered condition."""
import inspect,textwrap
import numpy as np
from nomad_phase12.graph_gf import GraphGF,graph_protocol
from nomad_phase17.graph import ClearanceGraph

source=textwrap.dedent(inspect.getsource(GraphGF.__init__))
old='''    if previous_command[0] <= 0:
        raise ValueError("Previous speed is zero: boundary curvature undefined")
    self.kappa_before = previous_command[1]/previous_command[0]
    if abs(self.kappa_before) > protocol["curvature_limit_m_inv"]:
        raise ValueError("Previous curvature exceeds the fixed path limit")'''
new='''    self.kappa_before = previous_command[1]/previous_command[0] if previous_command[0] != 0 else 0.'''
assert source.count(old)==1
scope=dict(GraphGF.__init__.__globals__);exec(compile(source.replace(old,new),__file__,'exec'),scope)
init_without_boundary_guard=scope['__init__']

def drop_boundary(command):
    v,w=map(float,command)
    return abs(v)<.02 or abs(w/v)>8.

class HoldClearanceGraph(ClearanceGraph):
    def __init__(self,xy,boundary,previous_command,field,previous_xy=None):
        self.boundary_dropped=drop_boundary(previous_command);self.actual_previous_command=list(map(float,previous_command))
        if not self.boundary_dropped:super().__init__(xy,boundary,previous_command,field,previous_xy)
        else:
            init_without_boundary_guard(self,xy,boundary,previous_command,graph_protocol(),previous_xy)
            self.field=field;self.flags={**self.flags,'obstacle_sdf':True,'exact_certificate':True,'boundary_curvature':False}
    def constraints(self,x):
        g,j,e,je=super().constraints(x)
        if self.boundary_dropped:e=np.empty(0,dtype=x.dtype);je=np.empty((0,len(x)),dtype=x.dtype)
        return g,j,e,je
    def solve(self):
        poses,result=super().solve()
        result.update(boundary_curvature_dropped=self.boundary_dropped,actual_previous_command=self.actual_previous_command)
        return poses,result
