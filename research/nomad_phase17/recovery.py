"""Depth-only fixed 30-degree recovery; no planner, goal, or oracle inputs."""
import numpy as np

ANGLE=np.pi/6
OMEGA=.3
LIMIT=12


def free_rays(field, pose):
    """Fixed 1cm samples, including the current center; unknown stays free."""
    distance=np.linspace(0.,2.,201)
    rays={}
    for sign,name in ((1,'left'),(-1,'right')):
        yaw=pose[2]+sign*ANGLE
        points=np.asarray(pose[:2])+distance[:,None]*np.array([np.cos(yaw),np.sin(yaw)])
        hit=np.flatnonzero(field.query(points)[0]<=.025)
        rays[name]=float(distance[hit[0]]) if len(hit) else 2.
    return (1 if rays['left']>=rays['right'] else -1),rays


class Recovery:
    def __init__(self):
        self.state='NORMAL';self.streak=0;self.count=0
        self.remaining=0.;self.sign=1;self.awaiting_outcome=False
    def decision(self,mode):
        self.streak=self.streak+1 if mode=='STOP_WAIT' else 0
    def eligible(self,actual_v):
        return self.state=='NORMAL' and self.streak>=2 and abs(actual_v)<.01 and self.count<LIMIT
    def start(self,field,pose):
        self.sign,rays=free_rays(field,pose)
        self.state='RECOVER_ROTATE';self.remaining=ANGLE;self.count+=1
        return rays
    def interval_command(self):
        if self.state!='RECOVER_ROTATE':return 0.,0.
        # Only the last 72Hz interval may be shorter than omega=.3; exact 30deg.
        return 0.,self.sign*min(OMEGA,self.remaining*72)
    def integrated(self,w):
        self.remaining=max(0.,self.remaining-abs(w)/72)
        if self.remaining<=1e-12:
            self.state='WAIT_FRESH';self.streak=0;self.awaiting_outcome=True
            return True
        return False
