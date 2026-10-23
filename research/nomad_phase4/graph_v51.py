"""v5.1 numerical initialization/coordinates only; unchanged physical v5 problem."""
import time
import numpy as np
from scipy.optimize import Bounds, minimize
from nomad_isaac.handoff_audit import path_safety
from .graph_v5 import GraphV5, SignedDistanceField


class GraphV51(GraphV5):
    def __init__(self,*args,warm_start=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.scale=np.r_[np.ones(24),np.full(8,self.p['v5']['v_max']-.05)]
        self.offset=np.r_[np.zeros(24),np.full(8,.05)]
        self.warm_start_used=warm_start is not None
        if warm_start is not None:
            poses=np.asarray(warm_start['poses'],dtype=float).copy()
            speeds=np.asarray(warm_start['speed_profile']['v_m_s'],dtype=float).copy()
            if poses.shape!=(8,3) or speeds.shape!=(8,) or not np.isfinite(np.r_[poses.ravel(),speeds]).all():
                raise ValueError('Invalid previous accepted initialization')
            # Numerical guess only: no claim that equal node indices correspond physically.
            poses[:,2]=self.initial[:,2]+(poses[:,2]-self.initial[:,2]+np.pi)%(2*np.pi)-np.pi
            speeds[0]=self.v0
            self.initial_vector=np.clip(np.r_[poses.ravel(),speeds],self.bounds.lb,self.bounds.ub)
        self.normalized_initial=(self.initial_vector-self.offset)/self.scale
        self.normalized_bounds=Bounds((self.bounds.lb-self.offset)/self.scale,(self.bounds.ub-self.offset)/self.scale)

    def physical(self,z):return self.offset+self.scale*z

    def normalized_objective(self,z):
        value,gradient=GraphV5.objective(self,self.physical(z))
        return value,gradient*self.scale

    def normalized_constraints(self,z):
        g,j,e,je=GraphV5.constraints(self,self.physical(z))
        return g,j*self.scale,e,je*self.scale

    def solve(self):
        start=time.perf_counter()
        sol=minimize(lambda z:self.normalized_objective(z)[0],self.normalized_initial,
            jac=lambda z:self.normalized_objective(z)[1],method='SLSQP',bounds=self.normalized_bounds,
            constraints=[{'type':'ineq','fun':lambda z:self.normalized_constraints(z)[0],'jac':lambda z:self.normalized_constraints(z)[1]},
                         {'type':'eq','fun':lambda z:self.normalized_constraints(z)[2],'jac':lambda z:self.normalized_constraints(z)[3]}],
            options={'maxiter':100,'ftol':self.p['solver']['ftol'],'disp':False})
        elapsed=time.perf_counter()-start;x=self.physical(sol.x);poses=x[:24].reshape(8,3);speeds=x[24:]
        g,_,e,_=GraphV5.constraints(self,x);delta=self.weights@poses[:,:2]-self.boundary[:2]
        entry_k=float(2*(delta@self.left)/(delta@delta)) if np.linalg.norm(delta)>1e-12 else None
        exact=path_safety(poses[:,:2],self.config)
        constraints_ok=bool(g.min()>=-self.p['constraint_tolerance'] and np.max(np.abs(e))<=self.p['constraint_tolerance']
            and entry_k is not None and abs(entry_k-self.kappa_before)<=self.p['entry_curvature_tolerance_m_inv'])
        exact_ok=bool(exact['obstacle_clearance_m']>=.025-1e-8 and exact['corridor_clearance_m']>=self.p['corridor_margin_m']-1e-8)
        lengths=np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1)
        profile={'s_m':np.r_[0.,np.cumsum(lengths)].tolist(),'v_m_s':speeds.tolist(),
            'semantics':'auxiliary arclength speed profile; no native timing'}
        return poses,profile,{'success':bool(sol.success),'status':int(sol.status),'message':str(sol.message),
            'solver_wall_s':elapsed,'solve_and_certificate_wall_s':time.perf_counter()-start,'iterations':int(sol.nit),
            'objective':float(sol.fun),'constraints_satisfied':constraints_ok,'exact_certificate_pass':exact_ok,
            'exact_path_certificate':exact,'feasible':bool(sol.success and constraints_ok and exact_ok),
            'minimum_scaled_inequality':float(g.min()),'maximum_scaled_equality_error':float(np.max(np.abs(e))),
            'entry_curvature_m_inv':entry_k,'previous_curvature_m_inv':self.kappa_before,
            'zero_speed_heading_variant':self.zero_speed_variant,'boundary_speed_m_s':self.v0,
            'travel_time_term_s':float(np.sum(lengths/speeds[:-1])),
            'warm_start_used':self.warm_start_used,'speed_coordinates':'u=(v-.05)/(.3-.05) in [0,1]',
            'derivatives':'unchanged physical v5 analytic derivatives times affine variable scales'}
