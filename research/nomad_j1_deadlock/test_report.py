import unittest
import numpy as np
from .report import stop_intervals,within,lengths,candidate_details,result_reason

class Tests(unittest.TestCase):
    def test_72hz_interval_edges_and_exact_five_seconds(self):
        rows=[dict(simulation_time_s=i/72,v_m_s=0. if 1<=i<=360 else .1,w_rad_s=0.) for i in range(370)]
        stops=stop_intervals(rows);self.assertEqual(len(stops),1);self.assertEqual(stops[0]['start_tick'],0);self.assertEqual(stops[0]['end_tick'],360)
        self.assertEqual(stops[0]['duration_s'],5.)
        self.assertTrue(within(0.,stops[0]));self.assertFalse(within(5.,stops[0]))
        rows[360]['v_m_s']=.1;self.assertEqual(stop_intervals(rows),[])
    def test_remaining_and_signed_forward_components(self):
        full,remaining=lengths([[0.,0.],[1.,0.]],[.4,.2,0.]);self.assertEqual(full,1.);self.assertAlmostEqual(remaining,.6)
        samples=np.zeros((8,8,2));samples[:,:,0]=np.linspace(.1,1.,8)
        event=dict(j_selection=dict(candidates=[dict(index=i,remaining_length_m=i/10,safe=i in (1,3)) for i in range(8)],
                    selected_sample=3,installed=False,disposition='EC_REJECT_KEEP_CURRENT'),
                   observation_pose=[0.,0.,np.pi/2],agent_pose_at_switch=[0.,.2,np.pi/2],overnight_metric_samples=samples.tolist())
        r=candidate_details(event);self.assertEqual(r['longest_all_index'],7);self.assertEqual(r['longest_safe_index'],3)
        self.assertAlmostEqual(r['longest_safe_forward_body_m'],.8);self.assertAlmostEqual(r['longest_safe_forward_plus_y_m'],.8)
        self.assertEqual(result_reason(dict(disposition='INITIALIZATION_REJECTED',error="ValueError('Previous speed is zero: boundary curvature undefined')")),
                         'BOUNDARY_CURVATURE_UNDEFINED')

if __name__=='__main__':unittest.main()
