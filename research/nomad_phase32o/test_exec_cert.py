import json,unittest
from types import SimpleNamespace
import numpy as np
from scipy.ndimage import distance_transform_edt
from nomad_phase15b.depth import Snapshot
from nomad_phase28.alignment import NoAlignment
from nomad_isaac.common import integrate_se2
from .exec_cert import rollout,certify,swept_clearance,HZ

def field(site=None):
 f=object.__new__(Snapshot);f.h=.01;f.origin=np.array([-1.,-1.]);f.radius=.09;f.error_bound=.01/np.sqrt(2);f.occupied=np.zeros((301,401),bool)
 if site is not None:
  p=np.rint((np.array(site)-f.origin)/f.h).astype(int);f.occupied[p[1],p[0]]=True
 f.values=distance_transform_edt(~f.occupied,sampling=f.h)-f.radius if f.occupied.any() else np.full(f.occupied.shape,3.)
 return f

class CertificateTests(unittest.TestCase):
 def test_straight_frozen_control_and_limits(self):
  path=[[0,0],[1,0]];r=rollout([0,0,0],[.1,.2],path);c=NoAlignment();c.replace_path(path,[0,0,0],.1);q=np.zeros(3);v=.1
  for i in range(144):
   if i%8==0:(v,w),_=c.control(q,v)
   q=integrate_se2(q,v,w,1/72);np.testing.assert_allclose(q,r['poses'][i+1],atol=1e-12)
  cmd=r['commands'];self.assertLessEqual(abs(cmd[:,1]).max(),.4);self.assertLessEqual(cmd[:,0].max(),.3);self.assertLessEqual(abs(np.diff(np.r_[.1,cmd[::8,0]])).max(),.5/9+1e-12)
 def test_ninety_degree_rule(self):
  self.assertFalse(rollout([0,0,0],[0,0],[[0,0],[0,1]])['alignment'])
  self.assertTrue(rollout([0,0,0],[0,0],[[0,0],[-.1,1]])['alignment'])
 def test_actual_heading_and_initial_velocity(self):
  r=rollout([0,0,np.pi/2],[.3,.4],[[0,0],[1,0]]);np.testing.assert_array_equal(r['poses'][0],[0,0,np.pi/2]);self.assertGreaterEqual(r['commands'][0,0],.3-.5/9-1e-12)
 def test_endpoint_and_cap(self):
  r=rollout([1,0,0],[.2,0],[[0,0],[1,0]]);self.assertTrue(r['endpoint_reached']);self.assertEqual(r['duration_s'],0)
  r=rollout([0,0,0],[0,0],[[0,0],[3,0]]);self.assertEqual(r['duration_s'],2.)
 def test_path_past_endpoint_is_not_artificially_completed(self):
  r=rollout([1.1,0,0],[.1,0],[[0,0],[1,0]]);self.assertEqual(r['duration_s'],2.)
 def test_swept_between_endpoints(self):
  f=field([.5,.1]);q=np.array([[0,0,0],[1,0,0]]);r=swept_clearance(f,q,np.array([[72.,0.]]));self.assertAlmostEqual(r['clearance_m'],.01,places=10);self.assertFalse(r['passed'])
 def test_curved_arc_interior(self):
  f=field([1.,-.5]);q=np.array([[0.,0.,0.],[2.,0.,np.pi]])
  # Full semicircle of radius1 about(1,0), start heading -pi/2.
  q=np.array([[0.,0.,-np.pi/2],[2.,0.,np.pi/2]])
  r=swept_clearance(f,q,np.array([[72*np.pi,72*np.pi]]));self.assertAlmostEqual(r['clearance_m'],.41,places=8)
 def test_arc_against_dense_reference(self):
  f=field([.2,.12]);q=np.array([.1,.02,.7]);v,w=.3,.4;end=integrate_se2(q,v,w,1/72)
  r=swept_clearance(f,np.array([q,end]),np.array([[v,w]]));dense=np.array([integrate_se2(q,v,w,t) for t in np.linspace(0,1/72,10001)]);ref=np.linalg.norm(dense[:,:2]-[.2,.12],axis=1).min()-.09
  self.assertAlmostEqual(r['clearance_m'],ref,places=8)
 def test_rotation_footprint(self):
  f=field([.12,0]);r=certify([0,0,0],[0,0],[[0,0],[-1,0]],f);self.assertTrue(r['passed']);self.assertAlmostEqual(r['clearance_m'],.03,places=8)
 def test_json_and_input_immutable(self):
  f=field([.3,.03]);before=f.values.copy();r=certify([0,0,0],[.2,0],[[0,0],[1,0]],f);self.assertFalse(r['passed']);json.dumps(r,allow_nan=False);np.testing.assert_array_equal(f.values,before)
 def test_timed_stationary_path_is_explicitly_rejected(self):
  r=certify([0,0,0],[0,0],[[0,0]]*11,field());self.assertFalse(r['passed']);self.assertEqual(r['reason'],'INVALID_INPUT');json.dumps(r,allow_nan=False)
 def test_slowdown_acceleration(self):
  r=rollout([0,0,0],[.3,0],[[0,0],[1,0]],.1);v=r['commands'][::8,0];self.assertGreater(v[0],.1);self.assertLessEqual(np.max(abs(np.diff(np.r_[.3,v]))),.5/9+1e-12);self.assertAlmostEqual(v[-1],.1)


class GateTests(unittest.TestCase):
 def test_gate_boundaries(self):
  from .report import gate
  self.assertEqual(gate(12,.10,.03,.02)[0],'OFFLINE_PASS')
  for values in [(11,.10,.03,.02),(12,.10001,.03,.02),(12,.10,.03001,.02),(12,.10,.03,.02001)]:self.assertEqual(gate(*values)[0],'OFFLINE_FAIL')

if __name__=='__main__':unittest.main()
