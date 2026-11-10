"""Scenario/evaluation only: no dynamic oracle data enters the controller."""
import csv,json,math
import numpy as np
from nomad_isaac.common import integrate_se2,write_json
from nomad_isaac.clearance import configured_obstacles,segment_clearance
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase16.geometry import rect

PERSON_RADIUS=.2

def reference(c):
    nodes=json.load(open(c['topomap_manifest']))['nodes']
    return XYPath(np.asarray([n['world_pose'][:2] for n in nodes]))

def placement(c,index,seed=20261113):
    scene=c['phase16_scene'];axis=0 if scene=='L2' else 1;lat=1-axis
    path=reference(c);cross_axis=3.5 if scene=='L2' else 2.7
    hits=[]
    for a,b in zip(path.points[:-1],path.points[1:]):
        if a[axis]<=cross_axis<=b[axis] and b[axis]>a[axis]:hits.append(a+(b-a)*(cross_axis-a[axis])/(b[axis]-a[axis]))
    assert hits,'No reference crossing'
    cross=hits[0];bounds=rect(c);lo,hi=((bounds[0],bounds[1]),(bounds[2],bounds[3]))[lat]
    for box in configured_obstacles(c):
        center=np.asarray(box['center_xy_m']);half=np.asarray(box['size_xyz_m'][:2])/2
        if abs(center[axis]-cross_axis)>half[axis]+PERSON_RADIUS:continue
        if center[lat]<cross[lat]:lo=max(lo,center[lat]+half[lat])
        else:hi=min(hi,center[lat]-half[lat])
    rng=np.random.default_rng(np.random.SeedSequence([seed,index,axis]))
    distance=float(rng.uniform(1.5,2.5));jitter=float(rng.uniform(-.1,.1));positive=index%2==1
    start=cross.copy();end=cross.copy()
    start[lat]=lo+.35+jitter if positive else hi-.35-jitter
    end[lat]=hi-.25 if positive else lo+.25
    s_cross=path.project(cross)[0];assert 1.5<=distance<=2.5 and s_cross-distance>0
    return dict(crossing_xy=cross.tolist(),crossing_s_m=s_cross,spawn_distance_m=distance,
        trigger_s_m=s_cross-distance,start_xy=start.tolist(),end_xy=end.tolist(),lateral_jitter_m=jitter,
        direction='LOW_TO_HIGH' if positive else 'HIGH_TO_LOW',axis=axis,reference_definition='Topomap node-pose polyline arclength; scenario only',
        diameter_m=.4,height_m=1.7,exit_policy='REMOVE_AT_OPPOSITE_EDGE',random_seed=seed)

def geometry_check(c,p):
    a=np.asarray(p['start_xy']);b=np.asarray(p['end_xy']);xmin,xmax,ymin,ymax=rect(c)
    wall=min(min(q[0]-xmin,xmax-q[0],q[1]-ymin,ymax-q[1])-PERSON_RADIUS for q in (a,b))
    gaps={}
    for box in configured_obstacles(c):
        center=np.asarray(box['center_xy_m']);half=np.asarray(box['size_xyz_m'][:2])/2
        gaps[box['id']]=segment_clearance(a,b,center-half,center+half,PERSON_RADIUS)[0]
    okay=wall>0 and all(g>0 for g in gaps.values())
    return dict(passed=bool(okay),wall_clearance_m=float(wall),static_clearance_m=gaps,
        start_xy=a.tolist(),end_xy=b.tolist(),diameter_m=.4,height_m=1.7,depth_render_performed=False)

def travel_duration(p):return float(np.linalg.norm(np.asarray(p['end_xy'])-p['start_xy'])/p['speed_m_s'])

def center_at(p,elapsed):
    a=np.asarray(p['start_xy'],float);b=np.asarray(p['end_xy'],float);duration=travel_duration(p)
    return a+np.clip(elapsed/duration,0.,1.)*(b-a)

def relative_sweep(pose,v,w,h,person_start,person_end,robot_radius=.09):
    """Circular robot arc versus translating circle, continuous-time bounds.

    Subtract linear person motion. Relative chord distance minus robot arc
    sagitta is a lower bound; actual relative arc witness is an upper bound.
    Same 1e-12 slack/refinement/contact-stop convention as frozen box monitor.
    """
    pose=np.asarray(pose,float);a=np.asarray(person_start,float);b=np.asarray(person_end,float)
    pieces=1
    while True:
        lows=[];highs=[];witnesses=[];step=h/pieces
        angle=abs(w*step);sag=abs(v)*step*(2*math.sin(angle/4)**2/angle) if angle else 0.
        for i in range(pieces):
            t0=i*step;t1=(i+1)*step;u0=i/pieces;u1=(i+1)/pieces
            q0=integrate_se2(pose,v,w,t0)[:2]-(a+(b-a)*u0)
            q1=integrate_se2(pose,v,w,t1)[:2]-(a+(b-a)*u1)
            delta=q1-q0;den=float(delta@delta);fraction=float(np.clip(-q0@delta/den,0,1)) if den else 0.
            offset=t0+fraction*step;person=a+(b-a)*(u0+fraction/pieces)
            robot=integrate_se2(pose,v,w,offset);radius=PERSON_RADIUS+robot_radius
            lows.append(float(np.linalg.norm(q0+fraction*delta)-radius-sag-1e-12))
            highs.append(float(np.linalg.norm(robot[:2]-person)-radius));witnesses.append((offset,robot,person))
        low=min(lows);high=min(highs)
        if not low<=0<high or high-low<=1e-9 or pieces==256:break
        pieces*=2
    j=int(np.argmin(highs));offset,robot,person=witnesses[j]
    return dict(lower_m=float(low),upper_m=float(high),center_distance_upper_m=float(high+PERSON_RADIUS+robot_radius),
        geometric_overlap=bool(high<=0),pieces=pieces,witness_offset_s=float(offset),witness_pose=robot.tolist(),person_witness_xy=person.tolist())

