"""The reopen warning survives app restarts without confusing a reused PID."""
import importlib.util
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('permissions',ROOT/'v17/kinect-facecam-firefox-permission-v17.py')
permissions=importlib.util.module_from_spec(spec);spec.loader.exec_module(permissions)


class MarkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='kinect-marker-test-')
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'state'/'firefox-restart.json'
        self.patch=patch.object(permissions,'marker_path',return_value=self.path)
        self.patch.start();self.addCleanup(self.patch.stop)

    def test_read_does_not_create_marker(self):
        self.assertEqual(permissions.pending_restart([42]),[])
        self.assertFalse(self.path.exists())

    def test_pending_browser_is_remembered(self):
        with patch.object(permissions,'process_token',return_value='123'):
            permissions.remember_restart([42])
            self.assertEqual(permissions.pending_restart([42]),[42])
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)

    def test_new_process_reusing_pid_is_not_blocked(self):
        with patch.object(permissions,'process_token',return_value='123'):
            permissions.remember_restart([42])
        with patch.object(permissions,'process_token',return_value='456'):
            self.assertEqual(permissions.pending_restart([42]),[])

    def test_closed_browser_is_not_blocked(self):
        with patch.object(permissions,'process_token',return_value='123'):
            permissions.remember_restart([42])
            self.assertEqual(permissions.pending_restart([]),[])


if __name__=='__main__':unittest.main()
