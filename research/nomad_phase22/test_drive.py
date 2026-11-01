import io,queue,threading,time,unittest
from unittest.mock import patch
import numpy as np
from .drive_backend import select_final,Worker
from .drive_geometry import point_gap,swept_gap,corners,bounds,local_pose
from nomad_isaac.common import integrate_se2
from nomad_isaac.clearance import swept_clearance

class Tests(unittest.TestCase):
    def result(self,end=20,selected=0):return dict(job_id=1,kind='R3',end_ns=end,selected_sample=selected,results=[dict(path=np.c_[np.linspace(0,1.5,11),np.zeros(11)].tolist())])
    def test_branch_order(self):
        a=self.result(20);r=self.result(50);g=self.result(70)
        self.assertEqual(select_final(a,r,g,100,80)[0],'REFINED')
        self.assertEqual(select_final(a,self.result(101),g,100,110)[0],'A*_RAW')
        self.assertEqual(select_final(self.result(20,None),None,g,100,80)[0],'GRAPH_FALLBACK')
        self.assertEqual(select_final(self.result(101,None),None,self.result(102),100,110)[0],'NONE')
        self.assertEqual(np.shape(select_final(a,None,None,100,101)[1]['results'][0]['path']),(11,2))
    def test_deadline_uses_cached_plan_not_late_refinement(self):
        w=object.__new__(Worker);w.lock=threading.Lock();w.event_lock=threading.Lock();w.events=io.StringIO();w.results=queue.SimpleQueue();w.delivered_ids=set();w.pending=dict(job_id=1,kind='R3',dispatch_ns=0);w.partial=self.result(500_000_000)
        with patch('nomad_phase22.drive_backend.time.monotonic_ns',return_value=1_111_111_111):r=w.poll()
        self.assertEqual(r['branch'],'A*_RAW');self.assertEqual(r['end_ns'],500_000_000);self.assertIsNone(w.poll())
        # A late old job must not suppress the next job's cached deadline fallback.
        w.pending=dict(job_id=2,kind='R3',dispatch_ns=0);w.partial={**self.result(500_000_000),'job_id':2};w.results.put(self.result(600_000_000))
        with patch('nomad_phase22.drive_backend.time.monotonic_ns',return_value=1_111_111_111):
            self.assertEqual(w.poll()['job_id'],1);self.assertEqual(w.poll()['job_id'],2)
    def test_rotated_geometry_uses_exact_rigid_transform(self):
        box=dict(center_xy_m=[3.,.25],size_xyz_m=[.4,1.,.8],yaw_deg=20.)
        p=np.array([2.2,-.3,.4]);a=swept_gap(p,.3,.4,1/72,box,.09);local=local_pose(p,box)
        b=swept_clearance(local,.3,.4,1/72,np.array([-.2,-.5]),np.array([.2,.5]),.09)
        self.assertEqual(a['lower_m'],b['lower_m']);self.assertEqual(a['upper_m'],b['upper_m'])
        samples=np.array([integrate_se2(p,.3,.4,t)[:2] for t in np.linspace(0,1/72,101)])
        values=[point_gap(q,box,.09) for q in samples];self.assertLessEqual(a['lower_m'],min(values)+1e-12)
        lo,hi=bounds(box);np.testing.assert_allclose(hi-lo,[.4*np.cos(np.pi/9)+np.sin(np.pi/9),.4*np.sin(np.pi/9)+np.cos(np.pi/9)],atol=1e-12)
if __name__=='__main__':unittest.main()
