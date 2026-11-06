"""Run actual base.main argument validation; stop before socket/files/processes."""
import copy,io,sys,tempfile,unittest
from contextlib import ExitStack,redirect_stderr
from pathlib import Path
from unittest.mock import Mock,patch
from . import launch
from .config import protocol

class ArgumentsValidated(Exception):pass

class LauncherCompatibilityTests(unittest.TestCase):
    def context(self,root,verify=None):
        stack=ExitStack();self.addCleanup(stack.close)
        # main mutates base module globals; restore all of them after each test.
        for name in ('subprocess','verify','METHODS','SCENES','write_json','atomic_json'):
            stack.enter_context(patch.object(launch.base,name,getattr(launch.base,name)))
        stack.enter_context(patch.object(sys,'argv',['launch','--scene','H1','--method','C0-H','--index','201','--output',str(root)]))
        stack.enter_context(patch.object(launch,'plan',return_value=dict(possible=False,reason='ARGUMENT_TEST_ONLY',worker_cpu=None)))
        stack.enter_context(patch.object(launch.os,'sched_setaffinity'))
        self.writer=stack.enter_context(patch.object(launch.base,'write_json'))
        self.spawn=stack.enter_context(patch.object(launch.subprocess,'Popen',side_effect=AssertionError('No child process allowed')))
        self.cleanup=stack.enter_context(patch.object(launch,'cleanup'))
        self.boundary=stack.enter_context(patch.object(launch.base,'socket_path_for_run',side_effect=ArgumentsValidated))
        if verify is not None:stack.enter_context(patch.object(launch,'verify',verify))
        return stack

    def test_actual_base_argument_validation_with_real_phase28t_verify(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'never_created';self.context(out)
            # This executes the real argparse and status/index assertion. The
            # first subsequent function is the boundary; nothing is launched.
            with self.assertRaises(ArgumentsValidated):launch.main()
            self.boundary.assert_called_once_with(out.resolve())
            self.assertEqual(launch.base.METHODS,('C0-H',));self.assertEqual(launch.base.SCENES,('H1',))
            self.assertFalse(out.exists());self.spawn.assert_not_called();self.cleanup.assert_not_called()

    def test_copy_keeps_registered_status_and_provenance(self):
        registered=protocol();original=copy.deepcopy(registered);checker=Mock(return_value=registered)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'never_created';self.context(out,checker)
            with self.assertRaises(ArgumentsValidated):launch.main()
            checker.assert_called_once_with();compatible=launch.base.verify()
            self.assertEqual(compatible['status'],'FROZEN');self.assertEqual(registered,original)
            compatible['indices'].append(999);self.assertEqual(registered,original)
            compatible=launch.base.verify()
            launch.base.write_json(out/'provenance.json',dict(protocol=compatible,phase='26'))
            recorded=self.writer.call_args.args[1]
            self.assertEqual(recorded['protocol'],original)
            self.assertEqual(recorded['protocol']['status'],'FROZEN_SMOKE_ONLY')
            self.assertEqual(recorded['launcher_compatibility']['base_launcher_status'],'FROZEN')
            self.assertEqual(recorded['launcher_compatibility']['original_status'],'FROZEN_SMOKE_ONLY')
            self.assertFalse(recorded['launcher_compatibility']['protocol_file_modified'])
            self.assertTrue(recorded['smoke_excluded']);self.assertFalse(recorded['campaign'])
            self.spawn.assert_not_called();self.assertFalse(out.exists())

    def test_phase28t_verification_failure_is_not_bypassed(self):
        checker=Mock(side_effect=AssertionError('SOURCE_HASH_MISMATCH'))
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'never_created';self.context(out,checker)
            with self.assertRaisesRegex(AssertionError,'SOURCE_HASH_MISMATCH'):launch.main()
            self.boundary.assert_not_called();self.writer.assert_not_called();self.spawn.assert_not_called();self.assertFalse(out.exists())

    def test_base_choices_and_index_reject_unregistered_arguments(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'never_created';self.context(out,Mock(return_value=protocol()))
            with self.assertRaises(ArgumentsValidated):launch.main()
            for field,value in (('--method','C0-NA'),('--scene','L2'),('--index','202')):
                argv=['launch','--scene','H1','--method','C0-H','--index','201','--output',str(out)]
                argv[argv.index(field)+1]=value;self.boundary.reset_mock()
                with patch.object(sys,'argv',argv),redirect_stderr(io.StringIO()):
                    with self.assertRaises(AssertionError if field=='--index' else SystemExit):launch.base.main()
                self.boundary.assert_not_called()
            self.spawn.assert_not_called();self.assertFalse(out.exists())

    def test_wrapper_rejects_legacy_smoke_flag(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'never_created';self.context(out,Mock(return_value=protocol()))
            sys.argv.append('--smoke')
            with self.assertRaises(AssertionError):launch.main()
            self.boundary.assert_not_called();self.spawn.assert_not_called();self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
