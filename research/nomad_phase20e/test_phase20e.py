import json,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace,MappingProxyType
from unittest.mock import patch
import numpy as np
from .trigger import obstacle_ahead,ConditionalNoProgress
from .config import runtime_config
from .campaign import plan_jobs


def field(points):
    h=.01;origin=np.array([-2.,-2.]);occ=np.zeros((501,501),bool)
    for q in points:
        ix,iy=np.rint((np.asarray(q)-origin)/h).astype(int);occ[iy,ix]=True
    return SimpleNamespace(occupied=occ,origin=origin,h=h,metadata=dict(frame_id=0,sim_s=3.,publication_monotonic_ns=0))


class Tests(unittest.TestCase):
    def test_rectangle_occupied_and_empty(self):
        for q,expected in [([.5,0],True),([1.,.2],True),([.5,.21],False),([1.01,0],False),([-.01,0],False)]:
            self.assertEqual(obstacle_ahead(field([q]),[0,0,1.8],[1,0])['obstacle_ahead'],expected)
        self.assertFalse(obstacle_ahead(field([]),[0,0,0],[1,0])['obstacle_ahead'])
    def test_world_translation_and_reference_direction(self):
        # u_ref, not robot yaw, sets the rectangle orientation.
        self.assertTrue(obstacle_ahead(field([[1.1,1.5]]),[1,1,0],[0,1])['obstacle_ahead'])
        self.assertFalse(obstacle_ahead(field([[1.21,1.5]]),[1,1,0],[0,1])['obstacle_ahead'])
        self.assertTrue(obstacle_ahead(field([[.6,.6]]),[.1,.1,-2],np.array([1,1])/np.sqrt(2))['obstacle_ahead'])
    def test_trigger_and_existing_cooldown(self):
        log=[];f=field([]);owner=SimpleNamespace(suppress_trigger_tick=-1,depth_maps=SimpleNamespace(snapshot=lambda:f),drecord=lambda event,**kw:log.append(dict(event=event,**kw)))
        n=ConditionalNoProgress(owner);poses=np.zeros((721,3));self.assertFalse(n.check(poses,216,np.array([1.,0.]))[0]);self.assertEqual(log[-1]['reason'],'NO_OBSTACLE_AHEAD')
        f=field([[.5,0]]);self.assertTrue(n.check(poses,224,np.array([1.,0.]))[0]);self.assertEqual(log[-1]['reason'],'OBSTACLE_AHEAD')
        n.started();self.assertFalse(n.check(poses,232,np.array([1.,0.]))[0]);n.ended(4.)
        self.assertFalse(n.check(poses,432,np.array([1.,0.]))[0]);self.assertTrue(n.check(poses,504,np.array([1.,0.]))[0])
        self.assertFalse(n.check(poses,512,np.array([1.,0.]),True)[0])
    def test_reuse_and_R2_submission(self):
        from .runtime import Execution
        from nomad_phase20d.runtime import Execution as Previous
        from nomad_phase19r.test_repair import synthetic
        self.assertIs(Execution._normal_apply.__code__,Previous._normal_apply.__code__);self.assertIs(Execution.collect_repair,Previous.collect_repair)
        self.assertIs(Execution.detour_control,Previous.detour_control);self.assertIs(Execution.apply,Previous.apply)
        class StubWorker:
            def __init__(self,out):self.jobs=[]
            def busy(self):return False
            def poll(self):return None
            def submit(self,job,snapshot):self.jobs.append(job)
            def close(self):pass
        with tempfile.TemporaryDirectory() as d,patch('nomad_phase20d.runtime.Worker',StubWorker):
            out=Path(d);ex=Execution('M3_DETOUR',out);f=synthetic(True);f.metadata=MappingProxyType(dict(frame_id=0,sim_s=0.,publication_monotonic_ns=0,file='/unused'))
            ex.depth_maps=SimpleNamespace(snapshot=lambda:f);core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.);ex.integrate_record(core.pose,core.pose)
            xy=np.c_[np.linspace(0,1.4,8),np.zeros(8)];switch=dict(id=0,observation_pose=[0,0,0],observation_sim_s=0.,overnight_metric_samples=np.repeat(xy[None],8,axis=0).tolist())
            try:
                ex.apply(core,dict(valid=True,monotonic_ns=time.monotonic_ns(),simulation_time_s=0.),switch)
                self.assertTrue(switch['phase16']['selection']['all_unsafe']);self.assertEqual(len(ex.repair_worker.jobs),1)
            finally:ex.close()
    def test_plan_and_labels_and_figures(self):
        from .report import groups,paired,decision,render
        from .visualize import passage_summary
        jobs=plan_jobs(Path('/tmp/phase20e-'+'x'*100));self.assertEqual(len(jobs),12);self.assertEqual([j['index'] for j in jobs],[i for i in range(89,95) for _ in range(2)])
        rng=np.random.default_rng(20261104);self.assertEqual([j['method'] for j in jobs],[str(m) for i in range(89,95) for m in rng.permutation(['M1_ROTATE','M3_DETOUR'])])
        self.assertTrue(all(j['socket_bytes']<100 and j['scene']=='L2' and j['seed_offset']==10000*j['index'] for j in jobs))
        self.assertEqual(runtime_config('M1_ROTATE',89)['blockage_center_y_m'],0.)
        records=[dict(scene='L2',index=i,method=m,technical_validation='PASS',classification='SUCCESS',success=True,passed_box=True,box_passage_time_s=10 if m=='M1_ROTATE' else 9,goal_time_s=40 if m=='M1_ROTATE' else 39,output='/missing') for i in range(89,95) for m in ('M1_ROTATE','M3_DETOUR')]
        self.assertEqual(decision(groups(records),paired(records))['label'],'DETOUR_PASSES_FASTER')
        same=[{**r,'box_passage_time_s':10} for r in records];self.assertEqual(decision(groups(same),paired(same))['label'],'DETOUR_MIXED')
        helps=[{**r,'success':not(r['method']=='M1_ROTATE' and r['index']<91)} for r in records];self.assertEqual(decision(groups(helps),paired(helps))['label'],'DETOUR_HELPS')
        worse=[{**r,'success':not(r['method']=='M3_DETOUR' and r['index']<91)} for r in records];self.assertEqual(decision(groups(worse),paired(worse))['label'],'DETOUR_WORSE')
        none=[{**r,'passed_box':False,'box_passage_time_s':None} for r in records];self.assertEqual(decision(groups(none),paired(none))['label'],'DETOUR_MIXED')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);render(records,p/'out',p/'report.md',False);passage_summary(paired(records),p/'out')
            self.assertIn('DETOUR_PASSES_FASTER',(p/'report.md').read_text());self.assertTrue((p/'out/passage_summary.png').exists())

if __name__=='__main__':unittest.main()
