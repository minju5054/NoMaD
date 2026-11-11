"""Five fixed variants; shared saved-window masking, no truth input."""
import numpy as np
from nomad_hmm_replay.filter import Replay,predict
from .data import tangents
from .calibration import obs_log_emission
VARIANTS=('HMM0','NET','OBS','SIGN','OBS+SIGN')

def gaussian_transition(n,mean,sigma2):
    """Normal density at integer node offsets, normalized over global nodes."""
    offsets=np.arange(n)[None,:]-np.arange(n)[:,None]
    logt=-.5*(offsets-mean)**2/sigma2
    return logt-np.logaddexp.reduce(logt,axis=1)[:,None]

class Filter:
    def __init__(self,xy,spacing,variant,model):
        assert variant in VARIANTS;self.variant=variant;self.n=len(xy);self.spacing=float(spacing);self.model=model
        self.direction=tangents(xy);self.base=Replay(self.n,spacing,variant) if variant in ('HMM0','NET') else None
        self.logp=None;self.current=None;self.previous_position=None;self.previous_total=None
    def step(self,ids,distances,position,total):
        if self.base is not None:return self.base.step(ids,distances,position,total)
        ids=np.asarray(ids,int);d=np.asarray(distances,float);position=np.asarray(position,float)[:2];total=float(total)
        if not len(ids) or len(ids)!=len(d) or len(set(ids))!=len(ids) or not np.isfinite(d).all() or np.any(ids<0) or np.any(ids>=self.n):raise ValueError('Invalid saved window')
        if not np.isfinite(position).all() or not np.isfinite(total) or total<0:raise ValueError('Invalid odometry')
        if self.previous_total is not None and total<self.previous_total-1e-10:raise ValueError('Odometry decreased')
        travel=0. if self.previous_total is None else max(0.,total-self.previous_total)
        s=0. if self.previous_position is None else float((position-self.previous_position)@self.direction[self.current])
        mu=s/self.spacing;width=None
        if self.logp is None:prior=np.full(self.n,-np.log(self.n))
        elif 'SIGN' in self.variant:
            logt=gaussian_transition(self.n,mu,self.model['sigma2']);prior=np.logaddexp.reduce(self.logp[:,None]+logt,axis=0)
        else:
            width=min(self.n-1,max(1,int(np.ceil(travel/self.spacing))));prior=predict(self.logp,self.n,width)
        if width is None and self.variant=='OBS':width=min(self.n-1,max(1,int(np.ceil(travel/self.spacing))))
        previous_outside=self.current is not None and self.current not in ids
        prediction=int(np.argmax(prior)) if self.logp is not None else None
        window=prior[ids].copy();reset=False
        if not np.isfinite(window).any():window[:]=-np.log(len(ids));reset=True
        emission=obs_log_emission(self.model,ids,d) if 'OBS' in self.variant else -(d-d.min())
        score=window+emission;score-=np.logaddexp.reduce(score)
        self.logp=np.full(self.n,-np.inf);self.logp[ids]=score
        chosen=int(min(ids,key=lambda j:(-self.logp[j],int(j))))
        detail=dict(transition_half_width=width,signed_forward_m=s,transition_mean_nodes=mu,sigma2=self.model['sigma2'] if 'SIGN' in self.variant else None,
            window_reset=reset,previous_map_outside_window=bool(previous_outside),predicted_map_outside_window=prediction is not None and prediction not in ids,
            posterior_map_outside_window=False,posterior_max=float(np.exp(self.logp[chosen])))
        self.current=chosen;self.previous_position=position.copy();self.previous_total=total
        return chosen,detail
