"""Reuse20D execution audits; add new-cell decisions, end reasons and goal y."""
from pathlib import Path
from collections import Counter
import numpy as np
from nomad_phase20d.metrics import audit as previous_audit
from nomad_phase20.metrics import rows
from nomad_phase0.chunk_report import trace
from .history import HistorySnapshot
from .trigger import choose_ahead


def audit(run):
    run=Path(run);r=previous_audit(run);_,poses=trace(run);events=rows(run/'detour.jsonl');cache={}
    checks=[e for e in events if e['event']=='NEW_OBSTACLE_CONDITION']
    for e in checks:
        field=HistorySnapshot.load(e['snapshot']['file']);selected,info=choose_ahead(field,poses,e['tick'],cache)
        assert selected==e['component'];assert (selected is not None)==e['new_obstacle_ahead']
        if selected:np.testing.assert_array_equal(selected['u_ref'],e['u_ref'])
    triggers=[e for e in events if e['event']=='TRIGGER'];applied=[e for e in events if e['event']=='APPLIED'];ends=[e for e in events if e['event']=='END']
    passage=r['spawn_s']+r['box_passage_time_s'] if r.get('passed_box') else None
    def stage(e):return 'AFTER_PASSAGE' if passage is not None and e['simulation_time_s']>=passage else 'BEFORE_PASSAGE'
    r.update(no_new_obstacle_ahead_count=sum(e['reason']=='NO_NEW_OBSTACLE_AHEAD' for e in checks),new_obstacle_checks=len(checks),
        trigger_stages={s:sum(stage(e)==s for e in triggers) for s in ('BEFORE_PASSAGE','AFTER_PASSAGE')},
        no_progress_stages={s:sum(stage(e)==s and e['trigger']=='B' for e in triggers) for s in ('BEFORE_PASSAGE','AFTER_PASSAGE')},
        detour_applied_after_passage=sum(stage(e)=='AFTER_PASSAGE' for e in applied),detour_end_reasons=dict(Counter(e['reason'] for e in ends)),
        detour_durations_s=[e['execution_s'] for e in ends],goal_y_m=float(poses[-1,1]) if r['success'] else None,passage_absolute_s=passage)
    return r
