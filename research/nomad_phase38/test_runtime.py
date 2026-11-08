import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace,MappingProxyType
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import integrate_se2
from nomad_phase32o.test_exec_cert import field
from .ec_normal import RTCWithEC,TEWithEC,te_trajectory
from .runtime import CareExecution

def prepare(e):
    f=field();f.observed=np.ones_like(f.occupied);f.metadata=MappingProxyType(dict(frame_id=0,sim_s=0.,publication_monotonic_ns=0))
    if isinstance(e,CareExecution):f=SimpleNamespace(points_world=np.empty((0,2)),metadata=f.metadata)
    e.depth_maps=SimpleNamespace(snapshot=lambda:f)
    if isinstance(e,TEWithEC):e.ec_te_mode='ENSEMBLE'
    return SimpleNamespace(pose=np.zeros(3),v=0.,w=0.),f

def fresh(i=1):
    path=np.c_[np.linspace(0,1,8),np.zeros(8)]
    return dict(id=i,observation_pose=[0,0,0],overnight_metric_samples=np.repeat(path[None],8,axis=0).tolist(),
        observation_sim_s=0.,received_monotonic_ns=1_000_000_000,monotonic_ns=1_000_000_000)
def refresh(tick=0):return dict(monotonic_ns=1_000_000_000+round(tick/72*1e9),simulation_time_s=tick/72,valid=True)

