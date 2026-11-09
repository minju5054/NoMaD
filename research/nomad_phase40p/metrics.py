"""Frozen evaluator plus descriptive planner/escape/wait telemetry."""
from collections import Counter
from pathlib import Path
from nomad_phase35.metrics import audit as frozen_audit,q
from nomad_phase32.report import lines


def audit(root):
    root=Path(root);r=frozen_audit(root);r['method']='OURS-N'
    events=lines(root/'phase40p.jsonl');ticks=[e for e in events if e['event']=='TICK']
    installs=[e for e in events if e['event']=='APPLIED']
    escapes=[e for e in events if e['event']=='ESCAPE_INSTALL']
    unique_escapes={e['job_id']:e for e in escapes}
    checks=lines(root/'exec_cert.jsonl')
    r.update(planner_installations=dict(Counter(e['kind'] for e in installs)),
             escape_installations=len(escapes),consecutive_escape_installations=sum(e['consecutive'] for e in escapes),
             escape_times_s=[e['t_escape_s'] for e in escapes],escape_time_p50_s=q([e['t_escape_s'] for e in escapes],.5),
             escape_time_p95_s=q([e['t_escape_s'] for e in escapes],.95),
             escape_time_reasons=dict(Counter(e['time_reason'] for e in escapes)),
             escape_two_second_cap_installations=sum(e['cap_applied'] for e in escapes),
             escape_two_second_cap_jobs=sum(e['cap_applied'] for e in unique_escapes.values()),
             escape_periodic_rejections=sum(e['event']=='CHECK' and e.get('escape_active',False) and e.get('scope')=='PERIODIC' and not e['passed'] for e in checks),
             waiting_seconds=sum(e['waiting'] for e in ticks)/72,
             stopped_while_waiting_seconds=sum(e['waiting'] and e['physical_stop'] for e in ticks)/72,
             result_dispositions=dict(Counter(e['disposition'] for e in events if e['event']=='RESULT')))
    return r
