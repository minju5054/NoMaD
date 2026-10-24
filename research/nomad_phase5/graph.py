"""Selective v4 factors/constraints. Original implementation and weights untouched."""
import time
import numpy as np
from scipy.optimize import minimize
from nomad_phase0.graph_v4 import GraphV4, menger, selection_score
from nomad_isaac.handoff_audit import path_safety


class InactiveField:
    """Discarded SDF rows must not impose even a field-domain restriction."""
    error_bound=0.
    def query(self,points):
        return np.zeros(len(points),dtype=points.dtype),np.zeros_like(points)


class FlagGraphV4(GraphV4):
    def __init__(self,xy,boundary,previous_command,config,protocol,field,previous_xy=None):
        self.flags=protocol['phase5_flags']
        super().__init__(xy,boundary,previous_command,config,protocol,field if self.flags['obstacle_sdf'] else InactiveField(),
                         previous_xy if self.flags['previous_prior'] else None)

    def constraints(self,x):
        g,j,e,je=super().constraints(x)
        if not self.flags['obstacle_sdf']:
            start=7+1+len(self.chords)+12;end=start+len(self.sample_matrix)
            keep=np.r_[np.arange(start),np.arange(end,len(g))]
            g,j=g[keep],j[keep]
        if not self.flags['boundary_curvature']:
            e=np.empty(0,dtype=x.dtype);je=np.empty((0,len(x)),dtype=x.dtype)
        return g,j,e,je

    def certificate(self,poses):
        exact=path_safety(poses[:,:2],self.config)
        corridor=exact['corridor_clearance_m']>=self.p['corridor_margin_m']-1e-8
        obstacle=exact['obstacle_clearance_m']>=self.p['path_safety_target_m']-1e-8
        return exact,bool(corridor and (obstacle or not self.flags['obstacle_sdf']))

    def solve(self):
        start=time.perf_counter()
        constraints=[{'type':'ineq','fun':lambda x:self.constraints(x)[0],'jac':lambda x:self.constraints(x)[1]}]
        if self.flags['boundary_curvature']:
            constraints.append({'type':'eq','fun':lambda x:self.constraints(x)[2],'jac':lambda x:self.constraints(x)[3]})
        solution=minimize(lambda x:self.objective(x)[0],self.initial.ravel(),jac=lambda x:self.objective(x)[1],
            method='SLSQP',bounds=self.bounds,constraints=constraints,
            options={'maxiter':self.p['solver']['maxiter'],'ftol':self.p['solver']['ftol'],'disp':False})
        wall=time.perf_counter()-start;poses=solution.x.reshape(8,3);g,_,eq,_=self.constraints(solution.x)
        d=self.weights@poses[:,:2]-self.boundary[:2]
        k=float(2*(d@self.left)/(d@d)) if np.linalg.norm(d)>1e-12 else None
        eq_ok=(not self.flags['boundary_curvature'] or (abs(eq[0])<=self.p['constraint_tolerance'] and k is not None and abs(k-self.kappa_before)<=self.p['entry_curvature_tolerance_m_inv']))
        constraint_ok=bool(g.min()>=-self.p['constraint_tolerance'] and eq_ok)
        exact,exact_ok=self.certificate(poses)
        r,_,names,sizes=self.residual_jacobian(solution.x);costs={};offset=0
        for name,size in zip(names,sizes):
            costs[name]=costs.get(name,0.)+.5*float(r[offset:offset+size]@r[offset:offset+size]);offset+=size
        return poses,dict(success=bool(solution.success),status=int(solution.status),message=str(solution.message),
            solver_wall_s=wall,solve_and_certificate_wall_s=time.perf_counter()-start,iterations=int(solution.nit),
            objective_evaluations=int(solution.nfev),objective_calls=self.objective_calls,constraint_calls=self.constraint_calls,
            objective=float(solution.fun),factor_costs=costs,minimum_scaled_inequality=float(g.min()),
            scaled_equality_error=float(abs(eq[0])) if len(eq) else None,entry_curvature_m_inv=k,
            previous_curvature_m_inv=self.kappa_before,maximum_node_curvature_m_inv=float(np.max(np.abs(menger(poses[:,:2])[0]))),
            constraints_satisfied=constraint_ok,exact_path_certificate=exact,exact_certificate_pass=exact_ok,
            feasible=bool(solution.success and constraint_ok and exact_ok),selection_score=selection_score(poses[:,:2],self.xy,self.boundary,self.p),
            previous_prior_applied=self.previous_target is not None,phase5_flags=self.flags,
            certificate_scope='OBSTACLE_AND_CORRIDOR' if self.flags['obstacle_sdf'] else 'CORRIDOR_ONLY',
            derivatives='unchanged explicit analytic v4 Jacobians; flag-selected rows only')
