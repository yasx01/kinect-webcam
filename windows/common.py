"""Windows paths and device identification; audio helpers stay shared with Linux."""
from pathlib import Path
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[1]
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(SOURCE_ROOT/'v15'))
from kinect_facecam_media_v15 import atomic_write, audio_level, write_clip, RATE, RECORD_BYTES


def resources():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def native_dir():
    return resources()/'native'


def is_kinect(name):
    name = (name or '').casefold()
    return 'kinect' in name or 'xbox nui' in name


def microphone_endpoint():
    from pycaw.pycaw import AudioUtilities
    # Capture + active only. Never change the default microphone or a speaker.
    matches = [dev for dev in AudioUtilities.GetAllDevices(data_flow=1, device_state=1)
               if is_kinect(dev.FriendlyName)]
    if len(matches) != 1:
        raise RuntimeError('Tek bir Kinect mikrofonu bulunamadı; bağlantıyı ve Windows ses ayarlarını denetle.')
    return matches[0].EndpointVolume
