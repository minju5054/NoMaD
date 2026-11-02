"""Recover missing free timestamps from original static depth; never change V1 values."""
import json
from pathlib import Path
import numpy as np
from nomad_phase15.occupancy import LogOddsSDF
from nomad_phase15.depth_sdf import intrinsics
from nomad_phase15b.depth import Snapshot
from nomad_phase20d.recent import RecentSnapshot
from nomad_isaac.common import sha256_file

def ensure(cases,out):
    mapping={};groups={}
    for c in cases:groups.setdefault(c['run'],[]).append(c)
    for run,cc in groups.items():
        targets={c['snapshot_file'] for c in cc}
        with np.load(next(iter(targets))) as z:has_recent='last_free_tick' in z.files
        if has_recent:
            mapping.update({f:f for f in targets});continue
        root=Path(run);directory=Path(out)/root.name;directory.mkdir(parents=True,exist_ok=True)
        targets_by_frame={int(Snapshot.load(f).metadata['frame_id']):f for f in targets}
        files={frame:directory/f'recent_{frame:04d}.npz' for frame in targets_by_frame}
        if all(f.exists() for f in files.values()):mapping.update({targets_by_frame[i]:str(f) for i,f in files.items()});continue
        base=Snapshot.load(next(iter(targets)));upper=base.origin+(np.array(base.values.shape[::-1])-1)*base.h
        bounds=np.round(np.r_[base.origin,upper],8);field=LogOddsSDF(bounds,'V1',base.h,base.radius);assert field.values.shape==base.values.shape
        last=np.full(base.values.shape,-1,dtype=np.int32);config=json.loads((root/'scenario.json').read_text());updates=[json.loads(x) for x in (root/'depth/updates.jsonl').read_text().splitlines()]
        for update in updates:
            frame=update['frame_id']
            if frame>max(targets_by_frame):break
            file=root/f'depth/depth_{frame:04d}.npz'
            with np.load(file) as z:depth=z['depth'];transform=z['camera_to_world']
            rng=np.random.default_rng(np.random.SeedSequence([20261027,config['seed_offset'],frame]))
            field.update(depth,intrinsics(config['camera']),transform,True,rng)
            last[field._free.astype(bool)&~field._hits.astype(bool)]=round(update['sim_s']*72)
            if frame in targets_by_frame:
                original=Snapshot.load(targets_by_frame[frame]);np.testing.assert_array_equal(original.occupied,field.occupied);np.testing.assert_array_equal(original.observed,field.observed)
                new=object.__new__(RecentSnapshot);new.__dict__.update(original.__dict__);new.last_free_tick=last.copy();new.save(files[frame],compressed=True)
                mapping[targets_by_frame[frame]]=str(files[frame])
        if -1 in targets_by_frame:
            original=Snapshot.load(targets_by_frame[-1]);new=object.__new__(RecentSnapshot);new.__dict__.update(original.__dict__);new.last_free_tick=np.full(original.values.shape,-1,np.int32);new.save(files[-1],compressed=False);mapping[targets_by_frame[-1]]=str(files[-1])
        assert all(f in mapping for f in targets),run
    return mapping
