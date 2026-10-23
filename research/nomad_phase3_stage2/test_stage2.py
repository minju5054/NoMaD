import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import numpy as np
from nomad_isaac.common import ROOT
from nomad_isaac.async_core import WaypointExecution
from nomad_phase0.chunk_execution import describe_chunk, ChunkExecution
from nomad_phase3.config import validate_options as stage1_gate
from .config import protocol, validate_options
from .batch import matrix
from .execution import Stage2Execution, speed_command, horizon_command, decision


class FakeClient:
    def __init__(self):self.jobs=[];self.results=[]
    def submit(self,x):self.jobs.append(copy.deepcopy(x))
    def poll(self):return self.results.pop(0) if self.results else None
    def close(self):pass


def metadata(i,ns):
    points=np.column_stack([np.linspace(.1,.8,8),np.zeros(8)])
    return {'id':i,'received_monotonic_ns':ns,'chunk':describe_chunk(points,[0,0,0]),
        'observation_pose':[0,0,0],'observation_sim_s':0.}


class Tests(unittest.TestCase):
    def test_speed(self):
        for k in (0,1,2,4,8,20,-20):
            for previous in (0,.05,.1,.2):
                (v,w),f=speed_command(k,previous)
                self.assertGreaterEqual(v,.05);self.assertLessEqual(v,.2)
                self.assertLessEqual(abs(v-previous),.5/9+1e-12)
                self.assertLessEqual(abs(w),.4)
                self.assertEqual(f['CURVATURE_SATURATED'],abs(k)>8)
                self.assertAlmostEqual(w,np.clip(v*k,-.4,.4))
        (_, _), f=horizon_command(1,.2,.1,0)
        self.assertAlmostEqual(f['v_target_m_s'],.1/.998)
        (_, _), f=horizon_command(1,.2,.1,1)
        self.assertEqual(f['T_rem_s'],.1);self.assertEqual(f['v_target_m_s'],.2)

    def test_gate_matrix(self):
        jobs=matrix(Path('/tmp/stage2-not-executed'))
        self.assertEqual(len(jobs),15);self.assertEqual(len(jobs[3:]),12)
        for j in jobs:
            self.assertEqual(j['seed_offset'],j['index']*10000)
        p=protocol()
        a=SimpleNamespace(s0_stage2_method='GRAPH',asynchronous=True,pure_pursuit=True,
            scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],run_id='S0_01',seed_offset=10000,uniform_delivery_delay_s=.75)
        validate_options(a)
        for key,value in [('uniform_delivery_delay_s',.5),('seed_offset',20000),('s0_delay_sweep',True),('phase2_method','M0')]:
            b=copy.copy(a);setattr(b,key,value)
            with self.assertRaises(ValueError):validate_options(b)
        b=copy.copy(a);b.s0_stage2_method=None;b.s0_delay_sweep=True;b.uniform_delivery_delay_s=0.
        stage1_gate(b)
        b.s0_stage2_method='GRAPH'
        with self.assertRaises(ValueError):stage1_gate(b)

    def test_switch_graph_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            fake=FakeClient();e=Stage2Execution({'s0_stage2_method':'GRAPH'},Path(d),fake)
            core=WaypointExecution([0,0,0]);core.receive(metadata(0,1_000_000_000),[.3,0])
            refresh,switch=core.control(0,1_000_000_001);e.apply(core,refresh,switch)
            self.assertAlmostEqual(core.v,.5/9);self.assertEqual(len(fake.jobs),1)
            self.assertEqual(fake.jobs[0]['previous_command'],[0.,0.])
            xy=np.column_stack([np.linspace(.1,.8,8),np.ones(8)*.01,np.zeros(8)])
            result={'job_id':0,'id':0,'worker_start_ns':1_000_000_010,'worker_end_ns':1_050_000_010,
                'result_received_ns':1_055_000_000,'accepted':True,'poses':xy.tolist(),
                'solver':{'success':True,'constraints_satisfied':True,'exact_certificate_pass':True}}
            fake.results.append(result)
            refresh,switch=core.control(8,1_111_111_111);e.apply(core,refresh,switch)
            self.assertIsNone(switch);self.assertEqual(refresh['stage2']['graph_applied_job'],0)
            self.assertEqual(core.latest['received_monotonic_ns'],1_000_000_000)
            prior=e.previous_accepted
            core.receive(metadata(1,1_200_000_000),[.3,0])
            refresh,switch=core.control(16,1_222_222_222);e.apply(core,refresh,switch)
            self.assertEqual(fake.jobs[-1]['previous_xy'],prior)
            self.assertFalse(refresh['stage2']['corrected_path_active'])
            fake.results.append({**result,'job_id':1,'id':1,'worker_start_ns':1_222_222_230,
                'worker_end_ns':1_823_000_000,'result_received_ns':1_824_000_000})
            refresh,switch=core.control(64,1_888_888_888);e.apply(core,refresh,switch)
            self.assertFalse(refresh['stage2']['corrected_path_active'])
            refresh,switch=core.control(88,2_222_222_222);e.apply(core,refresh,switch)
            self.assertFalse(refresh['valid']);self.assertEqual((core.v,core.w),(0.,0.))
            e.close();logs=[json.loads(x) for x in (Path(d)/'stage2_graph.jsonl').read_text().splitlines()]
            self.assertEqual([r['disposition'] for r in logs if r['event']=='RESULT'],['ACCEPTED','STALE'])

    def test_superseded_and_stale(self):
        result={'id':1,'worker_start_ns':0,'worker_end_ns':600_000_000,'accepted':False,'solver':{'success':False}}
        self.assertEqual(decision(result,2,True)[:2],('SUPERSEDED',True))
        self.assertEqual(decision(result,1,True)[:2],('STALE',True))
        result.update(worker_end_ns=100_000_000,initialization_rejected=True)
        self.assertEqual(decision(result,1,True)[0],'INITIALIZATION_REJECTED')

    def test_legacy_chunk_unchanged(self):
        core=WaypointExecution([0,0,0]);e=ChunkExecution()
        core.receive(metadata(0,10),[.3,0]);r,s=core.control(0,11);e.apply(core,r,s)
        self.assertEqual((core.v,core.w),(.2,0.))
        self.assertNotIn('stage2',r)

if __name__=='__main__':unittest.main()
