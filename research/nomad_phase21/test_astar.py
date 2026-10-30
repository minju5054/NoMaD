"""Generic solver tests only; does not freeze the unresolved baseline wiring."""
import time,unittest
import numpy as np
from nomad_phase19r.test_repair import synthetic
from nomad_phase20d.recent import CachedField
from .astar import solve

class Tests(unittest.TestCase):
    def run_case(self,obstacle):
        f=synthetic(obstacle);strict=object.__new__(CachedField);strict.__dict__.update(f.__dict__)
        return solve([0,0,0],[1,0],f,strict,1.,20,11,time.monotonic_ns()+1_000_000_000)
    def test_free_output_format(self):
        r=self.run_case(False);self.assertTrue(r['accepted'],r);self.assertEqual(np.shape(r['path']),(11,2));self.assertGreaterEqual(r['progress_m'],.5)
    def test_blocked_cells_avoided(self):
        r=self.run_case(True);self.assertTrue(r['accepted'],r);self.assertTrue(r['certificate_pass']);self.assertGreaterEqual(r['depth_clearance_m'],.025)
    def test_deadline(self):
        f=synthetic(False);start=time.monotonic_ns();r=solve([0,0,0],[1,0],f,f,1.,20,11,start-1)
        self.assertEqual(r['disposition'],'TIMEOUT');self.assertLess((time.monotonic_ns()-start)/1e9,.02)
if __name__=='__main__':unittest.main()

class RepairTests(unittest.TestCase):
    def test_repair_output_and_trust(self):
        from .astar import solve_repair
        f=synthetic(False);path=np.c_[np.linspace(0,1.2,8),np.zeros(8)];r=solve_repair(path,[0,0,0],f,1.,5,time.monotonic_ns()+1_000_000_000)
        self.assertTrue(r['accepted'],r);self.assertEqual(np.shape(r['path']),(8,2));self.assertLessEqual(r['max_edit_m'],.75*np.sqrt(2))
