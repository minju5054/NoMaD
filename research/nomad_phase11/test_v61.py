import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
import numpy as np
from nomad_isaac.common import ROOT,sha256_file
from nomad_phase9.graph import GraphV6,FreeField
from nomad_phase8.config import runtime_config,validate_options
from nomad_phase10b.test_noobs import options
from .graph import GraphV61,progress_metadata
from .config import protocol
from .batch import matrix,execute
from .metrics import passage,graph_calls
from .report import decide,generate


def fixtures():
    records=[]
    specs=[('11','sudden','GRAPH-v6.1',(.75,0.)),('11','noobs','GRAPH-v6.1',(.75,0.))]
    specs += [('9','sudden',m,(.75,0.) if m in ('CURV','GRAPH-v6') else (.75,)) for m in ('CURV','SELECT','INTENT-SPLICE','GRAPH-v6')]
    specs += [('10B','noobs',m,(.75,0.)) for m in ('CURV','GRAPH-v6')]
    for dataset,scene,method,ds in specs:
        for d in ds:
            for i in range(1,(8 if scene=='sudden' and d==.75 else 4)+1):
                success=dataset=='11' or i<= (5 if d==.75 else 2)
                records.append(dict(dataset=dataset,scene=scene,method=method,index=i,delay_s=d,key=f'{dataset}_{scene}_{method}_{d}_{i}',
                    classification='SUCCESS' if success else 'STUCK',technical_validation='PASS',success=success,goal_time_s=40 if success else None,
                    duration_s=40 if success else 90,mean_speed_m_s=.2,geometric_overlap=False,corridor_violation=False,termination_reason='test',
                    passage=dict(safe_passage=scene=='sudden',dynamic_minimum_clearance_m=.1 if scene=='sudden' else None),
                    route=dict(backtracking_count=0,near_goal_max_abs_y_m=.1,near_goal_left_time_s=0,topomap_series=[]),
                    topomap_by_intent={stage:dict(closest=0,subgoal=0,observations=1) for stage in ('intent_active','other')}))
    calls=[]
    for r in records:
        if not r['method'].startswith('GRAPH'):continue
        for short in (True,False):
            calls.append({k:r[k] for k in ('dataset','scene','method','key','index','delay_s')}|dict(
                short=short,solver_ran=True,nonconverged=r['dataset']!='11' and short,accepted=r['dataset']=='11',
                initialization_rejected=False,disposition='ACCEPTED' if r['dataset']=='11' else 'NONCONVERGED',
                fresh_length_m=.2 if short else .4,progress_cost=0.,endpoint_edit_forward_m=.03,
                p_native_m=.15,progress_target_m=.135 if r['dataset']=='11' else .25,progress_enabled=True,x_bin='6–8'))
    return records,calls


