"""Offline path-constrained SE(2) graph; explicit Jacobians, no PP in the solve."""
import time

import numpy as np
from scipy.optimize import Bounds, minimize

from nomad_isaac.clearance import configured_obstacles
from nomad_isaac.handoff_audit import path_safety
from .graph_v2 import chord_values, fixed_entry, heading_chords
from .graph_v3 import side_labels
from .pure_pursuit import XYPath


def norm(x, axis=-1):
    # Analytic regularization only at singular lengths; feasible chords are >=5mm.
    return np.sqrt(np.sum(x*x, axis=axis)+1e-24)


def menger(points):
    """Signed circumcircle curvature and exact XY derivative for every triple."""
    u = points[1:-1]-points[:-2]; v = points[2:]-points[1:-1]; w = u+v
    lu, lv, lw = norm(u), norm(v), norm(w)
    cross = u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0]
    den = lu*lv*lw; k = 2*cross/den
    gu = 2*np.column_stack([v[:, 1], -v[:, 0]])/den[:, None]-k[:, None]*(u/lu[:, None]**2+w/lw[:, None]**2)
    gv = 2*np.column_stack([-u[:, 1], u[:, 0]])/den[:, None]-k[:, None]*(v/lv[:, None]**2+w/lw[:, None]**2)
    derivative = np.zeros((len(k), len(points), 2), dtype=np.result_type(points, float))
    for i in range(len(k)):
        derivative[i, i] = -gu[i]
        derivative[i, i+1] = gu[i]-gv[i]
        derivative[i, i+2] = gv[i]
    return k, derivative


class SignedDistanceField:
    """Precomputed AABB-union SDF, bilinear analytic gradient and error bound.

    Values are signed distance to boxes minus robot radius. Bilinear error is
    bounded by h/sqrt(2) using the 1-Lipschitz distance field. Grid build never
    uses unavailable obstacles; query contains no obstacle-dependent branches.
    """
    def __init__(self, config, resolution, padding):
        start = time.perf_counter()
        self.h = resolution; self.radius = config["agent_radius_m"]
        c = config["corridor"]
        self.origin = np.array([c["xmin"]-padding, -c["half_width"]-padding])
        upper = np.array([c["xmax"]+padding, c["half_width"]+padding])
        nx, ny = np.ceil((upper-self.origin)/self.h).astype(int)+1
        xx, yy = np.meshgrid(self.origin[0]+np.arange(nx)*self.h,
                             self.origin[1]+np.arange(ny)*self.h)
        distance = np.full((ny, nx), np.inf)
        self.obstacle_ids = []
        for box in configured_obstacles(config):
            self.obstacle_ids.append(box["id"])
            qx = np.abs(xx-box["center_xy_m"][0])-box["size_xyz_m"][0]/2
            qy = np.abs(yy-box["center_xy_m"][1])-box["size_xyz_m"][1]/2
            signed = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))+np.minimum(np.maximum(qx, qy), 0)
            distance = np.minimum(distance, signed)
        assert self.obstacle_ids
        self.values = distance-self.radius
        self.error_bound = self.h/np.sqrt(2)
        self.build_wall_s = time.perf_counter()-start

    def query(self, points):
        t = (points-self.origin)/self.h
        # The real cell is frozen for complex-step derivative verification only.
        cell = np.floor(t.real).astype(int)
        if np.any(cell < 0) or np.any(cell[:, 0] >= self.values.shape[1]-1) or np.any(cell[:, 1] >= self.values.shape[0]-1):
            raise ValueError("SDF query outside pre-registered field")
        x, y = cell.T; a, b = (t-cell).T
        f00, f10 = self.values[y, x], self.values[y, x+1]
        f01, f11 = self.values[y+1, x], self.values[y+1, x+1]
        value = (1-a)*(1-b)*f00+a*(1-b)*f10+(1-a)*b*f01+a*b*f11
        gradient = np.column_stack([((1-b)*(f10-f00)+b*(f11-f01))/self.h,
                                    ((1-a)*(f01-f00)+a*(f11-f10))/self.h])
        return value, gradient


