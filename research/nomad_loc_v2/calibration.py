"""Fit only approved calibration data. No evaluation argument is accepted."""
from collections import Counter
import numpy as np
from .data import load,tangents
BIN_WIDTH=.5;LAPLACE=1.

def offset_bin(k):return int(k)+4 if -4<=int(k)<=4 else 9

def contributions(item,heartbeat=None):
    assert item['split']=='CAL'
    events,xy,spacing,stop,missing=load(item);direction=tangents(xy);counts=[Counter() for _ in range(10)];residuals=[];skipped_pairs=0
    previous=None
    for e in events:
        for j,d in zip(e['ids'],e['distances']):counts[offset_bin(j-e['true_node'])][int(np.floor(d/BIN_WIDTH))]+=1
        if previous is not None:
            if e['id']!=previous['id']+1:skipped_pairs+=1
            else:
                s=float((np.asarray(e['odometry_xy'])-previous['odometry_xy'])@direction[previous['logged_map']])
                residuals.append(float(e['true_node']-previous['true_node']-s/spacing))
        previous=e
        if heartbeat:heartbeat(e['id'])
    return dict(uid=item['uid'],phase=item['phase'],run_count=1,inference_count=len(events),missing_events=missing,skipped_pairs=skipped_pairs,
        histogram=[{str(k):v for k,v in c.items()} for c in counts],residuals=residuals,
        input_sha256=item['input_sha256'])

def fit(parts):
    if not parts:raise ValueError('No calibration runs')
    hist=[Counter() for _ in range(10)];res=[]
    for p in parts:
        for row,counts in zip(hist,p['histogram']):row.update({int(k):v for k,v in counts.items()})
        res.extend(p['residuals'])
    ids=[k for row in hist for k in row]
    if not ids or len(res)<2:raise ValueError('Insufficient calibration observations or adjacent pairs')
    lo=min(ids);hi=max(ids);counts=np.zeros((10,hi-lo+3),dtype=np.int64)
    # Fixed underflow and overflow bins; extent comes from calibration only.
    for i,row in enumerate(hist):
        for b,n in row.items():counts[i,1+b-lo]=n
    prob=(counts+LAPLACE)/(counts.sum(axis=1,keepdims=True)+LAPLACE*counts.shape[1])
    variance=float(np.var(res,ddof=0))
    if not np.isfinite(variance) or variance<=0:raise ValueError('Zero/nonfinite SIGN variance; no tuned floor is allowed')
    return dict(status='FROZEN_CALIBRATION',bin_width=BIN_WIDTH,laplace=LAPLACE,distance_floor_min=lo,distance_floor_max=hi,
        distance_bin_count=counts.shape[1],offset_rows=list(range(-4,5))+['OUTSIDE'],counts=counts.tolist(),probabilities=prob.tolist(),
        sigma2=variance,residual_mean=float(np.mean(res)),residual_count=len(res),variance_ddof=0,
        tangent_calibration='previous inference logged HMM0 MAP; central node difference,one-sided ends',
        run_count=len(parts),inference_count=sum(p['inference_count'] for p in parts),candidate_distance_count=int(counts.sum()),
        by_phase=[dict(phase=phase,runs=sum(p['phase']==phase for p in parts),inferences=sum(p['inference_count'] for p in parts if p['phase']==phase),
            adjacent_pairs=sum(len(p['residuals']) for p in parts if p['phase']==phase)) for phase in sorted({p['phase'] for p in parts})])

def obs_log_emission(model,ids,distances):
    ids=np.asarray(ids,int);d=np.asarray(distances,float);lo=model['distance_floor_min'];hi=model['distance_floor_max'];nb=model['distance_bin_count']
    raw=np.floor(d/model['bin_width']).astype(int);bins=np.where(raw<lo,0,np.where(raw>hi,nb-1,1+raw-lo))
    probabilities=np.asarray(model['probabilities'],float);result=[]
    for i in ids:
        offsets=np.array([offset_bin(j-i) for j in ids]);result.append(float(np.log(probabilities[offsets,bins]).sum()))
    return np.array(result)
