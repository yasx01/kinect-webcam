"""Prove the archived pipeline is preserved and camera setup precedes browser repair."""
import ast
import json
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('backend',ROOT/'v19/kinect-facecam-firefox-permission-v19.py')
backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
READY='''Audio
 ├─ Sources:
 │  10. Other microphone
Video
 ├─ Devices:
 ├─ Sinks:
 ├─ Sources:
 │  90. Kinect Kamerasi
 ├─ Filters:
 └─ Streams:
Settings
'''


def gst_args(source):
    tree=ast.parse(source)
    variables={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
            if name in ('WIDTH','HEIGHT','FPS','CLIENT_NAME'):
                variables[name]=ast.literal_eval(node.value)
            elif name=='gst_cmd':
                return eval(compile(ast.Expression(node.value),'<pipeline expression>','eval'),{'__builtins__':{},'str':str},variables)
    raise AssertionError('gst_cmd missing')


class LegacyStreamTests(unittest.TestCase):
    def test_gstreamer_pipeline_matches_working_archive(self):
        reference=json.loads((ROOT/'tests/fixtures/legacy-gst-command.json').read_text())
        current=(ROOT/'v19/kinect-facecam-bridge-pipewire-v19.py').read_text()
        self.assertEqual(gst_args(current),reference)

    def test_only_video_source_counts_as_ready(self):
        self.assertTrue(backend.has_kinect_video_source(READY))
        self.assertFalse(backend.has_kinect_video_source(READY.replace('90. Kinect Kamerasi','90. Other camera')))
        self.assertFalse(backend.has_kinect_video_source('Audio\n Sources:\n Kinect Kamerasi\nVideo\n Sources:\n Other camera'))
        self.assertFalse(backend.has_kinect_video_source('Video\n Streams:\n Kinect Kamerasi'))

    def test_ensure_starts_packaged_stream_then_checks_wpctl(self):
        responses=[subprocess.CompletedProcess([],0,'started',''),subprocess.CompletedProcess([],0,READY,'')]
        with patch.object(backend.subprocess,'run',side_effect=responses) as run:
            backend.ensure_browser_stream()
        self.assertTrue(run.call_args_list[0].args[0][1].endswith('kinect-facecam-pw-start-v19'))
        self.assertEqual(run.call_args_list[1].args[0],['/usr/bin/wpctl','status'])

    def test_start_failure_is_a_stream_error(self):
        with patch.object(backend.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'OBS is running','')) as run:
            with self.assertRaisesRegex(backend.StreamNotReady,'Firefox değiştirilmedi'):
                backend.ensure_browser_stream()
        self.assertEqual(run.call_count,1)

    def test_no_source_is_not_success(self):
        responses=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,'Video\n Sources:\n','')]
        with patch.object(backend.subprocess,'run',side_effect=responses),patch.object(backend.time,'monotonic',side_effect=[0,9]):
            with self.assertRaisesRegex(backend.StreamNotReady,'Video / Sources'):
                backend.ensure_browser_stream()

    def test_missing_wpctl_is_not_success(self):
        responses=[subprocess.CompletedProcess([],0,'',''),FileNotFoundError('wpctl missing')]
        with patch.object(backend.subprocess,'run',side_effect=responses):
            with self.assertRaisesRegex(backend.StreamNotReady,'doğrulanamadı'):
                backend.ensure_browser_stream()

    def test_publishing_delay_is_retried_without_restarting_stream(self):
        responses=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,'Video\n Sources:\n',''),subprocess.CompletedProcess([],0,READY,'')]
        with patch.object(backend.subprocess,'run',side_effect=responses) as run,patch.object(backend.time,'sleep'):
            backend.ensure_browser_stream()
        self.assertEqual(run.call_count,3)
        self.assertEqual(sum(call.args[0][0]=='/bin/bash' for call in run.call_args_list),1)


if __name__=='__main__':unittest.main()
