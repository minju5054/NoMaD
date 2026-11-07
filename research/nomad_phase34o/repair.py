"""Only add the frozen R3 clearance residual to the frozen R2 objective."""
from types import FunctionType
import numpy as np
from nomad_phase20.repair import RepairGraphR2, solve_sample as original_sample


class RepairGraphCLR(RepairGraphR2):
    def residual_jacobian(self, x):
        residual, jacobian = super().residual_jacobian(x)
        # Same nine closed inspection points/segment as R2 hard constraints;
        # same .15/.05, multiplicity and .5*r.T*r convention as frozen R3.
        distance, gradient = self.field.query(self.sample_matrix @ self.points(x))
        clearance = np.maximum(0., .15 - distance) / .05
        derivative = np.zeros((63, 14))
        derivative[:, 0::2] = -gradient[:, 0, None] * self.sample_matrix[:, 1:] / .05
        derivative[:, 1::2] = -gradient[:, 1, None] * self.sample_matrix[:, 1:] / .05
        derivative[distance >= .15] = 0.
        return np.r_[residual, clearance], np.vstack([jacobian, derivative])


# Reuse exact initializer, SLSQP options, hard constraints, certificate,
# diagnostics and acceptance without copying/modifying frozen source.
solve_sample = FunctionType(original_sample.__code__,
    dict(original_sample.__globals__, RepairGraphR2=RepairGraphCLR),
    original_sample.__name__, original_sample.__defaults__, original_sample.__closure__)
