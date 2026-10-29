import unittest
import numpy as np
from scipy.ndimage import distance_transform_edt
from nomad_phase15.depth_sdf import DepthSDF
from nomad_phase15b.depth import Snapshot
from .repair import RepairGraph,initialize,solve_sample

class Affine:
    error_bound=.01/np.sqrt(2)
    def query(self,p):return 1.+.3*p[:,0]+.7*p[:,1],np.tile([.3,.7],(len(p),1))
    def exact_clearance(self,p):return float(self.query(p)[0].min())

def synthetic(box=False):
    field=DepthSDF([-1.,-1.,2.,1.]);field.observed[:]=True
    if box:
        yy,xx=np.indices(field.occupied.shape);x=field.origin[0]+xx*field.h;y=field.origin[1]+yy*field.h
        field.occupied[:]=(x>=.55)&(x<=.75)&(y>=-.25)&(y<=-.03)
        field.values=distance_transform_edt(~field.occupied,sampling=field.h)-field.radius
    else:field.values[:]=1.
    return Snapshot(field,dict(synthetic=True))

class Tests(unittest.TestCase):
    def test_analytic_jacobians(self):
        B=[.003,.004,.17];native=np.c_[np.linspace(.003,.703,8),.004+.08*np.linspace(0,.7,8)**2]
        q,_=initialize(native,B);g=RepairGraph(q,B,Affine());x=g.initial.copy();x[3]+=.003
        h=1e-7;eye=np.eye(14)
        for func in (g.residual_jacobian,g.constraints):
            _,jac=func(x);fd=np.column_stack([(func(x+h*e)[0]-func(x-h*e)[0])/(2*h) for e in eye])
            np.testing.assert_allclose(jac,fd,rtol=0,atol=1e-5)

    def test_free_straight_path_preserved(self):
        xy=np.c_[np.linspace(0,.7,8),np.zeros(8)];r=solve_sample(xy,[0,0,0],synthetic())
        self.assertTrue(r['accepted'],r);self.assertLess(r['mean_edit_m'],.001)
        np.testing.assert_array_equal(r['path'][0],[0,0])

    def test_footprint_blocking_box_detour(self):
        xy=np.c_[np.linspace(0,1.4,8),np.zeros(8)];field=synthetic(True)
        self.assertLess(field.exact_clearance(xy),0)
        r=solve_sample(xy,[0,0,0],field)
        self.assertTrue(r['accepted'],r)
        self.assertLessEqual(r['constraint_violation'],1e-7);self.assertGreaterEqual(r['depth_clearance_m'],.025)
        self.assertGreater(max(p[1] for p in r['path']),.05)

    def test_short_suffix_excluded_before_connector(self):
        xy=np.c_[np.linspace(0,1.,8),np.zeros(8)]
        q,reason=initialize(xy,[.9,.7,0])
        self.assertIsNone(q);self.assertEqual(reason['disposition'],'SHORT_REMAINING')

    def test_selection_and_safety_priority(self):
        from .evaluate import select_repair,decision
        self.assertEqual(select_repair([dict(accepted=True,mean_edit_m=.1),dict(accepted=True,mean_edit_m=.1)]),0)
        e=dict(split='eval',repair_success=True,rollout_overlap=False,selected_mean_edit_m=.10,eight_sample_wall_s=.5,cause='TRUE_BLOCK',selected_oracle_clearance_m=.03,rollout_progress_m=.2)
        r=dict(split='eval',accepted=True,oracle_clearance_m=.03,solver_started=True,attempt_wall_s=.10)
        self.assertEqual(decision([e],[r])['label'],'REPAIR_VIABLE')
        self.assertEqual(decision([e],[r,{**r,'oracle_clearance_m':-.01}])['label'],'REPAIR_UNSAFE')
        self.assertEqual(decision([e],[{**r,'attempt_wall_s':.21}])['label'],'REPAIR_SLOW')
        self.assertEqual(decision([{**e,'repair_success':False}],[{**r,'accepted':False}])['label'],'REPAIR_RARE')

if __name__=='__main__':unittest.main()
