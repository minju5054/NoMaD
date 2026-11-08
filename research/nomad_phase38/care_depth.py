"""Current depth-frame receiver at the frozen capture seam, not an SDF mapper."""
import json,threading,time
from types import MappingProxyType,SimpleNamespace
import numpy as np
from nomad_phase24.retention import full_frames
from .care import frame_obstacles

class CareFrames:
    def __init__(self,out,camera,offset):
        self.out=out/'depth';self.out.mkdir();self.camera=camera;self.offset=offset;self.lock=threading.Lock();self.full_frames=full_frames()
        self.log=(self.out/'updates.jsonl').open('x')
        empty=np.empty((0,2));empty.flags.writeable=False
        self.latest=SimpleNamespace(points_world=empty,metadata=MappingProxyType(dict(frame_id=-1,sim_s=0.,empty=True,source='CURRENT_FRAME_CARE')))
    def submit(self,depth,pose,sim_s,capture_end_ns,observation_id):
        points,detail=frame_obstacles(depth,self.camera,pose,self.offset,observation_id)
        points.flags.writeable=False;path=self.out/f'care_frame_{observation_id:04d}.npz'
        meta=dict(frame_id=int(observation_id),sim_s=float(sim_s),pose=list(map(float,pose)),capture_end_monotonic_ns=int(capture_end_ns),
            publication_monotonic_ns=time.monotonic_ns(),source='CURRENT_FRAME_CARE',file=str(path),**detail)
        snap=SimpleNamespace(points_world=points,metadata=MappingProxyType(meta))
        with self.lock:self.latest=snap
        # At most32 derived points per frame; no map, occupied cells or SDF.
        np.savez_compressed(path,points_world=points,metadata=json.dumps(meta))
        if self.full_frames:np.savez_compressed(self.out/f'depth_{observation_id:04d}.npz',depth=np.asarray(depth,dtype=np.float32),pose=np.asarray(pose))
        self.log.write(json.dumps(meta,allow_nan=False)+'\n');self.log.flush()
    def snapshot(self):
        with self.lock:return self.latest
    def close(self):self.log.close()
