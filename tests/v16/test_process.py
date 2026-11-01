"""Bridge identity and stop checks; all signalling is mocked."""
import importlib.util
from pathlib import Path
import os
import signal
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('processes',ROOT/'v16/kinect_facecam_process_v16.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.proc=self.root/'12345';self.proc.mkdir()
        self.pidfile=self.root/'bridge.pid';self.pidfile.write_text('12345')
        (self.proc/'cmdline').write_bytes(b'/usr/bin/python3\0/tmp/kinect-facecam-bridge-v16.py\0')
        mock=patch.object(p,'PROC_ROOT',self.root);mock.start();self.addCleanup(mock.stop)
        token=patch.object(p,'process_token',return_value='original');token.start();self.addCleanup(token.stop)
    def test_only_matching_bridge_mode_is_accepted(self):
        self.assertEqual(p.instance(self.pidfile,'obs'),(12345,'original'))
        self.assertIsNone(p.instance(self.pidfile,'pw'))
    def test_unrelated_pid_is_not_signalled(self):
        (self.proc/'cmdline').write_bytes(b'/usr/bin/python3\0unrelated.py\0')
        with patch.object(p.os,'pidfd_open') as openfd:p.stop(self.pidfile,'obs')
        openfd.assert_not_called()
    def test_nonpositive_and_malformed_pids_are_rejected(self):
        for value in ['0','-1','1','not-a-pid']:
            self.pidfile.write_text(value);self.assertIsNone(p.instance(self.pidfile,'obs'))
    def test_symlink_and_foreign_owner_are_rejected(self):
        link=self.root/'link';link.symlink_to(self.pidfile)
        self.assertIsNone(p.instance(link,'obs'))
        with patch.object(p.os,'getuid',return_value=os.getuid()+1):self.assertIsNone(p.instance(self.pidfile,'obs'))
    def test_changed_identity_after_pidfd_open_never_receives_signal(self):
        with patch.object(p,'instance',side_effect=[(12345,'old'),(12345,'new')]),patch.object(p.os,'pidfd_open',return_value=10),patch.object(p.os,'close') as close,patch.object(p.signal,'pidfd_send_signal') as send:
            with self.assertRaisesRegex(RuntimeError,'değişti'):p.stop(self.pidfile,'obs')
        send.assert_not_called();close.assert_called_once_with(10)
    def test_stop_uses_pidfd_and_removes_old_pidfile(self):
        with patch.object(p,'instance',side_effect=[(12345,'old'),(12345,'old'),None]),patch.object(p.select,'poll') as poll,patch.object(p.os,'pidfd_open',return_value=10),patch.object(p.os,'close'),patch.object(p.signal,'pidfd_send_signal') as send:
            poll.return_value.poll.return_value=[(10,p.select.POLLIN)]
            p.stop(self.pidfile,'obs')
        send.assert_called_once_with(10,signal.SIGTERM)
        self.assertFalse(self.pidfile.exists())
if __name__=='__main__':unittest.main()
