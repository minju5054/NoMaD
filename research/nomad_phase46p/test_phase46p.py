import copy,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import config,runtime,campaign,launch,report
from .triggers import classify,box_distance


class Tests(unittest.TestCase):
    def test_all_unsafe_matches_no_detour_fallback_and_B_still_uses_frozen_R3(self):
        from nomad_phase38.ec_normal import RTCWithEC
        from nomad_phase24r.trigger import PersistentNoProgress
        from nomad_phase32o.test_exec_cert import field
        from nomad_phase20f.runtime import Execution as FrozenB
        f=field();f.observed=np.ones(f.occupied.shape,bool)
        f.metadata=dict(frame_id=1,sim_s=0.,publication_monotonic_ns=0)
        submitted=[]
        worker=SimpleNamespace(poll=lambda:None,busy=lambda:False,submit=lambda job,snap:submitted.append(job),close=lambda:None)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'new').mkdir();(root/'old').mkdir()
            with patch('nomad_phase20d.runtime.Worker',return_value=worker),patch('nomad_phase20f.runtime.NewObstacleNoProgress',PersistentNoProgress):
                new=runtime.Execution('C0-NA+EC',root/'new')
            old=RTCWithEC(root/'old')
            try:
                cores=[]
                for obj in (new,old):
                    obj.depth_maps=SimpleNamespace(snapshot=lambda:f);obj.snapshot=f;obj.history=[np.zeros(3)]
                    core=SimpleNamespace(pose=np.zeros(3),v=.2,w=0.);cores.append(core)
                    obj.new_path([[0,0],[1,0]],core,dict(simulation_time_s=0.,monotonic_ns=1),0,'SAFE')
                    obj.last_command=[.2,0.]
                bank=np.repeat(np.array([[[0.,0],[.5,0],[1,0]]]),8,axis=0)
                switch=dict(id=1,observation_pose=[0,0,0],observation_sim_s=0.,overnight_metric_samples=bank.tolist(),received_monotonic_ns=1)
                def unsafe(*a):return bank[0],dict(all_unsafe=True,selected_sample=0,candidates=[dict(safe=False)]*8)
                for obj,core in zip((new,old),cores):
                    refresh=dict(simulation_time_s=0.,monotonic_ns=time.monotonic_ns(),valid=True)
                    with patch.dict(runtime.Execution._normal_apply.__globals__,evaluate_samples=unsafe),patch('nomad_phase20.runtime.evaluate_samples',unsafe):
                        obj.apply(core,refresh,copy.deepcopy(switch))
                    json.dumps(refresh,allow_nan=False)
                self.assertEqual(new.last_command,old.last_command);self.assertEqual(new.mode,old.mode)
                self.assertEqual(submitted,[]);self.assertIsNone(new.repair_pending)
                with self.assertRaises(AssertionError):new.start_detour(cores[0],{},'A',None)
                self.assertIs(runtime.Execution.detour_control,FrozenB.detour_control)
                # Read-only telemetry must preserve the exact B predicate and
                # record the actual field, not a later archived replacement.
                f.new_component_ids=np.zeros(f.occupied.shape,dtype=int);f.component_births={1:0}
                center=np.rint((np.array([.6,0])-f.origin)/f.h).astype(int);x,y=center
                f.occupied[y,x:x+5]=True;f.new_component_ids[y,x:x+5]=1
                new.history=[np.zeros(3)]*217;new.suppress_trigger_tick=-1
                plain=PersistentNoProgress(new)
                expected=plain.check(np.asarray(new.history),216,np.array([1.,0.]))
                actual=new.no_progress.check(np.asarray(new.history),216,np.array([1.,0.]))
                self.assertEqual(actual,expected);self.assertTrue(actual[0])
                new.start_detour(cores[0],dict(simulation_time_s=3.),'B',actual[1])
                self.assertEqual(len(submitted),1);self.assertEqual(submitted[0]['kind'],'R3');self.assertEqual(submitted[0]['trigger'],'B')
                triggers=[json.loads(s) for s in (root/'new/detour.jsonl').read_text().splitlines() if json.loads(s)['event']=='TRIGGER']
                evidence=triggers[0]['trigger_component_evidence'];self.assertEqual(evidence['frame_id'],1)
                self.assertEqual(len(evidence['cell_centers_world']),5);json.dumps(triggers,allow_nan=False)
            finally:new.close();old.close()
        self.assertEqual(runtime.BWorker.__init__,runtime.GraphWorker.__init__)
        with self.assertRaises(AssertionError):runtime.BWorker.submit(object(),{'kind':'R2'},None)

    def test_oracle_footprint_association_spawn_time_and_missing_evidence(self):
        box=dict(id='box',center_xy_m=[1.,0.],size_xyz_m=[.4,1.2,.8])
        boxes=[dict(time_s=5.,box=box)]
        self.assertEqual(classify([[.7,.5]],boxes,5.)['classification'],'BOX')
        self.assertEqual(classify([[.49,.5]],boxes,5.)['classification'],'NON_BOX')
        self.assertEqual(classify(None,boxes,5.)['classification'],'UNMEASURED')
        self.assertEqual(classify(None,boxes,4.)['classification'],'NON_BOX')
        self.assertAlmostEqual(box_distance([[.2,0]],dict(box,yaw_deg=90.)),.2)
        self.assertEqual(classify([[.5,0]],boxes,5.)['classification'],'BOX')

    def test_fifteen_configs_args_no_execution_and_fixed_gate(self):
        from nomad_phase45p.config import runtime_config as old
        class Boundary(Exception):pass
        plan=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(plan),15)
        for j in plan:
            c=config.runtime_config(j['method'],j['index'],90,j['scene'])
            self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase46p')},old('OURS+HMM',j['index'],90,j['scene']))
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**kw:self.fail('No process')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            argv=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            with patch.object(sys,'argv',argv),self.assertRaises(Boundary):fn()
        code='''
from nomad_phase46p import campaign as c
from nomad_phase46p.config import RUN_ROOT
def halt():
 assert len(c.frozen.base.jobs(RUN_ROOT))==15
 assert not c.frozen.base.protocol()['smoke']['enabled']
 assert c.frozen.base.run_job.__globals__['subprocess'].__class__ is c.Routes
 print('NO_EXECUTION')
c.frozen.base.main=halt
c.main()
assert not RUN_ROOT.exists()
'''
        r=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr[-1800:])
        new=[dict(j,technical_validation='PASS',success=i<11,collision=False) for i,j in enumerate(config.protocol()['main_order'])]
        old=[dict(r,success=i<9) for i,r in enumerate(new)]
        self.assertEqual(report.decide(new,old)['label'],'B_ONLY_OK')
        old[9]['success']=True;self.assertEqual(report.decide(new,old)['label'],'B_ONLY_NOT_OK')
        self.assertEqual(report.decide(new[:-1],old)['label'],'NOT_EVALUATED')

    def test_report_tables_and_false_trigger_outcomes(self):
        baseline=json.loads((config.OUT/'preparation/baselines.json').read_text())
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,j in enumerate(config.protocol()['main_order']):
                r=dict(j,technical_validation='PASS',success=True,wrong_stop=False,collision=False,
                    planner_wait_s=1.,stop_wait_s=2.,total_stopped_s=3.,r3_installations=1,
                    trigger_b_analysis=[dict(job_id=0,classification='NON_BOX',r3_installed=True,r3_disposition='ACCEPTED',
                        r3_end_reason='ENDPOINT',run_success=True,run_collision=False,run_termination='declared_arrival')])
                (root/'metrics'/f'{i}.json').write_text(json.dumps(r))
            doc=report.generate(root,root/'results',root/'report.md',baseline)
            self.assertTrue(all(not line or line.startswith('|') for line in doc.read_text().splitlines()))
            self.assertIn('NON_BOX',doc.read_text());self.assertTrue((root/'results/false_trigger_events.csv').exists())


if __name__=='__main__':unittest.main()
