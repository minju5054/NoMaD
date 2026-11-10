"""Minimal dry-run/environment wiring tests; no actual inference/solver/sim."""
import copy,inspect,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from . import config,launch,campaign,runtime,report
from nomad_phase53p import config as original_config,runtime as original_runtime
from nomad_h1v2.scene import configure,load_spec,project,at,Monitor

class Tests(unittest.TestCase):
    def test_four_configs_only_environment_and_names_change(self):
        p=config.verify();self.assertEqual(len(p['main_order']),4);self.assertFalse(p['smoke']['enabled'])
        for j in p['main_order']:
            cond=config.split(j['scene'])[1];old=original_config.runtime_config(j['method'],221,90,'H1_'+cond)
            expected=configure(old);c=config.runtime_config(j['method'],221,90,j['scene'])
            for k,v in expected.items():
                if k!='run_id':self.assertEqual(c[k],v,k)
            added=set(c)-set(expected);self.assertEqual(added,{'h1v2_trial','h1v2_trial_level'})
            self.assertEqual(c['phase53p_delay_s'],.75 if cond=='D075' else 1.5)
            self.assertEqual(c['phase16_scene'],'H1');self.assertEqual(c['dynamic_obstacle']['center_xy_m'],load_spec()['box']['center_xy_m'])
            json.dumps(c,allow_nan=False)
    def test_method_functions_are_frozen_environment_installed_last(self):
        self.assertIs(runtime.run_without_oracle,original_runtime.run_without_oracle)
        calls=[]
        with patch.object(runtime,'frozen_install',side_effect=lambda c:calls.append('METHOD')),patch.object(runtime,'install_environment',side_effect=lambda c:calls.append('SCENE')):
            runtime.install({'h1v2_trial':True})
        self.assertEqual(calls,['METHOD','SCENE'])
        self.assertNotIn('Execution(',inspect.getsource(runtime))
    def test_four_real_launcher_argument_paths_without_starting(self):
        class Boundary(Exception):pass
        jobs=campaign.jobs();self.assertEqual(len(jobs),4);self.assertEqual(len({j['key'] for j in jobs}),4)
        for j in jobs:
            self.assertEqual(len(j['outputs']),2)
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**k:self.fail('No process')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            with patch.object(sys,'argv',['launch','--scene',j['scene'],'--method',j['method'],'--index','221','--output',j['outputs'][0]]),self.assertRaises(Boundary):fn()
        with patch.object(sys,'argv',['launch','--smoke']),self.assertRaises(AssertionError):launch.main()
    def test_spawn_first_threshold_geometry_and_single_box(self):
        c=config.runtime_config('CUT',221,90,'H1-v2_D075');p=c['h1v2']
        from nomad_h1v2.scene import triggered,place
        for ds,expected in [(-.001,False),(.001,True)]:
            q,_=at(p['topomap_nodes_xy_m'],p['spawn']['arc_m']+ds)
            self.assertEqual(triggered(c,[*q,0.],0),expected);self.assertFalse(triggered(c,[*q,0.],1))
        q=p['spawn']['position_xy_m'];r=place(c,[*q,0.],0)
        self.assertEqual(r['status'],'PLACED');self.assertEqual(r['obstacle']['size_xyz_m'],[.5,.4,.8])
    def test_routes_only_local_entrypoint_and_no_smoke(self):
        with patch('subprocess.Popen') as popen:
            obj=launch.Processes();obj.Popen(['isaac','/old/nomad_phase26/simulator.py','--level','H1-v2_D150','--delay','.75'])
            args=popen.call_args.args[0];self.assertEqual(args[1],str(config.HERE/'simulator.py'));self.assertEqual(args[-1],'1.5')
            obj.Popen(['python','-m','nomad_isaac.worker']);self.assertEqual(popen.call_args.args[0][2],'nomad_phase43p.worker')
            campaign.Routes().Popen(['/usr/bin/python3','-m','nomad_phase26.launch','--index','221'])
            args=popen.call_args.args[0];self.assertIn('nomad_h1v2_trial.launch',args);self.assertNotIn('--smoke',args)
    def test_report_and_five_images_from_temporary_synthetic_logs(self):
        from PIL import Image
        def write(p,x):p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(x))
        def lines(p,xx):p.write_text(''.join(json.dumps(x)+'\n' for x in xx))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,j in enumerate(config.registered_order()):
                c=config.runtime_config(j['method'],221,90,j['scene']);out=root/f'run{i}';out.mkdir();write(out/'scenario.json',c)
                path=np.column_stack([np.linspace(.1,.8,8),np.zeros(8)]).tolist();graph=j['method']=='GRAPH-HO';key=f"{j['scene']}_221_{j['method']}"
                r=dict(j,key=key,output=str(out),condition=config.split(j['scene'])[1],technical_validation='PASS',classification='SUCCESS',success=True,collision=False,
                    wrong_stop=False,timeout_without_declaration=False,goal_time_s=2/72,stopped_s=0.,align_rotate_s=0.,graph_attempts=int(graph),graph_applied=int(graph),
                    graph_adoption_rate=1. if graph else None,ec_checks=1,ec_rejects=0,graph_rejection_reasons={})
                write(root/'metrics'/f'{i}.json',r);write(out/'summary.json',dict(scenario=c,dynamic_obstacle={}))
                (out/'agent_trajectory.csv').write_text('simulation_time_s,x_m,y_m,yaw_rad,v_m_s,w_rad_s,goal_distance_m\n0,0,0,0,0,0,4.6\n'+f'{1/72},0,0,0,0,0,4.6\n{2/72},0,0,0,0,0,4.6\n')
                lines(out/'phase20_commands.jsonl',[dict(time_s=0.,pose=[0,0,0],source='NORMAL')])
                lines(out/'repair.jsonl',[dict(event='PATH_APPLIED',id=0,simulation_time_s=0.,path_world=path,kind='SAFE')])
                ho=[dict(event='SOLVE',id=0,simulation_time_s=0.,applied=True)] if graph else []
                ho.append(dict(event='INSTALL',id=0,simulation_time_s=0.,path_world=path,path_type='GRAPH_HO' if graph else 'CUT'))
                lines(out/'graph_ho.jsonl',ho);lines(out/'exec_cert.jsonl',[dict(event='CHECK',simulation_time_s=0.,passed=True,pose=[0,0,0])])
                lines(out/'received.jsonl',[dict(id=0,latched_sim_s=0.,observation_pose=[0,0,0])]);(out/'model/derived').mkdir(parents=True)
                np.savez_compressed(out/'model/derived/0000.npz',metric=np.repeat(np.array(path)[None],8,axis=0))
            doc,figs=report.generate(root,root/'results',root/'report.md',root/'figures')
            self.assertEqual(len(figs['files']),5);self.assertEqual(len(figs['details']),4)
            self.assertTrue(all(d['candidates']==8 and not d['missing_chunk_ids'] for d in figs['details']))
            for f in figs['files']:
                with Image.open(f) as im:self.assertGreater(im.width,1000);self.assertAlmostEqual(im.info['dpi'][0],150,delta=.02)
            self.assertEqual(json.loads((root/'results/status.json').read_text())['completed'],4)
            self.assertIn('graph_rejection_reasons',doc.read_text());self.assertIn('h1v2_trial_all.png',doc.read_text())
if __name__=='__main__':unittest.main()
