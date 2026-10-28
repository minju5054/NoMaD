"""Frozen confirmatory decisions; exact Bonferroni alpha=.05/3."""
import numpy as np
from .config import METHODS,PROPOSED,SCENES


def valid(r):return r.get('technical_validation')=='PASS'


def counts(records,method,scene=None):
    rr=[r for r in records if r['method']==method and (scene is None or r['scene']==scene)]
    vv=[r for r in rr if valid(r)]
    return dict(method=method,scene=scene or 'ALL',planned=24 if scene is None else 8,attempted=len(rr),valid=len(vv),
        technical_failures=sum(not valid(r) for r in rr),success=sum(bool(r.get('success')) for r in vv),
        safety_failures=sum(bool(r.get('collision') or r.get('corridor')) for r in vv),
        collision=sum(bool(r.get('collision')) for r in vv),corridor=sum(bool(r.get('corridor')) for r in vv),
        timeout=sum(bool(r.get('stuck')) for r in vv))


def paired(records,other,key,alpha=.05/3,scene=None):
    lookup={(r['scene'],r['index'],r['method']):r for r in records if valid(r) and r.get(key) is not None}
    values=[]
    for sc in ([scene] if scene else SCENES):
        for i in range(66,74):
            a,b=lookup.get((sc,i,PROPOSED)),lookup.get((sc,i,other))
            if a is not None and b is not None:values.append(dict(scene=sc,index=i,difference=float(a[key]-b[key])))
    ci=None;mean=None
    if values:
        ids=sorted({x['index'] for x in values});clusters=[[x['difference'] for x in values if x['index']==i] for i in ids]
        sums=np.array([sum(x) for x in clusters]);size=np.array([len(x) for x in clusters])
        draws=np.random.default_rng(20261030).integers(0,len(ids),(20000,len(ids)))
        boot=sums[draws].sum(axis=1)/size[draws].sum(axis=1)
        ci=np.quantile(boot,[alpha/2,1-alpha/2]).tolist();mean=float(sums.sum()/size.sum())
    return dict(scene=scene or 'ALL',method=PROPOSED,comparator=other,metric=key,n=len(values),
        seed_clusters=len({x['index'] for x in values}),mean_difference=mean,ci=ci,confidence=1-alpha,pairs=values)


def speed_label(p):
    if p['n']<12:return 'INSUFFICIENT_PAIRS'
    if p['ci'][1]<0:return 'FASTER'
    if p['ci'][0]>0:return 'SLOWER'
    return 'INCONCLUSIVE'


def composite(faster,noninferior,safety_ok):
    if noninferior is None or safety_ok is None:return 'INCONCLUSIVE'
    n=sum((faster,noninferior,safety_ok))
    return 'CONFIRMED' if n==3 else 'PARTIAL' if n==2 else 'NOT_CONFIRMED'


def decisions(records,technical_rule):
    assert technical_rule in ('INCONCLUSIVE','COUNT_AS_PLANNED')
    primary=[]
    for other in METHODS[1:4]:
        p=paired(records,other,'checkpoint_time_s');a,b=counts(records,PROPOSED),counts(records,other)
        complete=a['valid']==a['planned'] and b['valid']==b['planned']
        ni=a['success']>=b['success']-3;safe=a['safety_failures']<=b['safety_failures']+1
        if not complete and technical_rule=='INCONCLUSIVE':ni=safe=None
        h1=speed_label(p)
        primary.append({**p,'H1':h1,'CLR_success':a['success'],'comparator_success':b['success'],
            'CLR_safety_failures':a['safety_failures'],'comparator_safety_failures':b['safety_failures'],
            'CLR_valid':a['valid'],'comparator_valid':b['valid'],'data_complete':complete,
            'H2':'INCONCLUSIVE' if ni is None else 'NONINFERIOR' if ni else 'NOT_NONINFERIOR',
            'safety':'INCONCLUSIVE' if safe is None else 'SAFETY_OK' if safe else 'SAFETY_NOT_OK',
            'combined':composite(h1=='FASTER',ni,safe)})
    auxiliary=[]
    for other,key in [(METHODS[4],'minimum_oracle_clearance_m'),(METHODS[4],'checkpoint_time_s'),(METHODS[0],'checkpoint_time_s')]:
        p=paired(records,other,key,.05)
        p['label']='CLEARANCE_LARGER' if key=='minimum_oracle_clearance_m' and p['ci'] and p['ci'][0]>0 else 'NOT_SHOWN' if key=='minimum_oracle_clearance_m' else 'DESCRIPTIVE'
        auxiliary.append(p)
    descriptive=[]
    for sc in SCENES:
        for other in METHODS[1:4]:
            p=paired(records,other,'checkpoint_time_s',scene=sc)
            p.update(CLR_counts=counts(records,PROPOSED,sc),comparator_counts=counts(records,other,sc),scope='scene-specific descriptive; no additional primary hypothesis')
            descriptive.append(p)
    return dict(experiment='사전 등록 확인 실험',primary=primary,auxiliary=auxiliary,scene_descriptive=descriptive,
        overall='ALL_CONFIRMED' if all(r['combined']=='CONFIRMED' for r in primary) else None,
        technical_failure_rule=technical_rule)
