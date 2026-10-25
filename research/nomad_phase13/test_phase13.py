import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import ROOT, local_to_world, integrate_se2
from nomad_isaac.async_core import WaypointExecution
from nomad_phase0.chunk_execution import describe_chunk, protocol as pp_protocol
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase4c.plant import control_command
from .config import protocol, validate_options, runtime_config
from .methods import METHODS, GF, smooth, transition_state
from .execution import make_execution
from .metrics import checkpoint
from .batch import matrix, execute, completion
from .report import tables, paired, generate


def options(method='FRESHEST',index=35):
    p=protocol()
    return SimpleNamespace(phase13_method=method,overnight_phase=8,overnight_method='CURV',
        phase4c_method='GRAPH' if method==GF else 'CURV',plant_alpha='inf',asynchronous=True,pure_pursuit=True,
        scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id=f'S0_{index:02d}',
        seed_offset=index*10000,uniform_delivery_delay_s=.75)


def fake_runs():
    records=[]
    for i in range(35,47):
        for m in METHODS:
            t=20+(i-35)*.2+{METHODS[0]:4,METHODS[1]:2,GF:0,METHODS[3]:5}[m]
            records.append(dict(key=f'S0_{i}_D750_{m}',method=m,index=i,success=True,
                classification='SUCCESS',technical_validation='PASS',checkpoint_time_s=t,checkpoint_x_m=3.55,
                checkpoint_mean_speed_m_s=3.55/t,goal_time_s=t+6,minimum_obstacle_clearance_m=.1,
                curv_slow_time_fraction=.2,endpoint_clamp_fraction=.4,plot_xy=[[0,0],[3.55,.5],[4.5,0]]))
    return records


