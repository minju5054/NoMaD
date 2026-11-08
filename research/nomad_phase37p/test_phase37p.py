"""Offline-only tests: publisher, B predicate, launcher validation and report."""
import copy,io,json,queue,sys,tempfile,threading,unittest,subprocess,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import provenance as p
from . import runtime,config,report,launch
from nomad_phase24r.trigger import PersistentNoProgress
from nomad_phase37b.test_prov import ProvenanceTests as Fixture


class PublicationTests(unittest.TestCase):
    def test_witness_and_first_occupied_order(self):
        track=p.PublishedFree((1,6))
        info=track.update(np.array([[1,0,1,1,1,1]],bool),np.array([[0,0,1,0,0,0]],bool),
            np.array([[18,18,18,17,18,18]]),np.array([[-1,-1,18,-1,17,18]]),18)
        np.testing.assert_array_equal(track.first_confirmed_free_tick,[[18,-1,-1,-1,-1,-1]])
        json.dumps(info,allow_nan=False)
        track.update(np.ones((1,6),bool),np.zeros((1,6),bool),np.full((1,6),36),np.full((1,6),20),36)
        np.testing.assert_array_equal(track.first_confirmed_free_tick,[[18,-1,-1,-1,-1,-1]])

    def test_snapshot_immutable_storage_v2_roundtrip(self):
        field=p.ProvenMap([0,0,.2,.2]);field.observed[1,1]=True;field.last_free_tick[1,1]=18
        snap=p.ProvenSnapshot(field,dict(frame_id=1,sim_s=.25))
        before=field.values.copy();field.prov.first_confirmed_free_tick[2,2]=36
        self.assertFalse(snap.prov_confirmed_free[2,2]);self.assertTrue(snap.prov_confirmed_free[1,1])
        self.assertFalse(snap.prov_confirmed_free.flags.writeable)
        np.testing.assert_array_equal(field.values,before)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'snapshot.npz';snap.save(path)
            with np.load(path) as z:self.assertNotIn('values',z.files);self.assertIn('prov_confirmed_free',z.files)
            restored=p.ProvenSnapshot.load(path)
            for key in ('values','occupied','observed','last_free_tick','first_free_tick','first_occupied_tick','new_component_ids','prov_confirmed_free','prov_first_confirmed_free_tick'):
                np.testing.assert_array_equal(getattr(snap,key),getattr(restored,key))
            self.assertEqual(dict(restored.metadata),dict(snap.metadata))

    def test_every_publication_without_a_control_reader(self):
        pub=object.__new__(p.ProvenPublisher);pub.field=p.ProvenMap([0,0,.2,.2])
        pub.queue=queue.Queue();pub.archive_queue=queue.Queue();pub.lock=threading.Lock();pub.log=io.StringIO();pub.error=None;pub.count=0
        pub.out=Path('/tmp/not-written');pub.offset=1;pub.camera={'height_m':.5,'focal_length_mm':1,'horizontal_aperture_mm':2,'vertical_aperture_mm':1.5}
        def update(*args,frame_tick,**kw):
            f=pub.field;f.last_free_tick[1,1]=frame_tick if frame_tick==18 else 18
            f.observed[1,1]=True;f.occupied[1,1]=frame_tick==36
            if frame_tick==36:f.history.first_occupied_tick[1,1]=36
            return {}
        pub.field.update=update
        for i in (1,2):pub.queue.put((np.ones((2,2)),[0,0,0],i*.25,0,i))
        pub.queue.put(None);pub.run()
        self.assertIsNone(pub.error);self.assertEqual(pub.count,2);self.assertEqual(pub.field.prov.updates,2)
        self.assertTrue(pub.latest.prov_confirmed_free[1,1]);self.assertEqual(pub.latest.prov_first_confirmed_free_tick[1,1],18)
        for row in pub.log.getvalue().splitlines():self.assertEqual(json.loads(row)['prov_schema_version'],1)
        # Same publisher bytecode: no capture/update/queue/drop policy rewrite.
        self.assertIs(p.ProvenPublisher.run.__code__,p.OriginalPublisher.run.__code__)
        self.assertIs(p.ProvenPublisher.archive,p.OriginalPublisher.archive)


