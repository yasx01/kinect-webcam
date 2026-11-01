"""Preflight UI: no real DBus writes, browser termination or camera start."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gui',ROOT/'v16/kinect-facecam-gui-v16.py')
gui=importlib.util.module_from_spec(spec);spec.loader.exec_module(gui)
app=gui.QApplication([])


def state(status, **extra):
    return dict(status=status,firefox_pids=[],changed=False,**extra)


class PermissionGuiTests(unittest.TestCase):
    def setUp(self):
        self.parent=gui.QWidget()
        self.addCleanup(self.parent.close)

    def dialog(self, status='denied', for_start=False):
        d=gui.BrowserPermissionDialog(self.parent,for_start=for_start,initial_state=state(status))
        self.addCleanup(d.reject)
        return d

    def test_denial_blocks_start_and_offers_repair(self):
        d=self.dialog(for_start=True)
        self.assertFalse(d.proceed.isEnabled())
        self.assertTrue(d.reset.isEnabled())
        self.assertIn('engelleyebilir',d.title.text())

    def test_allowed_and_unset_do_not_offer_reset(self):
        for status in ('allowed','unset'):
            d=self.dialog(status,True)
            self.assertFalse(d.reset.isEnabled())
            self.assertTrue(d.proceed.isEnabled())

    def test_reset_requires_explicit_yes(self):
        d=self.dialog()
        with patch.object(gui.QMessageBox,'question',return_value=gui.QMessageBox.StandardButton.No),patch.object(d,'_run') as run:
            d.confirm_reset()
        run.assert_not_called()
        with patch.object(gui.QMessageBox,'question',return_value=gui.QMessageBox.StandardButton.Yes),patch.object(d,'_run') as run:
            d.confirm_reset()
        run.assert_called_once_with('reset')

    def test_reset_command_has_consent_and_no_root(self):
        d=self.dialog()
        with patch.object(d.process,'start') as start:
            d._run('reset')
        program,args=start.call_args.args
        self.assertEqual(program,'/usr/bin/python3')
        self.assertEqual(args[-2:],['--reset-blocking','--consent'])
        self.assertNotIn('pkexec',str(start.call_args))
        self.assertNotIn('pkill',str(start.call_args))
        d.timeout.stop()

    def test_no_auto_continue_until_old_firefox_has_closed(self):
        d=self.dialog(for_start=True)
        result={'status':'unset','changed':True,'previous_firefox_pids':[42],'firefox_pids':[42]}
        d._buffer.extend(json.dumps(result).encode())
        d._finished(0,gui.QProcess.ExitStatus.NormalExit)
        self.assertFalse(d.proceed.isEnabled())
        self.assertIn('yeniden aç',d.title.text())
        self.assertEqual(self.parent._firefox_restart_pids,{42})
        d.reject()
        # Closing and reopening the dialog must not forget the cached-browser warning.
        next_dialog=gui.BrowserPermissionDialog(self.parent, for_start=True,
            initial_state={'status':'unset','firefox_pids':[42]})
        self.addCleanup(next_dialog.reject)
        self.assertFalse(next_dialog.proceed.isEnabled())
        next_dialog.show_state({'status':'unset','firefox_pids':[99]})
        self.assertTrue(next_dialog.proceed.isEnabled())

    def test_error_is_not_reported_as_ready(self):
        d=self.dialog(for_start=True)
        d.show_state({'status':'error','details':'D-Bus unavailable'})
        self.assertIn('denetlenemedi',d.title.text())
        self.assertFalse(d.reset.isEnabled())
        self.assertEqual(d.proceed.text(),'Yine de başlat')

    def test_read_failure_does_not_forget_pending_restart(self):
        d=self.dialog(for_start=True)
        d._blocked_pids={42}
        d.show_state({'status':'error','details':'offline'})
        self.assertFalse(d.proceed.isEnabled())
        self.assertEqual(d._blocked_pids,{42})

    def test_browser_preflight_cancel_does_not_start_camera(self):
        with patch.object(gui,'find_kinect_mic',return_value=(True,None)), \
             patch.object(gui,'kinect_audio_usb_ids',return_value=set()), \
             patch.object(gui.MainWindow,'refresh_log'):
            window=gui.MainWindow()
        self.addCleanup(window.close)
        window.mode=gui.MODE_PW
        with patch.object(window,'_firefox_permission',return_value=False),patch.object(window,'_run_scripts') as run:
            window.start_stream();window.restart_stream()
        run.assert_not_called()

    def test_permission_check_auto_continues_without_reset(self):
        d=self.dialog('unset',True)
        d._buffer.extend(json.dumps(state('unset')).encode())
        with patch.object(d,'accept') as accept,patch.object(d,'_run') as run:
            d._finished(0,gui.QProcess.ExitStatus.NormalExit)
        accept.assert_called_once()
        run.assert_not_called()

    def test_fallback_requires_separate_confirmation(self):
        d=self.dialog('allowed')
        self.assertTrue(d.restart_browser.isEnabled())
        with patch.object(gui.QMessageBox,'question',return_value=gui.QMessageBox.StandardButton.No),patch.object(d,'_run') as run:
            d.confirm_restart()
        run.assert_not_called()
        with patch.object(gui.QMessageBox,'question',return_value=gui.QMessageBox.StandardButton.Yes),patch.object(d,'_run') as run:
            d.confirm_restart()
        run.assert_called_once_with('restart')

    def test_fallback_invocation_is_explicit_and_never_auto_continues(self):
        d=self.dialog('unset',True)
        with patch.object(d.process,'start') as start:
            d._run('restart')
        self.assertEqual(start.call_args.args[1][-2:],['--restart-firefox','--consent'])
        d._buffer.extend(json.dumps(dict(state('unset'),restarted=True)).encode())
        with patch.object(d,'accept') as accept:
            d._finished(0,gui.QProcess.ExitStatus.NormalExit)
        accept.assert_not_called()
        self.assertIn('yeniden açıldı',d.title.text())
        self.assertTrue(d.proceed.isEnabled())

    def test_stream_failure_is_not_reported_as_a_firefox_failure(self):
        d=self.dialog('unset',True)
        d.show_state({'status':'error','stage':'stream','details':'source missing'})
        self.assertIn('Kinect tarayıcı akışı',d.title.text())
        self.assertIn('Firefox’a dokunulmadı',d.message.text())


if __name__=='__main__':unittest.main()
