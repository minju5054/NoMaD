"""Frozen descriptive pilot labels and complete-pair technical exclusions."""
from .config import PRIMARY

def exclusions(rows):
    return sorted({(r['scene'],r['index']) for r in rows if r['method'] in PRIMARY and r['technical_validation']!='PASS'})

def classify(summary):
    def row(group,method):return next(r for r in summary if r['group']==group and r['method']==method)
    g=row('SUDDEN','C0');checks={}
    for m in ('B1_SAFE_TE','B2_SAFE_RTC','B3_SAFE_ROTATE'):
        c=row('SUDDEN',m);checks[m]=g['goal']>=c['goal']+2 and g['collision']<=c['collision']
    a=row('SUDDEN','B4_ASTAR');safe=g['collision']<=a['collision']
    # Literal registered clauses: BETTER is the goal+2 clause; the collision
    # condition is explicit in NONINFERIOR. Report collisions independently.
    astar='BETTER' if g['goal']>=a['goal']+2 else 'NONINFERIOR' if safe and g['goal']>=a['goal']-1 else 'WORSE'
    gs=row('STATIC','C0');bs=row('STATIC','B3_SAFE_ROTATE');static=gs['goal']>=bs['goal']-1 and gs['collision']<=bs['collision']
    label='PILOT_SUPPORTS' if all(checks.values()) and astar!='WORSE' and static else 'PILOT_AGAINST' if not checks['B3_SAFE_ROTATE'] and astar=='WORSE' else 'PILOT_MIXED'
    return dict(label=label,C0_BETTER_vs=checks,C0_vs_ASTAR=astar,STATIC_OK=static,
                satisfied=[k for k,v in checks.items() if v]+(['ASTAR'] if astar!='WORSE' else [])+(['STATIC_OK'] if static else []),
                unsatisfied=[k for k,v in checks.items() if not v]+(['ASTAR'] if astar=='WORSE' else [])+(['STATIC_OK'] if not static else []))
