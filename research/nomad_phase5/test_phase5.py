import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from nomad_isaac.common import ROOT
from nomad_isaac.async_core import WaypointExecution
from nomad_phase0.graph_v4 import GraphV4,SignedDistanceField
from nomad_phase0.graph_v2 import heading_chords,chord_values,fixed_entry,entry_pose
from nomad_phase3_stage2.test_stage2 import FakeClient,metadata
from nomad_phase4c.execution import AccelExecution
from nomad_phase4c.batch import matrix as old_matrix
from .graph import FlagGraphV4
from .rigid import rigid_entry
from .config import METHODS,protocol,graph_protocol,validate_options,base_method
from .execution import Phase5Execution
from .metrics import circling
from .batch import matrix,execute,completion


def graph_fixture(method,xy=None):
    p=graph_protocol(method);c=json.loads((ROOT/protocol()['scenario']).read_text())
    field=SignedDistanceField(c,p['sdf_resolution_m'],p['sdf_padding_m'])
    if xy is None:xy=np.column_stack([np.linspace(.1,.8,8),np.linspace(.01,.06,8)])
    return xy,np.array([0.,0.,0.]),[.2,0.],c,p,field,xy+np.array([.01,.03])


class Tests(unittest.TestCase):
    def test_flags_remove_only_requested_rows_and_factors(self):
        original=json.loads((ROOT/'research/nomad_phase0/graph_v4_protocol.json').read_text())
        for method in METHODS[2:]:
            args=graph_fixture(method);g=FlagGraphV4(*args);base=GraphV4(*args);x=g.initial.ravel()
            self.assertEqual({k:v for k,v in g.p.items() if k!='phase5_flags'},original)
            gb,jb,eb,jeb=base.constraints(x);gg,jg,eg,jeg=g.constraints(x)
            if method=='GRAPH-NO-SDF':
                keep=np.r_[np.arange(28),np.arange(91,len(gb))];gb,jb=gb[keep],jb[keep]
            np.testing.assert_array_equal(gg,gb);np.testing.assert_array_equal(jg,jb)
            if method=='GRAPH-NO-KB':self.assertEqual(eg.shape,(0,));self.assertEqual(jeg.shape,(0,24))
            else:np.testing.assert_array_equal(eg,eb);np.testing.assert_array_equal(jeg,jeb)
            if method=='GRAPH-NO-SDF':
                far=x.copy();far[0::3]+=100
                self.assertTrue(np.isfinite(g.constraints(far)[0]).all())
            if method=='GRAPH-NO-PREV':
                self.assertIsNone(g.previous_target)
                without=GraphV4(*args[:-1],previous_xy=None)
                np.testing.assert_array_equal(g.residual_jacobian(x)[0],without.residual_jacobian(x)[0])
            else:
                np.testing.assert_array_equal(g.residual_jacobian(x)[0],base.residual_jacobian(x)[0])

    def test_solver_constraint_selection_and_obstacle_certificate(self):
        for method in ('GRAPH-NO-SDF','GRAPH-NO-KB'):
            g=FlagGraphV4(*graph_fixture(method));captured={}
            def fake(fun,x,**kwargs):
                captured.update(kwargs)
                return SimpleNamespace(x=x,success=True,status=0,message='SYNTHETIC',nit=0,nfev=1,fun=fun(x))
            with patch('nomad_phase5.graph.minimize',side_effect=fake):poses,info=g.solve()
            self.assertEqual(len(captured['constraints']),1 if method=='GRAPH-NO-KB' else 2)
            self.assertEqual(captured['options']['maxiter'],100)
            self.assertEqual(captured['options']['ftol'],1e-8)
            self.assertTrue(callable(captured['jac']))
            self.assertEqual(info['phase5_flags'],g.flags)
        unsafe=np.column_stack([np.linspace(1.35,1.65,8),np.zeros(8)])
        for method,expected in (('GRAPH',False),('GRAPH-NO-SDF',True)):
            g=FlagGraphV4(*graph_fixture(method,unsafe));exact,passed=g.certificate(g.initial)
            self.assertLess(exact['obstacle_clearance_m'],0);self.assertEqual(passed,expected)
            outside=g.initial.copy();outside[:,1]=2.
            self.assertFalse(g.certificate(outside)[1])

    def test_rigid_entry_matches_existing_projection_and_preserves_shape(self):
        xy=np.column_stack([np.linspace(.1,.8,8),np.linspace(.1,.2,8)]);b=np.array([.32,-.04,-.3])
        corrected,detail=rigid_entry(xy,b)
        chords=heading_chords(xy,.02);head,_=chord_values(xy,chords);entry=fixed_entry(xy,b)
        ep=entry_pose(np.column_stack([xy,head]),entry)
        np.testing.assert_allclose(detail['entry_world_xy'],ep[:2],atol=1e-15)
        self.assertAlmostEqual(detail['entry_heading_rad'],ep[2])
        a,z,u=entry['a'],entry['b'],entry['fraction']
        np.testing.assert_allclose((1-u)*corrected[a]+u*corrected[z],b[:2],atol=1e-15)
        np.testing.assert_allclose(np.linalg.norm(np.diff(corrected,axis=0),axis=1),np.linalg.norm(np.diff(xy,axis=0),axis=1))
        for j,k in chords:
            before=np.arctan2(*(xy[k]-xy[j])[::-1]);after=np.arctan2(*(corrected[k]-corrected[j])[::-1])
            self.assertAlmostEqual((after-before-detail['rotation_rad']+np.pi)%(2*np.pi)-np.pi,0.)
        with self.assertRaises(ValueError):rigid_entry(np.zeros((8,2)),b)

    def test_execution_matches_curv_graph_and_preserves_native_chunk(self):
        for method in METHODS:
            with tempfile.TemporaryDirectory() as td:
                out=Path(td);actual=out/'new';actual.mkdir();reference=out/'base';reference.mkdir()
                cfg={'phase5_method':method,'phase4c_method':base_method(method),'plant_alpha':'inf'}
                fake=FakeClient() if method.startswith('GRAPH') else None
                e=Phase5Execution(cfg,actual,fake);core=WaypointExecution([0,0,0]);core.receive(metadata(0,1_000_000_000),[.3,0])
                r,s=core.control(0,1_000_000_001);native=copy.deepcopy(s['chunk']);e.apply(core,r,s)
                self.assertEqual(s['chunk'],native)
                if method in ('CURV','GRAPH'):
                    base=AccelExecution(cfg,reference,FakeClient() if method=='GRAPH' else None)
                    c=WaypointExecution([0,0,0]);c.receive(metadata(0,1_000_000_000),[.3,0]);rr,ss=c.control(0,1_000_000_001)
                    base.apply(c,rr,ss);np.testing.assert_array_equal([c.v,c.w],[core.v,core.w]);base.close()
                if fake:
                    self.assertEqual(len(fake.jobs),1)
                    xy=np.column_stack([np.linspace(.1,.8,8),np.full(8,.02),np.zeros(8)])
                    fake.results.append({'job_id':0,'id':0,'worker_start_ns':1_000_000_010,'worker_end_ns':1_050_000_010,
                        'result_received_ns':1_055_000_000,'accepted':True,'poses':xy.tolist(),
                        'solver':{'success':True,'constraints_satisfied':True,'exact_certificate_pass':True}})
                    for t in range(1,9):e.plant.integrate(core,t)
                    rr,ss=core.control(8,1_111_111_111);e.apply(core,rr,ss)
                    self.assertEqual(rr['stage2']['graph_applied_job'],0)
                e.close();apps=[json.loads(x) for x in (actual/'phase5_applications.jsonl').read_text().splitlines()]
                self.assertEqual(apps[0]['kind'],'RIGID' if method=='RIGID-ENTRY' else 'RAW')
                self.assertGreaterEqual(apps[0]['staleness'],0.)

    def test_gate_matrix_seeds_and_no_retries(self):
        jobs=matrix(Path('/tmp/phase5-never-run'));self.assertEqual(len(jobs),48)
        for i in range(8):self.assertEqual([j['method'] for j in jobs[i*6:i*6+6]],list(METHODS))
        for j in jobs:self.assertEqual(j['seed_offset'],10000*j['index'])
        p=protocol();a=SimpleNamespace(phase5_method='GRAPH',phase4c_method='GRAPH',plant_alpha='inf',asynchronous=True,
            pure_pursuit=True,scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id='S0_09',seed_offset=90000,uniform_delivery_delay_s=.75)
        validate_options(a)
        for change in ({'run_id':'S0_08','seed_offset':80000},{'plant_alpha':'2.0'},{'phase4c_method':'CURV'},{'phase4d_confirm':True}):
            with self.assertRaises(ValueError):validate_options(SimpleNamespace(**{**vars(a),**change}))
        self.assertEqual(tuple(map(len,old_matrix(Path('/tmp/old-matrix')))),(21,3))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir();(root/'launcher_logs').mkdir();plan={'jobs':jobs}
            (root/'plan.json').write_text(json.dumps(plan))
            with patch('nomad_phase4c.batch.verify'),patch('nomad_phase4c.batch.git_state',return_value={'git_sha':'SYNTHETIC'}), \
                 patch('nomad_phase4c.batch.launch_one',side_effect=[1]+[0]*47) as launch,patch('builtins.print'):
                execute(plan,root,audit_fn=lambda *a:dict(classification='SUCCESS',technical_validation='PASS',success=True))
            self.assertEqual(launch.call_count,48);status,done=completion(root);self.assertTrue(done);self.assertEqual(status['technical_passes'],47)

    def test_circling_is_literal_total_variation(self):
        poses=np.zeros((2001,3));poses[:,2]=np.linspace(0,7,2001)
        result=circling(poses);self.assertTrue(result['exists']);self.assertAlmostEqual(result['cumulative_abs_heading_rad'],7.)
        poses[:,2]=np.linspace(0,1,2001);self.assertFalse(circling(poses)['exists'])

    def test_decisions_and_report_with_two_figures(self):
        from .report import decide,generate,overlay_index
        source=json.loads((ROOT/'research/results/phase4c/runs.json').read_text())[0];records=[]
        counts={'CURV':3,'RIGID-ENTRY':4,'GRAPH':7,'GRAPH-NO-PREV':5,'GRAPH-NO-SDF':6,'GRAPH-NO-KB':8}
        for j in matrix(Path('/tmp/phase5-test')):
            r=copy.deepcopy(source);r.update({k:v for k,v in j.items() if k not in ('argv','shell_command')})
            r.update(output=source['output'],success=j['index']>=17-counts[j['method']],technical_validation='PASS',
                control_count=100,circling={'exists':False,'cumulative_abs_heading_rad':1.},applied_staleness_samples=[.2],
                corrected_staleness_samples=[0.],solver_wall_samples_s=[.05] if j['method'].startswith('GRAPH') else [],rigid_applied=0,rigid_rejected=0)
            r['classification']='SUCCESS' if r['success'] else 'STUCK';records.append(r)
        d=decide(records);self.assertEqual(d['verdict'],'GRAPH_SUPPORTED')
        self.assertEqual([d['C3'][m]['verdict'] for m in METHODS[3:]],['CONTRIBUTES','NOT_SHOWN','ABLATION_BETTER'])
        self.assertEqual(overlay_index(records),10)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);out=root/'result';doc=root/'doc.md'
            with patch('nomad_phase5.report.load',return_value=(records,{'git_sha':'SYNTHETIC_TEST'})):
                generate(root,out,doc)
            self.assertEqual(len(list(out.glob('*.png'))),2);self.assertIn('SYNTHETIC_TEST',doc.read_text())
            with self.assertRaises(AssertionError):generate(root,out,doc)
        for r in records:
            if r['method']=='RIGID-ENTRY':r['success']=True
        self.assertEqual(decide(records)['verdict'],'RIGID_SUFFICIENT_POSSIBLE')
        for r in records:
            if r['method']=='CURV':r['success']=True
        self.assertEqual(decide(records)['verdict'],'NOT_REPLICATED')


if __name__=='__main__':unittest.main()
