"""Frozen outcome audit plus Phase53 telemetry, no historical re-analysis."""
import csv,json
from collections import Counter
from pathlib import Path
import numpy as np
from nomad_phase47c.metrics import audit as frozen_audit
from nomad_phase24r.online_metrics import rows

def q(a,p):return float(np.quantile(a,p)) if len(a) else None

def audit(root):
    root=Path(root);r=frozen_audit(root);c=json.loads((root/'scenario.json').read_text());assert c['phase53p']
    duration=r['duration_s'];trajectory=list(csv.DictReader((root/'agent_trajectory.csv').open()))
    t=np.array([float(e['simulation_time_s']) for e in trajectory]);v=np.array([float(e['v_m_s']) for e in trajectory]);dt=np.diff(t)
    commands=rows(root/'phase20_commands.jsonl');states=Counter();cursor=0
    for i,left in enumerate(t[:-1]):
        while cursor+1<len(commands) and commands[cursor+1]['time_s']<=left+1e-10:cursor+=1
        source=commands[cursor]['source'] if commands and commands[cursor]['time_s']<=left+1e-10 else 'INITIAL_INFERENCE_WAIT'
        states[source]+=float(dt[i])
    graph=rows(root/'graph_ho.jsonl');solves=[e for e in graph if e['event']=='SOLVE'];installs=[e for e in graph if e['event']=='INSTALL']
    ec=[e for e in rows(root/'exec_cert.jsonl') if e['event']=='CHECK']
    assert ec and all(e['model']=='C0_NA_BRAKING_TAIL' and e['stopped'] and e['terminal_vw']==[0.,0.] for e in ec)
    assert r['detour_applied_count']==0 and r['g_dispatches']==0
    assert not [e for e in rows(root/'repair.jsonl') if e['event'] in ('DISPATCH','TRIGGER')]
    assert all(e['tail_pass'] and e['accepted'] for e in solves if e['applied'])
    # Expiry is deliberately retained: valid controls have age<1s; actual
    # expirations and startup missing are separately reported, never forbidden.
    controls=rows(root/'controller.jsonl')
    for e in controls:
        if e.get('waypoint_age_wall_s') is not None and e.get('status') in ('valid','expired'):
            assert bool(e['valid'])==(e['waypoint_age_wall_s']<1.0),(e['simulation_time_s'],e['status'])
    assert json.loads((root/'summary.json').read_text())['delivery_delay']['configured_additional_s']==c['phase53p_delay_s']
    jumps=[e['heading_discontinuity_deg'] for e in installs if e['heading_discontinuity_deg'] is not None]
    times=[e['solve_s'] for e in solves]
    r.update(method=c['phase53p_method'],base_scene=r['scene'],scene=c['phase53p_level'],condition=c['phase53p_condition'],delay_s=c['phase53p_delay_s'],
        stopped_s=float(dt[np.abs(v[1:])<.01].sum()),command_state_seconds=dict(states),align_rotate_s=states['ALIGN_ROTATE'],
        heading_discontinuity_p50_deg=q(jumps,.5),heading_discontinuity_p95_deg=q(jumps,.95),heading_discontinuity_n=len(jumps),
        ec_checks=len(ec),ec_rejects=sum(not e['passed'] for e in ec),graph_attempts=len(solves),graph_applied=sum(e['applied'] for e in solves),
        graph_adoption_rate=sum(e['applied'] for e in solves)/len(solves) if solves else None,
        graph_solve_p50_s=q(times,.5),graph_solve_p95_s=q(times,.95),graph_reasons=dict(Counter(e['reason'] for e in solves)),
        graph_installations=len(installs),new_timeout_count=sum(bool(e.get('new_timeout')) for e in controls),
        startup_missing_rows=sum(e.get('status')=='missing' for e in controls))
    return r
