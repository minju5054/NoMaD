"""Phase18 SAFE + CLR scheduler, without recovery or STOP_WAIT special policy.

Only current-path retention and an endpoint latch wrap the original PP/CURV
executor. Graph factors, initialization, worker and acceptance clocks are reused.
"""
import json
import time
import numpy as np
from nomad_isaac.common import local_to_world
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase4c.execution import AccelExecution
from nomad_phase12.gf_worker import CONTROL_CONFIG, numeric_job
from nomad_phase15b.depth import evaluate_samples
from nomad_phase17.worker import Client
from nomad_phase28.telemetry import builtin
from .common import METHOD

class Execution(AccelExecution):
    def __init__(self, out, client=None):
        super().__init__(dict(CONTROL_CONFIG), out, client if client is not None else Client(out, True))
        self.depth_maps = None
        self.snapshot = None
        self.last_application_ns = None
        self.path_received_ns = None
        self.path_source_id = None
        self.active_sample = None
        self.endpoint_latched = False
        self.apps = (out / 'j_applications.jsonl').open('x')

    def record(self, row):
        if row['event'] == 'SUBMIT':
            row = dict(event='SUBMIT', **numeric_job({k:v for k,v in row.items() if k != 'event'}),
                       depth_snapshot=dict(self.snapshot.metadata))
        super().record(builtin(row))

    def apply(self, core, refresh, switch):
        original = None
        install = False
        before = list(self.last_command)
        if switch is not None:
            self.snapshot = self.depth_maps.snapshot()
            switch['j_selection_ns'] = time.monotonic_ns()
            worlds = np.array([local_to_world(np.asarray(x), switch['observation_pose'])
                               for x in switch['overnight_metric_samples']])
            selected, detail = evaluate_samples(worlds, core.pose, self.snapshot)
            install = not detail['all_unsafe']
            if install:
                try:
                    XYPath(selected)
                except ValueError:
                    install = False
            switch['j_selection'] = dict(detail, installed=install,
                                        disposition='SAFE_SELECTED' if install else 'NO_SAFE_KEEP_CURRENT',
                                        oracle_used=False)
            if install:
                original = switch['chunk']
                switch['chunk'] = dict(original, world_xy_m=selected.tolist(), path_valid=True)
                self.active_sample = detail['selected_sample']
                self.path_source_id = switch['id']
                self.path_received_ns = switch['received_monotonic_ns']
                self.endpoint_latched = False
                self.client.snapshot_file = self.snapshot.metadata['file']
            else:
                # The incoming chunk is acknowledged by the unchanged timing
                # core, but cannot refresh the retained path's own one-second age.
                self.active_id = switch['id']
        latest_valid = refresh['valid']
        if self.path_received_ns is not None and refresh['monotonic_ns'] - self.path_received_ns >= 1_000_000_000:
            refresh.update(valid=False, status='expired')
        refresh['j_latest_chunk_valid'] = latest_valid
        try:
            super().apply(core, refresh, switch if install else None)
        finally:
            if original is not None:
                switch['chunk'] = original
        graph_job = refresh['stage2']['graph_applied_job']
        if graph_job is not None:
            self.endpoint_latched = False
        if refresh['pure_pursuit'].get('endpoint_stop'):
            self.endpoint_latched = True
        if self.endpoint_latched:
            core.v, core.w = 0., 0.
            self.last_command = [0., 0.]
            refresh.update(commanded_v_m_s=0., commanded_w_rad_s=0., applied_v_m_s=0.,
                           applied_command_source='ENDPOINT')
            refresh['pure_pursuit']['stop_reason'] = 'ENDPOINT'
            refresh['stage2'].update(v_target_m_s=0., kappa_pp=None, CURVATURE_SATURATED=False,
                                     ACCEL_LIMITED=False, OMEGA_CLIPPED=False)
        refresh['j_execution'] = dict(method=METHOD, endpoint_latched=self.endpoint_latched,
                                     path_source_id=self.path_source_id, path_received_ns=self.path_received_ns,
                                     recovery=False, stop_wait_special=False, EC=False)
        if switch is not None:
            switch.update({k:refresh[k] for k in ('commanded_v_m_s','commanded_w_rad_s','applied_v_m_s',
                           'applied_command_source','pure_pursuit','stage2','j_execution')})
        if install or graph_job is not None:
            self.last_application_ns = refresh['monotonic_ns']
            row = dict(tick=round(refresh['simulation_time_s']*72), simulation_time_s=refresh['simulation_time_s'],
                       id=self.active_id, path_source_id=self.path_source_id, kind='GRAPH' if graph_job is not None else 'SAFE',
                       graph_job_id=graph_job, selected_sample=self.active_sample, pose=core.pose.tolist(),
                       world_xy=self.follower.path.points.tolist(), before_vw=before, after_vw=self.last_command,
                       depth_snapshot=dict(self.snapshot.metadata))
            self.apps.write(json.dumps(builtin(row), allow_nan=False)+'\n')
            self.apps.flush()

    def close(self):
        try:
            super().close()
        finally:
            self.apps.close()

def install(c):
    from nomad_phase16.execution import install_runtime_adapters
    install_runtime_adapters()
    import nomad_phase15b.execution as factory
    def make(config, out):
        assert config['j_common'] and config['j_method'] == METHOD
        return Execution(out)
    factory.make_execution = make
    if c.get('phase26_dynamic'):
        from nomad_phase26.scenes import MultiSuddenMonitor
        import nomad_isaac.sudden_obstacle as sudden
        sudden.SuddenObstacleMonitor = MultiSuddenMonitor
    if c['phase16_scene'] == 'H1':
        # H1 contains static corner boxes. H2 deliberately retains the frozen
        # empty S1-v2 corridor evaluator, whose obstacle clearance is None.
        import nomad_phase1.s1_v2 as s1
        from nomad_isaac.clearance import MultiObstacleMonitor
        s1.CorridorOnlyMonitor = lambda ignored, out: MultiObstacleMonitor(c, out)
    if c.get('h1v2'):
        from nomad_h1v2.scene import install_environment
        install_environment(c)

def run_without_oracle(*args, **kwargs):
    """Frozen async driver with only visibility-gated oracle publication removed."""
    import ast
    import inspect
    from nomad_isaac import async_runtime as runtime
    tree = ast.parse(inspect.getsource(runtime.run_async))
    count = 0
    for i, node in enumerate(tree.body[0].body):
        if isinstance(node, ast.If) and ast.unparse(node.test) == 's1 and engine.dynamic is not None':
            tree.body[0].body[i] = ast.Assign(targets=[ast.Name(id='oracle_gate', ctx=ast.Store())], value=ast.Constant(None))
            count += 1
    assert count == 1
    namespace = dict(runtime.__dict__)
    exec(compile(ast.fix_missing_locations(tree), runtime.__file__, 'exec'), namespace)
    return namespace['run_async'](*args, **kwargs)
