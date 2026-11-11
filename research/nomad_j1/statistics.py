"""Preregistered seed-cluster bootstrap + exact paired McNemar, Holm family2."""
import numpy as np
from scipy.stats import binomtest
from .config import SCENES,INDICES,METHODS

def completed_seeds(records):
    keys={(r['scene'],r['index'],r['method']) for r in records}
    return [i for i in INDICES if all((s,i,m) in keys for s in SCENES for m in METHODS)]

def primary(records):
    complete=completed_seeds(records)
    lookup={(r['scene'],r['index'],r['method']):r for r in records if r.get('technical_validation')=='PASS' and r['index'] in complete}
    differences=[];discordant=[0,0];pairs=0
    for scene in SCENES:
        for i in complete:
            ours=lookup.get((scene,i,'OURS'));rtc=lookup.get((scene,i,'RTC-hard'));noec=lookup.get((scene,i,'OURS-noEC'))
            if ours and rtc and ours.get('checkpoint_time_s') is not None and rtc.get('checkpoint_time_s') is not None:
                differences.append(dict(scene=scene,index=i,difference_s=ours['checkpoint_time_s']-rtc['checkpoint_time_s']))
            if ours and noec:
                pairs+=1;a=bool(ours['collision'] or ours['wall_intrusion']);b=bool(noec['collision'] or noec['wall_intrusion'])
                discordant[0]+=a and not b;discordant[1]+=b and not a
    speed=dict(comparison='OURS − RTC-hard',metric='checkpoint_time_s',pairs=len(differences),mean_difference_s=None,ci95_s=None,p_raw=None)
    if differences:
        ids=sorted({x['index'] for x in differences});clusters=[[x['difference_s'] for x in differences if x['index']==i] for i in ids]
        sums=np.array([sum(x) for x in clusters]);sizes=np.array([len(x) for x in clusters]);mean=float(sums.sum()/sizes.sum())
        draws=np.random.default_rng(20261030).integers(0,len(ids),(20000,len(ids)))
        boot=sums[draws].sum(axis=1)/sizes[draws].sum(axis=1)
        p=float((1+np.sum(np.abs(boot-mean)>=abs(mean)))/(len(boot)+1))
        speed.update(seed_clusters=len(ids),mean_difference_s=mean,ci95_s=np.quantile(boot,[.025,.975]).tolist(),p_raw=p)
    total=sum(discordant);safety=dict(comparison='OURS vs OURS-noEC',metric='collision OR wall intrusion',pairs=pairs,
        OURS_only_failure=int(discordant[0]),noEC_only_failure=int(discordant[1]),
        p_raw=float(binomtest(discordant[0],total,.5).pvalue) if total else 1. if pairs else None)
    results=[speed,safety];order=sorted(range(2),key=lambda k:results[k]['p_raw'] if results[k]['p_raw'] is not None else 1.)
    running=0.
    for rank,k in enumerate(order):
        value=results[k]['p_raw'];running=max(running,(2-rank)*(value if value is not None else 1.))
        results[k]['p_holm']=min(1.,running) if value is not None else None
    final=len(complete)==13
    for row in results:row['decision']='판정 보류' if not final else 'REJECT_H0' if row['p_holm'] is not None and row['p_holm']<.05 else 'NOT_REJECTED'
    return dict(completed_seeds=complete,completed_seed_count=len(complete),final=final,
                label='최종 결과' if final else '중간 결과, 판정 보류',primary=results,checkpoint_pairs=differences)
