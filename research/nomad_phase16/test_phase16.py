import copy,json,tempfile,unittest,signal
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from nomad_isaac.common import ROOT,local_to_world
from nomad_isaac.socket_path import validate_socket_path,socket_path_for_run
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase0.chunk_execution import protocol as pp_protocol
from nomad_phase12.methods import hermite_splice,TemporalTargets
from nomad_phase15.depth_sdf import DepthSDF
from nomad_phase15b.depth import Snapshot,evaluate_samples
from .config import METHODS,SAFE,scene
from .execution import fallback,stop_command,SafeExecution,filter_ensemble
from .geometry import rect,grid_path,path_safety,corridor_clearance,reference_path
from .campaign import plan_jobs
from .report import judgments

class Field:
    error_bound=0.
    def query(self,points):return np.full(len(points),.10),np.zeros_like(points)

class Tests(unittest.TestCase):
    def test_fallback_geometry_and_deceleration(self):
        p=np.array([[0.,0.],[.5,0.]])
        self.assertEqual(fallback(p,[0,0,0],Field())[0],'KEEP_ACTIVE')
        self.assertEqual(fallback(p,[.4,0,0],Field())[0],'STOP_WAIT')
        self.assertEqual(fallback(None,[0,0,0],Field())[0],'STOP_WAIT')
        v=.3
        for _ in range(6):
            next_v,w=stop_command(v);self.assertLessEqual(v-next_v,.5/9+1e-12);self.assertEqual(w,0);v=next_v
        self.assertAlmostEqual(v,0.,places=12)
    def test_scene_geometry_and_lc_rectangle(self):
        for name in ('SL','LC','CL'):
            c=scene(name);p,diag=grid_path(c);s=path_safety(p,c)
            self.assertGreaterEqual(s['obstacle_clearance_m'],.02-1e-10);self.assertGreater(s['corridor_clearance_m'],0)
            self.assertAlmostEqual(diag['length_m'],c['oracle_shortest_grid_length_m'])
            reference=json.loads((ROOT/c['reference_file']).read_text());s=path_safety(np.array(reference['world_xy']),c)
            self.assertGreaterEqual(min(s['obstacle_clearance_m'],s['corridor_clearance_m'])+.09,.25-1e-8)
            self.assertAlmostEqual(np.linalg.norm(np.diff(reference['world_xy'],axis=0),axis=1).sum(),c['reference_length_m'])
        c=scene('LC');self.assertEqual(rect(c),(-1.,4.2,-1.,4.2))
        self.assertAlmostEqual(corridor_clearance([0,-.9,0],[0,-.9,0],0,0,0,c['corridor'],.09),.01-1e-12)
        self.assertLess(corridor_clearance([0,-.92,0],[0,-.92,0],0,0,0,c['corridor'],.09),0.)
    def test_matrix_and_socket_names(self):
        jobs=plan_jobs(ROOT.parent/'artifacts/isaac6/phase16_multiscene_01')
        self.assertEqual(len(jobs),108);self.assertEqual(len(METHODS),6);self.assertNotIn('SELECT+GRAPH',METHODS)
        for j in jobs:self.assertLess(j['socket_bytes'],100)
        for m in METHODS:
            self.assertLess(validate_socket_path(socket_path_for_run(ROOT.parent/'artifacts/isaac6/phase16_preflight_01'/f'SL_902_D750_{m}')),100)
    def test_selected_hermite_and_te_kernels(self):
        # Use one actual saved FRESH; no inference or scene geometry is consulted.
        run=ROOT.parent/'artifacts/isaac6/phase15b_depth_02/S0_47_D750_FRESHEST-SAFE'
        e=json.loads((run/'events.jsonl').read_text().splitlines()[1])
        ctr=next(json.loads(l) for l in (run/'controller.jsonl').read_text().splitlines() if json.loads(l)['simulation_time_s']==e['application_sim_s'])
        f=DepthSDF([-4,-3.5,8,6.2]);f.values[:]=.5
        snapshot=Snapshot(f,dict(file='synthetic',frame_id=0,sim_s=0.))
        worlds=np.array([local_to_world(np.array(x),e['observation_pose']) for x in e['overnight_metric_samples']]);selected,detail=evaluate_samples(worlds,e['agent_pose_at_switch'],snapshot)
        for method in (METHODS[1],METHODS[2]):
            with tempfile.TemporaryDirectory() as tmp:
                obj=SafeExecution(method,Path(tmp));obj.depth_maps=SimpleNamespace(snapshot=lambda:snapshot)
                core=SimpleNamespace(pose=np.array(e['agent_pose_at_switch']),v=.2,w=0.,latest={'id':e['id']},applied_id=e['id'])
                refresh,switch=copy.deepcopy(ctr),copy.deepcopy(e);obj.apply(core,refresh,switch)
                self.assertEqual(switch['phase16']['selection']['selected_sample'],detail['selected_sample'])
                if method==METHODS[1]:np.testing.assert_array_equal(obj.follower.path.points,hermite_splice(selected,core.pose)[0])
                else:
                    expected=TemporalTargets();expected.push(selected,e['id'],e['received_monotonic_ns']);diag,meta=expected.control(core.pose,ctr['monotonic_ns'])
                    np.testing.assert_allclose([refresh['pure_pursuit']['target_x_m'],refresh['pure_pursuit']['target_y_m']],[diag['target_x_m'],diag['target_y_m']])
                    self.assertEqual(refresh['phase16_ensemble']['chunk_ids'],meta['chunk_ids'])
                self.assertEqual(obj.mode,'NORMAL');obj.close()
    def test_new_comparison_indices(self):
        gs=[]
        for sc in ('SL','ALL'):
            for m in METHODS:gs.append(dict(scene=sc,method=m,valid=6,planned=6,success=5 if m.endswith('GRAPH-depth') else 2,safety_failures=0,sdf_active_fraction=.06))
        d=judgments(gs,['SL'])
        self.assertEqual(d['5_vs_1'],'PILOT_GRAPH_HELPS');self.assertEqual(d['5_vs_2'],'PILOT_GRAPH_HELPS');self.assertEqual(d['5_vs_3'],'PILOT_GRAPH_HELPS')
    def test_te_keeps_only_passing_chunks_and_reweights(self):
        class SplitField:
            error_bound=0.
            def query(self,q):return np.where(q[:,1]<.05,.10,-.10),np.zeros_like(q)
        te=TemporalTargets();now=1_000_000_000
        for identifier,y,received in ((1,0.,100_000_000),(2,.1,200_000_000),(3,-.1,900_000_000)):
            te.push(np.array([[0.,y],[.8,y]]),identifier,received)
        kept_objects=[te.chunks[0]['follower'],te.chunks[2]['follower']]
        mode,detail=filter_ensemble(te,[0,0,0],SplitField(),now)
        self.assertEqual(mode,'KEEP_ACTIVE');self.assertEqual(detail['removed_chunk_ids'],[2]);self.assertEqual(detail['kept_chunk_ids'],[1,3])
        self.assertEqual([x['follower'] for x in te.chunks],kept_objects)
        _,meta=te.control([0,0,0],now);expected=np.exp(-.5*np.arange(2));expected/=expected.sum()
        np.testing.assert_array_equal(meta['weights'],expected)
        # No new chunk was inserted, reception timestamps and one-second expiry stay unchanged.
        mode,detail=filter_ensemble(te,[0,0,0],SplitField(),1_900_000_000)
        self.assertEqual(mode,'STOP_WAIT');self.assertEqual(detail['expired_chunk_count'],2)
    def test_narrow_reference_uses_centerline_exception(self):
        c=copy.deepcopy(scene('SL'));c['corridor'].update(xmin=-1.,xmax=2.,half_width=.23)
        c['goal_pose']=[.8,0.,0.];c['obstacles']=[dict(id='FarBox',center_xy_m=[1.8,.15],size_xyz_m=[.1,.1,.8])]
        path,diag=reference_path(c)
        self.assertTrue(diag['narrow_centerline_used']);np.testing.assert_allclose(path[:,1],0.,atol=1e-12)
        self.assertAlmostEqual(diag['minimum_center_distance_m'],.23,places=10)
    def test_keep_active_preserves_follower_and_relabels_fresh_clock(self):
        class SplitField:
            error_bound=0.;metadata={'file':'synthetic','sim_s':0.,'frame_id':0}
            def query(self,q):return np.where(q[:,1]<0.,.5,-.1),np.zeros_like(q)
            def unknown_fraction(self,q):return 0.
        run=ROOT.parent/'artifacts/isaac6/phase15b_depth_02/S0_47_D750_FRESHEST-SAFE'
        e=json.loads((run/'events.jsonl').read_text().splitlines()[1]);ctr=next(json.loads(l) for l in (run/'controller.jsonl').read_text().splitlines() if json.loads(l)['simulation_time_s']==e['application_sim_s'])
        e['observation_pose']=[0,0,0];e['overnight_metric_samples']=[np.column_stack([np.linspace(.1,.8,8),np.full(8,.25)]).tolist()]*8
        with tempfile.TemporaryDirectory() as tmp:
            obj=SafeExecution(METHODS[0],Path(tmp));obj.depth_maps=SimpleNamespace(snapshot=lambda:SplitField())
            old=PurePursuit([[0.,-.1],[1.,-.1]],pp_protocol()['follower']);old.progress=.1
            obj.follower=old;obj.path_source_id=0;obj.active_id=0;obj.last_command=[.2,0.]
            core=SimpleNamespace(pose=np.array([0.,0.,0.]),v=.2,w=0.,latest={'id':e['id']},applied_id=e['id'])
            obj.apply(core,ctr,e)
            self.assertEqual(obj.mode,'KEEP_ACTIVE');self.assertIs(obj.follower,old);self.assertEqual(obj.path_source_id,0)
            self.assertEqual(obj.active_id,e['id']);self.assertGreaterEqual(old.progress,.1);self.assertGreater(core.v,0);self.assertLess(core.w,0);obj.close()
    def test_campaign_resume_does_not_retry_interrupted_run(self):
        from . import campaign as module
        launches=[];interrupted=[False]
        class FakeProcess:
            pid=123456789
            def __init__(self,argv,**kwargs):
                self.argv=argv;self.output=None
                if 'nomad_phase16.launch' in argv:
                    self.output=Path(argv[argv.index('--output')+1]);self.output.mkdir(parents=True,exist_ok=False)
                    launches.append(str(self.output));self.main='/main/' in str(self.output)
                    if argv[argv.index('--mode')+1]=='reference':
                        (self.output/'topomap').mkdir();(self.output/'topomap/manifest.json').write_text('{}')
            def wait(self,**kwargs):
                if self.output and self.main and not interrupted[0]:interrupted[0]=True;raise KeyboardInterrupt
                if self.output:(self.output/'launch_complete.json').write_text('{}')
                return 0
        def audit(path):
            success='SL_' in Path(path).name
            return dict(technical_validation='PASS',success=success,classification='SUCCESS' if success else 'STUCK')
        def git(args,**kwargs):return '' if 'diff' in args else 'synthetic-sha\n'
        handlers={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGINT)}
        try:
            with tempfile.TemporaryDirectory() as tmp,patch.object(module.subprocess,'Popen',FakeProcess),patch.object(module.subprocess,'check_output',git),patch('nomad_isaac.topomap.load_map',side_effect=lambda path:([None]*(18 if path.parents[1].name=='SL' else 15),[])),patch('nomad_phase16.metrics.audit',side_effect=audit):
                root=Path(tmp)/'campaign'
                with self.assertRaises(KeyboardInterrupt):module.campaign(root)
                module.campaign(root)
                self.assertEqual(len(launches),len(set(launches)))
                self.assertEqual(sum('/main/' in x for x in launches),36)
                records=[json.loads(f.read_text()) for f in (root/'metrics').glob('main_*.json')]
                self.assertEqual(len(records),36);self.assertEqual(sum(r['classification']=='TECHNICAL_FAILURE' for r in records),1)
                before=len(launches);module.campaign(root);self.assertEqual(len(launches),before)
        finally:
            for s,h in handlers.items():signal.signal(s,h)

if __name__=='__main__':unittest.main()
