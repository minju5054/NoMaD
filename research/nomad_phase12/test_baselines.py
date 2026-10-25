import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import ROOT,sha256_file,local_to_world,integrate_se2
from nomad_isaac.async_core import WaypointExecution
from nomad_phase0.chunk_execution import describe_chunk,protocol as pp_protocol
from nomad_phase0.pure_pursuit import PurePursuit
from nomad_phase4c.plant import control_command
from .methods import NEW,PATH_BASELINES,GF,hermite_splice,bid_select,TemporalTargets,TransitionState
from .config import METHODS,internal,protocol,runtime_config,validate_options
from .execution import BaselineExecution
from .batch import matrix,execute,completion
from .report import decide,generate


def config(m='CURV',i=25):
    p=protocol();a=SimpleNamespace(phase12_method=m,overnight_phase=8,overnight_method=internal(m),phase4c_method='GRAPH' if m in ('SELECT+GRAPH',GF) else 'CURV',plant_alpha='inf',asynchronous=True,pure_pursuit=True,scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id=f'S0_{i:02d}',seed_offset=i*10000,uniform_delivery_delay_s=.75)
    return runtime_config(json.loads(a.scenario.read_text()),a),a


def samples():return np.stack([np.column_stack([np.linspace(.02,.55,8),np.linspace(0,(i-3)*.04,8)]) for i in range(8)])


