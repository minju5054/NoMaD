import json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from nomad_phase20.execution import SPAlignment
from nomad_phase26.config import protocol as original
from .campaign import routed
from .config import protocol,verify,RUN_ROOT,check_run_root

class AlignmentTests(unittest.TestCase):
    def test_middle_targets_forward_suffix_not_passed_prefix(self):
        c=SPAlignment();p=[[0,0],[.2,0],[.4,0],[.6,0]]
        c.replace_path(p,[.35,0,0],.2)
        self.assertFalse(c.trigger_S);self.assertAlmostEqual(c.initial_heading_error_deg,0.)
        c.replace_path(p,[.35,0,math.pi],.2)
        self.assertTrue(c.trigger_S);self.assertAlmostEqual(c.target_yaw,0.)
    def test_short_suffix_disables_alignment(self):
        c=SPAlignment();c.replace_path([[0,0],[.5,0],[1,0]],[.97,0,math.pi],0.)
        self.assertFalse(c.trigger_S);self.assertIsNone(c.target_yaw);self.assertIsNone(c.initial_heading_error_deg)
    def test_past_endpoint_disables_alignment(self):
        c=SPAlignment();c.replace_path([[0,0],[.5,0],[1,0]],[1.2,.1,math.pi],.2)
        self.assertFalse(c.trigger_S);self.assertIsNone(c.initial_heading_error_deg)
    def test_curved_suffix_uses_arclength_not_radial_distance(self):
        p=[[0,0],[.06,0],[.06,.02],[.02,.02],[.02,.1]];B=[.05,0,math.pi/2]
        c=SPAlignment();c.replace_path(p,B,.2)
        self.assertTrue(c.trigger_S)
        self.assertAlmostEqual(c.target_yaw,math.atan2(.02,-.03))
        # The selected point is >=5cm along the suffix, but <5cm from B.
        self.assertLess(np.linalg.norm(np.array(p[3])-B[:2]),.05)
    def test_exact_five_cm_suffix_is_eligible(self):
        c=SPAlignment();c.replace_path([[0,0],[.05,0]],[0,0,math.pi/2],0.)
        self.assertTrue(c.trigger_S);self.assertAlmostEqual(c.target_yaw,0.)
    def test_thresholds_and_rotation_command_unchanged(self):
        p=[[0,0],[0,.1],[0,.2]];c=SPAlignment()
        c.replace_path(p,[0,0,math.radians(60)],0.);self.assertTrue(c.trigger_S);self.assertEqual(c.alignment_threshold_deg,20.)
        c.replace_path(p,[0,0,math.radians(60)],.2);self.assertFalse(c.trigger_S);self.assertEqual(c.alignment_threshold_deg,45.)
        c.replace_path(p,[0,0,0],0.);vw,_=c.control([0,0,0],0.)
        self.assertEqual(vw,(0.,.4))

class PreparationTests(unittest.TestCase):
    def test_single_hash_exception_and_matrix(self):
        p=verify();old=original();changed=[k for k in old if p[k]!=old[k]]
        self.assertEqual(changed,['frozen_sources'])
        delta=[k for k in old['frozen_sources'] if old['frozen_sources'][k]!=p['frozen_sources'][k]]
        self.assertEqual(delta,['research/nomad_phase20/execution.py'])
        self.assertEqual(len(p['main_order']),60);self.assertEqual(p['main_order'],old['main_order'])
    def test_routes_change_only_process_module(self):
        for mod in ('launch','report'):
            a=['/usr/bin/python3','-u','-m','nomad_phase26.'+mod,'--run-root',str(RUN_ROOT)]
            b=routed(a);self.assertEqual(b[:3]+b[4:],a[:3]+a[4:]);self.assertEqual(b[3],'nomad_phase27r.'+mod)
        self.assertEqual(routed(['git','push']),['git','push'])
    def test_reject_old_run_root(self):
        with self.assertRaises(ValueError):check_run_root(RUN_ROOT.with_name('phase26_pilot_01'))
    def test_same_evaluator_new_output(self):
        from .report import generate
        from nomad_phase26.report import generate as old_generate
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'metrics').mkdir()
            for j in original()['main_order']:
                r=dict(j,technical_validation='PASS',success=j['index']==201,collision=False,obstacle_collision=False,wall_overlap=False,corridor=False,
                    box_passage=j['scene'] in ('L2','H1','H2'),recovery_count=0,detour_trigger_count=0)
                (root/'metrics'/f"{j['scene']}_{j['index']}_{j['method']}.json").write_text(json.dumps(r))
            a=generate(root,root/'new',root/'new.md');b=old_generate(root,root/'old',root/'old.md')
            self.assertEqual(a,b)
            for name in ('runs.json','summary.csv','paired.csv','decision.json','exclusions.json'):
                self.assertEqual((root/'new'/name).read_bytes(),(root/'old'/name).read_bytes())

if __name__=='__main__':unittest.main()
