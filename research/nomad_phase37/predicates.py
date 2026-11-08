"""Unambiguous TRIG primitives only; caller supplies the baseline direction.

No component association, episode labels, gate denominators or online policy
are assumed here. Those require the preregistration clarifications.
"""
import numpy as np
from nomad_phase20f.direction import inside_rectangle


def observed_obstacle_ahead(snapshot, pose, direction):
    direction=np.asarray(direction,dtype=float)
    if direction.shape!=(2,) or not np.isfinite(direction).all() or abs(np.linalg.norm(direction)-1.)>1e-9:
        raise ValueError('Unit direction required')
    mask=np.asarray(snapshot.observed,dtype=bool)&np.asarray(snapshot.occupied,dtype=bool)
    yy,xx=np.nonzero(mask)
    points=np.asarray(snapshot.origin)+np.column_stack([xx,yy])*float(snapshot.h)
    selected=points[inside_rectangle(points,pose,direction)]
    return dict(present=bool(len(selected)>=5),cells_ahead=int(len(selected)),points=selected)


def guarded_direction(poses,tick,baseline_direction):
    """The >90-degree guard alone; does not redefine the baseline direction."""
    poses=np.asarray(poses,dtype=float);base=np.asarray(baseline_direction,dtype=float)
    assert 0<=tick<len(poses) and base.shape==(2,) and abs(np.linalg.norm(base)-1.)<1e-9
    info=dict(overridden=False,baseline_direction=base.tolist(),distance_3s_m=None,distance_10s_m=None,angle_deg=None)
    if tick<720:return base.copy(),dict(info,reason='INCOMPLETE_10S_HISTORY')
    d3=poses[tick,:2]-poses[tick-216,:2];d10=poses[tick,:2]-poses[tick-720,:2]
    n3=float(np.linalg.norm(d3));n10=float(np.linalg.norm(d10));info.update(distance_3s_m=n3,distance_10s_m=n10)
    if n10<.3:return base.copy(),dict(info,reason='SHORT_10S_DISPLACEMENT')
    if n3<=1e-12:return base.copy(),dict(info,reason='UNDEFINED_3S_DIRECTION')
    u3=d3/n3;u10=d10/n10;dot=float(np.clip(u3@u10,-1.,1.));angle=float(np.degrees(np.arccos(dot)))
    info.update(direction_3s=u3.tolist(),direction_10s=u10.tolist(),angle_deg=angle)
    if dot<0.:return u10,dict(info,overridden=True,reason='DIRECTION_DISAGREEMENT_GT_90')
    return base.copy(),dict(info,reason='BASELINE_DIRECTION_RETAINED')
