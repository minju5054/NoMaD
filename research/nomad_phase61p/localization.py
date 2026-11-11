"""Oracle XY nearest node at the image observation pose; no HMM state or filter."""
import numpy as np
from nomad_isaac.topomap import candidate_range

class Localization:
    def __init__(self,node_poses,position_provider):
        self.nodes=np.asarray(node_poses,float)[:,:2]
        assert len(self.nodes)>0 and np.isfinite(self.nodes).all()
        self.goal=len(self.nodes)-1;self.closest=0;self.position_provider=position_provider;self.pending=None
    def window(self):
        pose=np.asarray(self.position_provider(),float)
        assert pose.shape==(3,) and np.isfinite(pose).all()
        previous=self.closest;distance=np.linalg.norm(self.nodes-pose[:2],axis=1)
        self.closest=int(np.argmin(distance)) # np.argmin gives lowest-index tie.
        start,end=candidate_range(self.closest,self.goal,radius=4)
        self.pending=dict(pose=pose.tolist(),previous=previous,start=start,end=end,distance=float(distance[self.closest]))
        return start,end
    def select(self,values):
        if self.pending is None:raise ValueError('Oracle window must be prepared before encoding')
        q=self.pending;values=np.asarray(values,float);start,end=q['start'],q['end']
        assert values.ndim==1 and len(values)==end-start+1 and np.isfinite(values).all()
        # Exact Phase43/official subgoal expression, with oracle closest input.
        selected=min(self.closest+int(values[self.closest-start]<3),end)
        result=dict(candidate_start=start,candidate_end_inclusive=end,candidate_ids=list(range(start,end+1)),distances=values.tolist(),
            previous_closest_node=q['previous'],closest_node=self.closest,selected_subgoal_id=selected,selected_condition_index=selected-start,
            goal_node=self.goal,topomap_goal_node_reached=self.closest==self.goal,raw_argmin_node=int(start+np.argmin(values)),
            oracle=dict(enabled=True,analysis_only=True,pose_clock='observation_pose',pose=q['pose'],nearest_node=self.closest,
                nearest_node_distance_m=q['distance'],tie_rule='lowest_node_id',HMM_used=False))
        self.pending=None;return result
