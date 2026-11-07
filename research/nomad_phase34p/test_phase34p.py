import copy,io,json,tempfile,time,unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase32.test_phase32 import WiringTests
from nomad_phase20c.detour_known import radial_reference
from .runtime import Execution,BASE,VARIANT
from .routing import ORIGINAL,BYPASS,AST_PROOF

class RoutingTests(unittest.TestCase):
    def fake(self,method,folder,busy=False):
        o=WiringTests().fake_execution();o.__class__=Execution;o.phase34_method=method;o.phase34_log=io.StringIO();o.dlog=io.StringIO();o.apps=io.StringIO()
        o.next_repair=3;o.detour_count=0;o.detour_sent=False;o.pending_field=None;o.await_repair_fresh=False;o.detour_outcome_pending=None;o.suppress_trigger_tick=-1
        o.path_source_id=None;o.path_kind=None;o.active_id=1;o.jobs_dir=Path(folder);o.out=Path(folder)
        B=np.array([2.,.4,.2]);o.history=np.linspace(np.zeros(3),B,73).tolist();o.last_command=[.1,0.];o.plant.actual_w=0.
        o.recovery.base.awaiting_outcome=False;o.recovery.base.eligible=lambda v:True
        o.recovery.base.start=lambda *a:(_ for _ in ()).throw(AssertionError('Pending planner must block recovery'))
        o.no_progress=SimpleNamespace(started=lambda:None,check=lambda *a:(False,0.,'BLOCKED'))
        o.collect_repair=lambda *a:None;o.commands=[];o.write_command=lambda *a:o.commands.append(a[-2]);o.submitted=[]
        o.repair_worker=SimpleNamespace(busy=lambda:busy,submit=lambda job,field:o.submitted.append(copy.deepcopy(job)),poll=lambda:None)
        o.depth_maps.snapshot().metadata={'frame_id':1,'sim_s':1.,'publication_monotonic_ns':1}
        core=SimpleNamespace(pose=B,v=.1,w=0.);refresh=dict(simulation_time_s=1.,monotonic_ns=1,valid=True)
        switch=dict(id=2,observation_pose=B.tolist(),observation_sim_s=.25,overnight_metric_samples=np.tile(np.c_[np.linspace(0,1,8),np.zeros(8)][None],(8,1,1)).tolist())
        return o,core,refresh,switch
    def unsafe(self,worlds,pose,field):return worlds[0],dict(all_unsafe=True,selected_sample=0,candidates=[dict(safe=False)]*8)
    def test_bypass_dispatches_only_original_R3_and_preserves_stop_command(self):
        with tempfile.TemporaryDirectory() as td:
            base,bc,br,bs=self.fake(BASE,td);variant,vc,vr,vs=self.fake(VARIANT,td)
            with patch.dict(ORIGINAL.__globals__,evaluate_samples=self.unsafe),patch.dict(BYPASS.__globals__,evaluate_samples=self.unsafe):
                base._normal_apply(bc,br,bs);variant._normal_apply(vc,vr,vs)
            self.assertEqual(len(base.submitted),1);self.assertNotIn('kind',base.submitted[0]);self.assertIsNotNone(base.repair_pending)
            self.assertEqual(len(variant.submitted),1);job=variant.submitted[0];self.assertEqual(job['kind'],'R3');self.assertIsNone(variant.repair_pending)
            expected,_=radial_reference(np.asarray(variant.history),72);np.testing.assert_array_equal(job['u_ref'],expected)
            self.assertEqual((bc.v,bc.w),(vc.v,vc.w));self.assertEqual(job['B'],vc.pose.tolist());self.assertEqual(job['trigger'],'A')
            self.assertEqual(vs['phase16']['fallback_mode'],'REPAIR_WAIT');self.assertEqual(variant.detour_count,1)
            for stream in (variant.phase34_log,variant.dlog,variant.apps,base.repair_log):
                for line in stream.getvalue().splitlines():json.dumps(json.loads(line),allow_nan=False)
    def test_only_two_AST_changes_and_restore_identity(self):
        self.assertEqual(AST_PROOF['original_ast_sha256'],AST_PROOF['restored_ast_sha256']);self.assertEqual(len(AST_PROOF['changes']),2)
    def test_B_uses_the_same_frozen_method(self):
        from nomad_phase32.runtime import Execution as Frozen
        o=object.__new__(Execution);o.detour=None;o.phase34_method=VARIANT;o.phase34_log=io.StringIO()
        with patch.object(Frozen,'start_detour') as original:o.start_detour('core','refresh','B',.1)
        original.assert_called_once_with('core','refresh','B',.1);self.assertEqual(o.phase34_log.getvalue(),'')
    def test_A_direction_short_displacement_keeps_start_heading(self):
        poses=np.array([[0,0,np.pi/2],[.2,.1,0.]])
        u,info=radial_reference(poses,1);np.testing.assert_allclose(u,[0,1],atol=1e-12);self.assertEqual(info['source'],'START_HEADING')
    def test_worker_busy_keeps_frozen_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            o,c,r,s=self.fake(VARIANT,td,True);called=[];o.recovery.base.eligible=lambda v:False
            def fallback(*a):called.append(True);o.mode='STOP_WAIT';return {}
            o.use_fallback=fallback
            with patch.dict(BYPASS.__globals__,evaluate_samples=self.unsafe):o._normal_apply(c,r,s)
            self.assertTrue(called);self.assertFalse(o.submitted);self.assertIsNone(o.detour)

