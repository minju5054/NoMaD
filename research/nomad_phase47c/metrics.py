import json
from pathlib import Path
from nomad_phase41.metrics import audit as original_audit
from nomad_phase43p.metrics import audit as hmm_audit
from nomad_phase43p.nodes import node_errors


def audit(root):
    root=Path(root);cfg=json.loads((root/'scenario.json').read_text());method=cfg['phase47c_method']
    r=hmm_audit(root) if method=='OURS-DETOUR+HMM' else original_audit(root)
    r['method']=method
    r['node_errors']=node_errors(root,'Phase47-C')
    for e in r['node_errors']:e['method']=method
    summary=json.loads((root/'summary.json').read_text());r['final_pose']=summary['final_pose']
    r['stop_pose']=summary['final_pose'] if r['declared_arrival'] else None
    if method!='OURS-DETOUR+HMM':
        for line in (root/'model/inference.jsonl').read_text().splitlines():
            if line.strip():assert 'hmm' not in json.loads(line)['topomap']
    return r
