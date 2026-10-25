"""Reuse the saved-data command/pose/RGB/clearance audit; add checkpoint metrics."""
import json
from pathlib import Path
import numpy as np
from nomad_isaac.common import sha256_file
from nomad_isaac.async_report import rows
from nomad_phase0.chunk_report import trace
from nomad_phase12.metrics import baseline_audit
from .methods import METHODS, GF, transition_state
from .config import protocol


def checkpoint(scene, records, poses, failure_time=None):
    box = next(b for b in scene['obstacles'] if b['id'] == protocol()['checkpoint']['obstacle_id'])
    threshold = float(box['center_xy_m'][0] + box['size_xyz_m'][0]/2 + .30)
    times = np.array([float(r['simulation_time_s']) for r in records])
    crossings = np.flatnonzero(poses[:, 0] >= threshold)
    k = int(crossings[0]) if len(crossings) else None
    if k is not None and failure_time is not None and times[k] >= failure_time:
        k = None
    duration = float(times[k]) if k is not None else None
    distance = float(np.linalg.norm(np.diff(poses[:k+1, :2], axis=0), axis=1).sum()) if k is not None else None
    return dict(checkpoint_x_m=threshold, checkpoint_tick=k, checkpoint_time_s=duration,
                checkpoint_distance_m=distance, checkpoint_mean_speed_m_s=distance/duration if duration else None)


def extra_metrics(run, result):
    run = Path(run)
    scene = json.loads((run/'scenario.json').read_text())
    records, poses = trace(run)
    failure_time = result['duration_s'] if result.get('geometric_overlap') or result.get('corridor_violation') else None
    out = checkpoint(scene, records, poses, failure_time)
    controls = rows(run/'controller.jsonl')
    times = np.array([c['simulation_time_s'] for c in controls])
    dt = np.maximum(0., np.r_[times[1:], result['duration_s']] - times)
    active = np.array([c['pure_pursuit']['stop_reason'] is None for c in controls])
    slow = np.array([(c['stage2'].get('v_target_m_s') or .3) < .2-1e-12 for c in controls])
    out['curv_slow_time_fraction'] = float(dt[active & slow].sum()/dt[active].sum()) if dt[active].sum() else None
    return out


def audit(run, run_id, offset, delay):
    run = Path(run)
    c = json.loads((run/'scenario.json').read_text())
    m = c['phase13_method']
    assert m in METHODS and 35 <= int(run_id[-2:]) <= 46 and delay == .75
    assert c['phase12_method'] == m and c['overnight_method'] == 'CURV'
    assert json.loads((run/'phase13_protocol.json').read_text()) == protocol()
    assert json.loads((run/'provenance.json').read_text())['phase13_method'] == m
    r = baseline_audit(run, run_id, offset, delay, transition_factory=transition_state,
                       path_baselines=tuple(x for x in METHODS if x != GF))
    assert not rows(run/'overnight_oracle.jsonl')
    if m != GF:
        assert not rows(run/'stage2_graph.jsonl')
    assert all(e['phase12']['oracle_used'] is False for e in rows(run/'events.jsonl'))
    r.update(extra_metrics(run, r))
    r['input_log_sha256']['phase13_protocol.json'] = sha256_file(run/'phase13_protocol.json')
    return r
