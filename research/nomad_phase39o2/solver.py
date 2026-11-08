"""Frozen costs/bounds, no slack variables; omit exactly SDF row0."""
import time
import numpy as np
from scipy.optimize import minimize
from nomad_phase0.graph_v4 import norm,menger
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase19r.repair import initialize
from nomad_phase20.repair import RepairGraphR2
from nomad_phase20c.detour import ANGLES
from nomad_phase20c.detour_known import KnownDetourGraph

VARIANTS=('VB','VO','VE')
TOL=1e-7

def arclength_jacobian(graph,x):
    p=graph.points(x);delta=np.diff(p,axis=0);length=norm(delta);n=len(length);jl=np.zeros((n,len(x)))
    for i in range(n):
        if i:jl[i,2*(i-1):2*i]-=delta[i]/length[i]
        jl[i,2*i:2*i+2]+=delta[i]/length[i]
    fractions=np.linspace(0,1,9);starts=np.r_[0.,np.cumsum(length)[:-1]]
    js=np.vstack([np.zeros(len(x)),np.cumsum(jl,axis=0)[:-1]])
    return (starts[:,None]+length[:,None]*fractions).ravel(),(js[:,None,:]+fractions[None,:,None]*jl[:,None,:]).reshape(n*9,len(x))

def escape_certificate(graph,path):
    if graph.cB>=.025:return graph.certificate(path)
    curve=XYPath(path);end=float(curve.s[-1]);s_esc=float((.03-graph.cB)/.5)
    cuts=sorted(set([0.,end]+[s for s in (.3,s_esc) if 0<s<end]))
    base=getattr(graph,'base_field',graph.field);strict=getattr(graph,'strict_field',base);segments=[]
    for lo,hi in zip(cuts,cuts[1:]):
        p=np.vstack([curve.at(lo),curve.points[(curve.s>lo)&(curve.s<hi)],curve.at(hi)])
        field=base if lo<.3 else strict
        threshold=float(graph.cB-.005) if lo<s_esc else .025
        exact=float(field.exact_clearance(p))
        segments.append(dict(s_a=lo,s_b=hi,threshold_m=threshold,exact_clearance_m=exact,strict_field=lo>=.3))
    if abs(end-s_esc)<=1e-12:
        field=base if end<.3 else strict;point=curve.at(end)
        segments.append(dict(s_a=end,s_b=end,threshold_m=.025,exact_clearance_m=float(field.exact_clearance(np.array([point,point]))),strict_field=end>=.3))
    return dict(certificate_pass=all(x['exact_clearance_m']>=x['threshold_m'] for x in segments),
        depth_clearance_m=min(x['exact_clearance_m'] for x in segments),s_escape_m=s_esc,certificate_segments=segments,escape_certificate=True)