class Checks(unittest.TestCase):
    def test_only_progress_target_changes(self):
        a=options('GRAPH-v6');c=runtime_config(json.loads(a.scenario.read_text()),a)
        p=json.loads((ROOT/'research/nomad_phase0/graph_v4_protocol.json').read_text())
        xy=np.column_stack([np.linspace(.02,.20,8),np.zeros(8)])
        # Include inherited previous-path prior in the equality check.
        v6=GraphV6(xy,[0,0,0],[.2,0],c,p,FreeField(),xy)
        v61=GraphV61(xy,[0,0,0],[.2,0],c,p,FreeField(),xy)
        self.assertAlmostEqual(v61.progress['progress_target_m'],.18)
        x=v6.initial.ravel().copy();x[-3]=.10
        r,j,n,s=v6.residual_jacobian(x);r1,j1,n1,s1=v61.residual_jacobian(x)
        self.assertEqual((n,s),(n1,s1));row=sum(s[:n.index('endpoint_progress')]);keep=np.arange(len(r))!=row
        np.testing.assert_array_equal(r[keep],r1[keep]);np.testing.assert_array_equal(j[keep],j1[keep])
        self.assertAlmostEqual(r1[row],.08/.25);self.assertEqual(j1[row,-3],-4.)
        for original,new in zip(v6.constraints(x),v61.constraints(x)):np.testing.assert_array_equal(original,new)
        self.assertEqual(v6.p,v61.p);np.testing.assert_array_equal(v6.initial,v61.initial)
        for boundary,target in (([.3,0,0],0.),([-1,0,0],.25)):
            g=GraphV61(xy,boundary,[.2,0],c,p,FreeField());self.assertAlmostEqual(g.progress['progress_target_m'],target)
            _,_,names,_=g.residual_jacobian(g.initial.ravel());self.assertEqual('endpoint_progress' in names,target>0)
        self.assertAlmostEqual(progress_metadata([[0,0],[0,.2]],[0,0,np.pi/2])['p_native_m'],.2)
        # No heading/zero-speed initialization relaxation.
        with self.assertRaises(ValueError):GraphV61(xy,[0,0,0],[0,0],c,p,FreeField())
        # Intent and forced side factors stay numerically identical outside progress.
        c['obstacles']=[dict(id='DynamicObstacle',center_xy_m=[.15,-.5],size_xyz_m=[.35,.35,.8])]
        c['public_intent']=dict(side=1,V=[.15,.1]);v6=GraphV6(xy,[0,0,0],[.2,0],c,p,FreeField())
        v61=GraphV61(xy,[0,0,0],[.2,0],c,p,FreeField());self.assertEqual(v6.sides,v61.sides)
        r,j,n,s=v6.residual_jacobian(x);r1,j1,n1,s1=v61.residual_jacobian(x);row=sum(s[:n.index('endpoint_progress')]);keep=np.arange(len(r))!=row
        self.assertIn('heuristic_intent_xy',n);np.testing.assert_array_equal(r[keep],r1[keep]);np.testing.assert_array_equal(j[keep],j1[keep])

    def test_gate_matrix_and_original_hashes(self):
        a=options('GRAPH-v6');a.phase11_v61=True;c=json.loads(a.scenario.read_text())
        new=runtime_config(c,a);a.phase11_v61=False;old=runtime_config(c,a)
        self.assertEqual(new.pop('phase11_v61'),True);self.assertEqual(new,old)
        for changes in ({'overnight_method':'CURV','phase4c_method':'CURV'},{'seed_offset':0},{'uniform_delivery_delay_s':.5},{'run_id':'S1_05','seed_offset':50000},{'overnight_phase':8}):
            bad=copy.copy(a);bad.phase11_v61=True;vars(bad).update(changes)
            with self.assertRaises(AssertionError):validate_options(bad)
        for path,h in protocol()['protected_sha256'].items():self.assertEqual(sha256_file(ROOT/path),h,path)
        jobs=matrix(Path('/tmp/phase11_dry_test'));self.assertEqual(len(jobs),20)
        self.assertEqual(len({j['output'] for j in jobs}),20)
        self.assertEqual(sum(j['scene']=='sudden' for j in jobs),12)
        for j in jobs:
            self.assertEqual(j['seed_offset'],10000*j['index']);self.assertIn('--phase11-v61',j['argv'])
            self.assertEqual('--phase10b-no-obstacle' in j['argv'],j['scene']=='noobs')
            self.assertEqual(j['argv'][j['argv'].index('--overnight-method')+1],'GRAPH-v6')

    def test_runtime_hook_and_worker_metadata_without_solve(self):
        from nomad_isaac.async_runtime import ExecutionThread
        from .execution import AdaptiveExecution
        from . import worker
        a=options('GRAPH-v6');a.phase11_v61=True;c=runtime_config(json.loads(a.scenario.read_text()),a);c['goal_mode']='topomap'
        with tempfile.TemporaryDirectory() as tmp,patch('nomad_phase11.execution.Client',return_value=MagicMock()):
            engine=ExecutionThread(c,Path(tmp),pure_pursuit=True)
            self.assertIsInstance(engine.stage2,AdaptiveExecution);self.assertIsNone(engine.dynamic)
            engine.stage2.close();engine.monitor.finish(False)
        xy=np.column_stack([np.linspace(.02,.2,8),np.zeros(8)]).tolist()
        job=dict(job_id=1,id=2,world_xy=xy,boundary=[0,0,0],previous_command=[.2,0],public_config=c)
        metadata=progress_metadata(xy,job['boundary']);fake=MagicMock();fake.solve.return_value=(np.column_stack([xy,np.zeros(8)]),dict(feasible=True,**metadata))
        stream=io.StringIO()
        with patch.object(worker.sys,'stdin',io.StringIO(json.dumps(job)+'\n'+json.dumps({'kind':'stop'})+'\n')),patch.object(worker.sys,'stdout',stream),patch.object(worker,'GraphV61',return_value=fake):worker.main()
        response=json.loads(stream.getvalue().splitlines()[-1]);self.assertTrue(response['accepted'])
        for k,v in metadata.items():self.assertEqual(response[k],v)
        self.assertEqual(fake.solve.call_count,1)  # mocked only; no optimization

    def test_passage_and_logged_progress(self):
        poses=np.array([[0,0,0],[1.2,.4,0],[1.3,.4,0],[1.4,1.5,0]])
        spawn=dict(tick=0,obstacle=dict(center_xy_m=[1.,0.],size_xyz_m=[.35,.35,.8]))
        gap=[dict(geometric_overlap=False,lower_m=.1) for _ in poses]
        result=passage(np.arange(4),poses,spawn,gap,.09)
        self.assertTrue(result['safe_passage']);self.assertEqual(result['passage_tick'],2)
        gap[3]['geometric_overlap']=True;self.assertTrue(passage(np.arange(4),poses,spawn,gap,.09)['safe_passage'])
        gap[1]['geometric_overlap']=True;self.assertFalse(passage(np.arange(4),poses,spawn,gap,.09)['safe_passage'])
        self.assertIsNone(passage(np.arange(4),poses,None,[],.09)['safe_passage'])
        with tempfile.TemporaryDirectory() as tmp:
            xy=np.column_stack([np.linspace(.02,.2,8),np.zeros(8)]).tolist();b=[.3,0,0];m=progress_metadata(xy,b)
            submit=dict(event='SUBMIT',job_id=1,id=2,world_xy=xy,boundary=b,switch_sim_s=5.,observation_pose=[0,0,0],public_config={'obstacles':[],'phase11_v61':True})
            result=dict(event='RESULT',job_id=1,poses=np.column_stack([xy,np.zeros(8)]).tolist(),disposition='ACCEPTED',solver=dict(success=True,factor_costs={},**m),**m)
            Path(tmp,'stage2_graph.jsonl').write_text('\n'.join(map(json.dumps,[submit,result])))
            r=dict(method='GRAPH-v6.1',key='test',index=1,delay_s=.75,duration_s=6,success=True,scene='noobs')
            j=graph_calls(tmp,r,'11')[0];self.assertEqual(j['progress_cost'],0.);self.assertFalse(j['progress_enabled'])
            result['progress_target_m']=.25;Path(tmp,'stage2_graph.jsonl').write_text('\n'.join(map(json.dumps,[submit,result])))
            with self.assertRaises(AssertionError):graph_calls(tmp,r,'11')

    def test_decision_validity_gates(self):
        rs,js=fixtures();self.assertEqual(len(rs),76)
        self.assertTrue(all(v['verdict']=='SUPPORTED' for v in decide(rs,js).values()))
        # A 4-run group needs4; cannot hide it in a pooled12 denominator.
        bad=copy.deepcopy(rs)
        next(r for r in bad if r['dataset']=='11' and r['scene']=='sudden' and r['delay_s']==0)['technical_validation']='FAIL'
        d=decide(bad,js)
        for name in ('V61_SAFE_PASSAGE','V61_GOAL_IMPROVES','C6_FIXED'):self.assertEqual(d[name]['verdict'],'INCONCLUSIVE')
        self.assertEqual(d['V61_VS_SPLICE']['verdict'],'SUPPORTED')
        self.assertEqual(decide(rs,[])['C6_FIXED']['verdict'],'INCONCLUSIVE')
        bad=copy.deepcopy(rs)
        for r in bad:
            if r['dataset']=='11' and r['scene']=='noobs' and r['delay_s']==0 and r['index']==1:r['classification']='PLACEMENT_INVALID'
        self.assertEqual(decide(bad,js)['NO_HARM_NOOBS']['verdict'],'INCONCLUSIVE')

    def test_serial20_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'metrics').mkdir();(root/'launcher_logs').mkdir();jobs=matrix(root)
            with patch('nomad_phase11.batch.verify'),patch('nomad_phase11.batch.launch_one',side_effect=[1]+[0]*19) as launch,patch('nomad_phase11.metrics.audit',return_value=dict(classification='STUCK',technical_validation='PASS',success=False)),patch('builtins.print'):
                execute(dict(git_sha='TEST',protocol=protocol(),jobs=jobs),root)
            marker=json.loads((root/'complete.json').read_text());self.assertEqual(launch.call_count,20)
            self.assertEqual(marker['technical_passes'],19);self.assertEqual(marker['retries'],0)

    def test_report_end_to_end_fixture_and_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);run=root/'fake';run.mkdir();rs,js=fixtures()
            with (run/'agent_trajectory.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['x_m','y_m','yaw_rad']);w.writeheader();w.writerows([dict(x_m=x,y_m=0,yaw_rad=0) for x in (0,4,8)])
            for r in rs:r['output']=str(run)
            with patch('nomad_phase11.report.load',return_value=(rs,js,{'git_sha':'FIXTURE_ONLY'},{'state':'COMPLETE','completed':20},{})):
                out=root/'results';doc=root/'report.md';decision=generate(root,out,doc)
                self.assertTrue(all(v=='SUPPORTED' for v in decision.values()));self.assertTrue(doc.is_file())
                self.assertEqual(len(list(out.glob('*.png'))),2)
                summary=json.loads((out/'summary.json').read_text());self.assertEqual(len(summary['groups']),14)
                with self.assertRaises(AssertionError):generate(root,out,doc)


if __name__=='__main__':unittest.main()
