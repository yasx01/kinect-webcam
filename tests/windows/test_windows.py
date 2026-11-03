"""Windows logic tests use synthetic frames and audio; no real drivers are changed."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock,patch
os.environ['QT_QPA_PLATFORM']='offscreen'
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'windows'))
import common,camera,firmware
import app as gui
import audio
from PyQt6.QtCore import QProcess
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimedia import QAudioFormat
from PyQt6.QtWidgets import QApplication
qt=QApplication.instance() or QApplication([])


class CoreTests(unittest.TestCase):
    def test_device_names_never_select_default_microphone(self):
        self.assertTrue(common.is_kinect('Microphone Array (Kinect USB Audio)'))
        self.assertTrue(common.is_kinect('Xbox NUI Audio'))
        self.assertFalse(common.is_kinect('Laptop microphone'))
        self.assertFalse(common.is_kinect(None))

    def test_endpoint_query_is_capture_active_and_unambiguous(self):
        endpoint=Mock();device=types.SimpleNamespace(FriendlyName='Kinect Audio',EndpointVolume=endpoint)
        utilities=Mock();utilities.GetAllDevices.return_value=[device]
        package=types.ModuleType('pycaw');module=types.ModuleType('pycaw.pycaw');module.AudioUtilities=utilities
        with patch.dict(sys.modules,{'pycaw':package,'pycaw.pycaw':module}):
            self.assertIs(common.microphone_endpoint(),endpoint)
            utilities.GetAllDevices.assert_called_with(data_flow=1,device_state=1)
            utilities.GetAllDevices.return_value=[device,device]
            with self.assertRaises(RuntimeError):common.microphone_endpoint()

    def test_wrong_firmware_never_launches_loader(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(firmware.subprocess,'run') as run:
            p=Path(folder)/'not-firmware';p.write_bytes(b'not Microsoft firmware')
            with self.assertRaises(ValueError):firmware.upload(p)
            run.assert_not_called()

    def test_firmware_nonzero_exit_is_failure(self):
        with patch.object(firmware,'validate',return_value=Path('verified')),patch.object(firmware.subprocess,'run',return_value=types.SimpleNamespace(returncode=1,stdout='USB error',stderr='')):
            with self.assertRaises(RuntimeError):firmware.upload('unused')

    def test_worker_writes_synthetic_preview_and_stops(self):
        from selftest import TestSource,TestSink
        with tempfile.TemporaryDirectory() as folder:
            sink=TestSink()
            self.assertEqual(camera.run(folder,True,lambda:TestSource(folder),lambda:sink),0)
            self.assertEqual(sink.frames,3)
            state=json.loads((Path(folder)/'state.json').read_text())
            self.assertEqual(state['state'],'running')
            self.assertTrue((Path(folder)/'frame.jpg').read_bytes().startswith(b'\xff\xd8'))

    def test_missing_obs_is_not_a_running_camera(self):
        source=Mock()
        with tempfile.TemporaryDirectory() as folder:
            def failure():raise RuntimeError('OBS not installed')
            self.assertEqual(camera.run(folder,True,lambda:source,failure),1)
            state=json.loads((Path(folder)/'state.json').read_text())
            self.assertEqual(state['state'],'error');source.close.assert_called_once()
            source.frame.assert_not_called()

    def test_preview_only_does_not_open_virtual_camera(self):
        from selftest import TestSource
        with tempfile.TemporaryDirectory() as folder:
            sink=Mock()
            self.assertEqual(camera.run(folder,False,lambda:TestSource(folder),sink),0)
            sink.assert_not_called()

    def test_four_channel_float_audio_becomes_mono_pcm16(self):
        import numpy as np
        fmt=QAudioFormat();fmt.setChannelCount(4);fmt.setSampleRate(48000);fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
        pcm=audio.mono_pcm16(np.full((10,4),0.5,dtype='<f4').tobytes(),fmt)
        self.assertEqual(len(pcm),20);self.assertEqual(struct.unpack('<h',pcm[:2])[0],16384)


class GuiTests(unittest.TestCase):
    def setUp(self):
        mock=patch.object(gui,'microphone_endpoint',side_effect=RuntimeError('No Kinect'));mock.start();self.addCleanup(mock.stop)
        self.window=gui.MainWindow();self.addCleanup(self.window.close)

    def test_launch_does_not_start_camera_or_microphone(self):
        self.assertEqual(self.window.worker.state(),QProcess.ProcessState.NotRunning)
        self.assertIsNone(self.window.mic_dialog)
        self.assertFalse(self.window.details.isHidden())

    def test_utf8_child_messages_ignore_windows_ansi_locale(self):
        message='Kinect kamerası açılamadı. USB/güç bağlantısını denetle. ŞİĞÜÖÇ ıüğöç'
        (self.window.folder/'state.json').write_bytes(json.dumps({'state':'error','message':message},ensure_ascii=False).encode('utf-8'))
        original=Path.read_text
        def windows_read(path,encoding=None,errors=None):
            return original(path,encoding=encoding or 'cp1252',errors=errors)
        with patch.object(Path,'read_text',windows_read):
            with patch.object(self.window.worker,'state',return_value=QProcess.ProcessState.Running),patch.object(self.window,'stop'):
                self.window.refresh()
            self.assertEqual(self.window.status.text(),message)
            self.window.finished(1,QProcess.ExitStatus.NormalExit)
            self.assertEqual(self.window.status.text(),message)
            dialog=gui.Setup(self.window);self.addCleanup(dialog.reject)
            dialog.result_temp=tempfile.TemporaryDirectory();self.addCleanup(dialog.result_temp.cleanup)
            (Path(dialog.result_temp.name)/'result.json').write_bytes(json.dumps({'message':message},ensure_ascii=False).encode('utf-8'))
            dialog.completed(0,QProcess.ExitStatus.NormalExit)
            self.assertEqual(dialog.status.text(),message)

    def test_reference_theme_toggle_and_restart(self):
        self.assertTrue(self.window.dark_mode)
        self.assertIn('Kare Al / Test Et',self.window.test_button.text())
        self.window.toggle_theme();self.assertFalse(self.window.dark_mode)
        self.assertEqual(self.window.theme_button.text(),'Koyu Tema')
        with patch.object(self.window,'stop') as stop,patch.object(self.window,'start') as start:
            self.window.restart()
        stop.assert_called_once();start.assert_called_once()

    def test_stopped_stream_cannot_freeze_stale_image(self):
        self.window.pixmap=QPixmap(12,12)
        self.window.freeze_frame()
        self.assertFalse(self.window.frozen);self.assertIsNone(self.window.pixmap)

    def test_stale_live_frame_is_cleared(self):
        self.window.pixmap=QPixmap(12,12)
        (self.window.folder/'state.json').write_text(json.dumps({'state':'running','captured':0,'sequence':1}))
        self.window.last_frame=gui.time.monotonic()
        with patch.object(self.window.worker,'state',return_value=QProcess.ProcessState.Running):self.window.refresh()
        self.assertIsNone(self.window.pixmap)

    def test_freeze_and_live_resume(self):
        import numpy as np
        camera.write_frame(self.window.folder,np.zeros((480,640,3),dtype=np.uint8),1)
        with patch.object(self.window.worker,'state',return_value=QProcess.ProcessState.Running):
            self.window.freeze_frame();self.assertTrue(self.window.frozen)
            self.assertIn('Test karesi',self.window.frame_status.text())
        self.window.resume();self.assertFalse(self.window.frozen);self.assertIsNone(self.window.pixmap)

    def test_camera_failure_never_shows_running(self):
        (self.window.folder/'state.json').write_text('{"state":"error","message":"USB missing"}')
        with patch.object(self.window.worker,'state',return_value=QProcess.ProcessState.Running),patch.object(self.window,'stop') as stop:
            self.window.refresh()
        stop.assert_called_once();self.assertEqual(self.window.status.text(),'USB missing')

    def test_microphone_test_never_uses_another_device(self):
        dialog=audio.AudioTest(self.window);self.addCleanup(dialog.reject)
        self.assertIsNone(dialog.source)
        other=Mock();other.description.return_value='Laptop microphone'
        with patch.object(audio.QMediaDevices,'audioInputs',return_value=[other]),patch.object(audio,'QAudioSource') as start:
            dialog.start()
        start.assert_not_called();self.assertIn('Başka mikrofon kullanılmadı',dialog.status.text())

    def test_native_audio_recording_is_exactly_five_seconds(self):
        import wave
        import numpy as np
        dialog=audio.AudioTest(self.window);self.addCleanup(dialog.reject)
        fmt=QAudioFormat();fmt.setSampleRate(48000);fmt.setChannelCount(4);fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
        dialog.format=fmt;dialog.rate=48000;dialog.target=48000*2*5
        dialog.stream=Mock()
        dialog.stream.readAll.return_value=np.full((48000*6,4),0.5,dtype='<f4').tobytes()
        dialog.read()
        with wave.open(str(dialog.path),'rb') as recording:
            self.assertEqual(recording.getframerate(),48000)
            self.assertEqual(recording.getnframes(),48000*5)
            self.assertEqual(recording.getnchannels(),1)
        self.assertTrue(dialog.play.isEnabled());self.assertEqual(len(dialog.samples),0)

    def test_audio_dialog_close_deletes_recording(self):
        dialog=audio.AudioTest(self.window);path=dialog.path;path.write_bytes(b'synthetic')
        dialog.reject();self.assertFalse(path.exists())

    def test_close_cleans_camera_folder(self):
        folder=self.window.folder
        self.window.close();self.assertFalse(folder.exists())

if __name__=='__main__':unittest.main()
