import copy,io,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import Future
from unittest.mock import patch
import numpy as np
from . import graph,graph_r1
from .handoff import HExecution
from .runtime import NAExecution
from .online_r1 import R1Execution,_new_path,_collect_h,solve_job
from .report import case_statistics
from .config import ROOT,HERE

def empty():
    x=object.__new__(R1Execution);x.init_telemetry();x.h_log=io.StringIO();x.r1_cases[0]=dict(id=7,commands=0,clips=0)
    x.r1_current=0;x.r1_now_s=1.;return x

class OnlineRevisionTests(unittest.TestCase):
    def test_only_solver_and_follower_binding(self):
        self.assertIs(_new_path.__code__,HExecution.new_path.__code__);self.assertIs(_new_path.__globals__['solve'],solve_job)
        self.assertIs(_collect_h.__code__,HExecution.collect_h.__code__);self.assertIs(_collect_h.__globals__['TimedFollower'],graph_r1.R1Follower)
        self.assertIs(HExecution.new_path.__globals__['solve'],graph.solve)
        self.assertIs(R1Execution._normal_apply,NAExecution._normal_apply)
        self.assertIs(R1Execution.start_detour,NAExecution.start_detour)
    def test_worker_passes_exact_arguments_to_frozen_solver(self):
        args=([0,0,0],[.1,0],[[0,0],[1,0]],object(),2.,None,12.)
        with patch.object(graph_r1,'solve',return_value={'output_type':'INIT_ONLY'}) as fn:
            self.assertEqual(solve_job(*args),{'output_type':'INIT_ONLY'});fn.assert_called_once_with(*args)
    def test_numpy_clip_flags_serialize_and_case_denominator(self):
        x=empty();x.hrecord('DISPATCH',job_id=2,dispatch_wall_s=0.)
        r=dict(output_type='OPTIMIZED',disposition='OPTIMIZED',wall_s=.03)
        x.hrecord('APPLIED',job_id=2,result=r);x.hrecord('COMMAND',diag={'any_clipped':np.bool_(True)},command=np.array([.1,.2]))
        f=Future();f.set_result(r);x.r1_futures[2]=f;x.finalize_telemetry()
        rows=[json.loads(line) for line in x.h_log.getvalue().splitlines()];m=case_statistics(rows)
        self.assertEqual(m['handoff_case_count'],1);self.assertEqual(m['handoff_case_types']['OPTIMIZED'],1);self.assertEqual(m['handoff_feedback_clip_fraction'],1.)
    def test_init_reason_and_application_rejection_are_distinct(self):
        x=empty();x.hrecord('DISPATCH',job_id=2,dispatch_wall_s=0.)
        r=dict(output_type='INIT_ONLY',disposition='INIT_ONLY',optimized_failure='SOLVER_FAILURE',wall_s=.05)
        x.hrecord('FALLBACK',job_id=2,id=7,reason='APPLICATION_CERTIFICATE_FAILURE',result={'result':r,'certificate':{'passed':False}})
        rows=[json.loads(s) for s in x.h_log.getvalue().splitlines()];out=next(r for r in rows if r['event']=='CASE_OUTCOME')
        self.assertEqual(out['output_type'],'FALLBACK');self.assertEqual(out['solver_output_type'],'INIT_ONLY');self.assertTrue(out['explicit_na_fallback'])
        self.assertFalse(out['feedback_clip_any'])
    def test_discard_does_not_claim_na_installation(self):
        x=empty();x.hrecord('DISPATCH',job_id=2,dispatch_wall_s=0.);x.hrecord('DISCARDED',job_id=2,reason='SUPERSEDED')
        r=next(json.loads(s) for s in x.h_log.getvalue().splitlines() if json.loads(s)['event']=='CASE_OUTCOME')
        self.assertEqual(r['output_type'],'FALLBACK');self.assertFalse(r['explicit_na_fallback']);self.assertIsNone(r['compute_wall_s'])
    def test_worker_busy_is_one_noncomputed_case(self):
        x=empty();x.hrecord('FALLBACK',id=7,reason='WORKER_BUSY');x.finalize_telemetry()
        m=case_statistics([json.loads(s) for s in x.h_log.getvalue().splitlines()])
        self.assertEqual(m['handoff_case_count'],1);self.assertEqual(m['handoff_all_case_compute_p50_s'],0.)
    def test_report_event_fractions_are_case_weighted(self):
        rows=[dict(event='CASE_OUTCOME',case_id=i,output_type='OPTIMIZED' if i==0 else 'INIT_ONLY' if i==1 else 'FALLBACK',reason='x',compute_wall_s=.1) for i in range(5)]
        m=case_statistics(rows);self.assertEqual(m['handoff_case_fractions'],dict(OPTIMIZED=.2,INIT_ONLY=.2,FALLBACK=.6))
    def test_actual_simulator_entry_routes_to_r1_after_kit(self):
        wrapper=(HERE/'simulator.py').read_text();self.assertIn('from nomad_phase28.online_r1 import install,run_without_oracle',wrapper)
        source=(ROOT/'research/nomad_phase26/simulator.py').read_text().replace('from nomad_phase26.execution import install,run_without_oracle','from nomad_phase28.online_r1 import install,run_without_oracle')
        self.assertLess(source.index('# SimulationApp is now initialized.'),source.index('from nomad_phase28.online_r1'))
        compile(source,'r1-simulator-entry','exec')
    def test_prediction_continues_an_active_r1_follower(self):
        from .tracking import predict
        from nomad_isaac.common import integrate_se2
        r=dict(poses=[[0,0,0],[.1,0,.1],[.2,.02,.1]],dt=[1.,1.],speed=[.1,.1],omega=[.1,0.],initial_vw=[.1,.1],allow_rotation=False)
        ctl=graph_r1.R1Follower(r,0.,2.);before=copy.deepcopy(ctl);pose=np.array([.02,0.,.02]);vw=[.1,.1]
        predicted=predict(pose,vw,ctl,16)
        reference=copy.deepcopy(ctl);q=pose.copy();v,w=vw
        for tick in range(16,32):
            if tick%8==0:reference.now_s=tick/72;reference.previous_w=w;(v,w),_=reference.control(q,v)
            q=integrate_se2(q,v,w,1/72)
        np.testing.assert_allclose(predicted['pose'],q,atol=1e-12,rtol=0)
        np.testing.assert_allclose(predicted['vw'],[v,w],atol=1e-12,rtol=0)
        self.assertEqual(ctl.now_s,before.now_s);np.testing.assert_array_equal(ctl.mid,before.mid)
    def test_report_includes_case_types_and_paired_continuous_metrics(self):
        from . import report
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);baseline=root/'research/results/phase27r';baseline.mkdir(parents=True);(root/'docs').mkdir();run=root/'run';(run/'metrics').mkdir(parents=True);out=root/'out';out.mkdir()
            old=[r for r in json.loads((ROOT/'research/results/phase27r/runs.json').read_text()) if r['method']=='C0']
            (baseline/'runs.json').write_text(json.dumps(old));(baseline/'time_budget_runs.csv').write_bytes((ROOT/'research/results/phase27r/time_budget_runs.csv').read_bytes())
            for r in old:
                for method in ('C0-NA','C0-H'):
                    q=dict(r,method=method,mean_speed_m_s=.2,alignment_rotation_fraction=.1,alignment_brake_fraction=.03,
                        handoff_case_count=10 if method=='C0-H' else 0,handoff_case_types={'OPTIMIZED':5,'INIT_ONLY':3,'FALLBACK':2} if method=='C0-H' else {})
                    (run/'metrics'/f"{r['scene']}_{r['index']}_{method}.json").write_text(json.dumps(q))
            with patch.object(report,'ROOT',root),patch.object(report,'OUT',out):doc=report.generate(run)
            self.assertIn('GATE_FAIL',doc.read_text());self.assertIn('OPTIMIZED_fraction',(out/'summary.csv').read_text());self.assertIn('goal_time_s_difference',(out/'paired.csv').read_text());self.assertIn('collision_difference',(out/'paired.csv').read_text())

if __name__=='__main__':unittest.main()
