import json,multiprocessing as mp,tempfile,unittest
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase20c.detour_known import KnownDetourGraph
from nomad_phase20d.recent import RecentSnapshot,build_cache
from nomad_phase33p.storage import save_snapshot,install
from .test_maps import base_field
from .maps import policy_map
from .cache import save_bundle,load_bundle
from .solver import MapGraph,map_certificate,solve
from .metrics import measure

class Plane:
    h=.01;radius=.09;error_bound=.01/np.sqrt(2)
    def __init__(self,value,gradient=(.02,.03)):self.value=value;self.gradient=np.array(gradient)
    def query(self,p):p=np.asarray(p);return self.value+p@self.gradient,np.repeat(self.gradient[None],len(p),axis=0)
    def exact_clearance(self,p):return float(self.query(p)[0].min())
    def unknown_fraction(self,p):return 0.

def jac(fn,x):
    eye=np.eye(len(x));h=1e-6
    return np.column_stack([(fn(x+h*d)-fn(x-h*d))/(2*h) for d in eye])

class SolverTests(unittest.TestCase):
    def test_hard_query_changes_but_soft_and_cB_are_frozen(self):
        for value in (.014,1.):
            base=Plane(value);cost=Plane(-.09,(0.,0.));planning=Plane(.5,(.04,-.01))
            original=KnownDetourGraph([0,0,.1],[1,0],base,cost,30);original.initial*=.93
            x=original.initial+.001*np.sin(np.arange(20));before=original.objective(x);m=MapGraph(original,planning,'VU')
            _,j=m.constraints(x);np.testing.assert_allclose(j,jac(lambda x:m.constraints(x)[0],x),atol=1e-5,rtol=0)
            after=original.objective(x);self.assertEqual(before[0],after[0]);np.testing.assert_array_equal(before[1],after[1])
            self.assertAlmostEqual(original.cB,value-base.error_bound);self.assertEqual(len(x),20)
            self.assertIs(original.field.strict,cost)
    def test_certificate_policy_map_applies_even_before_0p3(self):
        base=Plane(1.);cost=Plane(1.);g=KnownDetourGraph([0,0,0],[1,0],base,cost,0)
        path=[[0,0],[.2,0]];self.assertTrue(g.certificate(path)['certificate_pass'])
        self.assertFalse(map_certificate(g,path,Plane(-.09,(0,0)),'VN')['certificate_pass'])
        self.assertTrue(map_certificate(g,path,Plane(.5),'VU')['certificate_pass'])
    def test_cached_variants_and_R2_never_solved(self):
        from .pool import evaluate_job
        for variant,kind in (('V0','R3'),('VE','R3'),('VN','R2'),('VU','R2')):
            with self.assertRaises(AssertionError):evaluate_job(None,dict(variant=variant,kind=kind))
            with self.assertRaises(AssertionError):solve(0,dict(variant=variant,kind=kind),None,None,None)
    def test_map_bundle_preserves_three_views_and_exact_query(self):
        f=base_field();f.observed[20,22]=False;base=RecentSnapshot(f,dict(frame_id=1,sim_s=0));cost,_=build_cache(base,0)
        with tempfile.TemporaryDirectory() as d:
            for variant in ('VN','VU'):
                planning,_=policy_map(base,[0,0,0],variant);path=Path(d)/(variant+'.npz');save_bundle(base,cost,planning,path,variant)
                b,c,p=load_bundle(path)
                for before,after in ((base,b),(cost,c),(planning,p)):
                    np.testing.assert_array_equal(before.values,after.values);np.testing.assert_array_equal(before.occupied,after.occupied)
                self.assertEqual(p.exact_clearance([[0,0],[.5,0]]),planning.exact_clearance([[0,0],[.5,0]]))
    def test_cached_path_metrics_do_not_call_optimizer(self):
        f=base_field();f.observed[20,22]=False;snap=RecentSnapshot(f,dict(frame_id=1,sim_s=0))
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'input.npz';save_snapshot(snap,file)
            numeric=dict(results=[dict(accepted=True,path=[[0,0],[.5,0]])],selected_sample=0)
            with patch('scipy.optimize.minimize',side_effect=AssertionError('No baseline optimize')):
                result=measure(dict(job={'B':[0,0,0],'snapshot_file':str(file)}),numeric)
            self.assertFalse(result['optimizer_called']);self.assertFalse(result['EC_executed'])
            self.assertAlmostEqual(result['accepted_base_clearances'][0]['base_exact_clearance_m'],.41)
            self.assertGreater(result['selected_path_unknown']['unknown_fraction_all'],0);json.dumps(result,allow_nan=False)
    def test_new_map_four_worker_job_only(self):
        from .pool import initialize,ping,evaluate_job
        install();f=base_field();f.occupied[:]=False;f.values[:]=5.;f.observed[:]=True
        base=RecentSnapshot(f,dict(frame_id=1,sim_s=0))
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'input.npz';save_snapshot(base,file);ctx=mp.get_context('spawn');queue=ctx.Queue()
            with ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
                futures=[pool.submit(ping) for _ in range(4)];pids=[queue.get(timeout=30) for _ in range(4)]
                for future in futures:future.result()
                self.assertEqual(len(set(pids)),4)
                r=evaluate_job(pool,dict(variant='VU',kind='R3',job_id=0,B=[0,0,0],u_ref=[1,0],evaluation_tick=0,soft_policy_map=False,
                    snapshot_file=str(file),cache_file=str(Path(d)/'cache.npz')))
                self.assertEqual(len(r['results']),7);self.assertIsNotNone(r['selected_sample'])
                self.assertEqual(r['results'][r['selected_sample']]['soft_map'],'FROZEN_VE_PIECEWISE')
                json.dumps(r,allow_nan=False)

if __name__=='__main__':unittest.main()
