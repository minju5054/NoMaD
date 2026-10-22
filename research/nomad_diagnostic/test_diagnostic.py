"""Minimal mode/placement/measurement checks; no navigation or GPU."""
import copy
import json
import unittest
import numpy as np
from nomad_isaac.common import ROOT
from nomad_phase2.config import place,validate_options
from .config import MaskSchedule,ratio_band
from .data import lateral,scope
from .batch import preflight

class DiagnosticTests(unittest.TestCase):
    def test_modes(self):
        box={'center_xy_m':[3.,0.],'size_xyz_m':[.35,.35,.8]}
        s=MaskSchedule('C3');snap={'pose':[2.,0.,0.],'tick':100,'monotonic_ns':100}
        self.assertEqual(s.decide({'geometry_available':False},box,snap)['goal_mask'],0)
        self.assertEqual(s.decide({'geometry_available':True},box,snap)['goal_mask'],1)
        snap['pose'][0]=3.5
        self.assertEqual(s.decide({'geometry_available':True},box,snap)['goal_mask'],0)
        snap['pose'][0]=2.
        self.assertEqual(s.decide({'geometry_available':True},box,snap)['goal_mask'],0)
        self.assertEqual(MaskSchedule('C2').decide({'geometry_available':True},box,snap)['goal_mask'],0)
    def test_lateral_and_thresholds(self):
        box={'center_xy_m':[3.,0.],'size_xyz_m':[.35,.35,.8]}
        self.assertEqual(lateral(np.array([[1.,.5],[2.,.5]]),box)['lateral'],'NOT_REACHED')
        self.assertEqual(lateral(np.array([[2.,.5],[4.,.5]]),box)['lateral'],'LEFT')
        self.assertEqual(lateral(np.array([[2.,-.5],[4.,-.5]]),box)['lateral'],'RIGHT')
        self.assertEqual(lateral(np.array([[2.,0.],[4.,0.]]),box)['lateral'],'FRONT')
        self.assertEqual([ratio_band(v) for v in (.099,.1,.299,.3)],['RARE','INDETERMINATE','INDETERMINATE','SUFFICIENT'])
    def test_preflight_and_placement(self):
        p=preflight(ROOT.parent/'artifacts/isaac6/p2_diagnostic_01');self.assertEqual(len(p['jobs']),12)
        c=json.loads((ROOT/'research/nomad_phase2/scenario.json').read_text())
        c.update(phase2_distance_m=1.,diagnostic_y_offset_m=.2,dynamic_obstacle={'id':'DynamicObstacle','size_xyz_m':[.35,.35,.8]})
        r=place(c,[2.01,.8,.5]);self.assertEqual(r['status'],'PLACED')
        self.assertAlmostEqual(r['obstacle']['center_xy_m'][1],.925)
        self.assertAlmostEqual(r['y_clip_delta_m'],-.075)
        self.assertAlmostEqual(r['measured_world_forward_surface_d_m'],1.)
    def test_saved_scope(self):
        runs=list((ROOT.parent/'artifacts/isaac6/p2_01').glob('s2a_*_M0'));self.assertEqual(len(runs),16)
        for r in runs:
            inputs,captures,box,c=scope(r);self.assertTrue(inputs)
            self.assertTrue(all(n['oracle_information']['geometry_available'] for n in inputs))
            self.assertTrue(all(n['observation_id'] in {o['observation_id'] for o in captures} for n in inputs))

if __name__=='__main__':unittest.main()
