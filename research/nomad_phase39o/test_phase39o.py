"""Synthetic-only numerical tests; never solve the saved Phase38 dataset."""
import json,multiprocessing as mp,tempfile,time,unittest
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase20.repair import RepairGraphR2,solve_sample
from nomad_phase20c.detour_known import KnownDetourGraph
from .solver import SlackGraph,certificate,escape_threshold,solve
from .inputs import extra_path
from .report import gate

class Plane:
    h=.01;radius=.09;error_bound=.01/np.sqrt(2)
    def __init__(self,height=1.,gradient=(.03,.02)):self.height=height;self.gradient=np.array(gradient)
    def query(self,q):q=np.asarray(q);return self.height+q@self.gradient,np.repeat(self.gradient[None],len(q),axis=0)
    def exact_clearance(self,p):return float(self.query(np.asarray(p))[0].min())
    def unknown_fraction(self,p):return 0.

def jacobian(fn,x,step=1e-6):
    return np.column_stack([(fn(x+np.eye(len(x))[i]*step)-fn(x-np.eye(len(x))[i]*step))/(2*step) for i in range(len(x))])

class GraphTests(unittest.TestCase):
    def graph(self,kind,height=.014):
        B=np.array([0.,0.,.1]);base=Plane(height)
        if kind=='R2':return RepairGraphR2(np.c_[np.linspace(0,1.05,8),np.zeros(8)],B,base)
        g=KnownDetourGraph(B,[1,0],base,Plane(height+.02),30)
        g.initial*=.93;return g
    def test_analytic_gradients_slack_and_escape(self):
        for kind in ('R2','R3'):
            for variant in ('V1','V2'):
                with self.subTest(kind=kind,variant=variant):
                    g=SlackGraph(self.graph(kind),variant);z=g.initial.copy();z[:g.n]+=.001*np.sin(np.arange(g.n));z[g.n:]+=.003
                    _,grad=g.objective(z);numeric=jacobian(lambda x:np.array([g.objective(x)[0]]),z).ravel()
                    np.testing.assert_allclose(grad,numeric,atol=1e-5,rtol=0)
                    _,j=g.constraints(z);np.testing.assert_allclose(j,jacobian(lambda x:g.constraints(x)[0],z),atol=1e-5,rtol=0)
    def test_frozen_objective_and_no_escape_for_high_B(self):
        for kind in ('R2','R3'):
            old=self.graph(kind,1.);g=SlackGraph(old,'V2');self.assertFalse(g.escape)
            value,grad=g.objective(np.r_[old.initial,np.zeros(g.m)]);baseline,j=old.objective(old.initial)
            self.assertEqual(value,baseline);np.testing.assert_array_equal(grad[:g.n],j)
            a,b=g.physical_constraints(old.initial);c,d=old.constraints(old.initial)
            np.testing.assert_array_equal(a,c);np.testing.assert_array_equal(b,d)
            self.assertEqual(certificate(old,old.points(old.initial),False),old.certificate(old.points(old.initial)))
    def test_V0_frozen_replay_and_slack_zero_open_scene(self):
        native=np.c_[np.linspace(0,1.05,8),np.zeros(8)];B=[0,0,0];field=Plane()
        job=dict(variant='V0',B=B,samples_world=np.repeat(native[None],8,axis=0).tolist())
        a=solve_sample(native,B,field);b=solve('R2',0,job,field,None)
        self.assertEqual(a['disposition'],b['disposition']);np.testing.assert_array_equal(a['path'],b['path'])
        job['variant']='V1';r=solve('R2',0,job,field,None)
        self.assertTrue(r['accepted']);self.assertLessEqual(r['xi_max'],1e-6);self.assertTrue(r['certificate_pass']);json.dumps(r,allow_nan=False)
    def test_negative_B_precheck_only_V1(self):
        old=self.graph('R3',-.03);a=SlackGraph(old,'V1').solve()
        self.assertFalse(a['solver_started']);self.assertEqual(a['disposition'],'NEGATIVE_DEPTH_AT_B')
        g=SlackGraph(old,'V2')
        def result(fun,x,**kw):return SimpleNamespace(x=x,success=False,status=8,message='test stop',nit=1,fun=fun(x))
        with patch('nomad_phase39o.solver.minimize',side_effect=result) as called:b=g.solve()
        called.assert_called_once();self.assertTrue(b['solver_started']);self.assertTrue(b['escape_negative_B'])
        with patch.object(KnownDetourGraph,'constraints',side_effect=AssertionError('V1 precheck must precede initial constraints')):
            r=solve('R3',0,dict(variant='V1',B=[0,0,0],u_ref=[1,0]),Plane(-.03),Plane(-.03))
            self.assertEqual(r['disposition'],'NEGATIVE_DEPTH_AT_B')
    def test_fixed_B_escape_infeasibility_not_hidden_by_slack(self):
        g=SlackGraph(self.graph('R3',-.03),'V2');x=g.graph.initial;values,_=g.physical_constraints(x)
        length=np.linalg.norm(g.graph.points(x)[1]-g.graph.B[:2])
        self.assertAlmostEqual(values[0],.005-length/16);self.assertLess(values[0],-1e-6)
        augmented,_=g.constraints(g.initial);self.assertGreaterEqual(augmented[0],-1e-12)
    def test_end_threshold_continuous_certificate_is_conservative(self):
        g=self.graph('R3',.01);p=np.array([[0,0],[.2,0],[.4,0]])
        r=certificate(g,p,True);self.assertFalse(r['certificate_pass'])
        intervals=r['certificate_segments'];self.assertEqual(len(intervals),3)
        self.assertEqual([x['strict_field'] for x in intervals],[False,False,True])
        for row in intervals:self.assertAlmostEqual(row['threshold_m'],float(escape_threshold(g.cB,row['s_b'])) if not row['strict_field'] else .025)
    def test_slack_and_physical_tolerances_both_required(self):
        g=SlackGraph(self.graph('R3',1.),'V1');z=g.initial.copy();z[-1]=2e-6
        def result(fun,x,**kw):return SimpleNamespace(x=z,success=True,status=0,message='test',nit=1,fun=fun(z))
        with patch('nomad_phase39o.solver.minimize',side_effect=result):r=g.solve()
        self.assertFalse(r['accepted']);self.assertEqual(r['disposition'],'SLACK_REJECTED')

