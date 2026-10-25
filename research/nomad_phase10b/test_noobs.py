import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase8.config import protocol as old_protocol,runtime_config,validate_options
from nomad_phase8.batch import matrix as old_matrix
from nomad_phase9.graph import GraphV6,FreeField
from nomad_phase9.intent import intention
from .batch import matrix,execute
from .config import protocol
from .metrics import route_windows,graph_calls,x_bin
from .report import decide,generate


def options(method='CURV',flag=True):
    p=old_protocol(9)
    return SimpleNamespace(overnight_phase=9,overnight_method=method,phase4c_method='GRAPH' if method=='GRAPH-v6' else 'CURV',
        phase10b_no_obstacle=flag,plant_alpha='inf',asynchronous=True,pure_pursuit=True,scenario=ROOT/p['scenario'],
        topomap=Path(p['topomap']),run_id='S1_01',seed_offset=10000,uniform_delivery_delay_s=.75)


def fixture_records():
    rows=[]
    for dataset in ('9','10B'):
        for d in (0.,.75):
            for m in ('CURV','GRAPH-v6'):
                for i in range(1,5):
                    success=not(m=='GRAPH-v6' and i<=2)
                    rows.append(dict(dataset=dataset,key=f'{dataset}_{int(d*1000)}_{m}_{i}',method=m,index=i,delay_s=d,
                        technical_validation='PASS',success=success,classification='SUCCESS' if success else 'STUCK',
                        goal_time_s=20 if success else None,duration_s=20 if success else 90,mean_speed_m_s=.2,
                        corridor_violation=False,geometric_overlap=False,termination_reason='goal_entry' if success else 'simulation_timeout',
                        route=dict(backtracking_count=0,backtracking_events=[],near_goal_max_abs_y_m=.1,near_goal_left_time_s=0,
                        closest_backwards=0,subgoal_backwards=0,curv_slow_fraction=.2,endpoint_clamp_fraction=.4,
                        topomap_series=[],topomap_failure_last10=[])))
    return rows


def fixture_calls(rs):
    js=[]
    for r in rs:
        if r['method']!='GRAPH-v6':continue
        for i in range(4):
            short=i<3
            js.append(dict(dataset=r['dataset'],key=r['key'],method=r['method'],index=r['index'],delay_s=r['delay_s'],
                job_id=i,fresh_id=i,time_s=r['duration_s']-2+i/4,boundary_x_m=7.,observation_x_m=6.9,x_bin='6–8',
                fresh_length_m=.2 if short else .3,short=short,solver_ran=True,nonconverged=short,solver_success=not short,
                initialization_rejected=False,initialization_error=None,disposition='NONCONVERGED' if short else 'ACCEPTED',
                accepted=not short,progress_cost=.1,fresh_endpoint_forward_m=.15,corrected_endpoint_forward_m=.25,
                endpoint_edit_forward_m=.1,failure_last10=not r['success'],public_obstacle_count=0,intent_active=False))
    return js


