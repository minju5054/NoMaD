"""Synthetic occupancy semantics plus a saved-frame V0 regression check."""
import csv
import hashlib
import json
from pathlib import Path
import unittest
import numpy as np
from nomad_isaac.common import ROOT
from .depth_sdf import bounds_from_config
from .occupancy import LogOddsSDF, make_field


class OccupancyTests(unittest.TestCase):
    def test_bresenham_clears_false_hit(self):
        field=LogOddsSDF([0,-1,2,1],'V1')
        hit=np.array([[1.,0.,.5]]);floor=np.array([[1.5,0.,0.]])
        for _ in range(2):field.accumulate(hit,np.array([1.]),[0,0,.5])
        self.assertTrue(field.occupied[100,100])
        for _ in range(3):field.accumulate(floor,np.array([1.6]),[0,0,.5])
        self.assertFalse(field.occupied[100,100])
        self.assertTrue(field.observed[100,150])
        self.assertLess(field.log_odds_hundredths[100,150],0)
        self.assertFalse(field.observed[120,150])

    def test_frame_count_thresholds_range_and_clamps(self):
        points=np.tile([[1.,0.,.5]],(20,1));ranges=np.ones(20)
        field=LogOddsSDF([0,-1,4,1],'V2')
        field.accumulate(points,ranges,[0,0,.5])
        self.assertEqual(field.occupied_observations[100,100],1)
        self.assertEqual(field.log_odds_hundredths[100,100],85)
        self.assertFalse(field.occupied[100,100])
        field.accumulate(points,ranges,[0,0,.5]);self.assertFalse(field.occupied[100,100])
        field.accumulate(points,ranges,[0,0,.5]);self.assertTrue(field.occupied[100,100])
        for _ in range(10):field.accumulate(points,ranges,[0,0,.5])
        self.assertEqual(field.log_odds_hundredths[100,100],350)
        v3=LogOddsSDF([0,-1,4,1],'V3')
        for _ in range(3):v3.accumulate(np.array([[2.5,0,.5]]),np.array([2.5]),[0,0,.5])
        self.assertFalse(v3.occupied.any());self.assertEqual(v3.log_odds_hundredths[100,250],0)
        self.assertLess(v3.log_odds_hundredths[100,200],0)
        self.assertTrue(v3.observed[100,250])

    def test_hit_precedence_and_last_obstacle_reset(self):
        f=LogOddsSDF([0,-1,2,1],'V1')
        p=np.array([[1,0,.5],[1.5,0,0.]])
        f.accumulate(p,np.array([1.,1.6]),[0,0,.5])
        self.assertEqual(f.log_odds_hundredths[100,100],85)
        # No artificial occupancy from an unknown/unvisited cell.
        self.assertEqual(f.log_odds_hundredths[120,100],0)
        f.values.fill(-.09)
        from .depth_sdf import camera_to_world,intrinsics
        from .test_depth_sdf import CAM
        f.update(np.full((240,320),np.inf),intrinsics(CAM),camera_to_world([0,0,0]))
        self.assertTrue(np.all(f.values==f.empty_distance))

    def test_v0_first_saved_frame_matches_original(self):
        summary=json.loads((ROOT/'research/results/phase15a/summary.json').read_text())
        root=Path(summary['render_root']);plan=json.loads((root/'plan.json').read_text())
        source=plan['runs'][0];name=source['key']
        frames=json.loads((root/name/'frames.json').read_text())
        k=np.array(json.loads((root/'camera.json').read_text())['intrinsics'])
        with (ROOT/'research/results/phase15a/updates.csv').open() as file:
            old={r['noise']:r for r in csv.DictReader(file)
                 if r['run']==name and int(r['observation_id'])==frames[0]['observation_id']}
        with np.load(root/name/'depth.npz') as archive:
            d=archive['depth'][0];t=archive['camera_to_world'][0]
        for noise in ('none','gaussian'):
            f=make_field(bounds_from_config(source['scenario']),'V0')
            key=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)
            rng=np.random.default_rng(np.random.SeedSequence([20261026,key,frames[0]['observation_id']]))
            actual=f.update(d,k,t,noise=='gaussian',rng)
            for column in ('points','obstacle_points','occupied_cells','unknown_fraction'):
                self.assertEqual(actual[column],float(old[noise][column]))

    def test_selection_excludes_held_out_and_tie_breaks(self):
        from .occupancy_report import select_variant
        base=dict(split='selection',noise='gaussian',dangerous_fraction=.01,update_ms_p95=40,conservative_fraction=.1)
        rows=[dict(base,variant='V2'),dict(base,variant='V1'),
              dict(base,variant='V0',conservative_fraction=0,update_ms_p95=50.1),
              dict(base,variant='V3',conservative_fraction=0,dangerous_fraction=.02001),
              dict(base,variant='V4',split='judgment',conservative_fraction=0)]
        self.assertEqual(select_variant(rows)['selected_variant'],'V1')
        self.assertIsNone(select_variant(rows[2:])['selected_variant'])


if __name__=='__main__':unittest.main()
