"""Existing online window/emission/subgoal code with frozen NET transition adapter."""
import numpy as np
from nomad_phase43p.localization import Localization as FrozenLocalization
from nomad_hmm_replay.filter import Replay

class TransitionAdapter:
    def __init__(self,owner,nodes,spacing):self.owner=owner;self.replay=Replay(nodes,spacing,'NET')
    def step(self,ids,values,travel_m):
        chosen,detail=self.replay.step(ids,values,self.owner.net_position,self.owner.net_total)
        assert abs(detail['odometry_travel_m']-travel_m)<1e-9
        # Frozen select() already publishes this identical telemetry field.
        detail={k:v for k,v in detail.items() if k!='odometry_travel_m'}
        return chosen,dict(detail,transition_model='NET',odometry_xy_m=self.owner.net_position.tolist())

class Localization(FrozenLocalization):
    def __init__(self,node_poses,position_provider=None):
        super().__init__(node_poses)
        self.position_provider=position_provider;self.net_position=None;self.net_total=None
        self.filter=TransitionAdapter(self,self.goal+1,self.spacing)
    def select(self,values,odometry_total_m,odometry_xy=None):
        if odometry_xy is None:
            if self.position_provider is None:raise ValueError('NET requires observation-time odometry XY')
            odometry_xy=self.position_provider()
        self.net_position=np.asarray(odometry_xy,float)[:2].copy();self.net_total=float(odometry_total_m)
        if self.net_position.shape!=(2,) or not np.isfinite(self.net_position).all():raise ValueError('Invalid NET odometry position')
        # This unmodified function still defines window-conditioned values,
        # closest/MAP, official threshold3 subgoal and goal declaration flag.
        return super().select(values,odometry_total_m)
