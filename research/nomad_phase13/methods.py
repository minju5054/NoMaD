"""Fixed two-pass smoothing. Only world paths and robot pose enter this module."""
import numpy as np
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase12.methods import freshest, TransitionState as Phase12State

METHODS = ('FRESHEST', 'FRESHEST+SMOOTH', 'FRESHEST+GRAPH-GF', 'TEMPORAL-ENSEMBLE')
GF = METHODS[2]


def smooth(xy, boundary):
    path = XYPath(xy)
    b = np.asarray(boundary, dtype=float)
    s, _ = path.project(b[:2])
    # Strictly after the projection; do not insert another projection waypoint.
    tail = path.points[path.s > s]
    points = np.vstack([b[:2], tail])
    if len(points) < 2:
        raise ValueError('NO_POINTS_AFTER_PROJECTION')
    original = points.copy()
    for _ in range(2):
        previous = points.copy()
        points[1:-1] = .25*previous[:-2] + .5*previous[1:-1] + .25*previous[2:]
    XYPath(points)  # Same nonzero/finite path requirement as original PP.
    return points, dict(projected_s_m=s, unsmoothed_suffix_xy=original.tolist(), passes=2,
                        weights=[.25, .5, .25], endpoints_fixed=True)


class FreshestState:
    def __init__(self, method):
        assert method in METHODS[:2]
        self.method = method

    def switch(self, samples, b, identifier, received_ns, now_ns):
        xy, detail = freshest(samples, b)
        detail = {**detail, 'kind': self.method}
        if self.method == 'FRESHEST+SMOOTH':
            try:
                xy, smoothing = smooth(xy, b)
                detail['smoothing'] = smoothing
            except ValueError as exc:
                xy = np.repeat(np.asarray(b)[None, :2], 2, axis=0)
                detail['invalid_reason'] = str(exc)
        return xy, detail


def transition_state(method):
    return FreshestState(method) if method in METHODS[:2] else Phase12State(method)
