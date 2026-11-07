import io,json,tempfile,unittest
from pathlib import Path
import numpy as np
from nomad_phase15b.depth import Snapshot
from .loader import reconstruct,load_npz,restoring_numpy_load,array_fingerprint,bit_equal,resolve_original_hash
from .convert import inspect_file,compact_one,sha

class Tests(unittest.TestCase):
 def data(self):
  occ=np.zeros((12,13),bool);occ[5,6]=True
  d=dict(occupied=occ,observed=~occ,origin=np.array([-.1,-.2]),h=np.array(.01),radius=np.array(.09),metadata=np.array('{"frame_id":1}'),
         extra=np.array([0x8000000000000000,0x7ff8000000000001],np.uint64).view(np.float64),aux=np.asfortranarray(np.arange(12).reshape(3,4)))
  return dict(values=reconstruct(d),**d)
 def test_roundtrip_preserves_every_array_bit(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'a.npz';d=self.data();np.savez(p,**d);row,_=inspect_file(p);log=[];out=compact_one(p,row,'backup.tar','a.npz',lambda x:log.append(dict(x)))
   self.assertEqual(out['status'],'CONVERTED');self.assertEqual([x['status'] for x in log],['PREPARED','CONVERTED'])
   got=load_npz(p,row['original_arrays']);self.assertTrue(all(bit_equal(d[k],got[k]) for k in d))
   with np.load(p) as z:self.assertNotIn('values',z.files)
   m=Path(t)/'manifest.json';m.write_text(json.dumps([out]));self.assertEqual(resolve_original_hash(p,row['original_sha256'],m)['status'],'LOSSLESS_RETROFIT')
 def test_mismatch_is_byte_for_byte_untouched(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'a.npz';d=self.data();d['values'][0,0]=np.nextafter(d['values'][0,0],np.inf);np.savez(p,**d);old=sha(p);r,_=inspect_file(p);self.assertFalse(r['values_bit_equal']);out=compact_one(p,r,'b.tar','a',lambda x:None);self.assertEqual(out['status'],'SKIPPED_VALUES_MISMATCH');self.assertEqual(old,sha(p))
 def test_frozen_snapshot_loader_opt_in(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'a.npz';d=self.data();np.savez_compressed(p,**{k:v for k,v in d.items() if k!='values'})
   original=np.load
   with restoring_numpy_load():loaded=Snapshot.load(p);self.assertTrue(bit_equal(loaded.values,d['values']))
   self.assertIs(np.load,original)
 def test_empty_grid(self):
  d=self.data();d['occupied'].fill(False);a=reconstruct(d);self.assertTrue(np.all(a==a[0,0]))
 def test_hash_lineage_rejects_tamper(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'a.npz';np.savez(p,**self.data());r,_=inspect_file(p);out=compact_one(p,r,'b.tar','a',lambda x:None);m=Path(t)/'m.json';m.write_text(json.dumps([out]));p.write_bytes(p.read_bytes()+b'changed')
   with self.assertRaises(ValueError):resolve_original_hash(p,r['original_sha256'],m)
 def test_changed_source_refuses_conversion(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'a.npz';d=self.data();np.savez(p,**d);r,_=inspect_file(p);d['observed'][0,0]=~d['observed'][0,0];np.savez(p,**d)
   with self.assertRaises(RuntimeError):compact_one(p,r,'b.tar','a',lambda x:None)

if __name__=='__main__':unittest.main()
