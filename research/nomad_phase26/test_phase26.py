import unittest,math,tempfile,json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from .config import runtime_config
from .scenes import triggered,place,MultiSuddenMonitor
from .decisions import classify,exclusions
from nomad_phase24r.geometry import verify_bounds

class Tests(unittest.TestCase):
    def test_h1_spawn_exit_and_gap(self):
        c=runtime_config('C0',95,level='H1')
        self.assertFalse(triggered(c,[3.3,1.19,math.pi/2],0));self.assertTrue(triggered(c,[3.3,1.2,math.pi/2],0))
        p=place(c,[3.3,1.2,math.pi/2],0);self.assertEqual(p['status'],'PLACED')
        b=p['obstacle'];self.assertAlmostEqual(b['center_xy_m'][1]-b['size_xyz_m'][1]/2-1.2-.09,1.)
        self.assertGreaterEqual(b['center_xy_m'][0]-.5-2.4,.6)
    def test_h2_requires_first_passage_and_alternates_offsets(self):
        c=runtime_config('C0',95,level='H2')
        self.assertTrue(triggered(c,[2.01,0,0],0));self.assertFalse(triggered(c,[5.01,0,0],1,False))
        self.assertTrue(triggered(c,[5.01,0,0],1,True));self.assertFalse(triggered(c,[5.11,0,0],1,True))
        self.assertEqual(place(c,[2,0,0],0)['obstacle']['center_xy_m'][1],.3)
        self.assertEqual(place(c,[5,0,0],1)['obstacle']['center_xy_m'][1],-.3)
    def test_second_box_keeps_first_evaluation_and_geometry(self):
        c=runtime_config('C0',95,level='H2')
        with tempfile.TemporaryDirectory() as name:
            m=MultiSuddenMonitor(c,Path(name));m.observe_tick(0,[2,0,0],[2,0,0],0,0,-1,False,0)
            self.assertEqual(len(m.children),1)
            m.children[0]['monitor'].crossing=dict(side='-Y',simulation_time_s=.1,pose=[4,0,0])
            m.observe_tick(1,[5,0,0],[5,0,0],0,0,-1,False,1)
            self.assertEqual(len(m.obstacle['phase26_boxes']),2)
            r=m.finish(False);self.assertEqual(len(r['boxes']),2);self.assertIsNone(r['evaluation']['passage'])
            self.assertIn('avoidance_success',r['evaluation']);self.assertFalse(r['evaluation']['avoidance_success'])
    def test_walls_refuse_fixed_slw_geometry(self):
        c=runtime_config('C0',95,level='SLW')
        bounds=dict(LeftWall=[[-1,.9,0],[6,1,2]],RightWall=[[-1,-1,0],[6,-.9,2]],EndWall=[[6,0,0],[6.1,1,2]],StartWall=[[-1.1,0,0],[-1,1,2]])
        self.assertEqual(verify_bounds(c,bounds)['status'],'PASS')
        bounds['LeftWall'][0][1]=1.5
        with self.assertRaises(ValueError):verify_bounds(c,bounds)
    def test_c0_l2_frozen_runtime_and_b0_no_depth(self):
        from nomad_phase24r2.online_config import runtime_config as old
        a=runtime_config('C0',201);b=old('C0',151)
        for k in set(a)|set(b):
            if k in ('phase26','phase26_method','phase24r2','seed_offset','run_id'):continue
            self.assertEqual(a.get(k),b.get(k),k)
        self.assertFalse(runtime_config('B0_NOMAD_RAW',201)['depth_camera'])
        self.assertEqual(runtime_config('B2_SAFE_RTC',201)['overnight_method'],'RTC-hard')
    def test_astar_replaces_r3_only(self):
        from . import astar_pool
        with patch.object(astar_pool,'r2_job',return_value='unchanged') as spy:
            self.assertEqual(astar_pool.evaluate(None,dict(kind='R2')),'unchanged');spy.assert_called_once()
    def test_labels_and_reference_exclusions(self):
        methods=['C0','B1_SAFE_TE','B2_SAFE_RTC','B3_SAFE_ROTATE','B4_ASTAR']
        rr=[dict(group=g,method=m,goal=6 if m=='C0' else 3,collision=0) for g in ('SUDDEN','STATIC') for m in methods]
        self.assertEqual(classify(rr)['label'],'PILOT_SUPPORTS')
        rr[0]['collision']=1;self.assertEqual(classify(rr)['C0_vs_ASTAR'],'BETTER')
        rr[0]['collision']=0
        rr[0]['goal']=0;self.assertEqual(classify(rr)['label'],'PILOT_AGAINST')
        rr[0]['goal']=3;self.assertEqual(classify(rr)['label'],'PILOT_MIXED')
        self.assertEqual(exclusions([dict(scene='H1',index=201,method='B0_NOMAD_RAW',technical_validation='FAIL')]),[])
        self.assertEqual(exclusions([dict(scene='H1',index=201,method='C0',technical_validation='FAIL')]),[('H1',201)])
    def test_fake_sixty_run_report(self):
        from .config import protocol
        from .report import generate
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'metrics').mkdir()
            for j in protocol()['main_order']:
                r=dict(j,technical_validation='PASS',success=True,collision=False,obstacle_collision=False,wall_overlap=False,corridor=False,
                    box_passage=j['scene'] in ('H1','H2','L2'),recovery_count=0,detour_trigger_count=0)
                (root/'metrics'/f"{j['scene']}_{j['index']}_{j['method']}.json").write_text(json.dumps(r))
            result=generate(root,root/'out',root/'report.md')
            self.assertEqual(result['label'],'PILOT_MIXED');self.assertEqual(result['C0_vs_ASTAR'],'NONINFERIOR')
            self.assertIn('Draft expansion only',(root/'report.md').read_text())
if __name__=='__main__':unittest.main()
