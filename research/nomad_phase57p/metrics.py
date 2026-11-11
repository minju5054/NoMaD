"""Frozen outcome/HMM audits plus registered MIN switch and latch assertions."""
import csv,json
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_phase47c.metrics import audit as frozen_audit
from nomad_phase24r.online_metrics import rows
from nomad_phase53p.metrics import q

def audit(root):
    root=Path(root);r=frozen_audit(root);c=json.loads((root/'scenario.json').read_text());method=c['phase57p_method']
    assert c['phase57p'] and json.loads((root/'summary.json').read_text())['delivery_delay']['configured_additional_s']==.75
    commands=rows(root/'phase20_commands.jsonl');controls=rows(root/'controller.jsonl')
    for e in controls:
        if e.get('waypoint_age_wall_s') is not None and e.get('status') in ('valid','expired'):
            assert bool(e['valid'])==(e['waypoint_age_wall_s']<1.0)
    tr=list(csv.DictReader((root/'agent_trajectory.csv').open()));t=np.array([float(x['simulation_time_s']) for x in tr]);v=np.array([float(x['v_m_s']) for x in tr]);dt=np.diff(t)
    states=Counter();cursor=0
    for i,left in enumerate(t[:-1]):
        while cursor+1<len(commands) and commands[cursor+1]['time_s']<=left+1e-10:cursor+=1
        source=commands[cursor]['source'] if commands and commands[cursor]['time_s']<=left+1e-10 else 'INITIAL_INFERENCE_WAIT'
        states[source]+=float(dt[i])
    ho=rows(root/'graph_ho.jsonl');solves=[e for e in ho if e['event']=='SOLVE'];installs=[e for e in rows(root/'repair.jsonl') if e['event']=='PATH_APPLIED']
    checks=[e for e in rows(root/'exec_cert.jsonl') if e['event']=='CHECK']
    if method!='NOMAD_RAW':
        assert not any(e['source'] in ('ALIGN_ROTATE','ALIGN_BRAKE','RECOVER_ROTATE','WAIT_FRESH','KEEP_ACTIVE') for e in commands)
        assert not rows(root/'recovery.jsonl') and r['detour_applied_count']==0
        assert all(e['speed_cap_m_s'] is None for e in checks)
        assert all(e['stopped'] and e['terminal_vw']==[0.,0.] for e in checks if e.get('reason')!='INVALID_PATH')
        assert all(not e['alignment'] for e in installs)
        for e in rows(root/'events.jsonl'):
            if e.get('phase16'):assert e['phase16']['selection']['depth_filter_disabled']
        # A latched endpoint cannot emit another normal command until some new
        # path was actually installed, including a periodic EC replacement.
        latch=None
        for e in commands:
            now=e['time_s']
            if latch is not None and any(latch<x['simulation_time_s']<=now for x in installs):latch=None
            if latch is not None:assert e['source']!='NORMAL',(latch,now)
            if e['source']=='ENDPOINT':latch=now
        assert all(e['accepted'] and e['tail_pass'] for e in solves if e['applied'])
    else:
        assert not checks and not solves and not c['depth_camera']
        assert c['phase47c_method']=='NOMAD_RAW' and not c.get('phase43p')
    times=[e['solve_s'] for e in solves]
    r.update(method=method,base_scene='H1-v2' if c.get('h1v2') else r['scene'],scene=c['phase57p_level'],condition='D075',
        stopped_s=float(dt[np.abs(v[1:])<.01].sum()),align_rotate_s=states['ALIGN_ROTATE'],command_state_seconds=dict(states),
        graph_attempts=len(solves),graph_applied=sum(e['applied'] for e in solves),graph_adoption_rate=sum(e['applied'] for e in solves)/len(solves) if solves else None,
        graph_solve_p50_s=q(times,.5),graph_solve_p95_s=q(times,.95),graph_reasons=dict(Counter(e['reason'] for e in solves)),
        ec_checks=len(checks),ec_rejects=sum(not e['passed'] for e in checks),endpoint_latch_enabled=method!='NOMAD_RAW',
        boundary_curvature_dropped=sum(e.get('solver',{}).get('boundary_curvature_dropped',False) for e in solves),
        new_timeout_count=sum(bool(e.get('new_timeout')) for e in controls))
    return r
