"""The native C buffer is copied; no physical USB device is opened."""
import ctypes
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('camera_binding',ROOT/'v19/kinect_facecam_camera_v19.py');camera=importlib.util.module_from_spec(spec);spec.loader.exec_module(camera)

class NativeCameraTests(unittest.TestCase):
    def test_buffer_is_copied_before_next_native_frame(self):
        raw=(ctypes.c_ubyte*(640*480*3))();raw[0]=123
        def capture(data,timestamp,index,format):
            self.assertEqual((index,format),(0,0))
            ctypes.cast(data,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.cast(raw,ctypes.c_void_p)
            ctypes.cast(timestamp,ctypes.POINTER(ctypes.c_uint32))[0]=42
            return 0
        lib=Mock();lib.freenect_sync_get_video.side_effect=capture
        with patch.object(camera,'_library',lib):frame,timestamp=camera.sync_get_video()
        raw[0]=0
        self.assertEqual(frame.shape,(480,640,3));self.assertEqual(frame[0,0,0],123);self.assertEqual(timestamp,42)

    def test_no_frame_returns_none_without_reading_null_pointer(self):
        lib=Mock();lib.freenect_sync_get_video.return_value=-1
        with patch.object(camera,'_library',lib):self.assertIsNone(camera.sync_get_video())
        lib.freenect_sync_get_video.return_value=0
        with patch.object(camera,'_library',lib):self.assertIsNone(camera.sync_get_video())

    def test_no_library_does_not_open_device_on_stop(self):
        with patch.object(camera,'_library',None),patch.object(camera.ctypes,'CDLL') as load:
            camera.sync_stop()
        load.assert_not_called()

    def test_missing_library_is_a_clear_error(self):
        with patch.object(camera,'_library',None),patch.object(camera.ctypes.util,'find_library',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'libfreenect_sync'):camera.library()

if __name__=='__main__':unittest.main()
