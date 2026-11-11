"""Scene registration only; V1 accumulation, EDT and strict query stay frozen."""
import math
from decimal import Decimal, ROUND_CEILING

RESOLUTION = .01
RADIUS = .09
WALL_THICKNESS = .10
PADDING = .50

def registration(config):
    from nomad_phase16.config import protocol
    old = protocol()['depth_bounds_m']
    co = config['corridor']
    # Frozen renderer: wall inner faces equal evaluation bounds, walls .10m
    # thick, end/start walls span the side walls' exterior corners.
    box = [float(co['xmin'])-WALL_THICKNESS,
           float(co.get('ymin', -co['half_width']))-WALL_THICKNESS,
           float(co['xmax'])+WALL_THICKNESS,
           float(co.get('ymax', co['half_width']))+WALL_THICKNESS]
    objects = list(config.get('obstacles', []))
    dynamic = config.get('dynamic_obstacle')
    if dynamic and 'center_xy_m' in dynamic:
        objects.append(dynamic)
    for obj in objects:
        yaw = float(obj.get('yaw_rad', math.radians(obj.get('yaw_deg', 0.))))
        x, y = [float(v)/2 for v in obj['size_xyz_m'][:2]]
        half = [abs(math.cos(yaw))*x+abs(math.sin(yaw))*y,
                abs(math.sin(yaw))*x+abs(math.cos(yaw))*y]
        for axis in (0, 1):
            box[axis] = min(box[axis], obj['center_xy_m'][axis]-half[axis])
            box[axis+2] = max(box[axis+2], obj['center_xy_m'][axis]+half[axis])
    padded = [box[0]-PADDING, box[1]-PADDING, box[2]+PADDING, box[3]+PADDING]
    assert all(padded[k] >= old[k] for k in (0, 1)), 'Scene would require changing the frozen grid origin'
    # Never crop the legacy rectangle. This preserves every legacy cell index
    # and the four unchanged scenes' full arrays, including the empty map.
    upper = []
    for axis in (0, 1):
        origin = Decimal(str(old[axis]));h = Decimal(str(RESOLUTION))
        target = Decimal(str(max(old[axis+2], padded[axis+2])))
        cells = ((target-origin)/h).to_integral_value(rounding=ROUND_CEILING)
        upper.append(float(origin+cells*h))
    return dict(legacy_bounds_m=list(old), scene_bbox_with_walls_m=box, padded_bbox_m=padded,
                registered_bounds_m=list(old[:2])+upper, origin_m=list(old[:2]), resolution_m=RESOLUTION,
                radius_m=RADIUS, padding_m=PADDING, wall_thickness_m=WALL_THICKNESS,
                allocation='union of legacy rectangle and geometry+0.5m; upper edge snapped outward on legacy grid',
                query='frozen strict ValueError outside registered field; no clipping or fallback',
                unknown='unchanged V1 unknown=free', empty_distance='legacy sentinel retained bit-for-bit')

def make_registered_field(spec):
    import numpy as np
    from nomad_phase15.occupancy import make_field
    field = make_field(spec['registered_bounds_m'], 'V1')
    assert field.h == spec['resolution_m'] == RESOLUTION and field.radius == spec['radius_m'] == RADIUS
    np.testing.assert_array_equal(field.origin, spec['origin_m'])
    # Allocation size alone must not change a completely unobserved map's
    # sentinel distance; the original update() continues to use this scalar.
    old = np.asarray(spec['legacy_bounds_m'], dtype=float)
    field.empty_distance = float(np.linalg.norm(old[2:]-old[:2])-field.radius)
    field.values.fill(field.empty_distance)
    return field

def thread_type(spec):
    from types import FunctionType
    from nomad_phase16.depth import DepthMapThread as Frozen
    init = Frozen.__init__
    namespace = dict(init.__globals__, protocol=lambda: {'depth_bounds_m': spec['registered_bounds_m']},
                     make_field=lambda bounds, variant: make_registered_field(spec))
    class RegisteredDepthMapThread(Frozen):
        """Only constructor allocation changes; frozen thread/update/publish."""
    RegisteredDepthMapThread.__init__ = FunctionType(init.__code__, namespace, init.__name__, init.__defaults__, init.__closure__)
    return RegisteredDepthMapThread