class TriggerTests(unittest.TestCase):
    def fixture(self):
        f,poses=Fixture().data();f.provenance_mask=np.ones(f.occupied.shape,bool);records=[]
        owner=SimpleNamespace(depth_maps=SimpleNamespace(snapshot=lambda:f),suppress_trigger_tick=-1,drecord=lambda event,**kw:records.append(dict(event=event,**kw)))
        return f,poses,owner,records

    def test_all_confirmed_exact_baseline_birth_direction_and_json(self):
        f,poses,owner,records=self.fixture();poses[72,2]=.1
        a=PersistentNoProgress(owner);b=runtime.ProvenNoProgress(owner)
        self.assertEqual(a.check(poses,432,[1,0]),b.check(poses,432,[1,0]))
        self.assertEqual(a.last_gate,b.last_gate);self.assertTrue(b.check(poses,432,[1,0])[0])
        self.assertEqual(b.last_gate['component']['t_new_tick'],72)
        np.testing.assert_allclose(b.last_gate['component']['u_ref'],[np.cos(.1),np.sin(.1)])
        json.dumps(records,allow_nan=False)

    def test_component_threshold_after_filter_and_original_untouched(self):
        f,poses,owner,_=self.fixture();f.provenance_mask[8,16]=False
        self.assertFalse(runtime.ProvenNoProgress(owner).check(poses,432,[1,0])[0])
        self.assertTrue(PersistentNoProgress(owner).check(poses,432,[1,0])[0])
        from nomad_phase24r.trigger import no_new_obstacle_ahead
        self.assertFalse(no_new_obstacle_ahead(f,poses[432],432,[1,0]))

    def test_busy_cooldown_blocked_unmodified(self):
        _,poses,owner,_=self.fixture()
        for mode in ('busy','cooldown_until','blocked'):
            a=PersistentNoProgress(owner);b=runtime.ProvenNoProgress(owner)
            if mode!='blocked':setattr(a,mode,True if mode=='busy' else 10.);setattr(b,mode,getattr(a,mode))
            self.assertEqual(a.check(poses,432,[1,0],mode=='blocked'),b.check(poses,432,[1,0],mode=='blocked'))
        self.assertIs(runtime.ProvenNoProgress.check.__code__,PersistentNoProgress.check.__code__)

    def test_factory_changes_only_b_object(self):
        sentinel=object();old=SimpleNamespace(no_progress=sentinel,start_detour=object(),apply_result=object())
        with patch.object(runtime.frozen,'make_execution',return_value=old):
            self.assertIs(runtime.make_execution({'phase37p_method':'OURS'},None).no_progress,sentinel)
            before=vars(old).copy();runtime.make_execution({'phase37p_method':'OURS+PROV'},None)
            self.assertIsInstance(old.no_progress,runtime.ProvenNoProgress)
            for k in ('start_detour','apply_result'):self.assertIs(getattr(old,k),before[k])


