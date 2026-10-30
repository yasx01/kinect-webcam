#!/usr/bin/env python3
"""Kinect Webcam v14: sade kurulum denetimi; teknik ayrıntılar isteğe bağlı.
Kamera/mikrofon kontrolü v09 tabanlıdır. Sabit önizleme paneli kaldırılmıştır; isteğe bağlı kare/akış testi korunur.
"""
import datetime
import codecs
import glob
import re
import json
import os
import subprocess
import sys
import time
import shutil
import tempfile

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QProcess
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QTextEdit, QMessageBox, QDialog, QProgressBar, QPlainTextEdit, QScrollArea, QSizePolicy,
)

HOME = os.path.expanduser("~")
# Yardimci betikler bu dosyanin bulundugu klasorde durur. Ileride (v14)
# eklenecek "Ilk kurulum" betigi de buraya konup helper_path() ile bulunabilir.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kinect_facecam_media_v14 as media


def helper_path(name: str) -> str:
    return os.path.join(HERE, name)


# --- Mod tanimlari ---
MODE_OBS = "obs"
MODE_PW = "pw"

MODE_CONFIG = {
    MODE_OBS: {
        "label": "OBS Modu",
        "device_label": "Kinect360 Facecam",
        "start": helper_path("kinect-facecam-start-v14"),
        "stop": helper_path("kinect-facecam-stop-v14"),
        "pidfile": "/tmp/kinect-facecam.pid",
        "logfile": "/tmp/kinect-facecam.log",
        "device": "/dev/video20",
            },
    MODE_PW: {
        "label": "Tarayıcı Modu",
        "device_label": "Kinect Kamerasi",
        "start": helper_path("kinect-facecam-pw-start-v14"),
        "stop": helper_path("kinect-facecam-pw-stop-v14"),
        "pidfile": "/tmp/kinect-facecam-pw.pid",
        "logfile": "/tmp/kinect-facecam-pw.log",
        "device": None,
            },
}

ICON_CANDIDATES = [
    helper_path("kinect-facecam-icon-v14.png"),
    os.path.join(HOME, ".local", "share", "kinect-facecam", "icon.png"),
]

CONFIG_DIR = os.path.join(HOME, ".config", "kinect-facecam")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

WINDOW_SIZE = (820, 630)
WINDOW_MIN_SIZE = (760, 570)

# --- Kinect ses aygiti (USB kimlikleri) ---
KINECT_VENDOR = "045e"
KINECT_AUDIO_RAW = "02ad"   # firmware yuklenmeden onceki "ham" aygit
KINECT_AUDIO_UAC = "02bb"   # firmware yuklendikten sonra: mikrofon

# pactl ciktisi dile gore degisebilir ("Mute: yes"); hep Ingilizce iste.
PACTL_ENV = dict(os.environ, LC_ALL="C")

LIGHT = {
    "bg": "#eef1f6", "card_bg": "#ffffff", "border": "#dfe3ea",
    "fg": "#1a2233", "fg_muted": "#6b7280",
    "accent": "#3b5bfd", "accent_hover": "#2f4de0", "accent_fg": "#ffffff",
    "btn_bg": "#ffffff", "btn_hover": "#f2f4f8", "btn_fg": "#1a2233", "btn_border": "#dfe3ea",
    "log_bg": "#fbfcfe", "log_fg": "#2b3550",
    "dot_on": "#22c55e", "dot_off": "#ef4444", "dot_unknown": "#9ca3af",
    "warn": "#b45309",
}
DARK = {
    "bg": "#12151c", "card_bg": "#1b1f2a", "border": "#2a3040",
    "fg": "#e7ebf3", "fg_muted": "#9aa3b5",
    "accent": "#5b7dff", "accent_hover": "#7691ff", "accent_fg": "#ffffff",
    "btn_bg": "#232838", "btn_hover": "#2b3145", "btn_fg": "#e7ebf3", "btn_border": "#2a3040",
    "log_bg": "#0f1320", "log_fg": "#c7cee0",
    "dot_on": "#22c55e", "dot_off": "#ef4444", "dot_unknown": "#6b7280",
    "warn": "#f59e0b",
}


def load_settings() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f)
    except OSError:
        pass


def is_running(pidfile: str) -> bool:
    if not os.path.exists(pidfile):
        return False
    try:
        with open(pidfile) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
        return False


def log_marker(logfile: str, text: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        with open(logfile, "a") as f:
            f.write(f"[{ts}] {text}\n")
    except OSError:
        pass


# --- Mikrofon yardimcilari ---------------------------------------------
def run_pactl(*args) -> tuple:
    """(cikis_kodu, cikti) dondurur; pactl yoksa (-1, "")."""
    try:
        proc = subprocess.run(["pactl", *args], capture_output=True, text=True,
                              timeout=3, env=PACTL_ENV)
        return proc.returncode, proc.stdout
    except (OSError, subprocess.SubprocessError):
        return -1, ""


def find_kinect_mic() -> tuple:
    """(pactl_var_mi, kaynak_adi_veya_None)."""
    rc, out = run_pactl("list", "short", "sources")
    if rc == -1:
        return False, None
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) > 1 and "Kinect" in parts[1] and not parts[1].endswith(".monitor"):
            return True, parts[1]
    return True, None


def mic_is_muted(source: str):
    """True / False, okunamazsa None."""
    rc, out = run_pactl("get-source-mute", source)
    if rc != 0:
        return None
    return out.strip().lower().endswith("yes")


def kinect_audio_usb_ids() -> set:
    """USB'de gorunen Kinect (045e) urun kimlikleri."""
    ids = set()
    for dev in glob.glob("/sys/bus/usb/devices/*"):
        try:
            with open(os.path.join(dev, "idVendor")) as f:
                if f.read().strip() != KINECT_VENDOR:
                    continue
            with open(os.path.join(dev, "idProduct")) as f:
                ids.add(f.read().strip())
        except OSError:
            continue
    return ids


# ---------------------------------------------------------------------
class ScriptThread(QThread):
    """Betikleri sirayla calistirir; son betigin cikis kodunu ve ciktisini bildirir."""
    done = pyqtSignal(int, str)

    def __init__(self, scripts, timeout=120):
        super().__init__()
        self.scripts = scripts
        self.timeout = timeout   # pkexec sifre penceresi icin bol sure

    def run(self):
        rc, out = -1, ""
        for i, script in enumerate(self.scripts):
            if i:
                time.sleep(1)
            try:
                proc = subprocess.run(["bash", script], capture_output=True,
                                      text=True, timeout=self.timeout)
                rc, out = proc.returncode, (proc.stdout + proc.stderr).strip()
            except (OSError, subprocess.SubprocessError) as e:
                rc, out = -1, str(e)
            if rc != 0:
                break
        self.done.emit(rc, out)


