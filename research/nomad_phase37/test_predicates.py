import unittest
from types import SimpleNamespace
import numpy as np
from .predicates import observed_obstacle_ahead,guarded_direction


class PredicateTests(unittest.TestCase):
    def field(self):
        return SimpleNamespace(occupied=np.zeros((31,31),bool),observed=np.zeros((31,31),bool),origin=np.array([-1.,-1.]),h=.1)

    def test_five_observed_occupied_cells(self):
        f=self.field();f.occupied[10,11:16]=True;f.observed[10,11:16]=True
        self.assertTrue(observed_obstacle_ahead(f,[0,0,0],[1,0])['present'])
        f.observed[10,15]=False
        r=observed_obstacle_ahead(f,[0,0,0],[1,0]);self.assertFalse(r['present']);self.assertEqual(r['cells_ahead'],4)

    def test_unknown_and_observed_free_never_count(self):
        f=self.field();f.occupied[10,11:16]=True;f.observed[11,11:16]=True
        self.assertEqual(observed_obstacle_ahead(f,[0,0,0],[1,0])['cells_ahead'],0)

    def test_rectangle_rotation_translation_and_boundaries(self):
        f=self.field();f.occupied[16:21,14]=True;f.observed[:]=True
        # Origin (0.4,0.5), heading +y: .1 through .5m ahead.
        self.assertEqual(observed_obstacle_ahead(f,[.4,.5,0],[0,1])['cells_ahead'],5)
        self.assertEqual(observed_obstacle_ahead(f,[.4,.5,0],[0,-1])['cells_ahead'],0)

    def history(self,d3,d10):
        p=np.zeros((721,3));p[720,:2]=[2,2];p[504,:2]=p[720,:2]-d3;p[0,:2]=p[720,:2]-d10;return p

    def test_reversal_uses_ten_second_direction(self):
        p=self.history(np.array([-1.,0]),np.array([1.,0]));u,r=guarded_direction(p,720,[0,1])
        np.testing.assert_array_equal(u,[1,0]);self.assertTrue(r['overridden'])

    def test_exact_ninety_does_not_override(self):
        p=self.history(np.array([0.,1]),np.array([1.,0]));u,r=guarded_direction(p,720,[0,-1])
        np.testing.assert_array_equal(u,[0,-1]);self.assertFalse(r['overridden'])

    def test_short_or_missing_history_retains_baseline(self):
        p=self.history(np.array([-1.,0]),np.array([.29,0]));u,r=guarded_direction(p,720,[0,1]);self.assertFalse(r['overridden'])
        u,r=guarded_direction(p,719,[0,1]);self.assertEqual(r['reason'],'INCOMPLETE_10S_HISTORY')
        p=self.history(np.array([0.,0]),np.array([1.,0]));u,r=guarded_direction(p,720,[0,1]);self.assertEqual(r['reason'],'UNDEFINED_3S_DIRECTION')

if __name__=='__main__':unittest.main()
