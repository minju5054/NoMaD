"""Sensor-only persistent surface occupancy. No oracle boxes or wall constraints.

query/error_bound match GraphV4's field API. The interpolation bound is NOT a
bound on unseen geometry, noisy depth, or occupancy quantization. In particular
this deliberately does not infer solid interiors behind observed surfaces.
"""
import time
import numpy as np
from scipy.ndimage import distance_transform_edt


def intrinsics(camera, width=320, height=240):
    f = camera['focal_length_mm']
    return np.array([width*f/camera['horizontal_aperture_mm'],
                     height*f/camera['vertical_aperture_mm'], width/2, height/2])


def camera_to_world(pose, height=.5):
    """Column-vector USD camera basis: right, up, backward; optical axis -Z."""
    x, y, yaw = pose; c, s = np.cos(yaw), np.sin(yaw)
    return np.array([[s, 0, -c, x], [-c, 0, -s, y], [0, 1, 0, height], [0, 0, 0, 1.]])


def backproject(depth, k, transform, noise=False, rng=None):
    d = np.asarray(depth, dtype=float).copy()
    valid = np.isfinite(d) & (d > 0)
    if noise:
        if rng is None: raise ValueError('Noise requires explicit deterministic RNG')
        d[valid] += rng.normal(0., .01*d[valid]**2)
        valid &= d > 0
    vv, uu = np.nonzero(valid); z = d[vv, uu]
    p = np.column_stack([(uu+.5-k[2])*z/k[0], -(vv+.5-k[3])*z/k[1], -z])
    world = p@transform[:3,:3].T+transform[:3,3]
    return world, np.linalg.norm(p, axis=1), d


class DepthSDF:
    def __init__(self, bounds, resolution=.01, radius=.09):
        self.h = float(resolution); self.radius = float(radius)
        self.origin = np.asarray(bounds[:2], dtype=float)
        upper = np.asarray(bounds[2:], dtype=float)
        nx, ny = np.ceil((upper-self.origin)/self.h).astype(int)+1
        self.occupied = np.zeros((ny,nx), dtype=bool)
        self.observed = self.occupied.copy()
        self.height_rejected = self.occupied.copy(); self.range_rejected = self.occupied.copy()
        self.error_bound = self.h/np.sqrt(2)
        self.empty_distance = float(np.linalg.norm(upper-self.origin)-radius)
        self.values = np.full((ny,nx), self.empty_distance)
        self.build_wall_s = 0.

    def cells(self, xy):
        cells = np.rint((np.asarray(xy)-self.origin)/self.h).astype(int)
        ok = np.all(cells >= 0, axis=1) & (cells[:,0]<self.values.shape[1]) & (cells[:,1]<self.values.shape[0])
        return cells, ok

    def mark(self, grid, xy):
        cells, ok = self.cells(xy); x,y = cells[ok].T
        grid[y,x] = True

    def _visibility(self, d, k, transform, max_range):
        # At camera height, grid center is observable iff before the first
        # axial return. Use the minimum of both center rows/neighbor columns.
        # This marks coverage only: it NEVER clears persistent occupied cells.
        origin = transform[:2,3]
        low = np.maximum(np.floor((origin-max_range-self.origin)/self.h).astype(int), 0)
        high = np.minimum(np.ceil((origin+max_range-self.origin)/self.h).astype(int)+1,
                          self.values.shape[::-1])
        xx, yy = np.meshgrid(np.arange(low[0],high[0]), np.arange(low[1],high[1]))
        dx = self.origin[0]+xx*self.h-origin[0]; dy = self.origin[1]+yy*self.h-origin[1]
        right = dx*transform[0,0]+dy*transform[1,0]
        axial = -(dx*transform[0,2]+dy*transform[1,2])
        u = right/np.maximum(axial,1e-12)*k[0]+k[2]-.5
        ok = (axial>.02) & (dx*dx+dy*dy<=max_range**2) & (u>=0) & (u<d.shape[1]-1)
        x, y = xx[ok], yy[ok]; cols = np.floor(u[ok]).astype(int)
        mid = int(k[3])
        depths = np.minimum.reduce([d[mid-1,cols],d[mid,cols],d[mid-1,cols+1],d[mid,cols+1]])
        seen = (depths>0) & ~np.isnan(depths) & (axial[ok]<=depths)
        self.observed[y[seen],x[seen]] = True

    def update(self, depth, k, transform, noise=False, rng=None, max_range=3.):
        t0 = time.perf_counter()
        points, ranges, measured = backproject(depth,k,transform,noise,rng)
        t1 = time.perf_counter()
        heights = (points[:,2]>.03) & (points[:,2]<=.6)
        near = ranges<=max_range
        self.mark(self.height_rejected,points[~heights & near,:2])
        self.mark(self.range_rejected,points[heights & ~near,:2])
        hits = points[heights & near,:2]
        self.mark(self.occupied,hits)
        self._visibility(measured,k,transform,max_range)
        self.observed |= self.occupied
        occupied_count=int(self.occupied.sum())
        unknown_fraction=float((~self.observed).mean())
        t2 = time.perf_counter()
        if occupied_count:
            self.values = distance_transform_edt(~self.occupied, sampling=self.h)-self.radius
        t3 = time.perf_counter(); self.build_wall_s = t3-t0
        return dict(points=len(points),obstacle_points=len(hits),occupied_cells=occupied_count,
                    unknown_fraction=unknown_fraction,
                    pointcloud_ms=(t1-t0)*1000,accumulate_ms=(t2-t1)*1000,sdf_ms=(t3-t2)*1000,
                    update_ms=(t3-t0)*1000)

    def query(self, points):
        # Exact same bilinear convention as GraphV4.SignedDistanceField.
        t = (np.asarray(points)-self.origin)/self.h
        cell = np.floor(t.real).astype(int)
        if np.any(cell<0) or np.any(cell[:,0]>=self.values.shape[1]-1) or np.any(cell[:,1]>=self.values.shape[0]-1):
            raise ValueError('SDF query outside registered field')
        x,y = cell.T; a,b = (t-cell).T
        f00,f10 = self.values[y,x],self.values[y,x+1]
        f01,f11 = self.values[y+1,x],self.values[y+1,x+1]
        value = (1-a)*(1-b)*f00+a*(1-b)*f10+(1-a)*b*f01+a*b*f11
        grad = np.column_stack([((1-b)*(f10-f00)+b*(f11-f01))/self.h,
                                ((1-a)*(f01-f00)+a*(f11-f10))/self.h])
        return value,grad

    def unknown_fraction(self, points):
        cells, ok = self.cells(points); unknown = np.ones(len(cells),dtype=bool)
        x,y = cells[ok].T; unknown[ok] = ~self.observed[y,x]
        return float(unknown.mean())


def bounds_from_config(config, padding=2.):
    # Allocation metadata only. No obstacle or corridor value enters query.
    c = config['corridor']
    return [c['xmin']-padding,-c['half_width']-padding,c['xmax']+padding,c['half_width']+padding]