class PreparationTests(unittest.TestCase):
    def test_frozen_numerical_pool_reads_v2_R2_and_R3_inputs(self):
        from .worker import Worker
        from nomad_phase33p.storage import install
        from nomad_phase15b.depth import Snapshot
        from nomad_phase20d.recent import RecentSnapshot
        from nomad_phase20f.history import HistorySnapshot
        from nomad_phase32o.test_exec_cert import field
        classes=(Snapshot,RecentSnapshot,HistorySnapshot);saved={c:(c.__dict__['save'],c.__dict__['load']) for c in classes}
        worker=None
        try:
            install();s=field();s.observed=np.ones_like(s.occupied);s.last_free_tick=np.zeros(s.occupied.shape,np.int32);s.metadata={'frame_id':0,'sim_s':0.}
            with tempfile.TemporaryDirectory() as td:
                worker=Worker(Path(td))
                for ident,kind in enumerate(('R2','R3')):
                    job=dict(kind=kind,job_id=ident,B=[0.,0.,0.],u_ref=[1.,0.],evaluation_tick=0,dispatch_ns=time.monotonic_ns(),
                             samples_world=np.tile(np.c_[np.linspace(0,1,8),np.zeros(8)][None],(8,1,1)).tolist())
                    worker.submit(job,s);deadline=time.monotonic()+30;result=None
                    while result is None and time.monotonic()<deadline:result=worker.poll();time.sleep(.01)
                    self.assertIsNotNone(result);self.assertNotIn('error',result);self.assertEqual(len(result['results']),8 if kind=='R2' else 7)
                    with np.load(Path(td)/'repair_jobs'/f'input_{ident:04d}.npz') as z:self.assertNotIn('values',z.files)
                worker.close();worker=None
        finally:
            if worker is not None:worker.close()
            for cls,(save,load) in saved.items():cls.save=save;cls.load=load
    def test_configs_only_change_registered_seed_identifiers(self):
        from .config import runtime_config,registered_order
        from nomad_phase29.config import runtime_config as original
        for j in registered_order()[1]:
            c=runtime_config(j['method'],j['index'],90,j['scene']);base=original('C0-NA',201,90,j['scene'])
            for key in ('phase32','phase32_method','phase32_index','phase34','phase34_method','phase34_index','storage_version'):c.pop(key)
            c.update(seed_offset=2010000,run_id=f"{j['scene']}_201",phase29_index=201);self.assertEqual(c,base)
    def test_twenty_launcher_argument_checks_without_process(self):
        from . import config,launch
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        class Boundary(Exception):pass
        for j in config.registered_order()[1]:
            for attempt in (1,2):
                out=config.RUN_ROOT/'main'/f"{j['scene']}_{j['index']:03d}_{j['method']}"/f'attempt{attempt}'
                self.assertLess(validate_socket_path(socket_path_for_run(out)),100)
            with ExitStack() as stack:
                base=launch.old.base
                for key in ('subprocess','verify','METHODS','SCENES','write_json','atomic_json'):stack.enter_context(patch.object(base,key,getattr(base,key)))
                stack.enter_context(patch.dict(launch._main.__globals__,plan=lambda:dict(possible=True,worker_cpu=7,driver_cpus=[0]),pin=lambda x:dict(passed=True)))
                stack.enter_context(patch.object(launch.old.os,'sched_setaffinity'));proc=stack.enter_context(patch.object(launch.subprocess,'Popen'))
                stack.enter_context(patch.object(base,'socket_path_for_run',side_effect=Boundary))
                stack.enter_context(patch('sys.argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',str(out)]))
                with self.assertRaises(Boundary):launch.main()
                proc.assert_not_called();self.assertFalse(out.exists())
    def test_simulator_import_order(self):
        from .config import ROOT
        s=(ROOT/'research/nomad_phase26/simulator.py').read_text().replace('from nomad_phase26.config','from nomad_phase34p.config').replace('from nomad_phase26.execution','from nomad_phase34p.runtime')
        compile(s,'<phase34-app-first>','exec');self.assertLess(s.index('# SimulationApp is now initialized.'),s.index('from nomad_phase34p.runtime'))
    def test_storage_worker_routes_only_pool(self):
        from .worker import Processes
        with patch('nomad_phase34p.worker.subprocess.Popen') as child:
            Processes().Popen(['/usr/bin/python3','-m','nomad_phase20d.pool']);self.assertEqual(child.call_args.args[0],['/usr/bin/python3','-m','nomad_phase34p.pool'])
    def test_decision_and_report_fake_twenty_runs(self):
        from . import config,report
        rows=[dict(j,technical_validation='PASS',success=True,collision=False,goal_time_s=30.,stopped_fraction=.1,trigger_A_count=2,R2_calls=0,A_R3_attempts=1,A_R3_success=1,A_R3_failure=0,A_R3_EC_reject_jobs=0,A_R3_EC_reject_candidates=0,detour_execution_s=2.,collision_execution_state=None) for j in config.registered_order()[1]]
        self.assertEqual(report.decide(rows)['label'],'PROMISING')
        bad=copy.deepcopy(rows);next(r for r in bad if r['method']==config.METHODS[1])['success']=False;self.assertEqual(report.decide(bad)['label'],'NOT_PROMISING')
        self.assertEqual(report.decide(rows[:-1])['label'],'NOT_PROMISING')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'run/metrics').mkdir(parents=True);(root/'docs').mkdir()
            for i,r in enumerate(rows):(root/'run/metrics'/f'{i}.json').write_text(json.dumps(r))
            with patch.object(report,'ROOT',root),patch.object(report,'OUT',root/'results'):
                doc=report.generate(root/'run');self.assertIn('PROMISING',doc.read_text());self.assertTrue((root/'results/paired.csv').exists())
    def test_collision_state_uses_original_contact_interval(self):
        from .report import collision_state
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'phase20_commands.jsonl').write_text(json.dumps(dict(time_s=1.,source='REPAIR_WAIT',repair_active=False,command=[.1,0],pending_job=4))+'\n')
            (p/'phase20d_commands.jsonl').write_text(json.dumps(dict(time_s=1.,detour_state='WAIT'))+'\n')
            summary=dict(simulation_duration_s=2.,obstacle_evaluation=dict(first_contact=dict(interval_start_s=1.01,detected_sim_s=1.02)))
            self.assertEqual(collision_state(p,summary,True)['state'],'R3_WAIT')

if __name__=='__main__':unittest.main()
