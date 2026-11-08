import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import config,campaign,launch,report
from .scenes import registered_jitter,gap_check,straight_place,multi_place

class PreparationTests(unittest.TestCase):
    def test_all_180_blocks_nights_and_short_sockets(self):
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        blocks,order=config.registered_order();self.assertEqual(len(blocks),20);self.assertEqual(len(order),180)
        self.assertEqual(order,config.protocol()['main_order'])
        for b in blocks:self.assertEqual(set(b['methods']),set(config.METHODS))
        for n in (1,2):self.assertEqual(len(campaign.jobs(config.RUN_ROOT/f'night{n}',n)),90)
        jobs=campaign.jobs(config.RUN_ROOT);sockets=[socket_path_for_run(Path(p)) for j in jobs for p in j['outputs']]
        self.assertEqual(len(set(sockets)),360);self.assertTrue(all(validate_socket_path(s)<100 for s in sockets))
    def test_launcher_validation_stops_before_mkdir_or_process(self):
        class Stop(Exception):pass
        for smoke in (False,True):
            jobs=campaign.jobs(config.SMOKE_ROOT if smoke else config.RUN_ROOT,smoke=smoke)
            for job in jobs:
                fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No process allowed')))
                fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Stop())
                argv=['launch','--scene',job['scene'],'--method',job['method'],'--index',str(job['index']),'--output',job['outputs'][0]]+(['--smoke'] if smoke else [])
                with patch.object(sys,'argv',argv),self.assertRaises(Stop):fn()
        self.assertFalse(config.RUN_ROOT.exists());self.assertFalse(config.SMOKE_ROOT.exists())
    def test_original_five_configs_and_factories_unchanged(self):
        from nomad_phase35.config import runtime_config as old
        from . import runtime
        baseline=('NOMAD_RAW','TE','RTC','ASTAR+EC','OURS')
        allowed={'seed_offset','run_id','phase35_index','phase29_index','phase32_index','phase38','phase38_index','phase38_method','phase38_jitter','phase38_care','phase38_ec'}
        for m in baseline:
            for scene in config.SCENES:
                a=config.runtime_config(m,217,90,scene);b=old(config.ALIASES[m],212,90,scene)
                self.assertEqual({k:v for k,v in a.items() if k not in allowed},{k:v for k,v in b.items() if k not in allowed})
                with patch.object(runtime.frozen,'make_execution',return_value='EXACT_FROZEN') as factory:
                    self.assertEqual(runtime.make_execution(a,Path('/tmp')),'EXACT_FROZEN');factory.assert_called_once_with(a,Path('/tmp'))
        self.assertEqual(config.runtime_config('CARE',217)['overnight_method'],'CURV')
        self.assertEqual(config.runtime_config('RTC+EC',217)['overnight_method'],'RTC-hard')
    def test_seed_placements_shared_gap_and_rejection(self):
        p=config.protocol()
        for scene in config.SCENES:
            for index in (*config.INDICES,95):
                j=registered_jitter(scene,index);self.assertEqual(j,p['placements'][f'{scene}_{index}'])
                for x in j:self.assertLessEqual(abs(x['offset_m']),.2);self.assertTrue(x['geometry']['passed'])
                for m in config.METHODS:self.assertEqual(config.runtime_config(m,index,90,scene)['phase38_jitter'],j)
        c=config.runtime_config('OURS',217,90,'H1');pose=[3.3,1.25,np.pi/2]
        c['phase38_jitter']=[dict(offset_m=.2)];result=multi_place(c,pose,0)
        self.assertFalse(gap_check(c,result['obstacle'],1)['passed'])
    def test_fake_cumulative_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);nights=[root/'night1',root/'night2']
            for n in nights:(n/'metrics').mkdir(parents=True)
            for i,job in enumerate(config.registered_order()[1]):
                row=dict(job,technical_validation='PASS',success=True,collision=False,goal_time_s=40.)
                (nights[job['night']-1]/'metrics'/f'{i}.json').write_text(json.dumps(row))
            doc=report.generate(root/'results',root/'report.md',nights)
            result=json.loads((root/'results/analysis.json').read_text());self.assertEqual(result['completed'],180)
            self.assertEqual(result['stage'],'COMPLETE');self.assertTrue(all(x['label']=='NONINFERIOR' for x in result['noninferiority']))
            self.assertIn('Holm',doc.read_text());self.assertTrue((root/'results/mcnemar.csv').exists())
            report.generate(root/'interim',root/'interim.md',nights[:1])
            interim=json.loads((root/'interim/analysis.json').read_text())
            self.assertEqual((interim['stage'],interim['completed']),('NIGHT1_INTERIM',90))
            self.assertEqual(campaign.Routes.route(['nomad_phase26.report','--publish']),['nomad_phase38.report','--publish'])
    def test_no_simulator_import_in_wrapper_before_bootstrap(self):
        source=(config.ROOT/'research/nomad_phase26/simulator.py').read_text()
        self.assertLess(source.index('exec(compile(ast.Module(body=prefix'),source.index('from nomad_phase26.execution import install'))
    def test_campaign_wiring_reaches_engine_without_executing_it(self):
        code='''
import sys
from nomad_phase38 import campaign as c
from nomad_phase38.config import RUN_ROOT,SMOKE_ROOT
def halt():
 assert c.base.protocol()['status']=='FROZEN'
 assert len(c.base.jobs(SMOKE_ROOT if '--smoke-only' in sys.argv else RUN_ROOT))==(4 if '--smoke-only' in sys.argv else 90)
 assert c.base.run_job.__globals__['subprocess'].__class__ is c.Routes
 print('ENGINE_WIRING_OK_NO_EXECUTION')
c.base.main=halt
c.main()
assert not RUN_ROOT.exists() and not SMOKE_ROOT.exists()
'''
        for flags in (['--night','1'],['--smoke']):
            r=subprocess.run(['/usr/bin/python3','-c',code,*flags],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr[-2000:]);self.assertIn('ENGINE_WIRING_OK_NO_EXECUTION',r.stdout)

if __name__=='__main__':unittest.main()
