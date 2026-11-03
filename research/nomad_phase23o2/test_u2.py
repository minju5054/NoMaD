import json,tempfile,time,unittest,multiprocessing as mp
from pathlib import Path
import numpy as np
from nomad_phase23.optimized import OptimizedGraph
from nomad_phase23.runtime import managed_pool
from nomad_phase20d.pool import initialize,ping
from nomad_phase19r.test_repair import synthetic
from .graph import U2Graph,mixture,plan,FIXED_WEIGHTS
from .inputs import histories

class FreeField:
    origin=np.array([-2.,-2.]);h=.01;radius=.09;values=np.ones((501,501));occupied=np.zeros((501,501),bool)
    def query(self,q):return np.ones(len(q)),np.zeros((len(q),2))

def make(c=2.,T=1.,ages=None,v0=.03):
    path=np.c_[np.linspace(0,1.1,11),.08*np.sin(np.linspace(0,1.,11))]
    candidates=np.array([path+[0,i*.008] for i in range(8)])
    g=U2Graph([0.,0.,0.],v0,candidates,.08,FreeField(),dict(FIXED_WEIGHTS,u2=dict(c=c,T_m=T,ages_s=ages if ages is not None else [0.]*8)),time.monotonic_ns()+60_000_000_000)
    x=g.initial(path);x[30]=.36
    return g,x,path,candidates

def fd(fn,x):
    eye=np.eye(len(x))*1e-6;return np.array([(fn(x+d)-fn(x-d))/(2e-6) for d in eye]).T

