import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase42l.filter import WindowHMM
from nomad_isaac.topomap import candidate_range
from .localization import Localization
from . import config,launch,campaign,report


class Tensor:
    def __init__(self,x):self.x=np.asarray(x)
    def __getitem__(self,key):return Tensor(self.x[key])
    def detach(self):return self
    def flatten(self):return Tensor(self.x.flatten())
    def cpu(self):return self
    def numpy(self):return self.x
    def unsqueeze(self,axis):return Tensor(np.expand_dims(self.x,axis))


class Tests(unittest.TestCase):
    def test_frozen_hmm_and_map_centered_window_official_subgoal(self):
        poses=np.c_[np.arange(14)*.4,np.zeros((14,2))]
        loc=Localization(poses);reference=WindowHMM(14,loc.spacing)
        total=0.
        for change in (0.,.05,.5,.0):
            total+=change;start,end=loc.window();self.assertEqual((start,end),candidate_range(loc.closest,13,4))
            values=np.full(end-start+1,5.);values[-1]=.2
            expected,detail=reference.step(list(range(start,end+1)),values,change)
            result=loc.select(values,total)
            self.assertEqual(result['closest_node'],expected)
            self.assertEqual(result['hmm']['transition_half_width'],detail['transition_half_width'])
            self.assertEqual(result['selected_subgoal_id'],min(expected+int(values[expected-start]<3),end))
            json.dumps(result,allow_nan=False)

    def test_odometry_is_observation_tick_path_length_not_latest_or_displacement(self):
        from .odometry import ExecutionThread,Client,Phase41Thread,FrozenClient
        calls=[];plant=SimpleNamespace(last_tick=0)
        def init(self,*a,**kw):self.stage2=SimpleNamespace(plant=plant,integrate_record=lambda *a:calls.append('frozen'))
        with patch.object(Phase41Thread,'__init__',init):engine=ExecutionThread()
        positions=np.array([[0.,0,0],[.1,0,0],[0.,0,0],[.3,0,0]])
        for tick,q in enumerate(positions):
            plant.last_tick=tick;engine.stage2.integrate_record(positions[max(0,tick-1)],q)
        expected=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(positions[:,:2],axis=0),axis=1))]
        np.testing.assert_array_equal(engine.hmm_odometry,expected)
        client=object.__new__(Client);client.snapshot=engine.snapshot
        metadata=dict(observation_sim_s=2/72);arrays={'history':object()}
        with patch.object(FrozenClient,'submit',return_value=True) as submit:
            self.assertTrue(client.submit(metadata,**arrays))
        self.assertEqual(metadata['hmm_odometry_total_m'],.2);self.assertEqual(metadata['hmm_odometry_tick'],2)
        self.assertIs(submit.call_args.args[0],metadata);self.assertEqual(len(calls),4)

    def test_worker_selects_one_hmm_condition_and_keeps_decoder_rng(self):
        from .worker import make_policy
        calls=[]
        class Parent:
            def __init__(self,manifest):
                self.images=list(range(14));self.hashes=[{'rgb_sha256':str(i)} for i in self.images]
                self.closest_node=0;self.previous_subgoal=None;self.goal_node=13
        def encode(model,observations,images):
            values=np.full(len(images),10.)
            values[2 if not calls else -1]=0.
            return Tensor(np.asarray(images)[:,None]),Tensor(values),Tensor([1]),Tensor(images)
        def decode(model,condition,noise,seed):
            calls.append((int(condition.numpy().item()),noise,seed));return {'metric':Tensor(np.zeros((8,8,2)))}
        native=SimpleNamespace(TopomapPolicy=Parent,encode_candidates=encode,diffuse_condition=decode,
            torch=SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda:None)),CONFIG={'num_diffusion_iters':10})
        request={'hmm_odometry_total_m':0.,'hmm_odometry_tick':72}
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/'manifest.json';file.write_text(json.dumps({'nodes':[dict(node_id=i,world_pose=[i*.4,0,0]) for i in range(14)]}))
            policy=make_policy(native,lambda:request)(file);noise=object()
            _,a=policy.infer(None,[],noise,17);self.assertEqual((a['closest_node'],a['selected_subgoal_id']),(2,3))
            request.update(hmm_odometry_total_m=.01,hmm_odometry_tick=144)
            _,b=policy.infer(None,[],noise,19)
            self.assertEqual(b['candidate_ids'],list(range(8)));self.assertNotEqual(b['closest_node'],b['raw_argmin_node'])
            self.assertEqual([x[0] for x in calls],[a['selected_subgoal_id'],b['selected_subgoal_id']])
            self.assertIs(calls[0][1],noise);self.assertEqual([x[2] for x in calls],[17,19])
            json.dumps(b,allow_nan=False)

    def test_fifteen_frozen_configs_launch_routing_and_no_smoke_engine(self):
        from nomad_phase41.config import runtime_config as parent
        class Boundary(Exception):pass
        jobs=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(jobs),15)
        for j in jobs:
            c=config.runtime_config(j['method'],j['index'],90,j['scene'])
            self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase43p')},parent('OURS-DETOUR',j['index'],90,j['scene']))
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No simulator')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            argv=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            with patch.object(sys,'argv',argv),self.assertRaises(Boundary):fn()
        process=launch.Processes()
        with patch('subprocess.Popen',return_value=object()) as popen:
            process.Popen(['python','-m','nomad_isaac.worker'])
            self.assertEqual(popen.call_args.args[0][2],'nomad_phase43p.worker')
            process.Popen(['isaac',str(config.ROOT/'research/nomad_phase26/simulator.py')])
            self.assertEqual(popen.call_args.args[0][1],str(config.HERE/'simulator.py'))
        code='''
from nomad_phase43p import campaign as c
from nomad_phase43p.config import RUN_ROOT
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
        self.assertEqual(r.returncode,0,r.stderr[-1500:]);self.assertIn('NO_EXECUTION',r.stdout)

    def test_gate_and_tables_only_fake_report(self):
        baseline=json.loads((config.OUT/'preparation/baselines.json').read_text());rows=[]
        for i,j in enumerate(config.protocol()['main_order']):
            rows.append(dict(j,technical_validation='PASS',success=i<8,wrong_stop=8<=i<11,collision=False,
                timeout_without_declaration=i>=11,stop_distance_m=.4 if i<8 else .8 if i<11 else None,
                stop_pose=[1,0,0] if i<11 else None,final_pose=[1,0,0],termination='declared_arrival' if i<11 else 'simulation_timeout',node_errors=[]))
        self.assertEqual(report.decide(rows)['label'],'LOC_OK')
        self.assertEqual(report.decide(rows[:-1])['label'],'NOT_EVALUATED')
        rows[11]['wrong_stop']=True;self.assertEqual(report.decide(rows)['label'],'LOC_NOT_OK');rows[11]['wrong_stop']=False
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,r in enumerate(rows):(root/'metrics'/f'{i}.json').write_text(json.dumps(r))
            doc=report.generate(root,root/'results',root/'report.md',baseline)
            self.assertTrue(all(not line or line.startswith('|') for line in doc.read_text().splitlines()))
            self.assertEqual(json.loads((root/'results/decision.json').read_text())['label'],'LOC_OK')


if __name__=='__main__':unittest.main()
