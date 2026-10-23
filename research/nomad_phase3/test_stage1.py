"""Small gate/seed/default-path tests; no GPU/navigation."""
import ast
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from nomad_isaac.common import ROOT
from nomad_isaac.seed_offset import validate_seed_options,request_seed
from nomad_phase0.chunk_execution import validate_mode
from nomad_phase0.s0_batch import build_plan as legacy_plan
from nomad_phase0.s0_batch_metrics import classify
from .batch import build_plan
from .config import protocol,validate_options,runtime_config

class TestStage1(unittest.TestCase):
    def options(self):
        p=protocol()
        return SimpleNamespace(s0_delay_sweep=True,pure_pursuit=True,asynchronous=True,prepare_only=False,
            scenario=ROOT/p['scenario'],topomap=ROOT.parent/p['topomap'],seed_offset=10000,run_id='S0_01',
            uniform_delivery_delay_s=.25,oracle_safety_stop=False,early_obstacle_mode=None,
            controlled_delivery_delay=False,render_topomap_reference=None)
    def test_narrow_gate(self):
        for d in (0,.25,.5,.75):
            a=self.options();a.uniform_delivery_delay_s=d
            validate_options(a);validate_mode(a);validate_seed_options(a)
        for field,value in [('pure_pursuit',False),('asynchronous',False),('uniform_delivery_delay_s',None),
            ('uniform_delivery_delay_s',.1),('phase2_method','M0'),('s1_mode',True),('s1_v2_mode',True),
            ('run_id','S0_06'),('seed_offset',0),('controlled_delivery_delay',True),('oracle_safety_stop',True)]:
            a=self.options();setattr(a,field,value)
            with self.assertRaises(ValueError):validate_options(a)
        a=self.options();a.s0_delay_sweep=False
        with self.assertRaises(ValueError):validate_mode(a)
    def test_plan_and_legacy(self):
        p=build_plan(Path('/tmp/phase3_never_launch'))
        self.assertEqual([(j['index'],j['delay_s']) for j in p['jobs']],[(i,d) for i in range(1,6) for d in (0,.25,.5,.75)])
        for j in p['jobs']:
            self.assertEqual(j['request_0_seed'],101+j['index']*10000)
            self.assertEqual(request_seed({'seed':101,'seed_offset':j['seed_offset']},7),j['request_0_seed']+14)
        legacy=legacy_plan(Path('/tmp/legacy_never_launch'))
        self.assertEqual(len(legacy['jobs']),20)
        for j in legacy['jobs']:
            self.assertNotIn('--s0-delay-sweep',j['argv']);self.assertNotIn('--uniform-delivery-delay-s',j['argv'])
        source=json.loads(self.options().scenario.read_text());extended=runtime_config(source)
        self.assertEqual(source['timeout_sim_s'],60)
        self.assertEqual({k:v for k,v in extended.items() if k not in ('timeout_sim_s','s0_delay_sweep')},
                         {k:v for k,v in source.items() if k!='timeout_sim_s'})
        self.assertEqual(extended['timeout_sim_s'],90)
        self.assertEqual(classify(True,False,False,'goal_entry',50),'SUCCESS')
        self.assertEqual(classify(False,False,False,'simulation_timeout',90,90),'STUCK')
    def test_execution_class_unchanged(self):
        path='research/nomad_phase0/chunk_execution.py'
        old=subprocess.check_output(['git','show','c7fc0bc:'+path],cwd=ROOT,text=True)
        def node(text):return ast.dump(next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='ChunkExecution'))
        self.assertEqual(node(old),node((ROOT/path).read_text()))

if __name__=='__main__':unittest.main()