# ---------------------------------------------------------------------
def pill_button(text: str, object_name: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName(object_name)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setMinimumHeight(42)
    return btn


class SetupDialog(QDialog):
    """A short preparation checklist, with optional diagnostics and real phase feedback."""
    CHECKS = (
        ('packages', 'Gerekli uygulamalar'),
        ('microphone', 'Mikrofon hazırlığı'),
        ('camera', 'Kamera erişimi'),
        ('virtual_camera', 'Sanal kamera bağlantısı'),
    )
    PHASES = {
        'packages': (0, '1 / 4 · Gerekli uygulamalar hazırlanıyor'),
        'files': (1, '2 / 4 · Mikrofon ve kamera ayarları yapılıyor'),
        'camera': (2, '3 / 4 · Sanal kamera hazırlanıyor'),
        'verify': (3, '4 / 4 · Son kontroller yapılıyor'),
    }

    def __init__(self, parent, initial_state=None):
        super().__init__(parent)
        self.setObjectName('setupDialog')
        self.setWindowTitle('Kinect Webcam · İlk kurulum')
        self.resize(720, 710)
        self.setMinimumSize(620, 560)
        self._stage = None
        self._install_running = False
        self._dismissed = False
        self._state = None
        self._check_buffer = bytearray()
        self._pending_output = ''
        self._decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self._check_timed_out = False
        self._colors = DARK if getattr(parent, 'dark_mode', False) else LIGHT
        self._build_setup_ui()
        self._apply_setup_theme()
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.completed)
        self.process.errorOccurred.connect(self.process_error)
        self.check_process = QProcess(self)
        self.check_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.check_process.readyReadStandardOutput.connect(self._read_check)
        self.check_process.finished.connect(self._check_completed)
        self.check_process.errorOccurred.connect(self._check_error)
        self.check_timeout = QTimer(self)
        self.check_timeout.setSingleShot(True)
        self.check_timeout.timeout.connect(self._timeout_check)
        if initial_state is not None:
            self.show_state(initial_state)
        else:
            QTimer.singleShot(0, self.refresh_check)

    def _build_setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(self.scroll, 1)
        body = QWidget()
        body.setObjectName('setupBody')
        self.scroll.setWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(10)

        kicker = QLabel('KINECT FACECAM  /  İLK KURULUM')
        kicker.setObjectName('setupKicker')
        layout.addWidget(kicker)
        title = QLabel('Kinect’i kullanıma hazırla')
        title.setObjectName('setupTitle')
        title.setWordWrap(True)
        layout.addWidget(title)
        intro = QLabel('Bir kez hazırlayalım. Sonra kamera ve mikrofonunu ana ekrandan yönetebilirsin.')
        intro.setObjectName('setupMuted')
        intro.setWordWrap(True)
        layout.addWidget(intro)

        summary = QFrame()
        summary.setObjectName('setupSummary')
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(16, 13, 16, 13)
        summary_layout.setSpacing(5)
        self.summary_title = QLabel('Bilgisayarın kontrol ediliyor…')
        self.summary_title.setObjectName('setupSummaryTitle')
        self.summary_title.setWordWrap(True)
        summary_layout.addWidget(self.summary_title)
        self.summary_text = QLabel('Bu kontrol bilgisayarındaki ayarları değiştirmez.')
        self.summary_text.setWordWrap(True)
        self.summary_text.setObjectName('setupMuted')
        summary_layout.addWidget(self.summary_text)
        layout.addWidget(summary)

        self.rows = {}
        for number, (ident, name) in enumerate(self.CHECKS, 1):
            card = QFrame()
            card.setObjectName('setupCard')
            row = QHBoxLayout(card)
            row.setContentsMargins(14, 12, 14, 12)
            row.setSpacing(12)
            marker = QLabel(str(number))
            marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
            marker.setFixedSize(30, 30)
            row.addWidget(marker, 0, Qt.AlignmentFlag.AlignVCenter)
            text = QVBoxLayout()
            text.setSpacing(4)
            heading = QLabel(name)
            heading.setObjectName('setupRowTitle')
            text.addWidget(heading)
            detail = QLabel('Kontrol bekleniyor…')
            detail.setObjectName('setupMuted')
            detail.setWordWrap(True)
            text.addWidget(detail)
            row.addLayout(text, 1)
            badge = QLabel('Bekliyor')
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
            self.rows[ident] = (marker, detail, badge)
            self._row_status(ident, 'unknown', 'Kontrol bekleniyor…')
            layout.addWidget(card)

        self.stage_label = QLabel('')
        self.stage_label.setWordWrap(True)
        self.stage_label.setObjectName('setupMuted')
        layout.addWidget(self.stage_label)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        self.consent = QLabel('Kurulum, eksik bileşenleri ve sistem ayarlarını yönetici onayınla hazırlar. '
                              'İnternet gerekebilir; değişen ayarlar yedeklenir.')
        self.consent.setObjectName('setupMuted')
        self.consent.setWordWrap(True)
        layout.addWidget(self.consent)
        self.details_toggle = QPushButton('Teknik ayrıntıları göster')
        self.details_toggle.setObjectName('setupDetails')
        self.details_toggle.setCheckable(True)
        self.details_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.details_toggle.setMinimumHeight(36)
        self.details_toggle.toggled.connect(self.toggle_details)
        layout.addWidget(self.details_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName('setupLog')
        self.output.document().setMaximumBlockCount(1200)
        self.output.setMinimumHeight(160)
        self.output.setVisible(False)
        self.output.setAccessibleName('Kurulumun teknik ayrıntıları')
        layout.addWidget(self.output)
        layout.addStretch(1)

        footer = QFrame()
        footer.setObjectName('setupFooter')
        buttons = QHBoxLayout(footer)
        buttons.setContentsMargins(24, 16, 24, 16)
        buttons.setSpacing(10)
        outer.addWidget(footer)
        self.close_button = QPushButton('Kapat')
        self.close_button.clicked.connect(self.reject)
        buttons.addWidget(self.close_button)
        self.refresh_button = QPushButton('Yeniden denetle')
        self.refresh_button.clicked.connect(self.refresh_check)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch(1)
        self.install = QPushButton('Kurulumu tamamla')
        self.install.setObjectName('setupPrimary')
        self.install.setEnabled(False)
        self.install.clicked.connect(self.start_install)
        buttons.addWidget(self.install)
        for button in (self.close_button, self.refresh_button, self.install):
            button.setMinimumHeight(44)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAutoDefault(False)

    def _apply_setup_theme(self):
        c = self._colors
        self.setStyleSheet(f'''
            QDialog#setupDialog, QWidget#setupBody {{ background: {c['bg']}; color: {c['fg']}; }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 3px; min-height: 26px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
            QLabel {{ background: transparent; color: {c['fg']}; border: none; font-size: 13px; }}
            QLabel#setupKicker {{ color: {c['fg_muted']}; font-size: 11px; font-weight: 700; }}
            QLabel#setupTitle {{ font-size: 25px; font-weight: 700; }}
            QLabel#setupMuted {{ color: {c['fg_muted']}; font-size: 12px; }}
            QLabel#setupSummaryTitle {{ font-size: 15px; font-weight: 700; }}
            QLabel#setupRowTitle {{ font-size: 13px; font-weight: 600; }}
            QFrame#setupCard {{ background: {c['card_bg']}; border: 1px solid {c['border']}; border-radius: 12px; }}
            QFrame#setupSummary {{ background: {c['btn_bg']}; border: 1px solid {c['border']}; border-radius: 12px; }}
            QFrame#setupFooter {{ background: {c['card_bg']}; border-top: 1px solid {c['border']}; }}
            QPushButton {{ background: {c['btn_bg']}; color: {c['fg']}; border: 1px solid {c['border']};
                           border-radius: 10px; padding: 6px 14px; font-size: 13px; font-weight: 600; }}
            QPushButton:hover {{ background: {c['btn_hover']}; }}
            QPushButton:focus {{ border: 2px solid {c['accent']}; }}
            QPushButton:disabled {{ color: {c['fg_muted']}; }}
            QPushButton#setupPrimary {{ background: {c['accent']}; color: white; border: none; padding: 6px 18px; }}
            QPushButton#setupPrimary:hover {{ background: {c['accent_hover']}; }}
            QPushButton#setupPrimary:focus {{ border: 2px solid {c['fg']}; }}
            QPushButton#setupPrimary:disabled {{ background: {c['border']}; color: {c['fg_muted']}; }}
            QPushButton#setupDetails {{ background: transparent; border: none; color: {c['accent']}; padding: 0; text-align: left; }}
            QPushButton#setupDetails:focus {{ border: 1px solid {c['accent']}; }}
            QPlainTextEdit#setupLog {{ background: {c['log_bg']}; color: {c['log_fg']}; border: 1px solid {c['border']};
                                      border-radius: 8px; font-family: monospace; font-size: 11px; padding: 10px; }}
            QProgressBar {{ border: none; border-radius: 3px; background: {c['border']}; }}
            QProgressBar::chunk {{ background: {c['accent']}; border-radius: 3px; }}
        ''')

    def _row_status(self, ident, status, detail):
        marker, description, badge = self.rows[ident]
        dark = self._colors is DARK
        palette = {
            'ready': ('✓', 'Hazır', '#6ee7b7' if dark else '#166534', '#14362d' if dark else '#dcfce7'),
            'action': ('·', 'Hazırlanacak', '#fcd34d' if dark else '#92400e', '#352b17' if dark else '#fef3c7'),
            'restart': ('↻', 'Yeniden başlat', '#93c5fd' if dark else '#1e40af', '#1d304b' if dark else '#dbeafe'),
            'unknown': ('·', 'Kontrol gerekli', self._colors['fg_muted'], self._colors['btn_bg']),
        }
        symbol, text, fg, bg = palette.get(status, palette['unknown'])
        marker.setText(symbol)
        marker.setStyleSheet(f'background:{bg};color:{fg};border-radius:15px;font-size:19px;font-weight:700;')
        badge.setText(text)
        badge.setStyleSheet(f'background:{bg};color:{fg};border-radius:7px;padding:5px 9px;font-size:11px;font-weight:600;')
        description.setText(detail)

    def toggle_details(self, expanded):
        self.output.setVisible(expanded)
        self.details_toggle.setText('Teknik ayrıntıları gizle' if expanded else 'Teknik ayrıntıları göster')
        if expanded:
            QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(self.output))

    def refresh_check(self):
        if self._dismissed or self._install_running or self.check_process.state() != QProcess.ProcessState.NotRunning:
            return
        self._state = None
        self._check_buffer.clear()
        self._check_timed_out = False
        self.summary_title.setText('Bilgisayarın kontrol ediliyor…')
        self.summary_text.setText('Bu kontrol bilgisayarındaki ayarları değiştirmez.')
        self.stage_label.setText('Hazırlıklar denetleniyor; birazdan sonuçları göreceksin.')
        for ident, _ in self.CHECKS:
            self._row_status(ident, 'unknown', 'Kontrol ediliyor…')
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.install.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.check_timeout.start(30000)
        self.check_process.start('/usr/bin/python3', ['-I', helper_path('kinect-facecam-setup-v14.py'), '--check'])

    def _read_check(self):
        self._check_buffer.extend(bytes(self.check_process.readAllStandardOutput()))

    def _check_completed(self, code, status):
        self._read_check()
        self.check_timeout.stop()
        if self._check_timed_out:
            return
        try:
            state = json.loads(self._check_buffer.decode('utf-8'))
            if status != QProcess.ExitStatus.NormalExit or code not in (0, 1):
                raise ValueError('Denetim beklenmedik biçimde kapandı.')
            if not isinstance(state, dict) or not isinstance(state.get('ready'), bool) or not isinstance(state.get('checks'), list):
                raise ValueError('Denetim sonucu okunamadı.')
            self.show_state(state)
        except (ValueError, UnicodeError, TypeError) as exc:
            self.output.appendPlainText(self._check_buffer.decode('utf-8', errors='replace'))
            self._check_failure(str(exc))

    def _check_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.check_timeout.stop()
            self._check_failure('Denetim başlatılamadı: ' + self.check_process.errorString())

    def _timeout_check(self):
        self._check_timed_out = True
        self.check_process.kill()
        self._check_failure('Denetim beklenenden uzun sürdü. Yeniden deneyebilirsin.')

    def _check_failure(self, reason):
        self.progress.setVisible(False)
        self.refresh_button.setEnabled(True)
        self.install.setEnabled(False)
        self.summary_title.setText('Kontrol tamamlanamadı')
        self.summary_text.setText('Yeniden denetle düğmesiyle tekrar deneyebilirsin.')
        self.stage_label.setText(reason)
        self.output.appendPlainText(reason)

    def show_state(self, state):
        self._state = state
        for ident, _ in self.CHECKS:
            item = next((c for c in state.get('checks', []) if c.get('id') == ident), None)
            self._row_status(ident, item.get('status', 'unknown') if item else 'unknown',
                             item.get('detail', 'Kontrol edilemedi.') if item else 'Kontrol edilemedi.')
        ready = state.get('ready', False)
        pending = [c for c in state.get('checks', []) if c.get('status') != 'ready']
        restart_only = bool(pending) and all(c.get('status') == 'restart' for c in pending)
        self.progress.setVisible(False)
        self.refresh_button.setEnabled(True)
        self.install.setEnabled(not ready and state.get('can_install', False) and not restart_only)
        self.install.setText('Kurulum hazır' if ready else 'Kurulumu tamamla')
        if ready:
            self.summary_title.setText('Sistem hazırlığı tamam')
            self.summary_text.setText('Ek kurulum gerekmiyor. Kamera ve mikrofonu ana ekrandan deneyebilirsin.')
            self.stage_label.setText('Bu, hazırlık kontrolüdür; canlı görüntü testi değildir.')
        elif restart_only:
            self.summary_title.setText('Son bir adım: yeniden başlat')
            self.summary_text.setText('Bilgisayarı yeniden başlatıp bu ekrandan tekrar denetle.')
            self.stage_label.setText('Hazır ayarların yeniden yüklenmesi gerekiyor.')
        elif state.get('can_install', False):
            self.summary_title.setText(f'{len(pending)} hazırlık tamamlanacak')
            self.summary_text.setText('Aşağıdaki eksikleri tek işlemle hazırlayabiliriz.')
            self.stage_label.setText('Hazırsan Kurulumu tamamla düğmesine bas.')
        else:
            self.summary_title.setText('Kurulum şu an başlatılamıyor')
            self.summary_text.setText('Bu sürüm Fedora x86_64 içindir. Paket bütünlüğünün de doğrulanması gerekir.')
            self.stage_label.setText('Ayrıntılar için Teknik ayrıntıları göster düğmesini kullan.')
        issues = state.get('issues', [])
        self.output.appendPlainText('Denetim ayrıntıları:\n' + ('\n'.join(issues) if issues else 'Eksik hazırlık bulunmadı.'))

    def start_install(self):
        if self._install_running or not self.install.isEnabled():
            return
        self.install.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.close_button.setEnabled(False)
        try:
            self._stage = tempfile.TemporaryDirectory(prefix='kinect-facecam-setup-')
            setup_path = os.path.join(self._stage.name, 'kinect-facecam-setup-v14.py')
            shutil.copy2(helper_path('kinect-facecam-setup-v14.py'), setup_path)
            shutil.copytree(helper_path('payload'), os.path.join(self._stage.name, 'payload'))
        except OSError as exc:
            self.cleanup_stage()
            self._install_failure('Kurulum dosyaları hazırlanamadı.', str(exc))
            return
        self._install_running = True
        self._pending_output = ''
        self._decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.summary_title.setText('Yönetici onayı bekleniyor')
        self.summary_text.setText('Açılan sistem penceresinde şifreni gir. İstersen oradan iptal edebilirsin.')
        self.stage_label.setText('Onay alındıktan sonra kurulum başlayacak.')
        self.output.appendPlainText('\nYönetici onayı bekleniyor…')
        self.process.start('/usr/bin/pkexec', ['--disable-internal-agent', '/usr/bin/python3', '-I', '-u', setup_path, '--apply'])

    def cleanup_stage(self):
        if self._stage is not None:
            self._stage.cleanup()
            self._stage = None

    def consume_output(self, text, final=False):
        self._pending_output += text
        lines = self._pending_output.split('\n')
        self._pending_output = lines.pop()
        if final and self._pending_output:
            lines.append(self._pending_output)
            self._pending_output = ''
        for line in lines:
            if line.startswith('KINECT_SETUP_EVENT '):
                try:
                    phase = json.loads(line[len('KINECT_SETUP_EVENT '):]).get('phase')
                    if phase in self.PHASES:
                        step, label = self.PHASES[phase]
                        self.progress.setRange(0, 4)
                        self.progress.setValue(step)
                        self.stage_label.setText(label)
                        self.summary_title.setText('Kurulum sürüyor')
                        self.summary_text.setText('İşlem bitene kadar bu pencereyi açık tut.')
                        continue
                except (ValueError, AttributeError):
                    pass
            self.output.appendPlainText(line)

    def read_output(self):
        self.consume_output(self._decoder.decode(bytes(self.process.readAllStandardOutput())))

    def _install_failure(self, title, detail):
        self._install_running = False
        self.progress.setVisible(False)
        self.summary_title.setText(title)
        self.summary_text.setText('Tekrar deneyebilir veya teknik ayrıntılardan hatayı inceleyebilirsin.')
        self.stage_label.setText('Kurulum tamamlanmadı. Yeniden denetlemek yardımcı olabilir.')
        self.output.appendPlainText(detail)
        self.close_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.install.setText('Tekrar dene')
        self.install.setEnabled(bool(self._state and self._state.get('can_install')))

    def completed(self, code, status):
        self.read_output()
        self.consume_output(self._decoder.decode(b'', final=True), final=True)
        self.cleanup_stage()
        self._install_running = False
        self.close_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        if status == QProcess.ExitStatus.NormalExit and code == 0:
            self.progress.setRange(0, 4)
            self.progress.setValue(4)
            self.summary_title.setText('Sistem hazırlığı tamamlandı')
            self.summary_text.setText('Kinect’i çıkarıp yeniden tak. Sonra ana ekrandan kamerayı başlatıp mikrofonu dene.')
            self.stage_label.setText('Kurulum bitti. Kamera ve sesin gerçek çalışmasını ayrıca kontrol et.')
            for ident, _ in self.CHECKS:
                self._row_status(ident, 'ready', 'Hazırlık tamamlandı.')
            self.install.setText('Tamamlandı')
            self.install.setEnabled(False)
        elif status == QProcess.ExitStatus.NormalExit and code in (126, 127):
            self._install_failure('Kurulum iptal edildi', 'Yönetici onayı alınamadı; kurulum tamamlanmadı.')
        elif status == QProcess.ExitStatus.NormalExit and code == 3:
            self._install_failure('Yeniden kontrol gerekiyor', 'Ayarlar henüz hazır değil. Yeniden denetle; gerekirse bilgisayarı yeniden başlat.')
        else:
            self._install_failure('Kurulum tamamlanamadı', f'Kurulum çıkış kodu: {code}')

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.cleanup_stage()
            self._install_failure('Kurulum başlatılamadı', self.process.errorString())

    def reject(self):
        if self._install_running:
            return
        self._dismissed = True
        self.check_timeout.stop()
        if self.check_process.state() != QProcess.ProcessState.NotRunning:
            self.check_process.kill()
            self.check_process.waitForFinished(1000)
        super().reject()

    def closeEvent(self, event):
        if self._install_running:
            event.ignore()
        else:
            self.reject()
            event.accept()


