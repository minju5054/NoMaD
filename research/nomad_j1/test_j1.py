import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from nomad_j0.test_j0 import Client,Field,event,refresh
from nomad_phase15.depth_sdf import DepthSDF
from nomad_phase52ec.rollout import rollout as tail_rollout
from nomad_phase4c.plant import control_command
from nomad_isaac.common import integrate_se2
from . import config,runtime,ec,launch,campaign,statistics

class Tests(unittest.TestCase):
    def test195_real_launcher_plans_and_frozen_assets(self):
        jobs=campaign.jobs(config.RUN_ROOT);self.assertEqual(len(jobs),195)
        self.assertEqual([j['index'] for j in jobs],sum(([i]*15 for i in config.INDICES),[]))
        for j in jobs:
            args=launch.parser().parse_args(j['argv'][4:]+['--dry-run']);row=launch.build(args)
            self.assertEqual(row['smoke_excluded'],False);self.assertLess(row['socket_bytes'],100)
            self.assertEqual('nomad_phase8.worker' in row['worker'],j['method']=='RTC-hard')
        for s in config.SCENES:
            for m in config.METHODS:
                c=config.runtime_config(m,231,level=s)
                self.assertEqual(c['goal_tolerance_m'],.3);self.assertFalse(c['nomad_goal_stop'])
                self.assertEqual(c['checkpoint'],config.checkpoint_spec(s));self.assertTrue(c['depth_camera'])
        self.assertFalse(campaign.next_block_allowed(19800,False));self.assertTrue(campaign.next_block_allowed(19801,True))

    def test_tail_controller_exact_curv_and_terminal_braking(self):
        path=np.c_[np.linspace(.05,.30,8),np.zeros(8)];ctl=ec.CurvController(path)
        trace=tail_rollout([0.,0.,0.],[.3,0.],path,controller=ctl,start_tick=0)
        self.assertTrue(trace['stopped']);self.assertEqual(trace['terminal_vw'],[0.,0.])
        self.assertEqual(trace['stop_reason'],'ENDPOINT');self.assertGreater(trace['braking_s'],0.)
        self.assertGreater(trace['poses'][-1,0],.30)
        horizon=tail_rollout([0.,0.,0.],[.3,0.],[[0.,0.],[3.,0.]],controller=ec.CurvController([[0.,0.],[3.,0.]]))
        self.assertEqual(horizon['brake_request_s'],2.);self.assertTrue(horizon['stopped'])
        q=np.zeros(3);v=.0;profile=ec.CurvController([[0.,0.],[1.,.3]])
        (_, _),diag=profile.control(q,v)
        geometry=profile.follower.control(q)[1];x,y=geometry['target_local_x_m'],geometry['target_local_y_m']
        expected=control_command('CURV',2*y/(x*x+y*y),v,0.,float('inf'))[0]
        actual,_=ec.CurvController([[0.,0.],[1.,.3]]).control(q,v)
        np.testing.assert_array_equal(actual,expected)

    def test_install_reject_preserves_path_clock_but_graph_can_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            field=Field();client=Client();e=runtime.SafeExecution('OURS',Path(tmp),client);e.depth_maps=SimpleNamespace(snapshot=lambda:field)
            q=np.zeros(3);xy=np.c_[np.linspace(.1,1.,8),np.zeros(8)];bank=np.tile(xy,(8,1,1))
            core=SimpleNamespace(pose=q.copy(),latest={'id':0},applied_id=0,v=0.,w=0.)
            verdict=dict(passed=True,reason='PASS',compute_s=0.)
            with patch.object(runtime,'certify',side_effect=lambda *a,**k:verdict.copy()):
                try:
                    e.apply(core,refresh(0,1_000_000_000),event(0,1_000_000_000,q,bank));old=e.follower;receipt=e.path_received_ns
                    verdict['passed']=False;core.latest={'id':1};core.applied_id=1
                    e.apply(core,refresh(1,1_200_000_000,.2222222222),event(1,1_200_000_000,q,bank))
                    self.assertIs(e.follower,old);self.assertEqual(e.path_received_ns,receipt);self.assertEqual(len(client.jobs),2)
                    verdict['passed']=True;job=e.pending[1];start=job['dispatch_ns']
                    client.ready.append(dict(job_id=1,id=1,worker_start_ns=start,worker_end_ns=start+1_000_000,result_received_ns=1_300_000_000,
                        poses=np.c_[xy,np.zeros(8)].tolist(),accepted=True,solver=dict(success=True,solver_wall_s=.001)))
                    e.apply(core,refresh(1,1_300_000_000,.3333333333),None)
                    self.assertEqual(e.path_received_ns,1_200_000_000);self.assertEqual(e.graph_installed,1)
                    self.assertIsNot(e.follower,old)
                finally:e.close()

    def test_periodic36_then_next_control_brakes_without_path_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            field=Field();e=runtime.SafeExecution('OURS-noGRAPH',Path(tmp));e.depth_maps=SimpleNamespace(snapshot=lambda:field)
            q=np.zeros(3);bank=np.tile(np.c_[np.linspace(.1,2.,8),np.zeros(8)],(8,1,1))
            core=SimpleNamespace(pose=q.copy(),latest={'id':0},applied_id=0,v=0.,w=0.);passed=True
            with patch.object(runtime,'certify',side_effect=lambda *a,**k:dict(passed=passed,reason='PASS' if passed else 'DEPTH_SWEEP_UNSAFE',compute_s=0.)):
                try:
                    e.apply(core,refresh(0,1_000_000_000),event(0,1_000_000_000,q,bank));old=e.follower;receipt=e.path_received_ns
                    e.last_command=[.3,.1];e.plant.actual_w=.1;passed=False;e.plant.last_tick=36
                    e.integrate_record(q,q);self.assertEqual(e.ec_pending['check_tick'],36)
                    e.apply(core,refresh(0,1_500_000_000,40/72),None)
                    self.assertIs(e.follower,old);self.assertEqual(e.path_received_ns,receipt);self.assertTrue(e.ec_blocked)
                    self.assertAlmostEqual(core.v,.3-.5/9);self.assertEqual(core.w,0.)
                    for n in range(6):e.apply(core,refresh(0,1_600_000_000+n*100_000_000,(48+n*8)/72),None)
                    self.assertEqual(core.v,0.)
                    passed=True;core.latest={'id':1};core.applied_id=1
                    e.apply(core,refresh(1,2_500_000_000,112/72),event(1,2_500_000_000,q,bank))
                    self.assertFalse(e.ec_blocked);self.assertGreater(core.v,0.)
                finally:e.close()
            rows=[json.loads(x) for x in (Path(tmp)/'exec_cert.jsonl').read_text().splitlines()]
            applied=next(x for x in rows if x['event']=='PERIODIC_APPLY');self.assertEqual(applied['delay_ticks'],4)

    def test_json100ticks_all_five_methods_and_noEC_identity(self):
        self.assertIs(runtime.FrozenNoEC, __import__('nomad_j1.execution',fromlist=['Execution']).Execution)
        for method in config.METHODS:
            with tempfile.TemporaryDirectory() as tmp:
                field=Field();client=Client()
                if method=='NOMAD_RAW':e=runtime.RawExecution(Path(tmp))
                elif method=='OURS-noEC':e=runtime.FrozenNoEC(Path(tmp),client)
                else:e=runtime.SafeExecution(method,Path(tmp),client)
                e.depth_maps=SimpleNamespace(snapshot=lambda:field);q=np.zeros(3);bank=np.tile(np.c_[np.linspace(.1,1.,8),np.zeros(8)],(8,1,1))
                core=SimpleNamespace(pose=q.copy(),latest={'id':0},applied_id=0,v=0.,w=0.)
                with patch.object(runtime,'certify',return_value=dict(passed=True,reason='PASS',compute_s=0.)):
                    try:
                        s=event(0,1_000_000_000,q,bank)
                        for tick in range(104):
                            r=refresh(0,1_000_000_000+round(tick/9*1e9),tick/9)
                            if tick>=9:r.update(valid=False,status='expired')
                            e.apply(core,r,s if tick==0 else None);json.dumps(r,allow_nan=False)
                        json.dumps(s,allow_nan=False)
                    finally:e.close()
                for f in Path(tmp).glob('*.jsonl'):
                    for line in f.read_text().splitlines():json.dumps(json.loads(line),allow_nan=False)

    def test_statistics_completed_blocks_bootstrap_mcnemar_holm(self):
        rows=[]
        for j in config.order():
            r=dict(j,technical_validation='PASS',checkpoint_time_s=10. if j['method']=='OURS' else 12.,collision=j['method']=='OURS-noEC',wall_intrusion=False)
            rows.append(r)
        r=statistics.primary(rows);self.assertEqual(r['completed_seed_count'],13)
        self.assertEqual(r['primary'][0]['ci95_s'],[-2.,-2.]);self.assertEqual(r['primary'][0]['pairs'],39)
        self.assertEqual(r['primary'][1]['noEC_only_failure'],39);self.assertLess(r['primary'][1]['p_holm'],.05)
        partial=statistics.primary(rows[:14]);self.assertEqual(partial['completed_seed_count'],0)
        self.assertEqual(partial['label'],'중간 결과, 판정 보류')

if __name__=='__main__':unittest.main()
