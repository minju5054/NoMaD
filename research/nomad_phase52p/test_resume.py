"""Audit and metadata recovery regressions; no simulation/solver launches."""
import ast,copy,json,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import ExitStack
from .metrics import waypoint_lifetime
from . import resume,campaign


def missing(t):return dict(simulation_time_s=t,latest_received_id=-1,waypoint_id=-1,waypoint_age_wall_s=None,
    valid=False,status='missing',new_timeout=False,applied_command_source='WAYPOINT_TIMEOUT')
def chunk(t,source='NORMAL'):return dict(simulation_time_s=t,latest_received_id=0,waypoint_id=0,waypoint_age_wall_s=.02,
    valid=True,status='valid',new_timeout=False,applied_command_source=source)
def dump(path,row):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(row))

class LifetimeTests(unittest.TestCase):
    def test_startup_is_allowed_and_latch_vs_control_times_are_separate(self):
        records=[missing(0),missing(1),chunk(2),chunk(3)]
        r=waypoint_lifetime(records,4,[dict(id=0,latched_sim_s=1.9,terminal_unapplied=False)])
        self.assertEqual(r['initial_wait_s'],2);self.assertEqual(r['first_chunk_received_s'],1.9)
        self.assertEqual(r['startup_missing_timeout_rows'],2);self.assertEqual(r['new_timeout_count'],0)
    def test_post_first_chunk_timeout_fails_even_without_any_normal(self):
        records=[missing(0),chunk(1,'STOP_WAIT'),dict(chunk(2),applied_command_source='WAYPOINT_TIMEOUT')]
        with self.assertRaisesRegex(AssertionError,'POST_CHUNK'):waypoint_lifetime(records,3)
    def test_receipt_alone_blocks_forgiving_later_missing(self):
        with self.assertRaisesRegex(AssertionError,'POST_CHUNK'):
            waypoint_lifetime([missing(0),missing(1)],2,[dict(id=0,latched_sim_s=.5)])
    def test_new_timeout_always_fails(self):
        for records in ([dict(missing(0),new_timeout=True)],[missing(0),dict(chunk(1),new_timeout=True)]):
            with self.assertRaisesRegex(AssertionError,'EXPIRY'):waypoint_lifetime(records,2)
    def test_no_chunk_and_drained_result_are_missing_wait_not_expiry(self):
        r=waypoint_lifetime([missing(0),missing(1)],2,[dict(id=0,latched_sim_s=2.,terminal_unapplied=True)])
        self.assertEqual(r['initial_wait_s'],2);self.assertIsNone(r['first_chunk_received_s'])
        self.assertIsNone(r['first_chunk_control_s'])
    def test_declared_arrival_first_result(self):
        r=waypoint_lifetime([missing(0),dict(simulation_time_s=1.,applied_command_source='DECLARED_ARRIVAL')],1,
            [dict(id=0,latched_sim_s=1.,terminal_unapplied=True)],declared_id=0)
        self.assertEqual(r['initial_wait_s'],1);self.assertEqual(r['first_chunk_received_s'],1)
    def test_malformed_missing_does_not_get_exception(self):
        with self.assertRaisesRegex(AssertionError,'POST_CHUNK'):waypoint_lifetime([dict(missing(0),valid=True)],1)

