import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
from .config import runtime_config,METHODS,SCENES,ROOT
from nomad_phase26.config import runtime_config as original

class PipelineTests(unittest.TestCase):
    def test_frozen_runtime_configs(self):
        for scene in SCENES:
            for method in METHODS:
                c=runtime_config(method,201,level=scene);old=original('C0',201,level=scene)
                self.assertEqual({k:v for k,v in c.items() if k in old},old)
                self.assertEqual(c['phase28_alpha'],2.)
    def test_simulator_adapter_only_routes_two_imports(self):
        source=(ROOT/'research/nomad_phase26/simulator.py').read_text()
        for old,new in [('from nomad_phase26.config import runtime_config','from nomad_phase28.config import runtime_config'),('from nomad_phase26.execution import install,run_without_oracle','from nomad_phase28.handoff import install,run_without_oracle')]:
            self.assertEqual(source.count(old),1);source=source.replace(old,new)
        compile(source,'simulator-adapter','exec')  # Never execute or import Kit.
        self.assertLess(source.index('# SimulationApp is now initialized.'),source.index('from nomad_phase28.handoff'))
    def test_campaign_process_routes(self):
        from .campaign import Routes
        self.assertEqual(Routes.route(['python','-m','nomad_phase26.launch','--method','C0-H']),['python','-m','nomad_phase28.launch','--method','C0-H'])
    def test_runtime_timeout_and_solver_failure_fallback(self):
        from .handoff import HExecution
        for done,r,expected in [(False,None,'TIMEOUT'),(True,dict(accepted=False,disposition='SOLVER_FAILURE'),'SOLVER_FAILURE')]:
            o=object.__new__(HExecution);o.pending_h=dict(job_id=1,prediction={'apply_tick':16});o.detour=None;o.recovery=SimpleNamespace(state='NORMAL')
            o.h_future=Mock();o.h_future.done.return_value=done;o.h_future.result.return_value=r;o.fallback_h=Mock()
            o.collect_h(SimpleNamespace(),dict(simulation_time_s=16/72),None)
            self.assertEqual(o.fallback_h.call_args.args[3],expected)
    def test_twenty_run_report_template(self):
        from . import report
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'research/results/phase27r';base.mkdir(parents=True);(root/'docs').mkdir();run=root/'run';(run/'metrics').mkdir(parents=True);out=root/'out';out.mkdir()
            source=json.loads((ROOT/'research/results/phase27r/runs.json').read_text());old=[r for r in source if r['method']=='C0'];(base/'runs.json').write_text(json.dumps(old));(base/'time_budget_runs.csv').write_bytes((ROOT/'research/results/phase27r/time_budget_runs.csv').read_bytes())
            for b in old:
                for method in METHODS:
                    r=dict(b,method=method,mean_speed_m_s=.2,alignment_rotation_fraction=.1,alignment_brake_fraction=.02)
                    (run/'metrics'/f"{b['scene']}_{b['index']}_{method}.json").write_text(json.dumps(r))
            with patch.object(report,'ROOT',root),patch.object(report,'OUT',out):doc=report.generate(run)
            self.assertTrue(doc.exists());self.assertEqual(len(json.loads((out/'runs.json').read_text())),30)
            self.assertEqual(len((out/'paired.csv').read_text().splitlines()),21)

if __name__=='__main__':unittest.main()
