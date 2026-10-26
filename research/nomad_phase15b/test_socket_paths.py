"""Launcher/batch transport checks; no scipy, GPU, or navigation needed."""
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nomad_isaac.socket_path import socket_path_for_run, validate_socket_path
from .batch import matrix, preflight_sockets
from .config import METHODS, protocol


class SocketPathsTest(unittest.TestCase):
    def test_all_methods_longest_seed_key(self):
        root = Path('/home/gpuadmin/Workspace/NoMaD/artifacts/isaac6/phase15b_depth_02')
        index = max(protocol()['indices'], key=lambda i: (len(f'{i:02d}'), i))
        paths = [socket_path_for_run(root / f'S0_{index:02d}_D750_{m}') for m in METHODS]
        self.assertEqual(len(paths), 6)
        self.assertEqual(len(set(paths)), 6)
        for path in paths:
            self.assertLess(len(os.fsencode(path)), 100)
        jobs = matrix(root)
        self.assertEqual(len(jobs), 48)
        self.assertTrue(all(j['socket_path_bytes'] < 100 for j in jobs))

    def test_short_path_preserved_and_unicode_counted_in_bytes(self):
        self.assertEqual(socket_path_for_run('/tmp/short-run'), Path('/tmp/short-run/ipc.sock'))
        output = Path('/tmp') / ('한' * 35)
        path = socket_path_for_run(output)
        self.assertEqual(path.parent, Path('/tmp'))
        self.assertEqual(path, socket_path_for_run(output))
        self.assertLess(validate_socket_path(path), 100)

    def test_preflight_rejects_long_or_duplicate_paths(self):
        jobs = [dict(output='/tmp/run-a'), dict(output='/tmp/run-b')]
        with patch('nomad_phase15b.batch.socket_path_for_run', return_value=Path('/tmp') / ('x' * 100)):
            with self.assertRaises(ValueError):
                preflight_sockets(jobs)
        with patch('nomad_phase15b.batch.socket_path_for_run', return_value=Path('/tmp/same.sock')):
            with self.assertRaises(ValueError):
                preflight_sockets(jobs)

    def test_shortened_path_can_bind_and_be_cleaned(self):
        with tempfile.TemporaryDirectory() as directory:
            path = socket_path_for_run(Path(directory) / ('long-run-' * 20))
            try:
                with socket.socket(socket.AF_UNIX) as listener:
                    listener.bind(str(path))
                    self.assertTrue(path.exists())
            finally:
                path.unlink(missing_ok=True)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
