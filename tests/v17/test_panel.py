"""Main preview and Chromium route tests. No real capture or browser mutation."""
import ast
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gui_panel',ROOT/'v17/kinect-facecam-gui-v17.py')
gui=importlib.util.module_from_spec(spec);spec.loader.exec_module(gui)
app=gui.QApplication([])
real_load_settings=gui.load_settings
class Frame:
    shape=(8,8,3)
    def tobytes(self):return bytes([32,128,224])*64
class PanelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for mocked in [patch.dict(os.environ,XDG_RUNTIME_DIR=self.tmp.name),
                       patch.object(gui,'load_settings',return_value={'mode':gui.MODE_OBS}),
                       patch.object(gui,'save_settings'),
                       patch.object(gui,'find_kinect_mic',return_value=(True,None)),
                       patch.object(gui,'kinect_audio_usb_ids',return_value=set()),
                       patch.object(gui.MainWindow,'refresh_log'),
                       patch.object(gui,'is_running',side_effect=lambda path: Path(path).exists() and Path(path).parent==Path(self.tmp.name))]:
            mocked.start();self.addCleanup(mocked.stop)
        self.pid=Path(self.tmp.name)/'bridge.pid';self.pid.write_text(str(os.getpid()))
        config=patch.dict(gui.MODE_CONFIG[gui.MODE_OBS],pidfile=str(self.pid))
        config.start();self.addCleanup(config.stop)
        self.window=gui.MainWindow();self.addCleanup(self.window.close)
        self.writer=gui.media.SnapshotWriter('obs');self.addCleanup(self.writer.close)
    def test_reference_layout_preserves_camera_and_microphone_tests(self):
        self.assertTrue(self.window.dark_mode)
        self.assertEqual(gui.WINDOW_SIZE,(760,720))
        self.assertEqual(self.window.frame_btn.text(),'Kare Al / Test Et')
        self.assertEqual(self.window.preview_btn.parent(),self.window.mic_btn.parent())
        self.assertFalse(self.window.log_text.isHidden())
        self.assertTrue(self.window.details_toggle.isChecked())
        self.assertIsNot(self.window.frame_btn.parent(),self.window.preview_card)

    def test_live_snapshot_freeze_and_resume(self):
        self.assertTrue(self.writer.publish(Frame()))
        self.window.refresh_preview_panel()
        self.assertIsNotNone(self.window._panel_pixmap)
        self.assertTrue(self.window.capture_frame())
        self.assertTrue(self.window._preview_frozen)
        self.assertIn('Test karesi',self.window.preview_status.text())
        self.writer.close();self.window.refresh_preview_panel()
        self.assertIsNotNone(self.window._panel_pixmap)
        self.window.resume_preview()
        self.assertIsNone(self.window._panel_pixmap)
    def test_test_button_rejects_stale_frozen_image(self):
        self.writer.publish(Frame());self.assertTrue(self.window.capture_frame())
        self.writer.close()
        self.assertFalse(self.window.capture_frame())
        self.assertIsNone(self.window._panel_pixmap)
        self.assertFalse(self.window._preview_frozen)
    def test_missing_pid_never_displays_stale_frame(self):
        self.writer.publish(Frame());self.pid.unlink()
        self.assertFalse(self.window.capture_frame())
        self.assertIsNone(self.window._panel_pixmap)
    def test_small_window_keeps_preview_controls_separate(self):
        self.window.resize(720,640);self.window.show();app.processEvents()
        self.assertLess(self.window.live_btn.geometry().bottom(),self.window.preview_label.geometry().top())
        self.assertLess(self.window.preview_label.geometry().bottom(),self.window.preview_card.height())
    def test_switching_mode_clears_test_image(self):
        self.writer.publish(Frame());self.assertTrue(self.window.capture_frame())
        with patch.object(gui,'is_running',return_value=False):self.window.set_mode(gui.MODE_PW)
        self.assertFalse(self.window._preview_frozen)
        self.assertIsNone(self.window._panel_pixmap)
    def test_chromium_start_never_changes_firefox_permissions(self):
        with patch.object(gui,'is_running',return_value=False),patch.object(self.window,'_firefox_permission') as firefox,patch.object(self.window,'_run_scripts') as run:
            self.window.start_stream()
        firefox.assert_not_called();run.assert_called_once()
        self.assertEqual(run.call_args.args[0],[gui.MODE_CONFIG[gui.MODE_OBS]['start']])
        self.assertIn('Chromium',self.window.mode_obs_btn.text())
        self.assertIn('Kinect360 Facecam',self.window.browser_hint.text())
    def test_busy_operation_blocks_mode_changes_and_closing(self):
        self.window._busy=True
        self.addCleanup(setattr,self.window,'_busy',False)
        self.window.set_mode(gui.MODE_PW)
        self.assertEqual(self.window.mode,gui.MODE_OBS)
        from PyQt6.QtGui import QCloseEvent
        event=QCloseEvent();self.window.closeEvent(event)
        self.assertFalse(event.isAccepted())
        with patch.object(self.window,'_run_scripts') as run:
            self.window.start_stream();self.window.stop_stream();self.window.restart_stream()
        run.assert_not_called()
    def test_settings_with_wrong_json_type_fall_back_to_defaults(self):
        path=Path(self.tmp.name)/'settings.json';path.write_text('[]')
        with patch.object(gui,'CONFIG_FILE',str(path)):
            self.assertEqual(real_load_settings(),{})
    def test_invalid_saved_mode_does_not_crash(self):
        with patch.object(gui,'load_settings',return_value={'mode':[]}):
            window=gui.MainWindow();self.addCleanup(window.close)
            self.assertEqual(window.mode,gui.MODE_OBS)
    def test_log_starts_visible_and_can_be_collapsed(self):
        self.assertTrue(self.window.details_toggle.isChecked())
        self.assertFalse(self.window.log_text.isHidden())
        self.window.details_toggle.setChecked(False)
        self.assertTrue(self.window.log_text.isHidden())
    def test_chromium_uses_yuyv_v4l2_and_exclusive_capture_caps(self):
        text=(ROOT/'v17/kinect-facecam-bridge-v17.py').read_text()
        self.assertIn('"-pix_fmt", "yuyv422"',text)
        self.assertIn('"-f", "v4l2", DEVICE',text)
        self.assertIn('exclusive_caps=1,1',(ROOT/'v17/kinect-facecam-setup-v17.py').read_text())
        self.assertEqual(gui.MODE_CONFIG[gui.MODE_OBS]['device'],'/dev/video20')
if __name__=='__main__':unittest.main()