class Checks(unittest.TestCase):
    def test_kernels_and_degenerate_cases(self):
        xy=samples()[0];path,detail=hermite_splice(xy,[0,0,.1]);np.testing.assert_array_equal(path[0],[0,0])
        self.assertTrue(detail['analytic_c1']);self.assertGreater(detail['curve_points'],2)
        _,d=bid_select(samples(),[0,0,0],samples()[4]);self.assertEqual(d['selected_sample'],4)
        _,d=bid_select(samples(),[0,0,0],[[0,0],[.01,0]]);self.assertEqual(d['selected_sample'],0)
        state=TransitionState('HERMITE-SPLICE');out,d=state.switch(np.zeros((8,8,2)),[0,0,0],0,10,11)
        self.assertIn('invalid_reason',d)

    def test_temporal_timeout_order_and_progress(self):
        xy=samples()[0];ens=TemporalTargets();ens.push(xy,0,0)
        diag,meta=ens.control([0,0,0],1);_,pp=PurePursuit(xy,pp_protocol()['follower']).control([0,0,0])
        self.assertEqual(diag['target_x_m'],pp['target_x_m']);self.assertEqual(diag['target_y_m'],pp['target_y_m'])
        for i in range(1,4):ens.push(samples()[i],i,i*100_000_000)
        _,m=ens.control([.1,0,0],400_000_000);self.assertEqual(m['chunk_ids'],[1,2,3]);self.assertAlmostEqual(sum(m['weights']),1.)
        self.assertTrue(m['weights'][0]>m['weights'][1]>m['weights'][2]);prev=ens.chunks[0]['follower'].progress
        ens.control([0,0,0],500_000_000);self.assertGreaterEqual(ens.chunks[0]['follower'].progress,prev)
        _,m=ens.control([0,0,0],1_100_000_000);self.assertEqual(m['chunk_ids'],[2,3])
        diag,m=ens.control([0,0,0],1_300_000_000);self.assertIsNone(diag);self.assertEqual(m['chunk_count'],0)

    def test_optin_protected_seed_and70_jobs(self):
        p=protocol()
        for path,h in p['protected_sha256'].items():self.assertEqual(sha256_file(ROOT/path),h,path)
        jobs=matrix(Path('/tmp/phase12_matrix_only'));self.assertEqual(len(jobs),70);self.assertEqual([j['method'] for j in jobs[:7]],list(METHODS))
        self.assertTrue(all(j['seed_offset']==j['index']*10000 for j in jobs));self.assertEqual(len({j['output'] for j in jobs}),70)
        c,a=config('RTC-hard');self.assertEqual(c['overnight_method'],'RTC-hard')
        for change in ({'seed_offset':0},{'run_id':'S0_24','seed_offset':240000},{'uniform_delivery_delay_s':0},{'phase11_v61':True},{'overnight_phase':9}):
            bad=copy.copy(a);vars(bad).update(change)
            with self.assertRaises(AssertionError):validate_options(bad)
        # Removing opt-in cannot widen the old Phase8 index gate.
        from nomad_phase8.config import validate_options as old_gate
        a.phase12_method=None
        with self.assertRaises(AssertionError):old_gate(a)

    def test_runtime_command_pose_replay_no_navigation(self):
        # Tiny in-memory SE2 verification, no render/model/environment launch.
        for method in PATH_BASELINES:
            c,_=config(method)
            with tempfile.TemporaryDirectory() as tmp:
                exe=BaselineExecution(c,Path(tmp));core=WaypointExecution([0,0,0],72,9);ref=TransitionState(method);follower=None;previous=0.
                for tick in range(0,40,8):
                    now=1_000_000_000+tick*1_000_000_000//72
                    if tick in (0,16):
                        local=samples();a=core.pose.copy();i=tick//16
                        row=dict(id=i,received_monotonic_ns=now-1,observation_pose=a.tolist(),observation_sim_s=tick/72,chunk=describe_chunk(local[0],a),overnight_metric_samples=local.tolist())
                        core.receive(row,local[0,2])
                    refresh,event=core.control(tick,now);b=core.pose.copy()
                    if event:
                        worlds=np.array([local_to_world(x,np.array(event['observation_pose'])) for x in event['overnight_metric_samples']])
                        path,detail=ref.switch(worlds,b,event['id'],event['received_monotonic_ns'],now);follower=PurePursuit(path,pp_protocol()['follower'])
                    if method=='TEMPORAL-ENSEMBLE':diag,_=ref.ensemble.control(b,now)
                    else:_,diag=follower.control(b)
                    k=2*diag['target_local_y_m']/(diag['target_local_x_m']**2+diag['target_local_y_m']**2)
                    expected=(0.,0.) if diag['endpoint_stop'] else control_command('CURV',k,previous,0.,float('inf'))[0]
                    exe.apply(core,refresh,event);np.testing.assert_array_equal([core.v,core.w],expected)
                    if event:np.testing.assert_array_equal(event['chunk']['world_xy_m'],row['chunk']['world_xy_m'])
                    for step in range(tick+1,tick+9):
                        want=integrate_se2(core.pose,*expected,1/72);exe.plant.integrate(core,step);np.testing.assert_array_equal(core.pose,want)
                    previous=expected[0]
                refresh,event=core.control(40,3_000_000_000);exe.apply(core,refresh,event);self.assertEqual((core.v,core.w),(0.,0.));exe.close()
                self.assertEqual(Path(tmp,'stage2_graph.jsonl').read_text(),'')

    def test_batch_method_specific_gate_and_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();(root/'launcher_logs').mkdir();jobs=matrix(root);plan=dict(jobs=jobs,git_sha='FIXTURE',protocol=protocol())
            (root/'plan.json').write_text(json.dumps(plan))
            def launch(j,log):return 1 if j['index']==25 and j['method']=='TEMPORAL-ENSEMBLE' else 0
            with patch('nomad_phase12.batch.verify'),patch('nomad_phase12.batch.launch_one',side_effect=launch) as mocked,patch('nomad_phase12.metrics.audit',return_value=dict(classification='STUCK',technical_validation='PASS',success=False)),patch('builtins.print'):
                execute(plan,root)
            s=completion(root);self.assertEqual(s['state'],'COMPLETE');self.assertEqual((s['attempted'],s['skipped'],s['finished_slots']),(61,9,70))
            self.assertEqual(mocked.call_count,61);marker=json.loads((root/'complete.json').read_text());self.assertEqual(marker['disabled_methods'],['TEMPORAL-ENSEMBLE'])

    def test_statistics_and_report_smoke(self):
        records=[]
        for i in range(25,35):
            for m in METHODS:
                success=m in ('SELECT+GRAPH',GF) or i<=30
                records.append(dict(key=f'{m}_{i}',method=m,index=i,delay_s=.75,classification='SUCCESS' if success else 'STUCK',technical_validation='PASS',success=success,goal_time_s=20. if success else None,mean_speed_m_s=.25 if m in ('SELECT+GRAPH',GF) else .20,minimum_obstacle_clearance_m=.03,inference_ms={'median':50},curv_slow_time_fraction=.2,endpoint_clamp_fraction=.3))
        d,p=decide(records);self.assertEqual(d['BEATS_CURV'],'PASS');self.assertEqual(d['SPEED_VS_CURV'],'FASTER');self.assertNotIn('BEATS_SELECT+GRAPH',d)
        bad=copy.deepcopy(records)
        for r in bad:
            if r['method']=='CURV' and r['index']>=33:r['technical_validation']='FAIL'
        self.assertEqual(decide(bad)[0]['BEATS_CURV'],'INCONCLUSIVE');self.assertEqual(decide(bad)[0]['SPEED_VS_CURV'],'INCONCLUSIVE')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'fake';run.mkdir()
            with (run/'agent_trajectory.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['x_m','y_m','yaw_rad']);w.writeheader();w.writerows([dict(x_m=x,y_m=0,yaw_rad=0) for x in (0,1,4)])
            for r in records:r['output']=str(run)
            state=dict(state='COMPLETE',attempted=70,skipped=0)
            with patch('nomad_phase12.report.load',return_value=(records,{'git_sha':'FIXTURE'},state,{})):
                out=root/'results';doc=root/'report.md';generate(root,out,doc);self.assertTrue(doc.exists());self.assertEqual(len(list(out.glob('*.png'))),2)
                with self.assertRaises(AssertionError):generate(root,out,doc)


if __name__=='__main__':unittest.main()
