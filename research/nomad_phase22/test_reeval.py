import unittest
from unittest.mock import patch
import numpy as np
from .reeval import simulate,stop_reason,plan_oracle
from .rollout import simulate as original

class Tests(unittest.TestCase):
    def test_endpoint_cuts_identical_controller_prefix(self):
        p=np.c_[np.linspace(0,1.217,11),np.zeros(11)];old=original([0,0,0],p,.3);new=simulate([0,0,0],p,.3)
        self.assertTrue(new['completed']);self.assertEqual(new['termination'],'ENDPOINT_0P10');self.assertLessEqual(new['endpoint_distance_m'],.10)
        np.testing.assert_array_equal(new['poses'],old['poses'][:len(new['poses'])]);self.assertLess(new['duration_s'],old['duration_s'])
    def test_projection_can_complete_outside_endpoint_radius(self):
        p=[[0,0],[1,0]];r=simulate([1.2,.2,0],p,0.)
        self.assertEqual(r['termination'],'PROJECTED_END');self.assertTrue(r['completed']);self.assertGreater(r['endpoint_distance_m'],.1);self.assertEqual(r['duration_s'],0)
    def test_timeout_is_complete_and_excludes_alignment_time(self):
        class Stopped:
            def replace_path(self,*a):self.mode='ROTATE';self.trigger_S=True;self.calls=0
            def control(self,*a):
                self.mode='ROTATE' if self.calls<9 else 'GO';self.calls+=1
                return (0.,0.),dict(completed=False,mode=self.mode)
        with patch('nomad_phase22.reeval.SPAlignment',Stopped):r=simulate([0,0,0],[[0,0],[1,0]],0.)
        self.assertTrue(r['completed']);self.assertTrue(r['TIMEOUT']);self.assertEqual(r['alignment_time_s'],1.);self.assertAlmostEqual(r['duration_s'],21+1/72)
        self.assertIsNone(stop_reason([0,0,0],np.array([1,0]),0,1,21,1))
    def test_plan_segments_distinguish_safe_vertices(self):
        c=dict(agent_radius_m=.09,obstacles=[dict(id='Box',center_xy_m=[.5,0],size_xyz_m=[.2,.2,.8])],corridor=dict(xmin=-1,xmax=2,half_width=1.5),start_pose=[0,0,0],goal_pose=[1,0,0])
        r=plan_oracle(np.array([[0.,0.],[1.,0.]]),c)
        self.assertFalse(r['plan_oracle_point_collision']);self.assertTrue(r['plan_oracle_segment_collision']);self.assertAlmostEqual(r['plan_oracle_segment_clearance_m'],-.09)
if __name__=='__main__':unittest.main()
