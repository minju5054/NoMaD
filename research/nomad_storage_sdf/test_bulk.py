import json,tempfile,unittest,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from . import bulk
from .loader import reconstruct,load_npz,bit_equal
from .convert import sha
from .bulk_guard import Guard
from .versions import Registry

class Tests(unittest.TestCase):
 def arrays(self):
  occ=np.zeros((12,13),bool);occ[4,5]=True
  d=dict(occupied=occ,observed=occ.copy(),origin=np.array([0.,0.]),h=np.array(.01),radius=np.array(.09),metadata=np.array('{}'))
  return dict(values=reconstruct(d),**d)
 def test_prepare_does_not_replace_and_commit_roundtrip(self):
  with tempfile.TemporaryDirectory() as t,patch.object(bulk,'ISAAC',Path(t)):
   p=Path(t)/'snapshot_0.npz';d=self.arrays();np.savez(p,**d);old=sha(p)
   r=bulk.prepare_file(p,{'tar':'verified.tar'},{'version_id':'test'},{'sha256':old});self.assertEqual(sha(p),old)
   journal=[];guard=SimpleNamespace(assert_clear=lambda root:None)
   final=bulk.commit_file(r,guard,Path(t),lambda x:journal.append(dict(x)))
   self.assertEqual(final['status'],'CONVERTED');self.assertEqual([x['status'] for x in journal],['PREPARED','CONVERTED'])
   restored=load_npz(p);self.assertTrue(all(bit_equal(d[k],restored[k]) for k in d))
 def test_jsonl_manifest_resolves_original_hash(self):
  from .loader import resolve_original_hash
  with tempfile.TemporaryDirectory() as t,patch.object(bulk,'ISAAC',Path(t)):
   p=Path(t)/'a.npz';np.savez(p,**self.arrays());old=sha(p);r=bulk.prepare_file(p,{'tar':'original.tar'},{'version_id':'test'},{'sha256':old});r=bulk.commit_file(r,SimpleNamespace(assert_clear=lambda root:None),Path(t),lambda x:None)
   manifest=Path(t)/'manifest.jsonl';manifest.write_text(json.dumps(r)+'\n');proof=resolve_original_hash(p,old,manifest);self.assertEqual(proof['status'],'LOSSLESS_RETROFIT')
 def test_mismatch_is_unchanged(self):
  with tempfile.TemporaryDirectory() as t,patch.object(bulk,'ISAAC',Path(t)):
   p=Path(t)/'snapshot_0.npz';d=self.arrays();d['values'][0,0]=np.nextafter(d['values'][0,0],np.inf);np.savez(p,**d);old=sha(p)
   r=bulk.prepare_file(p,{'tar':'t'},{'version_id':'v'},{'sha256':old});self.assertEqual(r['status'],'SKIPPED_SDF_MISMATCH');self.assertEqual(old,sha(p));self.assertFalse(list(Path(t).glob('.*.tmp')))
 def test_legacy_object_format_is_skipped(self):
  with tempfile.TemporaryDirectory() as t,patch.object(bulk,'ISAAC',Path(t)):
   p=Path(t)/'snapshot_0.npz';d=self.arrays();d['metadata']=np.array({'old':'format'},dtype=object);np.savez(p,**d);old=sha(p)
   r=bulk.prepare_file(p,{'tar':'t'},{'version_id':'v'},{'sha256':old});self.assertEqual(r['status'],'SKIPPED_DIFFERENT_FORMAT');self.assertEqual(old,sha(p))
 def test_exception_batch_never_commits(self):
  with tempfile.TemporaryDirectory() as t,patch.object(bulk,'ISAAC',Path(t)),ThreadPoolExecutor(max_workers=2) as pool:
   files=[Path(t)/'a.npz',Path(t)/'bad.npz'];jobs=[]
   for p in files:np.savez(p,**self.arrays());jobs.append((p,{'tar':'t'},{'version_id':'v'},{'sha256':sha(p)},None))
   before={p:sha(p) for p in files};original=bulk.prepare_file
   def prepare(path,*a):
    if path.name=='bad.npz':raise OSError(5,'injected IO error')
    return original(path,*a)
   with patch.object(bulk,'prepare_file',side_effect=prepare):
    with self.assertRaises(OSError):bulk.prepare_batch(pool,jobs)
   self.assertEqual(before,{p:sha(p) for p in files})
 def test_disk_error_preserves_original_and_prepared_journal(self):
  with tempfile.TemporaryDirectory() as t,patch.object(bulk,'ISAAC',Path(t)):
   p=Path(t)/'a.npz';np.savez(p,**self.arrays());old=sha(p);r=bulk.prepare_file(p,{'tar':'t'},{'version_id':'v'},{'sha256':old});j=[]
   with patch.object(bulk.os,'replace',side_effect=OSError(28,'injected disk full')):
    with self.assertRaises(OSError):bulk.commit_file(r,SimpleNamespace(assert_clear=lambda root:None),Path(t),lambda x:j.append(x))
   self.assertEqual(old,sha(p));self.assertEqual(j[-1]['status'],'PREPARED')
 def test_running_and_root_marker_excluded_cache_residue_kept(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'old_run';root.mkdir();g=object.__new__(Guard);g.refresh=lambda *a,**kw:None;g.process_roots={};g.locks=set();g.lock_paths={}
   (root/'state.json').write_text(json.dumps({'status':'RUNNING'}));self.assertEqual(g.reason(root)['reason'],'ACTIVE_STATE')
   (root/'state.json').write_text(json.dumps({'status':'COMPLETE'}));(root/'cache').mkdir();lock=root/'cache/_cache.lock';lock.touch();self.assertIsNone(g.reason(root));self.assertTrue(lock.exists())
   st=lock.stat();g.locks={(st.st_dev,st.st_ino)};self.assertEqual(g.reason(root)['reason'],'HELD_CACHE_LOCK');g.locks=set();(root/'campaign.lock').touch();self.assertEqual(g.reason(root)['reason'],'RUN_ROOT_LOCK_MARKER')
 def test_unknown_runtime_version_skipped(self):
  with tempfile.TemporaryDirectory() as t:self.assertFalse(Registry().resolve(t)['supported'])
 def test_unsafe_source_sha_refuses_before_any_temp(self):
  with tempfile.TemporaryDirectory() as t,patch.object(bulk,'ISAAC',Path(t)):
   p=Path(t)/'a.npz';np.savez(p,**self.arrays())
   with self.assertRaises(RuntimeError):bulk.prepare_file(p,{'tar':'t'},{'version_id':'v'},{'sha256':'bad'})
   self.assertFalse(list(Path(t).glob('.*.tmp')))

if __name__=='__main__':unittest.main()
