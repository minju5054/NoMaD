"""Verbatim Phase31-E calculation functions; copied into a new validation tool.
Original transient script SHA256: 54c2d6aed3c1c07e33c9a61b8dc75139a4ee4973d134cfab1564b2d71df197cf
No existing analysis source/result is modified by this adapter.
"""
import hashlib,json,csv
from pathlib import Path
import numpy as np
from nomad_isaac.clearance import configured_obstacles
from nomad_phase16.geometry import path_safety
from nomad_phase15b.depth import Snapshot
from nomad_phase20d.recent import CachedField
INPUTS={};CACHE={};LOG={}
def register(p):
 p=Path(p).resolve()
 if str(p) not in INPUTS:INPUTS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 return p

def read(p):return json.loads(register(p).read_text())

def lines(p):return [json.loads(s) for s in register(p).read_text().splitlines() if s] if Path(p).exists() else []

def trajectory(root):
 p=Path(root)/'agent_trajectory.csv'
 if str(p) in CACHE:return CACHE[str(p)]
 with register(p).open() as f:r=list(csv.DictReader(f))
 d=dict(t=np.array([float(q['simulation_time_s']) for q in r]),q=np.array([[float(q[k]) for k in ('x_m','y_m','yaw_rad')] for q in r]),
        v=np.array([float(q['v_m_s']) for q in r]),w=np.array([float(q['w_rad_s']) for q in r]),goal=np.array([float(q['goal_distance_m']) for q in r]))
 CACHE[str(p)]=d;return d

def dynamic_entries(summary):
 d=summary.get('dynamic_obstacle') or {}
 return d.get('boxes') or ([d] if d.get('spawn') else [])

def contacts(summary):
 result=[];obs=summary['obstacle_evaluation']
 if obs.get('first_contact'):result.append(dict(obs['first_contact'],source='static',obstacle_id=obs['first_contact'].get('obstacle_id','StaticObstacle')))
 for b in dynamic_entries(summary):
  c=(b.get('evaluation') or {}).get('first_contact')
  if c:result.append(dict(c,source='dynamic',obstacle_id=b['spawn']['obstacle']['id']))
 return sorted(result,key=lambda r:r['detected_sim_s'])

def boxes_at(summary,c,t):
 boxes=list(configured_obstacles(c))
 for e in dynamic_entries(summary):
  if e.get('spawn') and e['spawn']['simulation_time_s']<=t+1e-10:boxes.append(e['spawn']['obstacle'])
 return boxes

def oracle_path(path,c,boxes):
 assert all(not b.get('yaw_deg',0) for b in boxes),'Selected scenes should be axis-aligned'
 cfg=dict(c,obstacles=boxes);cfg.pop('obstacle',None)
 value=path_safety(np.asarray(path),cfg)
 return float(min(value['obstacle_clearance_m'],value['corridor_clearance_m'])),value

def cached_field(file):
 register(file);raw=Snapshot.load(file);obj=object.__new__(CachedField);obj.__dict__.update(raw.__dict__);return obj

def log(root,name):
 k=(str(root),name)
 if k not in LOG:LOG[k]=lines(Path(root)/name)
 return LOG[k]

def trace(root):
 a=trajectory(root)
 if 'ns' not in a:
  with register(Path(root)/'agent_trajectory.csv').open() as f:a['ns']=np.array([int(x['monotonic_ns']) for x in csv.DictReader(f)],dtype=np.int64)
 return a

def box_history(root,tr,box,tc,ta,spawn):
 updates=log(root,'depth/updates.jsonl');ns_contact=float(np.interp(tc,tr['t'],tr['ns']))
 available=[u for u in updates if u['publication_monotonic_ns']<=ns_contact and u['sim_s']<=tc and Path(u['file']).exists()]
 if not available:return dict(depth_history_status='NO_ARCHIVED_PRECONTACT_MAP')
 u=available[-1];register(u['file'])
 with np.load(u['file']) as z:
  hist=z['first_occupied_tick'];occ=z['occupied'];origin=z['origin'];h=float(z['h']);ny,nx=hist.shape
  center=np.array(box['center_xy_m']);half=np.array(box['size_xyz_m'][:2])/2
  # Selected boxes are axis-aligned. Match occupied-cell centers to the physical
  # box with half a cell diagonal tolerance, never use RGB visibility as depth.
  assert not box.get('yaw_deg',0)
  eps=h/np.sqrt(2);xs=origin[0]+np.arange(nx)*h;ys=origin[1]+np.arange(ny)*h
  ix=np.where(np.abs(xs-center[0])<=half[0]+eps)[0];iy=np.where(np.abs(ys-center[1])<=half[1]+eps)[0]
  ht=hist[np.ix_(iy,ix)];ot=occ[np.ix_(iy,ix)]
  ticks=ht[(ht>=max(0,int(np.ceil(spawn*72-1e-7))))&(ht<=int(round(tc*72)))]
  when=float(ticks.min()/72) if len(ticks) else None
  after=ticks[ticks>ta*72+1e-7];after_t=float(after.min()/72) if len(after) else None
  pub=next((x for x in updates if when is not None and abs(x['sim_s']-when)<1/144),None)
  pub_s=float(np.interp(pub['publication_monotonic_ns'],tr['ns'],tr['t'])) if pub else None
  # For late archives there may be no frame exactly at contact. Carry the
  # historical first occupancy, but report this coverage gap explicitly.
  return dict(depth_history_status='MEASURED_CELL_HISTORY',depth_history_file=u['file'],history_snapshot_s=u['sim_s'],history_capture_gap_to_contact_s=tc-u['sim_s'],
   box_first_occupied_capture_s=when,box_first_occupied_publish_s=pub_s,
   box_first_seen_before_install=(pub_s<=ta if pub_s is not None else None),
   box_first_observation_after_install_s=when if when is not None and ta<when<=tc else None,
   newly_observed_box_cell_after_install_s=after_t,box_ever_occupied_cells=int(len(ticks)),box_current_occupied_cells=int(ot.sum()),box_cell_tolerance_m=eps,
   box_first_minus_install_s=when-ta if when is not None else None,box_first_publish_minus_install_s=pub_s-ta if pub_s is not None else None)
