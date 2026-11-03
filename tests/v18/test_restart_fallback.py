"""Legacy repair fallback; all browser, signal and portal actions are mocked."""
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('backend',ROOT/'v18/kinect-facecam-firefox-permission-v18.py')
backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)


class FallbackTests(unittest.TestCase):
    def setUp(self):
        self.data={'permission':'allowed','old':True,'new':False}
        self.calls=[]
        def pids():return [42] if self.data['old'] else ([99] if self.data['new'] else [])
        def inspect():return {'status':self.data['permission'],'firefox_pids':pids(),'restart_pids':[],'changed':False}
        def call(method):
            self.calls.append(method)
            self.data['permission']='unset'
            return subprocess.CompletedProcess([],0,'','')
        def close(pid,token):self.data['old']=False
        def launch(*args,**kwargs):
            self.data['new']=True
            return MagicMock(poll=MagicMock(return_value=None))
        replacements=[patch.object(backend,'ensure_browser_stream'),patch.object(backend.os.path,'isfile',return_value=True),
            patch.object(backend.os,'access',return_value=True),patch.object(backend,'inspect',side_effect=inspect),
            patch.object(backend,'permission',side_effect=lambda:self.data['permission']),
            patch.object(backend,'firefox_pids',side_effect=pids),patch.object(backend,'call',side_effect=call),
            patch.object(backend,'process_token',side_effect=lambda pid:'token' if pid==42 and self.data['old'] else None),
            patch.object(backend,'remember_restart'),patch.object(backend,'request_firefox_close',side_effect=close),
            patch.object(backend.subprocess,'Popen',side_effect=launch)]
        self.mocks=[]
        for p in replacements:
            self.mocks.append(p.start());self.addCleanup(p.stop)
        self.close=self.mocks[-2]
        self.launch=self.mocks[-1]

    def test_no_consent_means_no_reset_no_close_no_launch(self):
        with self.assertRaisesRegex(RuntimeError,'onayı'):
            backend.restart_firefox()
        self.assertEqual(self.calls,[])
        self.close.assert_not_called();self.launch.assert_not_called()

    def test_browser_binary_missing_leaves_everything_alone(self):
        with patch.object(backend.os.path,'isfile',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'bulunamadı'):
                backend.restart_firefox(True)
        self.close.assert_not_called();self.launch.assert_not_called()

    def test_missing_stream_leaves_firefox_and_permissions_alone(self):
        with patch.object(backend,'ensure_browser_stream',side_effect=backend.StreamNotReady('source missing')):
            with self.assertRaisesRegex(backend.StreamNotReady,'source missing'):
                backend.restart_firefox(True)
        self.assertEqual(self.calls,[])
        self.close.assert_not_called();self.launch.assert_not_called()

    def test_permission_service_failure_does_not_close_browser(self):
        with patch.object(backend,'inspect',side_effect=RuntimeError('portal unavailable')):
            with self.assertRaisesRegex(RuntimeError,'portal'):
                backend.restart_firefox(True)
        self.close.assert_not_called();self.launch.assert_not_called()

    def test_reset_failure_does_not_close_browser(self):
        with patch.object(backend,'call',return_value=subprocess.CompletedProcess([],1,'','reset failed')):
            with self.assertRaisesRegex(RuntimeError,'reset failed'):
                backend.restart_firefox(True)
        self.close.assert_not_called();self.launch.assert_not_called()

    def test_explicit_fallback_can_clear_allow_and_reopen(self):
        result=backend.restart_firefox(True)
        self.assertTrue(result['restarted']);self.assertTrue(result['changed'])
        self.assertEqual(result['status'],'unset')
        self.assertEqual(self.calls,['DeletePermission'])
        self.close.assert_called_once_with(42,'token')
        self.launch.assert_called_once()
        self.assertEqual(self.launch.call_args.args[0],['/usr/bin/firefox'])

    def test_unset_decision_still_allows_reopen_without_deleting(self):
        self.data['permission']='unset'
        result=backend.restart_firefox(True)
        self.assertTrue(result['restarted']);self.assertFalse(result['changed'])
        self.assertEqual(self.calls,[])

    def test_shutdown_timeout_does_not_force_kill_or_launch_duplicate(self):
        self.close.side_effect=lambda *args:None
        with patch.object(backend.time,'monotonic',side_effect=[0,13]):
            with self.assertRaisesRegex(RuntimeError,'Zorla sonlandırılmadı'):
                backend.restart_firefox(True)
        self.close.assert_called_once();self.launch.assert_not_called()

    def test_new_concurrent_browser_is_not_closed(self):
        def new_browser(*args):self.data.update(old=False,new=True)
        self.close.side_effect=new_browser
        with self.assertRaisesRegex(RuntimeError,'Başka bir Firefox'):
            backend.restart_firefox(True)
        self.close.assert_called_once();self.launch.assert_not_called()

    def test_launch_failure_is_reported(self):
        self.launch.side_effect=OSError('launch failed')
        with self.assertRaisesRegex(OSError,'launch failed'):
            backend.restart_firefox(True)

    def test_no_new_process_is_not_success(self):
        self.launch.side_effect=lambda *a,**kw:MagicMock(poll=MagicMock(return_value=1))
        with self.assertRaisesRegex(RuntimeError,'doğrulanamadı'):
            backend.restart_firefox(True)


class PidHandleTests(unittest.TestCase):
    def run_close(self, token='original', uid=None):
        node=MagicMock()
        node.stat.return_value=SimpleNamespace(st_uid=os.getuid() if uid is None else uid)
        node.joinpath.return_value.read_text.return_value='firefox\n'
        return [patch.object(backend,'Path',return_value=node),
                patch.object(backend,'process_token',return_value=token),
                patch.object(backend.os,'pidfd_open',return_value=7),
                patch.object(backend.signal,'pidfd_send_signal'),patch.object(backend.os,'close')]

    def test_signal_targets_checked_pid_handle(self):
        patches=self.run_close()
        mocks=[p.start() for p in patches]
        try:
            backend.request_firefox_close(42,'original')
            mocks[3].assert_called_once_with(7,signal.SIGTERM)
            mocks[4].assert_called_once_with(7)
        finally:
            for p in reversed(patches):p.stop()

    def test_reused_pid_is_not_signalled(self):
        patches=self.run_close(token='changed')
        mocks=[p.start() for p in patches]
        try:
            with self.assertRaisesRegex(RuntimeError,'kimliği değişti'):
                backend.request_firefox_close(42,'original')
            mocks[3].assert_not_called();mocks[4].assert_called_once_with(7)
        finally:
            for p in reversed(patches):p.stop()

    def test_other_user_process_is_not_signalled(self):
        patches=self.run_close(uid=os.getuid()+1)
        mocks=[p.start() for p in patches]
        try:
            with self.assertRaisesRegex(RuntimeError,'Başka kullanıcı'):
                backend.request_firefox_close(42,'original')
            mocks[3].assert_not_called()
        finally:
            for p in reversed(patches):p.stop()


if __name__=='__main__':unittest.main()
