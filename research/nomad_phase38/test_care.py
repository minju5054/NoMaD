import json,unittest
from types import SimpleNamespace
import numpy as np
from .care import correct,obstacles,ROTATION_CLIP

class CareTests(unittest.TestCase):
    def test_empty_unchanged(self):
        p=np.array([[.3,0],[.6,0],[1.,0]])
        q,d=correct(p,[0,0,0],[]);np.testing.assert_array_equal(q,p);self.assertFalse(d['safe_fov'])
    def test_inverse_square_max_waypoint_and_rotation_clip(self):
        p=np.array([[0,0],[1,0]])
        q,d=correct(p,[0,0,0],[[0,1]])
        np.testing.assert_allclose(d['forces'],[[0,-1],[1/(2*np.sqrt(2)),-1/(2*np.sqrt(2))]])
        self.assertEqual(d['selected_waypoint'],0);self.assertAlmostEqual(d['rotation_rad'],-ROTATION_CLIP)
        np.testing.assert_allclose(np.linalg.norm(q,axis=1),np.linalg.norm(p,axis=1));json.dumps(d,allow_nan=False)
    def test_obstacles_are_observed_occupied_within_one_metre(self):
        f=SimpleNamespace(occupied=np.array([[1,1,1,1]],bool),observed=np.array([[1,0,1,1]],bool),origin=np.array([0.,0.]),h=.5)
        np.testing.assert_array_equal(obstacles(f,[0,0,0]),[[0,0],[1,0]])
    def test_rigid_transform_and_coincidence_are_finite(self):
        p=np.array([[.3,0],[.65,.1]]);obs=np.array([[.4,.2]])
        a,d=correct(p,[0,0,0],obs);rot=np.array([[0,-1],[1,0]])
        b,e=correct(p@rot.T+[2,3],[2,3,np.pi/2],obs@rot.T+[2,3]);np.testing.assert_allclose(b,a@rot.T+[2,3])
        _,d=correct(p,[0,0,0],[p[0]]);json.dumps(d,allow_nan=False);self.assertEqual(d['coincident_pairs'],1)

if __name__=='__main__':unittest.main()
