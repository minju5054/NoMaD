import json
from pathlib import Path
from nomad_isaac.common import ROOT, sha256_file

HERE = Path(__file__).parent
METHODS = ('CURV', 'GRAPH')
ALPHAS = ('inf', '2.0')


def protocol():
    return json.loads((HERE / 'protocol.json').read_text())


def validate_frozen():
    for name, digest in protocol()['protected_sha256'].items():
        if sha256_file(ROOT / name) != digest:
            raise ValueError('Protected Phase4c implementation changed: ' + name)


def reference_records():
    p = protocol()
    source = ROOT / p['reference_results']
    assert sha256_file(source) == p['reference_results_sha256'], 'Phase4c results changed'
    records = json.loads(source.read_text())
    selected = [r for r in records if r['alpha'] in ALPHAS and r['method'] in METHODS]
    expected = {(a, m, i) for a in ALPHAS for m in METHODS for i in range(1, 4)}
    assert len(selected) == 12 and {(r['alpha'], r['method'], r['index']) for r in selected} == expected
    for r in selected:
        assert r['technical_validation'] == 'PASS'
        assert r['seed_offset'] == r['index'] * 10000 and r['delay_s'] == .75
    return selected
