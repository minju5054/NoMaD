"""Graph v4 subclass: identical geometry-free factors/Jacobians, oracle rows disabled.

No scene config or field argument exists. Non-oracle initialization/constraint
expressions are mirrored from protected v4, with parity tests against v4 rows.
The original residual and Phase5 flag-enabled SLSQP solve are inherited.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import Bounds
from nomad_phase0.graph_v4 import norm,menger,previous_stencil
from nomad_phase0.graph_v2 import chord_values,fixed_entry,heading_chords
from nomad_phase5.graph import FlagGraphV4

FLAGS=dict(previous_prior=True,obstacle_sdf=False,corridor=False,exact_certificate=False,boundary_curvature=True)

def graph_protocol():
    p=json.loads(Path(__file__).parents[1].joinpath('nomad_phase0/graph_v4_protocol.json').read_text())
    p['phase12_gf_flags']=dict(FLAGS)
    return p

def assert_protocol(p):
    # Exact keys/values from the protected numerical protocol: scene geometry
    # cannot be smuggled through a config, field, nested dict or unknown flag.
    assert p==graph_protocol(), 'Only unchanged v4 constants plus fixed GF flags are accepted'

class GraphGF(FlagGraphV4):
    def __init__(self, xy, boundary, previous_command, protocol, previous_xy=None):
        assert_protocol(protocol)
        for value,shape in ((xy,(8,2)),(boundary,(3,)),(previous_command,(2,))):
            assert not isinstance(value,dict), 'Geometry objects forbidden'
            a=np.asarray(value,dtype=float)
            assert a.shape==shape and np.isfinite(a).all()
        if previous_xy is not None:
            assert not isinstance(previous_xy,dict)
            a=np.asarray(previous_xy,dtype=float)
            assert a.shape==(8,2) and np.isfinite(a).all()
        self.flags = dict(protocol["phase12_gf_flags"])
        self.p = protocol
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
        self.sides = {}  # No geometry-derived side labels in oracle-free control.
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

    def certificate(self, poses):
        return {'status':'NOT_PERFORMED','reason':'oracle-free control; evaluation only after execution'}, True

    def solve(self):
        poses,result=super().solve()
        result.update(certificate_scope='NONE_ORACLE_FREE',exact_certificate_pass=None,
                      phase12_gf_flags=dict(self.flags))
        result.pop('phase5_flags',None)
        assert result['feasible']==bool(result['success'] and result['constraints_satisfied'])
        return poses,result
