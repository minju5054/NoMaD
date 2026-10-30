import json,tempfile,unittest
from pathlib import Path
import numpy as np
from nomad_phase20d.recent import RecentMap
from nomad_phase15.depth_sdf import intrinsics,camera_to_world
from .history import HistoryMap,HistorySnapshot

class Tests(unittest.TestCase):
    def test_history_is_observational_only_and_snapshot_immutable(self):
        # Saved depth frame; original/new mapping consume the identical depth/noise seed.
        records=json.loads(Path('research/results/phase20e/runs.json').read_text());run=Path(records[0]['output'])
        update=json.loads((run/'depth/updates.jsonl').read_text().splitlines()[0]);config=json.loads((run/'scenario.json').read_text())
        with np.load(run/f"depth/depth_{update['frame_id']:04d}.npz") as z:depth=z['depth'].copy();transform=z['camera_to_world'].copy()
        old=RecentMap([-4,-3.5,12,6.2]);new=HistoryMap([-4,-3.5,12,6.2])
        seed=[20261027,config['seed_offset'],update['frame_id']]
        for f in (old,new):f.update(depth,intrinsics(config['camera']),transform,True,np.random.default_rng(np.random.SeedSequence(seed)),frame_tick=round(update['sim_s']*72))
        for name in ('values','occupied','observed','last_free_tick'):np.testing.assert_array_equal(getattr(old,name),getattr(new,name))
        snap=HistorySnapshot(new,update);saved=snap.first_free_tick.copy();new.history.first_free_tick[:]=999
        np.testing.assert_array_equal(snap.first_free_tick,saved);self.assertFalse(snap.first_free_tick.flags.writeable)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.npz';snap.save(p);again=HistorySnapshot.load(p)
            for name in ('values','occupied','first_free_tick','first_occupied_tick','new_component_ids'):np.testing.assert_array_equal(getattr(snap,name),getattr(again,name))
if __name__=='__main__':unittest.main()
