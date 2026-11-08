"""TOPO-H score-only state machine; no pose, oracle, rendering or inference."""
from dataclasses import dataclass
import numpy as np
from nomad_isaac.topomap import candidate_range,select_subgoal


@dataclass
class TopoH:
    H:int=0
    c:int=0

    def query(self,distances,goal_node):
        start,end=candidate_range(self.H,goal_node,radius=4)
        missing=[i for i in range(start,end+1) if i not in distances]
        if missing:raise ValueError('UNMEASURED_WINDOW_NODES:'+','.join(map(str,missing)))
        values=np.array([distances[i] for i in range(start,end+1)],dtype=float)
        raw,_,_=select_subgoal(values,start,close_threshold=3)
        previous_H,previous_c=self.H,self.c
        if raw>=self.H:self.H=raw;self.c=0
        else:
            self.c+=1
            if self.c>=3:self.H=raw;self.c=0
        subgoal=min(self.H+int(distances[self.H]<3),goal_node)
        if self.H>=goal_node-1:subgoal=goal_node
        return dict(previous_H=previous_H,previous_c=previous_c,raw_closest=raw,H=self.H,c=self.c,subgoal=subgoal,
                    candidate_start=start,candidate_end_inclusive=end)


def possible_query(state,distances,goal_node):
    """Conservative offline state envelope for missing window scores.

    Never fill an unlogged score. Each missing candidate may be the argmin;
    known scores preserve their ordering. This over-approximation includes
    every possible exact TOPO-H output and is not an alternative online rule.
    """
    H,c=state;start,end=candidate_range(H,goal_node,radius=4);ids=list(range(start,end+1))
    known=[i for i in ids if i in distances];missing=[i for i in ids if i not in distances]
    if not missing:
        result=TopoH(H,c).query(distances,goal_node)
        return {(result['H'],result['c'],result['subgoal'])},False
    best=min(known,key=lambda i:(distances[i],i)) if known else None
    raw_choices=missing+([best] if best is not None else []);out=set()
    for raw in raw_choices:
        nh,nc=(raw,0) if raw>=H or c+1>=3 else (H,c+1)
        if nh>=goal_node-1:
            out.add((nh,nc,goal_node));continue
        if nh in distances:increments=[int(distances[nh]<3)]
        elif nh==raw:
            # An unmeasured winning score must be <= every measured score.
            increments=[1] if best is not None and distances[best]<3 else [0,1]
        elif raw==best:
            # The retained unmeasured H cannot beat the measured minimum.
            increments=[0] if distances[best]>=3 else [0,1]
        else:increments=[0,1]
        for inc in increments:out.add((nh,nc,min(nh+inc,goal_node)))
    return out,True
