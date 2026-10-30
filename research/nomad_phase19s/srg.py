"""Geometry-only SP/SRG execution. Oracle evaluation is a separate final pass."""
import math
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase0.chunk_execution import protocol
from nomad_phase0.pure_pursuit import XYPath, PurePursuit
from nomad_phase18d.speed_profile import make_profile
from nomad_phase18d.rollout import Evaluator

DT = 1 / 72
CONTROL_DT = 1 / 9
TOLERANCE = .01


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def pivots(xy, B):
    """Merge short chords for turn detection only; retain native path geometry."""
    p = XYPath(xy)
    indices = [0]
    for i in range(1, len(p.points)):
        if np.linalg.norm(p.points[i] - p.points[indices[-1]]) >= .01:
            indices.append(i)
    if indices[-1] != len(p.points) - 1:
        if len(indices) > 1:
            indices.pop()
        indices.append(len(p.points) - 1)
    s0, _ = p.project(np.asarray(B)[:2])
    found = []
    for a, b, c in zip(indices, indices[1:], indices[2:]):
        u, v = p.points[b] - p.points[a], p.points[c] - p.points[b]
        if min(np.linalg.norm(u), np.linalg.norm(v)) < .01:
            continue
        incoming, outgoing = math.atan2(u[1], u[0]), math.atan2(v[1], v[0])
        delta = wrap(outgoing - incoming)
        if abs(delta) >= np.pi / 4 - 1e-12 and p.s[b] > s0 + 1e-12:
            found.append(dict(index=b, s_m=float(p.s[b]), xy=p.points[b].tolist(),
                              turn_rad=float(delta), outgoing_heading=float(outgoing)))
    return found


def stop_profile(xy):
    """Unchanged SP curvature limits, with a zero terminal speed and same passes."""
    plan = make_profile(xy)
    lim = np.array(plan['v_limit_m_s']); lim[-1] = 0.
    v = lim.copy(); ds = np.diff(plan['s_m'])
    for i in range(len(v) - 2, -1, -1):
        v[i] = min(v[i], np.sqrt(v[i + 1] ** 2 + ds[i]))
    for i in range(1, len(v)):
        v[i] = min(v[i], np.sqrt(v[i - 1] ** 2 + ds[i - 1]))
    return {**plan, 'v_limit_m_s': lim.tolist(), 'v_m_s': v.tolist()}


