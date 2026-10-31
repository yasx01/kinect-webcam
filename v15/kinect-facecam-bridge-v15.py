#!/usr/bin/env python3
"""
Kinect 360'in RGB kamerasini /dev/video20 sanal kamera aygitina aktarir.
(v15: Kinect cikarilirsa/kare gelmezse CPU'yu kilitleyen siki dongu yerine
kisa bekleme; 10 sn boyunca hic kare gelmezse hata mesajiyla cikar.)
"""
import signal
import subprocess
import sys
import time
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kinect_facecam_media_v15 import SnapshotWriter

import freenect

WIDTH = 640
HEIGHT = 480
FPS = 30
DEVICE = "/dev/video20"
HEARTBEAT_SECONDS = 5
NO_FRAME_WAIT = 0.1          # kare gelmezse bu kadar bekle (sn)
NO_FRAME_GIVE_UP = 10        # bu kadar sn hic kare gelmezse cik

ffmpeg_cmd = [
    "ffmpeg", "-hide_banner", "-loglevel", "warning", "-y",
    "-f", "rawvideo", "-pixel_format", "rgb24",
    "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(FPS),
    "-i", "-",
    "-pix_fmt", "yuyv422",
    "-f", "v4l2", DEVICE,
]

print(f"Kinect -> {DEVICE} akisi baslatiliyor... (durdurmak icin Ctrl+C)", flush=True)

proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
running = True
exit_code = 0


def _stop(*_args):
    global running
    running = False


signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)

preview = SnapshotWriter("obs")
frame_count = 0
last_heartbeat = time.monotonic()
last_frame = time.monotonic()

try:
    while running:
        result = freenect.sync_get_video()
        frame = None if result is None else result[0]
        if frame is None:
            if time.monotonic() - last_frame >= NO_FRAME_GIVE_UP:
                print(f"HATA: {NO_FRAME_GIVE_UP} sn boyunca Kinect'ten kare gelmedi. "
                      "Kinect bagli ve adaptoru takili mi?", file=sys.stderr, flush=True)
                exit_code = 1
                break
            time.sleep(NO_FRAME_WAIT)
            continue
        preview.publish(frame)
        last_frame = time.monotonic()
        try:
            proc.stdin.write(frame.tobytes())
        except BrokenPipeError:
            print("ffmpeg beklenmedik sekilde kapandi.", file=sys.stderr, flush=True)
            exit_code = 1
            break

        frame_count += 1
        now = time.monotonic()
        if now - last_heartbeat >= HEARTBEAT_SECONDS:
            print(f"[calisiyor] {frame_count} kare aktarildi.", flush=True)
            last_heartbeat = now
finally:
    preview.close()
    try:
        freenect.sync_stop()
    finally:
        if proc.stdin:
            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    print("Durduruldu.", flush=True)

sys.exit(exit_code)
