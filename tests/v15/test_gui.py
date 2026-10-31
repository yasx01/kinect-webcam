"""UI regression tests: no root, camera stream, mute or system changes."""
import importlib.util
import json
import os
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('gui_v15', ROOT/'v15/kinect-facecam-gui-v15.py')
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)
app = gui.QApplication([])


def state(ready=False):
    return {'ready':ready,'can_install':True,
            'checks':[{'id':ident,'status':'ready' if ready else 'action','detail':'Hazır.' if ready else 'Hazırlanacak.'}
                      for ident,_ in gui.SetupDialog.CHECKS],
            'issues':[] if ready else ['/etc/private-technical-path']}


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.fixture=tempfile.TemporaryDirectory(prefix='setup-ui-fixture-')
        self.addCleanup(self.fixture.cleanup)
        folder=Path(self.fixture.name)/'payload';folder.mkdir()
        (folder/'UACFirmware').write_bytes(b'synthetic UI fixture, no Microsoft data')
        real_helper=gui.helper_path
        helper_patch=patch.object(gui,'helper_path',side_effect=lambda name:str(folder) if name=='payload' else real_helper(name))
        helper_patch.start();self.addCleanup(helper_patch.stop)
        for mock in (patch.object(gui,'find_kinect_mic',return_value=(True,None)),
                     patch.object(gui,'kinect_audio_usb_ids',return_value={'02ad'}),
                     patch.object(gui.MainWindow,'refresh_log'),
                     patch.object(gui,'save_settings')):
            mock.start();self.addCleanup(mock.stop)
        self.window=gui.MainWindow()
        self.addCleanup(self.window.close)

    def dialog(self, ready=False):
        dialog=gui.SetupDialog(self.window,state(ready))
        self.addCleanup(dialog.reject)
        return dialog

    def test_preview_and_media_test_exist_in_either_mode(self):
        for mode in (gui.MODE_OBS,gui.MODE_PW):
            self.window.set_mode(mode)
            self.assertTrue(hasattr(self.window,'preview_label'))
            self.assertTrue(self.window.preview_btn.isEnabled())
            self.assertIn('Mikrofon Testi',self.window.preview_btn.text())
            self.assertTrue(callable(self.window.capture_preview))
        self.assertIn('İlk Kurulum',self.window.mic_warning.text())

    def test_technical_details_are_opt_in(self):
        d=self.dialog()
        self.assertEqual(len(d.rows),4)
        self.assertTrue(d.output.isHidden())
        self.assertIn('/etc/private',d.output.toPlainText())
        self.assertNotIn('/etc/',d.summary_text.text())
        d.details_toggle.setChecked(True)
        self.assertFalse(d.output.isHidden())
        d.details_toggle.setChecked(False)
        self.assertTrue(d.output.isHidden())

    def test_ready_state_does_not_offer_reinstall(self):
        d=self.dialog(True)
        self.assertFalse(d.install.isEnabled())
        with patch.object(d.process,'start') as start:
            d.start_install()
            start.assert_not_called()
        self.assertIn('tamam',d.summary_title.text())

    def test_restart_only_does_not_repeat_install(self):
        value=state(True)
        value['ready']=False
        value['checks'][2].update(status='restart',detail='Yeniden başlat.')
        d=gui.SetupDialog(self.window,value)
        self.addCleanup(d.reject)
        self.assertFalse(d.install.isEnabled())
        self.assertIn('yeniden başlat',d.summary_title.text())

    def test_setup_stages_files_and_handles_cancel(self):
        d=self.dialog()
        with patch.object(d.process,'start') as start:
            d.start_install()
            program,args=start.call_args.args
            self.assertEqual(program,'/usr/bin/pkexec')
            self.assertEqual(args[-1],'--apply')
            staged=Path(args[-2])
            self.assertTrue(staged.is_file())
            self.assertTrue((staged.parent/'payload/UACFirmware').is_file())
            self.assertEqual(staged.parent.stat().st_mode & 0o777,0o700)
            self.assertFalse(d.close_button.isEnabled())
            self.assertFalse(d.refresh_button.isEnabled())
        d.completed(126,gui.QProcess.ExitStatus.NormalExit)
        self.assertIn('iptal',d.summary_title.text())
        self.assertFalse(staged.exists())
        self.assertTrue(d.close_button.isEnabled())

    def test_phase_event_can_be_split_between_reads(self):
        d=self.dialog()
        d.consume_output('KINECT_SETUP_E')
        self.assertNotIn('2 / 4',d.stage_label.text())
        d.consume_output('VENT {"phase":"files"}\nPaket çıktısı\n')
        self.assertIn('2 / 4',d.stage_label.text())
        self.assertEqual(d.progress.value(),1)
        self.assertNotIn('KINECT_SETUP_EVENT',d.output.toPlainText())
        self.assertIn('Paket çıktısı',d.output.toPlainText())
        self.assertTrue(d.output.isHidden())

    def test_partial_utf8_is_decoded_without_corruption(self):
        d=self.dialog()
        data='Hazırlanıyor'.encode()
        split=data.index(b'\xc4')+1
        d.consume_output(d._decoder.decode(data[:split]))
        d.consume_output(d._decoder.decode(data[split:]),final=True)
        self.assertIn('Hazırlanıyor',d.output.toPlainText())

    def test_failed_start_is_not_success(self):
        d=self.dialog()
        with patch.object(d.process,'start'):
            d.start_install()
        d.process_error(gui.QProcess.ProcessError.FailedToStart)
        self.assertIn('başlatılamadı',d.summary_title.text())
        self.assertIsNone(d._stage)
        self.assertTrue(d.install.isEnabled())

    def test_nonzero_and_crash_do_not_show_success(self):
        for code,status in ((1,gui.QProcess.ExitStatus.NormalExit),(0,gui.QProcess.ExitStatus.CrashExit)):
            d=self.dialog()
            d.completed(code,status)
            self.assertIn('tamamlanamadı',d.summary_title.text())
            self.assertTrue(d.install.isEnabled())

    def test_success_has_reconnect_instruction(self):
        d=self.dialog()
        d.completed(0,gui.QProcess.ExitStatus.NormalExit)
        self.assertIn('tamamlandı',d.summary_title.text())
        self.assertIn('çıkarıp',d.summary_text.text())
        self.assertFalse(d.install.isEnabled())
        self.assertEqual(d.progress.value(),4)

    def test_bad_check_output_disables_install(self):
        d=self.dialog()
        d._check_buffer.extend(b'not json')
        d._check_completed(1,gui.QProcess.ExitStatus.NormalExit)
        self.assertIn('tamamlanamadı',d.summary_title.text())
        self.assertFalse(d.install.isEnabled())
        self.assertTrue(d.refresh_button.isEnabled())

    def test_missing_setup_can_be_retried(self):
        d=self.dialog()
        d._check_buffer.extend(json.dumps(state()).encode())
        d._check_completed(1,gui.QProcess.ExitStatus.NormalExit)
        self.assertTrue(d.install.isEnabled())


if __name__=='__main__':
    unittest.main()
