"""Oracle/launcher/report plumbing only; no simulator, inference or solver run."""
import inspect,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase43p.test_phase43p import Tensor
from nomad_isaac.topomap import candidate_range
from nomad_phase40p.launch import bind
from . import config,campaign,launch,worker,runtime,localization,metrics,report,figures

class Tests(unittest.TestCase):
    def test_oracle_global_nearest_tie_and_official_subgoal(self):
        pose=[[.5,0,2.]];loc=localization.Localization([[0,0,0],[1,0,1],[2,0,2]],lambda:pose[0])
        start,end=loc.window();r=loc.select([5.,0.,0.])
        self.assertEqual(r['closest_node'],0);self.assertEqual(r['selected_subgoal_id'],0);self.assertEqual(r['raw_argmin_node'],1)
        pose[0]=[1.1,0,-2.];loc.window();r=loc.select([0.,2.,0.]);self.assertEqual(r['closest_node'],1);self.assertEqual(r['selected_subgoal_id'],2)
        self.assertFalse(r['topomap_goal_node_reached']);self.assertNotIn('hmm',r)
        pose[0]=[2.,0,0];loc.window();r=loc.select([0.,0.,9.]);self.assertTrue(r['topomap_goal_node_reached']);self.assertEqual(r['selected_subgoal_id'],2)
        json.dumps(r,allow_nan=False)
    def test_oracle_jump_outside_old_window_and_captured_pose_is_fixed(self):
        pose=[[10.1,0,0]];loc=localization.Localization(np.c_[np.arange(20),np.zeros((20,2))],lambda:pose[0])
        old_window=candidate_range(0,19,4);start,end=loc.window();self.assertGreater(loc.closest,old_window[1]);self.assertEqual((start,end),candidate_range(10,19,4))
        pose[0]=[17.,0,0] # Main thread movement cannot replace the captured query.
        r=loc.select(np.full(end-start+1,2.));self.assertEqual(r['closest_node'],10);self.assertEqual(r['oracle']['pose'],[10.1,0.,0.])
    def test_worker_one_decode_original_RNG_no_HMM_metadata_or_filter(self):
        calls=[];encodes=[]
        class Parent:
            def __init__(self,manifest):
                self.images=list(range(14));self.hashes=[{'rgb_sha256':str(i)} for i in self.images];self.closest_node=0;self.previous_subgoal=None;self.goal_node=13
        def encode(model,obs,images):
            encodes.append(list(images));values=np.full(len(images),2.);values[0]=0.
            return Tensor(np.asarray(images)[:,None]),Tensor(values),Tensor([1]),Tensor(images)
        def decode(model,condition,noise,seed):calls.append((int(condition.numpy().item()),noise,seed));return {'metric':Tensor(np.zeros((8,8,2)))}
        native=SimpleNamespace(TopomapPolicy=Parent,encode_candidates=encode,diffuse_condition=decode,torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda:None)),CONFIG={'num_diffusion_iters':10})
        request=dict(observation_pose=[4.01,0,.2],observation_sim_s=1.) # No HMM odometry fields.
        from nomad_phase42l.filter import WindowHMM
        with tempfile.TemporaryDirectory() as tmp,patch.object(WindowHMM,'__init__',side_effect=AssertionError('HMM forbidden')):
            f=Path(tmp)/'manifest.json';f.write_text(json.dumps(dict(nodes=[dict(node_id=i,world_pose=[i*.4,0,0]) for i in range(14)])))
            policy=worker.make_policy(native,lambda:request)(f);noise=object();_,a=policy.infer(None,[],noise,17)
            self.assertEqual(a['closest_node'],10);self.assertEqual(encodes[0],list(range(*[candidate_range(10,13,4)[0],candidate_range(10,13,4)[1]+1])))
            self.assertEqual(a['selected_subgoal_id'],11);self.assertNotIn('hmm',a);self.assertFalse(a['oracle']['HMM_used'])
            request.update(observation_pose=[5.2,0,0],observation_sim_s=2.);_,b=policy.infer(None,[],noise,19)
            self.assertTrue(b['topomap_goal_node_reached']);self.assertEqual(b['oracle']['observation_tick'],144)
            self.assertEqual([x[2] for x in calls],[17,19]);self.assertIs(calls[0][1],noise);self.assertEqual([x[0] for x in calls],[11,13]);json.dumps(b,allow_nan=False)
    def test_new_seed_only_with_exact_control_config_and_order(self):
        from nomad_phase58p import config as old,runtime as old_runtime
        expected=[dict(j,index=j['index']+2) for j in old.registered_order()];self.assertEqual(config.registered_order(),expected)
        self.assertIs(runtime.install,old_runtime.install);self.assertIs(runtime.run_without_oracle,old_runtime.run_without_oracle)
        for j in config.registered_order():
            before=bind(old.runtime_config,INDICES=config.INDICES,protocol=config.protocol)(j['method'],j['index'],90,j['scene'])
            before['phase47c_method']='OURS-DETOUR';before.pop('phase43p',None);before.pop('phase43p_method',None)
            c=config.runtime_config(j['method'],j['index'],90,j['scene'])
            self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase61p') and k!='oracle_localization_analysis_only'},before)
            self.assertEqual(c['seed_offset'],j['index']*10000);self.assertTrue(c['nomad_goal_stop']);self.assertFalse(c.get('phase43p',False))
            if j['scene']=='H1-v2':self.assertEqual(c['h1v2']['requested_target']['y_m'],1.10)
            json.dumps(c,allow_nan=False)
    def test_real_launcher18_and_oracle_worker_route(self):
        class Boundary(Exception):pass
        self.assertEqual(len(campaign.jobs()),18)
        for j in campaign.jobs():
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No process allowed')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            args=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            with patch.object(sys,'argv',args),self.assertRaises(Boundary):fn()
            with patch('subprocess.Popen',return_value=SimpleNamespace()) as popen:
                p=launch.Processes();p.Popen(['python','-m','nomad_isaac.worker']);self.assertIn('nomad_phase61p.worker',popen.call_args.args[0]);self.assertNotIn('nomad_phase43p.worker',popen.call_args.args[0])
                p.Popen(['isaac',str(config.ROOT/'research/nomad_phase26/simulator.py')]);self.assertIn(str(config.HERE/'simulator.py'),popen.call_args.args[0])
    def test_stop_dispatch_is_nonHMM_and_same_declaration_rule(self):
        from nomad_phase47c import runtime as dispatcher
        from nomad_phase41.stop import goal_node_reached
        c=config.runtime_config('CUT',229,90,'SLW')
        with patch.object(dispatcher,'original_localization') as original,patch.object(dispatcher,'hmm_localization',side_effect=AssertionError('HMM forbidden')):
            dispatcher.install(c);original.assert_called_once_with(c)
        self.assertTrue(goal_node_reached({'topomap':{'closest_node':3,'goal_node':3}}));self.assertFalse(goal_node_reached({'topomap':{'closest_node':2,'goal_node':3}}))
        from nomad_isaac.async_core import WaypointExecution
        self.assertIn('age < 1.0',inspect.getsource(WaypointExecution.control))
    def test_oracle_audit_and_frozen_outcome_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'model').mkdir();nodes=[dict(node_id=i,world_pose=[i,0,0]) for i in range(6)]
            manifest=root/'manifest.json';manifest.write_text(json.dumps(dict(nodes=nodes)));(root/'scenario.json').write_text(json.dumps(dict(topomap_manifest=str(manifest))))
            pose=[None];loc=localization.Localization([n['world_pose'] for n in nodes],lambda:pose[0]);events=[]
            for i,x in enumerate([0.,3.1,5.]):
                pose[0]=[x,0,0];a,b=loc.window();m=loc.select(np.full(b-a+1,2.));m['oracle']['observation_tick']=i
                events.append(dict(id=i,observation_pose=pose[0],observation_sim_s=i/72,topomap=m))
            f=root/'model/inference.jsonl';f.write_text(''.join(json.dumps(e)+'\n' for e in events))
            with patch.object(metrics,'original_outcomes',return_value=dict(success=True)) as outcome:r=metrics.oracle_audit(root);outcome.assert_called_once_with(root)
            self.assertTrue(r['success']);self.assertIs(metrics._a47.__globals__['original_audit'],metrics.oracle_audit)
            events[-1]['topomap']['closest_node']=4;f.write_text(''.join(json.dumps(e)+'\n' for e in events))
            with patch.object(metrics,'original_outcomes',return_value={}),self.assertRaises(AssertionError):metrics.oracle_audit(root)
    def test_success_pairs_all_three_and_missing_not_imputed(self):
        rows=[]
        for j in config.registered_order():rows.append(dict(j,technical_validation='PASS',success=j['method']!='CUT'))
        details,summary=report.paired(rows);self.assertEqual(len(details),18)
        self.assertEqual([r['success_difference'] for r in summary],[6,6,0]);self.assertEqual([r['valid_pairs'] for r in summary],[6,6,6])
        one=next(r for r in rows if r['method']=='CUT');one['technical_validation']='FAIL'
        details,summary=report.paired(rows);self.assertEqual([r['valid_pairs'] for r in summary],[5,5,6]);self.assertTrue(any(r['success_difference'] is None for r in details))
    def test_report_oracle_label_and_png_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir()
            for i,j in enumerate(config.registered_order()):(root/'metrics'/f'{i}.json').write_text(json.dumps(dict(j,key=str(i),technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)))
            with patch.object(figures,'generate',return_value=[]) as fig:doc=report.generate(root,root/'out',root/'report.md')
            self.assertEqual(len(fig.call_args.args[0]),18);self.assertIn('oracle 위치추정 분석용',doc.read_text());self.assertIn('CONS+G18 minus CONS',doc.read_text())
            repo=root/'repo';repo.mkdir();subprocess.run(['git','init','--quiet'],cwd=repo,check=True);(repo/'.gitignore').write_text('*.png\n')
            out=repo/'results/phase61p';(out/'figures').mkdir(parents=True);(out/'summary.json').write_text('{}');(out/'figures/run.png').write_bytes(b'PNG staging fixture')
            reportdoc=repo/'report.md';reportdoc.write_text('oracle analysis only')
            report.stage_report(reportdoc,out,repo);tracked=subprocess.check_output(['git','ls-files'],cwd=repo,text=True)
            self.assertIn('results/phase61p/figures/run.png',tracked)
if __name__=='__main__':unittest.main()