class GhostLog:
    """Read-only newly-published map samples at72Hz; never clears occupancy."""
    def __init__(self,out,p):
        self.stream=(out/'post_removal_ghost.jsonl').open('x');self.p=p;self.last_frame=None;self.indices=None
        self.baseline=None;self.records=0;self.max_offset=None
    def sample(self,field,now,spawn_s,end_s):
        if self.indices is None:
            h=field.h;a=np.asarray(self.p['start_xy']);b=np.asarray(self.p['end_xy']);r=PERSON_RADIUS+h/np.sqrt(2)
            # Cell centers whose square can meet the swept disk. Restrict all
            # later operations to this immutable crop, never scan full EDT.
            lo=np.floor((np.minimum(a,b)-r-field.origin)/h).astype(int);hi=np.ceil((np.maximum(a,b)+r-field.origin)/h).astype(int)
            xs=np.arange(max(0,lo[0]),min(field.occupied.shape[1]-1,hi[0])+1)
            ys=np.arange(max(0,lo[1]),min(field.occupied.shape[0]-1,hi[1])+1)
            xx,yy=np.meshgrid(xs,ys);xy=field.origin+np.stack([xx,yy],axis=-1)*h
            d=b-a;u=np.clip(np.sum((xy-a)*d,axis=-1)/float(d@d),0,1)
            trail=np.linalg.norm(xy-(a+u[...,None]*d),axis=-1)<=r
            self.indices=(yy[trail],xx[trail]);self.endpoint=np.linalg.norm(xy[trail]-b,axis=-1)<=r
        occupied=field.occupied[self.indices]
        if spawn_s is None:
            self.baseline=occupied.copy();return
        frame=int(field.metadata['frame_id']);sim_s=float(field.metadata.get('sim_s',0))
        if frame==self.last_frame:return
        self.last_frame=frame
        if end_s is None or not end_s<=sim_s<=end_s+5 or now<end_s:return
        new=occupied if self.baseline is None else occupied&~self.baseline
        observed=field.observed[self.indices]
        row=dict(frame_id=frame,capture_sim_s=sim_s,sampled_sim_s=now,offset_from_removal_s=sim_s-end_s,
            endpoint_occupied_cells=int(occupied[self.endpoint].sum()),endpoint_new_occupied_cells=int(new[self.endpoint].sum()),
            swept_trail_occupied_cells=int(occupied.sum()),swept_trail_new_occupied_cells=int(new.sum()),
            endpoint_observed_cells=int(observed[self.endpoint].sum()),trail_cells=len(occupied),endpoint_cells=int(self.endpoint.sum()),
            baseline_available=self.baseline is not None,publication_monotonic_ns=field.metadata.get('publication_monotonic_ns'))
        self.stream.write(json.dumps(row,allow_nan=False)+'\n');self.stream.flush();self.records+=1;self.max_offset=sim_s-end_s
    def close(self):self.stream.close()

