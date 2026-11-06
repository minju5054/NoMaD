"""Validate the Phase26 freeze, allowing exactly one registered source delta."""
import copy
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase26.config import protocol as original_protocol

HERE=Path(__file__).parent
OUT=ROOT/'research/results/phase27r'
RUN_ROOT=ROOT.parent/'artifacts/isaac6/phase27r_pilot_01'
PATCH='research/nomad_phase20/execution.py'

def registration():return json.loads((HERE/'protocol.json').read_text())

def protocol():
    p=copy.deepcopy(original_protocol());r=registration()
    assert p['frozen_sources'][PATCH]==r['allowed_source_change']['before_sha256']
    p['frozen_sources'][PATCH]=r['allowed_source_change']['after_sha256']
    p['phase27r']=dict(base_protocol_sha256=r['phase26_protocol_sha256'],registration_sha256=sha256_file(HERE/'protocol.json'),
        allowed_source_change=r['allowed_source_change'],results_directory=str(OUT))
    return p

def verify():
    r=registration();assert r['status']=='FROZEN'
    assert sha256_file(ROOT/'research/nomad_phase26/protocol.json')==r['phase26_protocol_sha256']
    p=protocol()
    for f,h in {**p['frozen_sources'],**p['source_sha256'],**r['wrapper_source_sha256']}.items():
        assert sha256_file(ROOT/f)==h,f
    for s in p['scenes'].values():
        assert sha256_file(ROOT/s['scenario'])==s['scenario_sha256']
        assert sha256_file(s['topomap'])==s['topomap_sha256']
    assert sha256_file(ROOT.parent/'artifacts/checkpoints/nomad.pth')==p['checkpoint_sha256']
    return p

def check_run_root(root):
    # Never feed an old phase's completed metrics into this rerun, or overwrite it.
    root=Path(root).resolve()
    if root!=RUN_ROOT.resolve():raise ValueError('Registered fresh Phase27-R run-root required: '+str(RUN_ROOT))
    return root
