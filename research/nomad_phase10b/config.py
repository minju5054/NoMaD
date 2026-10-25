import json
from nomad_isaac.common import ROOT


def protocol():
    return json.loads((ROOT/'research/nomad_phase10b/protocol.json').read_text())
