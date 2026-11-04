"""Frozen Phase24-R audit plus three preregistered return/localization metrics."""
import csv
from pathlib import Path
import numpy as np
from nomad_phase24r.online_metrics import audit as frozen_audit, rows


def return_metrics(time, y, intervals, passage, topology):
    time, y = np.asarray(time), np.asarray(y)
    inside = np.zeros(len(time), dtype=bool)
    for start, end in intervals:
        inside |= (time >= start) & (time <= end)
    post = None
    if passage is not None and time[0] <= passage+5 <= time[-1]+1e-9:
        post = abs(float(np.interp(passage+5, time, y)))
    progress = []
    def closest(t):
        available = [r for r in topology if r['time_s'] <= t+1e-9]
        return available[-1]['closest'] if available else None
    for _, end in intervals:
        before = closest(end)
        after = closest(min(end+5, time[-1]))
        final = closest(time[-1])
        progress.append(dict(handover_s=end, window_end_s=min(end+5, float(time[-1])),
            full_5s_observed=bool(time[-1] >= end+5), closest_at_handover=before,
            closest_after=after, delta_5s=None if before is None or after is None else after-before,
            delta_until_run_end=None if before is None or final is None else final-before))
    return dict(detour_max_abs_y_m=float(np.max(np.abs(y[inside]))) if inside.any() else None,
                post_passage_5s_abs_y_m=post, post_detour_closest_progress=progress)


def audit(run):
    run = Path(run)
    result = frozen_audit(run)
    data = list(csv.DictReader((run/'agent_trajectory.csv').open()))
    time = [float(r['simulation_time_s']) for r in data]
    y = [float(r['y_m']) for r in data]
    events = rows(run/('g_events.jsonl' if result['method']=='G' else 'detour.jsonl'))
    intervals, start = [], None
    for e in events:
        applied = (e['event']=='APPLY' and e.get('mode')=='DETOUR' and e.get('output_type')!='STOP') if result['method']=='G' else e['event']=='APPLIED'
        ended = e['event']==('MODE_EXIT' if result['method']=='G' else 'END')
        if applied:
            start = e['simulation_time_s']
        if ended and start is not None:
            intervals.append((start, e['simulation_time_s']))
            start = None
    # A detour interrupted by run termination has no handover; include it only
    # in excursion measurement, not in post-handover localization statistics.
    topology = [dict(time_s=e['application_sim_s'], closest=e['topomap']['closest_node'])
                for e in rows(run/'events.jsonl') if e.get('topomap') and 'application_sim_s' in e]
    topology.sort(key=lambda e:e['time_s'])
    extra = return_metrics(time, y, intervals, result['box_passage_time_s'], topology)
    if start is not None:
        values=[abs(yy) for t,yy in zip(time,y) if t>=start]
        if values:
            extra['detour_max_abs_y_m']=max(max(values),extra['detour_max_abs_y_m'] or 0.)
    result.update(extra)
    if result['method']=='G':
        inputs = rows(run/'g_events.jsonl')
        result['detour_return_lines']=[r['return_line'] for r in inputs if r['event']=='MODE_ENTER']
    return result
