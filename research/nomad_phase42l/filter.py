"""One fixed, window-conditioned forward HMM; no tuning or truth input."""
import numpy as np


class WindowHMM:
    def __init__(self,nodes,spacing):
        if nodes<1 or not np.isfinite(spacing) or spacing<=0:raise ValueError('Invalid node spacing')
        self.nodes=int(nodes);self.spacing=float(spacing);self.logp=None

    def step(self,ids,distances,travel_m):
        ids=np.asarray(ids,int);d=np.asarray(distances,float)
        if len(ids)==0 or len(ids)!=len(d) or len(set(ids.tolist()))!=len(ids) or not np.isfinite(d).all():raise ValueError('Invalid emission window')
        if np.any(ids<0) or np.any(ids>=self.nodes) or travel_m<0:raise ValueError('Invalid transition')
        # One-node quantization allowance permits adjacent-node relocalization
        # at rest. Beyond that, the support grows only with measured travel.
        width=min(self.nodes-1,max(1,int(np.ceil(travel_m/self.spacing))))
        reset=False
        if self.logp is None:
            predicted=np.full(len(ids),-np.log(self.nodes))
        else:
            predicted=np.full(len(ids),-np.inf)
            for k,j in enumerate(ids):
                origins=np.arange(max(0,j-width),min(self.nodes,j+width+1))
                degrees=np.minimum(self.nodes-1,origins+width)-np.maximum(0,origins-width)+1
                predicted[k]=np.logaddexp.reduce(self.logp[origins]-np.log(degrees))
            if not np.isfinite(predicted).any():
                # The logged raw-policy window can jump outside all reachable
                # states. Explicitly count this reset; never impute distances.
                predicted[:]=-np.log(len(ids));reset=True
        score=predicted-(d-d.min())  # Unit-temperature exp(-NoMaD distance).
        score-=np.logaddexp.reduce(score)
        self.logp=np.full(self.nodes,-np.inf);self.logp[ids]=score
        chosen=min(ids,key=lambda j:(-self.logp[j],int(j)))
        return int(chosen),dict(transition_half_width=int(width),window_reset=reset,
            posterior_max=float(np.exp(self.logp[chosen])),window_nodes=len(ids))
