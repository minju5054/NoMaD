import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.ndimage import distance_transform_edt
from nomad_phase15.depth_sdf import DepthSDF
from nomad_phase0.graph_v4 import GraphV4,SignedDistanceField
from nomad_phase12.graph_gf import graph_protocol
from nomad_isaac.common import ROOT
from .depth import Snapshot,evaluate_samples
from .graph import DepthGraph
from .execution import capped_command,SafeExecution
from .config import METHODS,SAFE,protocol
from .batch import matrix
from .report import render,tables

def synthetic():
    f=DepthSDF([-1,-1,2,1]);f.mark(f.occupied,np.array([[.5,.11],[.51,.11]]));f.values=distance_transform_edt(~f.occupied,sampling=f.h)-f.radius
    return Snapshot(f,dict(frame_id=0,sim_s=0.,file='synthetic'))

class Tests(unittest.TestCase):
    def test_interface_immutability_certificate(self):
        f=DepthSDF([-1,-1,2,1]);snap=Snapshot(f,dict(frame_id=0));before=snap.query(np.array([[.1,.2]]))
        f.values[:]=0.;f.occupied[:]=True
        np.testing.assert_array_equal(before[0],snap.query(np.array([[.1,.2]]))[0]);self.assertEqual(before[1].shape,(1,2));self.assertEqual(snap.error_bound,snap.h/np.sqrt(2))
        with self.assertRaises(ValueError):snap.values[0,0]=0
        with self.assertRaises(TypeError):snap.metadata['frame_id']=3
        s=synthetic();self.assertAlmostEqual(s.exact_clearance(np.array([[.4,0],[.6,0]])),.02,places=10)
    def test_graph_exact_v4_sdf_rows(self):
        c=json.loads((ROOT/'research/nomad_isaac/two_obstacles_wide_wall_scenario.json').read_text());field=SignedDistanceField(c,.01,2.)
        xy=np.column_stack([np.linspace(.08,.8,8),np.zeros(8)]);g=DepthGraph(xy,[0,0,0],[.2,0],field)
        original=GraphV4(xy,[0,0,0],[.2,0],c,graph_protocol(),field)
        a,j,_,_=original.constraints(g.initial.ravel());start=7+1+len(g.chords)+12
        b,bj=g.sdf_rows(g.initial.ravel());np.testing.assert_array_equal(a[start:start+len(b)],b);np.testing.assert_array_equal(j[start:start+len(b)],bj)
    def test_selection_and_fallback(self):
        s=synthetic();samples=np.array([np.column_stack([np.linspace(.1,.7+i*.01,8),np.full(8,-i*.02)]) for i in range(8)])
        xy,d=evaluate_samples(samples,[0,0,0],s);self.assertEqual(d['selected_sample'],7);self.assertFalse(d['all_unsafe'])
        crowded=Snapshot(s,dict(s.metadata));crowded.values.flags.writeable=True;crowded.values[:]=-.09;crowded.values.flags.writeable=False
        _,d=evaluate_samples(samples,[0,0,0],crowded);self.assertTrue(d['all_unsafe'])
        cmd,t=capped_command(1.,.3);self.assertEqual(t,.10);self.assertAlmostEqual(cmd[0],.3-.5/9)
    def test_gate_seed_order(self):
        jobs=matrix(Path('/tmp/never_execute_phase15b'));self.assertEqual(len(jobs),48)
        for i in range(47,55):
            subset=[j for j in jobs if j['index']==i];self.assertEqual([j['method'] for j in subset],protocol()['method_order'][str(i)])
            self.assertEqual({j['seed_offset'] for j in subset},{i*10000});self.assertEqual({j['method'] for j in subset},set(METHODS))
    def test_report_labels(self):
        rs=[]
        for i in range(47,55):
            for m in METHODS:
                rs.append(dict(index=i,method=m,technical_validation='PASS',classification='SUCCESS',success=True,checkpoint_time_s=20.+i/100,goal_time_s=30.,minimum_obstacle_clearance_m=.03,geometric_overlap=False,corridor_violation=False,inference_ms=dict(median=90.,p95=100.)))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'runs.json').write_text(json.dumps(rs));render(json.loads((root/'runs.json').read_text()),dict(git_sha='SYNTHETIC'),root/'results',root/'report.md',False)
            self.assertIn('PILOT_GRAPH_DEPTH_EQUAL',(root/'report.md').read_text());self.assertTrue((root/'results/paired.csv').exists())
        rs[0]['technical_validation']='FAIL';self.assertEqual(tables(rs)[2]['F1'],'PILOT_INCONCLUSIVE')
    def test_saved_execution_cap_and_dispatch(self):
        import copy
        from nomad_isaac.async_report import rows
        # Actual saved FRESH input; two controller ticks only, no navigation.
        p=json.loads((ROOT/'research/results/phase13/runs.json').read_text());r=next(r for r in p if r['method']=='FRESHEST');run=Path(r['output'])
        e=rows(run/'events.jsonl')[1];controllers=rows(run/'controller.jsonl');c=next(c for c in controllers if c['simulation_time_s']==e['application_sim_s'])
        f=DepthSDF([-4,-3.5,8,3.5]);f.values[:]=-.05
        snapshot=Snapshot(f,dict(frame_id=0,sim_s=0.,publication_monotonic_ns=1,capture_end_monotonic_ns=1,file='synthetic',empty_unknown=False))
        class FakeClient:
         def __init__(self):self.jobs=[]
         def poll(self):return None
         def submit(self,job):self.jobs.append(job)
         def close(self):pass
        for m in SAFE:
         with tempfile.TemporaryDirectory() as tmp:
          client=FakeClient();obj=SafeExecution(m,Path(tmp),client);obj.depth_maps=SimpleNamespace(snapshot=lambda:snapshot)
          core=SimpleNamespace(pose=np.array(e['agent_pose_at_switch']),v=.3,w=0.,latest=dict(id=e['id']),applied_id=e['id'])
          obj.last_command=[.3,0.];refresh=copy.deepcopy(c);switch=copy.deepcopy(e)
          obj.apply(core,refresh,switch)
          assert refresh['depth_fallback_cap_active'] and abs(core.v-(.3-.5/9))<1e-12
          assert abs(core.w)<=.4 and obj.last_application_ns==refresh['monotonic_ns']
          assert np.array_equal(switch['chunk']['world_xy_m'],e['chunk']['world_xy_m'])
          if 'GRAPH' in m:assert len(client.jobs)==1 and not any(k in client.jobs[0]['public_config'] for k in ('obstacles','corridor'))
          obj.close()
if __name__=='__main__':unittest.main()