class ModifiedGraph:
    def __init__(self,graph,variant):
        assert variant in VARIANTS,'V0 solving is forbidden'
        self.graph=graph;self.variant=variant;self.escape=bool(variant=='VE' and graph.cB<.025)
        self.m=(len(graph.points(graph.initial))-1)*9
    def full_constraints(self,x):
        g,j=self.graph.constraints(x);g=g.copy();j=j.copy()
        if self.escape:
            s,js=arclength_jacobian(self.graph,x);old=np.where(s<=.3,self.graph.near_threshold,.025)
            new=np.minimum(.025,self.graph.cB-.005+.5*s)
            g[:self.m]+=old-new
            active=self.graph.cB-.005+.5*s<.025;j[:self.m]-=.5*active[:,None]*js
        return g,j
    def constraints(self,x):
        g,j=self.full_constraints(x);return g[1:],j[1:]
    def certificate(self,p):return escape_certificate(self.graph,p) if self.escape else self.graph.certificate(p)
    def solve(self):
        graph=self.graph;start=time.perf_counter()
        if graph.cB<0 and not self.escape:return dict(accepted=False,disposition='NEGATIVE_DEPTH_AT_B',path=None,cB=graph.cB,solver_started=False)
        result=minimize(lambda x:graph.objective(x)[0],graph.initial,jac=lambda x:graph.objective(x)[1],method='SLSQP',bounds=graph.bounds,
            constraints=[dict(type='ineq',fun=lambda x:self.constraints(x)[0],jac=lambda x:self.constraints(x)[1])],options=dict(maxiter=100,ftol=1e-8,disp=False))
        solver_s=time.perf_counter()-start;p=graph.points(result.x);g,_=self.constraints(result.x);full,_=self.full_constraints(result.x)
        violation=max(0.,float(-g.min()),float(np.max(graph.bounds.lb-result.x)),float(np.max(result.x-graph.bounds.ub)))
        try:cert=self.certificate(p)
        except (ValueError,FloatingPointError) as exc:
            cert=dict(certificate_pass=False,depth_clearance_m=None,certificate_error=str(exc))
        r3=hasattr(graph,'u');progress=float((p[-1]-graph.B[:2])@graph.u) if r3 else None
        accepted=bool(result.success and violation<=TOL and cert['certificate_pass'] and (not r3 or progress>=.5))
        disposition='ACCEPTED' if accepted else 'NONCONVERGED' if not result.success else 'CONSTRAINT_FAILED' if violation>TOL else 'CERTIFICATE_REJECTED' if not cert['certificate_pass'] else 'INSUFFICIENT_PROGRESS'
        return dict(accepted=accepted,disposition=disposition,path=p.tolist(),solver_started=True,solver_success=bool(result.success),solver_status=int(result.status),
            message=str(result.message),iterations=int(result.nit),objective=float(result.fun),constraint_violation=violation,
            removed_B_sdf_value_m=float(full[0]),kept_sdf_min_m=float(g[:self.m-1].min()),cB=float(graph.cB),escape_schedule=self.escape,
            progress_m=progress,length_m=float(norm(np.diff(p,axis=0)).sum()),maximum_abs_curvature_m_inv=float(np.abs(menger(p)[0]).max()),
            variables=len(result.x),slack_variables=0,solver_wall_s=solver_s,**cert,attempt_wall_s=time.perf_counter()-start)

def solve(kind,index,job,base,strict):
    variant=job['variant'];assert variant in VARIANTS,'V0 solving is forbidden';start=time.perf_counter()
    cB=float(base.query(np.asarray(job['B'])[None,:2])[0][0])-base.error_bound
    source=f'SAMPLE_{index}' if kind=='R2' else f'FAN_{ANGLES[index]}' if index<7 else job['extra_initializations'][index-7]['source']
    if cB<0 and variant!='VE':return dict(accepted=False,disposition='NEGATIVE_DEPTH_AT_B',path=None,solver_started=False,cB=cB,initialization_source=source,total_attempt_s=time.perf_counter()-start)
    if kind=='R2':
        q,init=initialize(job['samples_world'][index],job['B'])
        if q is None:return dict(init,accepted=False,path=None,solver_started=False,cB=cB,initialization_source=source,total_attempt_s=time.perf_counter()-start)
        graph=RepairGraphR2(q,job['B'],base)
    else:
        graph=KnownDetourGraph(job['B'],job['u_ref'],base,strict,ANGLES[index] if index<7 else 0)
        if index>=7:
            graph.initial_path=np.asarray(job['extra_initializations'][index-7]['path']);graph.initial=graph.initial_path[1:].ravel().copy()
    try:
        r=ModifiedGraph(graph,variant).solve()
        if kind=='R2' and r.get('path') is not None:
            edits=norm(np.asarray(r['path'])-q);r.update(reference=q.tolist(),mean_edit_m=float(edits.mean()),max_edit_m=float(edits.max()))
        if kind=='R3':r['initial_path']=graph.initial_path.tolist()
        return dict(r,initialization_source=source,total_attempt_s=time.perf_counter()-start)
    except ValueError as exc:return dict(accepted=False,disposition='SDF_OR_NUMERICAL_ERROR',path=None,solver_started=True,error=str(exc),cB=cB,initialization_source=source,total_attempt_s=time.perf_counter()-start)
