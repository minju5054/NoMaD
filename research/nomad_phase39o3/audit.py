"""Recheck new-policy certificates, never optimize cached baselines."""
import numpy as np
from nomad_phase20d.recent import RecentSnapshot,build_cache
from nomad_phase33p.storage import load_snapshot
from nomad_phase20c.detour_known import KnownDetourGraph
from .maps import VARIANTS,policy_map
from .solver import map_certificate
from .metrics import measure

def check(case,variant,numeric):
    assert variant in VARIANTS and case['kind']=='R3'
    job=case['job'];base=load_snapshot(RecentSnapshot,job['snapshot_file']);planning,_=policy_map(base,job['B'],variant)
    # Only the original base-defined cB/near threshold is needed here. Both
    # certificate fields are explicitly replaced by the planning map.
    graph=KnownDetourGraph(job['B'],job['u_ref'],base,planning,0);rows=[]
    for i,r in enumerate(numeric['results']):
        if not r['accepted']:continue
        cert=map_certificate(graph,np.asarray(r['path']),planning,variant)
        rows.append(dict(index=i,certificate_pass=bool(cert['certificate_pass']),cB=float(graph.cB),
            depth_clearance_m=cert['depth_clearance_m'],certificate_map=variant,escape_schedule=bool(graph.cB<.025),
            negative_B_accepted=bool(graph.cB<0)))
    return rows,measure(case,numeric)