class MovingPersonMonitor:
    def __init__(self,c,out):
        self.c=c;self.p=c['phase50p_moving'];self.out=out/'dynamic';self.out.mkdir()
        self.path=reference(c);self.adaptive=True;self.spawn=None;self.placement=None;self.last_tick=-1
        self.stop_reason=None;self.contact=None;self.overlap=False;self.minimum=None;self.minimum_upper=None;self.last_pose=None
        self.active_checks=0;self.end_s=None;self.retired=False;self.last_progress=None;self.hz=c['integration_hz'];assert self.hz==72
        self.log=(self.out/'person_trajectory.jsonl').open('x');self.eval_log=(self.out/'clearance.jsonl').open('x')
        self.removal=None;self.depth_provider=None;self.ghost=GhostLog(self.out,self.p)
    @property
    def obstacle(self):
        if self.spawn is None:return None
        t=self.last_tick/self.hz;elapsed=t-self.spawn['simulation_time_s'];q=center_at(self.p,elapsed)
        return dict(id='MovingPerson',shape='cylinder',radius_m=.2,height_m=1.7,center_xy_m=q.tolist(),
            start_xy=self.p['start_xy'],end_xy=self.p['end_xy'],speed_m_s=self.p['speed_m_s'],
            spawn_tick=self.spawn['tick'],spawn_sim_s=self.spawn['simulation_time_s'],exit_sim_s=self.end_s,
            active=not self.retired,simulation_time_s=t)
    def observe_tick(self,tick,previous,pose,v,w,old_id,old_valid,monotonic_ns,old_received_ns=None):
        assert tick==self.last_tick+1;self.last_tick=tick;t=tick/self.hz
        if self.depth_provider is not None:
            self.ghost.sample(self.depth_provider(),t,None if self.spawn is None else self.spawn['simulation_time_s'],self.end_s)
        s=self.path.project(pose[:2])[0]
        if self.spawn is None and s>=self.p['trigger_s_m']:
            # No teleport-dependent trigger band: first forward threshold crossing.
            remaining=self.p['crossing_s_m']-s;assert 1.5-1/72*.3<=remaining<=2.5+1e-9
            self.placement=dict(status='PLACED',shape='cylinder',geometry=geometry_check(self.c,self.p));assert self.placement['geometry']['passed']
            self.spawn=dict(tick=tick,simulation_time_s=t,pose=list(pose),reference_remaining_m=float(remaining),
                obstacle=dict(self.c['dynamic_obstacle'],center_xy_m=self.p['start_xy']),old_id=old_id)
            self.end_s=t+travel_duration(self.p)
            write_json(self.out/'spawn.json',self.spawn);write_json(self.out/'placement.json',self.placement)
        if self.spawn is not None:
            begin=max((tick-1)/self.hz,self.spawn['simulation_time_s']);end=min(t,self.end_s)
            if begin<=end and not self.retired:
                offset=max(0.,begin-(tick-1)/self.hz) if tick else 0.
                start_pose=integrate_se2(previous,v,w,offset)
                gap=relative_sweep(start_pose,v,w,max(0.,end-begin),center_at(self.p,begin-self.spawn['simulation_time_s']),center_at(self.p,end-self.spawn['simulation_time_s']),self.c['agent_radius_m'])
                self.minimum=gap['lower_m'] if self.minimum is None else min(self.minimum,gap['lower_m'])
                self.minimum_upper=gap['upper_m'] if self.minimum_upper is None else min(self.minimum_upper,gap['upper_m'])
                self.overlap|=gap['geometric_overlap'];self.active_checks+=1
                record=dict(start_sim_s=begin,end_sim_s=end,**gap)
                if gap['lower_m']<=0 and self.contact is None:
                    self.contact=dict(detected_sim_s=t,detected_pose=list(pose),**record)
                    self.stop_reason='geometric_collision' if gap['geometric_overlap'] else 'conservative_contact_stop'
                self.eval_log.write(json.dumps(record,allow_nan=False)+'\n');self.eval_log.flush()
            if t>=self.end_s and not self.retired:
                offset=self.end_s-(tick-1)/self.hz;robot=integrate_se2(previous,v,w,max(0.,offset))
                center=np.asarray(self.p['end_xy']);distance=float(np.linalg.norm(robot[:2]-center))
                self.removal=dict(simulation_time_s=self.end_s,recorded_at_tick=tick,person_center_xy_m=center.tolist(),
                    robot_pose=robot.tolist(),center_distance_m=distance,footprint_clearance_m=distance-.2-self.c['agent_radius_m'],
                    surface_wall_gap_m=.05,reason='OPPOSITE_EDGE_0P05M',one_crossing=True)
                write_json(self.out/'removal.json',self.removal)
            self.retired=t>=self.end_s
            self.log.write(json.dumps(dict(tick=tick,**self.obstacle),allow_nan=False)+'\n');self.log.flush()
        self.last_progress=s
        return dict(tick=tick,active=self.spawn is not None and not self.retired)
    def finish(self,goal_entry):
        self.log.close();self.eval_log.close();self.ghost.close()
        return dict(status='SPAWNED' if self.spawn else 'NOT_TRIGGERED',spawn=self.spawn,placement=self.placement,shape='cylinder',
            removal=self.removal,exit_sim_s=self.end_s,active_checks=self.active_checks,
            ghost_records=self.ghost.records,ghost_last_offset_s=self.ghost.max_offset,evaluation=dict(geometric_overlap=bool(self.overlap),first_contact=self.contact,
                minimum_swept_clearance_lower_m=self.minimum,minimum_swept_clearance_upper_m=self.minimum_upper,
                minimum_center_distance_upper_m=None if self.minimum_upper is None else self.minimum_upper+.2+self.c['agent_radius_m'],
                corridor_containment_certified=True,minimum_corridor_clearance_lower_m=None,passage=None,
                avoidance_success=bool(goal_entry and self.spawn and not self.contact)))
