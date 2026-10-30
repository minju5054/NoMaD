import unittest
import tempfile,time,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from nomad_phase19r.repair import RepairGraph,initialize
from nomad_phase19r.test_repair import synthetic
from nomad_phase19s.srg import simulate
from nomad_phase17.config import scene
from .repair import RepairGraphR2,split_arclength,solve_sample
from .execution import SPAlignment,rollout


class Affine:
    error_bound=.01/np.sqrt(2)
    def query(self,p):return .01+.15*p[:,0]+.20*p[:,1],np.tile([.15,.20],(len(p),1))
    def exact_clearance(self,p):return float(self.query(p)[0].min())


class Tests(unittest.TestCase):
    def test_r2_zone_and_analytic_jacobian(self):
        B=[.003,.004,.17];xy=np.c_[np.linspace(.003,.733,8),.004+.08*np.linspace(0,.73,8)**2]
        q,_=initialize(xy,B);g=RepairGraphR2(q,B,Affine());base=RepairGraph(q,B,Affine());x=g.initial.copy();x[3]+=.003
        thresholds,s=g.thresholds(x);self.assertTrue(np.any(s<=.30) and np.any(s>.30))
        np.testing.assert_allclose(g.constraints(x)[0][63:],base.constraints(x)[0][63:],atol=0,rtol=0)
        np.testing.assert_allclose(g.constraints(x)[0][:63]-base.constraints(x)[0][:63],.025-thresholds,atol=1e-15,rtol=0)
        for f in (g.residual_jacobian,g.constraints):
            _,j=f(x);fd=np.column_stack([(f(x+e*1e-7)[0]-f(x-e*1e-7)[0])/(2e-7) for e in np.eye(14)])
            np.testing.assert_allclose(j,fd,atol=1e-5,rtol=0)
        np.testing.assert_array_equal(g.residual_jacobian(x)[0],base.residual_jacobian(x)[0])

    def test_certificate_splits_continuous_path(self):
        p=np.c_[np.linspace(0,.7,8),np.zeros(8)];g=RepairGraphR2(p,[0,0,0],Affine())
        near,far=split_arclength(p);np.testing.assert_allclose(near[-1],[.3,0]);np.testing.assert_array_equal(near[-1],far[0])
        r=g.certificate(p);self.assertTrue(r['certificate_pass']);self.assertLess(r['near_exact_clearance_m'],.025)
        self.assertGreaterEqual(r['far_exact_clearance_m'],.025)
        self.assertTrue(solve_sample(p,[0,0,0],synthetic())['accepted'])

    def test_sp_path_replacement_and_braking_profile(self):
        c=SPAlignment();c.replace_path([[0,0],[.4,0],[.8,0]],[0,0,0],.3)
        (v,w),_=c.control([0,0,0],.3);self.assertEqual(v,.3);self.assertEqual(w,0.)
        c.replace_path([[0,0],[.28,0],[.3,0],[.3,.02],[.3,.2]],[0,0,0],.3)
        self.assertEqual(c.plan_generation,2);self.assertLess(c.plan['v_m_s'][1],.3)

    def test_start_alignment_conditions_and_no_pivot(self):
        c=SPAlignment();xy=[[0,0],[0,.15],[0,.3]]
        c.replace_path(xy,[0,0,0],0.);self.assertTrue(c.trigger_S)
        (v,w),_=c.control([0,0,0],0.);self.assertEqual(v,0.);self.assertEqual(w,.4)
        c.replace_path(xy,[0,0,0],.01);self.assertTrue(c.trigger_S)
        c.replace_path(xy,[0,0,np.deg2rad(60)],.01);self.assertFalse(c.trigger_S)
        c.replace_path(xy,[0,0,np.deg2rad(60)],0.);self.assertTrue(c.trigger_S)
        c.replace_path([[0,0],[.1,0],[.1,.1]],[0,0,0],0.);self.assertFalse(c.trigger_S)

    def test_nonnegative_start_floor_and_negative_B_rejection(self):
        xy=np.c_[np.linspace(0,.7,8),np.zeros(8)]
        g=RepairGraphR2(xy,[0,0,0],Affine());self.assertEqual(g.near_threshold,0.)
        class Negative(Affine):
            def query(self,p):
                d,j=super().query(p);return d-.02,j
        result=solve_sample(xy,[0,0,0],Negative())
        self.assertFalse(result['accepted']);self.assertFalse(result['solver_started'])
        self.assertEqual(result['disposition'],'NEGATIVE_DEPTH_AT_B')

    def test_moving_alignment_brakes_before_rotation(self):
        xy=[[0,0],[0,.15],[0,.4]];r=rollout([0,0,0],xy,.2,scene('CL'))
        self.assertTrue(r['trigger_S']);self.assertEqual(r['alignment_count'],1)
        self.assertGreater(r['braking_time_s'],0.);self.assertGreater(r['rotation_time_s'],0.)
        self.assertTrue(all(c['v']==0. for c in r['commands'] if c['mode']=='ROTATE'))
        v=np.r_[.2,[c['v'] for c in r['commands']]]
        self.assertLessEqual(np.max(np.abs(np.diff(v))),.5/9+1e-12)

    def test_s_only_matches_protected_s_without_pivots(self):
        for xy,v in [([[0,0],[.15,0],[.3,0]],.1),([[0,0],[0,.15],[0,.3]],0.)]:
            r=rollout([0,0,0],xy,v,scene('CL'))
            old=simulate([0,0,0],xy,v,'SRG',ticks=108)
            np.testing.assert_array_equal(r['poses'],old['poses'])
            self.assertEqual(r['trigger_P'],0)

    def test_repair_deadline_and_no_queued_retry(self):
        from .worker import disposition
        self.assertEqual(disposition(None,0,499_000_000),'WAIT')
        self.assertEqual(disposition(None,0,501_000_000),'TIMEOUT')
        self.assertEqual(disposition(dict(end_ns=499_000_000,selected_sample=0),0,555_000_000),'ACCEPTED')
        self.assertEqual(disposition(dict(end_ns=501_000_000,selected_sample=0),0,555_000_000),'TIMEOUT')

    def test_runtime_safe_path_and_timeout(self):
        from .runtime import Execution
        for method in ('M1_ROTATE','M2_REPAIR'):
            with tempfile.TemporaryDirectory() as folder:
                ex=Execution(method,Path(folder));field=synthetic();ex.depth_maps=SimpleNamespace(snapshot=lambda:field)
                core=SimpleNamespace(pose=np.array([0.,0.,0.]),v=.1,w=0.)
                refresh=dict(valid=True,monotonic_ns=time.monotonic_ns(),simulation_time_s=0.)
                xy=np.c_[np.linspace(.05,.5,8),np.zeros(8)]
                switch=dict(id=0,observation_pose=[0,0,0],observation_sim_s=0.,overnight_metric_samples=np.repeat(xy[None],8,axis=0).tolist())
                ex.apply(core,refresh,switch);self.assertEqual(ex.mode,'NORMAL');self.assertEqual(ex.next_repair,0)
                self.assertEqual(ex.sp.plan_generation,1);self.assertAlmostEqual(core.v,.5/9)
                if method=='M2_REPAIR':
                    ex.repair_pending=dict(job_id=0,id=0,dispatch_ns=time.monotonic_ns()-600_000_000,B=[0,0,0])
                    status=ex.collect_repair(core,refresh,None);self.assertEqual(status,'TIMEOUT');self.assertIsNone(ex.repair_pending)
                ex.close()

    def test_main_matrix_sockets_and_fake_report(self):
        from .campaign import plan_jobs
        from .report import render_main,main_groups,main_decision
        jobs=plan_jobs(Path('/tmp/phase20-test-'+'x'*90));self.assertEqual(len(jobs),12)
        self.assertTrue(all(j['socket_bytes']<100 for j in jobs))
        records=[dict(**j,technical_validation='PASS',success=(j['index']<77 if j['method']=='M1_ROTATE' else j['index']<79),
            safety_failure=False,collision=False,corridor=False,stuck=False,stopped_fraction=.2,box_passage_time_s=12.,classification='STUCK') for j in jobs]
        self.assertEqual(main_decision(main_groups(records))['label'],'REPAIR_BETTER_SO')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);render_main(records,root,root/'result',root/'report.md',figures=False)
            self.assertTrue((root/'result/decisions.json').exists());self.assertIn('REPAIR_BETTER_SO',(root/'report.md').read_text())


if __name__=='__main__':unittest.main()
