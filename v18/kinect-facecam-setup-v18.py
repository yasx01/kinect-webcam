#!/usr/bin/env python3
"""Fedora x86_64 ilk kurulum. --plan ve --check salt okunurdur; --apply root ister."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
FW_SHA = "efd1dd2fd2610f69d07af7aeff56b26551ac6ec4251159c50027769545b6f7a5"
FIRMWARE_PATH = None
INSTALLED_FIRMWARE = Path('/usr/lib/firmware/kinect/UACFirmware')
PACKAGES = ["python3", "python3-pyqt6", "python3-libfreenect", "python3-numpy",
            "libfreenect", "libusb1", "pulseaudio-utils", "pipewire", "pipewire-pulseaudio",
            "wireplumber", "pipewire-utils", "pipewire-gstreamer", "gstreamer1", "gstreamer1-plugins-base",
            "gstreamer1-plugins-good", "v4l-utils", "akmods", "akmod-v4l2loopback",
            "polkit", "glib2", "policycoreutils", "kmod", "util-linux", "procps-ng", "systemd-udev", "xdg-desktop-portal", "xdg-desktop-portal-kde", "libnotify"]
UDEV = ('# Kinect Webcam v18: yalnızca USB cihazı eklenince bir kez çalıştır.\n'
        'ACTION=="add", SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", '
        'ATTR{idVendor}=="045e", ATTR{idProduct}=="02ad", '
        'RUN+="/usr/local/libexec/kinect-facecam/kinect_upload_fw /usr/lib/firmware/kinect/UACFirmware"\n'
        'SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="045e", '
        'ATTR{idProduct}=="02ae", TAG+="uaccess"\n')
V4L = 'options v4l2loopback video_nr=20,21 card_label="Kinect360 Facecam,OBS Virtual Camera" exclusive_caps=1,1\n'
ENV = dict(os.environ, PATH="/usr/sbin:/usr/bin:/sbin:/bin", LC_ALL="C")


def run(args, check=True, capture=False):
    result = subprocess.run(args, check=False, env=ENV, text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.STDOUT if capture else None)
    if check and result.returncode:
        raise RuntimeError("Komut başarısız: " + " ".join(args) + "\n" + (result.stdout or ""))
    return result


def supported():
    info = Path('/etc/os-release').read_text()
    return any(line.strip() in ('ID=fedora', 'ID="fedora"') for line in info.splitlines()) and platform.machine() == 'x86_64'


def required_packages():
    names = PACKAGES + ["kernel-devel-" + platform.release()]
    # Raw RGB/V4L2 needs no restricted codecs. Keep an existing full FFmpeg;
    # otherwise choose Fedora's ffmpeg-free to avoid codec-package conflicts.
    if run(['rpm', '-q', '--whatprovides', '/usr/bin/ffmpeg'], check=False, capture=True).returncode:
        names.append('ffmpeg-free')
    return names


def missing_packages():
    names = required_packages()
    result = run(["rpm", "-q", "--qf", "%{NAME}\n", *names], check=False, capture=True)
    # rpm emits a line per missing query, including the kernel-devel version query.
    installed = set(result.stdout.splitlines())
    return [name for name in names if (name not in installed if not name.startswith('kernel-devel-')
                                      else run(['rpm', '-q', name], check=False, capture=True).returncode != 0)]


def firmware_source():
    # Only explicit selections/staged firmware are mandatory; a corrupt old install is optional.
    explicit = FIRMWARE_PATH or (HERE/'payload/UACFirmware')
    if FIRMWARE_PATH is not None or explicit.exists():
        if explicit.stat().st_size > 4*1024*1024 or hashlib.sha256(explicit.read_bytes()).hexdigest() != FW_SHA:
            raise RuntimeError('Firmware SHA-256 eşleşmedi; dosya kullanılmadı.')
        return explicit
    if INSTALLED_FIRMWARE.is_file() and INSTALLED_FIRMWARE.stat().st_size <= 4*1024*1024:
        if hashlib.sha256(INSTALLED_FIRMWARE.read_bytes()).hexdigest() == FW_SHA:
            return INSTALLED_FIRMWARE
    return None


def validate_payload():
    firmware_source()
    manifest = json.loads((HERE/'payload/manifest.json').read_text())
    if hashlib.sha256((HERE/'payload/kinect_upload_fw').read_bytes()).hexdigest() != manifest['kinect_upload_fw']:
        raise RuntimeError('Paket bütünlüğü hatası: kinect_upload_fw')


def destinations():
    firmware = firmware_source()
    rules = UDEV if firmware else "\n".join(line for line in UDEV.splitlines() if line.startswith('SUBSYSTEM==')) + "\n"
    files = {
        Path('/usr/local/libexec/kinect-facecam/kinect_upload_fw'): (HERE/'payload/kinect_upload_fw').read_bytes(),
        Path('/etc/udev/rules.d/71-kinect-webcam-camera.rules'): rules.encode(),
        Path('/etc/modprobe.d/99-kinect-facecam.conf'): V4L.encode(),
        Path('/etc/modules-load.d/v4l2loopback.conf'): b'v4l2loopback\n',
        Path('/etc/modprobe.d/kinect-blacklist.conf'): b'# libfreenect uses the Kinect camera\nblacklist gspca_kinect\n',
    }
    if firmware is not None:
        files[Path('/etc/udev/rules.d/55-kinect_audio.rules')] = UDEV.encode()
        files[INSTALLED_FIRMWARE] = firmware.read_bytes()
    return files


def check_state():
    """Machine-readable, read-only summary for the graphical setup screen."""
    issues, checks = [], []
    if not supported():
        return {'ready': False, 'can_install': False, 'checks': [],
                'issues': ['Yalnızca Fedora x86_64 destekleniyor.']}
    try:
        validate_payload()
        missing = missing_packages()
        if missing:
            issues.append('Eksik paketler: ' + ', '.join(missing))
        checks.append({'id': 'packages', 'title': 'Gerekli uygulamalar',
                       'status': 'action' if missing else 'ready',
                       'detail': (str(len(missing)) + ' bileşen kurulacak.' if missing
                                  else 'Kamera ve ses için gerekli programlar kurulu.')})
        files = destinations()
        groups = [
            ('microphone', 'Mikrofon hazırlığı',
             ['/usr/lib/firmware/kinect/UACFirmware',
              '/usr/local/libexec/kinect-facecam/kinect_upload_fw', '/etc/udev/rules.d/55-kinect_audio.rules'],
             'Ses yazılımı ve otomatik yükleme hazır.',
             'Ses yazılımı ve otomatik yükleme hazırlanacak.'),
            ('camera', 'Kamera erişimi', ['/etc/modprobe.d/kinect-blacklist.conf', '/etc/udev/rules.d/71-kinect-webcam-camera.rules'],
             'Kamera sürücüsünün erişim ayarı hazır.', 'Kamera erişim ayarı tamamlanacak.'),
            ('virtual_camera', 'Sanal kamera bağlantısı',
             ['/etc/modprobe.d/99-kinect-facecam.conf', '/etc/modules-load.d/v4l2loopback.conf'],
             'Tarayıcı ve OBS için sanal kamera ayarları hazır.', 'Sanal kamera ayarları tamamlanacak.')]
        for ident, title, paths, ready_text, action_text in groups:
            if ident == 'microphone' and firmware_source() is None:
                checks.append({'id':ident,'title':title,'status':'optional',
                               'detail':'Kamera için gerekmez. Mikrofon hazırlığı için yerel firmware seçebilirsin.'})
                continue
            changed = []
            for name in paths:
                path = Path(name)
                if not path.is_file() or path.read_bytes() != files[path]:
                    changed.append(name)
                    issues.append('Kurulum gerekli: ' + name)
            status, detail = ('action', action_text) if changed else ('ready', ready_text)
            if ident == 'camera' and Path('/sys/module/gspca_kinect').exists():
                issues.append('gspca_kinect yüklü; yeniden başlatma gerekli.')
                if not changed:
                    status, detail = 'restart', 'Ayarlar hazır; yeniden başlatma gerekiyor.'
            if ident == 'virtual_camera':
                devices_ready = True
                for name, label in [('video20', 'Kinect360 Facecam'), ('video21', 'OBS Virtual Camera')]:
                    device = Path('/sys/class/video4linux') / name / 'name'
                    if not device.exists() or device.read_text().strip() != label:
                        devices_ready = False
                        issues.append('Sanal kamera hazır değil: ' + name)
                if not devices_ready:
                    status, detail = 'action', 'Sanal kamera hazırlanıp etkinleştirilecek.'
            checks.append({'id': ident, 'title': title, 'status': status, 'detail': detail})
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        return {'ready': False, 'can_install': False, 'checks': checks,
                'issues': issues + [str(exc)]}
    return {'ready': not issues, 'can_install': True, 'checks': checks, 'issues': issues,
            'microphone_ready': next((c['status']=='ready' for c in checks if c['id']=='microphone'),False),
            'note': 'Bu hazırlık kontrolüdür; kamera ve mikrofon ayrıca denenmelidir.'}


def phase(ident):
    print('KINECT_SETUP_EVENT ' + json.dumps({'phase': ident}), flush=True)


def plan():
    if not supported():
        raise RuntimeError('Bu kurulum yalnızca Fedora x86_64 içindir.')
    validate_payload()
    missing = missing_packages()
    print('Fedora KDE · Kinect Webcam v18 ilk kurulum\n', flush=True)
    print('Eksik paketler: ' + (', '.join(missing) if missing else 'yok'), flush=True)
    print('Mikrofon firmware’i: ' + ('mevcut, ses hazırlığı yapılacak.' if firmware_source() else 'seçilmedi; kamera kurulumu devam edebilir.'), flush=True)
    print('RPM Fusion Free deposu eksikse etkinleştirilecek. İnternet gereklidir.\n'
          'Açık kaynak yükleyicisi ve seçilmişse mikrofon firmware’i kurulacak.\n'
          'USB izinleri, otomatik firmware yükleme ve iki sanal kamera ayarlanacak.\n'
          'Değişen dosyalar /var/backups/kinect-facecam altında yedeklenecek.\n'
          'Kısmi hata durumunda kurulmuş paketler otomatik kaldırılmaz.\n'
          'Eski kinect-webcam.service değiştirilmez.\n'
          'Kurulumdan sonra Kinect’i çıkarıp takman, bazen yeniden başlatman gerekir.\n'
          'Mikrofon ve kamera başarı durumu ayrıca gerçek cihazla sınanmalıdır.', flush=True)
    return missing


def write_atomic(path, content, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.kinect-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def apply():
    if os.geteuid() != 0:
        raise RuntimeError('Yönetici onayı gerekli; uygulamadaki İlk kurulum düğmesini kullan.')
    missing = plan()
    phase("packages")
    # Do not race a camera stream or unload modules underneath existing software.
    if run(['pgrep', '-f', 'kinect-facecam-bridge'], check=False, capture=True).returncode == 0:
        raise RuntimeError('Önce çalışan Kinect kamera akışını durdur.')
    if run(['rpm', '-q', 'rpmfusion-free-release'], check=False, capture=True).returncode:
        fedora = run(['rpm', '-E', '%fedora'], capture=True).stdout.strip()
        if not fedora.isdigit():
            raise RuntimeError('Fedora sürümü okunamadı.')
        run(['dnf', 'install', '-y', 'https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-' + fedora + '.noarch.rpm'])
    if missing:
        print('Sistem paketleri kuruluyor...', flush=True)
        run(['dnf', 'install', '-y', *missing])
    remaining = missing_packages()
    if remaining:
        raise RuntimeError('Paketler hâlâ eksik: ' + ', '.join(remaining))
    run(['/usr/bin/python3', '-I', '-c', 'import freenect, numpy, PyQt6.QtWidgets'])
    for plugin in ('pipewiresink', 'rawvideoparse', 'videoconvert'):
        run(['gst-inspect-1.0', plugin], capture=True)
    formats = run(['ffmpeg', '-hide_banner', '-muxers'], capture=True).stdout
    if 'v4l2' not in formats:
        raise RuntimeError('FFmpeg V4L2 çıkış desteği bulunamadı.')
    # Verify loader dependencies only after libusb has been installed.
    result = run(['/usr/bin/ldd', str(HERE/'payload/kinect_upload_fw')], capture=True)
    if 'not found' in result.stdout:
        raise RuntimeError('Firmware yükleyicisi bağımlılıkları eksik:\n' + result.stdout)
    phase("files")
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = Path('/var/backups/kinect-facecam') / stamp
    files = destinations()
    # Disarm just the historical conflicting module configuration, retaining a backup.
    legacy = Path('/etc/modprobe.d/kinect-v4l2loopback.conf')
    for path, content in files.items():
        if path.is_symlink():
            raise RuntimeError('Beklenmeyen sembolik bağlantı: ' + str(path))
        mode = 0o755 if path.name == 'kinect_upload_fw' else 0o644
        if path.exists() and path.read_bytes() != content:
            target = backup / str(path).lstrip('/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        write_atomic(path, content, mode)
        print('Kuruldu: ' + str(path), flush=True)
    if legacy.exists():
        target = backup / str(legacy).lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, target)
        legacy.unlink()
    # Atomic replacement can inherit a temporary-file label; restore Fedora policy labels.
    run(['restorecon', '-RF', *[str(path) for path in files]])
    phase('camera')
    print('Çekirdek için sanal kamera modülü hazırlanıyor...', flush=True)
    run(['akmods', '--force', '--kernels', platform.release()])
    run(['modprobe', 'v4l2loopback'])
    run(['udevadm', 'control', '--reload-rules'])
    # No global trigger and no firmware upload now: reconnect applies permissions/rules safely.
    phase('verify')
    state = check_state()
    if not state['ready']:
        print('\nKurulum henüz hazır değil:\n' + '\n'.join(state['issues']), flush=True)
        print('Secure Boot modül yüklemesini engelliyorsa imzalama gerekir.\n'
              'Eski modül ayarları yüklüyse bilgisayarı yeniden başlatıp tekrar denetle.', flush=True)
        return 3
    print('\nKamera hazırlığı tamamlandı. Mikrofon durumu ayrıca denetlenmelidir. Kinect’i çıkarıp tekrar tak.\n'
          'Kamera ve mikrofonun gerçek çalışması henüz doğrulanmadı.', flush=True)
    return 0


def main():
    global FIRMWARE_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firmware',type=Path,help='Kullanıcının seçtiği yerel UACFirmware dosyası')
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ('plan', 'check', 'apply'):
        group.add_argument('--' + flag, action='store_true')
    args = parser.parse_args()
    FIRMWARE_PATH = args.firmware
    try:
        if args.check:
            state = check_state()
            print(json.dumps(state, ensure_ascii=False))
            return 0 if state['ready'] else 1
        if args.plan:
            plan()
            return 0
        return apply()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print('KURULUM BAŞARISIZ: ' + str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
