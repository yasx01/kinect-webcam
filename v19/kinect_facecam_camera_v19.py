"""Use the distro's stable libfreenect C API without a Python extension package."""
import ctypes
import ctypes.util
import numpy as np

_library = None


def library():
    global _library
    if _library is None:
        name = ctypes.util.find_library('freenect_sync')
        if not name:
            raise RuntimeError('libfreenect_sync bulunamadı; dağıtımın libfreenect paketini denetle.')
        lib = ctypes.CDLL(name)
        lib.freenect_sync_get_video.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int]
        lib.freenect_sync_get_video.restype = ctypes.c_int
        lib.freenect_sync_stop.argtypes = []
        lib.freenect_sync_stop.restype = None
        _library = lib
    return _library


def sync_get_video():
    data, timestamp = ctypes.c_void_p(), ctypes.c_uint32()
    if library().freenect_sync_get_video(ctypes.byref(data), ctypes.byref(timestamp), 0, 0) != 0 or not data.value:
        return None
    # FREENECT_VIDEO_RGB at medium resolution; copy before the native buffer is reused.
    frame = np.frombuffer(ctypes.string_at(data,640*480*3),dtype=np.uint8).reshape(480,640,3)
    return frame, timestamp.value


def sync_stop():
    if _library is not None:
        _library.freenect_sync_stop()
