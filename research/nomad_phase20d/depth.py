"""Publish immutable in-memory maps before archival compression; never drop frames."""
import queue,threading,time,json,hashlib
from pathlib import Path
from types import MappingProxyType
import numpy as np
from nomad_phase15.depth_sdf import camera_to_world,intrinsics
from nomad_phase20.depth import BOUNDS
from .recent import RecentMap,RecentSnapshot


class DepthMapThread:
    def __init__(self,out,camera,offset):
        self.out=out/'depth';self.out.mkdir();self.camera=camera;self.offset=offset;self.field=RecentMap(BOUNDS)
        self.queue=queue.Queue();self.archive_queue=queue.Queue();self.lock=threading.Lock();self.log_lock=threading.Lock();self.error=None;self.count=0
        self.log=(self.out/'updates.jsonl').open('x');self.qlog=(self.out/'queue.jsonl').open('x');self.alog=(self.out/'archives.jsonl').open('x')
        self.latest=RecentSnapshot(self.field,dict(frame_id=-1,sim_s=0.,capture_end_monotonic_ns=0,publication_monotonic_ns=0,empty_unknown=True,file=str(self.out/'snapshot_initial.npz')))
        self.latest.save(self.latest.metadata['file'])
        self.thread=threading.Thread(target=self.run,daemon=True,name='fresh-map-publisher');self.writer=threading.Thread(target=self.archive,daemon=True,name='depth-archive-writer')
        self.writer.start();self.thread.start()
    def qrecord(self,event,**kw):
        with self.log_lock:self.qlog.write(json.dumps(dict(event=event,monotonic_ns=time.monotonic_ns(),dropped_frames=0,**kw))+'\n');self.qlog.flush()
    def submit(self,depth,pose,sim_s,capture_end_ns,observation_id):
        if self.error:raise RuntimeError('Depth pipeline failed') from self.error
        self.queue.put_nowait((np.asarray(depth,dtype=np.float32).copy(),list(pose),sim_s,capture_end_ns,observation_id))
        self.qrecord('SUBMIT',frame_id=observation_id,queue_length=self.queue.qsize(),archive_queue_length=self.archive_queue.qsize())
    def snapshot(self):
        if self.error:raise RuntimeError('Depth pipeline failed') from self.error
        with self.lock:return self.latest
    def run(self):
        try:
            while True:
                item=self.queue.get()
                if item is None:break
                depth,pose,sim_s,ns,frame=item;started=time.monotonic_ns();transform=camera_to_world(pose,self.camera['height_m'])
                rng=np.random.default_rng(np.random.SeedSequence([20261027,self.offset,frame]))
                result=self.field.update(depth,intrinsics(self.camera),transform,True,rng,frame_tick=round(sim_s*72));processed=time.monotonic_ns()
                path=self.out/f'snapshot_{frame:04d}.npz';meta=dict(frame_id=frame,sim_s=sim_s,pose=pose,capture_end_monotonic_ns=ns,
                    file=str(path),empty_unknown=False,processing_start_ns=started,processing_end_ns=processed,archive_async=True)
                snap=RecentSnapshot(self.field,meta)
                with self.lock:
                    meta['publication_monotonic_ns']=time.monotonic_ns();snap.metadata=MappingProxyType(meta.copy());self.latest=snap
                self.log.write(json.dumps({**meta,**result,'snapshot_copy_ms':(meta['publication_monotonic_ns']-processed)/1e6,
                    'queue_length_at_publish':self.queue.qsize(),'archive_queue_length':self.archive_queue.qsize(),'dropped_frames':0})+'\n');self.log.flush()
                self.archive_queue.put_nowait((snap,depth,transform));self.count+=1
        except BaseException as exc:self.error=exc
    def archive(self):
        try:
            while True:
                item=self.archive_queue.get()
                if item is None:break
                snap,depth,transform=item;start=time.monotonic_ns();path=snap.metadata['file'];snap.save(path)
                np.savez_compressed(self.out/f"depth_{snap.metadata['frame_id']:04d}.npz",depth=depth,camera_to_world=transform)
                self.alog.write(json.dumps(dict(frame_id=snap.metadata['frame_id'],file=path,archive_start_ns=start,archive_end_ns=time.monotonic_ns(),
                    snapshot_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest()))+'\n');self.alog.flush()
        except BaseException as exc:self.error=exc
    def close(self):
        self.queue.put_nowait(None);self.thread.join(90)
        if self.thread.is_alive():raise RuntimeError('Map publisher drain timeout')
        self.archive_queue.put_nowait(None);self.writer.join(120)
        if self.writer.is_alive():raise RuntimeError('Archive drain timeout')
        self.log.close();self.qlog.close();self.alog.close()
        if self.error:raise RuntimeError('Depth pipeline failed') from self.error
        self.latest.save(self.out/'final.npz')
