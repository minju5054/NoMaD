"""Synthetic NET/worker/audit plumbing; no simulator, NoMaD or solver calls."""
import csv,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase43p.test_phase43p import Tensor
from nomad_hmm_replay.filter import Replay
from nomad_isaac.topomap import candidate_range
from .localization import Localization
from . import config,campaign,launch,worker,runtime,metrics,report,figures

class Tests(unittest.TestCase):
    def test_online_NET_exact_replay_window_and_subgoal(self):
        nodes=np.c_[np.arange(12)*.4,np.zeros((12,2))];loc=Localization(nodes);ref=Replay(12,.4,'NET')
        total=0.
        for i,position in enumerate(([0,0],[.1,0],[0,0],[.7,0],[.8,0],[.5,0])):
            if i:total+=.4
            start,end=loc.window();self.assertEqual((start,end),candidate_range(loc.closest,11,4))
            values=np.full(end-start+1,8.);values[min(i,len(values)-1)]=0.
            expected,detail=ref.step(list(range(start,end+1)),values,position,total)
            got=loc.select(values,total,position)
            self.assertEqual(got['closest_node'],expected)
            self.assertEqual(got['selected_subgoal_id'],min(expected+int(values[expected-start]<3),end))
            self.assertEqual(got['topomap_goal_node_reached'],expected==11)
            self.assertEqual(got['hmm']['transition_half_width'],detail['transition_half_width'])
            np.testing.assert_array_equal(loc.filter.replay.filter.logp,ref.filter.logp)
            self.assertEqual(got['hmm']['entry_position_after'],detail['entry_position_after']);self.assertTrue(all(x==0 for x in got['hmm']['memory_log_factors']))
            json.dumps(got,allow_nan=False)
    def test_zero_width_net_not_path_length_and_entry_reset(self):
        loc=Localization(np.c_[np.arange(5),np.zeros((5,2))])
        loc.select([0,100,100,100,100],0,[0,0]);r=loc.select([0,100,100,100,100],2.,[.1,0])
        self.assertEqual(r['hmm']['transition_half_width'],0);self.assertAlmostEqual(r['hmm']['entry_displacement_m'],.1)
        r=loc.select([100,0,100,100,100],3.,[.8,0]);self.assertEqual(r['closest_node'],1);self.assertEqual(r['hmm']['entry_position_after'],[.8,0.])
        r=loc.select([0,100,100,100,100],4.,[.2,0]);self.assertEqual(r['closest_node'],0);self.assertEqual(r['hmm']['entry_position_after'],[.2,0.])
    def test_worker_original_infer_decoder_RNG_and_captured_position(self):
        calls=[]
        class Parent:
            def __init__(self,manifest):
                self.images=list(range(14));self.hashes=[{'rgb_sha256':str(i)} for i in self.images];self.closest_node=0;self.previous_subgoal=None;self.goal_node=13
        def encode(model,observations,images):
            values=np.full(len(images),10.);values[2 if not calls else -1]=0.
            return Tensor(np.asarray(images)[:,None]),Tensor(values),Tensor([1]),Tensor(images)
        def decode(model,condition,noise,seed):calls.append((int(condition.numpy().item()),noise,seed));return {'metric':Tensor(np.zeros((8,8,2)))}
        native=SimpleNamespace(TopomapPolicy=Parent,encode_candidates=encode,diffuse_condition=decode,torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda:None)),CONFIG={'num_diffusion_iters':10})
        request=dict(hmm_odometry_total_m=0.,hmm_odometry_tick=72,observation_pose=[.1,.2,.3])
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'manifest.json';file.write_text(json.dumps(dict(nodes=[dict(node_id=i,world_pose=[i*.4,0,0]) for i in range(14)])))
            policy=worker.make_policy(native,lambda:request)(file);noise=object()
            _,first=policy.infer(None,[],noise,17);self.assertEqual(first['hmm']['odometry_xy_m'],[.1,.2])
            request.update(hmm_odometry_total_m=2.,hmm_odometry_tick=144,observation_pose=[.11,.2,.5])
            _,second=policy.infer(None,[],noise,19)
            self.assertEqual(second['hmm']['transition_half_width'],0);self.assertEqual(second['hmm']['odometry_tick'],144)
            self.assertEqual(second['hmm']['odometry_xy_m'],[.11,.2]);self.assertIs(calls[0][1],noise);self.assertEqual([x[2] for x in calls],[17,19])
            self.assertEqual([x[0] for x in calls],[first['selected_subgoal_id'],second['selected_subgoal_id']]);json.dumps(second,allow_nan=False)
    def test_exact18_config_order_and_runtime_identity(self):
        from nomad_phase58p import config as old,runtime as old_runtime
        self.assertEqual(config.registered_order(),old.registered_order());self.assertEqual(config.protocol()['placements'],old.protocol()['placements'])
        self.assertIs(runtime.install,old_runtime.install);self.assertIs(runtime.run_without_oracle,old_runtime.run_without_oracle)
        for j in config.registered_order():
            c=config.runtime_config(j['method'],j['index'],90,j['scene']);before=old.runtime_config(j['method'],j['index'],90,j['scene'])
            self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase59p')},before)
            self.assertEqual(c['phase59p_transition'],'NET');json.dumps(c,allow_nan=False)
    def test_real_launcher_18_argument_checks_and_NET_route(self):
        class Boundary(Exception):pass
        self.assertEqual(len(campaign.jobs()),18)
        for j in campaign.jobs():
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**k:self.fail('No processes allowed')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            with patch.object(sys,'argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]),self.assertRaises(Boundary):fn()
            with patch('subprocess.Popen',return_value=SimpleNamespace()) as popen:
                process=launch.Processes();process.Popen(['python','-m','nomad_isaac.worker']);self.assertIn('nomad_phase59p.worker',popen.call_args.args[0])
                process.Popen(['isaac',str(config.ROOT/'research/nomad_phase26/simulator.py')]);self.assertIn(str(config.HERE/'simulator.py'),popen.call_args.args[0])
    def test_NET_audit_uses_position_and_frozen_outcome_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'model').mkdir();nodes=[dict(node_id=i,world_pose=[i,0,0]) for i in range(5)]
            manifest=root/'manifest.json';manifest.write_text(json.dumps(dict(nodes=nodes)))
            (root/'scenario.json').write_text(json.dumps(dict(topomap_manifest=str(manifest),phase16_scene='SLW',seed_offset=2270000)))
            (root/'summary.json').write_text(json.dumps(dict(final_pose=[.1,0,0])))
            loc=Localization([n['world_pose'] for n in nodes]);events=[]
            for i,x in enumerate([0.,.1,0.]):
                start,end=loc.window();distances=[0.]+[100.]*(end-start)
                selection=loc.select(distances,i*.1,[x,0])
                events.append(dict(id=i,observation_pose=[x,0,0],observation_sim_s=i/72,hmm_odometry_total_m=i*.1,hmm_odometry_tick=i,topomap=selection))
            (root/'model/inference.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
            with patch.object(metrics.m43,'frozen_audit',return_value=dict(declared_arrival=False)) as outcome:
                result=metrics.net_audit(root);outcome.assert_called_once_with(root)
            self.assertEqual(len(result['node_errors']),3)
            self.assertIs(metrics._a58.__globals__['frozen_audit'],metrics._a53)
            self.assertIs(metrics._a53.__globals__['frozen_audit'],metrics._a47)
            self.assertIs(metrics._a47.__globals__['hmm_audit'],metrics.net_audit)
    def test_supplementary_stop_nodes_0p7_and_false_goal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=root/'manifest.json';manifest.write_text(json.dumps(dict(nodes=[dict(node_id=i,world_pose=[i,0,0]) for i in range(5)])))
            (root/'scenario.json').write_text(json.dumps(dict(topomap_manifest=str(manifest))))
            with (root/'agent_trajectory.csv').open('w') as f:
                writer=csv.writer(f);writer.writerow(['goal_distance_m']);writer.writerows([[1.5],[.65],[.8]])
            saved=dict(node_errors=[dict(inference_id=1,closest_node=4,true_node=0,transition_K=0),dict(inference_id=2,closest_node=4,true_node=2,transition_K=1)])
            r=metrics.localization_metrics(root,saved);self.assertTrue(r['reached_goal_0p7']);self.assertTrue(r['arrived_without_declaration']);self.assertFalse(r['arrived_0p5_without_declaration']);self.assertEqual(r['false_goal_count'],1)
            (root/'declared_arrival.json').write_text(json.dumps(dict(closest_node=4,pose=[3.35,0,0])))
            r=metrics.localization_metrics(root,saved);self.assertFalse(r['arrived_without_declaration']);self.assertEqual(r['declaration_estimated_node'],4);self.assertEqual(r['declaration_true_node'],3)
    def test_report_preparation_never_enriches_real_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();baseline=root/'baseline.json'
            baseline.write_text(json.dumps([dict(scene='SLW',index=227,method='CUT',technical_validation='PASS',success=True,stop_distance_m=.4)]))
            for i,j in enumerate(config.registered_order()):
                (root/'metrics'/f'{i}.json').write_text(json.dumps(dict(j,key=str(i),technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)))
            with patch.object(report,'BASELINE',baseline),patch.object(metrics,'localization_metrics',side_effect=AssertionError('No saved-log analysis in prep')),patch.object(figures,'generate',return_value=[]) as fig:
                doc=report.generate(root,root/'out',root/'report.md',prepare_only=True)
            self.assertEqual(len(fig.call_args.args[0]),18);self.assertIn('Phase58_success',doc.read_text());self.assertIn('arrived_without_declaration',doc.read_text())
            self.assertEqual(json.loads((root/'out/status.json').read_text())['completed'],18)
if __name__=='__main__':unittest.main()