class RuntimeTests(unittest.TestCase):
    def test_new_methods_no_planners_apply_and_json_160_ticks(self):
        for cls in (RTCWithEC,TEWithEC,CareExecution):
            with self.subTest(method=cls.__name__),tempfile.TemporaryDirectory() as d:
                e=cls(Path(d));core,_=prepare(e);self.assertIsNone(e.repair_worker)
                e.apply(core,refresh(),fresh())
                self.assertEqual(e.sp.alignment_threshold_deg,90.)
                for tick in range(1,161):
                    before=core.pose.copy();e.plant.integrate(core,tick);e.integrate_record(before,core.pose)
                    if tick%8==0:
                        r=refresh(tick);sw=fresh(tick//8+1) if tick%32==0 else None
                        if sw is not None:sw['received_monotonic_ns']=r['monotonic_ns']
                        e.apply(core,r,sw);json.dumps(r,allow_nan=False)
                        if sw:json.dumps(sw,allow_nan=False)
                    self.assertLessEqual(abs(core.w),.4+1e-12);self.assertLessEqual(core.v,.3+1e-12)
                e.close()
                for f in Path(d).glob('*.jsonl'):
                    for line in f.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)
    def test_ec_fallback_full_all_then_slow_then_stop(self):
        with tempfile.TemporaryDirectory() as d:
            e=RTCWithEC(Path(d));core,_=prepare(e);calls=[]
            def check(pose,vw,path,field,t,state,scope,cap,controller=None):calls.append(cap);return dict(passed=cap==.1)
            e.ec_check=check;e.apply(core,refresh(),fresh())
            self.assertEqual(calls,[None,.1]);self.assertEqual(e.ec_cap,.1)
            # All samples duplicate here: full-speed duplicates are deduplicated
            # by the inherited Phase32 path key, then the SAFE slow list is used.
            e.ec_check=lambda *a,**kw:dict(passed=True);e.apply(core,refresh(8),fresh(2));self.assertIsNone(e.ec_cap)
            e.ec_check=lambda *a,**kw:dict(passed=False);e.apply(core,refresh(16),fresh(3))
            self.assertEqual(e.mode,'STOP_WAIT');self.assertIsNone(e.sp);e.close()
    def test_te_preview_does_not_mutate_live_ensemble_and_matches_commands(self):
        with tempfile.TemporaryDirectory() as d:
            e=TEWithEC(Path(d));core,_=prepare(e);e.apply(core,refresh(),fresh())
            ids=[c['id'] for c in e.transition.ensemble.chunks]
            profile=e.make_profile([[0,0],[1,.15]],core.pose,core.v,1,None,refresh())
            self.assertEqual(ids,[c['id'] for c in e.transition.ensemble.chunks])
            trace=te_trajectory(profile,core.pose,[core.v,core.w],0);ctl=copy.deepcopy(profile)
            pose=core.pose.copy();poses=[pose.copy()];v,w=core.v,core.w;base_ns=ctl.now_ns
            for tick in range(144):
                if tick%8==0:
                    ctl.now_ns=base_ns+round(tick/72*1e9);(v,w),diag=ctl.control(pose,v)
                    if diag['completed']:break
                pose=integrate_se2(pose,v,w,1/72);poses.append(pose.copy())
            np.testing.assert_array_equal(trace['poses'],poses);self.assertLessEqual(trace['duration_s'],1.0)
            self.assertEqual(ids,[c['id'] for c in e.transition.ensemble.chunks]);e.close()
    def test_periodic_reject_tick36_applies_at40(self):
        with tempfile.TemporaryDirectory() as d:
            e=RTCWithEC(Path(d));core,_=prepare(e);e.apply(core,refresh(),fresh())
            original=e.ec_check
            def reject(*args,**kw):
                r=original(*args,**kw);r['passed']=False;return r
            e.ec_check=reject
            for tick in range(1,41):
                before=core.pose.copy();e.plant.integrate(core,tick);e.integrate_record(before,core.pose)
                if tick==36:self.assertEqual(e.ec_pending['check_tick'],36)
                if tick%8==0:e.apply(core,refresh(tick),None)
            e.close();events=[json.loads(x) for x in (Path(d)/'exec_cert.jsonl').read_text().splitlines()]
            event=next(x for x in events if x['event']=='PERIODIC_APPLY')
            self.assertEqual((event['check_tick'],event['apply_tick'],event['delay_ticks']),(36,40,4))
    def test_te_periodic_expiry_uses_inspection_clock_not_last_control(self):
        with tempfile.TemporaryDirectory() as d:
            e=TEWithEC(Path(d));core,f=prepare(e);e.apply(core,refresh(),fresh())
            e._ec_refresh=refresh(32);e.sp.now_ns=refresh(32)['monotonic_ns']
            before=e.sp.now_ns;r=e.ec_check(core.pose,[.1,0],e.follower.path.points,f,.5,'NORMAL','PERIODIC',None,e.sp)
            self.assertEqual(r['rollout_start_monotonic_ns'],1_500_000_000)
            self.assertEqual(r['duration_s'],.5);self.assertEqual(e.sp.now_ns,before);e.close()
    def test_all_unsafe_without_detour_uses_existing_fallback_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            e=RTCWithEC(Path(d));core,_=prepare(e);f=field([.02,0]);f.observed=np.ones_like(f.occupied);f.metadata={'frame_id':1,'sim_s':0.,'publication_monotonic_ns':0}
            e.depth_maps=SimpleNamespace(snapshot=lambda:f)
            e.start_detour=lambda *a:self.fail('OURS-DETOUR must never call R3')
            e.apply(core,refresh(),fresh());self.assertEqual(e.mode,'STOP_WAIT')
            e.apply(core,refresh(8),fresh(2));self.assertEqual(e.recovery.state,'RECOVER_ROTATE')
            self.assertIsNone(e.repair_worker);e.close()
    def test_care_safe_fov_immediate_zero_and_preserves_center(self):
        from .runtime import CareProfile
        ctl=CareProfile();ctl.replace_path([[0,0],[0,1]],[0,0,0],.2);ctl.care_waypoint=np.array([0,1.]);ctl.mode='GO'
        q=np.zeros(3);v=.2;rotated=False
        for step in range(80):
            (v,w),diag=ctl.control(q,v)
            before=q.copy();q=integrate_se2(q,v,w,1/9)
            if diag['mode']=='ROTATE':rotated=True;np.testing.assert_array_equal(q[:2],before[:2]);self.assertEqual(v,0.)
            json.dumps(diag,allow_nan=False)
        self.assertTrue(rotated)

if __name__=='__main__':unittest.main()
