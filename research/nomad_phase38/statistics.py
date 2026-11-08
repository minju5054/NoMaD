"""Paired, cumulative descriptive inference. No failed measurement imputation."""
import numpy as np
from scipy.stats import binomtest

COMPARISONS=(('OURS','NOMAD_RAW'),('OURS','TE'),('OURS','RTC'),('OURS','CARE'),
             ('TE','TE+EC'),('RTC','RTC+EC'),('OURS-DETOUR','OURS'),('ASTAR+EC','OURS'))
REPS=20000
SEED=20261111

def holm(values):
    p=np.asarray(values,float);order=np.argsort(p,kind='stable');out=np.empty(len(p));highest=0.
    for rank,i in enumerate(order):
        highest=max(highest,(len(p)-rank)*p[i]);out[i]=min(1.,highest)
    return out.tolist()

def paired(rows,a,b):
    groups={}
    for row in rows:
        key=(row['scene'],row['index']);groups.setdefault(key,{})[row['method']]=row
    matched=[];missing=[]
    for key,g in sorted(groups.items()):
        x,y=g.get(a),g.get(b)
        if x and y and all(r.get('technical_validation')=='PASS' and r.get('collision') is not None for r in (x,y)):
            matched.append((x,y))
        else:missing.append(dict(scene=key[0],index=key[1],reason='Missing/technical failure in pair'))
    return matched,missing

def bootstrap_pairs(differences,scenes):
    """Within each scene, resample whole matched scene×seed pairs; 20k draws."""
    d=np.asarray(differences,float);scenes=np.asarray(scenes)
    if not len(d):return None,None
    rng=np.random.default_rng(SEED);sums=np.zeros(REPS)
    for scene in sorted(set(scenes)):
        values=d[scenes==scene];sums+=values[rng.integers(0,len(values),(REPS,len(values)))].sum(axis=1)
    return tuple(float(v) for v in np.quantile(sums/len(d),[.025,.975]))

def analyze(rows,methods):
    tests=[];details=[];noninferiority=[]
    for a,b in COMPARISONS:
        pairs,missing=paired(rows,a,b)
        for metric in ('success','collision'):
            n10=sum(bool(x[metric]) and not bool(y[metric]) for x,y in pairs)
            n01=sum(not bool(x[metric]) and bool(y[metric]) for x,y in pairs)
            p=float(binomtest(n10,n10+n01,.5).pvalue) if n10+n01 else 1.
            tests.append(dict(left=a,right=b,metric=metric,n=len(pairs),left_only=n10,right_only=n01,
                p_exact=p,excluded_pairs=len(missing),estimable=bool(pairs)))
        for x,y in pairs:
            details.append(dict(left=a,right=b,scene=x['scene'],index=x['index'],left_goal=x['success'],right_goal=y['success'],
                left_collision=x['collision'],right_collision=y['collision'],
                arrival_delta_s=x['goal_time_s']-y['goal_time_s'] if x['success'] and y['success'] else None))
    for row,p in zip(tests,holm([r['p_exact'] for r in tests])):row.update(p_holm=p,holm_family_size=len(tests))
    for other in methods:
        if other=='OURS':continue
        pairs,missing=paired(rows,'OURS',other)
        delta=[int(x['success'])-int(y['success']) for x,y in pairs];lo,hi=bootstrap_pairs(delta,[x['scene'] for x,_ in pairs])
        label='INSUFFICIENT_DATA' if not delta else 'NONINFERIOR' if lo>=-.10-1e-12 else 'INFERIOR' if hi<-.10 else 'INCONCLUSIVE'
        noninferiority.append(dict(left='OURS',right=other,n=len(delta),goal_delta_pp=float(np.mean(delta)*100) if delta else None,
            ci95_low_pp=lo*100 if lo is not None else None,ci95_high_pp=hi*100 if hi is not None else None,
            margin_pp=-10.,label=label,excluded_pairs=len(missing)))
    return tests,details,noninferiority
