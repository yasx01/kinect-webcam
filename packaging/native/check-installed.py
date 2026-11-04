"""Check installed resources and startup, without opening the physical Kinect."""
import ctypes
import ctypes.util
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

base=Path('/usr/libexec/kinect-webcam')
manifest=json.loads((base/'payload/manifest.json').read_text())
assert hashlib.sha256((base/'payload/kinect_upload_fw').read_bytes()).hexdigest()==manifest['kinect_upload_fw']
assert not list(base.rglob('UACFirmware*'))
spec=importlib.util.spec_from_file_location('native_camera',base/'kinect_facecam_camera_v19.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.library().freenect_sync_get_video
linked=subprocess.run(['ldd',str(base/'payload/kinect_upload_fw')],check=True,capture_output=True)
assert b'not found' not in linked.stdout
process=subprocess.Popen(['/usr/bin/kinect-webcam'],env=dict(os.environ,QT_QPA_PLATFORM='offscreen'),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    time.sleep(1);assert process.poll() is None,'GUI did not remain open'
finally:
    process.terminate();stdout,stderr=process.communicate(timeout=10)
assert b'Traceback' not in stderr,stderr
report={'format':sys.argv[1],'installed':True,'gui_startup':True,'distro_libfreenect_load':True,'firmware_bundled':False,'physical_kinect_tested':False,'kernel_module_load_tested':False}
Path('dist/native-'+sys.argv[1]+'-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
