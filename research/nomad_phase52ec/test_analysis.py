import copy,json,unittest
import numpy as np
from nomad_phase32o.test_exec_cert import field
from nomad_phase32o.exec_cert import rollout as old_rollout,swept_clearance
from nomad_phase32.policy import CappedNA
from .rollout import rollout,certify
from . import fast
from .graph import ExecutionGraph,reference

class Tests(unittest.TestCase):
    def test_endpoint_tail_acceleration_and_omega(self):
        f=field([.4,0]);path=[[0,0],[.2,0]];old=old_rollout([0,0,0],[.3,.1],path)
        new=rollout([0,0,0],[.3,.1],path)
        np.testing.assert_allclose(new['poses'][:len(old['poses'])],old['poses'],atol=1e-12,rtol=0)
        self.assertTrue(new['stopped']);self.assertEqual(new['terminal_vw'],[0.,0.]);self.assertGreater(new['duration_s'],old['duration_s'])
        i=round(new['brake_start_s']*72);self.assertTrue(np.all(new['commands'][i:,1]==0))
        self.assertLessEqual(abs(np.diff(np.r_[new['commands'][i-1,0],new['commands'][i::8,0],0.])).max(),.5/9+1e-12)
    def test_horizon_tail_and_periodic_control_phase(self):
        ctl=CappedNA();ctl.replace_path([[0,0],[3,0]],[0,0,0],.3)
        new=rollout([0,0,0],[.3,0],[[0,0],[3,0]],controller=ctl,start_tick=36)
        self.assertEqual(new['stop_reason'],'HORIZON');self.assertEqual(new['control_rounding_ticks'],4);self.assertGreater(new['duration_s'],2.)
        self.assertEqual(ctl.follower.progress,0.)
    def test_compiled_trace_matches_python_and_exact_arc_certificate(self):
        rng=np.random.default_rng(20261116)
        cases=[(np.array([[0,0],[.2,0]]),[0,0,0],[.3,0]),(np.array([[0,0],[-1,0]]),[0,0,0],[.2,.2])]
        for _ in range(30):
            path=np.c_[np.linspace(0,rng.uniform(.15,1.5),8),np.cumsum(rng.normal(0,.03,8))];path[0]=0
            cases.append((path,[0,0,rng.uniform(-2,2)],[rng.uniform(0,.3),rng.uniform(-.4,.4)]))
        for path,B,vw in cases:
            for cap in (None,.1):
                a=rollout(B,vw,path,cap);b=fast.trace(path,B,vw,cap)
                self.assertEqual(len(a['poses']),len(b['poses']))
                np.testing.assert_allclose(a['poses'],b['poses'],atol=1e-9,rtol=0)
                np.testing.assert_allclose(a['commands'],b['commands'],atol=1e-9,rtol=0)
                for site in ([.35,.12],[.7,-.15]):
                    f=field(site);expected=swept_clearance(f,a['poses'],a['commands'])
                    value=fast.clearance(b,f)
                    if expected['clearance_m'] is not None:self.assertAlmostEqual(value,min(.075,expected['clearance_m']),places=8)
    def test_fixed_pose_and_objective_only(self):
        q=reference([[0,0],[.4,.2],[1,.3]],[.1,0,0]);g=ExecutionGraph(q,[.1,0,0],[0,0],field())
        self.assertEqual(g.objective(g.x0)[0],0);x=g.x0+.01;value,j=g.objective(x)
        self.assertAlmostEqual(value,14*.01**2);np.testing.assert_allclose(j,.02)
        np.testing.assert_array_equal(g.points(x)[0],[.1,0])
    def test_tail_reject_and_json(self):
        f=field([.33,0]);r=certify([0,0,0],[.3,0],[[0,0],[.2,0]],f)
        self.assertFalse(r['passed']);json.dumps(r,allow_nan=False)

if __name__=='__main__':unittest.main()
