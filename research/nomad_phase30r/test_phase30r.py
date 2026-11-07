import ast,copy,hashlib,inspect,io,json,tempfile,textwrap,unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase17.graph import ClearanceGraph as OriginalClearanceGraph
from nomad_phase20c.detour import DetourGraph,ANGLES
from nomad_phase20c.detour_known import KnownDetourGraph
from nomad_phase20.repair import RepairGraphR2
from nomad_phase19r.repair import RepairGraph
from nomad_phase29.runtime import PathExecution as OriginalExecution
from nomad_phase29.config import runtime_config as original_config
from nomad_phase29.client import Worker as OriginalWorker
from nomad_phase20d.worker import Worker as OriginalPoolWorker
from . import factors,config,launch,report,campaign
from .runtime import PathExecution
from .client import NormalWorker,PoolWorker

class LinearField:
    error_bound=.01/np.sqrt(2)
    def __init__(self,offset=.07):self.offset=offset
    def query(self,p):return self.offset+.1*np.asarray(p)[:,1],np.tile([0.,.1],(len(p),1))
    def exact_clearance(self,p):return float(self.query(p)[0].min())
    def unknown_fraction(self,p):return 0.

def gradient_check(fn,x):
    r,j=fn(x);numeric=np.empty_like(j);eps=1e-6
    for i in range(len(x)):
        a=x.copy();b=x.copy();a[i]+=eps;b[i]-=eps
        numeric[:,i]=(fn(a)[0]-fn(b)[0])/(2*eps)
    np.testing.assert_allclose(j,numeric,atol=1e-5,rtol=0)

def child_probe():
    import nomad_phase20d.pool as p
    import nomad_phase20.repair as repair
    from nomad_phase20c.detour import DetourGraph
    f=LinearField();g=KnownDetourGraph([0,0,0],[1,0],f,f,0)
    r,_=g.residual_jacobian(g.initial)
    return dict(clearance=r[19:109].tolist(),r2_original=p.solve_sample is repair.solve_sample,constants=DetourGraph.residual_jacobian.__code__.co_consts)

