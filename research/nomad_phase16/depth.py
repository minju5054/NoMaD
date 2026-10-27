"""Only allocation bounds differ; the frozen V1 update/snapshot implementation is inherited."""
import queue,threading
from pathlib import Path
from nomad_phase15b.depth import DepthMapThread as Base,Snapshot
from nomad_phase15.occupancy import make_field,ray_kernel
from .config import protocol

class DepthMapThread(Base):
    def __init__(self,out,camera,offset):
        self.out=Path(out)/'depth';self.out.mkdir();self.camera=camera;self.offset=offset
        ray_kernel();self.field=make_field(protocol()['depth_bounds_m'],'V1')
        empty=Snapshot(self.field,dict(frame_id=-1,sim_s=0.,capture_end_monotonic_ns=0,publication_monotonic_ns=0,empty_unknown=True,file=str(self.out/'snapshot_initial.npz')))
        empty.save(empty.metadata['file']);self.latest=empty
        self.queue=queue.Queue();self.lock=threading.Lock();self.error=None;self.count=0
        self.log=(self.out/'updates.jsonl').open('x')
        self.thread=threading.Thread(target=self.run,name='phase16-depth-v1',daemon=True);self.thread.start()
