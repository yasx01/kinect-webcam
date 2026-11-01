"""Test the diagnostic, with fake streams and no real camera access."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gui_v16',ROOT/'v16/kinect-facecam-gui-v16.py')
gui=importlib.util.module_from_spec(spec);spec.loader.exec_module(gui)
app=gui.QApplication([])


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='kinect-test-fixture-')
        self.addCleanup(self.tmp.cleanup)
        self.log=Path(self.tmp.name)/'camera.log'
        self.log.write_text('[calisiyor] 150 kare aktarildi.\n')
        self.parent=gui.QWidget()
        self.addCleanup(self.parent.close)

    def dialog(self, mode):
        cfg=dict(gui.MODE_CONFIG[mode],logfile=str(self.log))
        d=gui.CameraTestDialog(self.parent,cfg)
        self.addCleanup(d.reject)
        return d

    def test_stopped_stream_is_not_success(self):
        d=self.dialog(gui.MODE_OBS)
        with patch.object(gui,'is_running',return_value=False),patch.object(d.capture,'start') as start:
            d.start_test()
        start.assert_not_called()
        self.assertFalse(d.succeeded)
        self.assertIn('başlat',d.title.text())

    def test_obs_reads_existing_v4l2_output(self):
        d=self.dialog(gui.MODE_OBS)
        with patch.object(gui,'is_running',return_value=True),patch.object(d.capture,'start') as start:
            d.start_test()
        command,args=start.call_args.args
        self.assertEqual(command,'ffmpeg')
        self.assertIn('/dev/video20',args)
        self.assertEqual(args[-1],d.image_path)
        self.assertNotIn('freenect',str(start.call_args))
        image=gui.QPixmap(16,12);image.fill(gui.Qt.GlobalColor.darkBlue)
        self.assertTrue(image.save(d.image_path))
        d._capture_finished(0,gui.QProcess.ExitStatus.NormalExit)
        self.assertTrue(d.succeeded)
        self.assertFalse(d.frame.isHidden())

    def test_exit_zero_without_image_is_failure(self):
        d=self.dialog(gui.MODE_OBS)
        d._capture_finished(0,gui.QProcess.ExitStatus.NormalExit)
        self.assertFalse(d.succeeded)

    def test_timeout_is_failure_even_if_stale_image_exists(self):
        d=self.dialog(gui.MODE_OBS)
        image=gui.QPixmap(16,12);image.fill(gui.Qt.GlobalColor.black);image.save(d.image_path)
        d._capture_timeout()
        d._capture_finished(0,gui.QProcess.ExitStatus.NormalExit)
        self.assertFalse(d.succeeded)

    def test_old_browser_heartbeat_is_not_success(self):
        d=self.dialog(gui.MODE_PW)
        with patch.object(gui,'is_running',return_value=True):
            d.start_test();d._poll_frames()
        self.assertFalse(d.succeeded)
        self.assertTrue(d.poll.isActive())

    def test_new_browser_heartbeat_is_success(self):
        d=self.dialog(gui.MODE_PW)
        with patch.object(gui,'is_running',return_value=True):
            d.start_test()
            self.log.write_text('[calisiyor] 300 kare aktarildi.\n')
            d._poll_frames()
        self.assertTrue(d.succeeded)
        self.assertIn('ayrıca kontrol et',d.description.text())

    def test_browser_timeout_is_not_success(self):
        d=self.dialog(gui.MODE_PW)
        with patch.object(gui,'is_running',return_value=True):
            d.start_test()
            with patch.object(gui.time,'monotonic',return_value=d._deadline+1):
                d._poll_frames()
        self.assertFalse(d.succeeded)
        self.assertFalse(d.poll.isActive())

    def test_closing_cleans_only_test_artifacts(self):
        d=self.dialog(gui.MODE_OBS)
        directory=Path(d.image_path).parent
        d.reject()
        self.assertFalse(directory.exists())
        with patch.object(d.capture,'start') as start:
            d.start_test()
        start.assert_not_called()


if __name__=='__main__': unittest.main()
