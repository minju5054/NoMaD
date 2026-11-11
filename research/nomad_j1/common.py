"""Scene-only reuse plus the frozen Phase18 timing/controller configuration."""
import json
import math
from nomad_isaac.common import ROOT
from nomad_phase18 import config as phase18

METHOD = 'OURS-noEC'

def scene_config(name):
    if name in ('SLW', 'LC', 'CL'):
        c = phase18.scene(name)
        manifest = phase18.protocol()['topomaps'][name]['manifest']
    else:
        from nomad_phase26.config import runtime_config as scene_runtime
        c = scene_runtime('B3_SAFE_ROTATE', 95, level='H1' if name == 'H1-v2' else name)
        if name == 'H1-v2':
            from nomad_h1v2.scene import configure
            c = configure(c)
        manifest = c['topomap_manifest']
        # Keep geometry, spawn rules and assets only; none of the newer method
        # factories, localization adapters or decision layers are installed.
        keep = {'phase16_scene', 'phase26_spawn', 'phase26_dynamic'}
        for key in list(c):
            if key.startswith(('phase', 'overnight_')) and key not in keep:
                c.pop(key)
    return c, manifest

def half_extent(box, axis):
    yaw = float(box.get('yaw_rad', math.radians(box.get('yaw_deg', 0.))))
    x, y = map(lambda z: z / 2, box['size_xyz_m'][:2])
    return abs(math.cos(yaw)) * (x if axis == 0 else y) + abs(math.sin(yaw)) * (y if axis == 0 else x)

def checkpoint_spec(name):
    c, _ = scene_config(name)
    axis = 1 if name in ('LC', 'H1-v2') else 0
    if name == 'H2':
        return dict(axis=0, direction=1, box_id='DynamicObstacle2', dynamic=True,
                    threshold_m=None, formula='actual_last_spawn.center_x + projected_half_extent_x + 0.30',
                    expected_box_count=2, not_spawned='CHECKPOINT_NOT_OBSERVABLE')
    if name == 'H1-v2':
        box = c['dynamic_obstacle']
    elif name == 'LC':
        box = next(b for b in c['obstacles'] if b['id'] == 'AfterCorner')
    else:
        box = max(c['obstacles'], key=lambda b: b['center_xy_m'][axis] + half_extent(b, axis))
    threshold = float(box['center_xy_m'][axis] + half_extent(box, axis) + .30)
    if name in ('SLW', 'LC', 'CL'):
        assert abs(threshold - c['checkpoint']['threshold_m']) < 1e-12
    return dict(axis=axis, direction=1, box_id=box['id'], dynamic=False,
                threshold_m=threshold, formula='box center along axis + projected half extent + 0.30')

def runtime_config(method, index, timeout=90, level='SLW'):
    assert method == METHOD and timeout == 90
    c, manifest = scene_config(level)
    c = phase18.runtime_config(c, phase18.PROPOSED, index, manifest, timeout)
    c.update(j_common=True, j_method=method, j_scene=level, phase15b_method=method,
             nomad_goal_stop=False, oracle_publication=False, goal_tolerance_m=.3,
             checkpoint=checkpoint_spec(level))
    from .depth import registration
    c['sdf_registration'] = registration(c)
    return c
