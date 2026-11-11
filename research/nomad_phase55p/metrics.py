"""Frozen HMM/arrival/outcome audit plus U-Graph and HOLD telemetry."""
import csv,json
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_phase47c.metrics import audit as frozen_audit
from nomad_phase24r.online_metrics import rows
from nomad_phase52p.metrics import waypoint_lifetime

def q(a,p):return float(np.quantile(a,p)) if len(a) else None

def switches(installs):
    # Fixed report-only convention: B heading lateral endpoint,1cm dead band;
    # CENTER is skipped, consecutive non-centre L/R reversals are counted.
    previous=None;count=0;directions=[]
    for e in installs:
        if e.get('stationary_xy'):continue
        xy=np.asarray(e['path_world']);B=np.asarray(e['pose']);d=xy[-1]-B[:2]
        lateral=float(d@np.array([-np.sin(B[2]),np.cos(B[2])]))
        side='LEFT' if lateral>.01 else 'RIGHT' if lateral<-.01 else 'CENTER'
        if side!='CENTER':
            count+=int(previous is not None and previous!=side);previous=side
        directions.append(dict(tick=e['tick'],side=side,lateral_m=lateral))
    return count,directions

def audit(root):
    root=Path(root);r=frozen_audit(root);c=json.loads((root/'scenario.json').read_text());assert c['phase55p']
    summary=json.loads((root/'summary.json').read_text());duration=r['duration_s']
    assert summary['delivery_delay']['configured_additional_s']==c['phase53p_delay_s']
    declaration=root/'declared_arrival.json';did=json.loads(declaration.read_text())['id'] if declaration.exists() else None
    startup=waypoint_lifetime(rows(root/'controller.jsonl'),duration,rows(root/'received.jsonl'),did)
    assert r['detour_applied_count']==0 and r['g_dispatches']==0
    assert not [e for e in rows(root/'repair.jsonl') if e['event'] in ('DISPATCH','TRIGGER')]
    raw=list(csv.DictReader((root/'agent_trajectory.csv').open()));t=np.array([float(x['simulation_time_s']) for x in raw]);v=np.array([float(x['v_m_s']) for x in raw]);dt=np.diff(t)
    commands=rows(root/'phase20_commands.jsonl');states=Counter();cursor=0
    for i,left in enumerate(t[:-1]):
        while cursor+1<len(commands) and commands[cursor+1]['time_s']<=left+1e-10:cursor+=1
        source=commands[cursor]['source'] if commands and commands[cursor]['time_s']<=left+1e-10 else 'INITIAL_CHUNK_WAIT'
        if source=='WAYPOINT_TIMEOUT':source='INITIAL_CHUNK_WAIT'
        states[source]+=float(dt[i])
    records=rows(root/'ugraph.jsonl');solves=[x for x in records if x['event']=='SOLVE'];installs=[x for x in records if x['event']=='INSTALL']
    assert len(installs)==sum(x['applied'] for x in solves)
    for x in solves:
        assert len(x['results'])==11
        if x['applied']:
            selected=next(a for a in x['results'] if a['start_index']==x['chosen_start'])
            assert selected['hard_feasible'] and np.min(np.array(selected['states'])[:,3])>=-1e-7
            assert any(a['passed'] and a['start_index']==x['chosen_start'] for a in x['checks'])
    ec=[x for x in rows(root/'exec_cert.jsonl') if x['event']=='CHECK']
    assert all(x['model']=='C0_NA_BRAKING_TAIL' and x['stopped'] and x['terminal_vw']==[0.,0.] for x in ec)
    times=[x['solve_s'] for x in solves];total=[x['total_s'] for x in solves]
    flips,sides=switches(installs)
    all_installs=[x for x in rows(root/'repair.jsonl') if x['event']=='PATH_APPLIED'];all_flips,_=switches(all_installs)
    r.update(startup);r.update(method=c['phase55p_method'],base_scene='H1-v2' if c.get('h1v2') else r['scene'],scene=c['phase55p_level'],condition=c['phase55p_condition'],
        stopped_s=float(dt[np.abs(v[1:])<.01].sum()),align_rotate_s=states['ALIGN_ROTATE'],command_state_seconds=dict(states),
        graph_attempts=len(solves),graph_applied=len(installs),graph_adoption_rate=len(installs)/len(solves) if solves else None,
        graph_solve_p50_s=q(times,.5),graph_solve_p95_s=q(times,.95),graph_total_p50_s=q(total,.5),graph_total_p95_s=q(total,.95),
        graph_reasons=dict(Counter(x['reason'] for x in solves)),graph_trigger_counts=dict(Counter(x['trigger'] for x in solves)),
        graph_left_right_switches=flips,all_path_left_right_switches=all_flips,graph_sides=sides,
        ec_checks=len(ec),ec_rejects=sum(not x['passed'] for x in ec),stationary_graph_installs=sum(x['stationary_xy'] for x in installs))
    return r
