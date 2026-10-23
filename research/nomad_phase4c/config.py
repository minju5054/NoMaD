import json
import re
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file

HERE=Path(__file__).parent
METHODS=('CURV','CURV+ACC','GRAPH')


def protocol():return json.loads((HERE/'protocol.json').read_text())


def validate_options(a):
    p=protocol()
    if not (a.phase4c_method in METHODS and a.asynchronous and a.pure_pursuit and a.topomap):raise ValueError('Phase4c requires static S0 asynchronous PP')
    if any(getattr(a,k,None) for k in ('phase4_method','s0_stage2_method','s0_delay_sweep','s1_mode','s1_v2_mode','s1_distance_m','phase2_method','phase2_distance_m','diagnostic_condition','oracle_safety_stop','early_obstacle_mode','prepare_only','render_topomap_reference','controlled_delivery_delay')):raise ValueError('Cannot mix Phase4c with other modes')
    if a.plant_alpha not in ('inf','2.0','1.0'):raise ValueError('Frozen alpha required')
    if a.plant_alpha=='inf' and a.phase4c_method!='GRAPH':raise ValueError('Infinite-alpha CURV is reused, not rerun')
    if a.uniform_delivery_delay_s!=.75:raise ValueError('Phase4c is D750 only')
    if not re.fullmatch('S0_0[1-3]',a.run_id or '') or a.seed_offset!=10000*int(a.run_id[-1]):raise ValueError('Frozen paired indices1..3 required')
    if sha256_file(a.scenario)!=p['scenario_sha256'] or sha256_file(a.topomap)!=p['topomap_manifest_sha256']:raise ValueError('Frozen scenario/map changed')
    for name,digest in p['protected_sha256'].items():
        if sha256_file(ROOT/name)!=digest:raise ValueError('Protected input changed: '+name)


def runtime_config(source,a):
    return {**source,'timeout_sim_s':90,'phase4c_method':a.phase4c_method,'plant_alpha':a.plant_alpha,'execution_v_max_m_s':.3}


def allowed_status(status):
    # Preserve the user's existing report outputs; never hide, move or commit them.
    return all(line=='?? research/results/phase4_pilot/' for line in status.splitlines())
