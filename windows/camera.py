"""A separate child process owns the blocking libfreenect capture and OBS output."""
import ctypes
from contextlib import nullcontext
import json
import os
from pathlib import Path
import time
import numpy as np
from PyQt6.QtCore import QBuffer, QIODevice
from PyQt6.QtGui import QImage
from common import atomic_write, native_dir

WIDTH, HEIGHT, FPS = 640, 480, 30


class NativeCamera:
    def __init__(self):
        folder = native_dir().resolve()
        self.directory_cookie = os.add_dll_directory(str(folder)) if os.name == 'nt' else None
        candidates = [folder/'libfreenect_sync.dll', folder/'freenect_sync.dll']
        path = next((p for p in candidates if p.is_file()), None)
        if path is None:
            raise RuntimeError('Kamera kitaplığı eksik. Tam Windows paketini yeniden indir.')
        self.library = ctypes.CDLL(str(path))
        self.library.freenect_sync_get_video.argtypes = [ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int]
        self.library.freenect_sync_get_video.restype = ctypes.c_int
        self.library.freenect_sync_stop.argtypes = []
        self.library.freenect_sync_stop.restype = None

    def frame(self):
        pointer, timestamp = ctypes.c_void_p(), ctypes.c_uint32()
        # FREENECT_VIDEO_RGB=0, medium resolution=640x480; copy before the next call.
        if self.library.freenect_sync_get_video(ctypes.byref(pointer), ctypes.byref(timestamp), 0, 0) != 0 or not pointer.value:
            raise RuntimeError('Kinect kamerası açılamadı. USB/güç bağlantısını ve libusbK kamera sürücüsünü denetle.')
        return np.frombuffer(ctypes.string_at(pointer, WIDTH*HEIGHT*3), dtype=np.uint8).reshape(HEIGHT, WIDTH, 3)

    def close(self):
        self.library.freenect_sync_stop()
        if self.directory_cookie:
            self.directory_cookie.close()


def obs_camera():
    import pyvirtualcam
    return pyvirtualcam.Camera(width=WIDTH, height=HEIGHT, fps=FPS,
                               fmt=pyvirtualcam.PixelFormat.RGB, backend='obs')


def write_frame(folder, frame, sequence):
    if frame.shape != (HEIGHT, WIDTH, 3) or frame.dtype != np.uint8:
        raise ValueError('Kamera karesinin biçimi geçersiz.')
    raw = frame.tobytes()
    image = QImage(raw, WIDTH, HEIGHT, WIDTH*3, QImage.Format.Format_RGB888)
    buffer = QBuffer(); buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, 'JPEG', 80):
        raise RuntimeError('Önizleme oluşturulamadı.')
    atomic_write(folder/'frame.jpg', bytes(buffer.data()))
    atomic_write(folder/'state.json', json.dumps({'state':'running','sequence':sequence,
                                               'captured':time.time()}).encode())


def run(folder, virtual, source_factory=NativeCamera, sink_factory=obs_camera):
    folder = Path(folder)
    source = None
    try:
        atomic_write(folder/'state.json', b'{"state":"starting"}')
        source = source_factory()
        with sink_factory() if virtual else nullcontext() as sink:
            last_preview, sequence = 0, 0
            while not (folder/'stop').exists():
                frame = source.frame()
                if sink is not None:
                    sink.send(frame)
                    sink.sleep_until_next_frame()
                sequence += 1
                if time.monotonic()-last_preview >= 0.5:
                    write_frame(folder, frame, sequence)
                    last_preview = time.monotonic()
        return 0
    except Exception as exc:
        atomic_write(folder/'state.json', json.dumps({'state':'error','message':str(exc)},ensure_ascii=False).encode())
        return 1
    finally:
        if source is not None:
            source.close()
