"""Simulation tick deadlines and predictions using the frozen NA controller."""
import copy
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase16.execution import stop_command


def application_tick(dispatch_tick):
    # 0.75 seconds = 54 integration ticks; ceiling to the 9 Hz control grid.
    return ((int(dispatch_tick) + 54 + 7) // 8) * 8


def predict(controller, pose, vw, dispatch_tick, target_tick):
    """Current command has already been computed at dispatch_tick.

    Hold it until the next control tick, then invoke exactly the frozen
    controller. No separate motion approximation or future candidate is used.
    """
    assert target_tick >= dispatch_tick and dispatch_tick % 8 == 0
    ctl = copy.deepcopy(controller)
    q = np.asarray(pose, float).copy()
    v, w = map(float, vw)
    poses = [q.copy()]
    commands = []
    for tick in range(dispatch_tick, target_tick):
        if tick > dispatch_tick and tick % 8 == 0:
            if ctl is None:
                v, w = stop_command(v)
            else:
                (v, w), diag = ctl.control(q, v)
                if diag['completed']:
                    v, w = stop_command(v)
                    ctl = None
        q = integrate_se2(q, v, w, 1 / 72)
        poses.append(q.copy()); commands.append([v, w])
    return dict(pose=q.tolist(), vw=[float(v), float(w)],
                poses=np.asarray(poses).tolist(), commands=commands,
                dispatch_tick=int(dispatch_tick), apply_tick=int(target_tick))


def disposition(job, result, tick, control_ns, superseded=False):
    if superseded:
        return 'SUPERSEDED'
    if tick < job['apply_tick']:
        return 'WAIT'
    if tick > job['apply_tick']:
        return 'STALE'
    if result is None or result.get('parent_received_ns', control_ns + 1) > control_ns:
        return 'TIMEOUT'
    if result.get('error'):
        return 'WORKER_ERROR'
    return 'ACCEPTED' if result.get('selected_sample') is not None else 'REJECTED'
