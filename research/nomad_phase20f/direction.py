"""Component-frozen preappearance travel direction and rectangle membership."""
import numpy as np

def component_direction(poses,birth_tick):
    p=np.asarray(poses);end=int(birth_tick);assert 0<=end<len(p)
    start=max(0,end-216);delta=p[end,:2]-p[start,:2];distance=float(np.linalg.norm(delta))
    u=delta/distance if distance>=.3 else np.array([np.cos(p[end,2]),np.sin(p[end,2])])
    return u,dict(t_new_tick=end,history_start_tick=start,displacement_m=distance,source='PREAPPEARANCE_DISPLACEMENT' if distance>=.3 else 'T_NEW_HEADING')

def inside_rectangle(points,position,u):
    p=np.asarray(points)-np.asarray(position)[:2];left=np.array([-u[1],u[0]])
    along=p@u;side=p@left
    return (along>=-1e-12)&(along<=1.+1e-12)&(np.abs(side)<=.2+1e-12)
