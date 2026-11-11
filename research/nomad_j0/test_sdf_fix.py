"""Offline saved-depth equivalence, strict boundary, isolated four-run routing."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from nomad_isaac.common import sha256_file
from nomad_phase15.occupancy import make_field
from nomad_phase15.depth_sdf import intrinsics
from nomad_phase16.depth import DepthMapThread as FrozenThread
from nomad_j1.common import scene_config
from nomad_j1.depth import registration,make_registered_field,thread_type
from . import config,h2_rerun,campaign

def digest(array):return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()

def saved_depth_equivalence():
    artifacts=config.ROOT.parent/'artifacts/isaac6';records=[]
    for scene in ('SLW','LC','CL','H1-v2'):
        run=(artifacts/'h1v2_trial_01/main/H1-v2_D075_221_CUT/attempt1' if scene=='H1-v2' else
             artifacts/f'phase18_confirm_01/main/{scene}_066_D750_FRESHEST-SAFE')
        c,_=scene_config(scene);spec=registration(c)
        old=make_field(spec['legacy_bounds_m'],'V1');new=make_registered_field(spec)
        assert np.array_equal(old.origin,new.origin) and old.h==new.h
        assert old.values.shape==new.values.shape and old.values.tobytes()==new.values.tobytes()
        for frame in range(3):
            file=run/'depth'/f'depth_{frame:04d}.npz'
            with np.load(file) as z:depth=z['depth'].copy();transform=z['camera_to_world'].copy()
            for field in (old,new):
                field.update(depth,intrinsics(c['camera']),transform,True,np.random.default_rng(np.random.SeedSequence([20261027,660000,frame])))
            names=('values','occupied','observed','log_odds_hundredths','occupied_observations')
            equal={k:getattr(old,k).tobytes()==getattr(new,k).tobytes() for k in names}
            assert all(equal.values()),(scene,frame,equal)
            points=np.random.default_rng(20261112+frame).uniform(old.origin+.01,np.asarray(spec['legacy_bounds_m'][2:])-.01,(128,2))
            left,right=old.query(points),new.query(points)
            assert all(a.tobytes()==b.tobytes() for a,b in zip(left,right))
            records.append(dict(scene=scene,frame=frame,input_file=str(file),input_sha256=sha256_file(file),
                old_shape=list(old.values.shape),new_shape=list(new.values.shape),bit_equal=equal,query_value_gradient_bit_equal=True,
                old_values_sha256=digest(old.values),new_values_sha256=digest(new.values)))
    return records

class Tests(unittest.TestCase):
    def test_saved_depth_four_scenes_bit_exact(self):
        records=saved_depth_equivalence()
        self.assertEqual(len(records),12)

    def test_h2_geometry_padding_origin_empty_and_strict_query(self):
        c,_=scene_config('H2');spec=registration(c)
        self.assertEqual(spec['registered_bounds_m'],[-4.,-3.5,9.6,6.2])
        self.assertEqual(spec['origin_m'],[-4.,-3.5])
        self.assertEqual(spec['resolution_m'],.01)
        old=make_field(spec['legacy_bounds_m'],'V1');new=make_registered_field(spec)
        self.assertEqual(old.values.tobytes(),new.values[:old.values.shape[0],:old.values.shape[1]].tobytes())
        for point in ([8.1,0.],[9.1,0.],[9.59,0.]):
            with self.assertRaisesRegex(ValueError,'SDF query outside registered field'):old.query(np.array([point]))
            self.assertTrue(np.isfinite(new.query(np.array([point]))[0]).all())
        with self.assertRaisesRegex(ValueError,'SDF query outside registered field'):new.query(np.array([[9.7,0.]]))
        self.assertIs(type(new).query,type(old).query)
        self.assertIs(type(new).update,type(old).update)

    def test_live_factory_uses_frozen_thread_and_new_registration(self):
        c,_=scene_config('H2');spec=registration(c);cls=thread_type(spec)
        self.assertIs(cls.run,FrozenThread.run);self.assertIs(cls.submit,FrozenThread.submit)
        with tempfile.TemporaryDirectory() as temp:
            thread=cls(Path(temp),c['camera'],2210000)
            try:
                self.assertEqual(thread.field.values.shape,(971,1361))
                self.assertTrue(np.isfinite(thread.snapshot().query(np.array([[9.1,0.]]))[0]).all())
            finally:thread.close()

    def test_protocol_preserves_design_and_frozen_numerical_functions(self):
        before=json.loads((config.HERE/'protocol_before_sdf_fix.json').read_text());after=config.verify()
        for key in ('main_order','screening','execution','indices','delays_s'):self.assertEqual(after[key],before[key])
        for scene in config.SCENES:
            self.assertEqual({k:v for k,v in after['scenes'][scene].items() if k!='sdf_registration'},before['scenes'][scene])
            self.assertEqual(after['scenes'][scene]['sdf_registration'],registration(scene_config(scene)[0]))
        for name in ('research/nomad_phase15/depth_sdf.py','research/nomad_phase15/occupancy.py',
                     'research/nomad_phase17/graph.py','research/nomad_phase17/worker.py'):
            self.assertEqual(after['source_sha256'][name],before['source_sha256'][name])

    def test_rerun_four_and_merge_retains_other16(self):
        self.assertEqual([j['delay'] for j in h2_rerun.plan(h2_rerun.RERUN_ROOT)],[0.,0.,.75,.75])
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/'base';new=Path(temp)/'new';(base/'metrics').mkdir(parents=True);(new/'metrics').mkdir(parents=True)
            (base/'state.json').write_text(json.dumps(dict(status='COMPLETE',stage='DONE',protocol_sha256=sha256_file(config.HERE/'protocol_before_sdf_fix.json'))))
            old=[]
            for j in campaign.jobs(base):
                r=dict(j,technical_validation='FAIL' if j['scene']=='H2' else 'PASS',sentinel='unchanged')
                f=base/'metrics'/(j['key']+'.json');f.write_text(json.dumps(r));old.append((f,sha256_file(f)))
            for j in h2_rerun.plan(new):
                (new/'metrics'/(j['key']+'.json')).write_text(json.dumps(dict(j,technical_validation='PASS',sentinel='rerun')))
            combined,manifest=h2_rerun.combine(base,new)
            self.assertEqual(len(combined),20);self.assertEqual(sum(r['sentinel']=='unchanged' for r in combined),16)
            self.assertEqual(sum(r['sentinel']=='rerun' for r in combined),4);self.assertTrue(manifest['complete'])
            self.assertTrue(all(sha256_file(f)==h for f,h in old))
            state=json.loads((base/'state.json').read_text());state['status']='RUNNING';(base/'state.json').write_text(json.dumps(state))
            with self.assertRaisesRegex(AssertionError,'Wait for original J0'):h2_rerun.baseline(base)

if __name__=='__main__':unittest.main()
