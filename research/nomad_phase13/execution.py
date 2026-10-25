"""Opt-in factory. GF and temporal ensemble use the unchanged Phase12 classes."""
import json
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase4c.execution import AccelExecution
from nomad_phase12.gf_execution import GFExecution
from nomad_phase12.execution import BaselineExecution
from .methods import METHODS, GF, FreshestState


def make_execution(config, out):
    method = config['phase13_method']
    assert method in METHODS
    # Scene/goal/obstacle/corridor metadata stays exclusively in the evaluator.
    control = dict(phase12_method=method, phase4c_method='GRAPH' if method == GF else 'CURV', plant_alpha='inf')
    if method == GF:
        return GFExecution(control, out)
    if method == 'TEMPORAL-ENSEMBLE':
        return BaselineExecution(control, out)
    return FreshestExecution(control, out)


class FreshestExecution(AccelExecution):
    def __init__(self, config, out):
        assert set(config) == {'phase12_method', 'phase4c_method', 'plant_alpha'}
        super().__init__(config, out)
        self.named_method = config['phase12_method']
        self.state = FreshestState(self.named_method)
        self.last_application_ns = None
        self.applications = (out/'phase6_applications.jsonl').open('x')
        self.oracle = (out/'overnight_oracle.jsonl').open('x')

    def apply(self, core, refresh, switch):
        before = list(self.last_command)
        original = None
        if switch is not None:
            original = switch['chunk']
            samples = np.array([local_to_world(np.asarray(x), np.asarray(switch['observation_pose']))
                                for x in switch['overnight_metric_samples']])
            xy, detail = self.state.switch(samples, core.pose, switch['id'],
                                           switch['received_monotonic_ns'], refresh['monotonic_ns'])
            try:
                XYPath(xy)
                valid = True
            except ValueError:
                valid = False
            switch['chunk'] = {**original, 'world_xy_m': xy.tolist(), 'path_valid': valid}
            switch['phase12'] = dict(method=self.named_method, detail=detail,
                                     applied_initial_world_xy=xy.tolist(), oracle_used=False)
        try:
            super().apply(core, refresh, switch)
        finally:
            if original is not None:
                switch['chunk'] = original
        refresh['phase13_method'] = self.named_method
        if switch is not None:
            path = self.follower.path if self.follower else None
            s, d = path.project(core.pose[:2]) if path else (None, None)
            row = dict(tick=round(refresh['simulation_time_s']*72), simulation_time_s=refresh['simulation_time_s'],
                monotonic_ns=refresh['monotonic_ns'], id=self.active_id, pose=core.pose.tolist(),
                kind=self.named_method, graph_job_id=None, selected_sample=detail['selected_sample'],
                world_xy=path.points.tolist() if path else None, path_length_m=float(path.s[-1]) if path else None,
                projected_arclength_m=s, projection_distance_m=d, staleness=float(s/path.s[-1]) if path else None,
                before_vw=before, after_vw=list(self.last_command), abs_dw=abs(self.last_command[1]-before[1]), oracle_used=False)
            self.applications.write(json.dumps(row)+'\n')
            self.applications.flush()
            self.last_application_ns = refresh['monotonic_ns']

    def close(self):
        self.oracle.close()
        self.applications.close()
        super().close()
