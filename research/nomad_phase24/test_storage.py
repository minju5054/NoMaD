import ast,errno,json,queue,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from .storage import atomic_json,read,ensure_reserve,disk_full_state,capacity,HEADROOM_BYTES,retain_full_frames
from .retention import GuardRGBWrites,archive_compact,retained_apply
from .campaign import load_state,status

class Tests(unittest.TestCase):
    def test_enospc_preserves_last_complete_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);f=root/'state.json';atomic_json(f,dict(step=1));original=f.read_bytes()
            with patch('os.fsync',side_effect=OSError(errno.ENOSPC,'No space left on device')):
                with self.assertRaises(OSError):atomic_json(f,dict(step=2),backup=True)
            self.assertEqual(f.read_bytes(),original);self.assertFalse(list(root.glob('.*.tmp')))
            ensure_reserve(root);disk_full_state(root,dict(step=2),OSError(errno.ENOSPC,'full'))
            self.assertEqual(read(f)['status'],'DISK_FULL_STOP');self.assertFalse((root/'.metadata_reserve').exists());self.assertEqual(read(root/'state.json.bak')['step'],1)
    def test_corrupt_state_recovers_from_plan_without_changing_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'state.json').write_bytes(b'');(root/'state.tmp').write_bytes(b'');atomic_json(root/'plan.json',dict(protocol=dict(frozen=True)))
            (root/'metrics').mkdir();atomic_json(root/'metrics/done.json',dict(success=False));before=(root/'metrics/done.json').read_bytes()
            recovered=load_state(root);self.assertEqual(recovered['protocol'],dict(frozen=True));self.assertEqual((root/'metrics/done.json').read_bytes(),before)
            self.assertEqual(status(root)['completed'],1);self.assertTrue(list(root.glob('state.corrupt.*')))
    def test_guard_requires_remaining_plus_headroom(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();(root/'done').mkdir();atomic_json(root/'metrics/done.json',dict(technical_validation='PASS'))
            plan=[dict(key='done',output=str(root/'done'),index=131),dict(key='next',output=str(root/'next'),index=132)]
            with patch('nomad_phase24.storage.measure_run',return_value=dict(bytes=1000,thin_projected_bytes=600)):
                self.assertFalse(capacity(root,plan,HEADROOM_BYTES+599)['enough']);self.assertTrue(capacity(root,plan,HEADROOM_BYTES+600)['enough'])
            self.assertTrue(retain_full_frames(131));self.assertFalse(retain_full_frames(132));self.assertTrue(retain_full_frames(95,True))
    def test_rgb_guard_keeps_identical_inputs_and_suppresses_only_writes(self):
        source="def capture(rgb,consume):\n consume(rgb)\n Image.fromarray(rgb).save('frame.png')\n return rgb\n"
        tree=ast.parse(source);guard=GuardRGBWrites();tree=guard.visit(tree);self.assertEqual(guard.count,1)
        for retain in (True,False):
            saved=[];consumed=[];rgb=object();image=SimpleNamespace(fromarray=lambda value:SimpleNamespace(save=lambda path:saved.append((value,path))))
            ns=dict(Image=image,_phase24_full_frames=retain);exec(compile(ast.fix_missing_locations(tree),'<test>','exec'),ns)
            self.assertIs(ns['capture'](rgb,consumed.append),rgb);self.assertIs(consumed[0],rgb);self.assertEqual(len(saved),int(retain))
    def test_compact_archive_keeps_fresh_and_visualization_maps_without_raw_depth(self):
        import io
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);owner=SimpleNamespace(archive_queue=queue.Queue(),alog=io.StringIO(),error=None)
            def snap(frame,stamp):
                data=('immutable map '+str(frame)).encode();path=root/f'snapshot_{frame:04d}.npz'
                return SimpleNamespace(metadata=dict(frame_id=frame,sim_s=stamp,file=str(path)),save=lambda p:Path(p).write_bytes(data))
            snapshots=[snap(i,i*.25) for i in range(8)]
            for s in snapshots:owner.archive_queue.put((s,b'raw depth',None))
            owner.archive_queue.put((snapshots[3],None,None));owner.archive_queue.put(None);archive_compact(owner)
            self.assertIsNone(owner.error);self.assertEqual(sorted(p.name for p in root.iterdir()),['snapshot_0000.npz','snapshot_0003.npz','snapshot_0004.npz'])
            self.assertEqual((root/'snapshot_0003.npz').read_bytes(),b'immutable map 3')
            calls=[];maps=SimpleNamespace(retain_latest=lambda:calls.append('retain'));result=object()
            execution=SimpleNamespace(depth_maps=maps,apply=lambda *args:(calls.append(args),result)[1]);retained_apply(execution)
            args=(object(),object(),object());self.assertIs(execution.apply(*args),result);self.assertEqual(calls,['retain',args,'retain'])
    def test_protected_runtime_has_only_registered_image_write_sites(self):
        import inspect
        from nomad_isaac.async_runtime import run_async
        from nomad_isaac.common import ROOT
        for source,expected in [(inspect.getsource(run_async),4),((ROOT/'research/nomad_phase21/simulator.py').read_text(),2)]:
            guard=GuardRGBWrites();guard.visit(ast.parse(source));self.assertEqual(guard.count,expected)
    def test_retention_inherits_unmodified_depth_publisher(self):
        from nomad_phase20f.depth import DepthMapThread as original
        from .retention import install_depth_retention
        import nomad_phase15b.depth as target
        before=target.DepthMapThread
        try:
            install_depth_retention();self.assertIs(target.DepthMapThread.run,original.run);self.assertIs(target.DepthMapThread.submit,original.submit)
        finally:target.DepthMapThread=before
if __name__=='__main__':unittest.main()
