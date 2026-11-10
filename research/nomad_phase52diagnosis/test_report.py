import unittest
import numpy as np
from .report import actual_geometry,oracle_polyline,classify,nearest_event

class Tests(unittest.TestCase):
    def test_dynamic_activation_and_surface_not_robot_center(self):
        c=dict(agent_radius_m=.09,corridor=dict(xmin=-1.,xmax=5.,half_width=1.5))
        box=dict(id='Box',center_xy_m=[1,0],size_xyz_m=[.4,1,.8],active_s=1.)
        poses=np.array([[.69,0,0],[.69,0,0]]);g,ids,surface=actual_geometry(poses,np.array([.9,1.]),c,[box])
        self.assertGreater(g[0],.025);self.assertAlmostEqual(g[1],.02);self.assertEqual(ids[1],'Box')
        np.testing.assert_allclose(surface[1],[.8,0])
    def test_shifted_rectangle_wall_clearance(self):
        c=dict(agent_radius_m=.09,corridor=dict(xmin=-1.,xmax=4.2,half_width=2.6,ymin=-1.,ymax=4.2))
        g,ids,surface=actual_geometry(np.array([[3,4.1,0]]),np.array([0.]),c,[])
        self.assertAlmostEqual(g[0],.01);self.assertEqual(ids[0],'LeftWall');np.testing.assert_allclose(surface[0],[3,4.2])
    def test_polyline_is_continuous_not_nodes_only(self):
        c=dict(agent_radius_m=.09,corridor=dict(xmin=-1.,xmax=5.,half_width=1.5))
        box=dict(id='Box',center_xy_m=[1,0],size_xyz_m=[.4,1,.8],active_s=0.)
        self.assertLess(oracle_polyline([[0,0],[2,0]],0,c,[box]),0)
        self.assertGreater(oracle_polyline([[0,.8],[2,.8]],0,c,[box]),.025)
    def classify(self,**kw):
        args=dict(has_ec=True,app={'kind':'GRAPH_REC'},last_check={'passed':False},last_pass={'passed':True},endpoint_tail=True,
            pass_state=dict(map_available=True,surface_cell='OCCUPIED',patch_all_unknown=False),in_horizon=False,following=False,path_clearance=.046,depth_path_clearance=None,cross_track=.046)
        args.update(kw);return classify(**args)
    def test_endpoint_model_difference_not_misattributed_to_map_or_graph(self):
        self.assertEqual(self.classify()[0],'C_PREDICTION_EXECUTION')
        self.assertEqual(self.classify(has_ec=False)[1],'NO_EC_BY_DESIGN')
        self.assertEqual(self.classify(endpoint_tail=False)[0],'A_UNCHECKED_COMMAND')
    def test_unknown_and_missing_are_not_conflated(self):
        self.assertEqual(self.classify(endpoint_tail=False,pass_state=dict(map_available=True,patch_all_unknown=True))[0],'B_UNOBSERVED_MAP')
        self.assertEqual(self.classify(endpoint_tail=False,last_check={'passed':True},in_horizon=True,pass_state=dict(map_available=False))[0],'E_OTHER')
    def test_no_future_control_check_used(self):
        events=[dict(simulation_time_s=x,check_id=i) for i,x in enumerate([1.,1.5,2.])]
        self.assertEqual(nearest_event(events,1.99)['check_id'],1)
        self.assertIsNone(nearest_event(events,1.99,2.))

if __name__=='__main__':unittest.main()
