import unittest
import numpy as np
from scipy.ndimage import distance_transform_edt
from nomad_phase15.depth_sdf import DepthSDF
from .maps import policy_map
from .metrics import path_unknown

def base_field():
    f=DepthSDF([-2,-2,2,2],resolution=.1);f.observed[:]=True;f.metadata={'frame_id':1}
    f.last_free_tick=np.full_like(f.occupied,-1000,dtype=np.int32)
    f.occupied[20,30]=True;f.values=distance_transform_edt(~f.occupied,sampling=f.h)-f.radius
    return f

class MapTests(unittest.TestCase):
    def test_VU_exact_base_and_no_stale_free_blocking(self):
        f=base_field();f.observed[20,22]=False;before={n:getattr(f,n).copy() for n in ('values','occupied','observed','last_free_tick')}
        out,info=policy_map(f,[0,0,0],'VU')
        np.testing.assert_array_equal(out.values,f.values);np.testing.assert_array_equal(out.occupied,f.occupied)
        self.assertFalse(out.occupied[20,22]);self.assertFalse(out.occupied[20,21]);self.assertEqual(info['added_unknown_cells'],0)
        for n,v in before.items():np.testing.assert_array_equal(getattr(f,n),v)
        self.assertFalse(out.occupied.flags.writeable);self.assertFalse(out.values.flags.writeable)
    def test_VN_unknown_radius_inclusive_and_keeps_all_occupied(self):
        f=base_field();f.observed[20,26]=False;f.observed[20,27]=False
        out,info=policy_map(f,[0,0,0],'VN')
        self.assertTrue(out.occupied[20,26]);self.assertFalse(out.occupied[20,27]);self.assertTrue(out.occupied[20,30])
        self.assertFalse(out.occupied[20,21]);self.assertEqual(info['added_unknown_cells'],1)
        np.testing.assert_array_equal(out.values,distance_transform_edt(~out.occupied,sampling=f.h)-f.radius)
    def test_unknown_metrics_use_original_observed_for_both_domains(self):
        f=base_field();f.observed[20,22:25]=False;f.observed[20,28:30]=False
        r=path_unknown(f,[[0,0],[1,0]],[0,0,0])
        self.assertEqual(r['sampled_points'],201);self.assertGreater(r['unknown_fraction_all'],0.)
        self.assertGreater(r['unknown_fraction_within_0p6'],0.)
        self.assertLessEqual(r['sample_arclength_step_m'],.005)

if __name__=='__main__':unittest.main()