class RecoveryTests(unittest.TestCase):
    def test_original_protocol_and_runtime_configuration_are_unchanged(self):
        from . import config
        from nomad_isaac.common import sha256_file
        self.assertEqual(sha256_file(config.HERE/'protocol.json'),resume.ORIGINAL_PROTOCOL)
        original=subprocess.check_output(['git','show','bfe19d0:research/nomad_phase52p/config.py'],cwd=config.ROOT,text=True)
        def method(text):return next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='runtime_config')
        self.assertEqual(ast.dump(method(original)),ast.dump(method((config.HERE/'config.py').read_text())))
        p=config.protocol()
        for name in ('runtime.py','graph.py','worker.py','pool.py','launch.py','simulator.py'):
            path=config.HERE/name;self.assertEqual(sha256_file(path),p['source_sha256'][str(path.relative_to(config.ROOT))])
    def fixture(self,root):
        plan=[]
        for i in range(2):
            key=f'SLW_D075_221_TEST{i}';outputs=[str(root/'main'/key/f'attempt{k}') for k in (1,2)]
            j=dict(key=key,scene='SLW_D075',method=f'TEST{i}',index=221,outputs=outputs);plan.append(j)
            for k,output in enumerate(outputs,1):
                d=Path(output);d.mkdir(parents=True);(d/'raw.txt').write_text(f'immutable{i}:{k}')
                if k==1 or i==0:dump(d/'launch_complete.json',{'exit_code':0});dump(d/'summary.json',{'success':False if k==1 else True})
                if k==1 or i==0:dump(root/'attempt_metrics'/f'{key}_{k}.json',dict(j,attempt=k,output=output,exit_code=0,technical_validation='FAIL',classification='TECHNICAL_FAILURE',error='AssertionError()',success=False))
            dump(root/'metrics'/f'{key}.json',dict(j,attempt=2,technical_validation='FAIL',success=False))
        dump(root/'state.json',dict(status='INTERRUPTED',pid=None,error='previous interrupt'))
        return plan
    def fake_audit(self,path):
        return dict(technical_validation='PASS',success=False,collision=True,output=str(path),
            initial_wait_s=2.,first_chunk_received_s=1.9,first_chunk_control_s=2.,startup_missing_timeout_rows=18,
            new_timeout_count=0,post_chunk_waypoint_timeout_rows=0)
    def patches(self,stack,root,plan):
        stack.enter_context(patch.object(resume,'verify',return_value={}))
        stack.enter_context(patch.object(resume,'planned',return_value=plan))
        stack.enter_context(patch.object(resume,'revision',return_value={'required_attempt1_keys':[j['key'] for j in plan]}))
        stack.enter_context(patch.object(resume,'OUT',root/'report'))
        stack.enter_context(patch.object(resume,'sha256_file',return_value='test-hash'))
    def test_restore_failed_navigation_first_attempt_exclude_successful_retry_and_interrupted_retry(self):
        with tempfile.TemporaryDirectory() as td,ExitStack() as stack:
            root=Path(td);plan=self.fixture(root);self.patches(stack,root,plan);before=resume.raw_inventory(plan)
            result=resume.repair(root,audit_fn=self.fake_audit);self.assertEqual(result['recovered'],2);self.assertEqual(result['attempt2_used'],0)
            for j in plan:
                final=resume.read(root/'metrics'/f"{j['key']}.json");self.assertEqual(final['attempt'],1);self.assertFalse(final['success']);self.assertTrue(final['collision'])
                retry=resume.read(root/'attempt_metrics'/f"{j['key']}_2.json");self.assertFalse(retry['included_in_analysis']);self.assertEqual(retry['exclusion_reason'],resume.REASON)
                self.assertEqual(resume.original_record(root,j['key'],1)['error'],'AssertionError()')
            self.assertEqual(before,resume.raw_inventory(plan));resume.audit_gate(root,audit_fn=self.fake_audit)
            # Repetition is metadata-idempotent and never reintroduces retry2.
            again=resume.repair(root,audit_fn=self.fake_audit);self.assertEqual(again['recovered'],2)
    def test_other_audit_failure_aborts_before_metric_mutations(self):
        with tempfile.TemporaryDirectory() as td,ExitStack() as stack:
            root=Path(td);plan=self.fixture(root);self.patches(stack,root,plan)
            before={str(f):f.read_bytes() for folder in ('metrics','attempt_metrics') for f in (root/folder).glob('*.json')}
            def fail(path):
                if 'TEST1' in str(path):raise AssertionError('actual later timeout')
                return self.fake_audit(path)
            with self.assertRaisesRegex(AssertionError,'later timeout'):resume.repair(root,audit_fn=fail)
            self.assertTrue(all(Path(f).read_bytes()==data for f,data in before.items()))
    def test_campaign_gate_precedes_navigation_and_failure_blocks_it(self):
        for passed in (True,False):
            order=[]
            def original(root,smoke=False):order.append('navigation')
            base=SimpleNamespace(campaign=original)
            base.main=lambda:base.campaign(Path('/tmp/nonexistent-test-only'))
            def gate(root):
                order.append('audit')
                if not passed:raise AssertionError('gate failed')
            with patch.object(resume,'audit_gate',side_effect=gate):
                if passed:campaign.run_with_audit_gate(base);self.assertEqual(order,['audit','navigation'])
                else:
                    with self.assertRaisesRegex(AssertionError,'gate failed'):campaign.run_with_audit_gate(base)
                    self.assertEqual(order,['audit'])
            self.assertIs(base.campaign,original)
    def test_eligibility_never_uses_outcomes_and_rejects_non_audit_failures(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan=self.fixture(root);j=plan[0]
            self.assertTrue(resume.eligible(j,root))
            f=root/'attempt_metrics'/f"{j['key']}_1.json";r=resume.read(f);r['success']=True;dump(f,r);self.assertTrue(resume.eligible(j,root))
            r['error']='Launcher error';dump(f,r);self.assertFalse(resume.eligible(j,root))

if __name__=='__main__':unittest.main()
