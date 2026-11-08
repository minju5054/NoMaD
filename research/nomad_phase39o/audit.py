"""Independent exact certificate checks and descriptive escape measurements."""
import numpy as np
from scipy.spatial import cKDTree
from nomad_phase20.repair import RepairGraphR2
from nomad_phase19r.repair import initialize
from nomad_phase20c.detour_known import KnownDetourGraph
from nomad_phase20d.recent import RecentSnapshot,build_cache
from nomad_phase33p.storage import load_snapshot
from nomad_phase0.pure_pursuit import XYPath
from .solver import certificate

def reaching_distance(path,base,strict=None):
    """Descriptive first exact point clearance>=.025 on a1mm arclength grid.

    This does not replace the continuous certificate. The interval resolution
    is explicitly reported rather than claiming an exact crossing location.
    """
    curve=XYPath(path);s=np.linspace(0,curve.s[-1],max(2,int(np.ceil(curve.s[-1]/.001))+1));q=np.array([curve.at(x) for x in s]);d=np.empty(len(s))
    for mask,field in ((s<=.3,base),(s>.3,strict if strict is not None else base)):
        if not mask.any():continue
        yy,xx=np.nonzero(field.occupied)
        if len(xx):d[mask]=cKDTree(field.origin+np.c_[xx,yy]*field.h).query(q[mask],workers=1)[0]-field.radius
        else:d[mask]=float(field.values.min())
    eligible=np.flatnonzero(d>=.025)
    return dict(first_clearance_025_distance_m=float(s[eligible[0]]) if len(eligible) else None,
        crossing_sampling_resolution_m=float(s[1]-s[0]),first_clearance_025_is_sampled=True)

def check(case,variant,numeric):
    base=load_snapshot(RecentSnapshot,case['job']['snapshot_file']);strict=build_cache(base,case['job']['evaluation_tick'])[0] if case['kind']=='R3' else None
    job=case['job'];rows=[]
    for i,r in enumerate(numeric['results']):
        if not r.get('accepted'):continue
        if case['kind']=='R2':
            reference,_=initialize(job['samples_world'][i],job['B']);graph=RepairGraphR2(reference,job['B'],base)
        else:graph=KnownDetourGraph(job['B'],job['u_ref'],base,strict,0)
        escape=variant in ('V2','V3') and graph.cB<.025
        c=certificate(graph,np.asarray(r['path']),escape)
        row=dict(index=i,certificate_pass=c['certificate_pass'],depth_clearance_m=c['depth_clearance_m'],cB=graph.cB,
            negative_B_escape=graph.cB<0,escape_schedule=escape)
        if escape:row.update(reaching_distance(r['path'],base,strict))
        rows.append(row)
    return rows

def reproduction(case,numeric):
    old=case.get('recorded_numeric')
    if old is None:return dict(available=False,reason='NO_RECORDED_NUMERICAL_RESULT')
    before=old.get('results',[]);after=numeric.get('results',[]);n=max(len(before),len(after));equal=[];errors=[]
    for i in range(n):
        a=before[i] if i<len(before) else {};b=after[i] if i<len(after) else {}
        equal.append(a.get('disposition')==b.get('disposition'))
        if a.get('path') is not None and b.get('path') is not None and np.shape(a['path'])==np.shape(b['path']):
            errors.append(float(np.linalg.norm(np.asarray(a['path'])-b['path'],axis=1).max()))
    return dict(available=True,sample_comparisons=n,disposition_matches=sum(equal),all_dispositions_match=all(equal),
        selected_index_match=old.get('selected_sample')==numeric.get('selected_sample'),maximum_path_difference_m=max(errors,default=None),
        recorded_runtime_disposition=case['recorded_runtime_disposition'],scope='numeric pre-EC per-sample disposition; timing-dependent online decisions not replayed')
