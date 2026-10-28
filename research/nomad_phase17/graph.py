"""Only an analytic soft residual is added to the unchanged DepthGraph."""
import numpy as np
from nomad_phase15b.graph import DepthGraph

D_PREF_M = .15
SIGMA_CLEARANCE_M = .05


class ClearanceGraph(DepthGraph):
    def clearance_residual(self, x):
        xy = x.reshape(8, 3)[:, :2]
        distance, gradient = self.field.query(self.sample_matrix @ xy)
        active = distance < D_PREF_M
        residual = np.maximum(0., D_PREF_M-distance)/SIGMA_CLEARANCE_M
        jac = np.zeros((len(distance), 24))
        jac[:, 0::3] = -gradient[:, 0, None]*active[:, None]*self.sample_matrix/SIGMA_CLEARANCE_M
        jac[:, 1::3] = -gradient[:, 1, None]*active[:, None]*self.sample_matrix/SIGMA_CLEARANCE_M
        return residual, jac

    def residual_jacobian(self, x):
        r, j, names, sizes = super().residual_jacobian(x)
        c, cj = self.clearance_residual(x)
        return np.r_[r, c], np.vstack([j, cj]), names+['depth_clearance_preference'], sizes+[len(c)]

    def solve(self):
        poses, result = super().solve()
        c, _ = self.clearance_residual(poses.ravel())
        result.update(clearance_preference_active=bool(np.any(c > 0)),
                      clearance_preference_active_points=int(np.sum(c > 0)),
                      clearance_preference_total_points=len(c),
                      clearance_preference_target_m=D_PREF_M,
                      clearance_preference_sigma_m=SIGMA_CLEARANCE_M)
        return poses, result
