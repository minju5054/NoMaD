import copy,io,json,tempfile,unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import numpy as np
from nomad_phase28.tracking import clip_command
from . import analysis,main_config,main_launch,drive_report,campaign
from .config import runtime_config as smoke_config
from .review import baselines
from .report import read

class Validated(Exception):pass

class ReviewTests(unittest.TestCase):
    def test_clip_causes_overlap_without_double_counting_commands(self):
        raw=[.5,.8];before=[0.,0.];command,_=clip_command(raw,before,2.)
        causes,flags=analysis.clip_causes(raw,before,command)
        self.assertTrue(flags['any_clipped']);self.assertEqual(sum(causes.values()),4)
        raw=[-.1,0.];command,_=clip_command(raw,before,2.)
        self.assertTrue(analysis.clip_causes(raw,before,command)[0]['v_lower'])

    def test_planned_pose_interpolation_unwrap(self):
        r=dict(poses=[[0,0,3.1],[1,0,-3.1]],dt=[1.])
        p=analysis.planned_pose(r,.5);np.testing.assert_allclose(p,[.5,0,np.pi])

    def test_smoke_saved_command_and_time_accounting(self):
        with tempfile.TemporaryDirectory() as d:
            root=main_config.ROOT.parent/'artifacts/isaac6/phase28t_smoke_02'
            r,b,c,_=analysis.analyze(root,Path(d))
            self.assertEqual(r['clip_count'],133);self.assertEqual(r['h_commands'],257)
            self.assertAlmostEqual(sum(x['seconds'] for x in b),42.25)
            self.assertAlmostEqual(r['stop_fraction'],.2156476002629847)
            self.assertEqual([x['count'] for x in c],[17,5,56,62,33])

    def test_main_configuration_only_changes_smoke_flag(self):
        old=smoke_config('C0-H',201,90,'H1');new=main_config.runtime_config('C0-H',201,90,'H1')
        old['phase28t_smoke_excluded']=False;self.assertEqual(old,new)
        for scene in main_config.SCENES:
            for index in (201,202):
                c=main_config.runtime_config('C0-H',index,90,scene)
                self.assertEqual(c['phase28t_apply_ticks'],24);self.assertEqual(c['phase28t_budget_s'],.3)
        with self.assertRaises(AssertionError):main_config.runtime_config('C0-NA',201)

    def test_all_main_launcher_arguments_without_processes(self):
        for scene in main_config.SCENES:
            for index in (201,202):
                with ExitStack() as stack:
                    base=main_launch.base
                    for name in ('verify','subprocess','METHODS','SCENES','write_json'):
                        stack.enter_context(patch.object(base,name,getattr(base,name)))
                    stack.enter_context(patch.object(main_launch,'plan',return_value=dict(possible=False,reason='TEST')))
                    stack.enter_context(patch.object(main_launch.os,'sched_setaffinity'))
                    spawn=stack.enter_context(patch.object(main_launch.subprocess,'Popen'))
                    edge=stack.enter_context(patch.object(base,'socket_path_for_run',side_effect=Validated))
                    out=main_config.RUN_ROOT/'main'/f'{scene}_{index}_C0-H'/'attempt1'
                    stack.enter_context(patch('sys.argv',['launch','--scene',scene,'--method','C0-H','--index',str(index),'--output',str(out)]))
                    with self.assertRaises(Validated):main_launch.main()
                    edge.assert_called_once();spawn.assert_not_called();self.assertFalse(out.exists())

    def test_plan_has_ten_jobs_and_no_smoke(self):
        p=main_config.verify()
        with patch.object(campaign.base,'protocol',return_value=p):jobs=campaign.base.jobs(main_config.RUN_ROOT)
        self.assertEqual(len(jobs),10);self.assertEqual({j['method'] for j in jobs},{'C0-H'})
        self.assertTrue(all(len(j['outputs'])==2 for j in jobs))
        self.assertIn('main_launch',campaign.Routes.route(['nomad_phase26.launch'])[0])
        self.assertIn('drive_report',campaign.Routes.route(['nomad_phase26.report'])[0])

    def test_drive_report_pairs_and_technical_exclusions(self):
        baseline=baselines();p=main_config.protocol()
        for failure in (False,True):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);run=root/'run';out=root/'result';(run/'metrics').mkdir(parents=True);(root/'docs').mkdir()
                new=[]
                for i,job in enumerate(p['main_order']):
                    r=copy.deepcopy(next(r for r in baseline if (r['scene'],r['index'],r['method'])==(job['scene'],job['index'],'C0-NA')))
                    r.update(method='C0-H',output=str(run/'main'/str(i)))
                    if failure and i==0:r.update(technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)
                    new.append(r);(run/'metrics'/f'{i}.json').write_text(json.dumps(r))
                def details(rows,_):
                    return [dict(scene=r['scene'],index=r['index'],method=r['method'],mean_speed_m_s=.2,alignment_rotation_s=1.,duration_s=30.) for r in rows if r['technical_validation']=='PASS'],[]
                with patch.object(drive_report,'ROOT',root),patch.object(drive_report,'OUT',out),patch.object(drive_report,'RUN_ROOT',run),patch.object(drive_report,'baselines',return_value=copy.deepcopy(baseline)),patch.object(drive_report,'summarize_rows',side_effect=details):
                    doc=drive_report.generate(run)
                import csv
                with (out/'paired.csv').open() as f:pairs=list(csv.DictReader(f))
                self.assertEqual(len(pairs),18 if failure else 20)
                self.assertIn('clip_commands',doc.read_text());self.assertIn('path_schedules',doc.read_text())

if __name__=='__main__':unittest.main()
