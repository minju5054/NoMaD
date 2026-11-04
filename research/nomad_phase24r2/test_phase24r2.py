import json, tempfile, unittest
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.optimize import minimize
from nomad_phase15.depth_sdf import DepthSDF
from nomad_phase15b.depth import Snapshot
from nomad_phase24r.graph import GraphR
from nomad_phase24r.safety import PlanningField, certificate
from .graph import GraphR2, return_line, fan_paths
from .online_config import runtime_config, protocol, verify
from .online_metrics import return_metrics
from .online_report import decision, generate


def field(blocked=False):
    f=DepthSDF([-1.,-2.,3.,2.]);f.observed[:]=True
    yy,xx=np.indices(f.values.shape);xy=f.origin+np.stack([xx,yy],axis=-1)*f.h
    if blocked:
        f.occupied[:]=(xy[:,:,0]>=.60)&(xy[:,:,0]<=.80)&(np.abs(xy[:,:,1])<=.12)
        f.values=distance_transform_edt(~f.occupied,sampling=f.h)-f.radius
    s=Snapshot(f,dict(frame_id=0));return s,PlanningField(s,s)


def graphs(mode='DETOUR',B=(0.,0.,0.),blocked=False):
    B=np.asarray(B);base,f=field(blocked)
    u=np.array([1.,0.]);line=dict(anchor_world=[0.,-.1],u_ref=u.tolist(),sigma_m=.30,weight=1.)
    weights=dict(mode=mode,u_ref=u.tolist() if mode=='DETOUR' else None,return_line=line)
    ref=fan_paths(B,u)[1]
    args=(B,0.,ref[None],.10,f,weights,10**30)
    return GraphR2(*args),GraphR(*args),ref,base


class Tests(unittest.TestCase):
    def test_line_is_component_birth_pose_or_actual_entry(self):
        poses=np.c_[np.arange(300)/100.,np.arange(300)/200.,np.zeros(300)]
        line=return_line(poses,250,[0,1],dict(component=dict(t_new_tick=100)))
        self.assertEqual(line['anchor_world'],poses[100,:2].tolist())
        fallback=return_line(poses,250,[1,0],dict(source='20F_A_FALLBACK'))
        self.assertEqual(fallback['anchor_world'],poses[250,:2].tolist())
        self.assertEqual(fallback['source'],'DETOUR_ENTRY_POSE')

    def test_gradient_rotated_frame_and_only_one_added_factor(self):
        g,old,path,_=graphs(B=(.15,.2,.4));x=g.initial(path)
        x[28]+=.13
        v,j=g.return_term(x);eps=1e-6
        numeric=np.array([(g.return_term(x+np.eye(len(x))[i]*eps)[0]-g.return_term(x-np.eye(len(x))[i]*eps)[0])/(2*eps) for i in range(len(x))])
        np.testing.assert_allclose(j,numeric,atol=1e-5,rtol=0)
        ov,oj=old.objective(x);nv,nj=g.objective(x)
        self.assertAlmostEqual(nv-ov,v,places=10);np.testing.assert_allclose(nj-oj,j,atol=1e-10)
        self.assertEqual(nv,g.objective(x.copy())[0]) # no double addition through cache
        np.testing.assert_array_equal(g.constraints(x)[0],old.constraints(x)[0])
        np.testing.assert_array_equal(g.constraints(x)[1],old.constraints(x)[1])

    def test_normal_is_bitwise_frozen_objective_and_constraints(self):
        g,old,path,_=graphs(mode='NORMAL');x=g.initial(path)
        self.assertEqual(g.objective(x)[0],old.objective(x)[0])
        np.testing.assert_array_equal(g.objective(x)[1],old.objective(x)[1])
        np.testing.assert_array_equal(g.constraints(x)[0],old.constraints(x)[0])

    def test_blocked_return_line_still_has_feasible_detour(self):
        g,_,_,base=graphs(blocked=True)
        self.assertFalse(certificate(np.c_[np.linspace(0,1.5,11),np.zeros(11)],[0,0,0],base,base)['passed'])
        # Same seven starts and SLSQP options, each exactly once; no tuning.
        good=[]
        for path in fan_paths([0,0,0],[1,0]):
            x=g.initial(path)
            r=minimize(g.objective,x,jac=True,method='SLSQP',bounds=g.bounds,
                constraints=[dict(type='ineq',fun=lambda z:g.constraints(z)[0],jac=lambda z:g.constraints(z)[1])],
                options=dict(maxiter=100,ftol=1e-8))
            p,_,_=g.unpack(r.x)
            # Frozen anytime policy accepts feasible iterates even if SLSQP
            # later reaches maxiter; solver success is not an added condition.
            if np.min(g.constraints(r.x)[0])>=-1e-7 and certificate(p,[0,0,0],base,base)['passed']:
                good.append(p)
        self.assertTrue(good,'No feasible detour around the synthetic blocker')

    def test_matrix_and_runtime_only_seed_namespace_change(self):
        from nomad_phase24r.online_config import runtime_config as old
        from .campaign import jobs
        verify();p=protocol();self.assertEqual(len(p['main_order']),12)
        self.assertEqual({j['index'] for j in p['main_order']},{151,152,153,154})
        self.assertEqual({j['scene'] for j in p['main_order']},{'L2'})
        for m in p['methods']:
            a=runtime_config(m,151);b=old(m,95)
            for k in ('phase24r2','seed_offset','run_id'):a.pop(k,None);b.pop(k,None)
            self.assertEqual(a,b)
        self.assertEqual(len(jobs(Path('/tmp/phase24r2_test_plan'))),12)
        with self.assertRaises(AssertionError):runtime_config('G',151,level='SLW')

    def test_metrics_missing_followup_is_not_extrapolated(self):
        t=np.arange(10.);y=t/10;topo=[dict(time_s=0.,closest=1),dict(time_s=5.,closest=4),dict(time_s=9.,closest=6)]
        r=return_metrics(t,y,[(1.,3.)],2.,topo)
        self.assertAlmostEqual(r['detour_max_abs_y_m'],.3)
        self.assertAlmostEqual(r['post_passage_5s_abs_y_m'],.7)
        self.assertEqual(r['post_detour_closest_progress'][0]['delta_5s'],3)
        self.assertIsNone(return_metrics(t,y,[],6.,topo)['post_passage_5s_abs_y_m'])

    def test_decision_and_synthetic_report(self):
        self.assertEqual(decision(dict(success=3,collision=0,box_passage=3),dict(success=4,box_passage=4))['label'],'R2_PASS')
        self.assertEqual(decision(dict(success=4,collision=1,box_passage=4),dict(success=4,box_passage=4))['label'],'R2_FAIL')
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'metrics').mkdir();doc=root/'report.md';doc.write_text('# Synthetic fixture\n')
            for j in protocol()['main_order']:
                r=dict(j,technical_validation='PASS',classification='SUCCESS',success=True,collision=False,corridor=False,box_passage=True)
                (root/'metrics'/f"{j['index']}_{j['method']}.json").write_text(json.dumps(r))
            result=generate(root,root/'out',doc,figures=False)
            self.assertEqual(result['label'],'R2_PASS');self.assertTrue((root/'out/summary.csv').exists())
            self.assertIn('post_passage_5s_abs_y_m',doc.read_text())


if __name__=='__main__':unittest.main()
