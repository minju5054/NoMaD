"""Read-only native safety and center-X crossing diagnostics (no extrapolation)."""
import copy
import csv
import json
from pathlib import Path
import numpy as np
from nomad_isaac.async_report import rows
from nomad_isaac.common import local_to_world, sha256_file
from nomad_phase2.config import native_safety
from .config import ratio_band


def scope(run):
    summary=json.loads((run/'summary.json').read_text())
    observations=rows(run/'observations.jsonl')
    public=rows(run/'phase2_oracle.jsonl')
    if not public:return [],[],None,summary['scenario']
    box=public[0]['obstacle'];available=public[0]['gate']['available_from']
    # Passing means entire footprint is beyond the rear face, as in the existing monitor.
    trace=np.genfromtxt(run/'agent_trajectory.csv',delimiter=',',names=True)
    threshold=box['center_xy_m'][0]+box['size_xyz_m'][0]/2+summary['scenario']['agent_radius_m']
    passed=np.flatnonzero((trace['x_m']>threshold)&(trace['simulation_time_s']>=available['observation_sim_s']))
    end=float(trace['simulation_time_s'][passed[0]]) if len(passed) else float('inf')
    def inside(r):
        return r['capture_end_monotonic_ns']>=available['capture_end_monotonic_ns'] and r['observation_sim_s']<end
    selected=[r for r in rows(run/'model/inference.jsonl') if inside(r)]
    captures=[o for o in observations if 'observation_id' in o and inside(o)]
    config=copy.deepcopy(summary['scenario']);config['obstacles']=[box];config.pop('dynamic_obstacle',None)
    return selected,captures,box,config


def lateral(xy,box,radius=.09,margin=.02):
    x,y=box['center_xy_m'];threshold=box['size_xyz_m'][1]/2+radius+margin
    for a,b in zip(xy[:-1],xy[1:]):
        if b[0]>a[0] and a[0]<=x<=b[0]:
            value=float(a[1]+(x-a[0])/(b[0]-a[0])*(b[1]-a[1])-y)
            return {'crossing_offset_m':value,'lateral':'LEFT' if value>threshold else 'RIGHT' if value<-threshold else 'FRONT'}
    return {'crossing_offset_m':None,'lateral':'NOT_REACHED'}


def evaluate(metric,pose,config,box):
    assert metric.shape==(8,8,2) and np.isfinite(metric).all()
    samples=[]
    for i,xy in enumerate(metric):
        world=local_to_world(xy,np.array(pose))
        samples.append({'sample':i,**native_safety(world,config),**lateral(world,box)})
    return {'safe_count':sum(s['safe'] for s in samples),'all_unsafe':not any(s['safe'] for s in samples),
            'sample0_safe':samples[0]['safe'],'sample0_lateral':samples[0]['lateral'],
            'sample0_crossing_offset_m':samples[0]['crossing_offset_m'],
            'safe_crossing_count':sum(s['safe'] and s['lateral'] in ('LEFT','RIGHT') for s in samples),
            'samples':samples}


def aggregate(records):
    n=len(records);fraction=sum(r['safe_count']>0 for r in records)/n if n else None
    counts={k:sum(s['lateral']==k for r in records for s in r['samples']) for k in ('LEFT','RIGHT','FRONT','NOT_REACHED')}
    return {'observations':n,'any_safe_observations':sum(r['safe_count']>0 for r in records),
            'any_safe_fraction':fraction,'band':ratio_band(fraction),
            'sample0_safe_fraction':sum(r['sample0_safe'] for r in records)/n if n else None,
            'safe_sample_fraction':sum(r['safe_count'] for r in records)/(8*n) if n else None,
            'any_safe_crossing_fraction':sum(r['safe_crossing_count']>0 for r in records)/n if n else None,
            'lateral_counts':counts}


def csv_write(path,records):
    if not records:return
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');writer.writeheader();writer.writerows(records)
