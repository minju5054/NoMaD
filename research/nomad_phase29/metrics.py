import json
from collections import Counter
from pathlib import Path
from nomad_phase26.metrics import audit as original
from nomad_phase28t.analysis import analyze

def audit(root):
    r=original(root);root=Path(root);c=json.loads((root/'scenario.json').read_text());r['method']=c['phase29_method']
    events=[json.loads(s) for s in (root/'phase29_paths.jsonl').read_text().splitlines()] if (root/'phase29_paths.jsonl').exists() else []
    results=[e for e in events if e['event']=='RESULT'];submitted=sum(e['event']=='SUBMIT' for e in events)
    import numpy as np
    times=[e['wall_s'] for e in results]
    r.update(path_jobs=submitted,path_applied=sum(e['applied'] for e in results),path_reasons=dict(Counter(e['disposition'] for e in results)),
        compute_p50_s=float(np.median(times)) if times else None,compute_p95_s=float(np.quantile(times,.95)) if times else None,
        mean_speed_m_s=r['distance_m']/r['duration_s'])
    return r
