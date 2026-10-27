import unittest
from unittest.mock import patch
import numpy as np
from .diagnose import ablation_label, wall_label, detour_label, detour_start, regression, solve_once, summarize_sigma


class DiagnosticsTest(unittest.TestCase):
    def test_preregistered_priorities(self):
        self.assertEqual(ablation_label(4,4,4),'NO_DANGEROUS_CORRECTIONS')
        self.assertEqual(ablation_label(10,5,9),'CONSTRAINT_MATTERS')
        self.assertEqual(ablation_label(10,4,8),'CERTIFICATE_SUFFICES')
        self.assertEqual(wall_label(True,.1,.1,-.01),'UNOBSERVED_WALL')
        self.assertEqual(wall_label(False,.1,.1,-.01),'EXECUTION')
        self.assertEqual(wall_label(False,.1,.01,-.01),'DEPTH_ERROR')
        rr=[dict(all_unsafe=False,remaining_length_m=.2,disposition='NONCONVERGED')]*2
        self.assertEqual(detour_label(rr),'SHORT_REMAINING')

    def test_regression_keeps_scheduling_separate(self):
        poses=np.column_stack([np.arange(8)*.1,np.zeros((8,2))]).tolist()
        a=dict(poses=poses,accepted=True,disposition='ACCEPTED')
        b=dict(poses=poses,accepted=True,solver={'success':True},disposition='STALE')
        self.assertTrue(regression(a,b)['regression_match'])
        self.assertEqual(regression(a,b)['replay_with_saved_schedule_disposition'],'STALE')
        self.assertFalse(regression(a,{'event':'TERMINAL_UNAPPLIED'})['regression_comparable'])

    def test_initialization_rejection_does_not_solve(self):
        j=dict(world_xy=np.column_stack([np.arange(1,9)*.1,np.zeros(8)]),boundary=[0,0,0],previous_command=[0,0],previous_xy=None)
        with patch('nomad_phase5.graph.minimize',side_effect=AssertionError('must not solve')):
            r=solve_once(j,None,'NEITHER')
        self.assertEqual(r['disposition'],'INITIALIZATION_REJECTED')

    def test_detour_uses_running_max_and_unwrapped_heading(self):
        p=np.array([[0,0,0],[.4,0,0],[.3,0,0],[.09,0,0]])
        self.assertEqual(detour_start(p),(3,'X_BACKTRACK_0.30M'))
        p=np.column_stack([np.arange(20),np.zeros(20),(np.arange(20)*.4+np.pi)%(2*np.pi)-np.pi])
        self.assertEqual(detour_start(p),(16,'ABS_HEADING_2PI'))

    def test_sigma_threshold_and_cert_only_is_same_solution(self):
        from .diagnose import SIGMAS
        rows=[]
        for name in ('baseline',*SIGMAS):
            for i in range(20):rows.append(dict(sigma=name,accepted=i>0 if name=='prior_x0.5' else True,baseline_accepted=True,path_difference_median_m=.02,path_difference_max_m=.03))
        self.assertTrue(all(r['within_threshold'] for r in summarize_sigma(rows)))
        class Field:
            def exact_clearance(self,xy):return .01
        j=dict(world_xy=[],boundary=[],previous_command=[],previous_xy=None)
        with patch('nomad_phase15c.diagnose.GraphGF') as graph:
            graph.return_value.p={}
            graph.return_value.solve.return_value=(np.zeros((8,3)),dict(success=True,feasible=True))
            r=solve_once(j,Field(),'CERT_ONLY')
        self.assertFalse(r['accepted']);self.assertEqual(r['disposition'],'CONSTRAINT_FAILED')


if __name__=='__main__':unittest.main()
