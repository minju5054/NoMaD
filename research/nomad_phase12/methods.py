"""Geometry-only transition kernels. No obstacles, goal, model or optimization."""
import numpy as np
from nomad_phase0.pure_pursuit import XYPath,PurePursuit
from nomad_phase0.chunk_execution import protocol
from nomad_phase9.intent import hermite

PATH_BASELINES=('HERMITE-SPLICE','TEMPORAL-ENSEMBLE','BID-COHERENCE')
GF='FRESHEST+GRAPH-GF'
NEW=(*PATH_BASELINES,GF)


def tangent(path,s):
    i=min(int(np.searchsorted(path.s,s,side='right')-1),len(path.delta)-1)
    return path.delta[i]/path.lengths[i]


def hermite_splice(xy,b):
    path=XYPath(xy);b=np.asarray(b);s,_=path.project(b[:2]);sj=min(s+.30,float(path.s[-1]));j=path.at(sj)
    length=float(np.linalg.norm(j-b[:2]))
    if length<=1e-12:raise ValueError('DEGENERATE_HERMITE: J coincides with B')
    ta=length*np.array([np.cos(b[2]),np.sin(b[2])]);tj=length*tangent(path,sj)
    # Fixed high-resolution arc-length quadrature, no scene/result-based tuning.
    grid=np.linspace(0.,1.,4097);dense=hermite(b[:2],j,ta,tj,grid)
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
    queries=np.r_[np.arange(0.,arc[-1],.02),arc[-1]];u=np.interp(queries,arc,grid)
    curve=hermite(b[:2],j,ta,tj,u);curve[0]=b[:2];curve[-1]=j
    tail=path.points[path.s>sj+1e-12];out=np.vstack([curve,tail])
    XYPath(out)
    return out,dict(kind='HERMITE-SPLICE',projected_s_m=s,join_s_m=sj,join_xy=j.tolist(),join_tangent=(tj/length).tolist(),
        tangent_start=ta.tolist(),tangent_end=tj.tolist(),curve_points=len(curve),join_endpoint_clamped=bool(s+.30>path.s[-1]),
        analytic_c1=True,sampling_step_m=.02,quadrature_points=4097)


def coherence_score(old,fresh,b):
    so,_=old.project(b[:2]);sf,_=fresh.project(b[:2]);common=float(min(old.s[-1]-so,fresh.s[-1]-sf))
    if common<.02:return None,common
    samples=np.r_[np.arange(0.,common,.01),common]
    a=np.array([old.at(so+s) for s in samples]);c=np.array([fresh.at(sf+s) for s in samples])
    return float(np.linalg.norm(a-c,axis=1).mean()),common


def bid_select(samples,b,old_xy):
    candidates=[]
    try:old=XYPath(old_xy) if old_xy is not None else None
    except ValueError:old=None
    for i,xy in enumerate(samples):
        try:
            path=XYPath(xy);score,common=coherence_score(old,path,b) if old is not None else (None,0.)
            candidates.append(dict(index=i,score_m=score,common_length_m=common,path_valid=True))
        except ValueError:candidates.append(dict(index=i,score_m=None,common_length_m=0.,path_valid=False))
    eligible=[c for c in candidates if c['score_m'] is not None]
    selected=min(eligible,key=lambda c:(c['score_m'],c['index']))['index'] if eligible else 0
    return np.asarray(samples[selected]),dict(kind='BID-COHERENCE',selected_sample=selected,candidates=candidates,
        fallback=None if eligible else 'NO_VALID_OLD' if old is None else 'COMMON_LENGTH_BELOW_2CM')


