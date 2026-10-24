"""Unchanged Phase5 GRAPH/CURV executor plus a SELECT-only switch hook."""
import json
import numpy as np
from nomad_phase0.chunk_execution import describe_chunk
from nomad_phase4c.execution import AccelExecution
from .selection import select


class Phase6Execution(AccelExecution):
    def __init__(self, config, out, client=None):
        super().__init__(config, out, client)
        self.phase6_method = config['phase6_method']
        self.applications = (out/'phase6_applications.jsonl').open('x')

    def apply(self, core, refresh, switch):
        before = list(self.last_command)
        original = None
        detail = None
        if switch is not None and self.phase6_method == 'SELECT':
            samples = np.asarray(switch['phase6_metric_samples'])
            _,detail = select(samples, switch['observation_pose'], core.pose, self.config)
            original = switch['chunk']
            switch['chunk'] = describe_chunk(samples[detail['selected_sample']], switch['observation_pose'])
        try:
            super().apply(core, refresh, switch)
        finally:
            if original is not None:
                switch['chunk'] = original
        refresh['phase6_method'] = self.phase6_method
        if switch is not None:
            switch['phase6_method'] = self.phase6_method
            if detail is not None:
                switch['phase6_selection'] = detail
                refresh['phase6_selection'] = detail
        graph_job = refresh['stage2']['graph_applied_job']
        if switch is not None or graph_job is not None:
            path = self.follower.path if self.follower is not None else None
            s,d = path.project(core.pose[:2]) if path is not None else (None,None)
            row = dict(tick=round(refresh['simulation_time_s']*72), simulation_time_s=refresh['simulation_time_s'],
                monotonic_ns=refresh['monotonic_ns'], id=self.active_id, pose=core.pose.tolist(),
                kind='GRAPH' if graph_job is not None else 'SELECT' if detail is not None else 'RAW',
                graph_job_id=graph_job, selected_sample=detail['selected_sample'] if detail else 0,
                world_xy=path.points.tolist() if path is not None else None,
                path_length_m=float(path.s[-1]) if path is not None else None,
                projected_arclength_m=s, projection_distance_m=d,
                staleness=float(s/path.s[-1]) if path is not None else None,
                before_vw=before, after_vw=list(self.last_command), abs_dw=abs(self.last_command[1]-before[1]))
            self.applications.write(json.dumps(row)+'\n')
            self.applications.flush()

    def close(self):
        self.applications.close()
        super().close()