class Tests(unittest.TestCase):
    def test_normal_target_jacobian_and_all_other_residuals(self):
        xy=np.c_[np.linspace(.08,.8,8),np.zeros(8)];field=LinearField()
        old=OriginalClearanceGraph(xy,[0,0,0],[.2,0],field);new=factors.ClearanceGraph(xy,[0,0,0],[.2,0],field);x=old.initial.ravel()
        r,j,n,s=old.residual_jacobian(x);rr,jj,nn,ss=new.residual_jacobian(x)
        self.assertEqual(n,nn);self.assertEqual(s,ss);np.testing.assert_array_equal(rr[:-63],r[:-63]);np.testing.assert_array_equal(jj[:-63],j[:-63])
        np.testing.assert_allclose(rr[-63:],.2);np.testing.assert_allclose(r[-63:],1.6)
        gradient_check(new.clearance_residual,x)
        for a,b in zip(old.constraints(x),new.constraints(x)):np.testing.assert_array_equal(a,b)
        self.assertEqual(old.certificate(old.initial),new.certificate(new.initial));self.assertEqual(old.p,new.p)
        np.testing.assert_array_equal(old.bounds.lb,new.bounds.lb);np.testing.assert_array_equal(old.bounds.ub,new.bounds.ub)
        self.assertIs(new.clearance_residual.__code__,old.clearance_residual.__code__)
        self.assertEqual(new.clearance_residual.__globals__['D_PREF_M'],.08);self.assertEqual(old.clearance_residual.__globals__['D_PREF_M'],.15)
        self.assertEqual(new.solve.__globals__['D_PREF_M'],.08)
        inactive=factors.ClearanceGraph(xy,[0,0,0],[.2,0],LinearField(.10))
        np.testing.assert_array_equal(inactive.clearance_residual(x)[0],np.zeros(63))

    def test_r3_only_clearance_rows_change_constraints_same(self):
        f=LinearField();old=KnownDetourGraph([0,0,0],[1,0],f,f,0);x=old.initial.copy()
        r,j=old.residual_jacobian(x);g,jg=old.constraints(x);cert=old.certificate(old.points(x))
        with patch.object(DetourGraph,'residual_jacobian',factors.R3_RESIDUAL):
            new=KnownDetourGraph([0,0,0],[1,0],f,f,0);rr,jj=new.residual_jacobian(x)
            np.testing.assert_array_equal(rr[:19],r[:19]);np.testing.assert_array_equal(rr[-1:],r[-1:]);np.testing.assert_allclose(rr[19:109],.2)
            gg,jgg=new.constraints(x);np.testing.assert_array_equal(gg,g);np.testing.assert_array_equal(jgg,jg)
            self.assertEqual(cert,new.certificate(new.points(x)));np.testing.assert_array_equal(new.initial,old.initial)
            gradient_check(new.residual_jacobian,x)
            inactive=KnownDetourGraph([0,0,0],[1,0],LinearField(.10),LinearField(.10),0)
            np.testing.assert_array_equal(inactive.residual_jacobian(x)[0][19:109],np.zeros(90))
        self.assertEqual(ANGLES,(0,30,-30,60,-60,90,-90))
        self.assertIs(RepairGraphR2.residual_jacobian,RepairGraph.residual_jacobian)
        # AST identity avoids bytecode differences between system/Kit Python
        # patch versions; the normalized source has exactly two substitutions.
        self.assertEqual(factors.R3_RESIDUAL.phase30r_original_ast_sha256,factors.R3_RESIDUAL.phase30r_restored_ast_sha256)
        restored=tuple(.15 if isinstance(v,float) and v==.08 else v for v in factors.R3_RESIDUAL.__code__.co_consts)
        self.assertEqual(restored,factors.ORIGINAL_R3_RESIDUAL.__code__.co_consts)

    def test_transports_lifecycle_and_configuration_unchanged(self):
        for name in ('submit','compute','close'):self.assertIs(getattr(NormalWorker,name),getattr(OriginalWorker,name))
        for name in ('submit','poll','busy','close'):self.assertIs(getattr(PoolWorker,name),getattr(OriginalPoolWorker,name))
        for name in ('new_path','apply','collect_paths','close','start_detour','use_fallback','certificate'):
            self.assertIs(getattr(PathExecution,name),getattr(OriginalExecution,name))
        self.assertIs(PathExecution.__init__.__code__,OriginalExecution.__init__.__code__)
        for scene in config.SCENES:
            for index in (201,202):
                a=original_config('G18',index,90,scene);b=config.runtime_config('G18-R',index,90,scene)
                b.pop('phase30r');b['phase29_method']='G18';self.assertEqual(a,b)
        config.verify()

    def test_json_serialization(self):
        x=object.__new__(PathExecution);x.path_log=io.StringIO()
        for event in ('SUBMIT','RESULT','COMMAND','WORKER_READY'):
            x.path_record(event,applied=np.bool_(True),sample=np.int64(4),path=np.ones((8,2)),cost=np.float64(.1))
        for line in x.path_log.getvalue().splitlines():json.dumps(json.loads(line))

    def test_normal_worker_process_target_and_json(self):
        from nomad_phase29.test_phase29 import field,job
        with tempfile.TemporaryDirectory() as d:
            worker=NormalWorker(Path(d))
            try:
                result=worker.submit(job(),field()).result(timeout=10);json.dumps(result)
                self.assertEqual(result['solver']['clearance_preference_target_m'],.08)
                self.assertEqual(worker.info['affinity']['actual'],[7])
            finally:worker.close()

    def test_spawn_pool_child_has_r3_patch_and_original_r2(self):
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor
        from .pool import initialize
        ctx=mp.get_context('spawn');q=ctx.Queue()
        try:
            with ProcessPoolExecutor(max_workers=1,mp_context=ctx,initializer=initialize,initargs=(q,)) as pool:
                future=pool.submit(child_probe);self.assertGreater(q.get(timeout=30),0);r=future.result(timeout=30)
            np.testing.assert_allclose(r['clearance'],.2);self.assertTrue(r['r2_original']);self.assertIn(.08,r['constants'])
        finally:q.close();q.join_thread()

    def test_include_rule_and_missing_evidence(self):
        old=[dict(scene=s,index=i,method='G18',technical_validation='PASS',success=True,collision=False,goal_time_s=20.) for s in config.SCENES for i in (201,202)]
        new=[dict(r,method='G18-R',goal_time_s=19.) for r in old]
        self.assertEqual(report.decide(new,old)[0]['label'],'INCLUDE_TONIGHT')
        for r in new:r['goal_time_s']=20.
        self.assertEqual(report.decide(new,old)[0]['label'],'EXCLUDE')
        new[0].update(technical_validation='FAIL',collision=None)
        self.assertEqual(report.decide(new,old)[0]['label'],'EXCLUDE')

    def test_launcher_argument_validation_no_simulator(self):
        class Validated(Exception):pass
        for scene in config.SCENES:
            for index in (201,202):
                with ExitStack() as stack:
                    b=launch.base.base
                    for k in ('subprocess','verify','METHODS','SCENES','write_json'):stack.enter_context(patch.object(b,k,getattr(b,k)))
                    stack.enter_context(patch.dict(launch._main.__globals__,plan=lambda:dict(possible=True,worker_cpu=7,driver_cpus=[0]),pin=lambda cpus:dict(passed=True)))
                    stack.enter_context(patch.object(launch.base.os,'sched_setaffinity'))
                    popen=stack.enter_context(patch.object(launch.subprocess,'Popen'))
                    edge=stack.enter_context(patch.object(b,'socket_path_for_run',side_effect=Validated))
                    path=config.RUN_ROOT/'main'/f'{scene}_{index}_G18-R'/'attempt1'
                    stack.enter_context(patch('sys.argv',['launch','--scene',scene,'--method','G18-R','--index',str(index),'--output',str(path)]))
                    with self.assertRaises(Validated):launch.main()
                    edge.assert_called_once();popen.assert_not_called();self.assertFalse(path.exists())

    def test_no_scipy_before_kit_and_routing(self):
        source=(config.ROOT/'research/nomad_phase26/simulator.py').read_text().replace('from nomad_phase26.execution','from nomad_phase30r.runtime').replace('from nomad_phase26.config','from nomad_phase30r.config')
        self.assertLess(source.index('# SimulationApp is now initialized.'),source.index('from nomad_phase30r.runtime'))
        compile(source,'<test-kit-order>','exec')
        self.assertEqual(campaign.Routes.route(['nomad_phase26.launch','nomad_phase26.report']),['nomad_phase30r.launch','nomad_phase30r.report'])
        p=config.verify()
        with patch.object(campaign.base,'protocol',return_value=p):jobs=campaign.base.jobs(config.RUN_ROOT)
        self.assertEqual(len(jobs),10);self.assertTrue(all(len(j['outputs'])==2 for j in jobs))

    def test_report_with_fake_completed_metrics(self):
        old=report.baseline();self.assertEqual(len(old),10)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'run';(run/'metrics').mkdir(parents=True);(root/'docs').mkdir()
            for r in old:
                n=copy.deepcopy(r);n['method']='G18-R'
                if n['success']:n['goal_time_s']-=.5
                n.update(report.detour_metrics(n['output']))
                (run/'metrics'/f"{n['scene']}_{n['index']}.json").write_text(json.dumps(n))
            with patch.object(report,'ROOT',root),patch.object(report,'OUT',root/'results'),patch.object(report,'baseline',return_value=copy.deepcopy(old)):
                doc=report.generate(run)
            result=json.loads((root/'results/decision.json').read_text())
            self.assertEqual(result['label'],'INCLUDE_TONIGHT');self.assertAlmostEqual(result['goal_time_difference_median_s'],-.5)
            self.assertIn('detour_path_length_m',doc.read_text());self.assertTrue((root/'results/paired.csv').exists())

if __name__=='__main__':unittest.main()
