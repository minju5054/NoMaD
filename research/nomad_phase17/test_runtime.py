import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import ROOT,integrate_se2
from nomad_phase15b.depth import Snapshot
from nomad_phase16.geometry import path_safety
from .config import METHODS,scene,protocol
from .recovery import Recovery,free_rays,ANGLE


class OpenField:
    def query(self,p):return np.ones(len(p)),np.zeros_like(p)


class RuntimeTests(unittest.TestCase):
    def test_trigger_direction_limit_and_rotation(self):
        r=Recovery();r.decision('STOP_WAIT');self.assertFalse(r.eligible(0))
        r.decision('STOP_WAIT');self.assertFalse(r.eligible(.01));self.assertTrue(r.eligible(.009))
        class Asymmetric:
            def query(self,p):return np.where((p[:,1]>0)&(p[:,0]>.4),0.,1.),np.zeros_like(p)
        self.assertEqual(free_rays(Asymmetric(),[0,0,0])[0],-1)
        self.assertEqual(free_rays(OpenField(),[0,0,0])[0],1)
        c=scene('CL');pose=np.array([0.,0.,0.]);initial=path_safety(np.repeat(pose[None,:2],2,axis=0),c)
        for _ in range(12):
            r.state='NORMAL';r.streak=2;self.assertTrue(r.eligible(0));r.start(OpenField(),pose)
            start=pose.copy()
            while r.state=='RECOVER_ROTATE':
                v,w=r.interval_command();pose=integrate_se2(pose,v,w,1/72);r.integrated(w)
                np.testing.assert_array_equal(pose[:2],start[:2])
                self.assertEqual(path_safety(np.repeat(pose[None,:2],2,axis=0),c),initial)
            self.assertAlmostEqual((pose[2]-start[2]+np.pi)%(2*np.pi)-np.pi,ANGLE,places=10)
        r.state='NORMAL';r.streak=2;self.assertFalse(r.eligible(0))
        r.decision('KEEP_ACTIVE');self.assertEqual(r.streak,0)

    def test_saved_stop_decisions_drive_real_wrapper(self):
        from .execution import SafeExecution
        run=ROOT.parent/'artifacts/isaac6/phase16_multiscene_01/main/CL_058_D750_FRESHEST-SAFE+GRAPH-depth'
        events=[json.loads(x) for x in (run/'events.jsonl').read_text().splitlines()]
        stops=[e for e in events if e['phase16']['fallback_mode']=='STOP_WAIT'][:2]
        controls={x['simulation_time_s']:x for x in map(json.loads,(run/'controller.jsonl').read_text().splitlines())}
        with tempfile.TemporaryDirectory() as tmp:
            obj=SafeExecution(METHODS[0],Path(tmp))
            for e in stops:
                e=copy.deepcopy(e);control=copy.deepcopy(controls[e['application_sim_s']])
                snap=Snapshot.load(e['phase16']['selection']['snapshot']['file']);obj.depth_maps=SimpleNamespace(snapshot=lambda:snap)
                core=SimpleNamespace(pose=np.array(e['agent_pose_at_switch']),v=0.,w=0.,latest={'id':e['id']},applied_id=e['id'])
                obj.apply(core,control,e)
            self.assertEqual(obj.recovery.state,'RECOVER_ROTATE');self.assertEqual(core.v,0)
            start=core.pose.copy()
            for tick in range(1,127):obj.plant.integrate(core,tick)
            self.assertEqual(obj.recovery.state,'WAIT_FRESH');np.testing.assert_array_equal(core.pose[:2],start[:2])
            self.assertAlmostEqual(abs((core.pose[2]-start[2]+np.pi)%(2*np.pi)-np.pi),ANGLE,places=10)
            obj.close()

    def test_matrix_assets_and_socket_gate(self):
        from .campaign import plan_jobs
        from .config import verify_sources
        p=verify_sources();jobs=plan_jobs(ROOT.parent/'artifacts/isaac6/phase17_multiscene_01')
        self.assertEqual(len(jobs),105);self.assertEqual(len(METHODS),7)
        self.assertLess(max(j['socket_bytes'] for j in jobs),100)
        self.assertEqual({j['index'] for j in jobs},set(range(61,66)))
        self.assertTrue(all(j['seed_offset']==j['index']*10000 for j in jobs))
        c=scene('SLW')
        for b in c['obstacles']:self.assertAlmostEqual(1.8-b['size_xyz_m'][1],.8)
        frozen=json.loads((ROOT/c['reference_file']).read_text());self.assertTrue(frozen['offline_pp']['goal'])
        self.assertGreaterEqual(frozen['geometry']['minimum_center_distance_m'],.25)

    def test_pilot_judgment_and_cluster_pairs(self):
        from .report import judgments,pairs
        gs=[dict(scene='ALL',method=m,valid=10,planned=10,success=8 if m==METHODS[5] else 6,no_detour_success=6,safety_failures=0) for m in METHODS]
        labels=judgments(gs,['LC','CL']);self.assertEqual(labels['P1_CLEARANCE_TERM'],'PILOT_CLR_HELPS')
        self.assertEqual(labels['P2_6_vs_2'],'PILOT_BETTER');self.assertEqual(labels['threshold'],2)
        rr=[dict(scene=sc,index=i,method=m,technical_validation='PASS',checkpoint_time_s=20 if m==METHODS[5] else 21) for sc in ('LC','CL') for i in (61,62) for m in METHODS]
        allpairs=[r for r in pairs(rr,['LC','CL']) if r['scene']=='ALL']
        self.assertTrue(all(r['n']==4 and r['ci95_s']==[-1.,-1.] for r in allpairs))

    def test_report_handles_all_technical_failures(self):
        from . import report
        from .campaign import write
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'campaign';out=Path(tmp)/'results';doc=Path(tmp)/'report.md'
            (root/'metrics').mkdir(parents=True);out.mkdir()
            write(root/'complete.json',{'complete':True});write(root/'gates.json',{'SLW':'NOMAD_INFEASIBLE','LC':'PASS','CL':'NOMAD_INFEASIBLE'})
            write(root/'resolved_protocol.json',{'topomaps':{}})
            for i in range(61,66):
                for m in METHODS:
                    r=dict(index=i,scene='LC',method=m,key=f'LC_{i}_{m}',output=str(root/'missing'),technical_validation='FAIL',classification='TECHNICAL_FAILURE',error='synthetic')
                    write(root/'metrics'/f'main_{r["key"]}.json',r)
            write(out/'offline_summary.json',json.loads((ROOT/'research/results/phase17/offline_summary.json').read_text()))
            with patch.object(report,'OUT',out),patch.object(report,'DOC',doc):report.render(root)
            self.assertIn('PILOT_INCONCLUSIVE',doc.read_text());self.assertTrue((out/'paired.csv').exists())


if __name__=='__main__':unittest.main()