class TemporalTargets:
    """ACT temporal ensembling (spatial adaptation), independent PP progress."""
    def __init__(self):self.chunks=[]
    def push(self,xy,identifier,received_ns):
        try:follower=PurePursuit(xy,protocol()['follower'])
        except ValueError:return False
        self.chunks.append(dict(id=identifier,received_ns=received_ns,follower=follower));self.chunks=self.chunks[-3:]
        return True
    def control(self,pose,now_ns):
        self.chunks=[c for c in self.chunks if 0<=now_ns-c['received_ns']<1_000_000_000]
        if not self.chunks:return None,dict(chunk_count=0,chunk_ids=[],weights=[],components=[])
        weights=np.exp(-.5*np.arange(len(self.chunks)));weights/=weights.sum();details=[];components=[]
        for c,w in zip(self.chunks,weights):
            _,diag=c['follower'].control(pose);details.append(diag)
            components.append(dict(id=c['id'],received_ns=c['received_ns'],weight=float(w),world_xy=c['follower'].path.points.tolist(),
                progress_m=c['follower'].progress,target_xy=[diag['target_x_m'],diag['target_y_m']],
                endpoint_clamped=bool(c['follower'].progress+.25>c['follower'].path.s[-1])))
        targets=np.array([[d['target_x_m'],d['target_y_m']] for d in details]);target=weights@targets
        delta=target-np.asarray(pose)[:2];c,s=np.cos(pose[2]),np.sin(pose[2]);local=np.array([[c,s],[-s,c]])@delta
        stop=all(d['endpoint_stop'] for d in details)
        diag=dict(target_x_m=float(target[0]),target_y_m=float(target[1]),target_local_x_m=float(local[0]),target_local_y_m=float(local[1]),
                  endpoint_stop=stop,endpoint_clamped=any(x['endpoint_clamped'] for x in components),
                  progress_m=float(weights@np.array([d['progress_m'] for d in details])),
                  target_s_m=None,cross_track_error_m=float(weights@np.array([d['cross_track_error_m'] for d in details])))
        return diag,dict(chunk_count=len(self.chunks),chunk_ids=[c['id'] for c in self.chunks],weights=weights.tolist(),components=components,
            component_clamp_fraction=float(weights@np.array([x['endpoint_clamped'] for x in components])))


class TransitionState:
    def __init__(self,method):
        assert method in PATH_BASELINES
        self.method=method;self.old_xy=None;self.old_received_ns=None;self.ensemble=TemporalTargets()
    def switch(self,samples,b,identifier,received_ns,now_ns):
        samples=np.asarray(samples);raw=samples[0];detail=dict(kind=self.method,selected_sample=0)
        if self.method=='HERMITE-SPLICE':
            try:xy,meta=hermite_splice(raw,b);detail.update(meta)
            except ValueError as exc:xy=np.repeat(np.asarray(b)[None,:2],2,axis=0);detail['invalid_reason']=str(exc)
        elif self.method=='BID-COHERENCE':
            valid=self.old_received_ns is not None and 0<=now_ns-self.old_received_ns<1_000_000_000
            xy,meta=bid_select(samples,b,self.old_xy if valid else None);detail.update(meta)
        else:
            xy=raw;detail['added']=self.ensemble.push(raw,identifier,received_ns)
        self.old_xy=np.array(xy,copy=True);self.old_received_ns=received_ns
        return xy,detail


def freshest(samples,b):
    """No geometry/config argument; only the eight world paths and actual B."""
    assert not isinstance(samples,dict) and not isinstance(b,dict), 'Geometry objects forbidden'
    samples=np.asarray(samples,dtype=float);b=np.asarray(b,dtype=float)
    assert samples.shape==(8,8,2) and b.shape==(3,) and np.isfinite(samples).all() and np.isfinite(b).all()
    candidates=[]
    for i,xy in enumerate(samples):
        try:
            path=XYPath(xy);s,d=path.project(b[:2]);remaining=float(path.s[-1]-s)
        except ValueError:s=d=remaining=None
        candidates.append(dict(index=i,path_valid=remaining is not None,projected_arclength_m=s,projection_distance_m=d,remaining_length_m=remaining))
    valid=[c for c in candidates if c['path_valid']]
    index=min(valid,key=lambda c:(-c['remaining_length_m'],c['index']))['index'] if valid else 0
    return samples[index],dict(kind='FRESHEST',selected_sample=index,candidates=candidates,
        fallback=None if valid else 'NO_VALID_PATH',oracle_used=False)
