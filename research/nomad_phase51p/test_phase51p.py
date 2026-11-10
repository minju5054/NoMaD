"""Dry-run/configuration tests only; no runtime thread, model or simulator."""
import ast,copy,inspect,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from . import config,geometry,runtime,launch,campaign,metrics,report

class Tests(unittest.TestCase):
    def test_environment_only_matrix_and_widths(self):
        from nomad_phase47c.config import runtime_config as original
        p=config.verify();self.assertEqual(len(p['main_order']),20)
        checks=[]
        for j in p['main_order']:
            scene,condition=config.split(j['scene']);c=config.runtime_config(j['method'],j['index'],90,j['scene']);old=original(j['method'],j['index'],90,scene)
            allowed={'run_id'}|{k for k in c if k.startswith('phase51p')}
            if condition=='WIDE' and 'dynamic_obstacle' in c:allowed|={'dynamic_obstacle','phase38_jitter','blockage_center_y_m','phase26_spawn'}
            self.assertEqual({k:v for k,v in c.items() if k not in allowed},{k:v for k,v in old.items() if k not in allowed})
            self.assertEqual(c['phase38_method'],'OURS-DETOUR');self.assertEqual(c['nomad_goal_stop'],True)
            if condition=='WIDE' and 'dynamic_obstacle' in c:
                axis=c['phase51p_wide']['lateral_axis']
                for k in ('color_rgb','id','placement','minimum_visible_pixels'):self.assertEqual(c['dynamic_obstacle'][k],old['dynamic_obstacle'][k])
                for a in range(3):
                    if a!=axis:self.assertEqual(c['dynamic_obstacle']['size_xyz_m'][a],old['dynamic_obstacle']['size_xyz_m'][a])
                for number,pose in geometry.canonical_poses(scene):
                    r=geometry.checked_straight(c,pose) if scene=='L2' else geometry.checked_place(c,pose,number)
                    check=geometry.validate_placement(c,r);self.assertGreaterEqual(max(check['side_gaps_m']),.33-1e-9)
                    self.assertAlmostEqual(r['obstacle']['center_xy_m'][axis],c['phase51p_wide']['centerline_m'])
                    checks.append(dict(scene=scene,seed=j['index'],number=number,pose=pose,**check));json.dumps(r,allow_nan=False)
        self.assertAlmostEqual(p['wide']['H1']['applied_multiplier'],1.14)
        self.assertEqual(p['wide']['L2']['applied_multiplier'],1.5);self.assertEqual(p['wide']['H2']['applied_multiplier'],1.5)
        self.assertFalse(p['wide']['SLW']['applies']);self.assertFalse(p['wide']['LC']['applies'])
        folder=config.OUT/'preparation';folder.mkdir(parents=True,exist_ok=True);(folder/'geometry_checks.json').write_text(json.dumps(checks,indent=2)+'\n')

    def test_delay_driver_accepts_1p5_without_starting_engine(self):
        from nomad_isaac import async_runtime as original
        from nomad_isaac.delivery_delay import UniformDeliveryDelay
        class Boundary(Exception):pass
        for retain in (True,False):
            tree=runtime.driver_tree(inspect.getsource(original.run_async),retain)
            ns=dict(original.__dict__,_phase24_full_frames=retain,ExecutionThread=lambda *a,**k:(_ for _ in ()).throw(Boundary()))
            exec(compile(tree,original.__file__,'exec'),ns)
            for scene in config.BASE_SCENES:
                with tempfile.TemporaryDirectory() as td:
                    c=config.runtime_config(config.METHODS[0],221,90,scene+'_L150')
                    with self.assertRaises(Boundary):ns['run_async'](c,Path(td),None,None,None,None,None,{},uniform_delivery_delay_s=1.5,pure_pursuit=True)
                    p=json.loads((Path(td)/'delivery_delay_protocol.json').read_text());self.assertEqual(p['configured_additional_s'],1.5)
                    # Execute only the deadline math on a fake clock; no real wait.
                    now=[1000];waits=[]
                    def wait(seconds):waits.append(seconds);now[0]+=round(seconds*1e9)
                    d=UniformDeliveryDelay(p,clock_ns=lambda:now[0],wait=wait);m={};d.annotate_accepted_request(m)
                    self.assertEqual(d.hold_until_deadline(m,1000),1_500_001_000);self.assertEqual(waits,[1.5]);self.assertEqual(d.accepted_count,1)
        c=config.runtime_config(config.METHODS[0],221,90,'LC_WIDE')
        with patch.object(runtime,'frozen_run',return_value='frozen') as fn:self.assertEqual(runtime.run_without_oracle(c,uniform_delivery_delay_s=.75),'frozen');fn.assert_called_once()
        # Neither branch replaces any execution, inference or depth class.
        targets={n.id for n in ast.walk(tree) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store)}
        self.assertTrue(targets.isdisjoint({'ExecutionThread','AsyncClient','DepthMapThread','WaypointExecution'}))

    def test_minimal_local_install_routing(self):
        import nomad_isaac.sudden_obstacle as sudden
        import nomad_phase2.config as location
        for level in config.SCENES:
            c=config.runtime_config(config.METHODS[0],221,90,level)
            with patch.object(runtime,'frozen_install') as frozen,patch.object(sudden,'SuddenObstacleMonitor',object),patch.object(location,'place',object):
                runtime.install(c);frozen.assert_called_once_with(c)
                if level in ('H1_WIDE','H2_WIDE'):self.assertIs(sudden.SuddenObstacleMonitor,geometry.WideMonitor)
                else:self.assertIs(sudden.SuddenObstacleMonitor,object)
                self.assertIs(location.place,geometry.checked_straight if level=='L2_WIDE' else object)

    def test_launcher_and_campaign_all20_without_processes(self):
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        class Boundary(Exception):pass
        jobs=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(jobs),20)
        for j in jobs:
            for out in j['outputs']:self.assertLess(validate_socket_path(socket_path_for_run(Path(out))),100)
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No child processes')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            with patch.object(sys,'argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]),self.assertRaises(Boundary):fn()
            args=launch.Processes.route(['python','simulator.py','--level',j['scene'],'--delay','.75'])
            self.assertEqual(args[-1],'1.5' if j['scene'].endswith('L150') else '.75')
        processes=launch.Processes()
        with patch('subprocess.Popen',return_value=object()) as popen:
            processes.Popen(['python','-m','nomad_isaac.worker']);self.assertEqual(popen.call_args.args[0][2],'nomad_phase43p.worker')
            processes.Popen(['python',str(config.ROOT/'research/nomad_phase26/simulator.py'),'--level','H1_L150','--delay','.75'])
            self.assertEqual(popen.call_args.args[0][1],str(config.HERE/'simulator.py'));self.assertEqual(popen.call_args.args[0][-1],'1.5')
        code='''
from nomad_phase51p import campaign as c
from nomad_phase51p.config import RUN_ROOT
def halt():
 assert len(c.frozen.base.jobs(RUN_ROOT))==20
 assert c.frozen.base.run_job.__globals__['subprocess'].__class__ is c.Routes
c.frozen.base.main=halt
c.main()
assert not RUN_ROOT.exists()
'''
        r=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr[-2000:])

    def test_ec_exhaustion_merge_terminal_and_empty(self):
        reject=lambda t:dict(event='FALLBACK',reason='NORMAL_NO_EC_SAFE_CANDIDATE',simulation_time_s=t)
        events=[reject(2),reject(3),dict(event='CHECK',passed=False,simulation_time_s=4),dict(event='INSTALL',simulation_time_s=5),reject(7)]
        r=metrics.ec_exhausted(events,10);self.assertEqual(r['ec_all_candidates_rejected_s'],6)
        self.assertEqual(r['ec_all_candidates_rejected_max_s'],3);self.assertEqual(r['ec_all_candidates_rejected_episodes'],2)
        self.assertEqual(metrics.ec_exhausted([],10)['ec_all_candidates_rejected_s'],0);json.dumps(r,allow_nan=False)

    def test_comparison_tables_and_no_fabricated_missing_outcomes(self):
        old=report.baselines();self.assertEqual(len(old),10)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            doc=report.generate(root,root/'empty',root/'empty.md')
            import csv
            paired=list(csv.DictReader((root/'empty/paired.csv').read_text().splitlines()));self.assertEqual(len(paired),20)
            self.assertTrue(all(r['success']=='' and r['phase47_success'] in ('True','False') for r in paired))
            by={(r['scene'],r['index']):r for r in old}
            for n,j in enumerate(config.registered_order()):
                s,k=config.split(j['scene']);r=dict(by[(s,j['index'])],**j,condition=k,base_scene=s)
                (root/'metrics'/f'{n}.json').write_text(json.dumps(r,allow_nan=False))
            doc=report.generate(root,root/'full',root/'full.md')
            self.assertEqual(json.loads((root/'full/analysis.json').read_text())['completed'],20)
            paired=list(csv.DictReader((root/'full/paired.csv').read_text().splitlines()));self.assertTrue(all(float(r['stopped_s_delta'])==0 for r in paired))
            self.assertTrue(all(not x or x.startswith('|') for x in doc.read_text().splitlines()))

if __name__=='__main__':unittest.main()
