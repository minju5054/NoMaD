"""Five-second continuous progress graph, exact and one noisy-odometry arm."""
import time
import numpy as np
from scipy.optimize import minimize,Bounds,LinearConstraint
from scipy.special import logsumexp

LAG_S=5.
REVERSE_ALLOWANCE_M=.05
NOISE_FRACTION=.02


def visual_cost(s,observations,kernel_sigma):
    """Available-node likelihood mixture, Cauchy on sqrt(2 negative log L).

    log L = log sum_j softmax(-d_j) exp(-(s-node_s_j)^2/(2 sigma²)).
    No missing-node network scores are invented. Kernel tails are a stated
    continuous-position model, not measured out-of-window distances.
    """
    cost=0.;gradient=np.zeros(len(s));variance=kernel_sigma**2
    for i,(x,obs) in enumerate(zip(s,observations)):
        d=np.asarray(obs['distances'],float);centers=np.asarray(obs['node_s'],float)
        weights=-d-logsumexp(-d);terms=weights-.5*(x-centers)**2/variance
        normalizer=logsumexp(terms);energy=max(0.,float(-normalizer))
        probabilities=np.exp(terms-normalizer)
        derivative=float(probabilities@(x-centers))/variance
        cost+=np.log1p(2*energy);gradient[i]=2*derivative/(1+2*energy)
    return float(cost),gradient


class Problem:
    def __init__(self,observations,spacing,total,noisy=False):
        self.obs=observations;self.spacing=float(spacing);self.total=float(total);self.noisy=noisy
        n=len(observations);self.offset=np.zeros(n);columns=[np.full(n,spacing)];lower=[0.];upper=[total/spacing];self.parameters=[]
        for i in range(1,n):
            edge=observations[i]['edge'];bound=edge['travel_m'];delta=edge['projected_delta_m']
            if edge['off_path']:
                sigma=NOISE_FRACTION*bound if noisy else 0.
                limit=max(0.,bound+sigma*edge['noise_z']) if noisy else bound
                if bound>0:
                    col=np.zeros(n);col[i:]=spacing;columns.append(col)
                    lower.append(-np.inf if noisy else -bound/spacing);upper.append(np.inf if noisy else bound/spacing)
                    self.parameters.append(dict(index=len(columns)-1,edge_index=i,kind='BOUND',scale=spacing,sigma=sigma,limit=limit))
                continue
            sigma=NOISE_FRACTION*abs(delta) if noisy else 0.
            measured=delta+sigma*edge['noise_z'];self.offset[i:]+=measured
            if sigma>0:
                col=np.zeros(n);col[i:]=sigma;columns.append(col);lower.append(-np.inf);upper.append(np.inf)
                self.parameters.append(dict(index=len(columns)-1,edge_index=i,kind='GAUSSIAN',scale=sigma,sigma=sigma,mean=measured))
        self.M=np.column_stack(columns);self.bounds=Bounds(lower,upper)
        self.constraint=LinearConstraint(self.M,-self.offset,self.total-self.offset)
        self.kernel_sigma=spacing/np.sqrt(12.)

    def states(self,z):return self.offset+self.M@z

    def objective(self,z):
        s=self.states(z);value,gs=visual_cost(s,self.obs,self.kernel_sigma);grad=self.M.T@gs
        for p in self.parameters:
            j=p['index']
            if p['kind']=='GAUSSIAN':value+=z[j]**2;grad[j]+=2*z[j]
            elif self.noisy and p['sigma']>0:
                d=p['scale']*z[j];excess=max(0.,abs(d)-p['limit'])
                value+=(excess/p['sigma'])**2
                if excess:grad[j]+=2*excess/p['sigma']**2*np.sign(d)*p['scale']
        for i,d in enumerate(np.diff(s),1):
            excess=max(0.,-d-REVERSE_ALLOWANCE_M)
            value+=(excess/self.spacing)**2
            if excess:grad+=(-2*excess/self.spacing**2)*(self.M[i]-self.M[i-1])
        return float(value),grad

    def initializations(self,previous):
        n=self.M.shape[1];candidates=[]
        desired=np.array([previous.get(o['id'],np.nan) for o in self.obs])
        if np.isfinite(desired[:-1]).all() and len(desired)>1:
            edge=self.obs[-1]['edge'];d=0. if edge['off_path'] else edge['projected_delta_m']
            if self.noisy and not edge['off_path']:d+=NOISE_FRACTION*abs(d)*edge['noise_z']
            desired[-1]=desired[-2]+d
            z=np.zeros(n);z[0]=desired[0]/self.spacing
            for p in self.parameters:
                diff=desired[p['edge_index']]-desired[p['edge_index']-1]
                z[p['index']]=(diff-p.get('mean',0.))/p['scale']
            candidates.append(np.clip(z,self.bounds.lb,self.bounds.ub))
        lo=max(0.,-float(self.offset.min()));hi=min(self.total,float(self.total-self.offset.max()))
        for target in self.obs[-1]['node_s']:
            z=np.zeros(n);anchor=float(target)-self.offset[-1]
            z[0]=np.clip(anchor,lo,hi)/self.spacing if lo<=hi else np.clip(anchor,0,self.total)/self.spacing
            candidates.append(z)
        unique=[];seen=set()
        for z in candidates:
            key=tuple(np.round(z,12))
            if key not in seen:seen.add(key);unique.append(z)
        return unique

    def violation(self,z):
        s=self.states(z)
        return max(0.,float(-s.min()),float(s.max()-self.total),float(np.max(self.bounds.lb-z)),float(np.max(z-self.bounds.ub)))


