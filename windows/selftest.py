"""Packaged-exe checks without recording or accessing a physical Kinect camera."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import numpy as np
from common import atomic_write, native_dir


class TestSource:
    def __init__(self, folder):self.folder=Path(folder);self.count=0
    def frame(self):
        self.count+=1
        if self.count==3:(self.folder/'stop').touch()
        return np.full((480,640,3),(32,128,224),dtype=np.uint8)
    def close(self):pass


class TestSink:
    def __init__(self):self.frames=0
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def send(self,frame):
        assert frame.shape==(480,640,3)
        self.frames+=1
    def sleep_until_next_frame(self):pass


def test_worker(folder):
    from camera import run
    return run(folder,True,source_factory=lambda:TestSource(folder),sink_factory=TestSink)


def self_test(report):
    checks={};window=None
    try:
        import pyvirtualcam
        import pycaw.pycaw
        import comtypes
        from camera import NativeCamera
        source=NativeCamera();source.close();checks['native_dll_load']=True
        checks['virtual_camera_module']=bool(pyvirtualcam.Camera)
        loader=subprocess.run([str(native_dir()/'kinect_upload_fw.exe'),'--help'],
                              capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert loader.returncode!=0 and b'Failed to open' in loader.stderr
        checks['native_loader_startup']=True
        driver=subprocess.run([str(native_dir()/'kinect-driver.exe'),'--self-test'],capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert driver.returncode==0,(driver.returncode,driver.stderr)
        checks['bundled_driver_and_kinect_only_allowlist']=True
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QProcess
        from app import MainWindow,child_command
        app=QApplication.instance() or QApplication([])
        window=MainWindow();window.show();app.processEvents();checks['gui_startup']=window.isVisible()
        with tempfile.TemporaryDirectory(prefix='kinect-exe-selftest-') as folder:
            command,args=child_command('--test-worker',folder)
            process=QProcess();process.start(command,args)
            if not process.waitForStarted(10000):raise RuntimeError('Child process did not start.')
            if not process.waitForFinished(20000):
                process.kill();process.waitForFinished(3000);raise RuntimeError('Child process did not stop.')
            assert process.exitCode()==0,(process.exitCode(),bytes(process.readAllStandardError()))
            state=json.loads((Path(folder)/'state.json').read_text(encoding='utf-8'))
            assert state['state']=='running'
            assert (Path(folder)/'frame.jpg').read_bytes().startswith(b'\xff\xd8')
            checks['packaged_camera_child_and_virtual_send']=True
        message='Kinect kamerası açılamadı. USB/güç bağlantısını denetle. ŞİĞÜÖÇ ıüğöç'
        atomic_write(window.folder/'state.json',json.dumps({'state':'error','message':message},ensure_ascii=False).encode('utf-8'))
        window.finished(1,QProcess.ExitStatus.NormalExit)
        assert window.status.text()==message
        checks['turkish_utf8_child_message']=True
        from audio import AudioTest,mono_pcm16
        dialog=AudioTest(window);assert dialog.source is None;dialog.reject()
        checks['audio_dialog_no_implicit_recording']=True
        result={'ok':all(checks.values()),'checks':checks,'python':sys.version,'platform':sys.platform,
                'physical_kinect_tested':False,'windows_10_hardware_tested':False}
        code=0
    except Exception:
        result={'ok':False,'checks':checks,'error':traceback.format_exc()};code=1
    finally:
        if window is not None:window.close()
    atomic_write(Path(report),json.dumps(result,indent=2).encode())
    return code
