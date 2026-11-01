"""Only a user-selected, known UACFirmware is passed to the bundled loader."""
import hashlib
from pathlib import Path
import subprocess
from common import native_dir

FW_SHA = 'efd1dd2fd2610f69d07af7aeff56b26551ac6ec4251159c50027769545b6f7a5'


def validate(path):
    path = Path(path)
    if path.stat().st_size > 4*1024*1024 or hashlib.sha256(path.read_bytes()).hexdigest() != FW_SHA:
        raise ValueError('Bu dosya beklenen Kinect UACFirmware dosyası değil; yükleme yapılmadı.')
    return path.resolve()


def upload(path):
    path = validate(path)
    loader = native_dir()/'kinect_upload_fw.exe'
    result = subprocess.run([str(loader),str(path)],capture_output=True,text=True,timeout=60,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise RuntimeError('Ses hazırlığı tamamlanmadı. Ham ses aygıtının (045e:02ad) sürücüsünü denetle.\n'+result.stdout[-2000:]+result.stderr[-1000:])
    return 'Firmware aktarıldı. Windows ses listesinde Kinect mikrofonunu denetle. USB yeniden takılırsa yükleme tekrarlanabilir.'
