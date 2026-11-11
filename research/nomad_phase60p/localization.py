"""Existing online selection wrapper; LOC_V2 Filter(SIGN) is used without changes."""
import numpy as np
from nomad_phase43p.localization import Localization as FrozenLocalization
from nomad_phase59p.localization import Localization as PositionLocalization
from nomad_loc_v2.filter import Filter
from .config import load_model,MODEL_SHA256

class TransitionAdapter:
    def __init__(self,owner,node_poses,spacing,model):
        self.owner=owner;self.replay=Filter(np.asarray(node_poses,float)[:,:2],spacing,'SIGN',model)
    def step(self,ids,values,travel_m):
        chosen,detail=self.replay.step(ids,values,self.owner.net_position,self.owner.net_total)
        return chosen,dict(detail,transition_model='SIGN',model_sha256=MODEL_SHA256,odometry_xy_m=self.owner.net_position.tolist())

class Localization(PositionLocalization):
    def __init__(self,node_poses,position_provider=None):
        FrozenLocalization.__init__(self,node_poses)
        self.position_provider=position_provider;self.net_position=None;self.net_total=None
        self.model=load_model();self.filter=TransitionAdapter(self,node_poses,self.spacing,self.model)
    # Inherit Phase59's XY validation/select wrapper, which delegates the exact
    # radius4 window, original emission/subgoal/goal flag to Phase43 select().
