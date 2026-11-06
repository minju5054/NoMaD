import ast,copy,inspect,json,os,tempfile,textwrap,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase28 import graph_r1
from nomad_phase28.alignment import NoAlignment
from nomad_phase28.test_handoff import Field
from nomad_phase28.handoff import HExecution
from . import timing
from .affinity import choose,pin,plan
from .client import ProcessWorker
from .report import smoke_gate,stage_values,application_counts

class TimingTests(unittest.TestCase):
    def test_three_budget_constants_only(self):
        original=ast.parse(textwrap.dedent(inspect.getsource(graph_r1.solve)));new=copy.deepcopy(original);replace=timing.BudgetOnly(.30);new=replace.visit(new)
        self.assertEqual(replace.count,3)
        class Undo(ast.NodeTransformer):
            def visit_Constant(self,node):
                if isinstance(node.value,float) and node.value==.30:return ast.copy_location(ast.Constant(.15),node)
                return node
        self.assertEqual(ast.dump(original),ast.dump(Undo().visit(new)))
    def test_factors_and_constraint_methods_unchanged(self):
        self.assertIs(timing.InstrumentedGraph.objective,graph_r1.R1Graph.objective)
        self.assertIs(timing.InstrumentedGraph.constraints,graph_r1.R1Graph.constraints)
        args=([0,0,0],[.3,0],[[0,0],[1.2,0]],Field(),2.)
        timing.LOCAL.record=dict(stages=[],iterations=[])
        try:
            a=graph_r1.R1Graph(*args);b=timing.InstrumentedGraph(*args);x=a.initial();np.testing.assert_array_equal(x,b.initial());self.assertEqual(a.objective(x)[0],b.objective(x)[0])
        finally:timing.LOCAL.record=None
    def test_apply_tick_three_and_same_integrator(self):
        c=NoAlignment();c.replace_path([[0,0],[1,0]],[0,0,0],.1);r=timing.predict([0,0,0],[.1,0],c,0)
        self.assertEqual(r['apply_tick'],24);self.assertAlmostEqual(r['delay_s'],1/3)
        q=np.zeros(3);v=.1
        for tick in range(24):
            if tick%8==0:(v,w),_=c.control(q,v)
            q=integrate_se2(q,v,w,1/72)
        np.testing.assert_array_equal(q,r['pose']);self.assertEqual(timing.apply_tick(8),32)
        with self.assertRaises(AssertionError):timing.apply_tick(1)
    def test_timeout_captures_completed_major_iterations(self):
        def timed_out(fun,x,**kw):kw['callback'](x);kw['callback'](x);raise TimeoutError('test deadline')
        with patch.object(timing,'scipy_minimize',side_effect=timed_out):r=timing.solve([0,0,0],[.3,0],[[0,0],[1.2,0]],Field(),2.)
        self.assertEqual(r['disposition'],'TIMEOUT');self.assertEqual(r['timing']['iterations_at_timeout'],2)
        self.assertEqual(len(r['timing']['iterations']),2);self.assertTrue(r['timing']['solver_started'])
    def test_expired_before_solver_is_distinct(self):
        r=timing.solve([0,0,0],[.3,0],[[0,0],[1.2,0]],Field(),2.,started=time.perf_counter()-1)
        self.assertFalse(r['timing']['solver_started']);self.assertEqual(r['timing']['iterations_at_timeout'],0);self.assertFalse(r['accepted'])
    def test_observer_preserves_numeric_output(self):
        plain,_=timing.clone_solver(.30,False);args=([0,0,0],[.3,0],[[0,0],[1.2,0]],Field(),2.)
        a=plain(*args);b=timing.solve(*args);self.assertEqual(a['output_type'],b['output_type']);self.assertTrue(a['accepted'])
        np.testing.assert_allclose(a['poses'],b['poses'],atol=1e-9,rtol=0);np.testing.assert_allclose(a['dt'],b['dt'],atol=1e-9,rtol=0)
    def test_physical_core_siblings_excluded(self):
        r=choose([0,1,2,3],{0:(0,0),2:(0,0),1:(0,1),3:(0,1)})
        self.assertEqual(r['worker_cpu'],1);self.assertEqual(r['driver_cpus'],[0,2]);self.assertEqual(r['reserved_siblings'],[1,3])
        self.assertFalse(choose([0,2],{0:(0,0),2:(0,0)})['possible'])
    def test_affinity_failure_reported(self):
        with patch('os.sched_setaffinity',side_effect=OSError('denied')):r=pin([0])
        self.assertFalse(r['passed']);self.assertIn('denied',r['reason'])
    def test_live_binding_keeps_apply_and_decision_body(self):
        from .runtime import TimingExecution,NEW_PATH,COLLECT
        from nomad_phase28.runtime import NAExecution
        self.assertIs(NEW_PATH.__code__,HExecution.new_path.__code__);self.assertIs(COLLECT.__code__,HExecution.collect_h.__code__)
        self.assertIs(TimingExecution._normal_apply,NAExecution._normal_apply)
        self.assertIs(TimingExecution.start_detour,NAExecution.start_detour)
    def test_stage_extraction_and_registered_gate(self):
        t=dict(submit_ns=10,transport_thread_start_ns=30,sdf_copy_start_ns=30,sdf_copy_end_ns=50)
        self.assertEqual(stage_values(dict(timing=t,wall_s=.1))['transport_thread_queue'],20e-9)
        self.assertEqual(smoke_gate(10,5,4,[.2]*10)['label'],'GATE_FAIL')
        self.assertEqual(smoke_gate(10,7,7,[.30]*10)['label'],'GATE_PASS')
        self.assertEqual(smoke_gate(10,5,5,[.2]*10,3)['denominator_n'],7)
        self.assertEqual(smoke_gate(10,5,5,[.2]*10,3)['label'],'GATE_PASS')
        self.assertEqual(smoke_gate(0,0,0,[])['label'],'GATE_FAIL')
        self.assertEqual(smoke_gate(3,0,0,[.2]*3,3)['label'],'GATE_FAIL')
    def test_only_detour_started_is_removed(self):
        cases=[dict(output_type='OPTIMIZED',applied=True,reason='OPTIMIZED') for _ in range(7)]
        cases += [dict(output_type='FALLBACK',applied=False,reason=r) for r in ['DETOUR_STARTED','DETOUR_STARTED','SUPERSEDED','WORKER_BUSY','TIMEOUT']]
        c=application_counts(cases)
        self.assertEqual(c,dict(total=12,detour_started_excluded=2,eligible=10,applied=7))
        gate=smoke_gate(c['total'],7,c['applied'],[.2]*11,c['detour_started_excluded'])
        self.assertEqual(gate['application_fraction'],.7);self.assertEqual(gate['label'],'GATE_PASS')
    def test_detour_compute_time_stays_in_p95(self):
        # Three excluded decisions still contribute their measured job times.
        gate=smoke_gate(10,7,7,[.2]*7+[.6]*3,3)
        self.assertEqual(gate['application_fraction'],1.);self.assertEqual(gate['compute_samples'],10)
        self.assertEqual(gate['compute_p95_s'],.6);self.assertEqual(gate['label'],'GATE_FAIL')
    def test_process_worker_transport_versions_and_affinity(self):
        with tempfile.TemporaryDirectory() as d:
            cpu=plan().get('worker_cpu');w=ProcessWorker(Path(d),cpu)
            try:
                field=Field();before=field.values.copy();r=w.submit(timing.solve,[0,0,0],[.3,0],[[0,0],[1.2,0]],field,2.,None,time.perf_counter()).result(timeout=5)
                self.assertNotEqual(w.info['pid'],os.getpid());self.assertTrue(r['accepted'],r.get('disposition'))
                if cpu is not None:self.assertEqual(w.info['affinity']['actual'],[cpu])
                self.assertIn('na_initial_72hz',[s['name'] for s in r['timing']['stages']]);self.assertIn('parent_receive_ns',r['timing'])
                again=w.submit(timing.solve,[0,0,0],[.3,0],[[0,0],[1.2,0]],field,2.,None,time.perf_counter()).result(timeout=5)
                self.assertEqual((r['request_id'],again['request_id']),(0,1))
                np.testing.assert_array_equal(field.values,before)
            finally:w.shutdown()
            self.assertEqual(w.process.returncode,0);self.assertFalse(Path(w.socket).exists())
    def test_dead_worker_never_retries_or_returns_stale_result(self):
        w=object.__new__(ProcessWorker);w.failed='broken socket'
        r=w.submit(None,None,None,None,None,None,None,time.perf_counter()).result()
        self.assertFalse(r['accepted']);self.assertEqual(r['disposition'],'WORKER_UNAVAILABLE')
    def test_fake_smoke_report_has_all_required_metrics(self):
        from . import report
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/'run';run.mkdir();(root/'docs').mkdir();(run/'launch_complete.json').write_text('{}')
            events=[]
            for i in range(10):
                typ='OPTIMIZED' if i<6 else 'INIT_ONLY' if i<8 else 'FALLBACK'
                reason='DETOUR_STARTED' if i==8 else 'SUPERSEDED' if i==9 else typ
                events.append(dict(event='CASE_SUMMARY',case_id=i,job_id=i,output_type=typ,reason=reason,applied=i<8,feedback_commands=2 if i<8 else 0,feedback_clipped_commands=1 if i<8 else 0))
                events.append(dict(event='TIMING_RESULT',job_id=i,result=dict(output_type=typ,wall_s=.2,timing=dict(completed_major_iterations=3,iterations=[],stages=[]))))
            (run/'phase28_handoff.jsonl').write_text('\n'.join(json.dumps(e) for e in events)+'\n')
            with patch.object(report,'ROOT',root),patch.object(report,'OUT',root/'out'),patch.object(report,'protocol',return_value={'gate':{'denominator':'ALL_H_CASES_EXCEPT_DETOUR_STARTED','excluded_reasons':['DETOUR_STARTED']}}),patch.object(report,'frozen_audit',return_value={'technical_validation':'PASS'}):r=report.smoke(run)
            self.assertEqual(r['gate']['label'],'GATE_PASS');self.assertEqual(r['actually_applied'],8);self.assertEqual(r['feedback_clip_fraction'],.5)
            self.assertEqual(r['detour_started_excluded'],1);self.assertEqual(r['gate_eligible_cases'],9)
            self.assertEqual(r['case_reasons']['SUPERSEDED'],1);self.assertAlmostEqual(r['gate']['application_fraction'],8/9)
            self.assertTrue((root/'docs/PHASE28T_SMOKE.md').exists());self.assertTrue((root/'out/smoke/stages.csv').exists())
            self.assertTrue((root/'out/smoke/gate_cases.csv').exists())

if __name__=='__main__':unittest.main()
