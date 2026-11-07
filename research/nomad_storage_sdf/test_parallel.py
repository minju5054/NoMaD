import json, multiprocessing as mp, os, tempfile, threading, unittest
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import bulk as b, parallel as p,profiled
from .loader import reconstruct,load_npz,bit_equal

def fixture(path):
    occupied=np.zeros((16,17),bool);occupied[7,8]=True
    arrays=dict(occupied=occupied,observed=occupied.copy(),origin=np.array([0.,0.]),h=np.array(.01),radius=np.array(.09),metadata=np.array('{}'))
    arrays['values']=reconstruct(arrays);np.savez(path,**arrays);return arrays

class Tests(unittest.TestCase):
    def test_profiled_conversion_keeps_all_bits_without_backup(self):
        with tempfile.TemporaryDirectory() as t:
            file=Path(t)/'snapshot_0.npz';arrays=fixture(file);old=b.sha(file);timer=profiled.Timer()
            with patch.object(b,'ensure_backup',side_effect=AssertionError('Backup forbidden')):
                row=profiled.prepare(file,{'version_id':'test'},None,timer)
                self.assertEqual(old,b.sha(file));self.assertIsNone(row['backup_tar'])
                records=[];row=profiled.commit(row,SimpleNamespace(assert_clear=lambda root:None),Path(t),records.append,timer)
            self.assertEqual(row['status'],'CONVERTED')
            restored=load_npz(file);self.assertTrue(all(bit_equal(v,restored[k]) for k,v in arrays.items()))
            self.assertEqual(timer.seconds['one_touch_backup'],0.)
            self.assertTrue(all(v>=0 for v in timer.seconds.values()));json.dumps(timer.seconds,allow_nan=False)
    def test_profiled_mismatch_preserves_file(self):
        with tempfile.TemporaryDirectory() as t:
            file=Path(t)/'snapshot_0.npz';data=fixture(file);data['values'][0,0]=np.nextafter(data['values'][0,0],np.inf);np.savez(file,**data);old=b.sha(file)
            row=profiled.prepare(file,{'version_id':'test'},None,profiled.Timer())
            self.assertEqual(row['status'],'SKIPPED_SDF_MISMATCH');self.assertEqual(old,b.sha(file));self.assertFalse(list(Path(t).glob('.*.tmp')))
    def test_unique_file_ownership(self):
        with self.assertRaises(ValueError):p.unique_jobs(['/tmp/a','/tmp/./a'])
        self.assertEqual(len(p.unique_jobs(['/tmp/a','/tmp/b'])),2)
    def test_memory_limits_and_preexisting_swap(self):
        base=dict(available_bytes=8*1024**3,swap_used_bytes=6*1024**3,swap_out_pages=100)
        self.assertFalse(p.memory_pressure(dict(base),base))
        self.assertTrue(p.memory_pressure(dict(base,available_bytes=3*1024**3),base))
        self.assertTrue(p.memory_pressure(dict(base,swap_out_pages=101),base))
        self.assertTrue(p.memory_pressure(dict(base,swap_used_bytes=base['swap_used_bytes']+4096),base))
    def test_spawned_workers_atomic_roundtrip_and_merge(self):
        ctx=mp.get_context('spawn')
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);root=base/'runroot';root.mkdir();logs=base/'manifests';files=[];original={}
            for i in range(6):
                f=root/f'snapshot_{i}.npz';original[str(f)]=fixture(f);files.append(f)
            ids=ctx.Queue();ready=ctx.Queue();start=ctx.Event();registry=ctx.Array('i',2);abort=ctx.Event();lock=ctx.Lock()
            for i in range(2):ids.put(i)
            with ProcessPoolExecutor(max_workers=2,mp_context=ctx,initializer=p.init_worker,
                    initargs=(ids,ready,start,registry,abort,lock,sorted(os.sched_getaffinity(0))[:2],str(base))) as pool:
                warm=[pool.submit(p.ping) for _ in range(2)]
                for _ in range(2):ready.get(timeout=30)
                start.set()
                for f in warm:f.result(timeout=30)
                jobs=[(str(f),{'tar':'test-original.tar'},{'version_id':'test'},{'sha256':b.sha(f)},None,str(root),str(logs)) for f in files]
                results=[f.result(timeout=30) for f in [pool.submit(p.worker_file,j) for j in jobs]]
            self.assertFalse(abort.is_set());self.assertTrue(all(r['status']=='CONVERTED' and r['nice']>=10 for r in results))
            merged=p.merged_rows(logs);self.assertEqual(len(merged),6)
            for f in files:
                restored=load_npz(f);self.assertTrue(all(bit_equal(v,restored[k]) for k,v in original[str(f)].items()))
            self.assertFalse(list(root.glob('.*.tmp')))
    def test_disk_error_sets_global_abort_preserves_original(self):
        with tempfile.TemporaryDirectory() as t,patch.object(b,'ISAAC',Path(t)):
            base=Path(t);root=base/'runroot';root.mkdir();f=root/'snapshot_0.npz';fixture(f);old=b.sha(f)
            context=dict(index=0,abort=threading.Event(),lock=threading.Lock(),guard=SimpleNamespace(assert_clear=lambda root:None))
            job=(str(f),{'tar':'original.tar'},{'version_id':'test'},{'sha256':old},None,str(root),str(base/'manifest'))
            with patch.dict(p.CTX,context,clear=True),patch.object(b.os,'replace',side_effect=OSError(28,'injected disk error')):
                with self.assertRaises(OSError):p.worker_file(job)
                self.assertTrue(p.CTX['abort'].is_set())
                with self.assertRaises(p.Aborted):p.worker_file(job)
            self.assertEqual(old,b.sha(f))
            records=[json.loads(line) for log in (base/'manifest/workers').glob('*.jsonl') for line in log.read_text().splitlines()]
            self.assertEqual([r['status'] for r in records],['PREPARED','ERROR'])
    def test_worker_manifest_merge_rejects_conflict(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t);(folder/'workers').mkdir()
            b.write_jsonl(folder/'manifest.jsonl',[dict(path='/tmp/test',new_sha256='a',status='CONVERTED')])
            b.write_jsonl(folder/'workers/worker.jsonl',[dict(path='/tmp/test',new_sha256='b',status='CONVERTED')])
            with self.assertRaises(RuntimeError):p.merged_rows(folder)

if __name__=='__main__':unittest.main()