class PreparationTests(unittest.TestCase):
    def test_extra_suffix_11_points_and_exclusion_no_padding(self):
        p,d=extra_path([[0,0],[.5,0]],[0,0,0]);self.assertIsNone(p);self.assertEqual(d['reason'],'SHORT_SUFFIX')
        p,d=extra_path([[0,0],[2,0]],[.2,0,0]);self.assertEqual(np.shape(p),(11,2));np.testing.assert_array_equal(p[0],[.2,0])
        self.assertTrue(np.allclose(np.linalg.norm(np.diff(p,axis=0),axis=1),.15))
    def test_gate_any_simplest_and_incomplete(self):
        cases=[dict(case_id=str(i),scene='SLW') for i in range(10)];rows=[]
        for v,count in (('V0',2),('V1',5),('V2',7),('V3',9)):
            rows.extend(dict(case_id=str(i),scene='SLW',variant=v,success=i<count,job_wall_s=.9,accepted_certificate_failures=0) for i in range(10))
        self.assertEqual(gate(rows,cases)['selected_variant'],'V1')
        rows[10]['accepted_certificate_failures']=1;self.assertEqual(gate(rows,cases)['selected_variant'],'V2')
        self.assertEqual(gate(rows[:-1],cases)['label'],'NOT_EVALUATED')
    def test_V0_pool_calls_frozen_evaluator(self):
        from . import pool
        with patch.object(pool.frozen,'evaluate_job',return_value='FROZEN') as call:
            job=dict(variant='V0');self.assertEqual(pool.evaluate_job(None,job),'FROZEN');call.assert_called_once_with(None,job)
    def test_four_process_pool_and_storage_v2_on_synthetic_input(self):
        from nomad_phase20d.recent import RecentMap,RecentSnapshot
        from nomad_phase33p.storage import save_snapshot,install
        from nomad_storage_sdf.loader import load_npz
        from nomad_phase20d.pool import ping
        from .pool import initialize,evaluate_job
        install()
        field=RecentMap([-2,-2,2,2],resolution=.05);field.observed[:]=True;field.last_free_tick[:]=0
        snap=RecentSnapshot(field,dict(frame_id=0,sim_s=0))
        native=np.c_[np.linspace(0,1.05,8),np.zeros(8)]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);file=root/'input.npz';save_snapshot(snap,file)
            with np.load(file) as z:self.assertNotIn('values',z.files)
            np.testing.assert_array_equal(load_npz(file)['values'],snap.values)
            context=mp.get_context('spawn');ready=context.Queue()
            with ProcessPoolExecutor(max_workers=4,mp_context=context,initializer=initialize,initargs=(ready,)) as pool:
                warm=[pool.submit(ping) for _ in range(4)];pids=[ready.get(timeout=30) for _ in range(4)]
                for f in warm:f.result()
                self.assertEqual(len(set(pids)),4)
                common=dict(job_id=0,kind='R2',snapshot_file=str(file),cache_file=str(root/'cache.npz'),B=[0,0,0],samples_world=np.repeat(native[None],8,axis=0).tolist(),extra_initializations=[])
                a=evaluate_job(pool,dict(common,variant='V0',dispatch_ns=time.monotonic_ns()))
                b=evaluate_job(pool,dict(common,variant='V1',dispatch_ns=time.monotonic_ns()))
                self.assertEqual(len(a['results']),8);self.assertEqual(len(b['results']),8)
                self.assertIsNotNone(a['selected_sample']);self.assertIsNotNone(b['selected_sample'])
                json.dumps([a,b],allow_nan=False)
    def test_V3_keeps_seven_fans_and_appends_extra_seeds(self):
        from .pool import variant_job
        from nomad_phase20d.recent import RecentMap,RecentSnapshot
        from nomad_phase33p.storage import save_snapshot,install
        install();field=RecentMap([-2,-2,2,2],resolution=.05);field.observed[:]=True;field.last_free_tick[:]=0
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'input.npz';save_snapshot(RecentSnapshot(field,dict(frame_id=0,sim_s=0)),f)
            counts=[]
            class Pool:
                def map(self,fn,args):
                    args=list(args);counts.append(len(args));return [dict(accepted=False,total_attempt_s=0) for _ in args]
            job=dict(kind='R3',variant='V3',job_id=1,dispatch_ns=time.monotonic_ns(),snapshot_file=str(f),cache_file=str(Path(d)/'cache.npz'),evaluation_tick=0,extra_initializations=[{}]*9)
            variant_job(Pool(),job);self.assertEqual(counts,[16])
    def test_fake_report_tables_and_registered_decision(self):
        from . import report
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'preparation').mkdir();(root/'jobs').mkdir()
            cases=[dict(case_id=str(i),scene='SLW',kind='R2',job={'B':[0,0,0]}) for i in range(10)]
            (root/'preparation/inputs.json').write_text(json.dumps(cases))
            (root/'preparation/inventory.json').write_text(json.dumps(dict(saved_jobs=10,missing_jobs=0,saved_negative_depth_jobs=0)))
            (root/'protocol.json').write_text(json.dumps(dict(selected_jobs=10,estimated_minutes=1.)))
            for v,n in (('V0',2),('V1',5),('V2',6),('V3',6)):
                for i,c in enumerate(cases):
                    yes=i<n;r=dict(accepted=yes,disposition='ACCEPTED' if yes else 'NONCONVERGED',reference=[[0,0],[1,0]],path=[[0,0],[1,0]])
                    data=dict(case_id=str(i),variant=v,numeric=dict(results=[r],selected_sample=0 if yes else None,pool_wall_s=.2),
                        certificate_audit=[dict(index=0,certificate_pass=True,depth_clearance_m=.1,negative_B_escape=False,escape_schedule=False)] if yes else [])
                    (root/'jobs'/f'{i}_{v}.json').write_text(json.dumps(data))
            with patch.object(report,'OUT',root),patch.object(report,'HERE',root):result=report.generate(root,root/'report.md')
            self.assertEqual(result['label'],'GO_ONLINE');self.assertEqual(result['selected_variant'],'V1')
            for file in ('jobs.csv','solutions.csv','summary.csv','messages.csv','decision.json'):self.assertTrue((root/file).exists())

if __name__=='__main__':unittest.main()
