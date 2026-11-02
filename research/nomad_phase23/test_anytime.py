import time,unittest,multiprocessing as mp,tempfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from nomad_phase20d.pool import initialize,ping
from .anytime import collect,select_messages
from .prediction import prefix,concatenate
from .response import reaction,avoiding_output

def fake_worker(payload,channel):
    try:
        time.sleep(payload['sleep']);now=time.monotonic_ns()
        channel.send(dict(kind='FEASIBLE',index=payload['index'],cost=payload['cost'],ready_ns=now,published_ns=now,path=[[0,0],[1,0]]))
        channel.send(dict(kind='DONE',index=payload['index'],published_ns=time.monotonic_ns()))
    except (BrokenPipeError,OSError):pass
    finally:channel.close()

class Tests(unittest.TestCase):
    def test_predicted_pose_and_same_motion_prefix(self):
        c=dict(B=[0.,0.,0.],previous_vw=[.2,0.],tick=0,baseline_old_path=[[0.,0.],[2.,0.]])
        r=prefix(c,.5,'continue_current_v_pp');np.testing.assert_allclose(r['B_pred'],[.1,0,0],atol=1e-12)
        self.assertEqual(len(r['speeds']),36);self.assertTrue(all(v==.2 for v in r['speeds']));self.assertFalse(r['future_log_used'])
        later=dict(poses=np.array([[.1,0,0],[.2,0,0]]),speeds=[.2],omegas=[0.],duration_s=1/72,completed=True,distance_m=.1,commands=[],tick_cap=2)
        joined=concatenate(r,later);np.testing.assert_allclose(joined['poses'][36],r['poses'][-1],atol=1e-15);self.assertEqual(joined['computation_prefix_ticks'],36)
    def test_anytime_cost_and_late_rejection(self):
        messages=[dict(kind='FEASIBLE',index=i,cost=cost,ready_ns=ready,published_ns=ready,received_ns=received) for i,cost,ready,received in [(0,5,10,11),(1,2,20,21),(2,0,30,101)]]
        self.assertEqual(select_messages(messages,100)['index'],1);self.assertIsNone(select_messages([],100))
    def test_parent_does_not_wait_for_late_worker(self):
        ctx=mp.get_context('spawn');queue=ctx.Queue()
        with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
            f=[pool.submit(ping) for _ in range(4)]
            for _ in range(4):queue.get(timeout=30)
            for x in f:x.result()
            payloads=[dict(index=0,cost=5,sleep=.01),dict(index=1,cost=2,sleep=.04),dict(index=2,cost=0,sleep=.4)]
            start=time.monotonic();r=collect(pool,payloads,time.monotonic_ns()+200_000_000,task=fake_worker)
            self.assertLess(time.monotonic()-start,.35);self.assertEqual(r['selected']['index'],1);self.assertGreater(r['pending_at_cutoff'],0)
    def test_reaction_delay_distance_and_censoring(self):
        box=dict(center_xy_m=[2.,0.],size_xyz_m=[.4,1.,.8]);c=dict(group='sudden',tick=720,B=[1.,0.,0.],spawn=dict(obstacle=box),oracle_config=dict(agent_radius_m=.09))
        path=[[1.,0.],[1.4,.8],[2.5,.8]];p=dict(path=path,B_pred=[1.,0.,0.],application_delay_s=.5,compute_s=.4)
        r=reaction(c,p,dict(computation_prefix_distance_m=.1),dict(first_map_available_s=8.,distance_to_snapshot_m=.3))
        self.assertEqual(r['reaction_delay_s'],2.5);self.assertAlmostEqual(r['reaction_distance_m'],.4)
        self.assertFalse(avoiding_output([[1,0],[1.1,0]],[1,0,0],box,.09)['avoids'])
    def test_half_second_decision_threshold(self):
        from .report import decision
        rows=[dict(group=g,method=m,oracle_collisions=0,planning_failure_fraction=0.,progress_median=1.,compute_p95_s=.5) for g in ('static','sudden') for m in ('U','C0')]
        self.assertEqual(decision(rows)['label'],'UNIFIED_READY')
        rows[0]['compute_p95_s']=.5001
        self.assertEqual(decision(rows)['label'],'UNIFIED_NOT_READY')
    def test_reaction_is_earliest_observed_per_run(self):
        from .report import reaction_table
        records=[dict(case=dict(group='sudden',run='test'),methods=dict(U=dict(row=dict(case_id=str(i),reaction_delay_s=d,reaction_distance_m=d/10,output_time_s=d+1,reaction_status='OBSERVED_AVOIDING_OUTPUT_UPPER_BOUND')))) for i,d in enumerate([4.,2.])]
        rows=reaction_table(records);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['reaction_delay_upper_bound_s'],2.)
    def test_amendment_report_without_results(self):
        from .report import write_selection_report
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'report.md';write_selection_report(dict(selection_evidence=None),file)
            text=file.read_text();self.assertIn('29/30',text);self.assertIn('19/30',text);self.assertIn('NOT_EVALUATED',text);self.assertIn('0.5s',text)

if __name__=='__main__':unittest.main()