class Checks(unittest.TestCase):
    def test_opt_in_preserves_old_mode_and_seeds(self):
        p=protocol();a=options();source=json.loads(a.scenario.read_text());original=copy.deepcopy(source)
        normal=runtime_config(source,options(flag=False));control=runtime_config(source,a)
        self.assertEqual(source,original);self.assertIn('dynamic_obstacle',normal)
        self.assertNotIn('dynamic_obstacle',control);self.assertNotIn('diagnostic_y_offset_m',control)
        ignored={'dynamic_obstacle','phase2_distance_m','diagnostic_y_offset_m','phase10b_no_obstacle'}
        self.assertEqual({k:v for k,v in normal.items() if k not in ignored},{k:v for k,v in control.items() if k not in ignored})
        for name,h in p['protected_sha256'].items():self.assertEqual(sha256_file(ROOT/name),h)
        for change in ({'seed_offset':10001},{'run_id':'S1_05','seed_offset':50000},{'overnight_method':'SELECT'}, {'uniform_delivery_delay_s':.5},{'overnight_phase':8}):
            bad=copy.copy(a);vars(bad).update(change)
            with self.assertRaises(AssertionError):validate_options(bad)
        self.assertEqual(len(old_matrix(Path('/tmp/old_phase9_no_launch'),9,False)),40)
        jobs=matrix(Path('/tmp/phase10b_no_launch'));self.assertEqual(len(jobs),16)
        self.assertTrue(all(j['argv'][-1]=='--phase10b-no-obstacle' and j['seed_offset']==j['index']*10000 for j in jobs))
        self.assertEqual([(j['delay_s'],j['method']) for j in jobs[:4]],[(0.,'CURV'),(0.,'GRAPH-v6'),(.75,'CURV'),(.75,'GRAPH-v6')])

    def test_no_monitor_or_intent_and_original_free_field(self):
        from nomad_isaac.async_runtime import ExecutionThread
        a=options('GRAPH-v6');c=runtime_config(json.loads(a.scenario.read_text()),a);c['goal_mode']='topomap'
        with tempfile.TemporaryDirectory() as tmp,patch('nomad_phase9.worker.Client',return_value=MagicMock()):
            engine=ExecutionThread(c,Path(tmp),pure_pursuit=True)
            self.assertIsNone(engine.dynamic);self.assertIsNone(engine.phase2)
            public,gate,_=engine.stage2.public_config();self.assertEqual(public['obstacles'],[]);self.assertIsNone(gate)
            self.assertIsNone(intention(public,[3,0,0]));self.assertFalse((Path(tmp)/'dynamic').exists())
            engine.stage2.close();engine.monitor.finish(False)
        c['public_intent']=None;xy=np.column_stack([np.linspace(.1,.6,8),np.zeros(8)])
        p=json.loads((ROOT/'research/nomad_phase0/graph_v4_protocol.json').read_text())
        self.assertEqual(p['progress_target_m'],.25)
        g=GraphV6(xy,[0,0,0],[.2,0],c,p,FreeField())
        residual,_,names,_=g.residual_jacobian(g.initial.ravel())
        self.assertTrue(np.isfinite(residual).all());self.assertNotIn('heuristic_intent_xy',names)
        certificate,ok=g.certificate(g.initial);self.assertTrue(ok);self.assertIsNone(certificate['obstacle_clearance_m'])

    def test_route_and_graph_metrics(self):
        t=np.arange(289)/72;p=np.column_stack([np.full(len(t),7.),np.full(len(t),1.1),np.zeros(len(t))]);p[:144,2]=np.deg2rad(150)
        m=route_windows(t,p);self.assertEqual(m['backtracking_count'],1);self.assertAlmostEqual(m['backtracking_events'][0]['duration_s'],2)
        self.assertAlmostEqual(m['near_goal_left_time_s'],4);p[143,2]=0;self.assertEqual(route_windows(t,p)['backtracking_count'],0)
        self.assertEqual([x_bin(x) for x in (-1,0,2,4,6,8,8.01)],['OUTSIDE','0–2','2–4','4–6','6–8','6–8','OUTSIDE'])
        with tempfile.TemporaryDirectory() as tmp:
            xy=np.column_stack([np.linspace(0,.25,8),np.zeros(8)]);out=xy+np.array([0,.1])
            job=dict(event='SUBMIT',job_id=1,id=5,world_xy=xy.tolist(),boundary=[0,0,np.pi/2],switch_sim_s=15,observation_pose=[0,0,0],public_config={'obstacles':[]})
            result=dict(event='RESULT',job_id=1,poses=np.column_stack([out,np.zeros(8)]).tolist(),disposition='SUPERSEDED',solver={'success':False,'factor_costs':{'endpoint_progress':.3}})
            Path(tmp,'stage2_graph.jsonl').write_text('\n'.join(map(json.dumps,[job,result])))
            r=dict(key='X',method='GRAPH-v6',index=1,delay_s=0,duration_s=20,success=False)
            j=graph_calls(Path(tmp),r,'TEST')[0]
            self.assertFalse(j['short']);self.assertTrue(j['nonconverged']);self.assertFalse(j['accepted']);self.assertTrue(j['failure_last10'])
            self.assertAlmostEqual(j['endpoint_edit_forward_m'],.1)

    def test_decision_denominators_and_strict_majority(self):
        rs=fixture_records();js=fixture_calls(rs);d=decide(rs,js)
        self.assertTrue(all(x['verdict']=='SUPPORTED' for x in d.values()))
        # Zero short and long nonconvergence is no evidence, not 0>=2*0 support.
        zero=[dict(j,nonconverged=False) for j in js]
        self.assertEqual(decide(rs,zero)['C6_SHORT_CHUNK_CONFLICT']['verdict'],'NOT_SUPPORTED')
        bad=copy.deepcopy(rs)
        for r in bad:
            if r['dataset']=='10B' and r['method']=='GRAPH-v6' and r['delay_s']==0 and r['index']<=2:r['technical_validation']='FAIL'
        self.assertTrue(all(v['verdict']=='INCONCLUSIVE' for v in decide(bad,js).values()))
        self.assertEqual(decide(rs,[])['C6_SHORT_CHUNK_CONFLICT']['verdict'],'INCONCLUSIVE')

    def test_serial_no_retry_all16(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();(root/'launcher_logs').mkdir();jobs=matrix(root)
            with patch('nomad_phase10b.batch.verify'),patch('nomad_phase10b.batch.launch_one',side_effect=[1]+[0]*15) as launch,patch('nomad_phase10b.metrics.audit',return_value=dict(classification='STUCK',technical_validation='PASS',success=False)),patch('builtins.print'):
                execute(dict(git_sha='TEST',protocol=protocol(),jobs=jobs),root)
            marker=json.loads((root/'complete.json').read_text());self.assertEqual(launch.call_count,16)
            self.assertEqual(marker['technical_passes'],15);self.assertEqual(marker['retries'],0);self.assertEqual(marker['status'],'COMPLETE')

    def test_report_smoke_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);tracepath=root/'fake';tracepath.mkdir();rs=fixture_records();js=fixture_calls(rs)
            # Tiny plotting fixture; no controller or navigation executes.
            with (tracepath/'agent_trajectory.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['x_m','y_m','yaw_rad']);w.writeheader();w.writerows([dict(x_m=x,y_m=0,yaw_rad=0) for x in (0,1,2)])
            for r in rs:r['output']=str(tracepath)
            plan={'git_sha':'TEST_ONLY'};state={'state':'COMPLETE','completed':16,'expected':16}
            with patch('nomad_phase10b.report.load',return_value=(rs,js,plan,state,{})):
                out=root/'results';doc=root/'report.md';d=generate(root,out,doc)
                self.assertEqual(len(list(out.glob('*.png'))),2);self.assertTrue(doc.is_file())
                self.assertEqual(d['C6_SHORT_CHUNK_CONFLICT'],'SUPPORTED')
                with self.assertRaises(AssertionError):generate(root,out,doc)


if __name__=='__main__':unittest.main()
