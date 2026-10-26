"""v4 non-oracle graph plus its unchanged analytic SDF constraint rows."""
import numpy as np
from nomad_phase12.graph_gf import GraphGF, graph_protocol
from nomad_phase5.graph import FlagGraphV4
from nomad_phase0.graph_v4 import norm

class DepthGraph(GraphGF):
    def __init__(self,xy,boundary,previous_command,field,previous_xy=None):
        super().__init__(xy,boundary,previous_command,graph_protocol(),previous_xy)
        self.field=field
        self.flags={**self.flags,'obstacle_sdf':True,'exact_certificate':True}
    def sdf_rows(self,x):
        xy=x.reshape(8,3)[:,:2];delta=np.diff(xy,axis=0);lengths=norm(delta)
        jl=np.zeros((7,24))
        for i in range(7):
            jl[i,3*i:3*i+2]=-delta[i]/lengths[i];jl[i,3*i+3:3*i+5]=delta[i]/lengths[i]
        points=self.sample_matrix@xy;sdf,gradient=self.field.query(points)
        count=self.p['segment_subdivisions']
        certified=sdf-self.field.error_bound-lengths[self.segment_ids]/(2*count)
        j=np.zeros((len(points),24));j[:,0::3]=gradient[:,0,None]*self.sample_matrix;j[:,1::3]=gradient[:,1,None]*self.sample_matrix
        j-=jl[self.segment_ids]/(2*count)
        scale=self.p['safety_constraint_scale_m']
        return (certified-self.p['path_safety_target_m'])/scale,j/scale
    def constraints(self,x):
        g,j,e,je=super().constraints(x);s,sj=self.sdf_rows(x)
        return np.r_[g,s],np.vstack([j,sj]),e,je
    def certificate(self,poses):
        clearance=self.field.exact_clearance(poses[:,:2])
        return dict(depth_site_clearance_m=clearance,oracle_used=False,corridor_halfplanes=False),bool(clearance>=self.p['path_safety_target_m']-1e-8)
    def solve(self):
        poses,r=FlagGraphV4.solve(self)
        slack=self.sdf_rows(poses.ravel())[0]*self.p['safety_constraint_scale_m']
        r.update(certificate_scope='DEPTH_OCCUPIED_SITES_ONLY',minimum_sdf_slack_m=float(slack.min()),sdf_active_within_1mm=bool(slack.min()<.001))
        return poses,r