def simulate(B, xy, previous_v, rule, ticks=576):
    """No environment input. Commands update at 9Hz, exact SE(2) at 72Hz.

    SP preserves Phase18-D command calculations, extending only its horizon.
    A pivot leg removes the .05m/s floor to permit stopping. Reaching its 1cm
    tolerance starts bounded braking; rotation starts only after actual v=0.
    No position/yaw teleport and no oracle-dependent control or termination.
    """
    assert rule in ('SP', 'SRG') and 0 <= ticks <= 576
    assert 0 <= previous_v <= .3 + 1e-12
    pose = np.asarray(B, dtype=float).copy(); full = XYPath(xy)
    pivot_list = pivots(xy, B) if rule == 'SRG' else []
    ends = [p['index'] for p in pivot_list] + [len(full.points) - 1]
    leg = 0

    def follower_for(i):
        start = 0 if i == 0 else ends[i - 1]
        points = full.points[start:ends[i] + 1]
        f = PurePursuit(points, protocol()['follower'])
        plan = stop_profile(points) if i < len(pivot_list) else make_profile(points)
        return f, plan

    follower, plan = follower_for(0)
    commands = []; poses = [pose.copy()]; velocities = []; angular = []; phases = []; events = []
    v_prev = float(previous_v); v = w = 0.; mode = 'GO'; turn_target = None; turn_kind = None
    trig_s = trig_p = rotations = 0; rotation_ticks = 0; braking_ticks = 0
    first = next((q for q in full.points if np.linalg.norm(q - pose[:2]) >= .05), None)
    if rule == 'SRG' and previous_v < .01 and first is not None:
        target = float(np.arctan2(*(first - pose[:2])[::-1]))
        if abs(wrap(target - pose[2])) >= np.deg2rad(20) - 1e-12:
            turn_target = target; turn_kind = 'S'; mode = 'BRAKE'; trig_s = 1
            events.append(dict(event='TRIGGER_S', tick=0, pose=pose.tolist(), target=target))
    reason = 'TIME_LIMIT'; completed = False
    max_cte = full.project(pose[:2])[1]; travelled = 0.
    for tick in range(ticks):
        if tick % 8 == 0:
            if mode == 'ROTATE' and abs(wrap(turn_target - pose[2])) < 1e-10:
                events.append(dict(event='ROTATION_END', trigger=turn_kind, tick=tick, pose=pose.tolist()))
                if turn_kind == 'P':
                    leg += 1; follower, plan = follower_for(leg)
                mode = 'GO'
            if mode == 'GO':
                _, diag = follower.control(pose)
                if diag['endpoint_stop']:
                    if leg < len(pivot_list):
                        mode = 'BRAKE'; turn_kind = 'P'; trig_p += 1
                        turn_target = pivot_list[leg]['outgoing_heading']
                        events.append(dict(event='TRIGGER_P', tick=tick, pose=pose.tolist(),
                                           pivot=pivot_list[leg]['xy'], endpoint_distance_m=float(np.linalg.norm(pose[:2] - follower.path.points[-1]))))
                    else:
                        completed = True; reason = 'ENDPOINT'; break
            if mode == 'BRAKE' and v_prev <= 1e-12:
                mode = 'ROTATE'; rotations += 1
                events.append(dict(event='ROTATION_START', trigger=turn_kind, tick=tick, pose=pose.tolist(), target=turn_target))
            if mode == 'ROTATE':
                v = 0.; w = float(np.clip(wrap(turn_target - pose[2]) / CONTROL_DT, -.4, .4))
                target = 0.; kappa = None
            else:
                _, diag = follower.control(pose)
                x, y = diag['target_local_x_m'], diag['target_local_y_m']
                kappa = 2*y/(x*x+y*y) if x*x+y*y > 1e-24 else 0.
                projected, _ = follower.path.project(pose[:2])
                target = float(np.interp(projected, plan['s_m'], plan['v_m_s']))
                floor = 0. if mode == 'BRAKE' or leg < len(pivot_list) else .05
                target = 0. if mode == 'BRAKE' else float(np.clip(target, floor, .3))
                v = float(np.clip(target, max(floor, v_prev - .5/9), min(.3, v_prev + .5/9)))
                w = float(np.clip(v*kappa, -.4, .4))
            commands.append(dict(tick=tick, v=v, w=w, target=target, kappa=kappa,
                                 mode=mode, leg=leg, progress=follower.progress))
            v_prev = v
        pose = integrate_se2(pose, v, w, DT)
        poses.append(pose.copy()); velocities.append(v); angular.append(w); phases.append(mode)
        rotation_ticks += mode == 'ROTATE'; braking_ticks += mode == 'BRAKE'
        travelled += abs(v)*DT
        max_cte = max(max_cte, full.project(pose[:2])[1])
    # Exact deadline endpoint entry is counted, without executing another tick.
    if not completed and mode == 'GO' and leg == len(pivot_list) and np.linalg.norm(pose[:2]-full.points[-1]) <= TOLERANCE:
        completed = True; reason = 'ENDPOINT'
    duration = len(velocities)*DT
    end_projection = full.project(pose[:2])[0]; initial_projection = full.project(np.asarray(B)[:2])[0]
    return dict(poses=np.array(poses), commands=commands, speeds=velocities, omegas=angular, phases=phases,
                events=events, pivots=pivot_list, completed=completed, termination=reason,
                incomplete_reason=None if completed else ('ROTATING' if mode == 'ROTATE' else 'BRAKING' if mode == 'BRAKE' else 'FOLLOWING'),
                duration_s=duration, completion_time_s=duration if completed else None,
                path_length_m=float(full.s[-1]), remaining_path_length_m=float(full.s[-1]-initial_projection),
                completion_average_speed_m_s=float(full.s[-1]/duration) if completed and duration else None,
                actual_average_speed_m_s=travelled/duration if duration else 0., distance_m=travelled,
                arclength_progress_m=float(max(0.,end_projection-initial_projection)),
                rotation_time_s=rotation_ticks*DT, braking_time_s=braking_ticks*DT, rotations=rotations,
                trigger_S=trig_s, trigger_P=trig_p, trigger_any=bool(trig_s or trig_p), pivot_candidates=len(pivot_list),
                omega_saturation_fraction=float(np.mean(np.abs(angular)>=.399)) if angular else 0.,
                translation_omega_saturation_fraction=float(np.mean(np.abs(np.array(angular)[np.array(velocities)>0])>=.399)) if any(vv>0 for vv in velocities) else 0.,
                max_cross_track_m=max_cte, endpoint_distance_m=float(np.linalg.norm(pose[:2]-full.points[-1])),end_pose=pose.tolist())


def evaluate(result, config):
    """Passive exact/swept oracle checks after geometry-only command generation."""
    ev = Evaluator(config); p = result['poses']
    minimum, obstacle, wall, witness = ev.interval(p[0],0.,0.,0.)
    first = 0 if minimum < 0 else None
    legacy = dict(minimum_clearance_m=minimum, overlap=minimum<0, distance_m=0., duration_s=0.) if first==0 else None
    distance = 0.
    for i,(v,w) in enumerate(zip(result['speeds'],result['omegas'])):
        gap,bg,wg,upper = ev.interval(p[i],v,w,DT)
        minimum=min(minimum,gap);obstacle=min(obstacle,bg);wall=min(wall,wg);witness=min(witness,upper)
        if gap<0 and first is None:first=i+1
        distance += abs(v)*DT
        if legacy is None and (gap<0 or i+1==108 or i+1==len(result['speeds'])):
            legacy=dict(minimum_clearance_m=minimum,overlap=minimum<0,distance_m=distance,duration_s=(i+1)*DT)
    if legacy is None:legacy=dict(minimum_clearance_m=minimum,overlap=minimum<0,distance_m=0.,duration_s=0.)
    return {**result,'minimum_clearance_m':minimum,'minimum_obstacle_clearance_m':obstacle,
            'minimum_wall_clearance_m':wall,'overlap':bool(minimum<0),'margin_violation':bool(minimum<.025),
            'geometric_negative_witness':bool(witness<0),'conservative_only_negative':bool(minimum<0 and witness>=0),
            'first_overlap_tick':first,'first_overlap_time_s':first*DT if first is not None else None,
            'safe_completion':bool(result['completed'] and minimum>=0),'legacy_1p5s_prefix':legacy}


def rollout(B,xy,previous_v,rule,config,ticks=576):
    return evaluate(simulate(B,xy,previous_v,rule,ticks),config)
