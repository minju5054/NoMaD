"""Auditor/report-only hash overlay. The preregistered protocol is immutable."""
import json
from nomad_isaac.common import ROOT,sha256_file

ALLOWED=frozenset({'research/nomad_j1/metrics.py','research/nomad_j1/config.py',
                   'research/nomad_j1/report.py','research/nomad_j1/campaign.py'})
REVISION='RTC_PREFIX_D_AND_INTERIM_REPORT_V1'

def validated_sources(p):
    file=ROOT/'research/nomad_j1/validation_revision.json'
    revision=json.loads(file.read_text())
    assert revision['revision']==REVISION
    assert revision['protocol_sha256']==sha256_file(ROOT/'research/nomad_j1/protocol.json')
    assert set(revision['replaced_source_sha256'])==ALLOWED
    result=dict(p['source_sha256'])
    for path,item in revision['replaced_source_sha256'].items():
        assert item['frozen']==result[path]
        result[path]=item['revised']
    for path,digest in revision['added_source_sha256'].items():
        assert path.startswith('research/nomad_j1/') and path.endswith('.py')
        assert sha256_file(ROOT/path)==digest,path
    return result
