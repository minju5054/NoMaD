"""Synthetic SIGN and publication plumbing only; no simulator/model/solver runs."""
import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase43p.test_phase43p import Tensor
from nomad_loc_v2.filter import Filter
from nomad_isaac.topomap import candidate_range
from . import config,campaign,launch,runtime,localization,worker,metrics,report,figures

class Tests(unittest.TestCase):
    def test_frozen_model_exact_bytes_and_original_precision(self):
        model=config.load_model();self.assertEqual(model['sigma2'],0.14923311275040188)
        self.assertEqual(hashlib.sha256(config.MODEL_FILE.read_bytes()).hexdigest(),config.MODEL_SHA256)
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'model.json';file.write_bytes(config.MODEL_FILE.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'model_sha256 mismatch'):config.load_model(file)
    def test_online_SIGN_matches_frozen_filter_full_posterior(self):
        xy=np.c_[np.arange(14)*.4,np.zeros(14)];nodes=np.c_[xy,np.zeros(14)];loc=localization.Localization(nodes)
        frozen=Filter(xy,loc.spacing,'SIGN',config.load_model());total=0.
        for i,position in enumerate(([0,0],[.1,0],[.05,0],[.6,.1],[.7,.2])):
            total+=.2 if i else 0.;start,end=loc.window();self.assertEqual((start,end),candidate_range(loc.closest,13,4))
            values=np.full(end-start+1,8.);values[min(i,len(values)-1)]=0.
            node,detail=frozen.step(list(range(start,end+1)),values,position,total)
            got=loc.select(values,total,position)
            self.assertEqual(got['closest_node'],node);self.assertEqual(got['selected_subgoal_id'],min(node+int(values[node-start]<3),end))
            self.assertEqual(got['topomap_goal_node_reached'],node==13)
            np.testing.assert_array_equal(loc.filter.replay.logp,frozen.logp)
            for key in ('signed_forward_m','transition_mean_nodes','sigma2','posterior_max'):self.assertEqual(got['hmm'][key],detail[key])
            self.assertIsNone(got['hmm']['transition_half_width']);self.assertEqual(got['hmm']['model_sha256'],config.MODEL_SHA256);json.dumps(got,allow_nan=False)
    def test_SIGN_uses_signed_previous_MAP_tangent_without_refit_or_OBS(self):
        import nomad_loc_v2.calibration as cal
        import nomad_loc_v2.filter as sign
        nodes=np.array([[0,0,0],[1,0,0],[1,1,0],[1,2,0],[1,3,0]],float)
        with patch.object(cal,'fit',side_effect=AssertionError('Refit forbidden')),patch.object(sign,'obs_log_emission',side_effect=AssertionError('OBS forbidden')):
            loc=localization.Localization(nodes);first=loc.select([100,100,0,100,100],0.,[1,1])
            self.assertEqual(first['closest_node'],2)
            result=loc.select([100,100,0,100,100],.5,[1,.5])
        self.assertAlmostEqual(result['hmm']['signed_forward_m'],-.5);self.assertAlmostEqual(result['hmm']['transition_mean_nodes'],-.5)
        self.assertEqual(result['hmm']['sigma2'],config.load_model()['sigma2'])
    def test_original_worker_decoder_and_capture_position(self):
        calls=[]
        class Parent:
            def __init__(self,manifest):
                self.images=list(range(14));self.hashes=[{'rgb_sha256':str(i)} for i in self.images];self.closest_node=0;self.previous_subgoal=None;self.goal_node=13
        def encode(model,obs,images):
            d=np.full(len(images),10.);d[2 if not calls else -1]=0.
            return Tensor(np.asarray(images)[:,None]),Tensor(d),Tensor([1]),Tensor(images)
        def decode(model,condition,noise,seed):calls.append((int(condition.numpy().item()),noise,seed));return {'metric':Tensor(np.zeros((8,8,2)))}
        native=SimpleNamespace(TopomapPolicy=Parent,encode_candidates=encode,diffuse_condition=decode,torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda:None)),CONFIG={'num_diffusion_iters':10})
        request=dict(hmm_odometry_total_m=0.,hmm_odometry_tick=72,observation_pose=[.1,.2,.3])
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'nodes.json';file.write_text(json.dumps(dict(nodes=[dict(node_id=i,world_pose=[i*.4,0,0]) for i in range(14)])))
            policy=worker.make_policy(native,lambda:request)(file);noise=object();_,a=policy.infer(None,[],noise,17)
            request.update(hmm_odometry_total_m=.01,hmm_odometry_tick=144,observation_pose=[.11,.2,.4]);_,b=policy.infer(None,[],noise,19)
            self.assertEqual(b['hmm']['transition_model'],'SIGN');self.assertEqual(b['hmm']['model_sha256'],config.MODEL_SHA256)
            self.assertEqual(b['hmm']['odometry_xy_m'],[.11,.2]);self.assertEqual(b['hmm']['odometry_tick'],144)
            self.assertIs(calls[0][1],noise);self.assertEqual([c[2] for c in calls],[17,19]);self.assertEqual([c[0] for c in calls],[a['selected_subgoal_id'],b['selected_subgoal_id']]);json.dumps(b,allow_nan=False)
    def test_all18_config_order_runtime_unchanged_except_transition(self):
        from nomad_phase59p import config as old,runtime as old_runtime
        self.assertEqual(config.registered_order(),old.registered_order());self.assertEqual(config.protocol()['placements'],old.protocol()['placements'])
        self.assertIs(runtime.install,old_runtime.install);self.assertIs(runtime.run_without_oracle,old_runtime.run_without_oracle)
        for j in config.registered_order():
            c=config.runtime_config(j['method'],j['index'],90,j['scene']);before=old.runtime_config(j['method'],j['index'],90,j['scene'])
            before['phase59p_transition']='SIGN';self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase60p')},before)
            self.assertEqual(c['phase60p_sigma2'],config.load_model()['sigma2']);json.dumps(c,allow_nan=False)
    def test_actual_launcher18_and_model_failure_before_launch(self):
        class Boundary(Exception):pass
        self.assertEqual(len(campaign.jobs()),18)
        for j in campaign.jobs():
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No process allowed')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            args=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            with patch.object(sys,'argv',args),self.assertRaises(Boundary):fn()
            with patch('subprocess.Popen',return_value=SimpleNamespace()) as popen:
                proc=launch.Processes();proc.Popen(['python','-m','nomad_isaac.worker']);self.assertIn('nomad_phase60p.worker',popen.call_args.args[0])
                proc.Popen(['isaac',str(config.ROOT/'research/nomad_phase26/simulator.py')]);self.assertIn(str(config.HERE/'simulator.py'),popen.call_args.args[0])
        with patch.object(sys,'argv',args),patch.object(config,'load_model',side_effect=ValueError('model_sha256 mismatch')),self.assertRaisesRegex(ValueError,'model_sha256'):fn()
    def test_SIGN_audit_uses_new_transition_but_frozen_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'model').mkdir();nodes=[dict(node_id=i,world_pose=[i,0,0]) for i in range(5)]
            manifest=root/'manifest.json';manifest.write_text(json.dumps(dict(nodes=nodes)))
            (root/'scenario.json').write_text(json.dumps(dict(topomap_manifest=str(manifest),phase16_scene='SLW',seed_offset=2270000)))
            (root/'summary.json').write_text(json.dumps(dict(final_pose=[.1,0,0])))
            loc=localization.Localization([n['world_pose'] for n in nodes]);events=[]
            for i,x in enumerate([0.,.1,0.]):
                start,end=loc.window();selection=loc.select([0.]+[100.]*(end-start),i*.1,[x,0])
                events.append(dict(id=i,observation_pose=[x,0,0],observation_sim_s=i/72,hmm_odometry_total_m=i*.1,hmm_odometry_tick=i,topomap=selection))
            file=root/'model/inference.jsonl';file.write_text(''.join(json.dumps(e)+'\n' for e in events))
            with patch.object(metrics.m43,'frozen_audit',return_value=dict(declared_arrival=False)) as outcome:
                result=metrics.sign_audit(root);outcome.assert_called_once_with(root)
            self.assertEqual(len(result['node_errors']),3)
            events[-1]['topomap']['hmm']['transition_mean_nodes']+=.01;file.write_text(''.join(json.dumps(e)+'\n' for e in events))
            with patch.object(metrics.m43,'frozen_audit',return_value=dict(declared_arrival=False)),self.assertRaises(AssertionError):metrics.sign_audit(root)
    def test_stage_report_force_adds_ignored_png_real_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);subprocess.run(['git','init','--quiet'],cwd=root,check=True)
            (root/'.gitignore').write_text('*.png\n');doc=root/'docs/report.md';doc.parent.mkdir();doc.write_text('# fixture\n')
            out=root/'results/phase60p';(out/'figures').mkdir(parents=True);(out/'summary.json').write_text('{}\n');png=out/'figures/run.png';png.write_bytes(b'PNG publication plumbing fixture')
            self.assertEqual(subprocess.run(['git','check-ignore','-q',str(png.relative_to(root))],cwd=root).returncode,0)
            report.stage_report(doc,out,root)
            staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=root,text=True)
            self.assertIn('results/phase60p/figures/run.png',staged);self.assertIn('docs/report.md',staged)
    def test_three_phase_report_pair_columns_preparation_no_log_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();baselines={}
            for phase in ('Phase58','Phase59'):
                f=root/(phase+'.json');f.write_text(json.dumps([dict(scene='SLW',index=227,method='CUT',technical_validation='PASS',success=True,stop_distance_m=.4)]));baselines[phase]=f
            for i,j in enumerate(config.registered_order()):(root/'metrics'/f'{i}.json').write_text(json.dumps(dict(j,key=str(i),technical_validation='FAIL',classification='TECHNICAL_FAILURE',success=False)))
            with patch.object(report,'BASELINES',baselines),patch.object(report,'localization_metrics',side_effect=AssertionError('No real log replay in prep')),patch.object(figures,'generate',return_value=[]) as fig:
                doc=report.generate(root,root/'out',root/'report.md',prepare_only=True)
            self.assertEqual(len(fig.call_args.args[0]),18);self.assertIn('Phase58_success',doc.read_text());self.assertIn('Phase59_success',doc.read_text());self.assertIn(config.MODEL_SHA256,doc.read_text())
            self.assertEqual(json.loads((root/'out/status.json').read_text())['completed'],18)
if __name__=='__main__':unittest.main()
