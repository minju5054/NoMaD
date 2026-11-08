"""Additional path-only measurements on original base occupancy and observed."""
import numpy as np
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase20d.recent import RecentSnapshot
from nomad_phase33p.storage import load_snapshot

def path_unknown(base,path,B):
    curve=XYPath(path);s=np.linspace(0,float(curve.s[-1]),max(2,int(np.ceil(curve.s[-1]/.005))+1))
    q=np.array([curve.at(x) for x in s]);cells,inside=base.cells(q)
    unknown=np.ones(len(q),bool);x,y=cells[inside].T;unknown[inside]=~base.observed[y,x]
    near=np.linalg.norm(q-np.asarray(B)[:2],axis=1)<=.6+1e-12
    return dict(unknown_fraction_all=float(unknown.mean()),unknown_fraction_within_0p6=float(unknown[near].mean()) if near.any() else None,
        sampled_points=len(q),sampled_points_within_0p6=int(near.sum()),unknown_points=int(unknown.sum()),
        unknown_points_within_0p6=int((unknown&near).sum()),sample_arclength_step_m=float(s[1]-s[0]),
        sampling='uniform arc samples <=5mm, original observed mask; near means Euclidean distance from original B')

def measure(case,numeric):
    if not any(r['accepted'] for r in numeric['results']):
        return dict(accepted_base_clearances=[],selected_path_unknown=None,optimizer_called=False,EC_executed=False)
    base=load_snapshot(RecentSnapshot,case['job']['snapshot_file']);accepted=[]
    for i,r in enumerate(numeric['results']):
        if not r['accepted']:continue
        exact=float(base.exact_clearance(np.asarray(r['path'])))
        accepted.append(dict(index=i,selected=i==numeric['selected_sample'],base_exact_clearance_m=exact,
            base_exact_ge_0p025=exact>=.025))
    selected=numeric['selected_sample']
    unknown=path_unknown(base,numeric['results'][selected]['path'],case['job']['B']) if selected is not None else None
    return dict(accepted_base_clearances=accepted,selected_path_unknown=unknown,optimizer_called=False,EC_executed=False)
