"""Once per segment: brake, rotate to its chord within10deg, then PP."""
import numpy as np
from nomad_phase23.rollout import GraphFollower,angle_delta
from nomad_phase24.live import ControlState as PreviousClock

class ChordFollower(GraphFollower):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.aligned=set();self.alignment=None;self.first_pending=True
    def priority(self,pose,previous_v):
        a=self.alignment;error=angle_delta(a['target_heading']-pose[2]);info=dict(rotation_priority=True,segment=a['segment'],target_heading=a['target_heading'],
            theta_chord_error_deg=a['theta_chord_error_deg'],theta_start_chord_error_deg=a['theta_start_chord_error_deg'],THETA_CHORD_INCONSISTENT=a['theta_chord_error_deg']>90.,heading_error_deg=float(abs(error)*180/np.pi))
        if previous_v>1e-12:return (max(0.,previous_v-.5/9),0.),dict(mode='GRAPH_ROTATION_BRAKE',**info)
        if abs(error)<=np.deg2rad(10)+1e-12:
            self.aligned.add(a['segment']);self.alignment=None;return None
        omega=float(np.sign(error)*min(.4,max(0.,abs(error)-np.deg2rad(10))*9))
        return (0.,omega),dict(mode='GRAPH_ROTATION',**info)
    def control(self,pose,previous_v):
        if self.alignment is not None:
            result=self.priority(pose,previous_v)
            if result is not None:return result
        # Keep the registered graph's zero-speed rotation segments. A chord
        # alignment is checked immediately before the PP command is released.
        command,diag=super().control(pose,previous_v)
        if diag['mode']!='PP_GRAPH_SPEED':return command,diag
        current=min(9,int(np.searchsorted(self.s,self.progress,side='right')-1));indices=list(dict.fromkeys(([0] if self.first_pending else [])+[current]));self.first_pending=False
        for i in indices:
            if i in self.aligned:continue
            delta=self.q[i+1,:2]-self.q[i,:2]
            if np.linalg.norm(delta)>1e-10:
                chord=float(np.arctan2(delta[1],delta[0]));error=abs(angle_delta(chord-pose[2]))
                if error>np.deg2rad(30):
                    self.alignment=dict(segment=i,target_heading=chord,theta_chord_error_deg=float(abs(angle_delta(self.q[i+1,2]-chord))*180/np.pi),theta_start_chord_error_deg=float(abs(angle_delta(self.q[i,2]-chord))*180/np.pi))
                    return self.priority(pose,previous_v)
        return command,diag

class ControlState(PreviousClock):
    def install(self,result,tick):
        self.plan=result;self.applied_tick=tick;self.ended=False
        self.controller=ChordFollower(result['poses'],result['dt']) if result.get('accepted') else None
