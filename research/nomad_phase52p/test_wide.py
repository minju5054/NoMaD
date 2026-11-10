import json,unittest
import numpy as np
from .wide import sample_metrics,crossing_points

class Tests(unittest.TestCase):
    def test_gap_complete_short_and_through_box(self):
        box=dict(center_xy_m=[1.,0.],size_xyz_m=[.4,1.,.8]);pose=np.array([0.,.8,0.])
        sample=np.c_[np.linspace(.1,1.6,8),np.zeros(8)]
        r=sample_metrics(sample,pose,box,0,[-1.5,1.5]);self.assertTrue(r['enters_front_gap']);self.assertTrue(r['clears_far_gap']);self.assertEqual(r['endpoint_side'],'LEFT')
        short=sample.copy();short[:,0]*=.4;r=sample_metrics(short,pose,box,0,[-1.5,1.5]);self.assertFalse(r['enters_front_gap']);self.assertFalse(r['clears_far_gap'])
        r=sample_metrics(sample,np.array([0.,0.,0.]),box,0,[-1.5,1.5]);self.assertFalse(r['enters_front_gap']);self.assertFalse(r['clears_far_gap']);self.assertLess(r['target_box_path_clearance_m'],0)
    def test_reverse_and_rotated_scene_coordinates(self):
        sample=np.c_[np.linspace(.1,1.6,8),np.zeros(8)]
        box=dict(center_xy_m=[0.,1.],size_xyz_m=[1.,.4,.8]);pose=np.array([-.8,0.,np.pi/2])
        r=sample_metrics(sample,pose,box,1,[-1.5,1.5]);self.assertTrue(r['clears_far_gap']);self.assertEqual(r['endpoint_side'],'LEFT')
        reverse=-sample;r=sample_metrics(reverse,pose,box,1,[-1.5,1.5]);self.assertTrue(r['backward_scene_direction']);json.dumps(r,allow_nan=False)
    def test_diagonal_corner_cut_is_not_gap(self):
        box=dict(center_xy_m=[1.,0.],size_xyz_m=[.4,1.,.8]);pose=np.array([0.,.8,0.])
        sample=np.c_[np.linspace(.1,1.6,8),np.linspace(0,-1.6,8)]
        r=sample_metrics(sample,pose,box,0,[-1.5,1.5]);self.assertFalse(r['clears_far_gap'])

if __name__=='__main__':unittest.main()
