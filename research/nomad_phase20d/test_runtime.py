import json,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .recent import RecentMap,RecentSnapshot
from .runtime import Execution
from .config import runtime_config,place
from .campaign import plan_jobs
from nomad_phase20b.worker import disposition

class RuntimeTests(unittest.TestCase):
    def test_protocol_order_geometry_sockets(self):
        jobs=plan_jobs(Path('/tmp/phase20d-'+'x'*100));self.assertEqual(len(jobs),12)
        self.assertEqual([j['index'] for j in jobs],[86]*4+[87]*4+[88]*4)
        rng=np.random.default_rng(20261103)
        self.assertEqual([j['method'] for j in jobs],[str(m) for i in range(86,89) for l in ('L2','L3') for m in rng.permutation(['M1_ROTATE','M3_DETOUR'])])
        for j in jobs:
            self.assertLess(j['socket_bytes'],100);self.assertEqual(j['seed_offset'],10000*j['index'])
            c=runtime_config(j['method'],j['index'],level=j['scene']);r=place(c,[2.02,.1,0])
            np.testing.assert_allclose(sorted([r['left_wall_gap_m'],r['right_wall_gap_m']]),[.9,.9] if j['scene']=='L2' else [.2,.8],atol=1e-12)
            self.assertEqual(r['status'],'PLACED');self.assertAlmostEqual(r['measured_world_forward_surface_d_m'],1.)
    def test_timeout(self):
        self.assertEqual(disposition(None,0,1_000_000_001),'TIMEOUT')
        self.assertEqual(disposition(dict(end_ns=999_999_999,selected_sample=0),0,1_010_000_000),'ACCEPTED')
        self.assertEqual(disposition(dict(end_ns=1_000_000_001,selected_sample=0),0,1_010_000_000),'TIMEOUT')
    def test_real_detour_delivery_hold_and_recheck(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);f=RecentMap([-2,-2,3,2]);f.observed[:]=True;f.last_free_tick[:]=216
            field=RecentSnapshot(f,dict(frame_id=0,sim_s=3.,publication_monotonic_ns=time.monotonic_ns(),file=str(out/'not_yet_archived.npz')))
            ex=Execution('M3_DETOUR',out);ex.depth_maps=SimpleNamespace(snapshot=lambda:field)
            core=SimpleNamespace(pose=np.array([0.,0.,0.]),v=0.,w=0.)
            def refresh(t):return dict(valid=False,monotonic_ns=time.monotonic_ns(),simulation_time_s=t)
            try:
                for i in range(217):ex.integrate_record(core.pose,core.pose)
                ex.apply(core,refresh(3.),None)
                self.assertIsNotNone(ex.detour);self.assertEqual(ex.detour['trigger'],'B')
                deadline=time.monotonic()+5
                while ex.detour is not None and not ex.detour_active and time.monotonic()<deadline:
                    time.sleep(.005);ex.apply(core,refresh(3.+1/9),None)
                self.assertTrue(ex.detour_active);self.assertGreater(core.v,0.)
                selected=ex.sp.follower.path.points.copy()
                switch=dict(id=99);ex.apply(core,refresh(3.+2/9),switch)
                self.assertTrue(switch['phase20d_selection_deferred']);np.testing.assert_array_equal(selected,ex.sp.follower.path.points)
                ex.plant.integrate(core,1);self.assertGreater(core.pose[0],0.)
                ex.apply(core,refresh(5.+1/9),None)
                self.assertIsNone(ex.detour);self.assertEqual(ex.mode,'STOP_WAIT')
                self.assertGreater(ex.no_progress.cooldown_until,8.)
                log=[json.loads(x) for x in (out/'detour.jsonl').read_text().splitlines()]
                self.assertTrue(any(r['event']=='END' and r['reason']=='PATH_BECAME_UNSAFE' for r in log))
                completed=[json.loads(x) for x in (out/'repair_pool_jobs.jsonl').read_text().splitlines()]
                self.assertEqual(completed[0]['cache']['edt_computations'],1);self.assertEqual(len(completed[0]['results']),7)
            finally:ex.close()
    def test_report_labels(self):
        from .report import render
        records=[dict(scene=l,index=i,method=m,technical_validation='PASS',classification='SUCCESS',success=True,detour_applied=1 if m=='M3_DETOUR' else 0,output='/missing') for l in ('L2','L3') for i in range(86,89) for m in ('M1_ROTATE','M3_DETOUR')]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);v=render(records,p/'out',p/'report.md',False)
            self.assertTrue(all(r['label']=='DETOUR_NO_HELP' for r in v));self.assertIn('탐색적 파일럿',(p/'report.md').read_text())
            self.assertTrue((p/'out/summary.csv').exists())

if __name__=='__main__':unittest.main()
