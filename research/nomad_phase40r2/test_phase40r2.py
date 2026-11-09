import copy,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from . import config,runtime,report,campaign,launch


class Tests(unittest.TestCase):
    def test_only_r2_and_frozen_failure_alternative(self):
        from nomad_phase40p.test_phase40p import RuntimeTests
        from nomad_phase40p.runtime import PlanningBase
        o=RuntimeTests().fake();o.__class__=runtime.Execution
        o.no_progress=runtime.DisabledTriggerB()
        self.assertEqual(o.no_progress.check(None,0,None),(False,None,'TRIGGER_B_DISABLED'))
        with self.assertRaises(AssertionError):o.dispatch(None,None,{'kind':'R3'})
        with self.assertRaises(AssertionError):o.start_detour(None,None,'B',None)
        o.n_pending=dict(job_id=0,kind='R2',id=3,apply_tick=56,dispatch_ns=1)
        o.n_result=dict(job_id=0,parent_received_ns=1,selected_sample=None,results=[])
        core=SimpleNamespace(pose=np.zeros(3));refresh=dict(simulation_time_s=56/72,monotonic_ns=2,valid=True)
        held=object();o.sp=held
        o.poll_job(core,refresh,None)
        self.assertFalse(o.n_after_r2);self.assertIs(o.sp,held)
        # EC rejection uses the same failure path; only its destination changes.
        o.n_pending=dict(job_id=1,kind='R2',id=3,apply_tick=56,dispatch_ns=1)
        o.n_result=dict(job_id=1,parent_received_ns=1,selected_sample=0,results=[dict(accepted=True,path=[[0,0],[1,0]],cB=.1)])
        o.ec_check=lambda *a,**kw:dict(passed=False,check_id=1)
        o.poll_job(core,refresh,None);self.assertFalse(o.n_after_r2);self.assertIs(o.sp,held)
        records=[json.loads(x) for x in o.ec_file.getvalue().splitlines()]
        self.assertEqual(records[-1]['route'],'R2_TO_ALTERNATIVE')
        # Periodic R2 rejection also clears the old R3 queue after its frozen
        # next-SAFE/slow/STOP EC replacement has executed.
        o.n_after_r2=True;o.poll_job(core,refresh,None);self.assertFalse(o.n_after_r2)
        self.assertIs(runtime.Execution.ec_check,runtime.Frozen.ec_check)
        self.assertIs(runtime.Execution.ec_install,runtime.Frozen.ec_install)
        self.assertIs(runtime.Execution.start_repair,runtime.Frozen.start_repair)
    def test_twenty_configs_launch_checks_and_campaign_without_smoke(self):
        from nomad_phase40p.config import runtime_config as parent
        from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
        class Boundary(Exception):pass
        plan=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(plan),20)
        for j in plan:
            c=config.runtime_config(j['method'],j['index'],90,j['scene'])
            self.assertEqual({k:v for k,v in c.items() if not k.startswith('phase40r2')},parent('OURS-N',j['index'],90,j['scene']))
            for output in j['outputs']:self.assertLess(validate_socket_path(socket_path_for_run(Path(output))),100)
            fn=launch.launcher_main(SimpleNamespace(Popen=lambda *a,**k:self.fail('No simulation')))
            fn.__globals__['socket_path_for_run']=lambda *_:(_ for _ in ()).throw(Boundary())
            args=['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',j['outputs'][0]]
            with patch.object(sys,'argv',args),self.assertRaises(Boundary):fn()
        code='''
from nomad_phase40r2 import campaign as c
from nomad_phase40r2.config import RUN_ROOT
def halt():
 assert len(c.base.jobs(RUN_ROOT))==20
 assert c.base.protocol()['smoke']['enabled'] is False
 assert c.base.run_job.__globals__['subprocess'].__class__ is c.Routes
 print('NO_SMOKE_ENGINE_OK')
c.base.main=halt
c.main()
assert not RUN_ROOT.exists()
'''
        r=subprocess.run(['/usr/bin/python3','-c',code],cwd=config.ROOT,env=dict(os.environ,PYTHONPATH='research'),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr[-1500:]);self.assertIn('NO_SMOKE_ENGINE_OK',r.stdout)
        self.assertFalse(config.RUN_ROOT.exists())
    def test_same_gate_and_tables_only_report(self):
        rows=[];prior=[]
        for i,j in enumerate(config.protocol()['main_order']):
            r=dict(j,technical_validation='PASS',success=i<17,collision=False,goal_time_s=40.,distance_m=8.)
            rows.append(r)
            prior.extend(dict(r,method=m,success=i<14) for m in report.frozen.COMPARATORS)
        d,_,_=report.analyze(rows+prior)
        self.assertEqual(d['pilot_label'],'PILOT_OK');self.assertEqual(d['graph_label'],'GRAPH_GAIN')
        self.assertEqual(report.analyze(rows[:-1]+prior)[0]['pilot_label'],'NOT_EVALUATED')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'metrics').mkdir()
            for i,r in enumerate(rows):(root/'metrics'/f'{i}.json').write_text(json.dumps(r))
            doc=report.generate(root,root/'results',root/'report.md',prior)
            text=doc.read_text();self.assertIn('OURS-R2',text);self.assertNotIn('OURS-N',text)
            self.assertTrue(all(not line or line.startswith('|') for line in text.splitlines()))
            self.assertEqual(json.loads((root/'results/decision.json').read_text()),d)


if __name__=='__main__':unittest.main()
