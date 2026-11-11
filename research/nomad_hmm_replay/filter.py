"""Fixed Phase42-L forward emissions/transitions, plus approved NET/MEM deltas."""
import numpy as np
from nomad_phase42l.filter import WindowHMM

VARIANTS=('HMM0','NET','NET+MEM')

def predict(logp,n,width):
    predicted=np.full(n,-np.inf)
    if logp is None:return np.full(n,-np.log(n))
    for j in range(n):
        origins=np.arange(max(0,j-width),min(n,j+width+1))
        degrees=np.minimum(n-1,origins+width)-np.maximum(0,origins-width)+1
        predicted[j]=np.logaddexp.reduce(logp[origins]-np.log(degrees))
    return predicted

class Replay:
    def __init__(self,nodes,spacing,variant):
        assert variant in VARIANTS
        self.filter=WindowHMM(nodes,spacing);self.variant=variant
        self.current=None;self.entry_position=None;self.visits={};self.previous_total=None
    def step(self,ids,distances,position,odometry_total):
        ids=np.asarray(ids,int);d=np.asarray(distances,float);position=np.asarray(position,float)[:2]
        n=self.filter.nodes;spacing=self.filter.spacing;total=float(odometry_total)
        if position.shape!=(2,) or not np.isfinite(position).all() or not np.isfinite(total) or total<0:raise ValueError('Invalid odometry')
        if self.previous_total is not None and total<self.previous_total-1e-10:raise ValueError('Cumulative odometry decreased')
        if not len(ids) or len(ids)!=len(d) or len(set(ids.tolist()))!=len(ids) or not np.isfinite(d).all() or np.any(ids<0) or np.any(ids>=n):raise ValueError('Invalid emission window')
        travel=0. if self.previous_total is None else max(0.,total-self.previous_total)
        net=0. if self.entry_position is None else float(np.linalg.norm(position-self.entry_position))
        width=min(n-1,max(1,int(np.ceil(travel/spacing)))) if self.variant=='HMM0' else min(n-1,int(round(net/spacing)))
        old=self.current;old_entry=None if self.entry_position is None else self.entry_position.copy()
        predicted=predict(self.filter.logp,n,width)
        predicted_map=int(np.argmax(predicted)) if self.filter.logp is not None else None
        previous_outside=old is not None and old not in ids
        predicted_outside=predicted_map is not None and predicted_map not in ids
        memory=np.zeros(len(ids));reset=False
        if self.variant=='HMM0':
            # Use the frozen function itself; no rewritten HMM0 numerical path.
            chosen,detail=self.filter.step(ids,d,travel)
        else:
            prior=predicted[ids].copy()
            if not np.isfinite(prior).any():prior[:]=-np.log(len(ids));reset=True
            if self.variant=='NET+MEM':
                for k,j in enumerate(ids):
                    if int(j) in self.visits:
                        delta=position-self.visits[int(j)];memory[k]=-float(delta@delta)/(2*spacing**2)
            score=prior-(d-d.min())+memory
            score-=np.logaddexp.reduce(score)
            self.filter.logp=np.full(n,-np.inf);self.filter.logp[ids]=score
            chosen=int(min(ids,key=lambda j:(-self.filter.logp[j],int(j))))
            detail=dict(transition_half_width=width,window_reset=reset,posterior_max=float(np.exp(self.filter.logp[chosen])),window_nodes=len(ids))
        # Entry anchor resets at EVERY MAP change; visits never overwrite p_j.
        changed=self.current is None or chosen!=self.current
        if changed:self.entry_position=position.copy()
        first_visit=chosen not in self.visits
        if first_visit:self.visits[chosen]=position.copy()
        self.current=chosen;self.previous_total=total
        return chosen,dict(detail,entry_displacement_m=net,odometry_travel_m=travel,map_changed=changed,first_visit=first_visit,
            previous_map=old,entry_position_before=None if old_entry is None else old_entry.tolist(),entry_position_after=self.entry_position.tolist(),
            first_visit_position=self.visits[chosen].tolist(),ell_m=spacing,memory_log_factors=memory.tolist(),
            previous_map_outside_window=bool(previous_outside),predicted_map_outside_window=bool(predicted_outside),
            predicted_map_before_window=predicted_map,posterior_map_outside_window=chosen not in ids)
