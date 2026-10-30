import json,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_phase20e.runtime import Execution as Previous
from nomad_phase20d.recent import RecentMap
from .history import HistoryMap,HistorySnapshot
from .runtime import Execution
from .trigger import NewObstacleNoProgress
from .config import runtime_config
from .campaign import plan_jobs

class Worker:
    def __init__(self,out):self.jobs=[]
    def busy(self):return False
    def poll(self):return None
    def submit(self,job,snapshot):self.jobs.append(job)
    def close(self):pass

class Tests(unittest.TestCase):
    def test_B_direction_and_early_end_preserves_A(self):
        with tempfile.TemporaryDirectory() as d,patch('nomad_phase20d.runtime.Worker',Worker):
            out=Path(d);ex=Execution('M3_DETOUR',out);f=HistoryMap([-2,-2,3,2]);f.observed[:]=True;f.last_free_tick[:]=216
            field=HistorySnapshot(f,dict(frame_id=0,sim_s=3.,publication_monotonic_ns=0,file='/unused'));ex.depth_maps=SimpleNamespace(snapshot=lambda:field)
            poses=np.c_[np.linspace(0,.6,217),np.zeros(217),np.zeros(217)];ex.history=list(poses);core=SimpleNamespace(pose=poses[-1].copy(),v=0.,w=0.)
            gate=dict(new_obstacle_ahead=True,component=dict(component_id=1,t_new_tick=216,u_ref=[0.,1.],direction=dict(source='TEST')),snapshot=dict(field.metadata))
            ex.no_progress.last_gate=gate;refresh=dict(valid=True,monotonic_ns=time.monotonic_ns(),simulation_time_s=3.)
            try:
                ex.start_detour(core,refresh,'B',.1);self.assertEqual(ex.detour['u_ref'],[0.,1.]);ex.detour_active=True;ex.detour.update(path=[[.6,0],[.6,1]],apply_sim_s=3.)
                ex.detour_control(core,refresh,None);self.assertIsNone(ex.detour)
                rows=[json.loads(x) for x in (out/'detour.jsonl').read_text().splitlines()]
                self.assertEqual([r['reason'] for r in rows if r['event']=='END'],['NO_NEW_OBSTACLE_AHEAD'])
                # A has no new-obstacle requirement and retains start-to-current direction.
                ex.start_detour(core,refresh,'A',None);np.testing.assert_array_equal(ex.detour['u_ref'],[1.,0.])
            finally:ex.close()
    def test_plans_and_frozen_labels(self):
        from .report import groups,paired,decision,render
        jobs=plan_jobs(Path('/tmp/phase20f-'+'x'*100));self.assertEqual(len(jobs),12)
        rng=np.random.default_rng(20261105);self.assertEqual([j['method'] for j in jobs],[str(m) for i in range(95,101) for m in rng.permutation(['M1_ROTATE','M3_DETOUR'])])
        self.assertEqual([j['index'] for j in jobs],[i for i in range(95,101) for _ in range(2)]);self.assertTrue(all(j['socket_bytes']<100 for j in jobs))
        self.assertEqual(runtime_config('M1_ROTATE',95)['blockage_center_y_m'],0.)
        records=[dict(scene='L2',index=i,method=m,technical_validation='PASS',classification='SUCCESS',success=True,passed_box=True,box_passage_time_s=10 if m=='M1_ROTATE' else 9,goal_time_s=40,output='/missing') for i in range(95,101) for m in ('M1_ROTATE','M3_DETOUR')]
        self.assertEqual(decision(groups(records),paired(records))['label'],'DETOUR_PASSES_FASTER')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);render(records,p/'out',p/'report.md',False);self.assertTrue((p/'out/cumulative.csv').exists());self.assertIn('DETOUR_PASSES_FASTER',(p/'report.md').read_text())
if __name__=='__main__':unittest.main()
