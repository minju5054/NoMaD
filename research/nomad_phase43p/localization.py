"""HMM window/MAP and official subgoal selection; no robot-truth input."""
import numpy as np
from nomad_phase42l.filter import WindowHMM
from nomad_isaac.topomap import candidate_range


class Localization:
    def __init__(self,node_poses):
        xy=np.asarray(node_poses,float)[:,:2]
        intervals=np.linalg.norm(np.diff(xy,axis=0),axis=1)
        positive=intervals[intervals>1e-12]
        if not len(positive):raise ValueError('No positive Topomap node spacing')
        self.spacing=float(np.median(positive));self.goal=len(xy)-1
        self.filter=WindowHMM(len(xy),self.spacing)
        self.closest=0;self.previous_total=None

    def window(self):return candidate_range(self.closest,self.goal,radius=4)

    def select(self,values,odometry_total_m):
        start,end=self.window();ids=list(range(start,end+1));values=np.asarray(values,float)
        assert len(values)==len(ids)
        total=float(odometry_total_m)
        if not np.isfinite(total) or total<0:raise ValueError('Invalid cumulative odometry')
        if self.previous_total is not None and total<self.previous_total-1e-10:raise ValueError('Odometry moved backward')
        travel=0. if self.previous_total is None else max(0.,total-self.previous_total)
        old=self.closest;self.closest,detail=self.filter.step(ids,values,travel)
        self.previous_total=total
        # Same official threshold and end-of-window clamp; only replace the
        # argmin closest with HMM MAP before applying the subgoal rule.
        selected=min(self.closest+int(values[self.closest-start]<3),end)
        return dict(candidate_start=start,candidate_end_inclusive=end,candidate_ids=ids,
            distances=values.tolist(),previous_closest_node=old,closest_node=self.closest,
            selected_subgoal_id=selected,selected_condition_index=selected-start,goal_node=self.goal,
            topomap_goal_node_reached=self.closest==self.goal,
            raw_argmin_node=int(ids[int(np.argmin(values))]),
            hmm=dict(odometry_total_m=total,odometry_travel_m=travel,node_spacing_m=self.spacing,**detail))
