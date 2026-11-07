import copy,io,json,tempfile,unittest,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import ExitStack
import numpy as np
from nomad_phase32o.test_exec_cert import field
from nomad_phase32o.exec_cert import rollout,certify,swept_clearance
from nomad_isaac.common import integrate_se2
from .policy import CappedNA,normal_choice,continuation_certificate
from .runtime import Execution,WorkerGate,RecoveryGate,ECInstaller

class Tests(unittest.TestCase):
 def test_full_na_forward_integration_unchanged(self):
  path=[[0,0],[.2,.1],[.6,.2]];q=np.array([0.,0.,.15]);c=CappedNA();c.replace_path(path,q,.1);v=.1;r=rollout(q,[v,0],path)
  for k in range(len(r['commands'])):
   if k%8==0:(v,w),d=c.control(q,v)
   q=integrate_se2(q,v,w,1/72);np.testing.assert_allclose(q,r['poses'][k+1],atol=1e-12)
 def test_periodic_clock_and_continuing_rotation(self):
  f=field([.8,.6]);c=CappedNA();c.replace_path([[0,0],[-1,0]],[0,0,0],0);c.control([0,0,0],0);self.assertEqual(c.mode,'ROTATE')
  # Remaining turn is below90deg: a reinstall would incorrectly leave rotation.
  c.target_yaw=.5;q=np.array([0.,0.,.2]);r=continuation_certificate(c,q,[0,.4],f,36)
  self.assertEqual(r['control_phase_tick'],4);self.assertTrue(r['passed']);self.assertEqual(c.mode,'ROTATE')
  independent=copy.deepcopy(c);poses=[q.copy()];commands=[];v,w=0.,.4
  for j in range(144):
   if (36+j)%8==0:
    (v,w),d=independent.control(q,v)
    if d['completed']:break
   q=integrate_se2(q,v,w,1/72);poses.append(q.copy());commands.append([v,w])
  ref=swept_clearance(f,np.array(poses),np.array(commands));self.assertAlmostEqual(r['clearance_m'],ref['clearance_m'])
 def test_capped_execution_matches_offline_cap(self):
  p=[[0,0],[.4,.1],[.8,.3]];q=np.zeros(3);c=CappedNA();c.replace_path(p,q,.3);c.speed_cap=.1;v=.3;r=rollout(q,[v,0],p,.1)
  for k in range(len(r['commands'])):
   if k%8==0:(v,w),_=c.control(q,v)
   q=integrate_se2(q,v,w,1/72);np.testing.assert_allclose(q,r['poses'][k+1],atol=1e-12)
 def test_fallback_full_then_same_candidates_slow(self):
  options=[dict(key=str(i),rank=i+1) for i in range(3)];calls=[]
  def check(x,cap):calls.append((x['key'],cap));return {'passed':cap==.1 and x['key']=='1'}
  r=normal_choice(options[0],options,check)
  self.assertEqual(calls,[('0',None),('1',None),('2',None),('0',.1),('1',.1)]);self.assertEqual(r['item']['rank'],2);self.assertEqual(r['cap'],.1)
 def test_periodic_rejected_primary_skipped_at_full_speed(self):
  options=[dict(key='0'),dict(key='1')];calls=[]
  def check(x,cap):calls.append((x['key'],cap));return {'passed':cap==.1}
  r=normal_choice(options[0],options,check,primary_rejected=True)
  self.assertEqual(calls,[('1',None),('0',.1)]);self.assertEqual(r['cap'],.1)
 def test_stop_and_cap_retention(self):
  options=[dict(key='0'),dict(key='1')];calls=[]
  def no(x,cap):calls.append(cap);return {'passed':False}
  self.assertEqual(normal_choice(options[0],options,no)['route'],'STOP_WAIT')
  calls.clear();normal_choice(options[0],options,no,.1);self.assertEqual(calls,[.1,.1])
 def test_r3_filter_uses_original_selection_rule(self):
  now=time.monotonic_ns();result=dict(job_id=2,end_ns=now,results=[dict(index=i,accepted=True,path=[[0,0],[i+1,0]],progress_m=7-i,length_m=1.) for i in range(7)],selected_sample=0)
  worker=SimpleNamespace(poll=lambda:copy.deepcopy(result));records=[];calls=[]
  owner=SimpleNamespace(detour={'job_id':2,'dispatch_ns':now-1000},repair_pending=None,ec_context=(SimpleNamespace(pose=np.zeros(3)),{'simulation_time_s':1.}),depth_maps=SimpleNamespace(snapshot=lambda:field()),ec_tokens=set(),ec_cap=None,ec_blocked=False,actual_vw=lambda:[0,0],ec_log=lambda *a,**k:records.append(k))
  def check(*args):i=len(calls);calls.append(i);return dict(passed=i in (3,4),check_id=i)
  owner.ec_check=check;r=WorkerGate(worker,owner).poll();self.assertEqual(r['selected_sample'],3);self.assertEqual(len(calls),7);self.assertTrue(all(x['accepted'] for x in r['results']));json.dumps(r)
 def test_r2_reject_is_forwarded_to_frozen_failure_branch(self):
  now=time.monotonic_ns();res=dict(job_id=1,end_ns=now,results=[dict(accepted=True,path=[[0,0],[1,0]])],selected_sample=0)
  records=[];o=SimpleNamespace(detour=None,repair_pending={'job_id':1,'dispatch_ns':now},ec_context=(SimpleNamespace(pose=np.zeros(3)),{'simulation_time_s':1}),depth_maps=SimpleNamespace(snapshot=lambda:field()),ec_tokens=set(),ec_cap=None,ec_blocked=False,actual_vw=lambda:[0,0],ec_check=lambda *a:dict(passed=False,check_id=0),ec_log=lambda *a,**k:records.append(k))
  r=WorkerGate(SimpleNamespace(poll=lambda:res),o).poll();self.assertIsNone(r['selected_sample']);self.assertEqual(records[0]['route'],'R2_TO_R3');self.assertTrue(o.ec_blocked)
 def test_recovery_does_not_erase_ec_stop_decision(self):
  changes=[];base=SimpleNamespace(state='NORMAL',decision=lambda mode:changes.append(mode));o=SimpleNamespace(ec_blocked=True);g=RecoveryGate(base,o)
  g.decision('STOP_WAIT');g.decision('NORMAL');self.assertEqual(changes,['STOP_WAIT']);g.state='RECOVER_ROTATE';self.assertEqual(base.state,'RECOVER_ROTATE');o.ec_blocked=False;g.decision('NORMAL');self.assertEqual(changes[-1],'NORMAL')
 def test_json_all_ec_records_and_follower_diagnostics(self):
  o=object.__new__(Execution);o.ec_file=io.StringIO();o.ec_check_sequence=0;o.ec_generation=0;o.depth_maps=SimpleNamespace();f=field([.7,.8]);f.metadata={'frame_id':0,'sim_s':0};p=[[0,0],[1,0]];q=np.zeros(3);c=CappedNA();c.replace_path(p,q,0);c.speed_cap=.1;v=0.
  for tick in range(144):
   if tick%8==0:(v,w),diag=c.control(q,v);json.dumps(diag,allow_nan=False)
   q=integrate_se2(q,v,w,1/72)
   if tick%36==0:o.ec_check(q,[v,w],p,f,tick/72,'NORMAL','PERIODIC',.1,c)
  for line in o.ec_file.getvalue().splitlines():json.dumps(json.loads(line),allow_nan=False)
 def test_installer_mro_catches_raw_path(self):
  self.assertLess(Execution.__mro__.index(ECInstaller),Execution.__mro__.index(__import__('nomad_phase28.runtime',fromlist=['NAExecution']).NAExecution))
 def test_periodic_delay_grid(self):
  for install in range(0,800,8):
   for n in range(1,10):
    check=install+n*36;apply=((check+7)//8)*8;self.assertIn(apply-check,(0,4));self.assertLessEqual((apply-check)/72,.056)


class WiringTests(unittest.TestCase):
 def fake_execution(self):
  o=object.__new__(Execution);o.ec_method='C0-NA+EC';o.ec_blocked=False;o.ec_cap=None;o.ec_generation=0;o.ec_due=None;o.ec_pending=None;o.ec_context=None;o.ec_tokens=set();o.ec_check_sequence=0;o.ec_samples={};o.ec_switch=None;o.ec_file=io.StringIO();o.ec_ticks=io.StringIO();o.repair_log=io.StringIO();o.command_log=io.StringIO();o.path_log=io.StringIO()
  f=field();f.observed=np.ones(f.occupied.shape,dtype=bool);f.metadata={'frame_id':0,'sim_s':0};o.depth_maps=SimpleNamespace(snapshot=lambda:f);o.snapshot=f;o.last_command=[0.,0.];o.plant=SimpleNamespace(actual_w=0,last_tick=0);o.active_sample=0;o.sp=None;o.follower=None;o.mode='NORMAL';o.repair_active=False;o.detour=None;o.detour_active=False;o.repair_pending=None;o.recovery=RecoveryGate(SimpleNamespace(state='NORMAL',decision=lambda mode:None),o)
  o.path_sequence=0;o.path_prior=None;o.path_jobs={};o.path_worker=None;o.named_method='M3_DETOUR'
  return o
 def test_g18_parent_raw_install_and_graph_result_both_go_through_ec(self):
  from concurrent.futures import Future
  o=self.fake_execution();o.ec_method='G18+EC';o.path_method='G18';future=Future();o.path_worker=SimpleNamespace(submit=lambda job,f:future);path=[[0,0],[.5,0],[1,0]];o.ec_switch={'id':1};o.ec_samples[1]={'worlds':np.repeat(np.array(path)[None],8,axis=0)}
  core=SimpleNamespace(pose=np.zeros(3),latest={'id':1},applied_id=1);refresh=dict(simulation_time_s=0.,monotonic_ns=100,valid=True)
  o.new_path(path,core,refresh,1,'SAFE');self.assertIsInstance(o.sp,CappedNA);self.assertEqual(o.ec_generation,1);self.assertEqual(len(o.path_jobs),1)
  future.set_result(dict(job_id=0,result_received_ns=101,worker_start_ns=90,poses=[[0,0,0],[.5,0,0],[1,0,0]]));refresh.update(simulation_time_s=8/72,monotonic_ns=102);o.ec_switch=None
  # Rejected normal Graph falls back/STOP, and does not silently update prior.
  o.ec_check=lambda *a,**kw:dict(passed=False,check_id=0)
  with patch('nomad_phase32.runtime.decision',return_value=('ACCEPTED',False,.01)):o.collect_paths(core,refresh,None)
  self.assertEqual(o.mode,'STOP_WAIT');self.assertIsNone(o.path_prior)
  records=[json.loads(x) for x in o.path_log.getvalue().splitlines()];self.assertEqual(records[-1]['disposition'],'EXEC_CERT_REJECT');self.assertFalse(records[-1]['applied'])
 def test_g18_reference_sample_survives_raw_ec_alternative(self):
  from concurrent.futures import Future
  o=self.fake_execution();o.ec_method='G18+EC';o.path_method='G18';f=Future();o.path_worker=SimpleNamespace(submit=lambda job,field:f)
  bank=np.array([[[0,0],[.5,.1*i],[1,.1*i]] for i in range(8)]);o.ec_samples[1]={'worlds':bank};o.ec_switch={'id':1};core=SimpleNamespace(pose=np.zeros(3),latest={'id':1},applied_id=1);refresh=dict(simulation_time_s=0.,monotonic_ns=100,valid=True)
  o.ec_check=lambda pose,vw,path,*a,**kw:dict(passed=not np.allclose(path,bank[0]),check_id=0)
  o.new_path(bank[0],core,refresh,1,'SAFE');self.assertNotEqual(o.active_sample,0)
  f.set_result(dict(job_id=0,result_received_ns=101,poses=np.c_[bank[0],np.zeros(3)].tolist()));o.ec_check=lambda *a,**kw:dict(passed=True,check_id=1);o.ec_switch=None;refresh.update(simulation_time_s=8/72,monotonic_ns=102)
  with patch('nomad_phase32.runtime.decision',return_value=('ACCEPTED',False,.01)):o.collect_paths(core,refresh,None)
  self.assertEqual(o.active_sample,0);self.assertEqual(o.path_kind,'GRAPH18')
 def test_periodic_fallback_uses_latest_native_candidate_bank(self):
  o=self.fake_execution();old=np.array([[0,0],[1,0]]);new=np.array([[0,0],[.5,.2],[1,.3]]);o.ec_samples={0:{'worlds':np.repeat(old[None],8,axis=0)},2:{'worlds':np.repeat(new[None],8,axis=0)}};o.path_source_id=0;o.active_sample=0
  core=SimpleNamespace(pose=np.zeros(3));refresh=dict(simulation_time_s=40/72,monotonic_ns=1)
  o.ec_install(old,core,refresh,0,'SAFE',periodic_rejected=True)
  self.assertEqual(o.path_source_id,2);np.testing.assert_array_equal(o.follower.path.points,new)
 def test_cap_released_only_by_full_fresh_install(self):
  o=self.fake_execution();path=[[0,0],[1,0]];o.ec_samples[1]={'worlds':np.repeat(np.array(path)[None],8,axis=0)};o.ec_cap=.1
  core=SimpleNamespace(pose=np.zeros(3));refresh=dict(simulation_time_s=0.,monotonic_ns=1);o.ec_install(path,core,refresh,1,'GRAPH18');self.assertEqual(o.sp.speed_cap,.1)
  o.ec_switch={'id':1};o.ec_install(path,core,refresh,1,'SAFE');self.assertIsNone(o.sp.speed_cap);self.assertTrue(json.loads(o.ec_file.getvalue().splitlines()[-1])['cap_released'])
 def test_periodic_reject_is_not_bypassed_by_simultaneous_fresh_keep(self):
  o=self.fake_execution();o.ec_pending=dict(generation=0,state='NORMAL',path=np.array([[0,0],[1,0]]),source_id=0,check_tick=36,check_id=3);o.path_kind='SAFE';o.ec_samples[0]={'worlds':np.repeat(np.array([[[0,0],[1,0]]]),8,axis=0)}
  called=[];o.ec_install=lambda *a,**kw:called.append('fallback');core=SimpleNamespace(pose=np.zeros(3));switch=dict(id=1,observation_pose=[0,0,0],overnight_metric_samples=np.repeat(np.array([[[0,0],[1,0]]]),8,axis=0).tolist());refresh=dict(simulation_time_s=40/72)
  with patch('nomad_phase29.runtime.PathExecution.apply',side_effect=lambda *args:called.append('parent')):o.apply(core,refresh,switch)
  self.assertEqual(called,['fallback','parent']);r=json.loads(o.ec_file.getvalue().splitlines()[-1]);self.assertEqual(r['delay_ticks'],4)

class PreparationTests(unittest.TestCase):
 def test_fallback_counts_include_periodic_transitions_without_passes(self):
  from .report import fallback_counts
  ev=[dict(event='INSTALL',route='PRIMARY_FULL'),dict(event='INSTALL',route='SAFE_SLOW'),dict(event='SOLVER_FILTER',route='SOLVER_EC_PASS'),dict(event='PERIODIC_APPLY',action='R2_TO_R3'),dict(event='FALLBACK',route='STOP_WAIT')]
  self.assertEqual(fallback_counts(ev),{'SAFE_SLOW':1,'R2_TO_R3':1,'STOP_WAIT':1})
 def test_fixed_order_and_baselines(self):
  from .config import verify,registered_order
  from .report import baselines
  p=verify();self.assertEqual(len(registered_order()[1]),30);self.assertEqual(len(baselines()),30);self.assertEqual(p['deviation']['original_label'],'OFFLINE_FAIL');self.assertEqual(p['execution_certificate']['period_ticks'],36)
 def test_thirty_launch_argument_checks_without_process(self):
  from . import config,launch
  from nomad_isaac.socket_path import socket_path_for_run,validate_socket_path
  class Boundary(Exception):pass
  for j in config.registered_order()[1]:
   out=config.RUN_ROOT/'main'/f"{j['scene']}_{j['index']}_{j['method']}"/'attempt1'
   with ExitStack() as stack:
    base=launch.old.base
    for key in ('subprocess','verify','METHODS','SCENES','write_json'):stack.enter_context(patch.object(base,key,getattr(base,key)))
    stack.enter_context(patch.dict(launch._main.__globals__,plan=lambda:dict(possible=True,worker_cpu=7,driver_cpus=[0]),pin=lambda x:dict(passed=True)))
    stack.enter_context(patch.object(launch.old.os,'sched_setaffinity'));proc=stack.enter_context(patch.object(launch.subprocess,'Popen'));stack.enter_context(patch.object(base,'socket_path_for_run',side_effect=Boundary))
    stack.enter_context(patch('sys.argv',['launch','--scene',j['scene'],'--method',j['method'],'--index',str(j['index']),'--output',str(out)]))
    with self.assertRaises(Boundary):launch.main()
    proc.assert_not_called();self.assertFalse(out.exists())
   self.assertLess(validate_socket_path(socket_path_for_run(out)),100)
 def test_simulationapp_precedes_numerical_import(self):
  from .config import ROOT
  s=(ROOT/'research/nomad_phase26/simulator.py').read_text().replace('from nomad_phase26.config','from nomad_phase32.config').replace('from nomad_phase26.execution','from nomad_phase32.runtime')
  compile(s,'<phase32-kit-first>','exec');self.assertLess(s.index('# SimulationApp is now initialized.'),s.index('from nomad_phase32.runtime'))
 def test_gate_and_report_without_navigation(self):
  from . import config,report
  old=report.baselines();rows=[]
  for j in config.registered_order()[1]:
   rows.append(dict(j,technical_validation='PASS',success=True,collision=False,goal_time_s=35.,stopped_fraction=.1,output='/unused',ec_checks=0,ec_rejects=0))
  base_collision=sum(x['collision'] for x in old);self.assertGreater(base_collision,0);self.assertEqual(report.decide(rows,old)['label'],'EC_HELPS')
  bad=copy.deepcopy(rows)
  for r in bad:r['collision']=True
  self.assertEqual(report.decide(bad,old)['label'],'EC_NO_HELP');self.assertEqual(report.decide(rows[:-1],old)['label'],'EC_NO_HELP')
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'run/metrics').mkdir(parents=True);(root/'docs').mkdir()
   for i,r in enumerate(rows):(root/'run/metrics'/f'{i}.json').write_text(json.dumps(r))
   with patch.object(report,'ROOT',root),patch.object(report,'OUT',root/'out'),patch.object(report,'baselines',return_value=old):doc=report.generate(root/'run')
   self.assertIn('EC_HELPS',doc.read_text());self.assertIn('OFFLINE_FAIL',doc.read_text())
 def test_period_and_fallback_definitions_in_protocol(self):
  from .config import verify
  p=verify();ec=p['execution_certificate'];self.assertEqual(ec['max_reject_apply_delay_ticks'],4);self.assertIn('same SAFE list',ec['normal']);self.assertIn('next FRESH',ec['capped'])

if __name__=='__main__':unittest.main()
