"""Reuse20D audits and add trigger-gate replay and before/after passage counts."""
import json
from pathlib import Path
import numpy as np
from nomad_phase20d.metrics import audit as base_audit
from nomad_phase20.metrics import rows
from nomad_phase15b.depth import Snapshot
from .trigger import obstacle_ahead


def audit(run):
    run=Path(run);r=base_audit(run);log=rows(run/'detour.jsonl');checks=[e for e in log if e['event']=='OBSTACLE_CONDITION']
    for e in checks:
        field=Snapshot.load(e['snapshot']['file']);actual=obstacle_ahead(field,e['pose'],e['u_ref'])
        assert actual['obstacle_ahead']==e['obstacle_ahead'] and actual['occupied_cells']==e['occupied_cells']
        assert e['reason']==('OBSTACLE_AHEAD' if e['obstacle_ahead'] else 'NO_OBSTACLE_AHEAD')
        assert e['snapshot']['publication_monotonic_ns']<=e['evaluated_monotonic_ns']
    passage=r['spawn_s']+r['box_passage_time_s'] if r.get('passed_box') else None
    def stage(e):return 'AFTER_PASSAGE' if passage is not None and e['simulation_time_s']>=passage else 'BEFORE_PASSAGE'
    triggers=[e for e in log if e['event']=='TRIGGER'];applications=[e for e in log if e['event']=='APPLIED']
    by_tick={e['tick']:e for e in checks}
    for t in triggers:
        if t['trigger']=='B':assert by_tick[t['evaluation_tick']]['obstacle_ahead'] and t['obstacle_condition']=={k:v for k,v in by_tick[t['evaluation_tick']].items() if k in ('obstacle_ahead','occupied_cells','nearest_forward_m','rectangle_world','snapshot')}
    r.update(no_obstacle_ahead_count=sum(e['reason']=='NO_OBSTACLE_AHEAD' for e in checks),obstacle_condition_checks=len(checks),
        trigger_stages={s:sum(stage(e)==s for e in triggers) for s in ('BEFORE_PASSAGE','AFTER_PASSAGE')},
        no_progress_stages={s:sum(stage(e)==s and e['trigger']=='B' for e in triggers) for s in ('BEFORE_PASSAGE','AFTER_PASSAGE')},
        blocked_stages={s:sum(stage(e)==s and e['reason']=='NO_OBSTACLE_AHEAD' for e in checks) for s in ('BEFORE_PASSAGE','AFTER_PASSAGE')},
        detour_applied_after_passage=sum(stage(e)=='AFTER_PASSAGE' for e in applications),passage_absolute_s=passage)
    return r
