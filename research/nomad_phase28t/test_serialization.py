"""Saved-input controller/log replay only: no solver, simulator or inference."""
import copy
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from nomad_isaac.common import ROOT, integrate_se2
from nomad_phase28.alignment import NoAlignment
from nomad_phase28.graph_r1 import R1Follower
from nomad_phase28.online_r1 import R1Execution
from nomad_phase28.telemetry import builtin
from . import smoke, launch, report

SMOKE01 = ROOT.parent/'artifacts/isaac6/phase28t_smoke_01'
TICKS = 128  # Controller calls; each followed by eight 72 Hz integration ticks.


class StrictStream(io.StringIO):
    def write(self, value):
        json.dumps(json.loads(value))  # No encoder/default hook.
        return super().write(value)


def saved_cases():
    manifest = json.loads((ROOT/'research/results/phase28_r1_online/parity_manifest.json').read_text())
    chosen = {}
    for item in manifest['cases']:
        chosen.setdefault(item['expected_output'], item)
    return chosen


def replay(result, path, pose, vw, alpha, start_s=0.):
    """Use real H COMMAND + inherited controller writer, including NA fallback."""
    obj = object.__new__(R1Execution)
    obj.init_telemetry()
    obj.h_log = StrictStream();obj.command_log = StrictStream();obj.repair_log = StrictStream();obj.dcmd = StrictStream()
    obj.r1_cases[0] = dict(id=0, commands=0, clips=0)
    obj.r1_current = 0;obj.r1_now_s = start_s
    obj.alpha = alpha;obj.last_command = list(vw)
    obj.plant = SimpleNamespace(actual_w=vw[1])
    obj.recovery = SimpleNamespace(state='NORMAL', count=0, streak=0)
    obj.named_method = 'M3_DETOUR';obj.mode = 'NORMAL';obj.repair_pending = None
    obj.repair_active = False;obj.path_source_id = 0
    obj.detour_active = False;obj.detour = None
    snapshot = SimpleNamespace(metadata=dict(frame_id=0,sim_s=start_s,publication_monotonic_ns=0))
    obj.depth_maps = SimpleNamespace(snapshot=lambda:snapshot)
    core = SimpleNamespace(pose=np.asarray(pose, float), v=float(vw[0]), w=float(vw[1]))
    refresh = dict(simulation_time_s=start_s, monotonic_ns=0)
    job = dict(job_id=0, id=0, path=path)
    obj.hrecord('DISPATCH', job_id=0, dispatch_wall_s=0.)
    if result['accepted']:
        obj.sp = R1Follower(copy.deepcopy(result), start_s, alpha)
        obj.follower = obj.sp.follower
        obj.hrecord('APPLIED', job_id=0, result=result)
    else:
        # FALLBACK has no timed solution; exercise the actual frozen NA route.
        obj.fallback_h(job, core, refresh, result['disposition'], result)
        assert isinstance(obj.sp, NoAlignment)
    reference = copy.deepcopy(obj.sp)
    original = {}
    if result['accepted']:
        source = subprocess.check_output(['git', 'show', 'f17baf3:research/nomad_phase28/tracking.py'], cwd=ROOT, text=True)
        original = dict(__name__='nomad_phase28._serialization_reference', __package__='nomad_phase28')
        exec(compile(source, '<pre-fix tracking>', 'exec'), original)

    records = 0
    old_non_json = 0
    for step in range(TICKS):
        now = start_s + step/9
        before = [core.v, core.w]
        if result['accepted']:
            for follower in (obj.sp, reference):
                follower.now_s = now;follower.previous_w = core.w
            expected, old_diag = original['TimedFollower'].control(reference, core.pose, core.v)
            try:json.dumps(old_diag)
            except TypeError:old_non_json += 1
        else:
            expected, old_diag = reference.control(core.pose, core.v)
        command, diag = obj.sp.control(core.pose, core.v)
        np.testing.assert_array_equal(command, expected)
        assert builtin(old_diag) == diag
        json.dumps(diag)
        core.v, core.w = command;obj.plant.actual_w = core.w
        refresh = dict(simulation_time_s=now, monotonic_ns=np.int64(step), valid=np.bool_(True))
        switch = dict(id=np.int64(0), telemetry=np.array([True, False]))
        obj.r1_now_s = now
        obj.write_command(core, refresh, switch, before, before, 'HANDOFF' if result['accepted'] else 'NORMAL', diag)
        for record in (diag, refresh, switch):
            json.dumps(record)  # The formerly failing async append boundary.
            assert_basic(record)
            records += 1
        obj.last_command = list(command)
        for _ in range(8):core.pose = integrate_se2(core.pose, core.v, core.w, 1/72)
    obj.finalize_telemetry()
    for stream in (obj.h_log, obj.command_log, obj.repair_log, obj.dcmd):
        for line in stream.getvalue().splitlines():
            json.dumps(json.loads(line));records += 1
    commands = [json.loads(line) for line in obj.command_log.getvalue().splitlines()]
    assert len(commands) == TICKS
    if result['accepted']:assert old_non_json > 0
    return dict(output_type=result['output_type'],controller_ticks=TICKS,integration_ticks=TICKS*8,
                serialized_records=records,pre_fix_non_json_diag_ticks=old_non_json,command_max_difference=0.)


