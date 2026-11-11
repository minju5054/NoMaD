"""Frozen Phase61 oracle/outcome audit plus U acceptance and length telemetry."""
import json
from pathlib import Path
import numpy as np
from nomad_phase61p.metrics import audit as frozen_audit
from nomad_phase24r.online_metrics import rows
from nomad_phase53p.metrics import q

def audit(root):
    root=Path(root);r=frozen_audit(root);c=json.loads((root/'scenario.json').read_text());assert c['phase62p_method']=='UG-GOAL'
    events=rows(root/'ugraph.jsonl');solves=[e for e in events if e['event']=='SOLVE'];installs=[e for e in events if e['event']=='INSTALL']
    assert len(installs)==sum(e['applied'] for e in solves)
    for e in solves:
        assert len(e['results'])==11 and e['source_chunk_id']==e['id']
        if e['applied']:
            chosen=next(x for x in e['results'] if x['start_index']==e['chosen_start'])
            assert chosen['hard_feasible'] and 'goal' in chosen['costs']
            assert any(x['passed'] and x['start_index']==e['chosen_start'] for x in e['checks'])
            assert np.min(np.asarray(chosen['states'])[:,3])>=-1e-7
    goals=[e['goal_distance_at_solve_m'] for e in solves]
    lengths=[float(np.linalg.norm(np.diff(np.asarray(e['path_world']),axis=0),axis=1).sum()) for e in installs]
    times=[e['solve_s'] for e in solves]
    r.update(method='UG-GOAL',u_attempts=len(solves),u_applied=len(installs),u_adoption_rate=len(installs)/len(solves) if solves else None,
        u_solution_length_median_m=q(lengths,.5),u_goal_distance_at_solve_median_m=q(goals,.5),u_solve_p50_s=q(times,.5),u_solve_p95_s=q(times,.95),
        u_install_lengths_m=lengths,u_goal_distances_at_solve_m=goals,u_stationary_installs=sum(e['stationary_xy'] for e in installs),
        u_reasons={reason:sum(e['reason']==reason for e in solves) for reason in sorted({e['reason'] for e in solves})})
    return r