class Checks(unittest.TestCase):
    def test_smoothing_exact_endpoints_line_and_short(self):
        p=np.column_stack([np.arange(6)*.1,np.zeros(6)])
        out,meta=smooth(p,[0,0,0]);np.testing.assert_allclose(out,p,atol=1e-15)
        q=p.copy();q[1:-1,1]=[.1,-.2,.1,-.1]
        out,meta=smooth(q,[0,0,0]);np.testing.assert_array_equal(out[[0,-1]],q[[0,-1]])
        expected=q.copy()
        for _ in range(2):
            old=expected.copy();expected[1:-1]=.25*old[:-2]+.5*old[1:-1]+.25*old[2:]
        np.testing.assert_array_equal(out,expected)
        with self.assertRaises(ValueError):smooth(p,[1,0,0])
        out,_=smooth([[0,0],[.01,0]],[0,0,0]);np.testing.assert_array_equal(out,[[0,0],[.01,0]])

    def test_order_gate_seeds_and_reuse(self):
        jobs=matrix(Path('/tmp/phase13_matrix_no_navigation'))
        self.assertEqual(len(jobs),48)
        for i in range(35,47):
            js=[j for j in jobs if j['index']==i]
            self.assertEqual([j['method'] for j in js],protocol()['method_order'][str(i)])
            self.assertEqual({j['seed_offset'] for j in js},{10000*i})
        a=options()
        for changes in ({'seed_offset':0},{'run_id':'S0_34','seed_offset':340000},{'uniform_delivery_delay_s':.5},{'phase12_method':GF}):
            bad=copy.copy(a);vars(bad).update(changes)
            with self.assertRaises(AssertionError):validate_options(bad)
        from nomad_phase8.config import validate_options as parent
        a.phase13_method=None
        with self.assertRaises(AssertionError):parent(a)
        for method,cls in ((GF,'GFExecution'),('TEMPORAL-ENSEMBLE','BaselineExecution')):
            with patch('nomad_phase13.execution.'+cls) as existing:
                make_execution(dict(phase13_method=method,obstacles=['FORBIDDEN'],corridor={'FORBIDDEN':True}),Path('/tmp'))
                config=existing.call_args.args[0]
                self.assertEqual(set(config),{'phase12_method','phase4c_method','plant_alpha'})

    def test_freshest_runtime_serialization_and_command_replay(self):
        local=np.stack([np.column_stack([np.linspace(.02,.55,8),np.linspace(0,(i-3)*.04,8)]) for i in range(8)])
        for method in METHODS[:2]:
            a=options(method);cfg=runtime_config(json.loads(a.scenario.read_text()),a)
            with tempfile.TemporaryDirectory() as td:
                ex=make_execution(cfg,Path(td));core=WaypointExecution([0,0,0],72,9)
                self.assertIsNone(ex.last_application_ns)
                ref=transition_state(method);follower=None;previous=0.
                for tick in range(0,32,8):
                    now=1_000_000_000+tick*1_000_000_000//72
                    if tick in (0,16):
                        obs=core.pose.copy();row=dict(id=tick//16,received_monotonic_ns=now-1,observation_pose=obs.tolist(),
                            observation_sim_s=tick/72,chunk=describe_chunk(local[0],obs),overnight_metric_samples=local.tolist())
                        core.receive(row,local[0,2])
                    refresh,event=core.control(tick,now);b=core.pose.copy()
                    if event:
                        worlds=np.array([local_to_world(x,np.array(event['observation_pose'])) for x in local])
                        path,_=ref.switch(worlds,b,event['id'],event['received_monotonic_ns'],now)
                        follower=PurePursuit(path,pp_protocol()['follower'])
                        native=json.dumps(event['chunk'])
                    _,diag=follower.control(b)
                    k=2*diag['target_local_y_m']/(diag['target_local_x_m']**2+diag['target_local_y_m']**2)
                    expected=(0.,0.) if diag['endpoint_stop'] else control_command('CURV',k,previous,0.,float('inf'))[0]
                    ex.apply(core,refresh,event)
                    if event:self.assertEqual(ex.last_application_ns,now)
                    np.testing.assert_array_equal([core.v,core.w],expected)
                    json.dumps(refresh);json.dumps(event)
                    if event:self.assertEqual(json.dumps(event['chunk']),native)
                    for t in range(tick+1,tick+9):
                        p=integrate_se2(core.pose,*expected,1/72);ex.plant.integrate(core,t)
                        np.testing.assert_array_equal(core.pose,p)
                    previous=expected[0]
                # A missing/expired FRESH still stops by the original 1s semantics.
                refresh,event=core.control(32,3_000_000_000);ex.apply(core,refresh,event)
                self.assertEqual((core.v,core.w),(0.,0.));ex.close()

    def test_checkpoint_geometry_not_hardcoded_and_failure(self):
        scene={'obstacles':[dict(id='StaticObstacle2',center_xy_m=[1.,0],size_xyz_m=[.4,.5,.8])]}
        rec=[dict(simulation_time_s=i/72) for i in range(4)]
        xy=np.array([[0,0,0],[1.4,0,0],[1.5,0,0],[1.6,0,0]])
        r=checkpoint(scene,rec,xy);self.assertEqual(r['checkpoint_tick'],2);self.assertAlmostEqual(r['checkpoint_x_m'],1.5)
        self.assertIsNone(checkpoint(scene,rec,xy,2/72)['checkpoint_time_s'])
        scene['obstacles'][0]['center_xy_m'][0]=8
        self.assertIsNone(checkpoint(scene,rec,xy)['checkpoint_time_s'])

    def test_no_technical_skip(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);jobs=matrix(root)
            plan=dict(git_sha='TEST',jobs=jobs);(root/'metrics').mkdir();(root/'launcher_logs').mkdir()
            (root/'plan.json').write_text(json.dumps(plan))
            with patch('nomad_phase13.batch.verify'),patch('nomad_phase13.batch.launch_one',return_value=1) as launch,patch('builtins.print'):
                execute(plan,root)
            self.assertEqual(launch.call_count,48)
            status=completion(root);self.assertEqual(status['completed'],48);self.assertEqual(status['technical_passes'],0)

    def test_paired_decisions_and_synthetic_report(self):
        records=fake_runs();_,pairs,label=tables(records)
        self.assertEqual(label,'SPEED_FROM_GRAPH');self.assertEqual(pairs[0]['n'],12)
        self.assertEqual(pairs[0]['ci95_s'],[-4.,-4.])
        for r in records:
            if r['method']==GF and r['index']>=42:r['checkpoint_time_s']=None
        self.assertEqual(paired(records,GF,'FRESHEST')['verdict'],'INCONCLUSIVE')
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'results';doc=Path(td)/'report.md'
            generate(fake_runs(),dict(git_sha='SYNTHETIC'),out,doc,synthetic=True)
            self.assertTrue(all((out/name).exists() for name in ('runs.json','summary.csv','paired.csv','checkpoint_time.png','paired_lines.png','paths.png')))
            self.assertIn('SPEED_FROM_GRAPH',doc.read_text())
            with self.assertRaises(AssertionError):generate(fake_runs(),dict(git_sha='SYNTHETIC'),out,doc,synthetic=True)


if __name__=='__main__':unittest.main()