class FixedLag:
    def __init__(self,node_s,spacing,noisy=False):
        self.node_s=np.asarray(node_s,float);self.total=float(self.node_s[-1]);self.spacing=float(spacing);self.noisy=noisy
        self.window=[];self.previous={}

    def step(self,observation):
        begin=time.perf_counter();cut=observation['time_s']-LAG_S
        self.window=[x for x in self.window if x['time_s']>=cut-1e-12]+[observation]
        problem=Problem(self.window,self.spacing,self.total,self.noisy);best=None;attempts=[]
        for z in problem.initializations(self.previous):
            result=minimize(lambda x:problem.objective(x)[0],z,jac=lambda x:problem.objective(x)[1],method='SLSQP',
                bounds=problem.bounds,constraints=[problem.constraint],options=dict(maxiter=100,ftol=1e-8,disp=False))
            violation=problem.violation(result.x)
            accepted=bool(result.success and np.isfinite(result.fun) and violation<=1e-7)
            attempts.append(dict(status=int(result.status),message=str(result.message),iterations=int(result.nit),accepted=accepted,violation_m=violation))
            if accepted and (best is None or result.fun<best.fun):best=result
        detail=dict(solve_s=time.perf_counter()-begin,window_n=len(self.window),starts=len(attempts),attempts=attempts,
                    lag_s=LAG_S,noisy=self.noisy,success=best is not None)
        if best is None:return None,dict(detail,reason='NO_CONVERGED_FEASIBLE_SOLUTION')
        states=problem.states(best.x);self.previous={o['id']:float(s) for o,s in zip(self.window,states)}
        latest=float(states[-1]);node=int(np.argmin(np.abs(self.node_s-latest)))
        hard_errors=[];bound_excess=[]
        for i,o in enumerate(self.window[1:],1):
            edge=o['edge'];ds=float(states[i]-states[i-1])
            if edge['off_path']:bound_excess.append(max(0.,abs(ds)-edge['travel_m']))
            elif not self.noisy or edge['projected_delta_m']==0:hard_errors.append(abs(ds-edge['projected_delta_m']))
        return node,dict(detail,s_m=latest,objective=float(best.fun),max_hard_equality_error_m=max(hard_errors,default=0.),
            max_original_travel_bound_excess_m=max(bound_excess,default=0.),states_m=states.tolist())
