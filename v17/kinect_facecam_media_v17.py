"""Private live-preview snapshots and bounded mono audio test utilities."""
import array
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid
import wave

RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
RECORD_SECONDS = 5
RECORD_BYTES = RATE * CHANNELS * SAMPLE_WIDTH * RECORD_SECONDS


def media_dir():
    base = Path(os.environ.get('XDG_RUNTIME_DIR', tempfile.gettempdir()))
    path = base / ('kinect-webcam-media-' + str(os.getuid()))
    if path.is_symlink():
        raise OSError('Önizleme dizini sembolik bağlantı olamaz.')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    stat = path.stat()
    if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise OSError('Önizleme dizini kullanıcıya özel olmalı.')
    return path


def atomic_write(path, data):
    fd, temp = tempfile.mkstemp(prefix='.media-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def process_token(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return None


class SnapshotWriter:
    def __init__(self, mode):
        self.mode = mode
        self.owner = uuid.uuid4().hex
        self.pid = os.getpid()
        self.token = process_token(self.pid)
        self.last = 0.0
        self.sequence = 0
        self.image_path = None
        self.meta_path = None
        self.warned = False

    def publish(self, frame):
        now = time.monotonic()
        if self.sequence and now - self.last < 0.5:
            return False
        try:
            from PyQt6.QtCore import QBuffer, QIODevice
            from PyQt6.QtGui import QImage
            folder = media_dir()
            self.image_path = folder / f'{self.mode}-{self.pid}-{self.owner}.jpg'
            self.meta_path = folder / f'{self.mode}-latest.json'
            height, width = frame.shape[:2]
            raw = frame.tobytes()
            image = QImage(raw, width, height, width * 3, QImage.Format.Format_RGB888)
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            if image.isNull() or not image.save(buffer, 'JPEG', 75):
                return False
            atomic_write(self.image_path, bytes(buffer.data()))
            self.sequence += 1
            atomic_write(self.meta_path, json.dumps({'pid': self.pid, 'process_start': self.token,
                'owner': self.owner, 'sequence': self.sequence, 'captured': now,
                'image': self.image_path.name}).encode())
            self.last = now
            return True
        except Exception as exc:
            if not self.warned:
                print('Önizleme yazılamadı; asıl kamera akışı korunuyor: ' + str(exc), file=sys.stderr, flush=True)
                self.warned = True
            return False

    def close(self):
        if self.image_path:
            try:
                self.image_path.unlink(missing_ok=True)
            except OSError:
                pass
        if self.meta_path:
            try:
                if json.loads(self.meta_path.read_text()).get('owner') == self.owner:
                    self.meta_path.unlink(missing_ok=True)
            except (OSError, ValueError):
                pass


def read_snapshot(mode, expected_pid, max_age=3):
    try:
        folder = media_dir()
        meta = json.loads((folder / f'{mode}-latest.json').read_text())
        token = process_token(expected_pid)
        if token is None or meta['pid'] != expected_pid or meta.get('process_start') != token:
            return None
        age = time.monotonic() - meta['captured']
        if age < 0 or age > max_age:
            return None
        name = meta['image']
        if not isinstance(name, str) or Path(name).name != name:
            return None
        path = folder/name
        if path.is_symlink():
            return None
        return path.read_bytes(), meta
    except (OSError, ValueError, KeyError, TypeError):
        return None


def audio_level(pcm):
    pcm = pcm[:len(pcm)//2*2]
    if not pcm:
        return 0, -90.0
    samples = array.array('h')
    samples.frombytes(pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    rms = math.sqrt(sum(int(s)*int(s) for s in samples)/len(samples))/32768
    db = max(-90.0, 20*math.log10(rms)) if rms else -90.0
    return int(max(0, min(100, (db+60)/60*100))), db


def write_clip(path, pcm):
    if len(pcm) != RECORD_BYTES:
        raise ValueError('Beş saniyelik kayıt tamamlanmadı.')
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'wb') as output:
        with wave.open(output, 'wb') as stream:
            stream.setnchannels(CHANNELS)
            stream.setsampwidth(SAMPLE_WIDTH)
            stream.setframerate(RATE)
            stream.writeframes(pcm)
