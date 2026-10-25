"""Frozen Hermite-only follow-up; no original experiment files are rewritten."""
import json
from pathlib import Path
from nomad_isaac.common import ROOT,sha256_file

HERE=Path(__file__).parent

def protocol():return json.loads((HERE/'protocol.json').read_text())

def assert_frozen():
    p=protocol()
    for name,digest in p['fixed_sha256'].items():assert sha256_file(ROOT/name)==digest,name
    for name,digest in p['reference_sha256'].items():assert sha256_file(Path(name))==digest,name
    return p


def references():
    p=assert_frozen();root=Path(p['phase12_run_root']);plan=json.loads((root/'plan.json').read_text());records=[]
    assert plan['git_sha']==p['reference_execution_sha']
    for j in plan['jobs']:
        if j['method']=='HERMITE-SPLICE':continue
        path=root/'metrics'/f"{j['key']}.json";r=json.loads(path.read_text())
        assert all(r[k]==j[k] for k in ('key','method','index','seed_offset','output'))
        if r['technical_validation']=='PASS':
            assert r['execution_git_sha']==plan['git_sha']
            for name,digest in r['input_log_sha256'].items():assert sha256_file(Path(r['output'])/name)==digest,name
        records.append(dict(r,reused=True,source_phase='12'))
    assert len(records)==60
    return records
