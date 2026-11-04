"""Preview and frame tests cannot start, stop, restart or open a camera consumer."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gui_camera',ROOT/'v19/kinect-facecam-gui-v19.py')
gui=importlib.util.module_from_spec(spec);spec.loader.exec_module(gui)
app=gui.QApplication([])

class Frame:
    shape=(8,8,3)
    def tobytes(self):return bytes([32,128,224])*64

class CameraTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.pid=Path(self.tmp.name)/'bridge.pid';self.pid.write_text(str(os.getpid()))
        for mocked in (patch.dict(os.environ,XDG_RUNTIME_DIR=self.tmp.name),
                       patch.dict(gui.MODE_CONFIG[gui.MODE_OBS],pidfile=str(self.pid)),
                       patch.object(gui,'is_running',side_effect=lambda path:Path(path)==self.pid and self.pid.exists()),
                       patch.object(gui,'load_settings',return_value={'mode':gui.MODE_PW}),
                       patch.object(gui,'save_settings'),
                       patch.object(gui,'find_kinect_mic',return_value=(True,None)),
                       patch.object(gui,'kinect_audio_usb_ids',return_value=set()),
                       patch.object(gui.MainWindow,'refresh_log')):
            mocked.start();self.addCleanup(mocked.stop)
        self.writer=gui.media.SnapshotWriter('obs');self.addCleanup(self.writer.close)
        self.writer.publish(Frame())
        self.window=gui.MainWindow();self.addCleanup(self.window.close)

    def test_opening_attaches_to_running_route_without_starting_anything(self):
        self.assertEqual(self.window.mode,gui.MODE_OBS)
        self.assertIsNotNone(self.window._panel_pixmap)
        self.assertIn('OBS',self.window.preview_status.text())

    def test_selected_other_mode_still_previews_the_running_route(self):
        self.window.set_mode(gui.MODE_PW)
        self.assertTrue(self.window.capture_frame())
        self.assertEqual(self.window.preview_mode(),gui.MODE_OBS)
        self.assertIn('OBS',self.window.status_label.text())

    def test_all_preview_controls_and_close_leave_broadcast_untouched(self):
        with patch.object(self.window,'_run_scripts') as scripts,patch.object(gui.QProcess,'start') as start:
            self.window.capture_frame();self.window.resume_preview()
            self.window.preview_toggle.setChecked(False)
            self.assertFalse(self.window.panel_timer.isActive())
            self.assertIsNone(self.window._panel_pixmap)
            self.window.preview_toggle.setChecked(True)
            self.assertIsNotNone(self.window._panel_pixmap)
            self.window.capture_preview();dialog=self.window._media_dialog
            dialog.capture_camera();self.assertTrue(dialog._preview_frozen)
            self.assertIsNotNone(dialog._pixmap)
            dialog.resume_camera();self.assertFalse(dialog._preview_frozen)
            dialog.reject();self.window.close()
            self.assertIsNone(dialog._pixmap)
            self.assertIsNone(self.window._panel_pixmap)
            self.assertFalse(self.window.panel_timer.isActive())
        scripts.assert_not_called();start.assert_not_called()
        self.assertTrue(self.pid.exists())
        self.assertIsNotNone(gui.media.read_snapshot('obs',os.getpid()))

    def test_no_snapshot_never_restarts_a_legacy_broadcast(self):
        self.writer.close()
        with patch.object(self.window,'_run_scripts') as scripts,patch.object(gui.QProcess,'start') as start:
            self.assertFalse(self.window.capture_frame())
            self.window.capture_preview();dialog=self.window._media_dialog
            dialog.capture_camera()
            self.assertIsNone(dialog._pixmap)
            self.assertFalse(dialog._preview_frozen)
            dialog.reject()
        scripts.assert_not_called();start.assert_not_called()
        self.assertTrue(self.pid.exists())

    def test_test_with_no_broadcast_does_not_claim_or_open_a_camera(self):
        self.pid.unlink()
        with patch.object(self.window,'_run_scripts') as scripts,patch.object(gui.QProcess,'start') as start:
            self.assertFalse(self.window.capture_frame())
        scripts.assert_not_called();start.assert_not_called()
        self.assertIsNone(self.window._panel_pixmap)

    def test_cancel_route_switch_does_not_run_firefox_preflight_or_stop_stream(self):
        self.window.set_mode(gui.MODE_PW)
        with patch.object(gui.QMessageBox,'question',return_value=gui.QMessageBox.StandardButton.No),patch.object(self.window,'_firefox_permission') as permission,patch.object(self.window,'_run_scripts') as scripts:
            self.window.start_stream()
        permission.assert_not_called();scripts.assert_not_called()

    def test_starting_an_existing_route_does_not_run_firefox_preflight(self):
        with patch.object(gui.QMessageBox,'information'),patch.object(self.window,'_firefox_permission') as permission,patch.object(self.window,'_run_scripts') as scripts:
            self.window.start_stream()
        permission.assert_not_called();scripts.assert_not_called()

    def test_switch_checks_permissions_after_new_route_started(self):
        self.window.set_mode(gui.MODE_PW)
        with patch.object(gui.QMessageBox,'question',return_value=gui.QMessageBox.StandardButton.Yes),patch.object(self.window,'_firefox_permission') as permission,patch.object(self.window,'_run_scripts') as scripts:
            self.window.start_stream()
            scripts.assert_called_once()
            self.assertEqual(scripts.call_args.args[0],[gui.MODE_CONFIG[gui.MODE_OBS]['stop'],gui.MODE_CONFIG[gui.MODE_PW]['start']])
            permission.assert_not_called()
            self.window._after_action(self.window.start_btn,'Mod değiştirme',0,'')
            permission.assert_called_once_with()

if __name__=='__main__':unittest.main()
