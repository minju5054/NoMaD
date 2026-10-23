"""Narrow opt-in gate; legacy S0/Phase1/Phase2 paths remain unchanged."""
import json
import re
from pathlib import Path
from nomad_isaac.common import ROOT, sha256_file

HERE = Path(__file__).parent


def protocol():
    return json.loads((HERE/'protocol.json').read_text())


def validate_options(a):
    p = protocol()
    if not (a.s0_delay_sweep and a.asynchronous and getattr(a, 'pure_pursuit', False) and a.topomap):
        raise ValueError('S0 delay sweep requires asynchronous PP and static Topomap')
    excluded = ('prepare_only', 'oracle_safety_stop', 'early_obstacle_mode', 'controlled_delivery_delay',
                'render_topomap_reference', 's1_mode', 's1_v2_mode', 's1_distance_m', 'phase2_method',
                'phase2_distance_m', 'diagnostic_condition', 's0_stage2_method')
    if any(getattr(a, name, None) for name in excluded):
        raise ValueError('S0 delay sweep cannot mix with another experiment mode')
    if a.uniform_delivery_delay_s not in p['delays_s']:
        raise ValueError('Expected explicit uniform D=0/250/500/750ms')
    if not re.fullmatch(r'S0_0[1-5]', a.run_id or '') or a.seed_offset != int(a.run_id[3:])*10000:
        raise ValueError('Expected frozen S0_01..05 paired seed offsets')
    if sha256_file(a.scenario) != p['scenario_sha256'] or sha256_file(a.topomap) != p['topomap_manifest_sha256']:
        raise ValueError('S0 scenario or 14-node Topomap differs from frozen inputs')
    for name in ('pure_pursuit.py', 'follower_protocol.json', 'chunk_pilot_protocol.json'):
        path = 'research/nomad_phase0/'+name
        if sha256_file(ROOT/path) != p['protected_sha256'][path]:
            raise ValueError('Frozen PP changed')


def runtime_config(source):
    # Only the new mode extends the termination ceiling. Never write the source JSON.
    return {**source, 'timeout_sim_s': protocol()['maximum_simulation_s'], 's0_delay_sweep': True}
