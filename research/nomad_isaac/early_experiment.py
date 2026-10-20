"""Narrow validation for the new fixed-location early-visibility experiment."""
import json
from pathlib import Path

from .common import sha256_file

PROTOCOL = Path(__file__).with_name("early_graph_protocol.json")


def validate_early(config, manifest, asynchronous, prepare_only=False, controlled_delay=False,
                   uniform_delay=None, oracle_stop=False):
    p = json.loads(PROTOCOL.read_text())
    if not asynchronous or prepare_only or controlled_delay or uniform_delay is not None or oracle_stop:
        raise ValueError("Early experiment requires async, fixed 2s Topomap, no extra delay or adaptive STOP mode")
    path = Path(__file__).with_name("early_obstacle_scenario.json")
    expected = json.loads(path.read_text())
    actual = dict(config)
    actual["synchronous"] = expected["synchronous"]
    if sha256_file(path) != p["scenario_sha256"] or actual != expected:
        raise ValueError("Early scenario differs from its frozen protocol")
    if sha256_file(manifest) != p["topomap_manifest_sha256"]:
        raise ValueError("Early experiment requires the unchanged 14-node reference")
