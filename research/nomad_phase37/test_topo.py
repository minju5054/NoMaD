import unittest
import numpy as np
from .topo import TopoH,possible_query
from nomad_isaac.topomap import candidate_range


def scores(raw,raw_distance=1.,other=5.):
    result={i:float(other) for i in range(21)};result[raw]=raw_distance;return result


class TopoTests(unittest.TestCase):
    def test_three_backward_queries_then_release(self):
        state=TopoH(6,0)
        for raw,c in ((4,1),(3,2)):
            r=state.query(scores(raw),20);self.assertEqual((r['H'],r['c'],r['subgoal']),(6,c,6))
        r=state.query(scores(5),20);self.assertEqual((r['H'],r['c'],r['subgoal']),(5,0,6))

    def test_forward_or_equal_resets_counter(self):
        s=TopoH(6,2);r=s.query(scores(6,3.),20);self.assertEqual((r['H'],r['c'],r['subgoal']),(6,0,6))
        r=s.query(scores(8,2.9),20);self.assertEqual((r['H'],r['c'],r['subgoal']),(8,0,9))

    def test_retained_H_own_distance_controls_subgoal(self):
        s=TopoH(6,0);d=scores(4);d[6]=2.5
        r=s.query(d,20);self.assertEqual((r['H'],r['subgoal']),(6,7))

    def test_goal_override_and_window_frozen(self):
        s=TopoH(19,0);r=s.query(scores(19,5.,9.),20);self.assertEqual(r['subgoal'],20)
        self.assertEqual((r['candidate_start'],r['candidate_end_inclusive']),candidate_range(19,20,4))

    def test_missing_scores_do_not_mutate_online_state(self):
        s=TopoH(6,1)
        with self.assertRaisesRegex(ValueError,'UNMEASURED'):s.query({5:1.},20)
        self.assertEqual((s.H,s.c),(6,1))

    def test_envelope_contains_all_sampled_completions(self):
        rng=np.random.default_rng(20261110)
        for H in (0,6,18):
            for c in (0,1,2):
                complete={i:float(rng.uniform(-1,10)) for i in range(21)}
                observed={i:v for i,v in complete.items() if i%3!=0}
                envelope,missing=possible_query((H,c),observed,20)
                for _ in range(30):
                    full={i:observed[i] if i in observed else float(rng.uniform(-2,12)) for i in range(21)}
                    r=TopoH(H,c).query(full,20);self.assertIn((r['H'],r['c'],r['subgoal']),envelope)

if __name__=='__main__':unittest.main()
