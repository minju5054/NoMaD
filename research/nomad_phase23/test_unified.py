import ast,inspect,time,unittest,tempfile,copy,json,multiprocessing as mp
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from unittest.mock import patch
import numpy as np
from nomad_phase19r.test_repair import synthetic
from . import graph

class Tests(unittest.TestCase):
    def fixture(self):
        q=np.c_[np.linspace(0,1.2,11),.02*np.sin(np.linspace(0,np.pi,11))];c=np.repeat(q[None],8,axis=0)
        return graph.UnifiedGraph([0,0,.1],.2,c,.1,synthetic(),dict(time=1.,goal=1.,curvature=.01),time.monotonic_ns()+10_000_000_000),q
    def test_max_mixture_switches_without_filter(self):
        g,q=self.fixture();g.candidates[1,:,1]+=.5
        self.assertEqual(g.active(g.candidates[0])[0],0);self.assertEqual(g.active(g.candidates[1])[0],1);self.assertEqual(len(g.candidates),8)
    def test_derivatives_and_kinematic_limits(self):
        g,q=self.fixture();x=g.initial(q);x[4]+=.013;x[32]=.8
        eps=1e-7;eye=np.eye(40)
        f,j=g.objective(x);fd=np.array([(g.objective(x+eps*e)[0]-g.objective(x-eps*e)[0])/(2*eps) for e in eye]);np.testing.assert_allclose(j,fd,atol=1e-5,rtol=1e-6)
        f,j=g.constraints(x);fd=np.column_stack([(g.constraints(x+eps*e)[0]-g.constraints(x-eps*e)[0])/(2*eps) for e in eye]);np.testing.assert_allclose(j,fd,atol=1e-5,rtol=1e-6)
        fast=x.copy();fast[30:]=.05;self.assertLess(g.constraints(fast)[0].min(),0)
    def test_deadline_and_shape(self):
        g,q=self.fixture();r=graph.solve_start([0,0,0],.2,np.repeat(q[None],8,0),.1,synthetic(),g.weights,q,time.monotonic_ns()-1)
        self.assertFalse(r['accepted']);self.assertEqual(r['disposition'],'TIMEOUT')
        r=graph.solve_start([0,0,0],.2,np.repeat(q[None],8,0),.1,synthetic(),g.weights,q,time.monotonic_ns()+200_000_000)
        self.assertTrue(r['accepted'],r);self.assertEqual(np.shape(r['poses']),(11,3));self.assertEqual(len(r['dt']),10)
    def test_side_initializations_do_not_search(self):
        q=np.c_[np.linspace(0,1.5,11),np.full(11,-.12)];B=[0,-.12,0];c=np.repeat(q[None],8,axis=0)
        paths,info=graph.side_initializations(c,B,synthetic(True));self.assertEqual(len(paths),2)
        self.assertEqual(paths[0].shape,(11,2));self.assertGreater(paths[0][:,1].max(),paths[1][:,1].max())
        imports=[n for n in ast.walk(ast.parse(inspect.getsource(graph))) if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertFalse(any('astar' in ast.unparse(n).lower() for n in imports))
    def test_graph_speed_rollout_reproducible(self):
        from .rollout import unified_simulate
        q=np.c_[np.linspace(0,1,11),np.zeros((11,2))];plan=dict(accepted=True,poses=q,dt=np.full(10,.5));c=dict(B=[0.,0.,0.],previous_vw=[.2,0.]);policy=dict(rotation_policy='graph_rotation')
        a=unified_simulate(c,plan,policy);b=unified_simulate(c,plan,policy)
        np.testing.assert_array_equal(a['poses'],b['poses']);self.assertTrue(a['completed']);self.assertLessEqual(abs(a['poses'][-1,0]-1),.1+1e-9)
        self.assertTrue(all(abs(w)<=.4 for w in a['omegas']))
    def test_rotation_segment_executes_graph_omega(self):
        from .rollout import GraphFollower
        from nomad_isaac.common import integrate_se2
        q=np.c_[np.r_[0.,.004,np.linspace(.1,1.,9)],np.zeros(11),np.r_[0.,np.full(10,.2)]];dt=np.ones(10);dt[1:]=.5
        ctl=GraphFollower(q,dt);pose=np.zeros(3);previous=0.;rotating=[]
        for tick in range(100):
            if tick%8==0:
                (v,w),diag=ctl.control(pose,previous);previous=v
                if diag['mode']=='PP_GRAPH_SPEED':break
            if diag['mode']=='GRAPH_ROTATION':
                self.assertEqual(v,0.);self.assertGreater(w,0.);self.assertLessEqual(w,.2+1e-12);rotating.append(pose.copy())
            pose=integrate_se2(pose,v,w,1/72)
        self.assertTrue(rotating);np.testing.assert_array_equal(np.array(rotating)[:,:2],np.zeros((len(rotating),2)));self.assertAlmostEqual(pose[2],.2,places=9)
    def test_bounded_stop(self):
        from .rollout import stop_rollout
        r=stop_rollout([0.,0.,0.],.3);v=np.r_[.3,[c['v'] for c in r['commands']]]
        self.assertTrue(np.all(np.diff(v)>=-.5/9-1e-12));self.assertTrue(np.all(v>=0));self.assertEqual(v[-1],0.);self.assertLess(r['distance_m'],.1)
    def test_arclength_speed_interpolation_and_short_prior(self):
        from .rollout import GraphFollower
        q=np.array([[0,0,0],[.1,0,0],[.3,0,0],[.6,0,0]])
        ctl=GraphFollower(q,[1,1,1]);self.assertAlmostEqual(ctl.speed_at(.125),.15);self.assertAlmostEqual(ctl.speed_at(.325),.25)
        self.assertEqual(ctl.control([.125,0,0],.15)[0],ctl.control([.125,0,0],.15)[0])
        short=np.repeat(np.c_[np.linspace(0,.12,8),np.zeros(8)][None],8,0)
        candidates,sigma,flags=graph.prepare_candidates(short,[0,0,0],None,'retain')
        self.assertEqual(candidates.shape,(8,11,2));self.assertTrue(all(f['still_short'] for f in flags));self.assertLessEqual(candidates[:,:,0].max(),.12)
    def test_arrival_warm_start_isolated_and_suffix(self):
        from .planner import Replanner,warm_suffix
        q=np.c_[np.linspace(0,1,11),np.zeros((11,2))];accepted=dict(accepted=True,poses=q.tolist(),dt=[.5]*10)
        before=copy.deepcopy(accepted);suffix=warm_suffix(accepted,[.2,0,0]);np.testing.assert_allclose(suffix['poses'][0],[.2,0,0]);self.assertEqual(accepted,before)
        with patch('nomad_phase23.planner.plan',side_effect=[copy.deepcopy(accepted) for _ in range(3)]) as call:
            planner=Replanner(None,{},{});c=dict(split='training',run='run1',tick=0,case_id='a')
            planner.on_candidates(c);r=planner.on_candidates(dict(c,tick=18,case_id='b'))
            self.assertEqual(r['warm_source_case_id'],'a');self.assertEqual(r['warm_source_gap_s'],.25);self.assertIsNotNone(call.call_args.kwargs['previous'])
            planner.on_candidates(dict(c,run='run2',tick=18,case_id='c'));self.assertIsNone(call.call_args.kwargs['previous'])
    def test_tuning_gate_rank_sum_and_p50(self):
        from .run import rank_weights
        def row(i,p95,p50,collision=0,static=1.,sudden=1.):return dict(index=i,weights={},collisions=collision,failure_fraction=0.,progress=dict(static=static,sudden=sudden),p95=p95,p50=p50)
        winner,evidence=rank_weights([row(0,.501,.01),row(1,.49,.2,1)])
        self.assertEqual(winner['index'],1);self.assertFalse(evidence['all_combinations_exceed_limit'])
        winner,evidence=rank_weights([row(0,.60,.01),row(1,.58,.2,5)])
        self.assertEqual(winner['index'],1);self.assertTrue(evidence['all_combinations_exceed_limit'])
        winner,evidence=rank_weights([row(0,.24,.1),row(1,.22,.15)])
        self.assertEqual(winner['index'],0)
    def test_four_worker_budget_on_synthetic_data(self):
        from .planner import plan
        from nomad_phase20d.pool import initialize,ping
        ctx=mp.get_context('spawn');queue=ctx.Queue()
        with tempfile.TemporaryDirectory() as tmp,ProcessPoolExecutor(max_workers=4,mp_context=ctx,initializer=initialize,initargs=(queue,)) as pool:
            futures=[pool.submit(ping) for _ in range(4)]
            self.assertEqual(len({queue.get(timeout=30) for _ in range(4)}),4)
            for f in futures:f.result()
            file=Path(tmp)/'snapshot.npz';synthetic().save(file)
            samples=np.repeat(np.c_[np.linspace(0,1.,8),np.zeros(8)][None],8,0)
            c=dict(B=[0.,0.,0.],previous_vw=[.2,0.],samples_world=samples,snapshot_file=str(file),old_path=None)
            r=plan(pool,c,dict(time=.1,goal=1.,curvature=.001),dict(short_policy='retain',kinematic_sigma=.03,prediction_mode='continue_current_v_pp'))
            self.assertGreaterEqual(r['initialization_count'],8)
            if r['accepted']:
                self.assertLessEqual(r['selected']['received_ns'],r['deadline_ns']);self.assertEqual(np.shape(r['poses']),(11,3));np.testing.assert_allclose(r['poses'][0],r['B_pred'])
            self.assertLessEqual(r['initialization_count'],10);self.assertEqual(r['application_delay_s'],.5);self.assertFalse(r['late_results_used'])

if __name__=='__main__':unittest.main()
