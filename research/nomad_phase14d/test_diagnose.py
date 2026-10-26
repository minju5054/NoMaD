"""Minimum saved-run replay test; no Graph solve, inference or simulation."""
import unittest
from .diagnose import sources, replay_clearance, cause, conclusion


class Checks(unittest.TestCase):
    def test_saved_run_clearance_replay(self):
        cases,_=sources();r=next(s['record'] for s in cases if s['phase']==12 and s['record']['index']==26)
        computed=replay_clearance(r['output'])
        self.assertLessEqual(abs(computed['minimum_m']-r['minimum_obstacle_clearance_m']),1e-6)
        self.assertLessEqual(computed['max_clearance_error'],1e-6)
        self.assertLess(computed['max_pose_error'],1e-12)

    def test_preregistered_cause_order(self):
        row=dict(raw_selected_clearance_m=.024,corrected_clearance_m=.001,delta_m=-.023,
                 active_path_clearance_m=.001,executed_clearance_m=-.0001)
        self.assertEqual(cause(row),'SELECTION')
        row.update(raw_selected_clearance_m=.05,delta_m=-.049)
        self.assertEqual(cause(row),'GRAPH_SHIFT')
        row.update(corrected_clearance_m=.04,delta_m=-.01,active_path_clearance_m=.04)
        self.assertEqual(cause(row),'EXECUTION')
        rows=[dict(cause='SELECTION',SDF_WOULD_FIX='YES',SAFE_SAMPLE_EXISTED='YES') for _ in range(4)]
        self.assertEqual(conclusion(rows),'ADD_CONSTRAINT')  # Union and ordered rules.


if __name__=='__main__':unittest.main()
