"""Only new factor: squared endpoint distance to the observed approach line."""
import types
import numpy as np
from nomad_phase24r.graph import GraphR, normal_inputs, fan_paths
from nomad_phase24r.safety import PlanningField
from nomad_phase23o3 import graph as frozen_worker


def return_line(poses, tick, u_ref, direction):
    """Anchor at depth component birth, or actual detour entry without one."""
    poses = np.asarray(poses, dtype=float)
    u = np.asarray(u_ref, dtype=float)
    np.testing.assert_allclose(np.linalg.norm(u), 1., atol=1e-12)
    component = direction.get('component')
    anchor_tick = int(component['t_new_tick']) if component is not None else int(tick)
    assert 0 <= anchor_tick <= tick < len(poses)
    return dict(anchor_world=poses[anchor_tick, :2].tolist(), u_ref=u.tolist(),
                anchor_tick=anchor_tick, detour_entry_tick=int(tick),
                source='COMPONENT_T_NEW_POSE' if component is not None else 'DETOUR_ENTRY_POSE',
                sigma_m=.30, weight=1.)


class GraphR2(GraphR):
    def __init__(self, B, v0, candidates, sigma, field, weights, deadline_ns, kinematic_sigma=.03):
        super().__init__(B, v0, candidates, sigma, field, weights, deadline_ns, kinematic_sigma)
        self.return_cache = None
        if self.mode == 'DETOUR':
            line = weights['return_line']
            np.testing.assert_allclose(line['u_ref'], weights['u_ref'], atol=1e-12)
            assert line['sigma_m'] == .30 and line['weight'] == 1.
            self.line_anchor = (np.asarray(line['anchor_world']) - self.B[:2]) @ self.R
            self.line_normal = np.array([-self.u[1], self.u[0]])

    def return_term(self, x):
        if self.mode != 'DETOUR':
            return 0., np.zeros_like(x)
        p, _, _ = self.unpack(x)
        error = float((p[-1] - self.line_anchor) @ self.line_normal)
        return (error / .30)**2, (2 * error / .30**2) * (self.line_normal @ self.jp[-1])

    def objective(self, x):
        self.check()
        if self.mode == 'NORMAL':
            return super().objective(x)
        if self.return_cache is None or not np.array_equal(x, self.return_cache[0]):
            value, gradient = super().objective(x)
            extra, jacobian = self.return_term(x)
            self.return_cache = (np.array(x, copy=True), (value + extra, gradient + jacobian))
        return self.return_cache[1]


_worker = types.FunctionType(frozen_worker.worker.__code__,
    dict(frozen_worker.worker.__globals__, U3Graph=GraphR2, Snapshot=PlanningField),
    argdefs=frozen_worker.worker.__defaults__)


def worker(payload, channel):
    return _worker(payload, channel)
