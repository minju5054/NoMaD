import math,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .alignment import NoAlignment
from .storage import cleanup

class IndependentTests(unittest.TestCase):
    def test_ninety_is_not_backward(self):
        c=NoAlignment();p=[[0,0],[0,.1],[0,.3]]
        for v in (0.,.2):
            c.replace_path(p,[0,0,0],v)
            self.assertFalse(c.trigger_S);self.assertEqual(c.mode,'GO')
    def test_more_than_ninety_brakes_then_rotates(self):
        c=NoAlignment();c.replace_path([[0,0],[-.1,.01],[-.3,.01]],[0,0,0],.2)
        self.assertTrue(c.trigger_S);self.assertEqual(c.mode,'BRAKE')
        (v,w),_=c.control([0,0,0],.2)
        self.assertLessEqual(abs(v-.2),.5/9+1e-12);self.assertLessEqual(abs(w),.4)
    def test_middle_suffix_and_short_endpoint(self):
        c=NoAlignment();p=[[0,0],[.2,0],[.4,0],[.6,0]]
        c.replace_path(p,[.3,0,0],0.);self.assertFalse(c.trigger_S)
        c.replace_path(p,[.59,0,math.pi],0.);self.assertFalse(c.trigger_S)
    def test_no_alignment_keeps_pp_limits(self):
        c=NoAlignment();c.replace_path([[0,0],[.1,.1],[.3,.3]],[0,0,0],0.)
        self.assertFalse(c.trigger_S)
        (v,w),_=c.control([0,0,0],0.)
        self.assertGreater(v,0);self.assertLessEqual(v,.5/9);self.assertLessEqual(abs(w),.4)
    def test_cache_cleanup_allowlist_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for name in ('portable/cache','portable/config','pycache','depth'):
                (p/name).mkdir(parents=True);(p/name/'sentinel').write_text('keep unless cache')
            with self.assertRaises(RuntimeError):cleanup(p,False)
            r=cleanup(p,True)
            self.assertEqual(r['removed'],['portable/cache','pycache'])
            self.assertTrue((p/'depth/sentinel').exists());self.assertTrue((p/'portable/config/sentinel').exists())
    def test_c0_installer_body_is_unchanged(self):
        from .runtime import NAExecution,PathInstaller
        self.assertIs(NAExecution.new_path.__code__,PathInstaller.new_path.__code__)
        self.assertIs(NAExecution.new_path.__globals__['SPAlignment'],NoAlignment)
        self.assertIsNot(PathInstaller.new_path.__globals__['SPAlignment'],NoAlignment)
    def test_installed_path_and_mode_preserved(self):
        from .runtime import NAExecution
        obj=object.__new__(NAExecution);obj.last_command=[0.,0.];rows=[]
        obj.rlog=lambda event,**kw:rows.append(dict(event=event,**kw))
        obj.new_path([[0,0],[0,.1],[0,.3]],SimpleNamespace(pose=np.array([0.,0.,0.])),dict(monotonic_ns=1,simulation_time_s=0.),3,'SAFE')
        self.assertFalse(obj.sp.trigger_S);self.assertEqual(obj.mode,'NORMAL');self.assertEqual(obj.path_source_id,3)
        self.assertEqual(rows[0]['threshold_deg'],90.);self.assertFalse(rows[0]['alignment'])

if __name__=='__main__':unittest.main()
