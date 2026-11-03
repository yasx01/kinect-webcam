#!/usr/bin/env python3
"""Inspect Firefox's camera portal decision; offer separately consented repair methods.

No profile/cache access or automatic grant. Browser restart is a separate explicit-consent fallback.
Fedora Firefox RPM app ID: org.mozilla.firefox. No operation targets another app.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import tempfile
import subprocess
import signal
import time

SERVICE = 'org.freedesktop.impl.portal.PermissionStore'
OBJECT = '/org/freedesktop/impl/portal/PermissionStore'
APP_ID = 'org.mozilla.firefox'


def call(method):
    return subprocess.run(['/usr/bin/gdbus', 'call', '--session', '--dest', SERVICE,
                           '--object-path', OBJECT, '--method', SERVICE + '.' + method,
                           'devices', 'camera', APP_ID], capture_output=True, text=True,
                          timeout=6, env=dict(os.environ, LC_ALL='C'))


def permission():
    result = call('GetPermission')
    if result.returncode:
        if 'GDBus.Error:org.freedesktop.portal.Error.NotFound:' in result.stderr:
            return 'unset'
        raise RuntimeError((result.stderr or 'Kamera izin servisine erişilemedi.').strip())
    # GVariant annotates empty arrays as @as []; non-empty string arrays are Python literals.
    text = result.stdout.strip()
    if text == '(@as [],)':
        return 'unset'
    value = ast.literal_eval(text)
    if not isinstance(value, tuple) or len(value) != 1 or not isinstance(value[0], list):
        raise ValueError('Kamera izin yanıtı anlaşılamadı.')
    values = value[0]
    if not values:
        return 'unset'
    if values == ['yes']:
        return 'allowed'
    if values == ['no']:
        return 'denied'
    if values == ['ask']:
        return 'ask'
    raise ValueError('Bilinmeyen kamera izin kararı; değiştirilmedi.')


def firefox_pids():
    result = subprocess.run(['/usr/bin/pgrep', '-u', str(os.getuid()), '-x', 'firefox|firefox-bin'],
                            capture_output=True, text=True, timeout=3)
    if result.returncode not in (0, 1):
        raise RuntimeError('Firefox süreç durumu okunamadı.')
    return [int(line) for line in result.stdout.splitlines() if line.strip()]


def marker_path():
    base = os.environ.get('XDG_RUNTIME_DIR') or os.environ.get('XDG_CACHE_HOME') or str(Path.home()/'.cache')
    return Path(base)/'kinect-facecam'/'firefox-restart.json'


def process_token(pid):
    try:
        # PID plus kernel start time avoids confusing a reused PID with the old browser.
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def pending_restart(pids):
    try:
        records = json.loads(marker_path().read_text())
    except FileNotFoundError:
        return []
    if not isinstance(records, dict):
        raise ValueError('Firefox yeniden açılma bilgisi okunamadı.')
    return [pid for pid in pids if str(pid) in records and process_token(pid) == records[str(pid)]
            and records[str(pid)] is not None]


def remember_restart(pids):
    records = {str(pid): process_token(pid) for pid in pids}
    records = {pid: token for pid, token in records.items() if token is not None}
    if not records:
        return
    path = marker_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix='.restart-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(records, stream)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def inspect():
    status = permission()
    pids = firefox_pids()
    return {'status': status, 'firefox_pids': pids, 'restart_pids': pending_restart(pids), 'changed': False}


def reset_blocking(consent=False):
    if not consent:
        raise RuntimeError('Kullanıcının açık onayı olmadan izin kararı değiştirilmez.')
    before = inspect()
    # Re-read just before removal: never delete a valid allow or already-unset entry.
    if before['status'] not in ('denied', 'ask') or permission() not in ('denied', 'ask'):
        return inspect()
    result = call('DeletePermission')
    if result.returncode:
        raise RuntimeError((result.stderr or 'Kamera kararı sıfırlanamadı.').strip())
    after = inspect()
    after['changed'] = True
    after['previous_firefox_pids'] = sorted(set(before['firefox_pids'] + after['firefox_pids']))
    remember_restart(after['previous_firefox_pids'])
    after['restart_pids'] = pending_restart(after['firefox_pids'])
    if after['status'] != 'unset':
        raise RuntimeError('Kamera kararı yeniden kaydedildi; otomatik tekrar sıfırlanmadı.')
    return after


class StreamNotReady(RuntimeError):
    stage = 'stream'


def has_kinect_video_source(text):
    """Like the original wpctl check, but match only Video / Sources, not another GST client."""
    in_video = in_sources = False
    for line in text.splitlines():
        if line.strip() == 'Video':
            in_video = True
            continue
        if not in_video:
            continue
        if 'Sources:' in line:
            in_sources = True
            continue
        if in_sources and any(name in line for name in ('Filters:', 'Streams:', 'Sinks:', 'Devices:', 'Settings')):
            in_sources = False
        if in_sources and 'Kinect Kamerasi' in line:
            return True
    return False


def ensure_browser_stream():
    """Restore steps 1/2 of the previously working kinect-fix-firefox-camera-v01.sh."""
    starter = Path(__file__).resolve().with_name('kinect-facecam-pw-start-v17')
    try:
        started = subprocess.run(['/bin/bash', str(starter)], capture_output=True, text=True, timeout=12)
        if started.returncode:
            detail = (started.stdout + started.stderr).strip()[-2000:]
            raise StreamNotReady('Tarayıcı kamera akışı başlatılamadı; Firefox değiştirilmedi. ' + detail)
        deadline = time.monotonic() + 8
        while True:
            result = subprocess.run(['/usr/bin/wpctl', 'status'], capture_output=True, text=True,
                                    timeout=3, env=dict(os.environ, LC_ALL='C'))
            if result.returncode == 0 and has_kinect_video_source(result.stdout):
                return
            if time.monotonic() >= deadline:
                raise StreamNotReady('Kinect Kamerasi, PipeWire Video / Sources bölümünde bulunamadı. '
                                     'Firefox değiştirilmedi; Kinect bağlantısını ve akış günlüğünü kontrol et.')
            time.sleep(0.25)
    except (OSError, subprocess.SubprocessError) as exc:
        raise StreamNotReady('Tarayıcı kamera akışı doğrulanamadı; Firefox değiştirilmedi. ' + str(exc)) from exc


def request_firefox_close(pid, token):
    """Use a PID handle, so PID reuse cannot redirect SIGTERM at another process."""
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('Güvenli süreç kapatma desteklenmiyor; Firefox’u kendin kapatıp yeniden denetle.')
    try:
        handle = os.pidfd_open(pid)
    except ProcessLookupError:
        return
    try:
        procdir = Path(f'/proc/{pid}')
        if procdir.stat().st_uid != os.getuid():
            raise RuntimeError('Başka kullanıcıya ait süreç kapatılmadı.')
        if procdir.joinpath('comm').read_text().strip() not in ('firefox', 'firefox-bin'):
            raise RuntimeError('Süreç artık Firefox değil; kapatılmadı.')
        if process_token(pid) != token:
            raise RuntimeError('Firefox süreç kimliği değişti; kapatılmadı.')
        signal.pidfd_send_signal(handle, signal.SIGTERM)
    except (ProcessLookupError, FileNotFoundError):
        pass
    finally:
        os.close(handle)


def restart_firefox(consent=False):
    """Old repair flow as an opt-in fallback; no force kill and no profile reset."""
    if not consent:
        raise RuntimeError('Firefox yeniden açılmadan önce açık kullanıcı onayı gerekir.')
    binary = '/usr/bin/firefox'
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        raise RuntimeError('Fedora Firefox başlatıcısı bulunamadı; Firefox kapatılmadı.')
    ensure_browser_stream()  # The old working repair prepared the camera before touching Firefox.
    before = inspect()  # If the permission service is broken, leave the browser alone.
    changed = False
    if before['status'] != 'unset':
        result = call('DeletePermission')
        if result.returncode:
            raise RuntimeError((result.stderr or 'Kamera kararı silinemedi; Firefox kapatılmadı.').strip())
        changed = True
        if permission() != 'unset':
            raise RuntimeError('İzin sıfırlaması doğrulanamadı; Firefox kapatılmadı.')
    pids = firefox_pids()
    identities = {pid: process_token(pid) for pid in pids}
    if any(token is None for token in identities.values()):
        raise RuntimeError('Firefox süreç kimliği doğrulanamadı; yeniden denetle.')
    remember_restart(pids)
    for pid, token in identities.items():
        request_firefox_close(pid, token)
    deadline = time.monotonic() + 12
    while any(process_token(pid) == token for pid, token in identities.items()):
        if time.monotonic() >= deadline:
            raise RuntimeError('Firefox kapanmadı. Zorla sonlandırılmadı; açık çalışmalarını kontrol edip kendin kapat.')
        time.sleep(0.2)
    if firefox_pids():
        raise RuntimeError('Başka bir Firefox oturumu açıldı; ona dokunulmadı. Yeniden denetle.')
    # The old session may write a decision while shutting down. Recheck once, before relaunching.
    if permission() != 'unset':
        result = call('DeletePermission')
        if result.returncode or permission() != 'unset':
            raise RuntimeError('Firefox kapandı ancak kamera kararı sıfırlanamadı. Firefox’u kendin yeniden açıp denetle.')
        changed = True
    child = subprocess.Popen([binary], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.monotonic() + 6
    while True:
        new_pids = firefox_pids()
        if new_pids:
            break
        if child.poll() not in (None, 0) or time.monotonic() >= deadline:
            raise RuntimeError('Firefox yeniden açıldığı doğrulanamadı; uygulama menüsünden kendin açıp denetle.')
        time.sleep(0.2)
    state = inspect()
    state.update(changed=changed, restarted=True, previous_firefox_pids=pids)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--reset-blocking', action='store_true')
    group.add_argument('--restart-firefox', action='store_true')
    parser.add_argument('--consent', action='store_true')
    args = parser.parse_args()
    try:
        if args.restart_firefox:
            state = restart_firefox(args.consent)
        else:
            state = reset_blocking(args.consent) if args.reset_blocking else inspect()
        print(json.dumps(state, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'error', 'changed': False, 'stage': getattr(exc, 'stage', 'permission'), 'details': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
