import io,queue,threading,time,unittest,tempfile
from pathlib import Path
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
        from .drive_backend import composite
        a={**self.result(time.monotonic_ns()),'cache':{}}
        job=dict(job_id=1,dispatch_ns=time.monotonic_ns(),cache_file='synthetic',B=[0,0,0],u_ref=[1,0],anchor_xy=[0,0])
        with patch('nomad_phase22.drive_backend.astar_job',return_value=a),patch('nomad_phase22.drive_backend.load_cache',return_value=(None,None)),patch('nomad_phase22.drive_backend.graph_refine',side_effect=ValueError('injected backend failure')):
            result=composite(None,job,lambda message:None,{},dict(lambda_=4,**{'lambda':4,'smoothing_iterations':0}))
        self.assertEqual(result['branch'],'A*_RAW');self.assertEqual(result['stage_results']['refine']['results'][0]['disposition'],'TECHNICAL_ERROR')
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
    def test_real_worker_free_straight_path(self):
        from nomad_phase20d.recent import RecentMap,RecentSnapshot
        field=RecentMap([-1.,-2.,3.,2.]);field.observed[:]=True;field.last_free_tick[:]=0;field.values[:]=1.
        snap=RecentSnapshot(field,dict(frame_id=0,sim_s=0.))
        with tempfile.TemporaryDirectory(prefix='phase22-worker-') as folder:
            worker=Worker(Path(folder),lambda job:dict(anchor_xy=[0.,0.],anchor_source='SYNTHETIC_TEST'))
            try:
                now=time.monotonic_ns();worker.submit(dict(kind='R3',job_id=1,B=[0.,0.,0.],u_ref=[1.,0.],evaluation_tick=0,dispatch_ns=now,simulation_time_s=0.),snap)
                deadline=time.monotonic()+10;result=None
                while result is None and time.monotonic()<deadline:result=worker.poll();time.sleep(.005)
                self.assertIsNotNone(result);self.assertNotIn('error',result,result)
                self.assertIn(result['branch'],('REFINED','A*_RAW'),result)
                self.assertLessEqual(result['end_ns']-now,1_000_000_000)
                path=np.array(result['results'][result['selected_sample']]['path']);self.assertEqual(path.shape,(11,2));np.testing.assert_array_equal(path[0],[0.,0.])
            finally:worker.close()
    def test_report_labels_missing_pair_and_blank_figures(self):
        from . import drive_report as report,drive_visualize as visual
        from .drive_config import protocol,METHODS
        p=protocol();p['indices']=[121,122];p['unclassified_label']='PENDING_USER_DEFINITION'
        records=[]
        for scene in ('L2','L2B'):
            for index in p['indices']:
                for method in METHODS:
                    records.append(dict(scene=scene,index=index,method=method,output='/tmp/phase22-test-no-data',technical_validation='PASS',classification='SUCCESS',success=True,passed_box=True,passage_time_capped_s=10.,goal_time_s=40.,collision=False,corridor=False,detour_minimum_clearance_m=.1,detour_execution_jerk_rms=2.))
        # Secondary advantage alone cannot make a higher-collision method HELPS.
        for r in records:
            if r['method']=='P2F_ASTAR_GRAPH':r['detour_minimum_clearance_m']=.14;r['detour_execution_jerk_rms']=1.
            if r['scene']=='L2' and r['method']=='P2F_ASTAR_GRAPH':r['collision']=True;r['success']=False
        next(r for r in records if r['scene']=='L2B' and r['index']==122 and r['method']=='P1_GRAPH')['technical_validation']='FAIL'
        with patch.object(report,'protocol',return_value=p),patch.object(visual,'protocol',return_value=p),tempfile.TemporaryDirectory(prefix='phase22-report-') as folder:
            out=Path(folder);verdict=report.render(records,out/'results',out/'report.md')
            self.assertEqual(verdict['final'],'REFINE_HELPS');self.assertEqual(verdict['scenes'][0]['label'],'REFINE_HURTS')
            self.assertEqual(verdict['scenes'][1]['n'],1);self.assertEqual(verdict['additional'],'MIXED_HELDOUT')
            for name in ('outcomes.png','heldout_paths.png','clearance_jerk.png'):self.assertGreater((out/'results'/name).stat().st_size,1000)
            self.assertIn('All three methods by seed',(out/'report.md').read_text())
if __name__=='__main__':unittest.main()