class WiringTests(unittest.TestCase):
    def test_actual_install_hooks_isolated_without_worker_creation(self):
        code='''
import sys
from nomad_phase37p.config import runtime_config
from nomad_phase37p.runtime import install,ProvenPublisher
from nomad_phase24r.depth import DepthMapThread as Original
from nomad_phase24r.trigger import no_new_obstacle_ahead
method=sys.argv[1];install(runtime_config(method,215,90,'L2'))
import nomad_phase15b.depth as depth
import nomad_phase20f.runtime as handover
assert depth.DepthMapThread is (ProvenPublisher if method=='OURS+PROV' else Original)
assert handover.no_new_obstacle_ahead is no_new_obstacle_ahead
assert 'isaacsim' not in sys.modules
'''
        for method in config.METHODS:
            result=subprocess.run(['/usr/bin/python3','-c',code,method],cwd=config.ROOT,
                env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr[-2000:])

    def test_config_only_registration_changes(self):
        from nomad_phase35.config import runtime_config as frozen
        baseline=frozen('OURS',212,90,'H2');a=config.runtime_config('OURS',215,90,'H2');b=config.runtime_config('OURS+PROV',215,90,'H2')
        self.assertEqual({k for k in a if a[k]!=b[k]},{'phase37p_method'})
        allowed={'seed_offset','run_id','phase35_index','phase29_index','phase32_index','phase37p','phase37p_index','phase37p_method'}
        self.assertFalse({k for k in a if a.get(k)!=baseline.get(k)}-allowed)
        json.dumps([a,b],allow_nan=False)

    def test_twenty_jobs_forty_short_unique_sockets(self):
        from nomad_phase26 import campaign as base
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        with patch.object(base,'protocol',config.protocol):jobs=base.jobs(config.RUN_ROOT)
        self.assertEqual(len(jobs),20);self.assertEqual(len({(j['scene'],j['index'],j['method']) for j in jobs}),20)
        sockets=[socket_path_for_run(Path(f)) for j in jobs for f in j['outputs']]
        self.assertEqual(len(set(sockets)),40);self.assertTrue(all(validate_socket_path(s)<100 for s in sockets))
        self.assertEqual([{'scene':j['scene'],'index':j['index'],'method':j['method']} for j in jobs],config.registered_order()[1])

    def test_launcher_argument_validation_only_all_jobs(self):
        class ReachedSocket(Exception):pass
        def stop(_):raise ReachedSocket()
        fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**k:self.fail('Must never spawn')))
        fn.__globals__['socket_path_for_run']=stop
        for row in config.registered_order()[1]:
            args=['launch','--scene',row['scene'],'--method',row['method'],'--index',str(row['index']),'--output',str(config.RUN_ROOT/'main'/'test'/'attempt1')]
            with patch.object(sys,'argv',args),self.assertRaises(ReachedSocket):fn()
        self.assertFalse(config.RUN_ROOT.exists())

    def test_routes_disk_and_simulator_import_barrier(self):
        from .campaign import Routes,capacity
        self.assertEqual(Routes.route(['nomad_phase26.launch','nomad_phase26.report']),['nomad_phase37p.launch','nomad_phase37p.report'])
        import shutil
        for free,enough in ((29_999_999_999,False),(30_000_000_000,True)):
            with patch.object(shutil,'disk_usage',return_value=SimpleNamespace(free=free)):
                self.assertEqual(capacity(config.RUN_ROOT,[])['enough'],enough)
        source=(config.ROOT/'research/nomad_phase26/simulator.py').read_text()
        self.assertLess(source.index('exec(compile(ast.Module(body=prefix'),source.index('from nomad_phase26.execution import install'))
        renderer=(config.ROOT/'research/nomad_isaac/simulator.py').read_text()
        self.assertLess(renderer.index('SimulationApp('),renderer.index('def main('))


class ReportTests(unittest.TestCase):
    def rows(self):
        return [dict(row,technical_validation='PASS',success=True,collision=False,goal_time_s=40.,mean_speed_m_s=.2,stopped_fraction=.1,
            trigger_counts={'B':2},trigger_oracle_counts={'B':{'BOX_AHEAD':2}},detour_applied_count=1,output='/no-data') for row in config.registered_order()[1]]

    def test_decision_strict_success_and_collision_boundaries(self):
        rows=self.rows();self.assertEqual(report.decide(rows)['label'],'NOT_PROMISING')
        next(r for r in rows if r['method']=='OURS')['success']=False
        self.assertEqual(report.decide(rows)['label'],'PROMISING')
        next(r for r in rows if r['method']=='OURS+PROV')['collision']=True
        self.assertEqual(report.decide(rows)['label'],'NOT_PROMISING')
        rows=self.rows();rows[0]['technical_validation']='FAIL';rows[0].pop('collision')
        self.assertFalse(report.decide(rows)['evidence_valid'])

    def test_fake_report_and_missing_data_figures(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'metrics').mkdir();rows=self.rows()
            for i,row in enumerate(rows):(root/'metrics'/f'{i}.json').write_text(json.dumps(row))
            doc,figures=report.generate(root,root/'results',root/'report.md')
            self.assertEqual(len(figures),10);self.assertTrue(all(x['skipped'] for x in figures))
            self.assertIn('PROV_NOT_ESTABLISHED_MISSING_HISTORY',doc.read_text())
            for file in ('decision.json','summary.csv','triggers.csv','paired.csv','failures.json'):self.assertTrue((root/'results'/file).exists())
            # One real stored trajectory and a missing partner: no simulations.
            from .figures import pair_plot
            data=json.loads((config.OUT/'preparation/replay.json').read_text())['cases'][0]
            row=dict(rows[0],method='OURS',scene='H1',output=data['output'])
            result=pair_plot([row],'H1',215,root/'one_valid.png')
            self.assertFalse(result['skipped']);self.assertEqual(result['missing_methods'],['OURS+PROV'])


if __name__=='__main__':unittest.main()
