"""Minimal synthetic integration tests; no simulator, inference or Graph solves."""
import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from nomad_isaac.common import ROOT, local_to_world, sha256_file
from nomad_isaac.async_core import WaypointExecution
from nomad_phase0.chunk_execution import describe_chunk
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase3_stage2.test_stage2 import FakeClient, metadata
from nomad_phase5.execution import Phase5Execution
from nomad_phase5.batch import matrix as old_matrix
from .config import protocol, validate_options, base_method
from .batch import matrix, references, execute, completion
from .execution import Phase6Execution
from .selection import select
from .metrics import application_measure, summarize_window, mechanisms
from .report import decide, generate, group, wilson


def scenario():
    return json.loads((ROOT/protocol()['scenario']).read_text())


def samples_fixture():
    samples=np.stack([np.column_stack([np.linspace(1.2,1.9,8),np.zeros(8)])]*8)
    samples[1,:,1]=.7
    samples[2]=samples[1]
    samples[2,:,0]=np.linspace(1.2,2.2,8)
    samples[3]=samples[2]
    return samples


class Tests(unittest.TestCase):
    def test_gate_matrix_seeds_legacy_and_protected_inputs(self):
        jobs=matrix(Path('/tmp/phase6-never-run'));refs=references()
        self.assertEqual((len(jobs),len(refs)),(56,24))
        self.assertEqual([j['delay_s'] for j in jobs[:6]],[0,0,.25,.25,.5,.5])
        self.assertTrue(all(j['method']=='SELECT' and j['delay_s']==.75 for j in jobs[48:]))
        self.assertTrue(all(j['seed_offset']==10000*j['index'] for j in jobs+refs))
        self.assertEqual(len(old_matrix(Path('/tmp/phase5-never-run'))),48)
        p=protocol();a=SimpleNamespace(phase6_method='GRAPH',phase4c_method='GRAPH',plant_alpha='inf',
            asynchronous=True,pure_pursuit=True,scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],
            run_id='S0_09',seed_offset=90000,uniform_delivery_delay_s=.25)
        validate_options(a)
        for change in ({'uniform_delivery_delay_s':.75},{'phase5_method':'GRAPH'},{'plant_alpha':'2.0'},
                       {'seed_offset':10000},{'phase6_method':'SELECT','phase4c_method':'CURV'}):
            with self.assertRaises(ValueError):validate_options(SimpleNamespace(**{**vars(a),**change}))
        for name,h in p['protected_sha256'].items():self.assertEqual(sha256_file(ROOT/name),h)

    def test_select_all_segments_actual_B_remaining_and_ties(self):
        samples=samples_fixture();b=np.array([1.6,.7,0.])
        xy,d=select(samples,[0,0,0],b,scenario())
        self.assertFalse(d['candidates'][0]['safe']);self.assertEqual(d['selected_sample'],2)
        self.assertEqual(d['candidates'][2]['remaining_length_m'],d['candidates'][3]['remaining_length_m'])
        np.testing.assert_array_equal(xy,samples[2]);self.assertFalse(d['all_unsafe'])
        samples[4]=np.column_stack([np.linspace(-.5,1.8,8),np.full(8,.7)])
        self.assertEqual(select(samples,[0,0,0],b,scenario())[1]['selected_sample'],2) # total longer, remaining shorter
        bad=np.stack([samples[0]]*8);xy,d=select(bad,[0,0,0],b,scenario())
        self.assertTrue(d['all_unsafe']);self.assertEqual(d['selected_sample'],0)
        np.testing.assert_array_equal(xy,bad[0])
        a=np.array([.2,.1,.3]);local=(samples-a[:2])@np.array([[np.cos(a[2]),-np.sin(a[2])],[np.sin(a[2]),np.cos(a[2])]])
        xy,d=select(local,a,b,scenario());np.testing.assert_allclose(xy,samples[d['selected_sample']],atol=1e-12)

    def test_curv_graph_identical_to_phase5_including_replacement_timeout(self):
        for method in ('CURV','GRAPH'):
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);outs=[root/'v5',root/'v6'];[p.mkdir() for p in outs]
                cfg={**scenario(),'phase4c_method':base_method(method),'plant_alpha':'inf','phase5_method':method,'phase6_method':method}
                clients=[FakeClient(),FakeClient()];cores=[WaypointExecution([0,0,0]),WaypointExecution([0,0,0])]
                ex=[Phase5Execution(cfg,outs[0],clients[0]),Phase6Execution(cfg,outs[1],clients[1])]
                for e,c in zip(ex,cores):
                    c.receive(metadata(0,1_000_000_000),[.3,0]);r,s=c.control(0,1_000_000_001)
                    original=copy.deepcopy(s['chunk']);e.apply(c,r,s);self.assertEqual(s['chunk'],original)
                np.testing.assert_array_equal(ex[0].last_command,ex[1].last_command)
                if method=='GRAPH':
                    for client in clients:
                        client.results.append(dict(job_id=0,id=0,worker_start_ns=1_000_000_010,worker_end_ns=1_050_000_010,
                            result_received_ns=1_055_000_000,accepted=True,
                            poses=np.column_stack([np.linspace(.1,.8,8),np.full(8,.02),np.zeros(8)]).tolist(),
                            solver=dict(success=True,constraints_satisfied=True,exact_certificate_pass=True)))
                for tick,now in ((8,1_111_111_111),(16,2_111_111_111)):
                    for e,c in zip(ex,cores):
                        for t in range(tick-7,tick+1):e.plant.integrate(c,t)
                        r,s=c.control(tick,now);e.apply(c,r,s)
                    np.testing.assert_array_equal(ex[0].last_command,ex[1].last_command)
                    np.testing.assert_array_equal(cores[0].pose,cores[1].pose)
                self.assertEqual(ex[1].last_command,[0.,0.])
                for e in ex:e.close()

    def test_select_switch_preserves_native_anchor_and_nominal_PD(self):
        with tempfile.TemporaryDirectory() as td:
            cfg={**scenario(),'phase4c_method':'CURV','phase6_method':'SELECT','plant_alpha':'inf'}
            e=Phase6Execution(cfg,Path(td));core=WaypointExecution([1.6,.7,0.]);samples=samples_fixture()
            m=metadata(0,1_000_000_000);m.update(observation_pose=[0.,0.,0.],phase6_metric_samples=samples.tolist(),chunk=describe_chunk(samples[0],[0,0,0]))
            core.receive(m,samples[0,2]);r,s=core.control(0,1_000_000_001)
            native=copy.deepcopy(s['chunk']);nominal=[r['v_m_s'],r['w_rad_s']];e.apply(core,r,s)
            self.assertEqual(s['phase6_selection']['selected_sample'],2);self.assertEqual(native,s['chunk'])
            self.assertEqual(nominal,[r['v_m_s'],r['w_rad_s']]);np.testing.assert_array_equal(e.follower.path.points,samples[2])
            e.close()

    def test_mechanism_window_and_existing_reference_projection(self):
        a=dict(world_xy=[[0,0],[1,0]],simulation_time_s=2.,kind='RAW',id=1)
        d=application_measure(a,np.array([.4,.3,np.pi/2]));self.assertAlmostEqual(d['heading_abs_rad'],np.pi/2);self.assertAlmostEqual(d['cross_track_m'],.3)
        short={**a,'world_xy':[[0,0],[.01,0]]}
        self.assertIsNone(application_measure(short,np.zeros(3))['heading_abs_rad'])
        times=np.array([0.,1.,2.,3.]);poses=np.column_stack([times,[0,1.1,1.1,0],np.zeros(4)])
        gaps=[dict(corridor_lower_m=x) for x in (1,.3,.2,.5)]
        w=summarize_window([d],[(1.,1.),(2.,4.)],poses,times,gaps,.5,3.)
        self.assertAlmostEqual(w['time_abs_y_over1_s'],1.5);self.assertEqual(w['minimum_wall_footprint_clearance_lower_m'],.2)
        self.assertEqual(w['kappa_over2_fraction'],.5)
        run=Path(protocol()['reference_root'])/'S0_09_CURV';result=mechanisms(run,True)
        apps=[json.loads(x) for x in (run/'phase5_applications.jsonl').read_text().splitlines()]
        self.assertEqual(len(result['applications']),len(apps))
        for m,a in zip(result['applications'],apps):self.assertAlmostEqual(m['cross_track_m'],a['projection_distance_m'])
        self.assertIsNone(result['failure_last3s'])

    def test_batch_passes_per_job_delay_and_never_retries(self):
        jobs=matrix(Path('/tmp/phase6-test-no-launch'));seen=[]
        def fake_audit(run,rid,offset,delay):
            seen.append(delay);return dict(classification='SUCCESS',technical_validation='PASS',success=True)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir();(root/'launcher_logs').mkdir();plan={'jobs':jobs}
            (root/'plan.json').write_text(json.dumps(plan))
            with patch('nomad_phase6.batch.verify'),patch('nomad_phase6.batch.git_state',return_value={'git_sha':'SYNTHETIC'}), \
                 patch('nomad_phase6.batch.launch_one',side_effect=[1]+[0]*55) as launch,patch('builtins.print'):
                execute(plan,root,fake_audit)
            self.assertEqual(launch.call_count,56);self.assertEqual(seen,[j['delay_s'] for j in jobs[1:]])
            status,done=completion(root);self.assertTrue(done);self.assertEqual(status['technical_passes'],55)

    def test_report_decisions_figures_and_no_imputed_goal_times(self):
        source=json.loads((ROOT/protocol()['reference_results']).read_text())[0];records=[]
        counts={0.:{'CURV':7,'GRAPH':7},.25:{'CURV':6,'GRAPH':7},.5:{'CURV':5,'GRAPH':7},.75:{'CURV':3,'GRAPH':7,'RIGID-ENTRY':3,'SELECT':5}}
        template=mechanisms(Path(source['output']),True)
        for j in references()+matrix(Path('/tmp/phase6-synthetic')):
            r=copy.deepcopy(source);r.update({k:v for k,v in j.items() if k not in ('argv','shell_command')})
            success=j['index']-9<counts[j['delay_s']][j['method']]
            r.update(success=success,classification='SUCCESS' if success else 'STUCK',technical_validation='PASS',
                goal_time_s=(40. if j['method']=='GRAPH' else 42.) if success else None)
            r['mechanisms']=copy.deepcopy(template)
            if not success:r['mechanisms']['failure_last3s']=copy.deepcopy(template['full'])
            records.append(r)
        d=decide(records);self.assertTrue(all(d[k] for k in ('D0_NO_HARM','TREND_SUPPORTED','BEATS_SELECT')))
        self.assertEqual(d['delta_success_counts'],{'0':0,'250':1,'500':2,'750':4})
        self.assertEqual(group(records,.75,'CURV')['goal_time_median_s'],42.)
        self.assertAlmostEqual(wilson(0,8)[1],.32440756488388023)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'results';doc=Path(td)/'report.md'
            with patch('nomad_phase6.report.load',return_value=(records,{'git_sha':'SYNTHETIC'})):
                result=generate(Path(td)/'never-run',out,doc)
                self.assertEqual(result,d);self.assertEqual(len(list(out.glob('*.png'))),2)
                self.assertIn('Table 3',doc.read_text())
                with self.assertRaises(AssertionError):generate(Path(td),out,doc)
            self.assertEqual(len(json.loads((out/'runs.json').read_text())),80)


if __name__=='__main__':unittest.main()
