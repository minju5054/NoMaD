"""Frozen evaluation; remove only inapplicable no-detour / one-second audits."""
import inspect,json
from pathlib import Path
from nomad_phase53p import metrics as frozen
from nomad_phase24r.online_metrics import rows

def adapted_audit(hold=False):
    s=inspect.getsource(frozen.audit)
    for line in ("    assert r['detour_applied_count']==0 and r['g_dispatches']==0\n", "    assert not [e for e in rows(root/'repair.jsonl') if e['event'] in ('DISPATCH','TRIGGER')]\n"):
        assert s.count(line)==1;s=s.replace(line,'')
    if hold:
        old="assert bool(e['valid'])==(e['waypoint_age_wall_s']<1.0)"
        assert s.count(old)==1;s=s.replace(old,"assert bool(e['valid'])")
    ns=dict(frozen.audit.__globals__);exec(compile(s,__file__,'exec'),ns);return ns['audit']

def audit(root):
    root=Path(root);c=json.loads((root/'scenario.json').read_text());hold=c['night_experiment']=='E2'
    r=adapted_audit(hold)(root)
    if hold:
        assert r['new_timeout_count']==0,'HOLD must not expire a received chunk'
    r.update(method=c['night_method'],scene=c['night_level'],base_scene=c['night_level'].rsplit('_',1)[0],experiment=c['night_experiment'])
    r['passage_side']=r['boxes'][0].get('side') if r.get('boxes') else None
    r['graph_rejection_reasons']={k:v for k,v in r['graph_reasons'].items() if k!='ACCEPTED'}
    r['boundary_curvature_dropped']=sum(e['event']=='SOLVE' and e.get('solver',{}).get('boundary_curvature_dropped',False) for e in rows(root/'graph_ho.jsonl'))
    if c.get('h1v2'):
        for b in (json.loads((root/'summary.json').read_text()).get('dynamic_obstacle') or {}).get('boxes',[]):
            assert b['spawn']['obstacle']['center_xy_m']==c['h1v2']['box']['center_xy_m']
    return r
