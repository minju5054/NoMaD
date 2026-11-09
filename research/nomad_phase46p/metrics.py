from pathlib import Path
from collections import Counter
from nomad_phase45p.metrics import audit as frozen_audit
from nomad_phase32.report import lines
from .triggers import evaluate


def waiting(root,duration):
    events=lines(Path(root)/'phase20_commands.jsonl');states=Counter()
    for i,e in enumerate(events):
        stop=min(duration,events[i+1]['time_s'] if i+1<len(events) else duration)
        states[e['source']]+=max(0.,stop-e['time_s'])
    return dict(planner_wait_s=states['REPAIR_WAIT']+states['DETOUR_WAIT'],r2_wait_s=states['REPAIR_WAIT'],
                r3_wait_s=states['DETOUR_WAIT'],stop_wait_s=states['STOP_WAIT'])


def augment(row):
    row.update(waiting(row['output'],row['duration_s']))
    row['trigger_b_analysis']=evaluate(row['output'],row)
    row['trigger_b_counts']=dict(Counter(e['classification'] for e in row['trigger_b_analysis']))
    row['false_trigger_r3_installs']=sum(e['classification']=='NON_BOX' and e['r3_installed'] for e in row['trigger_b_analysis'])
    row['total_stopped_s']=row['stopped_fraction']*row['duration_s']
    return row


def audit(root):
    r=frozen_audit(root);r['method']='OURS-B-ONLY+HMM'
    assert r['r2_installations']==0
    for e in lines(Path(root)/'repair_pool_jobs.jsonl'):assert e['kind']=='R3'
    for e in lines(Path(root)/'detour.jsonl'):
        if e['event']=='TRIGGER':assert e['trigger']=='B' and e.get('trigger_component_evidence')
    augment(r)
    assert all(e['classification']!='UNMEASURED' for e in r['trigger_b_analysis'])
    for e in r['node_errors']:e['cohort']='Phase46-P'
    return r
