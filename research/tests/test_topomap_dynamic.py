"""Only the frozen static-reference / async / zero-delay combination is allowed."""
import json
from pathlib import Path

import pytest

from nomad_isaac.common import ROOT
from nomad_isaac.topomap import validate_dynamic_combination


def inputs():
    config = json.loads((ROOT/"research/nomad_isaac/old_rollout_obstacle_scenario.json").read_text())
    manifest = ROOT.parent/"artifacts/isaac6/topomap_reference_2s_01/topomap/manifest.json"
    return config, manifest


def test_combination_accepts_original_config_and_async_runtime_config():
    config, manifest = inputs()
    validate_dynamic_combination(config, manifest, True)
    config["synchronous"] = False
    validate_dynamic_combination(config, manifest, True)


@pytest.mark.parametrize("kwargs", [dict(asynchronous=False), dict(asynchronous=True, prepare_only=True),
    dict(asynchronous=True, controlled_delay=True), dict(asynchronous=True, uniform_delay=.5),
    dict(asynchronous=True, uniform_delay=0.)])
def test_combination_rejects_other_execution_modes(kwargs):
    config, manifest = inputs()
    with pytest.raises(ValueError):
        validate_dynamic_combination(config, manifest, **kwargs)


def test_combination_rejects_changed_geometry_or_reference(tmp_path):
    config, manifest = inputs()
    config["dynamic_obstacle"]["spawn_tick"] += 1
    with pytest.raises(ValueError):
        validate_dynamic_combination(config, manifest, True)
    config, manifest = inputs()
    changed = json.loads(manifest.read_text())
    changed["dynamic_obstacle"] = True
    path = tmp_path/"manifest.json"; path.write_text(json.dumps(changed))
    with pytest.raises(ValueError):
        validate_dynamic_combination(config, path, True)
