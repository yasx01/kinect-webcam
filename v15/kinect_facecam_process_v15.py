"""Identify our own camera bridge before status checks or signalling it."""
import os
from pathlib import Path
import re
import select
import signal
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kinect_facecam_media_v15 import process_token

PROC_ROOT = Path('/proc')


def instance(pidfile, mode):
    try:
        path = Path(pidfile)
        if path.is_symlink() or path.stat().st_uid != os.getuid():
            return None
        pid = int(path.read_text().strip())
        if pid <= 1:
            return None
        proc = PROC_ROOT/str(pid)
        if proc.stat().st_uid != os.getuid():
            return None
        prefix = 'kinect-facecam-bridge-pipewire' if mode == 'pw' else 'kinect-facecam-bridge'
        pattern = re.compile(re.escape(prefix) + r'(?:-v[0-9]+)?\.py')
        args = (proc/'cmdline').read_bytes().split(b'\0')
        if not any(pattern.fullmatch(os.fsdecode(arg).rsplit('/', 1)[-1]) for arg in args[1:]):
            return None
        token = process_token(pid)
        return (pid, token) if token is not None else None
    except (OSError, ValueError):
        return None


def stop(pidfile, mode):
    target = instance(pidfile, mode)
    if target:
        pid, token = target
        try:
            fd = os.pidfd_open(pid)
        except ProcessLookupError:
            fd = None
        if fd is not None:
            try:
                if instance(pidfile, mode) != target:
                    raise RuntimeError('Kamera süreci değişti; durdurma iptal edildi.')
                watcher = select.poll()
                watcher.register(fd, select.POLLIN)
                signal.pidfd_send_signal(fd, signal.SIGTERM)
                if not watcher.poll(3000):
                    signal.pidfd_send_signal(fd, signal.SIGKILL)
                    if not watcher.poll(2000):
                        raise RuntimeError('Kamera süreci kapanmadı; tekrar denetle.')
            except ProcessLookupError:
                pass
            finally:
                os.close(fd)
    path = Path(pidfile)
    if not path.is_symlink() and path.exists() and path.stat().st_uid == os.getuid():
        # Do not remove the pidfile of a newly started replacement bridge.
        current = instance(pidfile, mode)
        if current is None or current == target:
            path.unlink(missing_ok=True)
    print('Kinect akışı durduruldu.' if target else 'Çalışan Kinect akışı yok.')


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] not in ('check', 'stop') or sys.argv[3] not in ('obs', 'pw'):
        raise SystemExit(2)
    operation, pidfile, mode = sys.argv[1:]
    try:
        if operation == 'check':
            raise SystemExit(0 if instance(pidfile, mode) else 1)
        stop(pidfile, mode)
    except (OSError, RuntimeError) as exc:
        print('İşlem tamamlanamadı: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
