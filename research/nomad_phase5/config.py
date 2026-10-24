import json
import re
from pathlib import Path
from nomad_isaac.common import ROOT, sha256_file

HERE = Path(__file__).parent
METHODS = ('CURV','RIGID-ENTRY','GRAPH','GRAPH-NO-PREV','GRAPH-NO-SDF','GRAPH-NO-KB')


def protocol():
    return json.loads((HERE/'protocol.json').read_text())


def graph_protocol(method):
    p = json.loads((ROOT/'research/nomad_phase0/graph_v4_protocol.json').read_text())
    p['phase5_flags'] = protocol()['graph_flags'][method]
    return p


def base_method(method):
    return 'GRAPH' if method.startswith('GRAPH') else 'CURV'


def validate_options(a):
    p=protocol()
    if a.phase5_method not in METHODS or a.phase4c_method!=base_method(a.phase5_method):raise ValueError('Phase5 method/executor mismatch')
    if not a.asynchronous or not a.pure_pursuit or not a.topomap or a.plant_alpha!='inf' or a.uniform_delivery_delay_s!=.75:raise ValueError('Phase5 requires frozen S0 PP D750 alpha inf')
    if any(getattr(a,k,None) for k in ('phase4d_confirm','phase4_method','s0_stage2_method','s0_delay_sweep','s1_mode','s1_v2_mode','s1_distance_m','phase2_method','phase2_distance_m','diagnostic_condition','oracle_safety_stop','early_obstacle_mode','prepare_only','render_topomap_reference','controlled_delivery_delay')):raise ValueError('Cannot combine experiment modes')
    if not re.fullmatch(r'S0_(09|1[0-6])',a.run_id or '') or a.seed_offset!=10000*int(a.run_id[-2:]):raise ValueError('Frozen seed indices9..16 required')
    if sha256_file(a.scenario)!=p['scenario_sha256'] or sha256_file(a.topomap)!=p['topomap_manifest_sha256']:raise ValueError('Frozen scenario/map changed')
    for name,digest in p['protected_sha256'].items():
        if sha256_file(ROOT/name)!=digest:raise ValueError('Protected implementation changed: '+name)
