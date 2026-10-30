import unittest
import numpy as np
from nomad_phase15b.depth import Snapshot
from .shadow import ShadowSDF,strict_snapshot
from .detour_known import KnownDetourGraph,radial_reference


class Tests(unittest.TestCase):
    def test_shadow_negative_reset_positive_preserved(self):
        f=ShadowSDF([-1,-1,3,1]);sites=np.array([[1.1,0],[1.2,0],[1.6,0]])
        cells,_=f.cells(sites)
        for (x,y),value in zip(cells,[-80,170,-80]):f.log_odds_hundredths[y,x]=value;f.observed[y,x]=True
        r=f.accumulate(np.array([[1.,0.,.2],[1.,0.,.2]]),np.array([1.,1.]),[0,0,.5])
        self.assertEqual(f.log_odds_hundredths[cells[0,1],cells[0,0]],0);self.assertFalse(f.observed[cells[0,1],cells[0,0]])
        self.assertEqual(f.log_odds_hundredths[cells[1,1],cells[1,0]],170);self.assertTrue(f.occupied[cells[1,1],cells[1,0]])
        self.assertEqual(f.log_odds_hundredths[cells[2,1],cells[2,0]],-80);self.assertEqual(r['shadow_rays'],1)

    def test_no_shadow_from_floor_or_rejected_points(self):
        f=ShadowSDF([-1,-1,3,1]);x,y=f.cells([[1.1,0]])[0][0];f.log_odds_hundredths[y,x]=-80;f.observed[y,x]=True
        f.accumulate(np.array([[1.,0.,0.],[1.,0.,.7],[1.,0.,.2]]),np.array([1.,1.,3.1]),[0,0,.5])
        self.assertEqual(f.log_odds_hundredths[y,x],-80);self.assertTrue(f.observed[y,x])

    def test_r3_unknown_only_far_and_certificate(self):
        f=ShadowSDF([-1,-1,3,1]);f.values[:]=1.;f.observed[:]=False
        b=Snapshot(f,{});s=strict_snapshot(b)
        g=KnownDetourGraph([0,0,0],[1,0],b,s,0);p=g.initial_path;g.field.configure(p)
        value,_=g.field.query(g.M@p)
        self.assertTrue(np.all(value[g.field.near]==1.));self.assertTrue(np.all(value[~g.field.near]<0))
        self.assertFalse(g.certificate(p)['certificate_pass'])
        self.assertEqual(g.cB,1.-b.error_bound)
        self.assertEqual(b.exact_clearance(p),1.)

    def test_reference_uses_start_only(self):
        p=np.zeros((100,3));p[0,2]=np.pi/2;p[30,:2]=[.4,0];p[60,:2]=[2.,.1]
        u,s=radial_reference(p,30,np.full((8,8,2),-999.));np.testing.assert_allclose(u,[0,1],atol=1e-12)
        self.assertEqual(s['source'],'START_HEADING')
        a,_=radial_reference(p,60,np.zeros((8,8,2)));b,_=radial_reference(p,60,np.ones((8,8,2))*99)
        np.testing.assert_array_equal(a,b);np.testing.assert_allclose(a,np.array([2,.1])/np.linalg.norm([2,.1]))

    def test_piecewise_field_jacobian(self):
        class Affine:
            error_bound=.01/np.sqrt(2)
            def __init__(self,offset,gradient):self.offset=offset;self.gradient=np.array(gradient)
            def query(self,p):return self.offset+p@self.gradient,np.tile(self.gradient,(len(p),1))
        b=Affine(1.,[.1,.2]);s=Affine(.1,[.02,.03])
        g=KnownDetourGraph([0,0,.1],[1,0],b,s,30);x=g.initial*.98;x[3]+=.001
        for func in (g.residual_jacobian,g.constraints):
            _,j=func(x);h=1e-7;fd=np.column_stack([(func(x+e*h)[0]-func(x-e*h)[0])/(2*h) for e in np.eye(20)])
            np.testing.assert_allclose(j,fd,rtol=0,atol=1e-5)


if __name__=='__main__':unittest.main()
