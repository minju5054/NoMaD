"""Depth-history-only20F reference reconstruction; preserve source map values."""
from pathlib import Path
from types import MappingProxyType
import json
import numpy as np
from nomad_phase15b.depth import Snapshot
from nomad_phase15.occupancy import LogOddsSDF
from nomad_phase15.depth_sdf import intrinsics
from nomad_phase20f.history import CellHistory,HistoryMap,HistorySnapshot
from nomad_phase20f.trigger import choose_ahead
from nomad_phase20c.detour_known import radial_reference
from nomad_phase0.chunk_report import trace


def reconstruct(cases,out):
    """Only needed runs/frames; no new capture, inference or changed occupancy."""
    mapping={};out=Path(out)
    for run in sorted({c['run'] for c in cases}):
        cc=[c for c in cases if c['run']==run];targets={c['snapshot_file'] for c in cc};missing=[]
        for file in targets:
            with np.load(file) as z:complete='first_free_tick' in z.files
            if complete:mapping[file]=file
            else:missing.append(file)
        if not missing:continue
        directory=out/Path(run).name;directory.mkdir(parents=True,exist_ok=True)
        target={int(Snapshot.load(f).metadata['frame_id']):f for f in missing};files={frame:directory/f'history_{frame:04d}.npz' for frame in target}
        if all(f.exists() for f in files.values()):mapping.update({target[k]:str(v) for k,v in files.items()});continue
        source=Snapshot.load(missing[0]);bounds=np.round(np.r_[source.origin,source.origin+(np.array(source.values.shape[::-1])-1)*source.h],8)
        config=json.loads((Path(run)/'scenario.json').read_text());shadow=bool(config.get('phase20d') or config.get('phase20e') or config.get('phase20f'))
        field=HistoryMap(bounds,source.h,source.radius) if shadow else LogOddsSDF(bounds,'V1',source.h,source.radius)
        if not shadow:field.last_free_tick=np.full(field.values.shape,-1,np.int32);field.history=CellHistory(field.values.shape)
        updates=[json.loads(s) for s in (Path(run)/'depth/updates.jsonl').read_text().splitlines()]
        if -1 in target:
            original=Snapshot.load(target[-1]);snap=HistorySnapshot(field,dict(original.metadata));snap.save(files[-1]);mapping[target[-1]]=str(files[-1])
        for update in updates:
            frame=int(update['frame_id'])
            if frame>max(target):break
            with np.load(Path(run)/f'depth/depth_{frame:04d}.npz') as z:depth=z['depth'];transform=z['camera_to_world']
            tick=round(update['sim_s']*72);rng=np.random.default_rng(np.random.SeedSequence([20261027,config['seed_offset'],frame]))
            if shadow:field.update(depth,intrinsics(config['camera']),transform,True,rng,frame_tick=tick)
            else:
                field.update(depth,intrinsics(config['camera']),transform,True,rng)
                field.last_free_tick[field._free.astype(bool)&~field._hits.astype(bool)]=tick;field.history.update(field.last_free_tick,field.occupied,tick)
            if frame in target:
                original=Snapshot.load(target[frame]);np.testing.assert_array_equal(field.occupied,original.occupied);np.testing.assert_array_equal(field.observed,original.observed)
                np.testing.assert_array_equal(field.values,original.values)
                snap=HistorySnapshot(field,dict(original.metadata));snap.save(files[frame]);mapping[target[frame]]=str(files[frame])
        assert all(f in mapping for f in targets),run
    return mapping


def direction(case,history_file,fallback_rule):
    _,poses=trace(Path(case['run']));field=HistorySnapshot.load(history_file);chosen,detail=choose_ahead(field,poses,case['tick'],{})
    if chosen is not None:return chosen['u_ref'],dict(source='20F_COMPONENT_PREAPPEARANCE',component=chosen,**detail)
    if fallback_rule=='20F_A_RADIAL':
        u,info=radial_reference(poses,case['tick']);return u.tolist(),dict(source='20F_A_FALLBACK',fallback=info,**detail)
    if fallback_rule=='NO_DIRECTION_RECOVERY':return None,dict(source='NO_COMPONENT_DIRECTION',**detail)
    raise ValueError('Register no-component direction before execution')
