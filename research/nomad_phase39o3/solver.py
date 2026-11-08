"""Frozen VE numerical formulation with explicit hard/certificate map override."""
import time
from types import SimpleNamespace,MethodType
import numpy as np
from nomad_phase39o2.solver import ModifiedGraph,escape_certificate
from nomad_phase20c.detour import ANGLES
from nomad_phase20c.detour_known import KnownDetourGraph
from .maps import VARIANTS,EverywhereField

def map_certificate(graph,path,planning,variant):
    proxy=SimpleNamespace(cB=graph.cB,near_threshold=graph.near_threshold,field=planning,base_field=planning,strict_field=planning)
    proxy.certificate=MethodType(KnownDetourGraph.certificate,proxy)
    result=escape_certificate(proxy,path) if graph.cB<.025 else proxy.certificate(path)
    return dict(result,certificate_map=variant,same_map_all_segments=True)

class MapGraph(ModifiedGraph):
    def __init__(self,graph,planning,variant):
        assert variant in VARIANTS,'Cached V0/VE cannot be solved'
        super().__init__(graph,'VE');self.variant=variant;self.planning=planning
    def full_constraints(self,x):
        g,j=super().full_constraints(x);q=self.graph.M@self.graph.points(x)
        old,og=self.graph.field.query(q);new,ng=self.planning.query(q)
        g[:self.m]+=new-old;delta=ng-og
        j[:self.m,0::2]+=delta[:,0,None]*self.graph.M[:,1:]
        j[:self.m,1::2]+=delta[:,1,None]*self.graph.M[:,1:]
        return g,j
    def certificate(self,path):return map_certificate(self.graph,path,self.planning,self.variant)

def solve(index,job,base,cost,planning):
    assert job['variant'] in VARIANTS and job['kind']=='R3','V0/VE/R2 are read-only references'
    start=time.perf_counter();graph=KnownDetourGraph(job['B'],job['u_ref'],base,cost,ANGLES[index] if index<7 else 0)
    if job['soft_policy_map']:graph.field=EverywhereField(planning)
    source=f'FAN_{ANGLES[index]}' if index<7 else job['extra_initializations'][index-7]['source']
    if index>=7:
        graph.initial_path=np.asarray(job['extra_initializations'][index-7]['path']);graph.initial=graph.initial_path[1:].ravel().copy()
    try:
        r=MapGraph(graph,planning,job['variant']).solve()
        return dict(r,initial_path=graph.initial_path.tolist(),initialization_source=source,map_variant=job['variant'],
            soft_map='POLICY_ALL_SEGMENTS' if job['soft_policy_map'] else 'FROZEN_VE_PIECEWISE',cB_source='ORIGINAL_BASE',total_attempt_s=time.perf_counter()-start)
    except ValueError as exc:return dict(accepted=False,disposition='SDF_OR_NUMERICAL_ERROR',path=None,solver_started=True,error=str(exc),initialization_source=source,total_attempt_s=time.perf_counter()-start)
