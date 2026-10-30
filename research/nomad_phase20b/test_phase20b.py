import json,tempfile,time,unittest
from pathlib import Path
import numpy as np
from nomad_phase19r.test_repair import synthetic
from nomad_phase15b.depth import Snapshot
from nomad_phase20.repair import solve_sample
from nomad_phase19r.evaluate import select_repair
from .worker import RepairWorker,disposition
from .config import runtime_config,place


class Tests(unittest.TestCase):
    def test_parallel_matches_serial(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);field=synthetic(True);f=root/'snapshot.npz';field.save(f)
            field=Snapshot.load(f)
            from types import MappingProxyType
            field.metadata=MappingProxyType({**field.metadata,'file':str(f)})
            paths=np.repeat(np.c_[np.linspace(0,1.4,8),np.zeros(8)][None],8,axis=0)
            paths[:,:,1]+=np.arange(8)[:,None]*np.linspace(0,.014,8)[None]
            serial=[solve_sample(p,[0,0,0],field) for p in paths]
            worker=RepairWorker(root)
            try:
                worker.submit(dict(job_id=0,B=[0,0,0],samples_world=paths.tolist(),dispatch_ns=time.monotonic_ns()),field)
                deadline=time.monotonic()+30;result=None
                while result is None and time.monotonic()<deadline:result=worker.poll();time.sleep(.005)
                self.assertIsNotNone(result);self.assertFalse(result.get('error'))
                self.assertEqual(len(result['results']),8);self.assertEqual(result['selected_sample'],select_repair(serial))
                self.assertTrue(any(r['accepted'] for r in serial))
                for a,b in zip(serial,result['results']):
                    self.assertEqual(a['disposition'],b['disposition'])
                    if a['path'] is None:self.assertIsNone(b['path'])
                    else:np.testing.assert_allclose(a['path'],b['path'],atol=1e-6,rtol=0)
                env=json.loads((root/'repair_pool_environment.json').read_text())
                self.assertEqual(len(set(env['pids'])),4);self.assertEqual(env['python'],'/usr/bin/python3')
            finally:worker.close()

    def test_one_second_deadline(self):
        self.assertEqual(disposition(None,0,999_000_000),'WAIT')
        self.assertEqual(disposition(None,0,1_001_000_000),'TIMEOUT')
        self.assertEqual(disposition(dict(end_ns=999_000_000,selected_sample=0),0,1_111_000_000),'ACCEPTED')
        self.assertEqual(disposition(dict(end_ns=1_001_000_000,selected_sample=0),0,1_111_000_000),'TIMEOUT')

    def test_frozen_size_gap_and_distance(self):
        for level in ('L2','L3'):
            for index in (80,81,82):
                c=runtime_config('M1_ROTATE',index,level=level);r=place(c,[2.04,.4,-.2])
                self.assertEqual(r['status'],'PLACED');self.assertAlmostEqual(r['measured_world_forward_surface_d_m'],1.)
                expected=[.9,.9] if level=='L2' else [.2,.8]
                np.testing.assert_allclose(sorted([r['left_wall_gap_m'],r['right_wall_gap_m']]),expected,atol=1e-12,rtol=0)
                self.assertEqual(r['obstacle']['center_xy_m'][1],0. if level=='L2' else .3 if index%2==0 else -.3)

    def test_plan_order_seeds_and_sockets(self):
        from .campaign import plan_jobs
        from .config import protocol
        jobs=plan_jobs(Path('/tmp/phase20b-test-'+'x'*90))
        self.assertEqual(len(jobs),12);self.assertEqual([r['index'] for r in jobs],[80]*4+[81]*4+[82]*4)
        self.assertTrue(all(r['socket_bytes']<100 and r['seed_offset']==r['index']*10000 for r in jobs))
        rng=np.random.default_rng(20261101);expected=[str(m) for i in (80,81,82) for level in ('L2','L3') for m in rng.permutation(['M1_ROTATE','M2_REPAIR'])]
        self.assertEqual([r['method'] for r in jobs],expected)

    def test_frozen_executor_and_report(self):
        import nomad_phase20.runtime as base
        from .runtime import Execution
        from .report import render,groups,decisions
        self.assertIs(Execution.apply,base.Execution.apply)
        self.assertIs(Execution.collect_repair.__code__,base.Execution.collect_repair.__code__)
        records=[]
        for level,n in [('L1',6),('L2',3),('L3',3)]:
            for i in range(n):
                for method in ('M1_ROTATE','M2_REPAIR'):
                    records.append(dict(scene=level,index=i,method=method,technical_validation='PASS',success=True,passed_box=True,
                        box_passage_time_s=10. if method=='M1_ROTATE' else 9.,repair_accepted=1 if method=='M2_REPAIR' else 0,
                        classification='SUCCESS',output='/nonexistent'))
        self.assertTrue(all(r['label']=='REPAIR_HELPS' for r in decisions(records,groups(records))))
        empty=[{**r,'box_passage_time_s':None} for r in records]
        self.assertTrue(all(r['label']=='REPAIR_NO_HELP' for r in decisions(empty,groups(empty))))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);render(records,p/'out',p/'report.md',make_figures=False)
            self.assertTrue((p/'out/decisions.json').exists());self.assertIn('REPAIR_HELPS',(p/'report.md').read_text())


if __name__=='__main__':unittest.main()
