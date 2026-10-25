import copy
import json
import re
from nomad_isaac.common import ROOT, sha256_file
from .methods import METHODS, GF

HERE = ROOT/'research/nomad_phase13'


def protocol():
    return json.loads((HERE/'protocol.json').read_text())


def validate_options(a):
    p = protocol()
    assert a.phase13_method in METHODS and a.overnight_phase == 8 and a.overnight_method == 'CURV'
    assert a.phase4c_method == ('GRAPH' if a.phase13_method == GF else 'CURV')
    assert a.asynchronous and a.pure_pursuit and a.topomap and a.plant_alpha == 'inf'
    assert a.uniform_delivery_delay_s == .75
    assert re.fullmatch(r'S0_(3[5-9]|4[0-6])', a.run_id or '')
    assert a.seed_offset == 10000*int(a.run_id[-2:])
    forbidden = ('phase12_method','phase11_v61','phase10b_no_obstacle','phase7_method','phase6_method',
        'phase5_method','phase4d_confirm','phase4_method','s0_stage2_method','s0_delay_sweep','s1_mode',
        's1_v2_mode','s1_distance_m','phase2_method','phase2_distance_m','diagnostic_condition',
        'oracle_safety_stop','early_obstacle_mode','prepare_only','render_topomap_reference','controlled_delivery_delay')
    assert not any(getattr(a, k, None) for k in forbidden)
    assert sha256_file(a.scenario) == p['scenario_sha256']
    assert sha256_file(a.topomap) == p['topomap_manifest_sha256']
    for name, h in p['protected_sha256'].items():
        assert sha256_file(ROOT/name) == h, name


def runtime_config(source, a):
    validate_options(a)
    c = copy.deepcopy(source)
    c.update(phase13_method=a.phase13_method, phase12_method=a.phase13_method,
             overnight_phase=8, overnight_method='CURV', phase4c_method=a.phase4c_method,
             plant_alpha='inf', execution_v_max_m_s=.3, timeout_sim_s=90)
    return c
