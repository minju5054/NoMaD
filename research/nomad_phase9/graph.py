"""v4 subclass: public dynamic SDF plus fixed intent XY/side factors only."""
import numpy as np
from nomad_phase5.graph import FlagGraphV4
from nomad_phase2.config import native_safety

class FreeField:
    error_bound=0.;build_wall_s=0.
    def query(self,points):return np.full(len(points),1e6,dtype=points.dtype),np.zeros_like(points)

class GraphV6(FlagGraphV4):
    def __init__(self,xy,boundary,previous_command,config,protocol,field,previous_xy=None):
        p={**protocol,'phase5_flags':{'previous_prior':True,'obstacle_sdf':True,'boundary_curvature':True}}
        super().__init__(xy,boundary,previous_command,config,p,field,previous_xy)
        self.intent=config.get('public_intent');self.intent_node=None
        if self.intent:
            v=np.array(self.intent['V']);self.intent_node=int(np.argmin(np.sum((self.xy-v)**2,axis=1)))
            box=next(b for b in config['obstacles'] if b['id']=='DynamicObstacle')
            x,y=box['center_xy_m'];crossings=[]
            for i,(a,b) in enumerate(zip(self.xy[:-1],self.xy[1:])):
                if abs(b[0]-a[0])>1e-12 and min(a[0],b[0])<=x<=max(a[0],b[0]):crossings.append(dict(a=i,b=i+1,fraction=float((x-a[0])/(b[0]-a[0]))))
            if not crossings:
                i=int(np.argmin(abs(self.xy[:,0]-x)));crossings=[dict(a=min(i,6),b=min(i,6)+1,fraction=1. if i==7 else 0.)]
            self.sides['DynamicObstacle']={'sign':self.intent['side'],'center_y_m':y,'minimum_offset_m':box['size_xyz_m'][1]/2+config['agent_radius_m'],'crossings':crossings}
    def residual_jacobian(self,x):
        r,j,names,sizes=super().residual_jacobian(x)
        if self.intent_node is None:return r,j,names,sizes
        i=self.intent_node;extra=(x.reshape(8,3)[i,:2]-np.array(self.intent['V']))/.05
        dj=np.zeros((2,24),dtype=x.dtype);dj[:,3*i:3*i+2]=np.eye(2)/.05
        return np.r_[r,extra],np.vstack([j,dj]),names+['heuristic_intent_xy'],sizes+[2]
    def certificate(self,poses):
        s=native_safety(poses[:,:2],self.config)
        gap=s['minimum_clearance_m']
        exact={'obstacle_clearance_m':gap,'obstacles':s['obstacles'],'corridor_clearance_m':s['corridor_clearance_m'],'safe':s['safe']}
        return exact,bool((gap is None or gap>=self.p['path_safety_target_m']-1e-8) and s['corridor_clearance_m']>=self.p['corridor_margin_m']-1e-8)