class Tests(unittest.TestCase):
    def test_cauchy_and_soft_acceleration_analytic_gradient(self):
        for c in (1.,2.,4.):
            g,x,_,_=make(c=c,ages=[0,.1,.2,.3,.4,.5,.6,.7])
            _,jac=g.objective(x);numeric=fd(lambda z:g.objective(z)[0],x)
            self.assertLess(float(np.max(np.abs(jac-numeric))),1e-5)
            h,j=g.constraints(x);numeric=fd(lambda z:g.constraints(z)[0],x)
            self.assertEqual(len(h),51);self.assertLess(float(np.max(np.abs(j-numeric))),1e-5)
    def test_acceleration_boundary_soft_but_speed_omega_time_stay_hard(self):
        path=np.c_[np.linspace(0,.3,11),np.zeros(11)];samples=np.repeat(path[None],8,0)
        settings=dict(FIXED_WEIGHTS,u2=dict(c=2.,T_m=1.,ages_s=[0.]*8))
        g=U2Graph([0,0,0],0.,samples,.1,FreeField(),settings,time.monotonic_ns()+5_000_000_000)
        g0=U2Graph([0,0,0],.3,samples,.1,FreeField(),settings,time.monotonic_ns()+5_000_000_000)
        x=g.initial(path);x[30:]=.1
        self.assertGreaterEqual(g.constraints(x)[0].min(),-1e-12)
        self.assertLess(g.full_constraints(x)[0].min(),-2.)
        self.assertAlmostEqual(g.objective(x)[0]-g0.objective(x)[0],2500.,places=7)
        np.testing.assert_array_equal(g.constraints(x)[0],g.full_constraints(x)[0][:-20])
        self.assertTrue(np.all(g.bounds.lb[30:]==.05));self.assertTrue(np.all(g.bounds.ub[30:]==1.))
    def test_history_frame_age_and_no_future_arrival(self):
        native=np.repeat(np.c_[np.linspace(.1,.8,8),np.zeros(8)][None],8,0).tolist()
        with tempfile.TemporaryDirectory() as tmp:
            events=[dict(id=i,received_sim_s=t,overnight_metric_samples=native,observation_pose=[1.,1.,np.pi/2]) for i,t in [(0,.1),(1,1.),(2,2.),(3,2.4),(4,3.)]]
            (Path(tmp)/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
            c=dict(run=tmp,tick=180,fresh_id=2);histories([c],{})
            self.assertEqual([r['fresh_id'] for r in c['memory_sets']],[1]);self.assertEqual(c['memory_sets'][0]['age_s'],1.5)
            np.testing.assert_allclose(c['memory_sets'][0]['samples_world'][0][0],[1.,1.1],atol=1e-12)
            c.update(samples_world=c['memory_sets'][0]['samples_world'],old_path=None)
            B=[1.,1.2,np.pi/2];q,sigma,ages,meta,_=mixture(c,B)
            self.assertEqual(q.shape,(16,11,2));self.assertEqual(meta[8]['age_s'],1.5)
            g=U2Graph(B,.2,q,sigma,FreeField(),dict(FIXED_WEIGHTS,u2=dict(c=2.,T_m=.5,ages_s=ages.tolist())),time.monotonic_ns()+5_000_000_000)
            np.testing.assert_allclose(g.candidates,(q-np.array(B[:2]))@g.R)
            self.assertAlmostEqual(g.component_sigma[8],sigma*4);self.assertEqual(g.age_cost[8],3.)
    def test_no_astar_old_component(self):
        samples=np.repeat(np.c_[np.linspace(0,1,8),np.zeros(8)][None],8,0).tolist()
        c=dict(samples_world=samples,fresh_id=0,memory_sets=[dict(kind='ASTAR_OLD',age_s=.5,samples_world=samples,fresh_id=-1)])
        with self.assertRaisesRegex(AssertionError,r'A\*'):mixture(c,[0,0,0])
    def test_large_c_limit_preserves_other_factors(self):
        g,x,path,candidates=make(c=1e6,v0=.2);x=g.initial(path)
        base=OptimizedGraph([0,0,0],.2,candidates,.08,FreeField(),FIXED_WEIGHTS,time.monotonic_ns()+5_000_000_000)
        self.assertLess(np.max(np.abs(g.objective(x)[1]-base.objective(x)[1])),1e-5)
        self.assertAlmostEqual(g.objective(x)[0],base.objective(x)[0],places=7)
    def test_four_worker_u2_anytime_and_application(self):
        ctx=mp.get_context('spawn');queue=ctx.Queue()
        with tempfile.TemporaryDirectory() as tmp,managed_pool(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
            futures=[pool.submit(ping) for _ in range(4)]
            for _ in range(4):queue.get(timeout=30)
            for f in futures:f.result()
            file=Path(tmp)/'snapshot.npz';synthetic(True).save(file)
            sample=np.c_[np.linspace(0,1,8),np.full(8,.4)];case=dict(B=[0,.4,0],tick=0,previous_vw=[.2,0],samples_world=np.repeat(sample[None],8,0).tolist(),old_path=sample.tolist(),fresh_id=0,memory_sets=[],snapshot_file=str(file))
            result=plan(pool,case,dict(c=2.,T_m=1.),dict(prediction_mode='existing_rollout'))
            self.assertTrue(result['accepted']);self.assertEqual(result['application_delay_s'],.5);self.assertLessEqual(result['initialization_count'],10)
            np.testing.assert_allclose(result['poses'][0],result['B_pred'],atol=1e-12)
            self.assertLessEqual(result['selected']['received_ns'],result['deadline_ns'])


class ReportTests(unittest.TestCase):
    def test_fake_report_tables_decision_and_figures(self):
        from unittest.mock import patch
        from . import report
        from .inputs import write
        import copy
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'results';here=root/'code';out.mkdir();here.mkdir();(root/'docs').mkdir()
            cases=[];path=np.c_[np.linspace(0,1,11),np.full(11,.4)];B=[0.,.4,0.]
            for identity,group in [('H0000','static'),('S0000','sudden')]:
                box=dict(id='test_box',center_xy_m=[.5,0.],size_xyz_m=[.2,.3,.8]);cfg=dict(start_pose=B,goal_pose=[1.,.4,0.],agent_radius_m=.09,corridor=dict(xmin=-1,xmax=2,half_width=1.),obstacles=[box] if group=='sudden' else [])
                c=dict(case_id=identity,group=group,scene='SLW' if group=='static' else 'L2',stratum='HELDOUT_STATIC' if group=='static' else 'SEEN_SUDDEN',B=B,oracle_config=cfg,spawn=dict(obstacle=box) if group=='sudden' else None,samples_world=np.repeat(path[None],8,0).tolist(),fresh_id=0,memory_sets=[],run=identity)
                methods={}
                for name in (('U2','U','C0','C1') if group=='sudden' else ('U2','U','C0')):
                    row=dict(case_id=identity,group=group,scene=c['scene'],stratum=c['stratum'],method=name,accepted=True,oracle_collision=False,progress=1.,compute_s=.1,execution_time_s=2.,oracle_minimum_clearance_m=.1,omega_saturation_fraction=0.,box_passage=group=='sudden')
                    if name=='U2':row.update(active_history=False,active_age_s=0.,prior_departure_030=False,prior_deviation_max_m=.02,prior_deviation_mean_m=.01)
                    methods[name]=dict(row=row,plan=dict(path=path.tolist(),B_pred=B),trace=np.c_[path,np.zeros(11)].tolist())
                write(out/'evaluation'/(identity+'.json'),dict(case=c,methods=methods));cases.append(c)
            write(out/'manifest.json',dict(evaluation=cases,examples_only=[],figures=[c['case_id'] for c in cases]))
            write(here/'protocol.json',dict(selected=dict(c=2.,T_m=1.),selection_evidence=dict(table=[dict(index=0,selected=True)])))
            with patch.object(report,'ROOT',root),patch.object(report,'OUT',out),patch.object(report,'HERE',here):result=report.generate()
            self.assertEqual(result['label'],'UNIFIED_READY');self.assertEqual(len(list(out.glob('*.png'))),2)
            self.assertIn('SEEN_SUDDEN',(root/'docs/PHASE23O2_UNIFIED.md').read_text());self.assertTrue((out/'summary.csv').exists())

if __name__=='__main__':unittest.main()
