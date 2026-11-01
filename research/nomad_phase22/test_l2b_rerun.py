"""Regression of the real spawn-monitor constructor; no planner changes."""
import json,tempfile,unittest
from pathlib import Path
import numpy as np
from nomad_isaac.clearance import single_obstacle_config,ObstacleMonitor
from .drive_config import runtime_config,place
from .drive_geometry import monitor,OrientedMonitor,point_gap,swept_gap

class Tests(unittest.TestCase):
    def test_oriented_spawn_creates_distinct_metadata_and_checks_swept_pose(self):
        for index in (121,122):
            c=runtime_config('P0_ASTAR',index,90,'L2B');p=np.array([2.5,0.,0.]);b=place(c,p)['obstacle']
            with tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp);m=monitor(single_obstacle_config(c,b),out)
                self.assertIsInstance(m,OrientedMonitor)
                original=(out/'obstacle_geometry.json').read_bytes()
                self.assertTrue((out/'oriented_obstacle_geometry.json').exists())
                row=m.observe_interval(p,p,0.,0.,0.,0.)
                self.assertAlmostEqual(row['lower_m'],point_gap(p[:2],b,.09),places=8)
                self.assertFalse(row['geometric_overlap'])
                row=m.observe_interval([*b['center_xy_m'],0.],[*b['center_xy_m'],0.],0.,0.,1.,0.)
                self.assertTrue(row['geometric_overlap']);self.assertEqual(m.stop_reason,'geometric_collision')
                m.finish(False);self.assertEqual(original,(out/'obstacle_geometry.json').read_bytes())
    def test_l2_keeps_original_monitor_class(self):
        c=runtime_config('P0_ASTAR',121,90,'L2');b=place(c,[2.,0.,0.])['obstacle']
        with tempfile.TemporaryDirectory() as tmp:
            m=monitor(single_obstacle_config(c,b),Path(tmp));self.assertIs(type(m),ObstacleMonitor);m.finish(False)
    def test_campaign_only_l2b_and_merged_report_reuses_l2(self):
        from .l2b_rerun import ns,registration
        from .l2b_report import merged_records
        from .drive_report import included_pairs,summarize,pairs,decisions
        r=registration()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);jobs=ns['jobs'](root);self.assertEqual(len(jobs),12)
            self.assertTrue(all(j['scene']=='L2B' for j in jobs));self.assertEqual({j['index'] for j in jobs},{121,122,123,124})
            self.assertTrue(all(len(j['outputs'])==2 for j in jobs))
            (root/'metrics').mkdir();(root/'plan.json').write_text(json.dumps(dict(jobs=jobs)))
            for j in jobs:
                fake=dict(scene=j['scene'],method=j['method'],index=j['index'],output=str(root/'absent'),classification='TECHNICAL_FAILURE',technical_validation='FAIL',success=False)
                (root/'metrics'/f"{j['key']}.json").write_text(json.dumps(fake))
            records=merged_records(root);self.assertEqual(len(records),24)
            for original,row in zip(r['reuse_L2'],records[:12]):
                original=json.loads(Path(original['metrics_file']).read_text())
                for key,value in original.items():self.assertEqual(row[key],value)
            included,excluded=included_pairs(records);self.assertEqual(included,{('L2',k) for k in range(121,125)})
            self.assertEqual(len(excluded),4)
            verdict=decisions(summarize(records,included),pairs(records,included));self.assertEqual(verdict['final'],'REFINE_INCONCLUSIVE')

if __name__=='__main__':unittest.main()
