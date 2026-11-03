import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase23.prediction import prefix
from .decision import recompute_trigger,advanced_case,choose_mode
from .run import combine_plans

class Tests(unittest.TestCase):
    def history(self):
        poses=np.zeros((301,3));poses[:109,0]=np.linspace(0,.8,109);poses[109:,0]=.8
        shape=(8,25);occupied=np.zeros(shape,bool);occupied[3,13:18]=True;ids=occupied.astype(np.int32)
        field=SimpleNamespace(origin=np.array([0.,-.3]),h=.1,occupied=occupied,new_component_ids=ids,first_occupied_tick=np.where(occupied,108,-1),component_births={1:108},metadata={})
        return poses,field
    def test_existing20f_trigger_on_recorded_history(self):
        poses,field=self.history();fired,detail=recompute_trigger(poses,300,field);self.assertTrue(fired);self.assertEqual(detail['reason'],'NO_PROGRESS')
        poses[-1,0]=1.3;self.assertFalse(recompute_trigger(poses,300,field)[0])
        poses[-1,0]=.8;field.occupied[:]=False;fired,detail=recompute_trigger(poses,300,field);self.assertFalse(fired);self.assertEqual(detail['reason'],'NO_NEW_OBSTACLE_AHEAD')
    def test_two_stage_time_sum_pose_and_braking(self):
        c=dict(B=[0.,0.,0.],previous_vw=[.2,0.],tick=0,old_path=[[0,0],[2,0]])
        motion1=prefix(c,.5,'existing_rollout')
        with patch('nomad_phase24.decision.pose_history',return_value=np.array([[0.,0.,0.]])):
            second_case,history=advanced_case(c,motion1)
        self.assertIsNone(second_case['executing_path']);self.assertEqual(second_case['tick'],36)
        motion2=prefix(second_case,.5,'existing_rollout');self.assertLess(motion2['previous_vw'][0],motion1['previous_vw'][0])
        first=dict(mode='NORMAL',accepted=False,prediction=motion1,compute_s=.2,source_B=c['B']);second=dict(mode='DETOUR',accepted=True,prediction=motion2,compute_s=.35)
        combined=combine_plans(first,second);self.assertAlmostEqual(combined['compute_s'],.55);self.assertEqual(combined['application_delay_s'],1.)
        self.assertEqual(len(combined['prediction']['speeds']),72);np.testing.assert_array_equal(history[-1],motion1['B_pred']);np.testing.assert_array_equal(combined['prediction']['poses'][-1],motion2['B_pred'])
        first['accepted']=True
        with self.assertRaises(AssertionError):combine_plans(first,second)
    def test_missing_history_uses_c0_only(self):
        c=dict(c0_record='/tmp/c0-decision-test.json',B=[0,0,0],run='/unused',tick=0)
        with patch('nomad_phase24.decision.Path.exists',return_value=True),patch('nomad_phase24.decision.Path.read_text',return_value='{"methods":{"C0":{"plan":{"disposition":"STOP_WAIT","stages":[{"kind":"R3"}]}}}}'),patch('nomad_phase24.decision.resolve_direction',return_value=([1,0],{})):
            result=choose_mode(c,None,['missing-depth']);self.assertEqual(result['mode'],'DETOUR');self.assertEqual(result['mode_source'],'MODE_FROM_C0')
if __name__=='__main__':unittest.main()