class CameraTestDialog(QDialog):
    """Read the existing stream, never open a second libfreenect camera client."""
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = dict(cfg)
        self.setWindowTitle('Kinect Webcam · Kamera testi')
        self.resize(660, 240)
        self._closed = False
        self._started = False
        self._timed_out = False
        self.succeeded = False
        self._temp = tempfile.TemporaryDirectory(prefix='kinect-camera-test-')
        self.image_path = os.path.join(self._temp.name, 'frame.png')
        c = DARK if getattr(parent, 'dark_mode', False) else LIGHT
        self.setStyleSheet(f'''QDialog {{background:{c['bg']};color:{c['fg']};}}
            QLabel {{background:transparent;color:{c['fg']};font-size:13px;}}
            QPushButton {{background:{c['btn_bg']};color:{c['fg']};border:1px solid {c['border']};
            border-radius:10px;padding:10px 18px;min-height:24px;}}
            QPushButton:focus {{border:2px solid {c['accent']};}}''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.title = QLabel('Kamera kontrol ediliyor…')
        self.title.setStyleSheet('font-size:19px;font-weight:700;')
        layout.addWidget(self.title)
        self.description = QLabel('')
        self.description.setWordWrap(True)
        layout.addWidget(self.description)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        layout.addWidget(self.progress)
        self.frame = QLabel()
        self.frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame.setVisible(False)
        layout.addWidget(self.frame)
        self.close_button = QPushButton('Kapat')
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button, 0, Qt.AlignmentFlag.AlignRight)
        self.capture = QProcess(self)
        self.capture.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.capture.finished.connect(self._capture_finished)
        self.capture.errorOccurred.connect(self._capture_error)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self._capture_timeout)
        self.poll = QTimer(self)
        self.poll.setInterval(250)
        self.poll.timeout.connect(self._poll_frames)
        QTimer.singleShot(0, self.start_test)

    def start_test(self):
        if self._closed or self._started:
            return
        self._started = True
        if not is_running(self.cfg['pidfile']):
            self._finish(False, 'Önce kamerayı başlat', 'Ana ekrandaki Başlat düğmesine basıp tekrar dene.')
            return
        if self.cfg['device']:
            self.description.setText('OBS çıkışından yeni bir kare alınıyor. Bu işlem kamera akışını durdurmaz.')
            self.timeout.start(10000)
            self.capture.start('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y',
                               '-f', 'v4l2', '-i', self.cfg['device'], '-frames:v', '1', self.image_path])
        else:
            self.description.setText('Yeni kare aktarımı bekleniyor; bu kontrol en fazla 10 saniye sürer.')
            self._initial_frames = self._frame_count()
            self._deadline = time.monotonic() + 10
            self.poll.start()

    def _frame_count(self):
        try:
            with open(self.cfg['logfile'], 'rb') as stream:
                stream.seek(0, os.SEEK_END)
                stream.seek(max(0, stream.tell() - 65536))
                text = stream.read().decode('utf-8', errors='replace')
            counts = re.findall(r'\[calisiyor\]\s+(\d+) kare aktarildi\.', text)
            return int(counts[-1]) if counts else 0
        except OSError:
            return 0

    def _poll_frames(self):
        if self._closed:
            return
        if not is_running(self.cfg['pidfile']):
            self._finish(False, 'Kamera akışı durdu', 'Ana ekrandaki günlükten hatayı inceleyip kamerayı yeniden başlat.')
            return
        current = self._frame_count()
        if current > 0 and current != self._initial_frames:
            self._finish(True, 'Yeni kare aktarımı doğrulandı',
                         'Köprü yeni kareleri PipeWire’a aktarıyor. Görüntüyü ve kamera iznini Firefox/Meet içinde ayrıca kontrol et.')
        elif time.monotonic() >= self._deadline:
            self._finish(False, 'Yeni kare aktarımı doğrulanamadı',
                         'Bu sürede kare sayacı değişmedi. Ana ekrandaki günlükten bağlantıyı kontrol et.')

    def _capture_finished(self, code, status):
        if self._closed:
            return
        self.timeout.stop()
        pixmap = QPixmap(self.image_path)
        if not self._timed_out and status == QProcess.ExitStatus.NormalExit and code == 0 and not pixmap.isNull():
            self.frame.setPixmap(pixmap.scaled(620, 380, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))
            self.frame.setVisible(True)
            self.resize(680, 560)
            self._finish(True, 'Kare başarıyla alındı', 'Bu, OBS sanal kamera çıkışından şimdi alınan bir karedir; canlı önizleme değildir.')
        else:
            detail = '10 saniye içinde kare alınamadı.' if self._timed_out else 'OBS çıkışından geçerli görüntü alınamadı. Günlüğü ve cihazı kontrol et.'
            self._finish(False, 'Kare alınamadı', detail)

    def _capture_error(self, error):
        if not self._closed and error == QProcess.ProcessError.FailedToStart:
            self._finish(False, 'Kare testi başlatılamadı', 'FFmpeg bulunamadı veya çalıştırılamadı. İlk Kurulum / Denetle bölümünü kontrol et.')

    def _capture_timeout(self):
        self._timed_out = True
        self.capture.kill()

    def _finish(self, success, title, detail):
        self.succeeded = success
        self.poll.stop()
        self.timeout.stop()
        self.progress.setVisible(False)
        self.title.setText(title)
        self.description.setText(detail)

    def reject(self):
        self._closed = True
        self.poll.stop()
        self.timeout.stop()
        if self.capture.state() != QProcess.ProcessState.NotRunning:
            self.capture.kill()
            self.capture.waitForFinished(1000)
        self._temp.cleanup()
        super().reject()

    def closeEvent(self, event):
        self.reject()
        event.accept()


class BrowserPermissionDialog(QDialog):
    """Detect stale portal refusals before use. No silent allow, reset or browser restart."""
    def __init__(self, parent, for_start=False, initial_state=None):
        super().__init__(parent)
        self.for_start = for_start
        self.last_state = None
        self._operation = 'check'
        self._closed = False
        self._blocked_pids = set(getattr(parent, "_firefox_restart_pids", set()))
        self._buffer = bytearray()
        self._timed_out = False
        self.setWindowTitle('Kinect Webcam · Firefox kamera izni')
        self.resize(700, 410)
        c = DARK if getattr(parent, 'dark_mode', False) else LIGHT
        self.setStyleSheet(f'''QDialog {{background:{c['bg']};color:{c['fg']};}}
            QLabel {{background:transparent;color:{c['fg']};font-size:13px;}}
            QPushButton {{background:{c['btn_bg']};color:{c['fg']};border:1px solid {c['border']};
                border-radius:10px;padding:10px 14px;min-height:24px;}}
            QPushButton:disabled {{color:{c['fg_muted']};}}
            QPushButton:focus {{border:2px solid {c['accent']};}}
            QPlainTextEdit {{background:{c['log_bg']};color:{c['fg']};border:1px solid {c['border']};}}''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.title = QLabel('Firefox kamera izni kontrol ediliyor…')
        self.title.setStyleSheet('font-size:19px;font-weight:700;')
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.message = QLabel('Bu kontrol Firefox ayarlarını değiştirmez.')
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.hint = QLabel('')
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(f'color:{c["fg_muted"]};font-size:12px;')
        layout.addWidget(self.hint)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        layout.addWidget(self.progress)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(100)
        self.details.setVisible(False)
        layout.addWidget(self.details)
        self.reset = QPushButton('Ret kararını kaldır')
        self.reset.setEnabled(False)
        self.reset.clicked.connect(self.confirm_reset)
        layout.addWidget(self.reset, 0, Qt.AlignmentFlag.AlignLeft)
        self.restart_browser = QPushButton('Olmazsa: Firefox’u yeniden açarak düzelt')
        self.restart_browser.setEnabled(False)
        self.restart_browser.clicked.connect(self.confirm_restart)
        layout.addWidget(self.restart_browser, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.close_button = QPushButton('Vazgeç' if for_start else 'Kapat')
        self.close_button.clicked.connect(self.reject)
        row.addWidget(self.close_button)
        self.refresh = QPushButton('Yeniden denetle')
        self.refresh.clicked.connect(self.run_check)
        row.addWidget(self.refresh)
        row.addStretch(1)
        self.proceed = QPushButton('Kamerayı başlat')
        self.proceed.setVisible(for_start)
        self.proceed.setEnabled(False)
        self.proceed.clicked.connect(self.accept)
        row.addWidget(self.proceed)
        for button in (self.reset, self.restart_browser, self.refresh, self.close_button, self.proceed):
            button.setAutoDefault(False)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._error)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self._timeout)
        if initial_state is not None:
            self.show_state(initial_state)
        else:
            QTimer.singleShot(0, self.run_check)

    def run_check(self):
        self._run('check')

    def _run(self, operation):
        if self._closed or self.process.state() != QProcess.ProcessState.NotRunning:
            return
        self._operation = operation
        self._buffer.clear()
        self._timed_out = False
        self.progress.setVisible(True)
        self.reset.setEnabled(False)
        self.restart_browser.setEnabled(False)
        self.refresh.setEnabled(False)
        self.proceed.setEnabled(False)
        self.close_button.setEnabled(operation not in ('reset', 'restart'))
        args = ['/usr/bin/python3', '-I', helper_path('kinect-facecam-firefox-permission-v14.py')]
        if operation == 'restart':
            args += ['--restart-firefox', '--consent']
        elif operation == 'reset':
            args += ['--reset-blocking', '--consent']
        else:
            args += ['--check']
        self.timeout.start(120000 if operation == 'restart' else 25000)
        self.process.start(args[0], args[1:])

    def _read(self):
        self._buffer.extend(bytes(self.process.readAllStandardOutput()))

    def _finished(self, code, status):
        self._read()
        self.timeout.stop()
        if self._closed or self._timed_out:
            return
        try:
            state = json.loads(self._buffer.decode('utf-8'))
            if not isinstance(state, dict) or state.get('status') not in ('allowed', 'unset', 'denied', 'ask', 'error'):
                raise ValueError('İzin servisi sonucu anlaşılamadı.')
            if status != QProcess.ExitStatus.NormalExit or (code != 0 and state['status'] != 'error'):
                raise ValueError('İzin denetimi tamamlanamadı.')
        except (ValueError, UnicodeError) as exc:
            state = {'status': 'error', 'details': str(exc)}
        if state.get('changed'):
            self._blocked_pids.update(state.get('previous_firefox_pids', []))
        self.show_state(state)
        if (self.for_start and self.proceed.isEnabled() and state['status'] in ('allowed', 'unset')
                and not self._blocked_pids and self._operation != 'restart'):
            self.accept()

    def show_state(self, state):
        self.last_state = state
        self.progress.setVisible(False)
        self.refresh.setEnabled(True)
        self.close_button.setEnabled(True)
        self.reset.setEnabled(state['status'] in ('denied', 'ask'))
        self.restart_browser.setEnabled(True)
        if state['status'] != 'error':
            self._blocked_pids.update(state.get('restart_pids', []))
            self._blocked_pids.intersection_update(state.get('firefox_pids', []))
        self.parent()._firefox_restart_pids = set(self._blocked_pids)
        restart = bool(self._blocked_pids)
        status = state['status']
        self.proceed.setEnabled(status in ('allowed', 'unset', 'error') and not restart)
        self.proceed.setText('Yine de başlat' if status == 'error' else 'Kamerayı başlat')
        self.details.setVisible(status == 'error')
        self.details.setPlainText(state.get('details', ''))
        if state.get('restarted') and not restart and status in ('allowed', 'unset'):
            self.title.setText('Firefox yeniden açıldı; kamera kararını yeniden verebilirsin')
            self.message.setText('Kamera izin kaydı yenilendi. Akış kapalıysa önce kamerayı başlat; sonra Meet sayfasını yenile ve izin penceresini kontrol et.')
            self.hint.setText('Profil, geçmiş ve çerezler silinmedi. Görüntünün geldiğini Meet içinde ayrıca doğrula.')
        elif restart:
            self.title.setText('Eski karar kaldırıldı; Firefox’u yeniden aç')
            self.message.setText('Firefox eski ret kararını açık oturumunda tutabilir. Önce çalışmalarını kaydet, '
                                 'Firefox’u tamamen kapatıp yeniden aç; sonra Yeniden denetle’ye bas.')
            self.hint.setText('İlk yöntem Firefox’u kapatmaz. İstersen aşağıdaki onaylı yeniden açma yöntemini kullanabilirsin.')
        elif status == 'allowed':
            self.title.setText('Firefox’un sistem kamera erişimi açık')
            self.message.setText('Kayıtlı bir sistem reddi bulunmadı. Meet içindeki site iznini ve Kinect Kamerasi seçimini ayrıca kontrol et.')
            self.hint.setText('Bu denetim canlı görüntünün tarayıcıya ulaştığını kanıtlamaz.')
        elif status == 'unset':
            self.title.setText('Yeni kamera isteği için izin bekleniyor')
            self.message.setText('Kayıtlı bir sistem kararı yok. Firefox kamerayı istediğinde sistem izin sorabilir; kararı sen vereceksin.')
            self.hint.setText('Meet kamera isteğinde bulunduğunda izin penceresini kontrol et. Otomatik izin verilmedi.')
        elif status in ('denied', 'ask'):
            self.title.setText('Firefox’un kayıtlı kamera kararı erişimi engelleyebilir')
            self.message.setText('Kamera takılı olsa bile Meet bu yüzden “Kamera bulunamadı” diyebilir. '
                                 'İstersen bu eski sistem kararını kaldırıp yeniden sorulmasını sağlayabilirsin.')
            self.hint.setText('Yalnızca Firefox’un kamera kararı değişir. Geçmiş, çerezler, mikrofon ve diğer uygulamalar korunur.')
        else:
            if state.get('stage') == 'stream':
                self.title.setText('Önce Kinect tarayıcı akışı hazırlanmalı')
                self.message.setText('Kamera kaynağı doğrulanamadığı için Firefox’a dokunulmadı. USB/güç bağlantısını, seçili modu ve akış günlüğünü kontrol et.')
            else:
                self.title.setText('Firefox kamera izni denetlenemedi')
                self.message.setText('İzin durumu doğrulanamadı. Bu durum, Kinect’in takılı olmadığı anlamına gelmez.')
            self.hint.setText('Durum doğrulanamadı; ayrıntıyı inceleyip yeniden denetle. '
                              'Yine de başlatırsan Firefox izni doğrulanmış sayılmaz.')

    def confirm_reset(self):
        if not self.last_state or self.last_state['status'] not in ('denied', 'ask'):
            return
        answer = QMessageBox.question(
            self, 'Firefox’un eski kamera kararını kaldır',
            'Bu işlem yalnızca Firefox için saklanan sistem kamera kararını siler; '
            'tüm kameralar için geçerli bu karar Kinect’e özel değildir.\n\n'
            'Otomatik izin vermez. Sonraki kamera isteğinde kararı yeniden sen verirsin. '
            'Firefox geçmişi, çerezler, mikrofon izni ve diğer uygulamaların izinleri silinmez.\n\n'
            'Firefox açıksa onu kendin tamamen kapatıp yeniden açman gerekebilir.\n\nDevam edilsin mi?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self._run('reset')

    def confirm_restart(self):
        answer = QMessageBox.question(
            self, 'Firefox kapatılıp yeniden açılacak',
            'Bu ikinci yöntem önce Kinect tarayıcı akışını başlatır ve kamera kaynağını doğrular. '
            'Sonra eski sürümlerdeki onarımı uygular: kamera izin kaydını sıfırlar, '
            'bu kullanıcıya ait TÜM Firefox pencerelerini kapatır ve Firefox’u yeniden açar.\n\n'
            'Açık görüşme kesilir; kaydedilmemiş yazılar kaybolabilir. Önce çalışmalarını kaydet. '
            'Geçmiş, çerezler, parolalar ve Firefox profili silinmez. Sekmelerin geri gelmesi '
            'Firefox’un oturum ayarlarına bağlıdır.\n\n'
            'Önceden verilmiş kamera izni de yeniden sorulmak üzere kaldırılabilir; otomatik izin verilmez.\n\n'
            'Devam edilsin mi?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self._run('restart')

    def _error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.timeout.stop()
            self.show_state({'status': 'error', 'details': self.process.errorString()})

    def _timeout(self):
        self._timed_out = True
        self.process.kill()
        self.show_state({'status': 'error', 'details': 'İzin denetimi zaman aşımına uğradı. İzin durumunu yeniden denetle.'})

    def reject(self):
        if self._operation in ('reset', 'restart') and self.process.state() != QProcess.ProcessState.NotRunning:
            return
        self._closed = True
        self.timeout.stop()
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
        super().reject()

    def closeEvent(self, event):
        if self._operation in ('reset', 'restart') and self.process.state() != QProcess.ProcessState.NotRunning:
            event.ignore()
        else:
            self.reject()
            event.accept()


class MediaTestDialog(QDialog):
    """Live camera preview + opt-in mic meter and a temporary five-second recording."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Kinect Webcam · Kamera ve mikrofon testi')
        self.resize(920, 600)
        self.setMinimumSize(760, 560)
        self._closing = False
        self._pixmap = None
        self._frame_key = None
        self._recording = False
        self._record_buffer = bytearray()
        self._pcm_pending = b''
        self._record_peak = 0
        self._temp = tempfile.TemporaryDirectory(prefix='kinect-webcam-audio-test-')
        self.clip_path = os.path.join(self._temp.name, 'microphone-test.wav')
        c = DARK if getattr(parent, 'dark_mode', False) else LIGHT
        self.setStyleSheet(f'''QDialog {{background:{c['bg']};color:{c['fg']};}}
            QLabel {{background:transparent;color:{c['fg']};font-size:13px;}}
            QFrame#mediaCard {{background:{c['card_bg']};border:1px solid {c['border']};border-radius:14px;}}
            QLabel#mediaHeading {{font-size:16px;font-weight:700;}}
            QPushButton {{background:{c['btn_bg']};color:{c['fg']};border:1px solid {c['border']};border-radius:10px;
                         padding:8px 12px;min-height:28px;font-size:12px;}}
            QPushButton:hover {{background:{c['btn_hover']};}}
            QPushButton:disabled {{color:{c['fg_muted']};}}
            QPushButton:focus {{border:2px solid {c['accent']};}}
            QProgressBar {{background:{c['border']};border:none;border-radius:6px;min-height:14px;text-align:center;}}
            QProgressBar::chunk {{background:{c['dot_on']};border-radius:6px;}}''')
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)
        title = QLabel('Kameranı gör, mikrofonunu dinle')
        title.setStyleSheet('font-size:23px;font-weight:700;')
        root.addWidget(title)
        subtitle = QLabel('Kamera önizlemesi mevcut akışı kullanır. Mikrofon yalnızca sen başlatınca dinlenir.')
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)
        columns = QHBoxLayout()
        columns.setSpacing(14)
        root.addLayout(columns, 1)
        camera = QFrame(); camera.setObjectName('mediaCard')
        camera_layout = QVBoxLayout(camera)
        camera_layout.setContentsMargins(16, 16, 16, 16)
        camera_layout.setSpacing(12)
        columns.addWidget(camera, 3)
        camera_title = QLabel('Canlı kamera'); camera_title.setObjectName('mediaHeading')
        camera_layout.addWidget(camera_title)
        self.image = QLabel('Kamerayı Başlat ile aç.\nGörüntü burada görünecek.')
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumSize(280, 150)
        self.image.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.image.setStyleSheet('background:#080c12;color:#9aa3b5;border-radius:10px;')
        camera_layout.addWidget(self.image, 1)
        self.camera_status = QLabel('Kamera durumu kontrol ediliyor…')
        self.camera_status.setWordWrap(True)
        camera_layout.addWidget(self.camera_status)
        camera_buttons = QHBoxLayout()
        self.camera_start = QPushButton('Kamerayı başlat')
        self.camera_start.clicked.connect(self.start_camera)
        camera_buttons.addWidget(self.camera_start)
        self.camera_stop = QPushButton('Durdur')
        self.camera_stop.clicked.connect(parent.stop_stream)
        camera_buttons.addWidget(self.camera_stop)
        camera_layout.addLayout(camera_buttons)
        self.output_test = QPushButton('Görüntü çıkışını da test et')
        self.output_test.clicked.connect(lambda: CameraTestDialog(parent, parent.cfg).exec())
        camera_layout.addWidget(self.output_test)
        mic = QFrame(); mic.setObjectName('mediaCard')
        mic_layout = QVBoxLayout(mic)
        mic_layout.setContentsMargins(16, 16, 16, 16)
        mic_layout.setSpacing(12)
        columns.addWidget(mic, 2)
        mic_title = QLabel('Mikrofon testi'); mic_title.setObjectName('mediaHeading')
        mic_layout.addWidget(mic_title)
        self.audio_status = QLabel('Mikrofon kapalı. Testi başlatınca yalnızca Kinect ses kaynağı kullanılır.')
        self.audio_status.setWordWrap(True)
        mic_layout.addWidget(self.audio_status)
        self.level = QProgressBar(); self.level.setRange(0, 100); self.level.setValue(0)
        mic_layout.addWidget(self.level)
        self.mic_test = QPushButton('Mikrofonu test et')
        self.mic_test.clicked.connect(self.toggle_microphone)
        mic_layout.addWidget(self.mic_test)
        self.record_button = QPushButton('5 saniye ses kaydet')
        self.record_button.clicked.connect(self.record_clip)
        mic_layout.addWidget(self.record_button)
        self.record_status = QLabel('Kısa bir cümle söyle; ardından kaydı dinle.')
        self.record_status.setWordWrap(True)
        mic_layout.addWidget(self.record_status)
        self.play_button = QPushButton('Kaydı dinle'); self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_clip)
        mic_layout.addWidget(self.play_button)
        self.stop_audio_button = QPushButton('Ses testini durdur')
        self.stop_audio_button.clicked.connect(self.stop_audio)
        mic_layout.addWidget(self.stop_audio_button)
        privacy = QLabel('Kayıt yalnızca bu bilgisayarda geçici tutulur. Pencere kapanınca silinir; internete gönderilmez.')
        privacy.setWordWrap(True)
        privacy.setStyleSheet(f'color:{c["fg_muted"]};font-size:12px;')
        mic_layout.addWidget(privacy)
        mic_layout.addStretch(1)
        footer = QHBoxLayout()
        note = QLabel('Pencere kapanınca ses testi durur. Kamera akışı, Durdur’a basana kadar sürer.')
        note.setWordWrap(True)
        note.setStyleSheet(f'color:{c["fg_muted"]};font-size:12px;')
        footer.addWidget(note, 1)
        close = QPushButton('Kapat'); close.clicked.connect(self.reject)
        footer.addWidget(close)
        root.addLayout(footer)
        self.mic_process = QProcess(self)
        self.mic_process.readyReadStandardOutput.connect(self.read_audio)
        self.mic_process.finished.connect(self.microphone_finished)
        self.mic_process.errorOccurred.connect(self.microphone_error)
        self.player = QProcess(self)
        self.player.finished.connect(self.playback_finished)
        self.player.errorOccurred.connect(self.playback_error)
        self.record_timeout = QTimer(self); self.record_timeout.setSingleShot(True)
        self.record_timeout.timeout.connect(self.record_failed)
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.refresh_camera)
        self.preview_timer.start(250)
        self.refresh_camera()

    def refresh_camera(self):
        if self._closing:
            return
        parent = self.parent()
        running = is_running(parent.cfg['pidfile'])
        self.camera_stop.setEnabled(running)
        self.camera_start.setText('Yeniden başlat' if running else 'Kamerayı başlat')
        try:
            with open(parent.cfg['pidfile']) as stream:
                pid = int(stream.read().strip())
        except (OSError, ValueError):
            pid = -1
        snapshot = media.read_snapshot(parent.mode, pid) if running else None
        if snapshot:
            payload, meta = snapshot
            key = (meta['owner'], meta['sequence'])
            if key != self._frame_key:
                pixmap = QPixmap()
                if pixmap.loadFromData(payload, 'JPEG'):
                    self._pixmap, self._frame_key = pixmap, key
                    self._show_image()
                    self.camera_status.setText(parent.cfg['label'] + ' · Canlı önizleme (yaklaşık 2 güncelleme/sn)')
                    return
            elif self._pixmap:
                self._show_image()
                return
        self._pixmap, self._frame_key = None, None
        self.image.setPixmap(QPixmap())
        self.image.setText('Henüz güncel görüntü yok.\nKamerayı başlat veya eski akışı yeniden başlat.')
        self.camera_status.setText('Akış çalışıyor fakat güncel v14 önizlemesi yok.' if running else 'Kamera akışı kapalı.')

    def _show_image(self):
        if self._pixmap:
            self.image.setPixmap(self._pixmap.scaled(self.image.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                    Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._show_image)

    def start_camera(self):
        parent = self.parent()
        if is_running(parent.cfg['pidfile']):
            answer = QMessageBox.question(self, 'Kamera akışı yeniden başlayacak',
                'Yeniden başlatma kamerayı kullanan bir görüşmeyi kısa süre kesebilir. Devam edilsin mi?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer == QMessageBox.StandardButton.Yes:
                parent.restart_stream()
        else:
            parent.start_stream()

    @staticmethod
    def stop_process(process):
        if process.state() != QProcess.ProcessState.NotRunning:
            process.terminate()
            if not process.waitForFinished(1000):
                process.kill(); process.waitForFinished(1000)

    def start_microphone(self):
        if self._closing:
            return False
        if self.mic_process.state() != QProcess.ProcessState.NotRunning:
            return True
        self.stop_process(self.player)
        ok, source = find_kinect_mic()
        if not ok or not source:
            self.audio_status.setText('Kinect mikrofonu bulunamadı. Başka bir mikrofon kullanılmadı; İlk Kurulum / Denetle bölümünü kontrol et.')
            return False
        if mic_is_muted(source) is True:
            self.audio_status.setText('Kinect mikrofonu sistemde sessizde. Ana ekrandaki Sesi Aç düğmesini kullan; test bunu kendiliğinden değiştirmez.')
            return False
        self._pcm_pending = b''
        self.audio_status.setText('Kinect mikrofonu dinleniyor · yalnızca seviye ölçümü; henüz kayıt yok.')
        self.mic_test.setText('Mikrofon testini durdur')
        self.mic_process.start('ffmpeg', ['-hide_banner','-loglevel','error','-f','pulse','-i',source,
                                        '-ac','1','-ar',str(media.RATE),'-f','s16le','pipe:1'])
        return True

    def toggle_microphone(self):
        if self.mic_process.state() == QProcess.ProcessState.NotRunning:
            self.start_microphone()
        else:
            self.stop_audio()

    def record_clip(self):
        if self._recording:
            return
        self.stop_audio()
        if not self.start_microphone():
            return
        self._recording = True
        self._record_buffer.clear(); self._record_peak = 0
        try:
            os.unlink(self.clip_path)
        except FileNotFoundError:
            pass
        self.record_button.setEnabled(False); self.play_button.setEnabled(False)
        self.record_status.setText('Kaydediliyor… 0 / 5 saniye')
        self.audio_status.setText('Kinect mikrofonundan kısa kayıt alınıyor.')
        self.record_timeout.start(10000)

    def read_audio(self):
        data = self._pcm_pending + bytes(self.mic_process.readAllStandardOutput())
        self._pcm_pending = data[len(data)//2*2:]
        data = data[:len(data)//2*2]
        if not data or self._closing:
            return
        value, db = media.audio_level(data)
        self.level.setValue(value)
        if self._recording:
            remaining = media.RECORD_BYTES - len(self._record_buffer)
            record_data = data[:remaining]
            self._record_peak = max(self._record_peak, media.audio_level(record_data)[0])
            self._record_buffer.extend(record_data)
            seconds = len(self._record_buffer)/(media.RATE*media.SAMPLE_WIDTH)
            self.record_status.setText(f'Kaydediliyor… {seconds:.1f} / 5 saniye')
            if len(self._record_buffer) == media.RECORD_BYTES:
                self.record_timeout.stop(); self._recording = False
                try:
                    media.write_clip(self.clip_path, self._record_buffer)
                    self.play_button.setEnabled(True)
                    self.record_status.setText('5 saniyelik kayıt hazır.' if self._record_peak else 'Kayıt hazır fakat ses seviyesi algılanmadı.')
                except (OSError, ValueError) as exc:
                    self.record_status.setText('Kayıt yazılamadı: ' + str(exc))
                self._record_buffer.clear()
                self.record_button.setEnabled(True)
                self.audio_status.setText('Kinect mikrofonu dinleniyor · seviye ölçümü sürüyor.')

    def record_failed(self):
        self.stop_audio()
        self.record_status.setText('Yeterli ses verisi gelmedi; beş saniyelik kayıt tamamlanamadı.')

    def stop_audio(self):
        if self._recording:
            self.record_status.setText('Kayıt tamamlanmadan durduruldu; eksik kayıt saklanmadı.')
        self._recording = False
        self.record_timeout.stop(); self._record_buffer.clear()
        self.stop_process(self.mic_process); self.stop_process(self.player)
        self.level.setValue(0)
        self.mic_test.setText('Mikrofonu test et')
        self.record_button.setEnabled(True)
        if not self._closing:
            self.audio_status.setText('Ses testi durduruldu.')

    def play_clip(self):
        if not os.path.isfile(self.clip_path):
            return
        self.stop_audio()
        self.play_button.setEnabled(False); self.record_button.setEnabled(False)
        self.audio_status.setText('Geçici kayıt çalınıyor. Mikrofon dinlemesi kapalı.')
        self.player.start('pw-play', ['--volume','0.6',self.clip_path])

    def microphone_finished(self, code, status):
        if self._closing:
            return
        if self._recording:
            self.record_failed()
        self.level.setValue(0)
        self.mic_test.setText('Mikrofonu test et')
        if code != 0 and self.mic_process.error() != QProcess.ProcessError.Crashed:
            self.audio_status.setText('Mikrofon akışı durdu. Kinect bağlantısını ve ses sistemini kontrol et.')

    def microphone_error(self, error):
        if not self._closing and error == QProcess.ProcessError.FailedToStart:
            self.record_failed()
            self.audio_status.setText('FFmpeg ses testi başlatılamadı. İlk Kurulum / Denetle bölümünü kontrol et.')

    def playback_finished(self, code, status):
        if self._closing:
            return
        self.play_button.setEnabled(os.path.isfile(self.clip_path)); self.record_button.setEnabled(True)
        self.audio_status.setText('Kayıt dinlendi.' if code == 0 and status == QProcess.ExitStatus.NormalExit else 'Kayıt çalınamadı; ses çıkışını kontrol et.')

    def playback_error(self, error):
        if not self._closing and error == QProcess.ProcessError.FailedToStart:
            self.audio_status.setText('pw-play bulunamadı; pipewire-utils paketi gerekli.')
            self.play_button.setEnabled(True); self.record_button.setEnabled(True)

    def reject(self):
        if self._closing:
            return
        self._closing = True
        self.preview_timer.stop(); self.stop_audio()
        self._temp.cleanup()
        super().reject()

    def closeEvent(self, event):
        self.reject(); event.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kinect Webcam v14")
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*WINDOW_MIN_SIZE)

        settings = load_settings()
        self.dark_mode = bool(settings.get("dark_mode", False))
        self.mode = settings.get("mode", MODE_OBS)
        if self.mode not in MODE_CONFIG:
            self.mode = MODE_OBS

        self._threads = []
        self._mic_source = None

        for icon_path in ICON_CANDIDATES:
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                break

        self._build_ui()
        self.apply_theme()
        self._apply_mode_ui()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(2000)
        self.refresh_status()

        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.refresh_log)
        self.log_timer.start(1500)
        self.refresh_log()

    # ------------------------------------------------------------------
    @property
    def cfg(self):
        return MODE_CONFIG[self.mode]

    @property
    def other_mode(self):
        return MODE_PW if self.mode == MODE_OBS else MODE_OBS

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralPanel")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # --- Ust satir ---
        top_row = QHBoxLayout()
        root.addLayout(top_row)

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(16, 16)
        top_row.addWidget(self.status_dot)

        self.status_label = QLabel("Kontrol ediliyor...")
        self.status_label.setObjectName("statusLabel")
        top_row.addWidget(self.status_label)

        top_row.addStretch(1)

        self.theme_btn = pill_button("🌙  Koyu Tema", "pill")
        self.theme_btn.clicked.connect(self.toggle_theme)
        top_row.addWidget(self.theme_btn)

        self.home_btn = pill_button("🖥  Ana Ekran", "pill")
        self.home_btn.clicked.connect(self.go_home)
        top_row.addWidget(self.home_btn)

        self.setup_btn = pill_button("İlk Kurulum / Denetle", "primaryPill")
        self.setup_btn.setAccessibleName("Kamera ve mikrofon ilk kurulumu")
        self.setup_btn.clicked.connect(self.open_setup)
        root.addWidget(self.setup_btn)

        # --- Mod secim karti ---
        mode_card = QFrame()
        mode_card.setObjectName("card")
        mode_layout = QHBoxLayout(mode_card)
        mode_layout.setContentsMargins(16, 14, 16, 14)
        mode_layout.setSpacing(10)
        root.addWidget(mode_card)

        mode_title = QLabel("Mod:")
        mode_title.setObjectName("cardTitle")
        mode_layout.addWidget(mode_title)

        self.mode_obs_btn = pill_button("📺  OBS Modu", "modePill")
        self.mode_obs_btn.clicked.connect(lambda: self.set_mode(MODE_OBS))
        mode_layout.addWidget(self.mode_obs_btn)

        self.mode_pw_btn = pill_button("🌐  Tarayıcı Modu", "modePill")
        self.mode_pw_btn.clicked.connect(lambda: self.set_mode(MODE_PW))
        mode_layout.addWidget(self.mode_pw_btn)

        mode_layout.addStretch(1)

        self.firefox_fix_btn = pill_button("Firefox İznini Denetle", "pill")
        self.firefox_fix_btn.clicked.connect(self.fix_firefox_camera)
        mode_layout.addWidget(self.firefox_fix_btn)

        # --- Buton karti ---
        btn_card = QFrame()
        btn_card.setObjectName("card")
        btn_card_layout = QHBoxLayout(btn_card)
        btn_card_layout.setContentsMargins(16, 16, 16, 16)
        btn_card_layout.setSpacing(10)
        root.addWidget(btn_card)

        self.start_btn = pill_button("▶  Başlat", "primaryPill")
        self.start_btn.clicked.connect(self.start_stream)
        btn_card_layout.addWidget(self.start_btn)

        self.stop_btn = pill_button("■  Durdur", "pill")
        self.stop_btn.clicked.connect(self.stop_stream)
        btn_card_layout.addWidget(self.stop_btn)

        self.restart_btn = pill_button("⟳  Yeniden Başlat", "pill")
        self.restart_btn.clicked.connect(self.restart_stream)
        btn_card_layout.addWidget(self.restart_btn)

        self.preview_btn = pill_button("Kamera / Mikrofon Testi", "pill")
        self.preview_btn.setToolTip("Canlı kamera önizlemesi, mikrofon seviye göstergesi ve geçici ses kaydı testi.")
        self.preview_btn.clicked.connect(self.capture_preview)
        btn_card_layout.addWidget(self.preview_btn)

        # --- Mikrofon karti ---
        mic_card = QFrame()
        mic_card.setObjectName("card")
        mic_layout = QVBoxLayout(mic_card)
        mic_layout.setContentsMargins(16, 14, 16, 14)
        mic_layout.setSpacing(6)
        root.addWidget(mic_card)

        mic_row = QHBoxLayout()
        mic_row.setSpacing(10)
        mic_layout.addLayout(mic_row)

        mic_title = QLabel("🎤  Mikrofon:")
        mic_title.setObjectName("cardTitle")
        mic_row.addWidget(mic_title)

        self.mic_dot = QLabel()
        self.mic_dot.setFixedSize(12, 12)
        mic_row.addWidget(self.mic_dot)

        self.mic_label = QLabel("Kontrol ediliyor...")
        mic_row.addWidget(self.mic_label)

        mic_row.addStretch(1)

        self.mic_btn = pill_button("🔇  Sessize Al", "pill")
        self.mic_btn.clicked.connect(self.toggle_mic)
        mic_row.addWidget(self.mic_btn)

        self.mic_warning = QLabel()
        self.mic_warning.setWordWrap(True)
        self.mic_warning.setVisible(False)
        mic_layout.addWidget(self.mic_warning)

        self.browser_hint = QLabel("Firefox’un kayıtlı kamera kararı Başlat’a basıldığında denetlenir.")
        self.browser_hint.setWordWrap(True)
        root.addWidget(self.browser_hint)

        # --- Log karti ---
        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 14, 16, 16)
        log_layout.setSpacing(8)
        root.addWidget(log_card, 1)

        self.log_title = QLabel("📄  Log")
        self.log_title.setObjectName("cardTitle")
        log_layout.addWidget(self.log_title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setObjectName("logArea")
        self.log_text.setFontFamily("Monospace")
        log_layout.addWidget(self.log_text, 1)

    # ------------------------------------------------------------------
    def set_mode(self, mode: str):
        if mode == self.mode:
            return
        self.mode = mode
        save_settings({"dark_mode": self.dark_mode, "mode": self.mode})
        self._apply_mode_ui()
        self.refresh_status()
        self.refresh_log()
        self.go_home()

    def _apply_mode_ui(self):
        c = DARK if self.dark_mode else LIGHT
        active_style = (
            f"background-color: {c['accent']}; color: {c['accent_fg']}; "
            f"border: none; border-radius: 18px; padding: 8px 16px; font-weight:700;"
        )
        inactive_style = (
            f"background-color: {c['btn_bg']}; color: {c['btn_fg']}; "
            f"border: 1px solid {c['btn_border']}; border-radius: 18px; "
            f"padding: 8px 16px; font-weight:600;"
        )
        self.mode_obs_btn.setStyleSheet(active_style if self.mode == MODE_OBS else inactive_style)
        self.mode_pw_btn.setStyleSheet(active_style if self.mode == MODE_PW else inactive_style)

        self.firefox_fix_btn.setVisible(self.mode == MODE_PW)
        self.browser_hint.setVisible(self.mode == MODE_PW)

    # ------------------------------------------------------------------
    def go_home(self):
        self.showNormal()
        self.resize(*WINDOW_SIZE)
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------------
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        save_settings({"dark_mode": self.dark_mode, "mode": self.mode})
        self.apply_theme()
        self._apply_mode_ui()
        self.refresh_status()

    def apply_theme(self):
        c = DARK if self.dark_mode else LIGHT
        self.theme_btn.setText("☀  Açık Tema" if self.dark_mode else "🌙  Koyu Tema")

        qss = f"""
        QMainWindow {{
            background-color: {c['bg']};
            color: {c['fg']};
            font-family: Sans;
        }}
        QLabel {{
            background: transparent;
            color: {c['fg']};
        }}
        QWidget#centralPanel {{
            background-color: {c['bg']};
            color: {c['fg']};
            font-family: Sans;
        }}
        QPushButton:focus {{
            border: 2px solid {c['accent']};
        }}
        QLabel#statusLabel {{
            font-size: 17px;
            font-weight: 700;
            color: {c['fg']};
        }}
        QFrame#card {{
            background-color: {c['card_bg']};
            border: 1px solid {c['border']};
            border-radius: 16px;
        }}
        QLabel#cardTitle {{
            font-size: 13px;
            font-weight: 700;
            color: {c['fg']};
        }}
        QTextEdit#logArea {{
            background-color: {c['log_bg']};
            color: {c['log_fg']};
            border: none;
            border-radius: 10px;
            font-size: 12px;
            padding: 8px;
        }}
        QPushButton#pill {{
            background-color: {c['btn_bg']};
            color: {c['btn_fg']};
            border: 1px solid {c['btn_border']};
            border-radius: 21px;
            padding: 8px 18px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton#pill:hover {{
            background-color: {c['btn_hover']};
        }}
        QPushButton#pill:disabled {{
            color: {c['fg_muted']};
        }}
        QPushButton#primaryPill {{
            background-color: {c['accent']};
            color: {c['accent_fg']};
            border: none;
            border-radius: 21px;
            padding: 8px 22px;
            font-size: 13px;
            font-weight: 700;
        }}
        QPushButton#primaryPill:hover {{
            background-color: {c['accent_hover']};
        }}
        QPushButton#primaryPill:disabled {{
            background-color: {c['btn_border']};
            color: {c['fg_muted']};
        }}
        """
        self.setStyleSheet(qss)
        self.mic_warning.setStyleSheet(f"color: {c['warn']}; font-size: 12px;")
        self.browser_hint.setStyleSheet(f"color: {c['fg_muted']}; font-size: 12px;")

        dot_color = c["dot_on"] if is_running(self.cfg["pidfile"]) else c["dot_off"]
        self.status_dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 8px;")

    # ------------------------------------------------------------------
    def _run_scripts(self, scripts, btn: QPushButton, action: str):
        btn.setEnabled(False)
        t = ScriptThread(scripts)
        t.done.connect(lambda rc, out: self._after_action(btn, action, rc, out))
        self._threads.append(t)
        t.start()

    def capture_preview(self):
        dialog = getattr(self, '_media_dialog', None)
        if dialog is not None and dialog.isVisible():
            dialog.raise_(); dialog.activateWindow()
            return
        self._media_dialog = MediaTestDialog(self)
        self._media_dialog.show()

    def closeEvent(self, event):
        dialog = getattr(self, '_media_dialog', None)
        if dialog is not None:
            dialog.reject()
        super().closeEvent(event)

    def open_setup(self):
        SetupDialog(self).exec()
        self.refresh_status()

    def start_stream(self):
        if self.mode == MODE_PW and not self._firefox_permission(for_start=True):
            return
        if is_running(self.cfg["pidfile"]):
            QMessageBox.information(self, "Bilgi", "Zaten çalışıyor.")
            return

        other = MODE_CONFIG[self.other_mode]
        if is_running(other["pidfile"]):
            answer = QMessageBox.question(
                self, "Diğer mod çalışıyor",
                f"{other['label']} şu an çalışıyor. Kinect aynı anda yalnızca "
                f"bir moda hizmet verebilir.\n\n"
                f"{other['label']} durdurulup {self.cfg['label']} başlatılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            log_marker(self.cfg["logfile"], f"GUI: {other['label']} durdurulup başlatılıyor.")
            self.status_label.setText("Mod değiştiriliyor...")
            self._run_scripts([other["stop"], self.cfg["start"]], self.start_btn, "Başlatma")
            return

        log_marker(self.cfg["logfile"], "GUI: Başlat butonuna basıldı.")
        self.status_label.setText("Başlatılıyor...")
        self._run_scripts([self.cfg["start"]], self.start_btn, "Başlatma")

    def stop_stream(self):
        log_marker(self.cfg["logfile"], "GUI: Durdur butonuna basıldı.")
        self.status_label.setText("Durduruluyor...")
        self._run_scripts([self.cfg["stop"]], self.stop_btn, "Durdurma")

    def restart_stream(self):
        if self.mode == MODE_PW and not self._firefox_permission(for_start=True):
            return
        log_marker(self.cfg["logfile"], "GUI: Yeniden Başlat butonuna basıldı.")
        self.status_label.setText("Yeniden başlatılıyor...")
        self._run_scripts([self.cfg["stop"], self.cfg["start"]], self.restart_btn, "Yeniden başlatma")

    def _after_action(self, btn: QPushButton, action: str, rc: int, out: str):
        btn.setEnabled(True)
        self.refresh_status()
        if rc != 0:
            log_marker(self.cfg["logfile"], f"GUI: {action} başarısız: {out}")
            QMessageBox.warning(self, f"{action} başarısız",
                                out or "Bilinmeyen hata. Ayrıntı için log'a bak.")

    # ------------------------------------------------------------------
    def _firefox_permission(self, for_start=False):
        dialog = BrowserPermissionDialog(self, for_start=for_start)
        result = dialog.exec()
        self.browser_hint.setText(dialog.title.text())
        return result == QDialog.DialogCode.Accepted

    def fix_firefox_camera(self):
        self._firefox_permission()

    # ------------------------------------------------------------------
    def toggle_mic(self):
        if not self._mic_source:
            return
        rc, _out = run_pactl("set-source-mute", self._mic_source, "toggle")
        if rc != 0:
            QMessageBox.warning(self, "Mikrofon", "Mikrofon durumu değiştirilemedi.")
        muted = mic_is_muted(self._mic_source)
        if muted is not None:
            log_marker(self.cfg["logfile"],
                       "GUI: Mikrofon sessize alındı." if muted else "GUI: Mikrofon açıldı.")
        self.refresh_mic()

    def refresh_mic(self):
        c = DARK if self.dark_mode else LIGHT
        pactl_ok, source = find_kinect_mic()
        self._mic_source = source
        warning = ""

        if not pactl_ok:
            dot, text = c["dot_unknown"], "Kontrol edilemiyor"
            warning = "'pactl' komutu bulunamadı (pulseaudio-utils paketi gerekli)."
        elif source:
            muted = mic_is_muted(source)
            if muted is None:
                dot, text = c["dot_unknown"], "Bağlı · durum okunamadı"
            elif muted:
                dot, text = c["dot_off"], "Bağlı · Sessizde"
            else:
                dot, text = c["dot_on"], "Bağlı · Açık"
            self.mic_btn.setText("🎤  Sesi Aç" if muted else "🔇  Sessize Al")
        else:
            dot, text = c["dot_unknown"], "Bulunamadı"
            ids = kinect_audio_usb_ids()
            if KINECT_AUDIO_RAW in ids and KINECT_AUDIO_UAC not in ids:
                warning = ("Kinect bağlı ama ses firmware'i yüklenmemiş. Kinect'i çıkarıp "
                           "tekrar takmayı dene; düzelmezse firmware kurulumu gerekir "
                           "(İlk Kurulum / Denetle düğmesini kullan).")
            elif KINECT_AUDIO_UAC in ids:
                warning = "Kinect mikrofonu USB'de görünüyor ama ses sisteminde (PipeWire) yok."
            else:
                warning = "Kinect ses aygıtı bulunamadı. USB ve güç adaptörü takılı mı?"

        self.mic_btn.setEnabled(bool(source))
        self.mic_dot.setStyleSheet(f"background-color: {dot}; border-radius: 6px;")
        self.mic_label.setText(text)
        self.mic_warning.setText(warning)
        self.mic_warning.setVisible(bool(warning))

    # ------------------------------------------------------------------
    def refresh_status(self):
        c = DARK if self.dark_mode else LIGHT
        running = is_running(self.cfg["pidfile"])
        dot_color = c["dot_on"] if running else c["dot_off"]
        self.status_dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 8px;")
        mode_label = self.cfg["label"]
        state_label = "Çalışıyor" if running else "Durduruldu"
        text = f"{state_label}  ·  {mode_label}"
        other = MODE_CONFIG[self.other_mode]
        if not running and is_running(other["pidfile"]):
            text += f"  ({other['label']} çalışıyor)"
        self.status_label.setText(text)
        self.refresh_mic()

    def refresh_log(self):
        logfile = self.cfg["logfile"]
        content = ""
        if os.path.exists(logfile):
            try:
                with open(logfile, errors="replace") as f:
                    lines = f.readlines()[-200:]
                content = "".join(lines)
            except OSError:
                content = "(log dosyası okunamadı)"
        else:
            content = "(henüz log yok)"

        if self.log_text.toPlainText() != content.rstrip("\n"):
            scrollbar = self.log_text.verticalScrollBar()
            at_bottom = scrollbar.value() >= scrollbar.maximum() - 4
            self.log_text.setPlainText(content)
            if at_bottom:
                scrollbar.setValue(scrollbar.maximum())

    # ------------------------------------------------------------------


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("kinect-facecam")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
