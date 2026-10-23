"""Frozen v5.1 timing and executed-command policy, shared by replay/runtime."""
import math
import numpy as np
from nomad_isaac.common import integrate_se2
from .execution import command_policy as v5_command


def candidates(pose,command):
    return {str(n):integrate_se2(np.asarray(pose),*command,n/9).tolist() for n in (1,2)}


def expected_tick(completed_durations,dispatch_phase_s=0.):
    # Causal estimate only. No current solve result or future stored pose is used.
    estimate=float(np.median(completed_durations[-20:])) if completed_durations else .1
    return min(2,max(1,math.ceil((estimate+dispatch_phase_s)*9))),estimate


def command_policy(kappa,previous_v,profile=None,projected_s=0.):
    if profile is None:
        command,flags=v5_command('CURV-SPEED',kappa,previous_v)
        flags.update(execution_policy='CURV-SPEED_FALLBACK');return command,flags
    target=float(np.clip(np.interp(projected_s,profile['s_m'],profile['v_m_s']),.05,.3))
    v=float(np.clip(target,max(.05,previous_v-.5/9),min(.3,previous_v+.5/9)))
    w=float(np.clip(v*kappa,-.4,.4))
    return (v,w),{'execution_policy':'GRAPH_PROFILE_ACCEL_LIMITED','v_target_m_s':target,
        'CURVATURE_SATURATED':bool(abs(kappa)>8),'ACCEL_LIMITED':bool(abs(v-target)>1e-12),
        'OMEGA_CLIPPED':bool(abs(w-v*kappa)>1e-12),'temporal_acceleration_exceeds_limit':bool(abs(v-previous_v)>.5/9+1e-12),
        'profile_projected_s_m':float(projected_s)}


def decision(result,latest_id,valid,pose,predicted_candidates,actual_tick_offset):
    duration=(result['worker_end_ns']-result['worker_start_ns'])/1e9;stale=duration>.3
    predicted=predicted_candidates.get(str(actual_tick_offset))
    mismatch=float(np.linalg.norm(np.asarray(pose)[:2]-np.asarray(predicted)[:2])) if predicted is not None else None
    if result['id']!=latest_id:status='SUPERSEDED'
    elif stale:status='STALE'
    elif not valid:status='WAYPOINT_EXPIRED'
    elif result.get('initialization_rejected'):status='INITIALIZATION_REJECTED'
    elif result.get('error'):status='SOLVER_ERROR'
    elif not result['solver']['success']:status='NONCONVERGED'
    elif not result['accepted']:status='CONSTRAINT_FAILED'
    elif predicted is None or mismatch>.03:status='APP_MISMATCH'
    else:status='ACCEPTED'
    return status,stale,duration,{'actual_tick_offset':actual_tick_offset,'matched_B_app':predicted,
        'app_mismatch_m':mismatch,'candidate_available':predicted is not None}
