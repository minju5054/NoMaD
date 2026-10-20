"""Independent geometric follower. Inputs contain no obstacles, goal or timestamps."""
import math

import numpy as np


class XYPath:
    def __init__(self, points):
        p = np.asarray(points, dtype=float)
        if p.ndim != 2 or p.shape[1] != 2 or len(p) < 2 or not np.isfinite(p).all():
            raise ValueError("Expected at least two finite world XY points")
        p = p[np.r_[True, np.linalg.norm(np.diff(p, axis=0), axis=1) > 1e-12]]
        if len(p) < 2:
            raise ValueError("Path has no nonzero segment")
        self.points = p
        self.delta = np.diff(p, axis=0)
        self.lengths = np.linalg.norm(self.delta, axis=1)
        self.s = np.r_[0., np.cumsum(self.lengths)]

    def project(self, xy):
        fraction = np.clip(np.sum((np.asarray(xy)-self.points[:-1])*self.delta, axis=1)
                           / self.lengths**2, 0., 1.)
        candidates = self.points[:-1] + fraction[:, None]*self.delta
        distance2 = np.sum((candidates-np.asarray(xy))**2, axis=1)
        index = int(np.argmin(distance2))
        return float(self.s[index]+fraction[index]*self.lengths[index]), float(math.sqrt(distance2[index]))

    def at(self, arclength):
        s = float(np.clip(arclength, 0., self.s[-1]))
        index = min(int(np.searchsorted(self.s, s, side="right")-1), len(self.delta)-1)
        return self.points[index] + (s-self.s[index])/self.lengths[index]*self.delta[index]


class PurePursuit:
    def __init__(self, xy, settings):
        self.path = XYPath(xy)
        self.settings = dict(settings)
        self.progress = 0.
        assert self.settings["lookahead_m"] > 0
        assert 0 < self.settings["speed_m_s"] <= self.settings["max_v_m_s"] == .2
        assert self.settings["max_abs_w_rad_s"] == .4
        assert self.settings["endpoint_tolerance_m"] > 0

    def control(self, pose):
        pose = np.asarray(pose, dtype=float)
        if pose.shape != (3,) or not np.isfinite(pose).all():
            raise ValueError("Expected finite SE(2) pose")
        projected, cte = self.path.project(pose[:2])
        self.progress = max(self.progress, projected)
        target_s = min(self.path.s[-1], self.progress+self.settings["lookahead_m"])
        target = self.path.at(target_s)
        dx, dy = target-pose[:2]
        c, s = math.cos(pose[2]), math.sin(pose[2])
        local_x, local_y = c*dx+s*dy, -s*dx+c*dy
        endpoint_stop = np.linalg.norm(pose[:2]-self.path.points[-1]) <= self.settings["endpoint_tolerance_m"]
        raw_v = 0. if endpoint_stop else self.settings["speed_m_s"]
        raw_w = 0. if endpoint_stop or dx*dx+dy*dy < 1e-24 else raw_v*2*local_y/(dx*dx+dy*dy)
        v = float(np.clip(raw_v, 0., self.settings["max_v_m_s"]))
        w = float(np.clip(raw_w, -self.settings["max_abs_w_rad_s"], self.settings["max_abs_w_rad_s"]))
        return (v, w), {"progress_m": self.progress, "target_s_m": float(target_s),
                        "target_x_m": float(target[0]), "target_y_m": float(target[1]),
                        "target_local_x_m": float(local_x), "target_local_y_m": float(local_y),
                        "cross_track_error_m": cte, "raw_v_m_s": float(raw_v), "raw_w_rad_s": float(raw_w),
                        "v_clipped": bool(abs(raw_v-v) > 1e-12), "w_clipped": bool(abs(raw_w-w) > 1e-12),
                        "endpoint_stop": bool(endpoint_stop)}
