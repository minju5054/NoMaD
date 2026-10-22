"""Only the new reference endpoint, empty geometry and narrow mode guards."""
import json
from types import SimpleNamespace

import numpy as np
import pytest

from nomad_isaac.clearance import corridor_clearance, MultiObstacleMonitor
from nomad_isaac.common import integrate_se2
from nomad_isaac.topomap import reference_rows
from nomad_phase1.s1_v2 import HERE, CorridorOnlyMonitor, centerline, create_reference, validate_options


def test_reference_first_goal_entry_and_spacing(tmp_path):
    config = json.loads((HERE/"s1_v2_scenario.json").read_text())
    path = centerline(config)
    distances = np.linalg.norm(path[:, :2]-[8., 0.], axis=1)
    assert np.all(distances[:-1] > .3) and distances[-1] <= .3
    assert np.all(path[:, 1:] == 0.)
    reference = tmp_path/"reference"
    create_reference(reference)
    selected = reference_rows(reference, config, 2.)
    assert [i for i, _ in selected[:-1]] == list(range(0, len(path)-1, 144))
    assert selected[-1][0] == len(path)-1 and len(selected) != 14


def test_corridor_only_keeps_original_bound_and_stop(tmp_path):
    config = json.loads((HERE/"s1_v2_scenario.json").read_text())
    monitor = CorridorOnlyMonitor(config, tmp_path)
    a = np.array([1., 1.409, np.pi/2]); b = integrate_se2(a, .2, .4, 1/72)
    row = monitor.observe_interval(a, b, .2, .4, 0., 1/72)
    assert row["corridor_lower_m"] == corridor_clearance(a, b, .2, .4, 1/72, config["corridor"], .09)
    assert row["lower_m"] is None and monitor.stop_reason == "corridor_footprint_stop"
    assert not monitor.finish(False)["corridor_containment_certified"]
    with pytest.raises(AssertionError):
        MultiObstacleMonitor(config, tmp_path)  # Old multi-box behavior is unchanged.


def test_s1_v2_cannot_enable_other_experiments():
    args = SimpleNamespace(s1_mode=False, s1_distance_m=None, seed_offset=0, run_id=None,
        oracle_safety_stop=False, early_obstacle_mode=None, controlled_delivery_delay=False,
        scenario=HERE/"s1_v2_scenario.json", prepare_only=False, asynchronous=True,
        pure_pursuit=True, topomap="unused", render_topomap_reference=None, uniform_delivery_delay_s=.75)
    with pytest.raises(ValueError, match="explicit uniform D=0"):
        validate_options(args)
    args.uniform_delivery_delay_s = 0.; args.seed_offset = 10000
    with pytest.raises(ValueError, match="only its frozen"):
        validate_options(args)
