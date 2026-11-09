import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from . import config,campaign,launch,report
from .metrics import detour_windows


class Tests(unittest.TestCase):
    def test_frozen_ours_factory_and_fifteen_arguments_no_execution(self):
        from nomad_phase38.config import runtime_config as old
        from nomad_phase38 import runtime
        from nomad_phase20d import pool
        self.assertEqual(pool.solve_sample.__module__,'nomad_phase20.repair')
        self.assertEqual(pool.solve_initialization.__module__,'nomad_phase20c.detour_known')
        class Boundary(Exception):pass
        jobs=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(jobs),15)
        for j in jobs:
            c=config.runtime_config(j['method'],j['index'],90,j['scene']);original=old('OURS',j['index'],90,j['scene'])
            skip={'phase41','nomad_goal_stop','phase43p','phase43p_method','phase45p','phase45p_method'}
            self.assertEqual({k:v for k,v in c.items() if k not in skip},original)
            self.assertTrue(c['nomad_goal_stop']);self.assertEqual(c['phase38_method'],'OURS')
            self.assertNotIn('phase40p',c);self.assertNotIn('phase44p',c)
            with patch.object(runtime.frozen,'make_execution',return_value='FROZEN_OURS') as factory:
                self.assertEqual(runtime.make_execution(c,Path('/tmp')),'FROZEN_OURS');factory.assert_called_once_with(c,Path('/tmp'))
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No process')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            argv=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            with patch.object(sys,'argv',argv),self.assertRaises(Boundary):fn()
        process=launch.Processes()
        with patch('subprocess.Popen',return_value=object()) as popen:
            process.Popen(['python','-m','nomad_isaac.worker'])
            self.assertEqual(popen.call_args.args[0][2],'nomad_phase43p.worker')
        code='''
from nomad_phase45p import campaign as c
from nomad_phase45p.config import RUN_ROOT
def halt():
 assert len(c.frozen.base.jobs(RUN_ROOT))==15
 assert c.frozen.base.protocol()['smoke']['enabled'] is False
 assert c.frozen.base.run_job.__globals__['subprocess'].__class__ is c.Routes
 print('NO_EXECUTION')
c.frozen.base.main=halt
c.main()
assert not RUN_ROOT.exists()
'''
        r=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr[-1800:]);self.assertIn('NO_EXECUTION',r.stdout)

    def test_actual_detours_only_clipping_and_no_double_count(self):
        events=[dict(event='END',job_id=99,simulation_time_s=1.,reason='REJECT'),
            dict(event='APPLIED',job_id=1,simulation_time_s=2.),dict(event='END',job_id=1,simulation_time_s=5.,reason='ENDPOINT'),
            dict(event='APPLIED',job_id=2,simulation_time_s=6.),dict(event='END',job_id=2,simulation_time_s=9.,reason='SIX_SECOND_LIMIT'),
            dict(event='APPLIED',job_id=3,simulation_time_s=18.)]
        errors=[dict(inference_id=i,observation_s=t,abs_error=i+1) for i,t in enumerate((6.,10.,15.,20.))]
        r=detour_windows(events,errors,20.)
        self.assertEqual(r['active_at_termination'],1);self.assertEqual(len(r['windows']),5)
        self.assertEqual(r['handover_10s']['n'],3);self.assertEqual(r['handover_10s']['mae'],2.)
        self.assertEqual(r['install_10s']['n'],4)
        self.assertTrue(r['windows'][-1]['truncated']);self.assertEqual(r['windows'][-1]['available_s'],2.)
        none=detour_windows([],errors,20.);self.assertEqual(none['handover_10s']['n'],0);self.assertIsNone(none['handover_10s']['mae'])
        json.dumps(r,allow_nan=False)

    def test_fifteen_paired_tables_with_baseline_post_detour_na(self):
        baseline=json.loads((config.OUT/'preparation/baselines.json').read_text())
        self.assertEqual(len(baseline),15);self.assertTrue(all(x['r3_installations']==0 for x in baseline))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,j in enumerate(config.protocol()['main_order']):
                row=dict(j,technical_validation='PASS',success=True,wrong_stop=False,collision=False,
                         r2_installations=1,r3_installations=2,post_detour=detour_windows([],[],30.))
                (root/'metrics'/f'{i}.json').write_text(json.dumps(row))
            doc=report.generate(root,root/'results',root/'report.md',baseline)
            self.assertTrue(all(not line or line.startswith('|') for line in doc.read_text().splitlines()))
            self.assertEqual(json.loads((root/'results/analysis.json').read_text())['paired_valid'],15)
            self.assertIn('HANDOVER_10S',doc.read_text())


if __name__=='__main__':unittest.main()