def previous_stencil(previous_xy, boundary, current_xy):
    """Existing nearest projection plus normalized arclength, not point IDs/time."""
    path = XYPath(previous_xy)
    start, _ = path.project(np.array(boundary)[:2])
    length = np.r_[0., np.cumsum(np.linalg.norm(np.diff(current_xy, axis=0), axis=1))]
    if length[-1] <= 1e-12:
        raise ValueError("No current path arclength")
    return np.array([path.at(start+(path.s[-1]-start)*fraction) for fraction in length/length[-1]])


def selection_score(xy, original, boundary, protocol):
    b = np.asarray(boundary); direction = np.array([np.cos(b[2]), np.sin(b[2])])
    modification = float(np.mean(np.sum((xy-original)**2, axis=1))/protocol["selection_xy_scale_m"]**2)
    progress = float((xy[-1]-b[:2])@direction)
    deficit = max(0., protocol["progress_target_m"]-progress)/protocol["progress_target_m"]
    return {"total": modification+deficit**2, "modification": modification,
            "progress_cost": deficit**2, "endpoint_forward_progress_m": progress}


class GraphV4:
    def __init__(self, xy, boundary, previous_command, config, protocol, field, previous_xy=None):
        self.p = protocol; self.config = config; self.field = field
        self.xy = np.asarray(xy, dtype=float); self.boundary = np.asarray(boundary, dtype=float)
        self.chords = heading_chords(self.xy, protocol["minimum_heading_chord_m"])
        heading, self.chord_lengths = chord_values(self.xy, self.chords)
        self.initial = np.column_stack([self.xy, np.unwrap(heading)])
        self.lengths = np.linalg.norm(np.diff(self.xy, axis=0), axis=1)
        self.entry = fixed_entry(self.xy, self.boundary)
        self.weights = np.zeros(8)
        self.weights[self.entry["a"]] = 1-self.entry["fraction"]
        self.weights[self.entry["b"]] = self.entry["fraction"]
        self.forward = np.array([np.cos(boundary[2]), np.sin(boundary[2])])
        self.left = np.array([-np.sin(boundary[2]), np.cos(boundary[2])])
        if previous_command[0] <= 0:
            raise ValueError("Previous speed is zero: boundary curvature undefined")
        self.kappa_before = previous_command[1]/previous_command[0]
        if abs(self.kappa_before) > protocol["curvature_limit_m_inv"]:
            raise ValueError("Previous curvature exceeds the fixed path limit")
        self.previous_target = previous_stencil(previous_xy, boundary, self.xy) if previous_xy is not None else None
        self.sides = side_labels(self.xy, config)
        self.relative = []
        for i in range(7):
            t = self.initial[i, 2]; c, s = np.cos(t), np.sin(t)
            self.relative.append(np.r_[np.array([[c, s], [-s, c]])@(self.xy[i+1]-self.xy[i]),
                                        self.initial[i+1, 2]-t])
        count = protocol["segment_subdivisions"]
        self.sample_matrix = np.zeros((7*(count+1), 8))
        self.segment_ids = np.repeat(np.arange(7), count+1)
        for i in range(7):
            for j, fraction in enumerate(np.linspace(0, 1, count+1)):
                self.sample_matrix[i*(count+1)+j, i:i+2] = [1-fraction, fraction]
        trust = np.tile([protocol["xy_trust_region_m"], protocol["xy_trust_region_m"], np.pi], 8)
        self.bounds = Bounds(self.initial.ravel()-trust, self.initial.ravel()+trust)
        self.objective_calls = 0; self.constraint_calls = 0
        self._objective_cache = None; self._constraint_cache = None

    def residual_jacobian(self, x):
        poses = x.reshape(8, 3); p = self.p
        dtype = np.result_type(x, float)
        rows = []; jacobians = []; names = []
        def add(name, residual, jacobian):
            rows.append(np.atleast_1d(residual)); jacobians.append(np.atleast_2d(jacobian)); names.append(name)
        def angular(name, angle, derivatives, sigma):
            row = np.zeros(24, dtype=dtype)
            for k, value in derivatives.items(): row[k] = value*np.cos(angle/2)/sigma
            add(name, 2*np.sin(angle/2)/sigma, row)
        for i in range(8):
            j = np.zeros((2, 24), dtype=dtype); j[:, 3*i:3*i+2] = np.eye(2)/p["prior_sigma_xy_m"]
            add("fresh_prior_xy", (poses[i, :2]-self.xy[i])/p["prior_sigma_xy_m"], j)
            angular("fresh_prior_heading", poses[i, 2]-self.initial[i, 2], {3*i+2:1}, np.radians(p["prior_sigma_yaw_deg"]))
        for i in range(7):
            theta = poses[i, 2]; c, s = np.cos(theta), np.sin(theta)
            rotation = np.array([[c, s], [-s, c]])
            t = rotation@(poses[i+1, :2]-poses[i, :2]); sigma = p["relative_sigma_xy_m"]
            j = np.zeros((2, 24), dtype=dtype)
            j[:, 3*i:3*i+2] = -rotation/sigma; j[:, 3*i+3:3*i+5] = rotation/sigma
            j[:, 3*i+2] = np.array([t[1], -t[0]])/sigma
            add("relative_translation", (t-self.relative[i][:2])/sigma, j)
            angular("relative_heading", poses[i+1, 2]-poses[i, 2]-self.relative[i][2],
                    {3*i+2:-1, 3*i+5:1}, np.radians(p["relative_sigma_yaw_deg"]))
        entry = self.weights@poses
        j = np.zeros((2, 24), dtype=dtype)
        j[0, 0::3] = self.weights/p["boundary_sigma_xy_m"]
        j[1, 1::3] = self.weights/p["boundary_sigma_xy_m"]
        add("boundary_position", (entry[:2]-self.boundary[:2])/p["boundary_sigma_xy_m"], j)
        angular("boundary_heading", entry[2]-self.boundary[2],
                {3*i+2:self.weights[i] for i in range(8)}, np.radians(p["boundary_sigma_yaw_deg"]))
        for i, (a, b) in enumerate(self.chords):
            d = poses[b, :2]-poses[a, :2]; length = norm(d); unit = d/length
            tangent = np.array([np.cos(poses[i, 2]), np.sin(poses[i, 2])])
            derivative = (np.eye(2)-np.outer(unit, unit))/length
            sigma = np.radians(p["tangent_sigma_deg"])
            j = np.zeros((2, 24), dtype=dtype)
            j[:, 3*a:3*a+2] += derivative/sigma; j[:, 3*b:3*b+2] -= derivative/sigma
            j[:, 3*i+2] += np.array([-tangent[1], tangent[0]])/sigma
            add("heading_tangent", (tangent-unit)/sigma, j)
        if self.previous_target is not None:
            for i in range(8):
                j = np.zeros((2, 24), dtype=dtype); j[:, 3*i:3*i+2] = np.eye(2)/p["previous_sigma_xy_m"]
                add("previous_corrected_xy", (poses[i, :2]-self.previous_target[i])/p["previous_sigma_xy_m"], j)
        for side in self.sides.values():
            if side["sign"] is None:
                continue
            for crossing in side["crossings"]:
                a, b, fraction = crossing["a"], crossing["b"], crossing["fraction"]
                offset = (1-fraction)*poses[a, 1]+fraction*poses[b, 1]-side["center_y_m"]
                deficit = side["minimum_offset_m"]-side["sign"]*offset
                j = np.zeros(24, dtype=dtype)
                if deficit.real > 0:
                    j[3*a+1] = -side["sign"]*(1-fraction)/p["side_sigma_m"]
                    j[3*b+1] = -side["sign"]*fraction/p["side_sigma_m"]
                    add("definite_side_preservation", deficit/p["side_sigma_m"], j)
                else:
                    add("definite_side_preservation", 0.*deficit, j)
        deficit = p["progress_target_m"]-(poses[-1, :2]-self.boundary[:2])@self.forward
        j = np.zeros(24, dtype=dtype)
        if deficit.real > 0:
            j[-3:-1] = -self.forward/p["progress_target_m"]
            add("endpoint_progress", deficit/p["progress_target_m"], j)
        else:
            add("endpoint_progress", 0.*deficit, j)
        return np.concatenate(rows), np.vstack(jacobians), names, [len(r) for r in rows]

    def objective(self, x):
        if self._objective_cache is None or not np.array_equal(x, self._objective_cache[0]):
            self.objective_calls += 1
            r, j, _, _ = self.residual_jacobian(x)
            self._objective_cache = (x.copy(), .5*(r@r), j.T@r)
        return self._objective_cache[1:]

    def constraints(self, x):
        if self._constraint_cache is not None and np.array_equal(x, self._constraint_cache[0]):
            return self._constraint_cache[1:]
        self.constraint_calls += 1
        poses = x.reshape(8, 3); xy = poses[:, :2]; p = self.p
        dtype = np.result_type(x, float)
        g = []; jac = []
        def add(values, derivatives):
            g.append(np.atleast_1d(values)); jac.append(np.atleast_2d(derivatives))
        delta = np.diff(xy, axis=0); lengths = norm(delta)
        jl = np.zeros((7, 24), dtype=dtype)
        for i in range(7):
            jl[i, 3*i:3*i+2] = -delta[i]/lengths[i]
            jl[i, 3*i+3:3*i+5] = delta[i]/lengths[i]
        minimum = np.maximum(p["minimum_segment_m"], p["minimum_segment_ratio"]*self.lengths)
        add(lengths/minimum-1, jl/minimum[:, None])
        total_min = p["minimum_total_length_ratio"]*sum(self.lengths)
        add(sum(lengths)/total_min-1, jl.sum(axis=0)/total_min)
        for (a, b), original_length in zip(self.chords, self.chord_lengths):
            d = xy[b]-xy[a]; length = norm(d); minimum_chord = p["minimum_chord_ratio"]*original_length
            j = np.zeros(24, dtype=dtype); j[3*a:3*a+2] = -d/length/minimum_chord; j[3*b:3*b+2] = d/length/minimum_chord
            add(length/minimum_chord-1, j)
        kappa, jkxy = menger(xy); jk = np.zeros((6, 24), dtype=dtype)
        jk[:, 0::3] = jkxy[:, :, 0]; jk[:, 1::3] = jkxy[:, :, 1]
        kmax = p["curvature_limit_m_inv"]
        add(1-kappa/kmax, -jk/kmax); add(1+kappa/kmax, jk/kmax)

        points = self.sample_matrix@xy
        sdf, gradient = self.field.query(points)
        count = p["segment_subdivisions"]
        certified = sdf-self.field.error_bound-lengths[self.segment_ids]/(2*count)
        j = np.zeros((len(points), 24), dtype=dtype)
        j[:, 0::3] = gradient[:, 0, None]*self.sample_matrix
        j[:, 1::3] = gradient[:, 1, None]*self.sample_matrix
        j -= jl[self.segment_ids]/(2*count)
        scale = p["safety_constraint_scale_m"]
        add((certified-p["path_safety_target_m"])/scale, j/scale)
        c = self.config["corridor"]; radius = p["radius_m"]+p["corridor_margin_m"]
        for axis, sign, offset in [(0, 1, -c["xmin"]), (0, -1, c["xmax"]),
                                   (1, 1, c["half_width"]), (1, -1, c["half_width"])]:
            j = np.zeros((8, 24), dtype=dtype)
            j[np.arange(8), 3*np.arange(8)+axis] = sign/scale
            add((sign*xy[:, axis]+offset-radius)/scale, j)
        entry_delta = self.weights@xy-self.boundary[:2]
        j = np.zeros(24, dtype=dtype)
        j[0::3] = self.weights*self.forward[0]/p["entry_forward_min_m"]
        j[1::3] = self.weights*self.forward[1]/p["entry_forward_min_m"]
        add(entry_delta@self.forward/p["entry_forward_min_m"]-1, j)
        # Tangent-circle curvature at fixed B. Polynomial equality is equivalent
        # to kappa_B=old_w/old_v; forward entry prevents a zero-length solution.
        equality = (2*(entry_delta@self.left)-self.kappa_before*(entry_delta@entry_delta))/p["entry_equality_scale_m"]
        de = (2*self.left-2*self.kappa_before*entry_delta)/p["entry_equality_scale_m"]
        je = np.zeros((1, 24), dtype=dtype)
        je[0, 0::3] = self.weights*de[0]; je[0, 1::3] = self.weights*de[1]
        result = (np.concatenate(g), np.vstack(jac), np.atleast_1d(equality), je)
        self._constraint_cache = (x.copy(), *result)
        return result

    def solve(self):
        start = time.perf_counter()
        solution = minimize(lambda x: self.objective(x)[0], self.initial.ravel(),
            jac=lambda x: self.objective(x)[1], method="SLSQP", bounds=self.bounds,
            constraints=[{"type":"ineq", "fun":lambda x:self.constraints(x)[0],
                          "jac":lambda x:self.constraints(x)[1]},
                         {"type":"eq", "fun":lambda x:self.constraints(x)[2],
                          "jac":lambda x:self.constraints(x)[3]}],
            options={"maxiter":self.p["solver"]["maxiter"], "ftol":self.p["solver"]["ftol"], "disp":False})
        solver_wall = time.perf_counter()-start
        poses = solution.x.reshape(8, 3)
        g, _, eq, _ = self.constraints(solution.x)
        entry_delta = self.weights@poses[:, :2]-self.boundary[:2]
        kappa_entry = float(2*(entry_delta@self.left)/(entry_delta@entry_delta)) if np.linalg.norm(entry_delta) > 1e-12 else None
        exact = path_safety(poses[:, :2], self.config)
        constraint_ok = bool(g.min() >= -self.p["constraint_tolerance"] and abs(eq[0]) <= self.p["constraint_tolerance"]
            and kappa_entry is not None and abs(kappa_entry-self.kappa_before) <= self.p["entry_curvature_tolerance_m_inv"])
        exact_ok = exact["obstacle_clearance_m"] >= self.p["path_safety_target_m"]-1e-8 and exact["corridor_clearance_m"] >= self.p["corridor_margin_m"]-1e-8
        r, _, names, sizes = self.residual_jacobian(solution.x)
        costs = {}; offset = 0
        for name, size in zip(names, sizes):
            costs[name] = costs.get(name, 0.)+.5*float(r[offset:offset+size]@r[offset:offset+size]); offset += size
        return poses, {"success":bool(solution.success), "status":int(solution.status), "message":str(solution.message),
            "solver_wall_s":solver_wall, "solve_and_certificate_wall_s":time.perf_counter()-start,
            "iterations":int(solution.nit), "objective_evaluations":int(solution.nfev),
            "objective_calls":self.objective_calls, "constraint_calls":self.constraint_calls,
            "objective":float(solution.fun), "factor_costs":costs,
            "minimum_scaled_inequality":float(g.min()), "scaled_equality_error":float(abs(eq[0])),
            "entry_curvature_m_inv":kappa_entry, "previous_curvature_m_inv":self.kappa_before,
            "maximum_node_curvature_m_inv":float(np.max(np.abs(menger(poses[:, :2])[0]))),
            "constraints_satisfied":constraint_ok, "exact_path_certificate":exact, "exact_certificate_pass":bool(exact_ok),
            "feasible":bool(solution.success and constraint_ok and exact_ok),
            "selection_score":selection_score(poses[:, :2], self.xy, self.boundary, self.p),
            "previous_prior_applied":self.previous_target is not None,
            "derivatives":"explicit analytic objective/constraint Jacobians; no finite difference; no PP residual"}
