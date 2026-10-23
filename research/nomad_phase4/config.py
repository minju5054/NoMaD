import json
import re
from pathlib import Path
from nomad_isaac.common import ROOT, sha256_file

HERE = Path(__file__).parent
METHODS = ('RAW', 'CURV-SPEED', 'GRAPH-v5')


def protocol():
    return json.loads((HERE/'protocol.json').read_text())


def validate_options(a):
    p = protocol()
    if not (a.phase4_method in METHODS and a.asynchronous and a.pure_pursuit and a.topomap):
        raise ValueError('Phase4 requires S0 asynchronous PP and static Topomap')
    excluded = ('prepare_only', 'oracle_safety_stop', 'early_obstacle_mode', 'controlled_delivery_delay',
        'render_topomap_reference', 's1_mode', 's1_v2_mode', 's1_distance_m', 'phase2_method',
        'phase2_distance_m', 'diagnostic_condition', 's0_delay_sweep', 's0_stage2_method')
    if any(getattr(a, k, None) for k in excluded):
        raise ValueError('Phase4 cannot mix with another experiment mode')
    if not re.fullmatch(r'S0_0[1-4]', a.run_id or '') or a.seed_offset != int(a.run_id[3:])*10000:
        raise ValueError('Phase4 requires paired S0_01..04 offsets')
    d = a.uniform_delivery_delay_s
    if d != .75 and not (d == 0 and a.phase4_method == 'GRAPH-v5' and int(a.run_id[3:]) <= 2):
        raise ValueError('Only frozen D750 three-method / D0 GRAPH matrix is allowed')
    if sha256_file(a.scenario) != p['scenario_sha256'] or sha256_file(a.topomap) != p['topomap_manifest_sha256']:
        raise ValueError('Frozen S0/map mismatch')
    # Lightweight launch gate. All other protected files are verified by the batch preflight.
    for name in ('pure_pursuit.py', 'graph_v4.py', 'graph_v4_protocol.json'):
        f = 'research/nomad_phase0/'+name
        if sha256_file(ROOT/f) != p['protected_sha256'][f]:
            raise ValueError('Protected follower or Graph changed')


def runtime_config(source, args):
    return {**source, 'timeout_sim_s': 90, 'phase4_method': args.phase4_method, 'execution_v_max_m_s': .3}
