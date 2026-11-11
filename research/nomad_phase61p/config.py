"""New seeds only; same Phase58 methods/scene rules with oracle-localization wiring."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase40p.launch import bind
from nomad_phase58p import config as base
HERE=Path(__file__).parent;OUT=ROOT/'research/results/phase61p';RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase61p_01'
METHODS=base.METHODS;SCENES=base.SCENES;INDICES=(229,230);ORDER_SEED=base.ORDER_SEED

def protocol():return json.loads((HERE/'protocol.json').read_text())
def registered_order():return bind(base.registered_order,INDICES=INDICES)()
def runtime_config(method,index,timeout=90,level='H1-v2'):
    c=bind(base.runtime_config,INDICES=INDICES,protocol=protocol)(method,index,timeout,level)
    # Use the original declared-stop driver, not the HMM odometry adapter.
    # Controller factory is still the exact Phase58 ConsExecution factory.
    c['phase47c_method']='OURS-DETOUR';c.pop('phase43p',None);c.pop('phase43p_method',None)
    c.update(phase61p=True,phase61p_localization='ORACLE_NEAREST_XY',oracle_localization_analysis_only=True,
        phase61p_pose_clock='observation_pose',phase61p_delay_s=.75)
    return c
def verify():
    base.verify();p=protocol();assert p['status']=='FROZEN' and p['main_order']==registered_order()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**p['reference_hashes']}.items():assert sha256_file(ROOT/f)==h,f
    return p
