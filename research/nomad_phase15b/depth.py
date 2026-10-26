"""FIFO depth integration thread. Consumers only acquire an immutable pointer."""
import hashlib
import json
import queue
import threading
import time
from pathlib import Path
from types import MappingProxyType
import numpy as np
from nomad_phase15.depth_sdf import DepthSDF, camera_to_world, intrinsics
from nomad_phase15.occupancy import make_field, ray_kernel
from nomad_phase15.evaluate import suffix, sample_path
from .config import protocol

class Snapshot(DepthSDF):
    def __init__(self,field,metadata):
        for k in ('h','radius','error_bound','origin'):
            value=getattr(field,k);setattr(self,k,value.copy() if isinstance(value,np.ndarray) else value)
        for k in ('values','occupied','observed'):
            value=getattr(field,k).copy();value.flags.writeable=False;setattr(self,k,value)
        self.origin.flags.writeable=False
        self.metadata=MappingProxyType(dict(metadata))
    def save(self,path):
        np.savez_compressed(path,values=self.values,occupied=self.occupied,observed=self.observed,origin=self.origin,h=self.h,radius=self.radius,metadata=json.dumps(dict(self.metadata)))
    @classmethod
    def load(cls,path):
        with np.load(path) as z:
            obj=object.__new__(cls)
            for k in ('values','occupied','observed','origin'):
                a=z[k].copy();a.flags.writeable=False;setattr(obj,k,a)
            obj.h=float(z['h']);obj.radius=float(z['radius']);obj.error_bound=obj.h/np.sqrt(2)
            obj.metadata=MappingProxyType(json.loads(str(z['metadata'])))
        return obj
    def exact_clearance(self,xy):
        # EDT distance sites are occupied cell centers, not filled oracle boxes.
        iy,ix=np.nonzero(self.occupied)
        points=self.origin+np.column_stack([ix,iy])*self.h
        if not len(points):return float(np.min(self.values))
        result=float('inf')
        for a,b in zip(xy[:-1],xy[1:]):
            delta=b-a;den=float(delta@delta)
            t=np.clip((points-a)@delta/den,0,1) if den>1e-24 else np.zeros(len(points))
            result=min(result,float(np.linalg.norm(points-(a+t[:,None]*delta),axis=1).min())-self.radius)
        return result

def evaluate_samples(samples,b,field):
    candidates=[]
    for i,xy in enumerate(samples):
        path,length=suffix(xy,b);q,step=sample_path(path)
        clearance=float(field.query(q)[0].min()-field.error_bound-step/2)
        candidates.append(dict(index=i,clearance_m=clearance,safe=clearance>=.025,remaining_length_m=length,unknown_fraction=field.unknown_fraction(q)))
    safe=[c for c in candidates if c['safe']]
    selected=min(safe,key=lambda c:(-c['remaining_length_m'],c['index'])) if safe else min(candidates,key=lambda c:(-c['clearance_m'],c['index']))
    return samples[selected['index']],dict(selected_sample=selected['index'],all_unsafe=not bool(safe),candidates=candidates,snapshot=dict(field.metadata))

class DepthMapThread:
    def __init__(self,out,camera,offset):
        self.out=Path(out)/'depth';self.out.mkdir();self.camera=camera;self.offset=offset
        ray_kernel()  # Compile once before paced execution begins.
        self.field=make_field(protocol()['depth']['bounds_m'],'V1')
        empty=Snapshot(self.field,dict(frame_id=-1,sim_s=0.,capture_end_monotonic_ns=0,publication_monotonic_ns=0,empty_unknown=True,file=str(self.out/'snapshot_initial.npz')))
        empty.save(empty.metadata['file']);self.latest=empty
        self.queue=queue.Queue();self.lock=threading.Lock();self.error=None;self.count=0
        self.log=(self.out/'updates.jsonl').open('x')
        self.thread=threading.Thread(target=self.run,name='depth-v1-map',daemon=True);self.thread.start()
    def submit(self,depth,pose,sim_s,capture_end_ns,observation_id):
        if self.error:raise RuntimeError('Depth map failed') from self.error
        self.queue.put_nowait((np.asarray(depth,dtype=np.float32).copy(),list(pose),sim_s,capture_end_ns,observation_id))
    def snapshot(self):
        if self.error:raise RuntimeError('Depth map failed') from self.error
        with self.lock:return self.latest
    def run(self):
        try:
            while True:
                item=self.queue.get()
                if item is None:break
                depth,pose,sim_s,ns,frame=item;t=time.perf_counter()
                transform=camera_to_world(pose,self.camera['height_m'])
                rng=np.random.default_rng(np.random.SeedSequence([20261027,self.offset,frame]))
                stats=self.field.update(depth,intrinsics(self.camera),transform,True,rng)
                path=self.out/f'snapshot_{frame:04d}.npz'
                meta=dict(frame_id=frame,sim_s=sim_s,pose=pose,capture_end_monotonic_ns=ns,file=str(path),empty_unknown=False)
                snap=Snapshot(self.field,meta)
                snap.save(path)
                np.savez_compressed(self.out/f'depth_{frame:04d}.npz',depth=depth,camera_to_world=transform)
                meta.update(publication_monotonic_ns=time.monotonic_ns())
                snap.metadata=MappingProxyType(meta.copy())
                row={**meta,**stats,'snapshot_and_persist_ms':(time.perf_counter()-t)*1000-stats['update_ms'],'snapshot_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                self.log.write(json.dumps(row)+'\n');self.log.flush()
                with self.lock:self.latest=snap
                self.count+=1
        except BaseException as e:self.error=e
    def close(self):
        self.queue.put_nowait(None);self.thread.join(60)
        if self.thread.is_alive():raise RuntimeError('Depth drain did not complete')
        self.log.close()
        if self.error:raise RuntimeError('Depth map failed') from self.error
        self.latest.save(self.out/'final.npz')
