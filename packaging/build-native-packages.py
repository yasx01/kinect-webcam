#!/usr/bin/env python3
"""Build native packages; never install on the build host."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '19.0.0'
FEDORA_DEPS = ['python3','python3-pyqt6','python3-numpy','libfreenect','libusb1','pulseaudio-utils',
               'pipewire','pipewire-pulseaudio','wireplumber','pipewire-utils','pipewire-gstreamer',
               'gstreamer1','gstreamer1-plugins-base','gstreamer1-plugins-good','v4l-utils',
               'polkit','glib2','kmod','util-linux','procps-ng','systemd-udev','xdg-desktop-portal','libnotify','/usr/bin/ffmpeg']
UBUNTU_DEPS = ['python3 (>= 3.12)','python3-pyqt6','python3-numpy','libfreenect0.5t64','libusb-1.0-0',
               'pulseaudio-utils','pipewire','pipewire-pulse','wireplumber','pipewire-bin','gstreamer1.0-pipewire',
               'gstreamer1.0-tools','gstreamer1.0-plugins-base','gstreamer1.0-plugins-good','v4l-utils',
               'v4l2loopback-dkms','dkms','pkexec','libglib2.0-bin','kmod','util-linux','procps','udev',
               'xdg-desktop-portal','libnotify-bin','ffmpeg']


def write(root, name, data, mode=0o644):
    path = root/name.lstrip('/')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode() if isinstance(data,str) else data)
    path.chmod(mode)


def stage(root):
    src = ROOT/'v19'
    base = 'usr/libexec/kinect-webcam'
    # Explicit allowlist excludes installed binaries, firmware, SDK and historical files.
    for path in src.iterdir():
        if path.is_file() and (path.name.endswith(('.py','.png')) or path.name.startswith('kinect-facecam-') and not path.suffix):
            write(root,base+'/'+path.name,path.read_bytes(),0o644 if path.suffix=='.png' else 0o755)
    flags = subprocess.check_output(['pkg-config','--cflags','--libs','libusb-1.0'],text=True).split()
    loader = root/base/'payload/kinect_upload_fw';loader.parent.mkdir(parents=True)
    subprocess.run(['cc','-O2','-s','-Wall','-Wextra',str(src/'vendor/kinect-audio-setup/kinect_upload_fw.c'),'-o',str(loader),*flags],check=True)
    write(root,base+'/payload/manifest.json',json.dumps({'kinect_upload_fw':hashlib.sha256(loader.read_bytes()).hexdigest()},indent=2)+'\n')
    for path in (src/'licenses').iterdir():write(root,'usr/share/doc/kinect-webcam/licenses/'+path.name,path.read_bytes())
    write(root,'usr/share/doc/kinect-webcam/copyright','Kinect Webcam project: https://github.com/yasx01/kinect-webcam\nProject license has not yet been declared.\nBundled kinect_upload_fw is BSD-2-Clause; see licenses/kinect_upload_fw-BSD-2-Clause.txt.\nSystem libraries are installed separately by the package manager.\n')
    write(root,'usr/share/doc/kinect-webcam/README.md',(ROOT/'README.md').read_bytes())
    write(root,'usr/bin/kinect-webcam','#!/bin/sh\nexec /usr/bin/python3 -I /usr/libexec/kinect-webcam/kinect-facecam-gui-v19.py "$@"\n',0o755)
    write(root,'usr/share/applications/kinect-webcam.desktop','[Desktop Entry]\nType=Application\nName=Kinect Webcam\nComment=Kinect kamera ve mikrofon kontrolü\nExec=kinect-webcam\nIcon=kinect-webcam\nTerminal=false\nCategories=AudioVideo;Video;\n')
    write(root,'usr/share/icons/hicolor/256x256/apps/kinect-webcam.png',(src/'kinect-facecam-icon-v19.png').read_bytes())
    # Configuration is package-managed; loading modules is left to reboot/explicit setup.
    spec=importlib.util.spec_from_file_location('setup',src/'kinect-facecam-setup-v19.py');setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
    write(root,'etc/udev/rules.d/71-kinect-webcam-camera.rules','\n'.join(line for line in setup.UDEV.splitlines() if line.startswith('SUBSYSTEM=='))+'\n')
    write(root,'etc/modprobe.d/99-kinect-facecam.conf',setup.V4L)
    write(root,'etc/modprobe.d/kinect-blacklist.conf','# libfreenect uses the Kinect camera\nblacklist gspca_kinect\n')
    write(root,'etc/modules-load.d/v4l2loopback.conf','v4l2loopback\n')
    assert not any(p.name.lower().startswith('uacfirmware') or p.suffix.lower() in ('.msi','.exe') for p in root.rglob('*'))


def build(kind):
    out=ROOT/'dist';out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='kinect-native-') as folder:
        work=Path(folder);payload=work/'root';payload.mkdir();stage(payload)
        if kind=='deb':
            write(payload,'DEBIAN/control',f'Package: kinect-webcam\nVersion: {VERSION}-1\nArchitecture: amd64\nMaintainer: yasx01 <221063449+yasx01@users.noreply.github.com>\nDepends: '+', '.join(UBUNTU_DEPS)+'\nRecommends: linux-headers-generic, xdg-desktop-portal-gnome | xdg-desktop-portal-kde\nSection: video\nPriority: optional\nHomepage: https://github.com/yasx01/kinect-webcam\nDescription: Kinect camera and microphone control panel\n Passive previews and native Ubuntu package integration.\n')
            write(payload,'DEBIAN/conffiles',''.join('/'+str(p.relative_to(payload))+'\n' for p in sorted((payload/'etc').rglob('*')) if p.is_file()))
            target=out/f'kinect-webcam_{VERSION}-1_amd64.deb'
            subprocess.run(['dpkg-deb','--root-owner-group','--build',str(payload),str(target)],check=True)
        else:
            top=work/'rpm';(top/'SOURCES').mkdir(parents=True);(top/'SPECS').mkdir()
            with tarfile.open(top/'SOURCES/payload.tar.gz','w:gz') as archive:
                for path in sorted(payload.iterdir()):archive.add(path,arcname=path.name)
            spec=top/'SPECS/kinect-webcam.spec'
            spec.write_text(f'''%global debug_package %{{nil}}
%global __brp_strip %{{nil}}
%global __brp_strip_comment_note %{{nil}}
%global __brp_strip_static_archive %{{nil}}
%global __brp_strip_lto %{{nil}}
%global __brp_python_bytecompile %{{nil}}
Name: kinect-webcam
Version: {VERSION}
Release: 1%{{?dist}}
Summary: Kinect camera and microphone control panel
License: LicenseRef-Unspecified AND BSD-2-Clause
URL: https://github.com/yasx01/kinect-webcam
Source0: payload.tar.gz
Requires: {', '.join(FEDORA_DEPS)}
Recommends: xdg-desktop-portal-kde

%description
Kinect camera and microphone control panel with passive previews.
Optional virtual camera preparation is available in the first setup dialog.

%prep
%build
%install
mkdir -p %{{buildroot}}
tar -xf %{{SOURCE0}} -C %{{buildroot}}

%files
%defattr(-,root,root,-)
/usr/bin/kinect-webcam
/usr/libexec/kinect-webcam
/usr/share/applications/kinect-webcam.desktop
/usr/share/icons/hicolor/256x256/apps/kinect-webcam.png
%doc /usr/share/doc/kinect-webcam
%config(noreplace) /etc/udev/rules.d/71-kinect-webcam-camera.rules
%config(noreplace) /etc/modprobe.d/99-kinect-facecam.conf
%config(noreplace) /etc/modprobe.d/kinect-blacklist.conf
%config(noreplace) /etc/modules-load.d/v4l2loopback.conf
''')
            subprocess.run(['rpmbuild','--define',f'_topdir {top}','-bb',str(spec)],check=True)
            built=list((top/'RPMS').rglob('*.rpm'));assert len(built)==1,built
            target=out/built[0].name;shutil.copy2(built[0],target)
    (out/(target.name+'.sha256')).write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n')
    print(target)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('format',choices=['rpm','deb']);build(parser.parse_args().format)