def assert_basic(value):
    assert type(value) in (dict, list, str, int, float, bool, type(None)), type(value)
    if isinstance(value, dict):
        for k, v in value.items():assert_basic(k);assert_basic(v)
    elif isinstance(value, list):
        for v in value:assert_basic(v)


class SerializationTests(unittest.TestCase):
    def saved(self, kind):
        item = saved_cases()[kind]
        result = json.loads(Path(item['expected_file']).read_text())
        return replay(result, item['case']['selected_path'], result['prediction']['pose'], result['prediction']['vw'], result['alpha'])

    def test_saved_optimized_128_ticks(self):self.saved('OPTIMIZED')
    def test_saved_init_only_128_ticks(self):self.saved('INIT_ONLY')
    def test_saved_fallback_128_ticks(self):self.saved('FALLBACK')

    def test_smoke01_applied_128_ticks(self):
        events = [json.loads(s) for s in (SMOKE01/'phase28_handoff.jsonl').read_text().splitlines()]
        applied = next(e for e in events if e['event']=='APPLIED')
        dispatch = next(e for e in events if e['event']=='DISPATCH' and e['job_id']==applied['job_id'])
        result = replay(applied['result'], dispatch['path'], applied['pose'], applied['prediction']['vw'], 2., applied['simulation_time_s'])
        self.assertGreater(result['pre_fix_non_json_diag_ticks'], 0)

    def test_nested_numpy_values_and_keys(self):
        value = {np.int64(7): (np.bool_(True), np.float32(.5), np.int32(3), np.array([[True, False]]))}
        converted = builtin(value);assert_basic(converted);json.dumps(converted)
        self.assertEqual(converted, {7:[True,.5,3,[[True,False]]]})
        self.assertIsInstance(value[np.int64(7)][0], np.bool_)

    def test_new_smoke_root_dry_run_only(self):
        self.assertEqual(smoke.SMOKE_ROOT.name, 'phase28t_smoke_02')
        args=['smoke','--output',str(smoke.SMOKE_ROOT),'--dry-run']
        with patch('sys.argv',args),patch.object(smoke.subprocess,'run') as run,patch('sys.stdout',new_callable=io.StringIO) as output:
            smoke.main()
        run.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['navigation_started'],0)

    def test_existing_smoke_rejected_by_runner_and_launcher(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);marker=root/'keep';marker.write_text('preserve')
            with patch.object(smoke,'SMOKE_ROOT',root),patch.object(smoke.subprocess,'run') as run,patch('sys.argv',['smoke','--output',str(root)]):
                with self.assertRaisesRegex(RuntimeError,'Existing smoke'):smoke.main()
            run.assert_not_called()
            with patch.object(launch,'plan') as affinity,patch('sys.argv',['launch','--scene','H1','--method','C0-H','--index','201','--output',str(root)]):
                with self.assertRaisesRegex(RuntimeError,'Existing smoke'):launch.main()
            affinity.assert_not_called();self.assertEqual(marker.read_text(),'preserve')

    def test_smoke02_report_does_not_overwrite_smoke01(self):
        old = report.smoke_destinations(SMOKE01)
        new = report.smoke_destinations(smoke.SMOKE_ROOT)
        self.assertEqual(old[0].name,'smoke');self.assertEqual(old[1].name,'PHASE28T_SMOKE.md')
        self.assertEqual(new[0].name,'smoke_02');self.assertEqual(new[1].name,'PHASE28T_SMOKE_02.md')


if __name__=='__main__':unittest.main()
