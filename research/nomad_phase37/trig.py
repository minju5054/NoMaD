"""Observed-obstacle trigger with a frozen first-forward-observation anchor.

Only depth occupancy/history and odometry enter this module. No oracle input.
"""
import numpy as np
from scipy.ndimage import label,find_objects
from nomad_phase20f.history import CONNECTIVITY
from nomad_phase20f.direction import component_direction,inside_rectangle
from nomad_phase20c.detour_known import radial_reference
from nomad_phase24r.trigger import approach_progress,passed
from .predicates import guarded_direction


class ObservedTrigger:
    def __init__(self):
        self.first_ahead=None;self.direction_cache={};self.origin=None;self.h=None

    def direction(self,poses,t_ref):
        t_ref=int(t_ref)
        if t_ref not in self.direction_cache:
            if 0<=t_ref<len(poses):base,detail=component_direction(poses,t_ref)
            else:base,detail=radial_reference(poses,len(poses)-1)
            u,guard=guarded_direction(poses,t_ref,base)
            self.direction_cache[t_ref]=(u,dict(t_ref_tick=t_ref,base=detail,guard=guard))
        return self.direction_cache[t_ref]

    def observe(self,field,poses,tick):
        """Track first entry at common observed ticks; backfill known births.

        first_occupied_tick explicitly proves an occupied observation even when
        that old frame was pruned. Backdating is allowed only when that cell
        was inside the base 3s-direction rectangle at its recorded birth.
        Otherwise retain the first *available* forward observation; no missing
        map is interpolated. The 10s guard changes the frozen direction after
        the base first-entry timestamp has been established.
        """
        if self.first_ahead is None:
            self.first_ahead=np.full(field.occupied.shape,-1,np.int32);self.origin=np.asarray(field.origin).copy();self.h=field.h
        assert self.first_ahead.shape==field.occupied.shape and np.array_equal(self.origin,field.origin) and self.h==field.h
        yy,xx=np.nonzero(np.asarray(field.occupied)&np.asarray(field.observed));points=field.origin+np.c_[xx,yy]*field.h
        unassigned=self.first_ahead[yy,xx]<0
        births=field.first_occupied_tick[yy,xx]
        for birth in np.unique(births[unassigned]):
            if birth<0 or birth>tick:continue
            ids=np.flatnonzero(unassigned&(births==birth));base,_=component_direction(poses,int(birth))
            selected=ids[inside_rectangle(points[ids],poses[birth],base)]
            self.first_ahead[yy[selected],xx[selected]]=birth
        unassigned=self.first_ahead[yy,xx]<0
        if np.any(unassigned):
            base,_=component_direction(poses,tick);ids=np.flatnonzero(unassigned)
            selected=ids[inside_rectangle(points[ids],poses[tick],base)]
            self.first_ahead[yy[selected],xx[selected]]=tick
        return yy,xx,points

    def choose(self,field,poses,tick):
        yy,xx,all_points=self.observe(field,poses,tick)
        labels,_=label(field.occupied&field.observed,CONNECTIVITY);candidates=[]
        # Components only associate an obstacle with its earliest anchor and
        # current distance. The required five cells are counted across the
        # entire rectangle, not an additional connected-component threshold.
        for identity,region in enumerate(find_objects(labels),1):
            if region is None:continue
            cy,cx=np.nonzero(labels[region]==identity);cy+=region[0].start;cx+=region[1].start
            seen=self.first_ahead[cy,cx];seen=seen[seen>=0]
            if not len(seen):continue
            t_ref=int(seen.min());u,detail=self.direction(poses,t_ref);points=field.origin+np.c_[cx,cy]*field.h
            if passed(points,poses[tick],u,field.radius,field.h):continue
            own_inside=inside_rectangle(points,poses[tick],u)
            if not own_inside.any():continue
            count=int(inside_rectangle(all_points,poses[tick],u).sum())
            if count<5:continue
            key=int(np.min(cy*labels.shape[1]+cx))
            candidates.append(dict(component_id=key,t_ref_tick=t_ref,t_new_tick=t_ref,u_ref=u.tolist(),direction=detail,
                cells_ahead=count,component_cells_ahead=int(own_inside.sum()),cells_total=len(points),points=points))
        return min(candidates,key=lambda c:(c['t_ref_tick'],c['component_id'])) if candidates else None

    def check(self,field,poses,tick):
        chosen=self.choose(field,poses,tick)
        if chosen is None:return dict(fire=False,reason='NO_OBSERVED_OBSTACLE_AHEAD',component=None)
        u=np.array(chosen['u_ref']);forward=float((poses[tick,:2]-poses[max(0,tick-216),:2])@u)
        drop,old,now=approach_progress(chosen['points'],poses[max(0,tick-216)],poses[tick])
        fire=bool(tick>=216 and (forward<.2 or drop<.1))
        return dict(fire=fire,reason='NO_PROGRESS' if fire else 'PROGRESS',component=chosen,
            progress_3s_m=forward,distance_drop_m=drop,distance_old_m=old,distance_now_m=now)
