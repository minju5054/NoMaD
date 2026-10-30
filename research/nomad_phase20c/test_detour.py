import unittest
import numpy as np
from scipy.ndimage import distance_transform_edt
from nomad_phase15.depth_sdf import DepthSDF
from nomad_phase15b.depth import Snapshot
from .detour import DetourGraph,ANGLES,solve_initialization,select_detour
from .trigger import NoProgress,reference_direction

def field(blocked=False):
    f=DepthSDF([-2.,-2.,3.,2.]);f.observed[:]=True
    if blocked:
        iy,ix=np.indices(f.occupied.shape);x=f.origin[0]+ix*f.h;y=f.origin[1]+iy*f.h
        f.occupied[:]=(x>=.6)&(x<=.9)&(y>=-.5)&(y<=.15)
        f.values=distance_transform_edt(~f.occupied,sampling=f.h)-f.radius
    else:f.values[:]=1.
    return Snapshot(f,dict(synthetic=True))

class Affine:
    error_bound=.01/np.sqrt(2)
    def query(self,p):return .12+.04*p[:,0]-.05*p[:,1],np.tile([.04,-.05],(len(p),1))

class Tests(unittest.TestCase):
    def test_progress_clearance_and_constraint_jacobians(self):
        g=DetourGraph([.01,.02,.17],[1.,0.],Affine(),30)
        p=g.initial_path.copy();p[1:]=np.array([.01,.02])+np.c_[np.linspace(.105,1.05,10),.006*np.sin(np.arange(1,11))]
        x=p[1:].ravel();h=1e-7
        for f in (g.residual_jacobian,g.constraints):
            _,j=f(x);fd=np.column_stack([(f(x+e*h)[0]-f(x-e*h)[0])/(2*h) for e in np.eye(20)])
            np.testing.assert_allclose(j,fd,atol=1e-5,rtol=0)

    def test_free_space_straight(self):
        result=solve_initialization([0,0,0],[1,0],field(),0)
        self.assertTrue(result['accepted'],result)
        self.assertLess(np.max(np.abs(np.array(result['path'])[:,1])),.001)
        self.assertGreaterEqual(result['progress_m'],.5)

    def test_blocked_scene_finds_gap(self):
        f=field(True);results=[solve_initialization([0,0,0],[1,0],f,a) for a in ANGLES]
        chosen=select_detour(results);self.assertIsNotNone(chosen,[r['disposition'] for r in results])
        r=results[chosen];self.assertGreaterEqual(r['depth_clearance_m'],.025)
        self.assertGreater(max(p[1] for p in r['path']),.25)
        self.assertLessEqual(r['constraint_violation'],1e-7)

    def test_no_progress_and_end_cooldown(self):
        p=np.zeros((20*72+1,3));p[:5*72+1,0]=np.linspace(0,1,5*72+1);p[5*72:,0]=1
        samples=np.repeat(np.c_[np.linspace(1,1.5,8),np.zeros(8)][None],8,axis=0)
        u,detail=reference_direction(p,8*72,samples);np.testing.assert_array_equal(u,[1,0]);self.assertEqual(detail['source'],'HISTORY_8_TO_3')
        d=NoProgress();self.assertTrue(d.check(p,8*72,u)[0]);self.assertFalse(d.check(p,8*72,u,blocked=True)[0])
        d.started();self.assertFalse(d.check(p,9*72,u)[0]);d.ended(10.)
        self.assertFalse(d.check(p,12*72,u)[0]);self.assertTrue(d.check(p,13*72,u)[0])
        u,detail=reference_direction(p,18*72,samples);self.assertTrue(detail['source'].startswith('MEAN_ENDPOINT'));np.testing.assert_array_equal(u,[1,0])

if __name__=='__main__':unittest.main()
