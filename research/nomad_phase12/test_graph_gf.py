import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from nomad_isaac.async_core import WaypointExecution
from nomad_phase0.chunk_execution import describe_chunk
from nomad_phase0.pure_pursuit import XYPath
from nomad_phase0.graph_v4 import GraphV4
from nomad_phase5.graph import InactiveField
from .methods import GF,freshest
from .graph_gf import GraphGF,graph_protocol
from .gf_worker import Client,numeric_job,validate_job
from .gf_execution import GFExecution
from .test_baselines import samples,config


def job():
    return dict(job_id=0,id=0,world_xy=samples()[4].tolist(),boundary=[0.,0.,0.],previous_command=[.2,0.],
        previous_commanded_vw=[.2,0.],previous_xy=None,dispatch_ns=0,switch_monotonic_ns=0,
        switch_sim_s=0.,observation_pose=[0.,0.,0.],observation_sim_s=0.,distance_m=0.)


class GraphChecks(unittest.TestCase):
    def test_geometry_firewall_and_freshest(self):
        ss=samples();b=[.08,.01,.05];xy,detail=freshest(ss,b)
        remain=[]
        for i,sample in enumerate(ss):
            path=XYPath(sample);remain.append((-(path.s[-1]-path.project(b[:2])[0]),i))
        self.assertEqual(detail['selected_sample'],min(remain)[1]);self.assertFalse(detail['oracle_used'])
        _,tied=freshest(np.repeat(ss[:1],8,axis=0),b);self.assertEqual(tied['selected_sample'],0)
        with self.assertRaises(AssertionError):freshest({'obstacles':[]},b)
        with self.assertRaises(AssertionError):validate_job({**job(),'corridor':{}})
        with self.assertRaises(AssertionError):numeric_job({**job(),'public_config':{'obstacles':[]}})
        with self.assertRaises(AssertionError):GraphGF(ss[0],b,[.2,0],{**graph_protocol(),'obstacles':[]})
        with patch('nomad_phase0.graph_v4.side_labels',side_effect=AssertionError('geometry forbidden')),patch('nomad_phase5.graph.path_safety',side_effect=AssertionError('geometry forbidden')):
            gf=GraphGF(ss[0],b,[.2,0],graph_protocol());gf.objective(gf.initial.ravel());gf.constraints(gf.initial.ravel());gf.certificate(gf.initial)
            self.assertFalse(hasattr(gf,'config'));self.assertFalse(hasattr(gf,'field'))

    def test_nonoracle_v4_expressions_and_jacobians_identical(self):
        ss=samples()[4];b=[0.,0.,.03];p=graph_protocol();basep={k:v for k,v in p.items() if k!='phase12_gf_flags'}
        scene={'obstacles':[],'corridor':{'xmin':-1,'xmax':9,'half_width':1.5},'agent_radius_m':.09,'safety_clearance_m':.02}
        # Geometry exists only in this reference parity check, never in GF.
        base=GraphV4(ss,b,[.2,.02],scene,basep,InactiveField(),ss+.01)
        gf=GraphGF(ss,b,[.2,.02],p,ss+.01)
        for displacement in (0.,.001):
            x=gf.initial.ravel()+np.linspace(0,displacement,24)
            br,bj,bn,bs=base.residual_jacobian(x);gr,gj,gn,gs=gf.residual_jacobian(x)
            np.testing.assert_array_equal(br,gr);np.testing.assert_array_equal(bj,gj);self.assertEqual((bn,bs),(gn,gs))
            bg,bj,be,bje=base.constraints(x);gg,gj,ge,gje=gf.constraints(x)
            n=7+1+len(gf.chords)+12;keep=np.r_[np.arange(n),len(bg)-1]
            np.testing.assert_array_equal(bg[keep],gg);np.testing.assert_array_equal(bj[keep],gj)
            np.testing.assert_array_equal(be,ge);np.testing.assert_array_equal(bje,gje)
        np.testing.assert_array_equal(base.bounds.lb,gf.bounds.lb)

    def test_numeric_dispatch_and_next_tick_graph_application(self):
        class FakeClient:
            def __init__(self):self.jobs=[];self.results=[]
            def submit(self,j):self.jobs.append(numeric_job(j))
            def poll(self):return self.results.pop(0) if self.results else None
            def close(self):pass
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);c,_=config(GF);client=FakeClient();exe=GFExecution(c,out,client);core=WaypointExecution([0,0,0],72,9)
            now=1_000_000_000;local=samples();row=dict(id=0,received_monotonic_ns=now-1,observation_pose=[0,0,0],observation_sim_s=0.,chunk=describe_chunk(local[0],[0,0,0]),overnight_metric_samples=local.tolist())
            core.receive(row,local[0,2]);refresh,event=core.control(0,now);exe.apply(core,refresh,event)
            j=client.jobs[0];self.assertNotIn('public_config',j);self.assertNotIn('obstacles',j)
            self.assertFalse(refresh['stage2']['corrected_path_active']);self.assertEqual(len(client.jobs),1)
            original=json.dumps(event['chunk']);corrected=np.array(j['world_xy']);corrected[:,1]+=.01
            result=dict(job_id=0,id=0,worker_start_ns=now,worker_end_ns=now+10_000_000,result_received_ns=now+20_000_000,
                kind='result',accepted=True,poses=np.column_stack([corrected,np.zeros(8)]).tolist(),geometry_free_assert=True,
                solver=dict(success=True,constraints_satisfied=True,exact_certificate_pass=None,certificate_scope='NONE_ORACLE_FREE'))
            client.results.append(result)
            for tick in range(1,9):
                before=core.pose.copy();exe.plant.integrate(core,tick);exe.integrate_record(before,core.pose)
            refresh,event2=core.control(8,now+111_111_111);exe.apply(core,refresh,event2)
            self.assertIsNone(event2);self.assertTrue(refresh['stage2']['corrected_path_active']);np.testing.assert_array_equal(exe.follower.path.points,corrected)
            self.assertEqual(json.dumps(event['chunk']),original)
            self.assertEqual(exe.previous_accepted,corrected.tolist())
            # Existing disposition logic also covers stale and superseded, without a solve.
            from nomad_phase3_stage2.execution import decision
            self.assertEqual(decision({**result,'worker_end_ns':now+600_000_000},0,True)[0],'STALE')
            self.assertEqual(decision(result,1,True)[0],'SUPERSEDED')
            exe.close()
            submits=[json.loads(s) for s in (out/'stage2_graph.jsonl').read_text().splitlines() if json.loads(s)['event']=='SUBMIT']
            validate_job({k:v for k,v in submits[0].items() if k!='event'})

    def test_external_cpu_worker_rejects_undefined_boundary_without_solve(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=Client(Path(tmp))
            try:
                j=job();j['previous_command']=[0.,0.];j['dispatch_ns']=time.monotonic_ns();c.submit(j)
                limit=time.monotonic()+10;result=None
                while result is None and time.monotonic()<limit:
                    result=c.poll()
                    if result is None:time.sleep(.01)
                self.assertIsNotNone(result);self.assertTrue(result['initialization_rejected']);self.assertTrue(result['geometry_free_assert']);self.assertNotIn('solver',result)
            finally:c.close()

if __name__=='__main__':unittest.main()
