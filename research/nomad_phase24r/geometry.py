"""Scene-coordinate wall repair and pre-navigation USD geometry refusal gate."""
import numpy as np

def expected(c):
    co=c['corridor'];return dict(LeftWall=co.get('ymax',co['half_width']),RightWall=co.get('ymin',-co['half_width']),EndWall=co['xmax'],StartWall=co['xmin'])

def verify_bounds(c,bounds):
    values=dict(LeftWall=bounds['LeftWall'][0][1],RightWall=bounds['RightWall'][1][1],EndWall=bounds['EndWall'][0][0],StartWall=bounds['StartWall'][1][0])
    errors={k:abs(float(values[k])-float(v)) for k,v in expected(c).items()}
    if not all(np.isfinite(list(errors.values()))) or max(errors.values())>1e-6:raise ValueError('USD_WALL_BOUNDARY_MISMATCH: '+str(errors))
    return dict(status='PASS',expected_inner_faces=expected(c),actual_inner_faces={k:float(v) for k,v in values.items()},max_error_m=max(errors.values()),bounds=bounds)

def repair_and_check(stage,c,base):
    from pxr import Usd,UsdGeom
    e=expected(c);xmin,xmax,ymin,ymax=e['StartWall'],e['EndWall'],e['RightWall'],e['LeftWall'];cx=(xmin+xmax)/2;cy=(ymin+ymax)/2;length=xmax-xmin;width=ymax-ymin
    def box(name,position,size):
        prim=stage.GetPrimAtPath('/World/'+name)
        if not prim.IsValid():
            prim=base.UsdGeom.Cube.Define(stage,'/World/'+name).GetPrim();prim.GetAttribute('size').Set(1.)
            base.UsdGeom.Xformable(prim).AddTranslateOp();base.UsdGeom.Xformable(prim).AddScaleOp()
            base.UsdGeom.Gprim(prim).CreateDisplayColorAttr().Set([base.Gf.Vec3f(.76,.77,.79)])
        prim.GetAttribute('xformOp:translate').Set(base.Gf.Vec3d(*position));prim.GetAttribute('xformOp:scale').Set(base.Gf.Vec3f(*size))
    box('Floor',(cx,cy,-.05),(length,width,.1))
    box('LeftWall',(cx,ymax+.05,1.3),(length,.1,2.6));box('RightWall',(cx,ymin-.05,1.3),(length,.1,2.6))
    box('EndWall',(xmax+.05,cy,1.3),(.1,width+.2,2.6));box('StartWall',(xmin-.05,cy,1.3),(.1,width+.2,2.6))
    box('EndDoor',(xmax-.002,cy+.15,1.1),(.004,.9,2.2))
    for prim in stage.Traverse():
        if not prim.IsA(base.UsdGeom.Cube):continue
        name=prim.GetName()
        if name.startswith('FloorSeam'):
            x=float(prim.GetAttribute('xformOp:translate').Get()[0]);box(name,(x,cy,.001),(.012,width,.002))
            if not xmin<x<xmax:base.UsdGeom.Imageable(prim).MakeInvisible()
        if name.startswith('Panel'):
            x=float(prim.GetAttribute('xformOp:translate').Get()[0]);side=ymax-.002 if name.endswith('_L') else ymin+.002
            box(name,(x,side,1.15),(.65,.004,1.7))
            if not xmin+.325<x<xmax-.325:base.UsdGeom.Imageable(prim).MakeInvisible()
    cache=UsdGeom.BBoxCache(Usd.TimeCode(0),[UsdGeom.Tokens.default_]);bounds={}
    for name in e:
        aabb=cache.ComputeWorldBound(stage.GetPrimAtPath('/World/'+name)).ComputeAlignedRange();bounds[name]=[list(aabb.GetMin()),list(aabb.GetMax())]
    return verify_bounds(c,bounds)
