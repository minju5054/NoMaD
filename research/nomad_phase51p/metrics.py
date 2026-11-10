"""Report-only interval reconstruction; never changes EC or its fallback."""
import csv,json
from pathlib import Path
import numpy as np
from nomad_phase47c.metrics import audit as frozen_audit
from nomad_phase24r.online_metrics import rows

def ec_exhausted(events,duration):
    active=None;intervals=[];calls=0
    for e in events:
        t=float(e.get('simulation_time_s',0.));assert 0<=t<=duration+1e-8
        if e['event']=='FALLBACK' and e.get('reason')=='NORMAL_NO_EC_SAFE_CANDIDATE':
            calls+=1
            if active is None:active=t
        elif e['event']=='INSTALL' and active is not None:
            if t>active:intervals.append(dict(start_s=active,end_s=t,duration_s=t-active,end_reason='EC_PASS_INSTALLED'))
            active=None
    if active is not None and duration>active:intervals.append(dict(start_s=active,end_s=duration,duration_s=duration-active,end_reason='RUN_ENDED'))
    return dict(ec_all_candidates_rejected_s=sum(x['duration_s'] for x in intervals),
        ec_all_candidates_rejected_max_s=max((x['duration_s'] for x in intervals),default=0.),
        ec_all_candidates_rejected_episodes=len(intervals),ec_exhaustion_calls=calls,ec_exhausted_intervals=intervals)

def saved_times(root,duration):
    root=Path(root);data=list(csv.DictReader((root/'agent_trajectory.csv').open()))
    t=np.array([float(r['simulation_time_s']) for r in data]);v=np.array([float(r['v_m_s']) for r in data]);dt=np.diff(t)
    assert np.all(dt>0) and abs(t[-1]-duration)<1e-9
    detail=ec_exhausted(rows(root/'exec_cert.jsonl'),duration)
    physical=0.
    for x in detail['ec_exhausted_intervals']:
        overlap=np.maximum(0,np.minimum(t[1:],x['end_s'])-np.maximum(t[:-1],x['start_s']))
        physical+=float(overlap[np.abs(v[1:])<.01].sum())
    return dict(detail,stopped_s=float(dt[np.abs(v[1:])<.01].sum()),ec_exhausted_physically_stopped_s=physical)

def audit(root):
    root=Path(root);r=frozen_audit(root);c=json.loads((root/'scenario.json').read_text())
    assert c['phase51p'] and c['phase47c_method']=='OURS-DETOUR+HMM'
    summary=json.loads((root/'summary.json').read_text());delay=c['phase51p_delay_s']
    assert summary['delivery_delay']['configured_additional_s']==delay
    assert json.loads((root/'delivery_delay_protocol.json').read_text())['configured_additional_s']==delay
    for req in rows(root/'requests.jsonl'):assert req['additional_delivery_delay_s']==delay
    assert r['g_dispatches']==0 and r['detour_applied_count']==0
    assert not [e for e in rows(root/'repair.jsonl') if e['event'] in ('DISPATCH','TRIGGER')]
    r.update(saved_times(root,r['duration_s']))
    r.update(base_scene=r['scene'],scene=c['phase51p_level'],condition=c['phase51p_condition'],delay_s=delay)
    return r
