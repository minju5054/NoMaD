import tempfile,time,unittest,json
from pathlib import Path
from types import SimpleNamespace,MappingProxyType
import numpy as np
from nomad_phase19r.test_repair import synthetic
from .execution import RawExecution,TEExecution,make_execution
from nomad_phase20f.runtime import Execution as Frozen

class Tests(unittest.TestCase):
    def switch(self,i=0):
        xy=np.c_[np.linspace(.1,1.2,8),np.zeros(8)];return dict(id=i,observation_pose=[0,0,0],observation_sim_s=0.,received_monotonic_ns=time.monotonic_ns(),overnight_metric_samples=np.repeat(xy[None],8,axis=0).tolist())
    def test_raw_has_no_depth_dependency(self):
        with tempfile.TemporaryDirectory() as d:
            e=RawExecution(Path(d));core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.)
            try:e.apply(core,dict(valid=True,simulation_time_s=0.,monotonic_ns=time.monotonic_ns()),self.switch());self.assertGreater(core.v,0);self.assertEqual(e.recovery.count,0)
            finally:e.close()
    def test_TE_sp_steering_and_expiry(self):
        with tempfile.TemporaryDirectory() as d:
            e=TEExecution(Path(d));f=synthetic(False);f.metadata=MappingProxyType(dict(file='/unused'));e.depth_maps=SimpleNamespace(snapshot=lambda:f);core=SimpleNamespace(pose=np.zeros(3),v=0.,w=0.);sw=self.switch();now=sw['received_monotonic_ns']
            try:
                e.apply(core,dict(valid=True,simulation_time_s=0.,monotonic_ns=now),sw);self.assertGreater(core.v,0);self.assertEqual(len(e.transition.ensemble.chunks),1)
                e.apply(core,dict(valid=True,simulation_time_s=2.,monotonic_ns=now+2_000_000_000),None);self.assertEqual(len(e.transition.ensemble.chunks),0)
            finally:e.close()
    def test_frozen_graph_dispatch(self):
        # Main Graph/M1 methods must continue to use the protected20F class.
        self.assertIs(make_execution.__globals__['Frozen'],Frozen)
if __name__=='__main__':unittest.main()
