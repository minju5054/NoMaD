"""GraphV4 subclass: 24 pose + 8 speed variables, analytic SLSQP derivatives."""
import time
import numpy as np
from scipy.optimize import Bounds, minimize
from nomad_phase0.graph_v4 import GraphV4, SignedDistanceField, menger, norm
from nomad_isaac.handoff_audit import path_safety


class GraphV5(GraphV4):
    def __init__(self, xy, boundary, previous_command, config, protocol, field, previous_xy=None):
        v,w=map(float,previous_command)
        if v<0 or v>protocol['v5']['v_max']+1e-12: raise ValueError('Invalid applied boundary speed')
        self.v0=max(v,.05)
        super().__init__(xy,boundary,[self.v0,w],config,protocol,field,previous_xy)
        self.zero_speed_variant=v==0
        if self.zero_speed_variant:
            # Auxiliary heading, not native NoMaD yaw. Retain the actual B yaw at rest.
            self.initial[0,2]=boundary[2]
            t=boundary[2];c,s=np.cos(t),np.sin(t)
            self.relative[0]=np.r_[np.array([[c,s],[-s,c]])@(self.xy[1]-self.xy[0]),self.initial[1,2]-t]
            lb,ub=self.bounds.lb.copy(),self.bounds.ub.copy()
            lb[2]=t-np.pi;ub[2]=t+np.pi;self.bounds=Bounds(lb,ub)
        self.initial_speeds=np.full(8,self.v0)
        self.initial_vector=np.r_[self.initial.ravel(),self.initial_speeds]
        self.bounds=Bounds(np.r_[self.bounds.lb,np.full(8,.05)],
                           np.r_[self.bounds.ub,np.full(8,protocol['v5']['v_max'])])

    @staticmethod
    def geometry(x):
        xy=x[:24].reshape(8,3)[:,:2];delta=np.diff(xy,axis=0);length=norm(delta)
        jl=np.zeros((7,32),dtype=np.result_type(x,float))
        for i in range(7):
            jl[i,3*i:3*i+2]=-delta[i]/length[i]
            jl[i,3*i+3:3*i+5]=delta[i]/length[i]
        k,jxy=menger(xy);jk=np.zeros((6,32),dtype=np.result_type(x,float))
        jk[:,0:24:3]=jxy[:,:,0];jk[:,1:24:3]=jxy[:,:,1]
        return length,jl,k,jk

    def objective(self,x):
        base,gradient=GraphV4.objective(self,x[:24])
        length,jl,k,jk=self.geometry(x);v=x[24:];q=self.p['v5']
        travel=np.sum(length/v[:-1]);change=np.diff(k)
        value=base+q['time_weight']*travel+q['curvature_change_weight']*(change@change)
        grad=np.r_[gradient,np.zeros(8,dtype=np.result_type(x,float))]
        grad+=q['time_weight']*np.sum(jl/v[:-1,None],axis=0)
        grad[24:31]-=q['time_weight']*length/v[:-1]**2
        grad+=2*q['curvature_change_weight']*change@np.diff(jk,axis=0)
        return value,grad

    def constraints(self,x):
        g,j,e,je=GraphV4.constraints(self,x[:24])
        j=np.pad(j,((0,0),(0,8)));je=np.pad(je,((0,0),(0,8)))
        length,jl,k,jk=self.geometry(x);v=x[24:];q=self.p['v5']
        # Endpoints inherit the nearest defined triple; no invented endpoint yaw/time.
        mapping=np.array([0,0,1,2,3,4,5,5]);kn=k[mapping];jn=jk[mapping]
        product=kn*v;dp=jn*v[:,None];dp[np.arange(8),24+np.arange(8)]+=kn
        dv2=v[1:]**2-v[:-1]**2
        jd=np.zeros((7,32),dtype=np.result_type(x,float))
        for i in range(7):jd[i,24+i]=-2*v[i];jd[i,25+i]=2*v[i+1]
        # Normalize both families by fixed physical scales; all Jacobians explicit.
        scale=q['omega_max'];a=q['a_max']
        extra=np.r_[1-product/scale,1+product/scale,2*a*length-dv2,2*a*length+dv2]
        jextra=np.vstack([-dp/scale,dp/scale,2*a*jl-jd,2*a*jl+jd])
        speed_e=np.zeros((1,32));speed_e[0,24]=1/q['v_max']
        return np.r_[g,extra],np.vstack([j,jextra]),np.r_[e,(v[0]-self.v0)/q['v_max']],np.vstack([je,speed_e])

    def solve(self):
        start=time.perf_counter()
        sol=minimize(lambda x:self.objective(x)[0],self.initial_vector,jac=lambda x:self.objective(x)[1],
            method='SLSQP',bounds=self.bounds,constraints=[
                {'type':'ineq','fun':lambda x:self.constraints(x)[0],'jac':lambda x:self.constraints(x)[1]},
                {'type':'eq','fun':lambda x:self.constraints(x)[2],'jac':lambda x:self.constraints(x)[3]}],
            options={'maxiter':100,'ftol':self.p['solver']['ftol'],'disp':False})
        elapsed=time.perf_counter()-start;poses=sol.x[:24].reshape(8,3);speeds=sol.x[24:]
        g,_,e,_=self.constraints(sol.x);delta=self.weights@poses[:,:2]-self.boundary[:2]
        entry_k=float(2*(delta@self.left)/(delta@delta)) if np.linalg.norm(delta)>1e-12 else None
        exact=path_safety(poses[:,:2],self.config)
        constraints_ok=bool(g.min()>=-self.p['constraint_tolerance'] and np.max(np.abs(e))<=self.p['constraint_tolerance']
            and entry_k is not None and abs(entry_k-self.kappa_before)<=self.p['entry_curvature_tolerance_m_inv'])
        exact_ok=bool(exact['obstacle_clearance_m']>=.025-1e-8 and exact['corridor_clearance_m']>=self.p['corridor_margin_m']-1e-8)
        lengths=np.linalg.norm(np.diff(poses[:,:2],axis=0),axis=1)
        profile={'s_m':np.r_[0.,np.cumsum(lengths)].tolist(),'v_m_s':speeds.tolist(),
                 'semantics':'auxiliary speed versus corrected world path arclength; no native timing'}
        return poses,profile,{'success':bool(sol.success),'status':int(sol.status),'message':str(sol.message),
            'solver_wall_s':elapsed,'solve_and_certificate_wall_s':time.perf_counter()-start,'iterations':int(sol.nit),
            'objective':float(sol.fun),'constraints_satisfied':constraints_ok,'exact_certificate_pass':exact_ok,
            'exact_path_certificate':exact,'feasible':bool(sol.success and constraints_ok and exact_ok),
            'minimum_scaled_inequality':float(g.min()),'maximum_scaled_equality_error':float(np.max(np.abs(e))),
            'entry_curvature_m_inv':entry_k,'previous_curvature_m_inv':self.kappa_before,
            'zero_speed_heading_variant':self.zero_speed_variant,'boundary_speed_m_s':self.v0,
            'travel_time_term_s':float(np.sum(lengths/speeds[:-1])),
            'derivatives':'explicit analytic objective/constraint Jacobians; no finite differences'}
