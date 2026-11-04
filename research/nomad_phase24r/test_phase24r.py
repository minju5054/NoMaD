import json,unittest,math
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from .geometry import verify_bounds
from .safety import certificate
from .candidates import CandidateBank
from .trigger import PersistentCellHistory,component_sets,passed,approach_progress,PersistentNoProgress
from .follower import ChordFollower
from .graph import GraphR

class Field:
    h=.01;error_bound=.01;radius=.09
    def __init__(self,d=.1,exact=.1):
        self.d=d;self.exact=exact;self.h=.01;self.error_bound=.01;self.radius=.09;self.origin=np.array([-1.,-1.]);self.values=np.full((201,201),d);self.occupied=np.zeros((201,201),bool);self.observed=np.ones((201,201),bool)
    def query(self,q):return np.full(len(q),self.d),np.zeros((len(q),2))
    def exact_clearance(self,q):return self.exact

class Tests(unittest.TestCase):
    def test_wall_inner_faces_must_equal_corridor(self):
        c=dict(corridor=dict(xmin=-1.,xmax=6.,half_width=.9))
        good=dict(LeftWall=[[-1,.9,0],[6,1,2]],RightWall=[[-1,-1,0],[6,-.9,2]],EndWall=[[6,0,0],[6.1,1,2]],StartWall=[[-1.1,0,0],[-1,1,2]])
        self.assertEqual(verify_bounds(c,good)['status'],'PASS')
        good['LeftWall'][0][1]=1.5
        with self.assertRaises(ValueError):verify_bounds(c,good)
    def test_certificate_uses_nine_points_error_and_exact(self):
        path=np.array([[0.,0.],[.2,0.],[.4,0.]])
        # 0.04 - h/sqrt2 - L/16 - .025 > 0: pass.
        base=strict=Field(.06,.06);ok=certificate(path,[0,0,0],base,strict);self.assertTrue(ok['passed'])
        # Nodes/midpoint would see .04, but h/sqrt2+L/16 rejects this output.
        base=strict=Field(.04,.06);bad=certificate(path,[0,0,0],base,strict);self.assertFalse(bad['passed']);self.assertEqual(bad['reason'],'NINE_POINT_MARGIN')
        base=Field(.06,-.001);strict=Field(.06,-.001);self.assertEqual(certificate(path,[0,0,0],base,strict)['reason'],'EXACT_DISTANCE')
    def test_certificate_bank_replaces_rejected_best(self):
        base=strict=Field();bank=CandidateBank([0,0,0],base,strict,10**30)
        invalid=dict(kind='FEASIBLE',index=0,cost=1.,ready_ns=1,path=[[0,0],[1,0]],poses=[[0,0,0],[1,0,0]],dt=[1.])
        valid=dict(kind='FEASIBLE',index=1,cost=2.,ready_ns=1,path=[[0,0],[0,1]],poses=[[0,0,0],[0,1,0]],dt=[1.])
        with patch('nomad_phase24r.candidates.certificate',side_effect=[dict(passed=False,reason='NINE_POINT_MARGIN'),dict(passed=True,reason='PASS')]):bank.ingest(invalid);bank.ingest(valid)
        self.assertEqual(bank.alternatives()[0]['index'],1);self.assertEqual(bank.statistics()['certificate_rejections'],1);self.assertTrue(bank.statistics()['alternative_initializer_used'])
    def test_chord_rotation_precedes_pp_and_preserves_position(self):
        q=np.array([[0.,0.,0.],[0.,.2,-math.pi/2],[0.,.4,-math.pi/2]])
        f=ChordFollower(q,[1.,1.]);command,diag=f.control([0,0,0],0.)
        self.assertEqual(diag['mode'],'GRAPH_ROTATION');self.assertTrue(diag['rotation_priority']);self.assertAlmostEqual(command[0],0.)
        self.assertTrue(diag['THETA_CHORD_INCONSISTENT']);self.assertGreater(diag['theta_chord_error_deg'],90)
        # At chord heading, segment is marked once; PP can then control.
        command,diag=f.control([0,0,math.pi/2],0.);self.assertEqual(diag['mode'],'PP_GRAPH_SPEED');self.assertGreaterEqual(command[0],0.)
    def test_persistent_component_and_shared_set_approach(self):
        history=PersistentCellHistory((4,4));free=np.full((4,4),-1,np.int32);free[1:3,1:4]=1;occ=np.zeros((4,4),bool);occ[1:3,1:4]=True
        history.update(free,occ,100);history.update(free,occ,10000) # no10-second expiry
        snap=SimpleNamespace(occupied=occ,observed=np.ones((4,4),bool),new_component_ids=history.new_component_ids,component_births=history.births,origin=np.zeros(2),h=.01,radius=.09)
        components=component_sets(snap);self.assertIn(1,components);self.assertFalse(passed(components[1],[-.2,0,0],[1,0],.09,.01))
        drop,old,new=approach_progress(np.array([[1.,0.]]),[0.,0.,0.],[.05,0.,0.]);self.assertLess(drop,.1);self.assertEqual((old,new),(1.,.95))
    def test_graph_hard_constraints_remain_nodes_midpoints(self):
        field=Field();field.origin=np.array([-1.,-1.]);field.values=np.ones((201,201));field.occupied=np.zeros((201,201),bool)
        reference=np.c_[np.linspace(0,1,11),np.zeros(11)]
        wrapped=SimpleNamespace(base=field,strict=field,origin=field.origin,h=field.h,radius=field.radius,values=field.values,occupied=field.occupied,error_bound=field.error_bound,query=field.query)
        g=GraphR([0,0,0],0.,np.array([reference]),.1,wrapped,dict(mode='NORMAL',u_ref=None),10**30)
        h,_=g.constraints(g.initial(np.c_[np.linspace(0,1,11),np.zeros(11)]));self.assertEqual(len(h),51) # 21 obstacle points + 10v +20omega
    def test_shared_install_patches_c0_c1_trigger_and_certificate_only(self):
        import nomad_phase20f.runtime as f
        import nomad_phase20d.runtime as d
        from .online_execution import install
        install()
        from .trigger import PersistentNoProgress
        self.assertIs(f.NewObstacleNoProgress,PersistentNoProgress)
        self.assertTrue(getattr(d.Execution,'_phase24r_patched'))
        self.assertIsNot(d.Execution.certificate.__module__.split('.')[-1],'runtime')
    def test_goal_entry_predicate_is_shared_runtime_policy(self):
        from pathlib import Path
        source=Path('research/nomad_isaac/async_runtime.py').read_text()
        self.assertIn('distance <= c["goal_tolerance_m"]',source)
        self.assertNotIn('goal_tolerance_m',Path('research/nomad_phase24r/live.py').read_text())
if __name__=='__main__':unittest.main()
