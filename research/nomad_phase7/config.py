import json
import re
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file

HERE=Path(__file__).parent
METHODS=('SELECT','CURV','GRAPH')


def protocol():
    return json.loads((HERE/'protocol.json').read_text())


def readiness():
    result=json.loads((HERE/'readiness.json').read_text())
    path=ROOT/protocol()['readiness_results']
    assert sha256_file(path)==result['summary_sha256'],'Offline readiness changed'
    summary=json.loads(path.read_text());assert summary['verdict']==result['verdict']
    # This frozen one-shot validation did not qualify. Do not offer unvalidated online RTC.
    assert result['verdict']=='RTC_NOT_READY' and not result['rtc_online_enabled']
    return result


def base_method(method):
    return 'GRAPH' if method=='GRAPH' else 'CURV'


def validate_options(a):
    p=protocol();readiness();m=a.phase7_method
    if m not in METHODS or a.phase6_method!=m or a.phase4c_method!=base_method(m):
        raise ValueError('Phase7 method/execution hook mismatch')
    if not a.asynchronous or not a.pure_pursuit or not a.topomap or a.plant_alpha!='inf':
        raise ValueError('Phase7 frozen static S0 PP only')
    if a.uniform_delivery_delay_s!=(.75 if m=='SELECT' else .625):raise ValueError('Phase7 fixed delay required')
    if any(getattr(a,k,None) for k in ('phase5_method','phase4d_confirm','phase4_method','s0_stage2_method',
        's0_delay_sweep','s1_mode','s1_v2_mode','s1_distance_m','phase2_method','phase2_distance_m','diagnostic_condition',
        'oracle_safety_stop','early_obstacle_mode','prepare_only','render_topomap_reference','controlled_delivery_delay')):
        raise ValueError('Cannot combine experiments')
    if not re.fullmatch(r'S0_(09|1[0-6])',a.run_id or '') or a.seed_offset!=10000*int(a.run_id[-2:]):
        raise ValueError('Frozen paired indices9..16 required')
    if sha256_file(a.scenario)!=p['scenario_sha256'] or sha256_file(a.topomap)!=p['topomap_manifest_sha256']:
        raise ValueError('Frozen scene/map changed')
    for name,h in p['protected_sha256'].items():
        if sha256_file(ROOT/name)!=h:raise ValueError('Protected input changed: '+name)
