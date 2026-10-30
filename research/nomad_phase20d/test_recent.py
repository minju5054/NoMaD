import json,tempfile,time,threading,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.ndimage import distance_transform_edt
from nomad_phase15b.depth import Snapshot
from nomad_phase20c.test_detour import field
from nomad_phase20b.config import runtime_config
from .recent import RecentMap,RecentSnapshot,build_cache,load_cache,save_cache,local_certificate
from .depth import DepthMapThread

class Tests(unittest.TestCase):
    def test_free_time_and_age_threshold(self):
        f=RecentMap([-1,-1,2,1]);f.frame_tick=100
        f.accumulate(np.array([[1.,0.,.2]]),np.array([1.]),[0,0,.5])
        cells,_=f.cells([[.5,0],[1.,0]])
        self.assertEqual(f.last_free_tick[cells[0,1],cells[0,0]],100)
        self.assertEqual(f.last_free_tick[cells[1,1],cells[1,0]],-1)
        s=RecentSnapshot(f,{})
        self.assertFalse(s.blocked(244)[cells[0,1],cells[0,0]])
        self.assertTrue(s.blocked(245)[cells[0,1],cells[0,0]])

    def test_cached_exact_equals_full_scan(self):
        rng=np.random.default_rng(20261103)
        f=RecentMap([-1,-1,2,1]);f.occupied[:]=rng.random(f.occupied.shape)<.35;f.observed[:]=True;f.last_free_tick[:]=100
        f.values=distance_transform_edt(~f.occupied,sampling=f.h)-f.radius;s=RecentSnapshot(f,{})
        cached,info=build_cache(s,100);self.assertEqual(info['edt_computations'],1)
        for _ in range(5):
            path=rng.uniform([-.8,-.8],[1.8,.8],size=(11,2))
            self.assertAlmostEqual(cached.exact_clearance(path),Snapshot.exact_clearance(cached,path),places=12)
            self.assertEqual(local_certificate(s,path,100,.025,True),cached.exact_clearance(path)>=.025)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cache.npz';save_cache(s,cached,p);base,reloaded=load_cache(p)
            np.testing.assert_array_equal(reloaded.values,cached.values)
            self.assertAlmostEqual(reloaded.exact_clearance(path),cached.exact_clearance(path),places=12)

    def test_stale_field_is_blocked(self):
        f=RecentMap([-1,-1,2,1]);f.observed[:]=True;f.last_free_tick[:]=0;f.values[:]=1.
        s=RecentSnapshot(f,{});fresh,_=build_cache(s,144);stale,_=build_cache(s,145)
        self.assertFalse(fresh.occupied.any());self.assertTrue(stale.occupied.all())
        self.assertLess(stale.exact_clearance([[0,0],[.3,0]]),0)

    def test_sparse_positive_exact_distance(self):
        f=RecentMap([-1,-1,2,1]);f.observed[:]=True;f.last_free_tick[:]=10
        x,y=f.cells([[1.,0]])[0][0];f.occupied[y,x]=True
        f.values=distance_transform_edt(~f.occupied,sampling=f.h)-f.radius
        s=RecentSnapshot(f,{});cached,_=build_cache(s,10);p=[[0,0],[.2,.1],[.5,0]]
        self.assertAlmostEqual(cached.exact_clearance(p),.41,places=12)
        self.assertAlmostEqual(cached.exact_clearance(p),Snapshot.exact_clearance(cached,p),places=12)
        self.assertTrue(local_certificate(s,p,10,.025,True))

    def test_publish_does_not_wait_for_archive(self):
        release=threading.Event();entered=threading.Event();save=RecentSnapshot.save
        def slow(s,path,compressed=True):
            if s.metadata.get('frame_id',-1)>=0 and str(path).endswith('.npz') and not str(path).endswith('final.npz'):
                entered.set();self.assertTrue(release.wait(10))
            return save(s,path,compressed)
        c=runtime_config('M1_ROTATE',80,level='L2')
        with tempfile.TemporaryDirectory() as d,patch.object(RecentSnapshot,'save',slow):
            maps=DepthMapThread(Path(d),c['camera'],800000)
            try:
                maps.submit(np.full((240,320),1.,np.float32),[0,0,0],0.,time.monotonic_ns(),0)
                self.assertTrue(entered.wait(10));self.assertEqual(maps.snapshot().metadata['frame_id'],0)
                self.assertFalse(Path(maps.snapshot().metadata['file']).exists())
                maps.submit(np.full((240,320),1.,np.float32),[0,0,0],.25,time.monotonic_ns(),1)
                deadline=time.monotonic()+10
                while maps.snapshot().metadata['frame_id']<1 and time.monotonic()<deadline:time.sleep(.01)
                self.assertEqual(maps.snapshot().metadata['frame_id'],1)
            finally:release.set();maps.close()
            self.assertEqual(len((Path(d)/'depth/updates.jsonl').read_text().splitlines()),2)
            self.assertEqual(len((Path(d)/'depth/archives.jsonl').read_text().splitlines()),2)

if __name__=='__main__':unittest.main()
