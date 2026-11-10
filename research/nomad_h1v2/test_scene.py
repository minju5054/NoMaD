"""Static geometry/predicate tests only; no renderer, physics or navigation."""
import copy,json,unittest
from unittest.mock import patch
import numpy as np
from nomad_phase26.config import runtime_config
from nomad_phase26 import scenes as frozen
from nomad_phase38.scenes import gap_check
from . import scene

class Tests(unittest.TestCase):
    def setUp(self):self.base=runtime_config('C0',201,90,'H1');self.p=scene.load_spec()
    def test_requested_center_and_size(self):
        q,s=scene.target(self.p['topomap_nodes_xy_m']);np.testing.assert_allclose(q,[2.8764528309775836,1.10],atol=1e-12,rtol=0)
        np.testing.assert_array_equal(q,self.p['box']['center_xy_m']);self.assertFalse(self.p['position_adjusted_for_overlap'])
        after=next(o for o in self.base['obstacles'] if o['id']=='AfterCorner');self.assertEqual(list(scene.SIZE),after['size_xyz_m'])
    def test_phase38_gap_and_no_overlap(self):
        p=self.p;self.assertEqual(scene.overlap_reasons(self.base,p['box']['center_xy_m']),[])
        result=gap_check(self.base,p['box'],1);self.assertTrue(result['passed']);self.assertEqual(result['required_gap_m'],.28)
        np.testing.assert_allclose(result['gaps_m'],[.22645283097758373,1.0735471690224165],atol=1e-12,rtol=0)
    def test_front_and_one_meter_arc_trigger_once(self):
        c=scene.configure(self.base);p=c['h1v2'];front_s,front=scene.box_front(p['topomap_nodes_xy_m'],p['box']['center_xy_m'])
        self.assertAlmostEqual(front[1],.9);self.assertAlmostEqual(front_s-p['spawn']['arc_m'],1.)
        for delta,expected in [(-1e-5,False),(1e-5,True),(.02,True)]:
            xy,_=scene.at(p['topomap_nodes_xy_m'],p['spawn']['arc_m']+delta)
            self.assertEqual(scene.triggered(c,[*xy,0.],0),expected);self.assertFalse(scene.triggered(c,[*xy,0.],1))
    def test_return_corridor_widths_and_exact_corner_witness(self):
        r=scene.return_gap_check(self.base,self.p['box']);self.assertTrue(r['passed']);self.assertAlmostEqual(r['top_to_aftercorner_m'],.4)
        self.assertAlmostEqual(r['diagonal_minimum_m'],.4582284766117627)
        self.assertAlmostEqual(r['horizontal_separation_m'],.22354716902241645)
        distance=np.linalg.norm(np.array(r['closest_box_point_xy_m'])-r['closest_aftercorner_point_xy_m'])
        self.assertAlmostEqual(distance,r['diagonal_minimum_m']);self.assertEqual(r['required_gap_m'],.28)
    def test_previous_position_return_check_failure_does_not_mutate_box(self):
        box=copy.deepcopy(self.p['previous_h1v2_preview']['box']);before=copy.deepcopy(box)
        r=scene.return_gap_check(self.base,box);self.assertFalse(r['passed']);self.assertEqual(box,before)
        self.assertAlmostEqual(r['top_to_aftercorner_m'],0.);self.assertAlmostEqual(r['diagonal_minimum_m'],.2159191472102826)
        self.assertEqual(r['checks'],dict(top_to_aftercorner=False,diagonal_minimum=False))
    def test_config_is_opt_in_and_preserves_frozen_inputs(self):
        before=copy.deepcopy(self.base);c=scene.configure(self.base);self.assertEqual(self.base,before)
        for k,v in before.items():
            if k!='dynamic_obstacle':self.assertEqual(c[k],v,k)
        for k,v in before['dynamic_obstacle'].items():
            if k not in ('size_xyz_m','center_xy_m','placement'):self.assertEqual(c['dynamic_obstacle'][k],v)
        self.assertEqual(c['phase16_scene'],'H1');self.assertEqual(c['scene_variant'],'H1-v2')
        with self.assertRaises(AssertionError):scene.configure(dict(self.base,phase16_scene='LC'))
    def test_fixed_placement_independent_of_actual_pose_and_seed_jitter(self):
        c=scene.configure(self.base);spawn=np.array(self.p['spawn']['position_xy_m']);center=self.p['box']['center_xy_m']
        for offset in (0.,.05):
            q=[spawn[0]+offset,spawn[1],0.];c['phase38_jitter']=[dict(offset_m=.2)]
            r=scene.place(c,q,0);self.assertEqual(r['status'],'PLACED');self.assertEqual(r['obstacle']['center_xy_m'],center);json.dumps(r,allow_nan=False)
    def test_closest_valid_polyline_point_only_if_overlap(self):
        c=dict(corridor=dict(xmin=-4.,xmax=4.,half_width=2.),agent_radius_m=.09,
            obstacles=[dict(id='Box',center_xy_m=[0.,0.],size_xyz_m=[.5,.5,.8])])
        path=[[-3.,0.],[3.,0.]];q,s,changed=scene.nearest_nonoverlap(c,path,np.array([0.,0.]),3.)
        self.assertTrue(changed);np.testing.assert_allclose(q,[-.5,0.],atol=1e-12,rtol=0);self.assertAlmostEqual(s,2.5)
        self.assertEqual(scene.overlap_reasons(c,q),[])
    def test_gap_failure_does_not_move_nonoverlapping_center(self):
        c=dict(corridor=dict(xmin=-.35,xmax=.35,half_width=2.),agent_radius_m=.09,obstacles=[])
        path=[[0.,-1.],[0.,1.]];q,s,changed=scene.nearest_nonoverlap(c,path,np.array([0.,0.]),1.)
        self.assertFalse(changed);np.testing.assert_array_equal(q,[0.,0.])
        r=gap_check(c,dict(center_xy_m=q.tolist(),size_xyz_m=list(scene.SIZE)),1);self.assertFalse(r['passed'])
    def test_frozen_monitor_only_binds_spawn_predicate_and_placement(self):
        self.assertIs(scene.Monitor.observe_tick.__code__,frozen.MultiSuddenMonitor.observe_tick.__code__)
        self.assertIs(scene.Monitor.observe_tick.__globals__['triggered'],scene.triggered)
        self.assertIs(scene.Monitor.observe_tick.__globals__['place'],scene.place)
        self.assertEqual(scene.place(self.base,[3.3,1.2,np.pi/2],0),frozen.place(self.base,[3.3,1.2,np.pi/2],0))
        import nomad_isaac.sudden_obstacle as sudden
        old=lambda c,out:('ORIGINAL',c,out)
        with patch.object(sudden,'SuddenObstacleMonitor',old),patch.object(scene,'Monitor',lambda c,out:('H1V2',c,out)):
            scene.install_environment(self.base);self.assertIs(sudden.SuddenObstacleMonitor,old)
            new=scene.configure(self.base);scene.install_environment(new)
            self.assertEqual(sudden.SuddenObstacleMonitor(self.base,None)[0],'ORIGINAL')
            self.assertEqual(sudden.SuddenObstacleMonitor(new,None)[0],'H1V2')
if __name__=='__main__':unittest.main()
