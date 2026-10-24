"""Narrow Phase8/9 opt-in; other experiment gates remain unchanged."""
import copy
import json
import re
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file

def protocol(phase=8):return json.loads((ROOT/f'research/nomad_phase{phase}/protocol.json').read_text())
def base_method(method):return 'GRAPH' if method in ('GRAPH','SELECT+GRAPH','GRAPH-v6') else 'CURV'
def validate_options(a):
    phase=a.overnight_phase;p=protocol(phase);m=a.overnight_method
    assert phase in (8,9) and m in p['methods'] and a.phase4c_method==base_method(m)
    assert a.asynchronous and a.pure_pursuit and a.topomap and a.plant_alpha=='inf'
    assert not any(getattr(a,k,None) for k in ('phase7_method','phase6_method','phase5_method','phase4d_confirm','phase4_method','s0_stage2_method','s0_delay_sweep','s1_mode','s1_v2_mode','s1_distance_m','phase2_method','phase2_distance_m','diagnostic_condition','oracle_safety_stop','early_obstacle_mode','prepare_only','render_topomap_reference','controlled_delivery_delay'))
    assert re.fullmatch(r'S[01]_\d{2}',a.run_id or '')
    i=int(a.run_id[-2:]);assert a.seed_offset==10000*i
    if phase==8:
        assert a.run_id.startswith('S0') and a.uniform_delivery_delay_s==.75
        assert (17<=i<=24 if m in ('CURV','SELECT','GRAPH') else 9<=i<=24 if m=='SELECT+GRAPH' else 9<=i<=16)
        if m=='RTC-hard':assert readiness()['included']
    else:
        assert a.run_id.startswith('S1') and (a.uniform_delivery_delay_s==.75 and 1<=i<=8 or a.uniform_delivery_delay_s==0 and 1<=i<=4 and m in ('CURV','GRAPH-v6'))
    assert sha256_file(a.scenario)==p['scenario_sha256'] and sha256_file(a.topomap)==p['topomap_manifest_sha256']
    for name,h in p['protected_sha256'].items():assert sha256_file(ROOT/name)==h,name

def runtime_config(source,a):
    validate_options(a);c=copy.deepcopy(source)
    c.update(overnight_phase=a.overnight_phase,overnight_method=a.overnight_method,phase4c_method=a.phase4c_method,plant_alpha='inf',execution_v_max_m_s=.3,timeout_sim_s=90)
    if a.overnight_phase==9:
        # Same Phase2 geometry/visibility semantics; never instantiate Phase2 controller.
        c.update(experiment_mode='phase2_s1_v2',phase2_distance_m=1.2,diagnostic_y_offset_m=.15 if int(a.run_id[-2:])%2 else -.15)
        c['dynamic_obstacle']={'id':'DynamicObstacle','size_xyz_m':[.35,.35,.8],'color_rgb':[.65,.04,.65],'minimum_visible_pixels':20,'spawn_tick':0,'placement':{'mode':'phase2_world_x','distance_m':1.2}}
    return c

def readiness():
    path=ROOT/'research/results/phase8_offline/summary.json'
    p=json.loads(path.read_text());assert p['count']==50
    lock=json.loads((ROOT/'research/nomad_phase8/readiness.json').read_text())
    assert lock['summary_sha256']==sha256_file(path)
    return dict(included=p['off_pass'] and p['prefix_pass'],summary=p)
