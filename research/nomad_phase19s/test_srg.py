import unittest
import numpy as np
from nomad_phase17.config import scene
from nomad_phase18d.rollout import rollout as original_rollout
from .srg import simulate, evaluate, pivots, stop_profile


class Tests(unittest.TestCase):
    def test_rotation_footprint_invariant(self):
        xy=[[0,0],[0,.15],[0,.3]]
        r=evaluate(simulate([0,0,0],xy,0.,'SRG'),scene('CL'))
        rotating=np.flatnonzero(np.array(r['phases'])=='ROTATE')
        self.assertGreater(len(rotating),0)
        np.testing.assert_array_equal(r['poses'][rotating,:2],np.zeros((len(rotating),2)))
        from nomad_phase18d.rollout import Evaluator
        ev=Evaluator(scene('CL'))
        distances=[ev.interval(p,0,0,0)[0] for p in r['poses'][rotating]]
        np.testing.assert_array_equal(distances,np.repeat(distances[0],len(distances)))
        self.assertEqual(r['trigger_S'],1)
        self.assertAlmostEqual(r['poses'][rotating[-1]+1,2],np.pi/2,places=12)

    def test_straight_srg_equals_sp_and_protected_prefix(self):
        xy=np.c_[np.linspace(.02,.7,8),np.zeros(8)]
        a=simulate([0,0,0],xy,.1,'SP',ticks=108)
        b=simulate([0,0,0],xy,.1,'SRG',ticks=108)
        c=original_rollout([0,0,0],xy,.1,'SP',scene('CL'))
        np.testing.assert_array_equal(a['poses'],b['poses'])
        np.testing.assert_array_equal(a['poses'],c['poses'])
        self.assertFalse(b['trigger_any'])

    def test_ninety_degree_pivot_stop_and_rotate(self):
        xy=[[0,0],[.15,0],[.15,.2]]
        r=simulate([0,0,0],xy,0.,'SRG')
        self.assertEqual(r['trigger_P'],1)
        self.assertEqual(r['rotations'],1)
        a=next(e for e in r['events'] if e['event']=='TRIGGER_P')
        self.assertLessEqual(a['endpoint_distance_m'],.01)
        rot=[c for c in r['commands'] if c['mode']=='ROTATE']
        self.assertTrue(all(c['v']==0. for c in rot))
        self.assertTrue(r['completed'])
        v=np.r_[0.,[c['v'] for c in r['commands']]]
        self.assertLessEqual(np.max(np.abs(np.diff(v))),.5/9+1e-12)
        self.assertTrue(all(abs(c['w'])<=.4 for c in r['commands']))
        self.assertEqual(stop_profile(xy[:2])['v_m_s'][-1],0.)

    def test_short_chord_detection_and_behind_boundary(self):
        xy=[[0,0],[.15,0],[.15,.005],[.15,.2]]
        p=pivots(xy,[0,0,0]);self.assertEqual(len(p),1)
        self.assertEqual(p[0]['index'],1)
        self.assertFalse(pivots(xy,[.15,.1,np.pi/2]))

    def test_oracle_does_not_change_execution(self):
        xy=[[0,0],[.1,0],[.3,0]]
        r=simulate([0,0,0],xy,0.,'SP')
        c=scene('CL');c['obstacles'][0]['center_xy_m']=[.2,0]
        assessed=evaluate(r,c)
        self.assertTrue(assessed['overlap'])
        self.assertTrue(assessed['completed'])
        np.testing.assert_array_equal(r['poses'],assessed['poses'])


if __name__=='__main__':unittest.main()
