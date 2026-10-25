import copy
import json
import re
from nomad_isaac.common import ROOT,sha256_file
from .methods import NEW
METHODS=('CURV','HERMITE-SPLICE','TEMPORAL-ENSEMBLE','BID-COHERENCE','RTC-hard','FRESHEST+GRAPH-GF','SELECT+GRAPH')


def protocol():return json.loads((ROOT/'research/nomad_phase12/protocol.json').read_text())
def internal(method):return 'CURV' if method in NEW else method


def validate_options(a):
    p=protocol();m=a.phase12_method
    assert m in METHODS and a.overnight_phase==8 and a.overnight_method==internal(m)
    assert a.phase4c_method==('GRAPH' if m in ('SELECT+GRAPH','FRESHEST+GRAPH-GF') else 'CURV')
    assert a.asynchronous and a.pure_pursuit and a.topomap and a.plant_alpha=='inf' and a.uniform_delivery_delay_s==.75
    assert not any(getattr(a,k,None) for k in ('phase11_v61','phase10b_no_obstacle','phase7_method','phase6_method','phase5_method','phase4d_confirm','phase4_method','s0_stage2_method','s0_delay_sweep','s1_mode','s1_v2_mode','s1_distance_m','phase2_method','phase2_distance_m','diagnostic_condition','oracle_safety_stop','early_obstacle_mode','prepare_only','render_topomap_reference','controlled_delivery_delay'))
    assert re.fullmatch(r'S0_(2[5-9]|3[0-4])',a.run_id or '') and a.seed_offset==10000*int(a.run_id[-2:])
    assert sha256_file(a.scenario)==p['scenario_sha256'] and sha256_file(a.topomap)==p['topomap_manifest_sha256']
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h,name
    if m=='RTC-hard':
        from nomad_phase8.config import readiness
        assert readiness()['included']


def runtime_config(source,a):
    validate_options(a);c=copy.deepcopy(source)
    c.update(phase12_method=a.phase12_method,overnight_phase=8,overnight_method=internal(a.phase12_method),
             phase4c_method=a.phase4c_method,plant_alpha='inf',execution_v_max_m_s=.3,timeout_sim_s=90)
    return c
