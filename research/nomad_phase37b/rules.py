"""Filter component cells only; retain the original identity, u_ref and rules."""
import inspect
from types import SimpleNamespace,FunctionType
import numpy as np
from nomad_phase24r import trigger as original
from nomad_phase20f.direction import inside_rectangle,component_direction
from nomad_phase20c.detour_known import radial_reference

_source=inspect.getsource(original.component_sets)
_old='mask=snapshot.occupied&snapshot.observed&(snapshot.new_component_ids>0)'
assert _source.count(_old)==1
_namespace=dict(original.component_sets.__globals__)
exec(_source.replace(_old,_old+'&snapshot.provenance_mask'),_namespace)
component_sets=_namespace['component_sets']
choose_ahead=FunctionType(original.choose_ahead.__code__,dict(original.choose_ahead.__globals__,component_sets=component_sets),
    original.choose_ahead.__name__,original.choose_ahead.__defaults__,original.choose_ahead.__closure__)


def view(field,mask):
    return SimpleNamespace(**vars(field),provenance_mask=np.asarray(mask,dtype=bool))


def evaluate(field,mask,poses,tick):
    subset=view(field,mask);sets=component_sets(subset);chosen,_=choose_ahead(subset,poses,tick,{})
    u=np.array(chosen['u_ref']) if chosen else radial_reference(poses,tick)[0]
    forward=float((poses[tick,:2]-poses[tick-216,:2])@u)
    drop=original.approach_progress(sets[chosen['component_id']],poses[tick-216],poses[tick])[0] if chosen else None
    fire=bool(chosen and (forward<.2 or (drop is not None and drop<.1)))
    return dict(fire=fire,u_ref=u,component=chosen,sets=sets,forward=forward,drop=drop)


def candidate_list(field,sets,poses,tick):
    candidates=[]
    for identity,points in sets.items():
        birth=field.component_births[identity];u,_=component_direction(poses,birth)
        if original.passed(points,poses[tick],u,field.radius,field.h):continue
        if inside_rectangle(points,poses[tick],u).any():candidates.append((birth,identity,u,points))
    return sorted(candidates,key=lambda x:(x[0],x[1]))


def outcome_envelope(field,confirmed,possible,poses,tick):
    """Conservative possible fires/selected IDs for unrecorded past evidence.

    Candidate membership is monotone under adding cells, but selection and the
    distance-drop predicate are not. Thus confirmed-only and all-possible
    replays are not falsely called statistical lower/upper bounds.
    """
    low=component_sets(view(field,confirmed));high=component_sets(view(field,possible))
    guaranteed=candidate_list(field,low,poses,tick);allowed=candidate_list(field,high,poses,tick)
    cutoff=guaranteed[0][:2] if guaranteed else None;out=[]
    if cutoff is None:out.append(dict(fire=False,component_id=None,u_ref=None))
    for birth,identity,u,points in allowed:
        if cutoff is not None and (birth,identity)>cutoff:break
        forward=float((poses[tick,:2]-poses[tick-216,:2])@u)
        if forward<.2:flags=[True];drop_low=drop_high=None
        else:
            old_dist=np.linalg.norm(points-poses[tick-216,:2],axis=1);new_dist=np.linalg.norm(points-poses[tick,:2],axis=1)
            mandatory=low.get(identity)
            if mandatory is not None:
                old_upper=float(np.linalg.norm(mandatory-poses[tick-216,:2],axis=1).min())
                new_upper=float(np.linalg.norm(mandatory-poses[tick,:2],axis=1).min())
            else:old_upper=float(old_dist.max());new_upper=float(new_dist.max())
            drop_low=float(old_dist.min())-new_upper;drop_high=old_upper-float(new_dist.min())
            flags=[True] if drop_high<.1 else [False] if drop_low>=.1 else [False,True]
        for flag in flags:out.append(dict(fire=flag,component_id=identity,t_new_tick=birth,u_ref=u,forward=forward,drop_lower=drop_low,drop_upper=drop_high))
    assert out
    return out
