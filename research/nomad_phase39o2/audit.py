"""Independent certificate check for new outputs only; V0 is read-only."""
import numpy as np
from nomad_phase19r.repair import initialize
from nomad_phase20.repair import RepairGraphR2
from nomad_phase20c.detour_known import KnownDetourGraph
from nomad_phase20d.recent import RecentSnapshot,build_cache
from nomad_phase33p.storage import load_snapshot
from .solver import escape_certificate,VARIANTS

def check(case,variant,numeric):
    assert variant in VARIANTS,'V0 audit/solve is not run again'
    job=case['job'];base=load_snapshot(RecentSnapshot,job['snapshot_file']);strict=build_cache(base,job['evaluation_tick'])[0] if case['kind']=='R3' else None;rows=[]
    for i,r in enumerate(numeric['results']):
        if not r['accepted']:continue
        if case['kind']=='R2':
            q,_=initialize(job['samples_world'][i],job['B']);graph=RepairGraphR2(q,job['B'],base)
        else:graph=KnownDetourGraph(job['B'],job['u_ref'],base,strict,0)
        cert=escape_certificate(graph,r['path']) if variant=='VE' and graph.cB<.025 else graph.certificate(r['path'])
        rows.append(dict(index=i,certificate_pass=bool(cert['certificate_pass']),cB=float(graph.cB),
            depth_clearance_m=cert['depth_clearance_m'],escape_schedule=bool(variant=='VE' and graph.cB<.025),
            negative_B_accepted=bool(graph.cB<0)))
    return rows
