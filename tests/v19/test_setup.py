"""No hardware, root, package manager or host system changes: mocked setup scenarios."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('setup_v19', ROOT/'v19/kinect-facecam-setup-v19.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def setUp(self):
        distro=patch.object(setup,'distribution',return_value='fedora');distro.start();self.addCleanup(distro.stop)
        self.tmp = tempfile.TemporaryDirectory(prefix='kinect-setup-test-')
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_ubuntu_queries_dpkg_and_uses_native_dependencies(self):
        def run(args,**kwargs):
            return subprocess.CompletedProcess(args,0,'ii ' if args[-1]!='python3-numpy' else '')
        with patch.object(setup,'distribution',return_value='ubuntu'),patch.object(setup,'run',side_effect=run):
            self.assertEqual(setup.missing_packages(),['python3-numpy'])
            self.assertIn('libfreenect0.5t64',setup.required_packages())

    def test_ubuntu_install_uses_apt_dkms_and_no_fedora_commands(self):
        stack, target, records = self.application()
        with stack,patch.object(setup,'distribution',return_value='ubuntu'):
            self.assertEqual(setup.apply(),0)
        commands=[args[0] for args in records]
        self.assertIn('apt-get',commands);self.assertIn('dkms',commands)
        self.assertFalse(set(commands)&{'rpm','dnf','akmods','restorecon'})

    def fixture_payload(self):
        folder=self.base/'payload';folder.mkdir()
        firmware=b'synthetic test firmware; not Microsoft data'
        loader=b'synthetic loader fixture'
        (folder/'UACFirmware').write_bytes(firmware)
        (folder/'kinect_upload_fw').write_bytes(loader)
        (folder/'manifest.json').write_text(json.dumps({
            'UACFirmware':hashlib.sha256(firmware).hexdigest(),
            'kinect_upload_fw':hashlib.sha256(loader).hexdigest()}))
        return hashlib.sha256(firmware).hexdigest()

    def test_payload_matches_installed_firmware_hash(self):
        digest=self.fixture_payload()
        with patch.object(setup,'HERE',self.base),patch.object(setup,'FW_SHA',digest):
            setup.validate_payload()

    def test_corrupted_firmware_is_rejected(self):
        (self.base/'payload').mkdir()
        (self.base/'payload/UACFirmware').write_bytes(b'corrupted')
        with patch.object(setup, 'HERE', self.base):
            with self.assertRaisesRegex(RuntimeError, 'SHA-256'):
                setup.validate_payload()

    def test_corrupted_loader_is_rejected(self):
        digest=self.fixture_payload()
        (self.base/'payload/kinect_upload_fw').write_bytes(b'corrupt')
        with patch.object(setup,'HERE',self.base),patch.object(setup,'FW_SHA',digest):
            with self.assertRaisesRegex(RuntimeError,'bütünlüğü'):
                setup.validate_payload()

    def test_no_root_is_rejected_before_plan(self):
        with patch.object(setup.os, 'geteuid', return_value=1000), patch.object(setup, 'plan') as plan:
            with self.assertRaisesRegex(RuntimeError, 'Yönetici'):
                setup.apply()
            plan.assert_not_called()

    def test_non_fedora_does_not_start_install(self):
        with patch.object(setup, 'supported', return_value=False), patch.object(setup, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'Fedora'):
                setup.plan()
            run.assert_not_called()

    def test_package_detection_reports_absent_tools(self):
        installed = '\n'.join(setup.PACKAGES[1:])
        def run(args, **kwargs):
            if args[0:3] == ['rpm', '-q', '--qf']:
                return subprocess.CompletedProcess(args, 1, installed)
            return subprocess.CompletedProcess(args, 0, '')
        with patch.object(setup, 'run', side_effect=run):
            self.assertEqual(setup.missing_packages(), ['python3'])

    def application(self, *, failure=None, ready=True, stream=False):
        target = self.base/'etc/rule'
        target.parent.mkdir()
        target.write_bytes(b'old')
        records = []
        def run(args, **kwargs):
            records.append(args)
            if args[0] == 'pgrep':
                return subprocess.CompletedProcess(args, 0 if stream else 1, '')
            if args[0] == failure:
                raise RuntimeError('simulated ' + failure + ' failure')
            return subprocess.CompletedProcess(args, 0, 'v4l2' if args[0]=='ffmpeg' else '')
        RealPath = Path
        def paths(value):
            if value == '/var/backups/kinect-facecam':
                return self.base/'backups'
            if value == '/etc/modprobe.d/kinect-v4l2loopback.conf':
                return self.base/'absent-legacy'
            return RealPath(value)
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(setup.os, 'geteuid', return_value=0))
        stack.enter_context(patch.object(setup, 'plan', return_value=['python3']))
        stack.enter_context(patch.object(setup, 'missing_packages', return_value=[]))
        stack.enter_context(patch.object(setup, 'destinations', return_value={target:b'new'}))
        stack.enter_context(patch.object(setup, 'check_state', return_value={'ready':ready,'issues':['reboot needed'] if not ready else []}))
        stack.enter_context(patch.object(setup, 'run', side_effect=run))
        stack.enter_context(patch.object(setup, 'Path', side_effect=paths))
        return stack, target, records

    def test_dnf_failure_does_not_write_system_files(self):
        stack, target, records = self.application(failure='dnf')
        with stack, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'dnf'):
                setup.apply()
        self.assertEqual(target.read_bytes(), b'old')

    def test_live_camera_prevents_changes(self):
        stack, target, records = self.application(stream=True)
        with stack:
            with self.assertRaisesRegex(RuntimeError, 'akışını durdur'):
                setup.apply()
        self.assertEqual(target.read_bytes(), b'old')
        self.assertFalse(any(cmd[0]=='dnf' for cmd in records))

    def test_changed_file_backup_and_idempotent_retry(self):
        stack, target, records = self.application()
        with stack, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.apply(),0)
            self.assertEqual(setup.apply(),0)
        self.assertEqual(target.read_bytes(), b'new')
        backups = list((self.base/'backups').rglob('rule'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_bytes(), b'old')
        self.assertFalse(any('kinect-webcam.service' in cmd for cmd in records))

    def test_akmods_failure_is_not_success(self):
        stack, target, records = self.application(failure='akmods')
        with stack, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'akmods'):
                setup.apply()
        self.assertFalse(any(cmd[0]=='udevadm' for cmd in records))

    def test_not_ready_returns_nonzero(self):
        stack, target, records = self.application(ready=False)
        with stack, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.apply(),3)


class OptionalFirmwareTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);payload=self.base/'payload';payload.mkdir()
        loader=b'open-source loader fixture';(payload/'kinect_upload_fw').write_bytes(loader)
        (payload/'manifest.json').write_text(json.dumps({'kinect_upload_fw':hashlib.sha256(loader).hexdigest()}))
        for item in [patch.object(setup,'HERE',self.base),patch.object(setup,'FIRMWARE_PATH',None),
                     patch.object(setup,'INSTALLED_FIRMWARE',self.base/'installed/UACFirmware')]:
            item.start();self.addCleanup(item.stop)
    def test_camera_payload_works_without_firmware(self):
        setup.validate_payload()
        files=setup.destinations()
        self.assertNotIn(setup.INSTALLED_FIRMWARE,files)
        rule=files[Path('/etc/udev/rules.d/71-kinect-webcam-camera.rules')]
        self.assertNotIn(Path('/etc/udev/rules.d/55-kinect_audio.rules'),files)
        self.assertIn(b'02ae',rule);self.assertNotIn(b'02ad',rule)
        self.assertNotIn('obs-studio',setup.PACKAGES)
    def test_selected_local_firmware_is_validated_and_installed(self):
        firmware=self.base/'user-file';firmware.write_bytes(b'synthetic firmware')
        with patch.object(setup,'FIRMWARE_PATH',firmware),patch.object(setup,'FW_SHA',hashlib.sha256(firmware.read_bytes()).hexdigest()):
            setup.validate_payload();files=setup.destinations()
        self.assertEqual(files[setup.INSTALLED_FIRMWARE],b'synthetic firmware')
        self.assertIn(b'02ad',files[Path('/etc/udev/rules.d/55-kinect_audio.rules')])
    def test_wrong_selection_cannot_start_install(self):
        firmware=self.base/'wrong';firmware.write_bytes(b'wrong')
        with patch.object(setup,'FIRMWARE_PATH',firmware),patch.object(setup,'supported',return_value=True),patch.object(setup,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'SHA-256'):setup.plan()
        run.assert_not_called()
    def test_existing_valid_firmware_is_reused(self):
        setup.INSTALLED_FIRMWARE.parent.mkdir()
        setup.INSTALLED_FIRMWARE.write_bytes(b'already installed')
        with patch.object(setup,'FW_SHA',hashlib.sha256(b'already installed').hexdigest()):
            self.assertEqual(setup.firmware_source(),setup.INSTALLED_FIRMWARE)


class SummaryTests(unittest.TestCase):
    def test_real_read_only_check_has_four_groups(self):
        paths=['/usr/lib/firmware/kinect/UACFirmware','/usr/local/libexec/kinect-facecam/kinect_upload_fw',
               '/etc/udev/rules.d/55-kinect_audio.rules','/etc/udev/rules.d/71-kinect-webcam-camera.rules','/etc/modprobe.d/kinect-blacklist.conf',
               '/etc/modprobe.d/99-kinect-facecam.conf','/etc/modules-load.d/v4l2loopback.conf']
        with patch.object(setup,'supported',return_value=True),patch.object(setup,'validate_payload'), patch.object(setup,'firmware_source',return_value=None), \
             patch.object(setup,'missing_packages',return_value=[]), \
             patch.object(setup,'destinations',return_value={Path(name):b'fixture' for name in paths}):
            value=setup.check_state()
        self.assertEqual([item['id'] for item in value['checks']],['packages','microphone','camera','virtual_camera'])
        self.assertIsInstance(value['ready'],bool)
        self.assertTrue(all(item['status'] in ('ready','action','restart','optional') for item in value['checks']))
        self.assertNotIn('/etc/',' '.join(item['detail'] for item in value['checks']))

    def test_unsupported_system_cannot_install(self):
        with patch.object(setup, 'supported', return_value=False):
            value = setup.check_state()
        self.assertFalse(value['ready'])
        self.assertFalse(value['can_install'])

    def test_bad_payload_cannot_install(self):
        with patch.object(setup, 'supported', return_value=True), \
             patch.object(setup, 'validate_payload', side_effect=RuntimeError('bad payload')):
            value = setup.check_state()
        self.assertFalse(value['ready'])
        self.assertFalse(value['can_install'])
        self.assertIn('bad payload',value['issues'])


if __name__ == '__main__':
    unittest.main()
