"""Live-preview/recording tests with synthetic frames and PCM, never real devices."""
import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import time
import unittest
import wave
from unittest.mock import patch
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gui',ROOT/'v15/kinect-facecam-gui-v15.py')
gui=importlib.util.module_from_spec(spec);spec.loader.exec_module(gui)
media=gui.media
app=gui.QApplication([])


class Frame:
    shape=(8,8,3)
    def tobytes(self):return bytes([32,128,224])*64


class MediaUtilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='kinect-media-test-')
        self.addCleanup(self.tmp.cleanup)
        self.env=patch.dict(os.environ,{'XDG_RUNTIME_DIR':self.tmp.name})
        self.env.start();self.addCleanup(self.env.stop)

    def test_snapshot_is_fresh_private_and_owned_by_expected_process(self):
        writer=media.SnapshotWriter('pw')
        self.addCleanup(writer.close)
        self.assertTrue(writer.publish(Frame()))
        result=media.read_snapshot('pw',os.getpid())
        self.assertIsNotNone(result)
        self.assertTrue(result[0].startswith(b'\xff\xd8'))
        self.assertEqual(writer.image_path.stat().st_mode & 0o777,0o600)
        self.assertEqual(media.media_dir().stat().st_mode & 0o777,0o700)
        self.assertIsNone(media.read_snapshot('pw',os.getpid()+999999))
        self.assertIsNone(media.read_snapshot('pw',os.getpid(),max_age=-1))

    def test_preview_rate_is_limited_and_close_removes_its_image(self):
        writer=media.SnapshotWriter('obs')
        self.assertTrue(writer.publish(Frame()))
        self.assertFalse(writer.publish(Frame()))
        path=writer.image_path
        writer.close()
        self.assertFalse(path.exists())

    def test_audio_level_silence_and_signal(self):
        self.assertEqual(media.audio_level(bytes(128))[0],0)
        self.assertGreater(media.audio_level(struct.pack('<h',12000)*128)[0],0)
        self.assertLessEqual(media.audio_level(struct.pack('<h',32767)*128)[0],100)
        self.assertEqual(media.audio_level(b'\x01')[0],0)

    def test_clip_has_exact_duration_and_rejects_partial_data(self):
        path=Path(self.tmp.name)/'test.wav'
        with self.assertRaises(ValueError):media.write_clip(path,b'\x00\x00')
        media.write_clip(path,bytes(media.RECORD_BYTES))
        with wave.open(str(path),'rb') as stream:
            self.assertEqual(stream.getnframes(),media.RATE*5)
            self.assertEqual(stream.getnchannels(),1)
            self.assertEqual(stream.getsampwidth(),2)


class MediaDialogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='kinect-dialog-test-')
        self.addCleanup(self.tmp.cleanup)
        self.env=patch.dict(os.environ,{'XDG_RUNTIME_DIR':self.tmp.name})
        self.env.start();self.addCleanup(self.env.stop)
        for mocked in (patch.object(gui,'find_kinect_mic',return_value=(True,'kinect-test-source')),
                       patch.object(gui,'mic_is_muted',return_value=False),patch.object(gui.MainWindow,'refresh_log')):
            mocked.start();self.addCleanup(mocked.stop)
        self.window=gui.MainWindow();self.window.mode=gui.MODE_PW
        self.addCleanup(self.window.close)
        self.dialog=gui.MediaTestDialog(self.window)
        self.addCleanup(self.dialog.reject)

    def test_opening_dialog_does_not_open_microphone(self):
        self.assertEqual(self.dialog.mic_process.state(),gui.QProcess.ProcessState.NotRunning)
        self.assertFalse(Path(self.dialog.clip_path).exists())

    def test_missing_kinect_never_falls_back_to_default_microphone(self):
        with patch.object(gui,'find_kinect_mic',return_value=(True,None)),patch.object(self.dialog.mic_process,'start') as start:
            self.assertFalse(self.dialog.start_microphone())
        start.assert_not_called()
        self.assertIn('Başka bir mikrofon kullanılmadı',self.dialog.audio_status.text())

    def test_muted_microphone_is_not_unmuted_by_test(self):
        with patch.object(gui,'mic_is_muted',return_value=True),patch.object(self.dialog.mic_process,'start') as start:
            self.assertFalse(self.dialog.start_microphone())
        start.assert_not_called()

    def test_finished_microphone_never_claims_to_be_listening(self):
        self.dialog.microphone_finished(0,gui.QProcess.ExitStatus.NormalExit)
        self.assertIn('durdu',self.dialog.audio_status.text())
    def test_meter_uses_exact_kinect_source(self):
        with patch.object(self.dialog.mic_process,'start') as start:
            self.assertTrue(self.dialog.start_microphone())
        args=start.call_args.args[1]
        self.assertEqual(args[args.index('-i')+1],'kinect-test-source')
        self.assertNotIn('@DEFAULT_SOURCE@',args)

    def test_recording_is_bounded_and_local(self):
        d=self.dialog
        with patch.object(d,'start_microphone',return_value=True):d.record_clip()
        pcm=struct.pack('<h',4000)*(media.RATE*5+100)
        with patch.object(d.mic_process,'readAllStandardOutput',return_value=pcm):d.read_audio()
        self.assertFalse(d._recording)
        self.assertTrue(d.play_button.isEnabled())
        with wave.open(d.clip_path,'rb') as stream:self.assertEqual(stream.getnframes(),media.RATE*5)

    def test_partial_recording_is_discarded_on_stop(self):
        d=self.dialog
        with patch.object(d,'start_microphone',return_value=True):d.record_clip()
        with patch.object(d.mic_process,'readAllStandardOutput',return_value=bytes(200)):d.read_audio()
        d.stop_audio()
        self.assertFalse(Path(d.clip_path).exists())
        self.assertFalse(d._recording)
        self.assertEqual(len(d._record_buffer),0)

    def test_playback_uses_existing_recording_and_stops_capture(self):
        d=self.dialog;media.write_clip(d.clip_path,bytes(media.RECORD_BYTES))
        with patch.object(d,'stop_audio') as stop,patch.object(d.player,'start') as start:d.play_clip()
        stop.assert_called_once()
        self.assertEqual(start.call_args.args[0],'pw-play')
        self.assertEqual(start.call_args.args[1][-1],d.clip_path)

    def test_closing_dialog_deletes_recording(self):
        d=self.dialog;media.write_clip(d.clip_path,bytes(media.RECORD_BYTES))
        path=Path(d.clip_path)
        d.reject()
        self.assertFalse(path.exists())
        self.assertFalse(d.preview_timer.isActive())

    def test_current_frame_can_be_shown_in_browser_mode(self):
        d=self.dialog
        pidfile=Path(self.tmp.name)/'bridge.pid';pidfile.write_text(str(os.getpid()))
        writer=media.SnapshotWriter('pw');self.addCleanup(writer.close)
        self.assertTrue(writer.publish(Frame()))
        with patch.dict(gui.MODE_CONFIG[gui.MODE_PW],{'pidfile':str(pidfile)}),patch.object(gui,'is_running',return_value=True):d.refresh_camera()
        self.assertIsNotNone(d._pixmap)
        self.assertIn('Canlı',d.camera_status.text())
        d.resize(760,560);d.show();app.processEvents()
        self.assertLess(d.image.geometry().bottom(),d.camera_status.geometry().top())
        self.assertLess(d.camera_status.geometry().bottom(),d.camera_start.geometry().top())
        writer.close()
        with patch.dict(gui.MODE_CONFIG[gui.MODE_PW],{'pidfile':str(pidfile)}),patch.object(gui,'is_running',return_value=True):d.refresh_camera()
        self.assertIsNone(d._pixmap)


if __name__=='__main__':unittest.main()
