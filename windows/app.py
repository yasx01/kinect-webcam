"""Kinect Webcam for Windows 10 1809+ x64. No driver changes on launch."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import resources, microphone_endpoint, atomic_write
from PyQt6.QtCore import Qt, QTimer, QProcess, QUrl
from PyQt6.QtGui import QPixmap, QDesktopServices, QIcon
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
    QPushButton,QCheckBox,QDialog,QMessageBox,QFileDialog,QProgressBar,QPlainTextEdit,QScrollArea,QFrame)


class Setup(QDialog):
    def __init__(self,parent):
        super().__init__(parent);self.setWindowTitle('İlk kurulum');self.resize(540,440)
        layout=QVBoxLayout(self)
        heading=QLabel('Kinect’i Windows’a hazırla');heading.setStyleSheet('font-size:21px;font-weight:700');layout.addWidget(heading)
        for text in ['1. Kinect’in güç adaptörünü ve USB kablosunu bağla.',
                     '2. Zadig ile yalnızca Xbox NUI Camera (045e:02ae/02bf) için libusbK kur. Başka aygıt seçme.',
                     '3. Tarayıcı çıkışı için OBS Studio’yu kur. OBS’nin kendi Sanal Kamerayı Başlat düğmesini aynı anda kullanma.',
                     '4. Mikrofon görünmüyorsa kendi UACFirmware dosyanla ses hazırlığını yap. Ham ses aygıtı 045e:02ad için libusbK gerekebilir. Firmware sonrası 045e:02bb üzerinde Windows USB Audio sürücüsünü koru.']:
            label=QLabel(text);label.setWordWrap(True);layout.addWidget(label)
        row=QHBoxLayout();layout.addLayout(row)
        for title,url in [('Zadig','https://zadig.akeo.ie/'),('OBS Studio','https://obsproject.com/download')]:
            button=QPushButton(title);button.clicked.connect(lambda _,u=url:QDesktopServices.openUrl(QUrl(u)));row.addWidget(button)
        self.firmware=QPushButton('Yerel ses firmware’ini yükle…');self.firmware.clicked.connect(self.start_upload);layout.addWidget(self.firmware)
        self.status=QLabel('Uygulama sürücüleri otomatik değiştirmez. Microsoft firmware’i bu pakette bulunmaz.');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.close_button=QPushButton('Kapat');self.close_button.clicked.connect(self.accept);layout.addWidget(self.close_button)
        self.process=QProcess(self);self.process.finished.connect(self.completed);self.process.errorOccurred.connect(self.error)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.timeout)
        self.result_temp=None

    def start_upload(self):
        if self.parent().worker.state()!=QProcess.ProcessState.NotRunning:
            self.status.setText('Önce kamera akışını durdur.');return
        path,_=QFileDialog.getOpenFileName(self,'UACFirmware dosyasını seç')
        if not path:return
        from firmware import validate
        try:validate(path)
        except (OSError,ValueError) as exc:self.status.setText(str(exc));return
        if QMessageBox.question(self,'Kinect sesini hazırla','Seçtiğin dosya Kinect ses aygıtına aktarılacak. Sürücü değiştirilmeyecek. Devam edilsin mi?')!=QMessageBox.StandardButton.Yes:return
        self.result_temp=tempfile.TemporaryDirectory(prefix='kinect-fw-result-')
        command,args=child_command('--upload-firmware',path,'--result',str(Path(self.result_temp.name)/'result.json'))
        self.process.start(command,args);self.timer.start(65000)
        self.firmware.setEnabled(False);self.close_button.setEnabled(False);self.status.setText('Ses hazırlanıyor…')

    def completed(self,code,status):
        self.timer.stop();self.firmware.setEnabled(True);self.close_button.setEnabled(True)
        try:
            value=json.loads((Path(self.result_temp.name)/'result.json').read_text(encoding='utf-8'))
            self.status.setText(value['message'])
        except (OSError,ValueError,TypeError,KeyError,AttributeError):self.status.setText('Ses hazırlığı tamamlanamadı. Kinect bağlantısını denetle.')
        if self.result_temp:self.result_temp.cleanup();self.result_temp=None
        self.parent().refresh_mic()

    def error(self,error):
        if error==QProcess.ProcessError.FailedToStart:self.completed(1,QProcess.ExitStatus.CrashExit)

    def timeout(self):
        self.process.kill();self.status.setText('Ses hazırlığı zaman aşımına uğradı.')

    def reject(self):
        if self.process.state()!=QProcess.ProcessState.NotRunning:return
        super().reject()

    def closeEvent(self,event):
        if self.process.state()!=QProcess.ProcessState.NotRunning:event.ignore()
        else:event.accept()


def child_command(*args):
    if getattr(sys,'frozen',False):return sys.executable,list(args)
    return sys.executable,[str(Path(__file__).resolve()),*args]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('Kinect Webcam · Windows v0.2.0');self.resize(760,720);self.setMinimumSize(720,640)
        icon=resources()/'kinect-facecam-icon-v15.png'
        if not icon.is_file():icon=Path(__file__).resolve().parents[1]/'v15/kinect-facecam-icon-v15.png'
        self.setWindowIcon(QIcon(str(icon)))
        self.temp=tempfile.TemporaryDirectory(prefix='kinect-webcam-camera-')
        self.folder=Path(self.temp.name);self.frozen=False;self.pixmap=None;self.key=None;self.mic_dialog=None
        self.started=0;self.last_frame=0;self.user_stop=False
        self.worker=QProcess(self);self.worker.finished.connect(self.finished);self.worker.errorOccurred.connect(self.worker_error)
        self.dark_mode=True
        content=QWidget();content.setObjectName('centralPanel')
        root=QVBoxLayout(content);root.setContentsMargins(20,14,20,14);root.setSpacing(10)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setWidget(content);self.setCentralWidget(scroll)
        header=QHBoxLayout();root.addLayout(header)
        self.status=QLabel('Durduruldu');self.status.setObjectName('statusLabel');self.status.setWordWrap(True);header.addWidget(self.status,1)
        self.theme_button=QPushButton('Açık Tema');self.theme_button.clicked.connect(self.toggle_theme);header.addWidget(self.theme_button)
        setup=QPushButton('İlk kurulum');setup.clicked.connect(lambda:Setup(self).exec());header.addWidget(setup)
        mode_card=QFrame();mode_card.setObjectName('card');mode=QHBoxLayout(mode_card);mode.setContentsMargins(14,10,14,10);root.addWidget(mode_card)
        mode.addWidget(QLabel('Mod:'))
        self.virtual=QCheckBox('Tarayıcıya aktar · OBS Virtual Camera');self.virtual.setChecked(True);mode.addWidget(self.virtual,1)
        controls_card=QFrame();controls_card.setObjectName('card');controls=QHBoxLayout(controls_card);controls.setContentsMargins(14,10,14,10);controls.setSpacing(10);root.addWidget(controls_card)
        self.start_button=QPushButton('Başlat');self.start_button.setObjectName('primary');self.start_button.clicked.connect(self.start);controls.addWidget(self.start_button,1)
        self.stop_button=QPushButton('Durdur');self.stop_button.setEnabled(False);self.stop_button.clicked.connect(self.stop);controls.addWidget(self.stop_button,1)
        self.restart_button=QPushButton('Yeniden Başlat');self.restart_button.clicked.connect(self.restart);controls.addWidget(self.restart_button,1)
        self.test_button=QPushButton('Kare Al / Test Et');self.test_button.clicked.connect(self.freeze_frame);controls.addWidget(self.test_button,1)
        mic_card=QFrame();mic_card.setObjectName('card');mic=QHBoxLayout(mic_card);mic.setContentsMargins(14,10,14,10);root.addWidget(mic_card)
        self.mic_status=QLabel('Mikrofon kontrol ediliyor…');self.mic_status.setWordWrap(True);mic.addWidget(self.mic_status,1)
        self.mute=QPushButton('Sessize al');self.mute.clicked.connect(self.toggle_mic);mic.addWidget(self.mute)
        audio=QPushButton('Mikrofon testi');audio.clicked.connect(self.audio_test);mic.addWidget(audio)
        preview=QFrame();preview.setObjectName('card');preview_layout=QVBoxLayout(preview);preview_layout.setContentsMargins(14,10,14,10);root.addWidget(preview,1)
        preview_header=QHBoxLayout();preview_layout.addLayout(preview_header)
        self.frame_status=QLabel('Son alınan kare · canlı önizleme');preview_header.addWidget(self.frame_status,1)
        self.live_button=QPushButton('Canlıya dön');self.live_button.setEnabled(False);self.live_button.clicked.connect(self.resume);preview_header.addWidget(self.live_button)
        self.image=QLabel('Henüz kare alınmadı. Kamerayı başlat.');self.image.setObjectName('preview');self.image.setAlignment(Qt.AlignmentFlag.AlignCenter);self.image.setMinimumHeight(150);preview_layout.addWidget(self.image,1)
        hint=QLabel('Görüşme sitesinde OBS Virtual Camera ve Kinect mikrofonunu seç.');hint.setWordWrap(True);root.addWidget(hint)
        log_card=QFrame();log_card.setObjectName('card');logs=QVBoxLayout(log_card);logs.setContentsMargins(14,10,14,10);root.addWidget(log_card)
        self.details_button=QPushButton('Günlük');self.details_button.setCheckable(True);self.details_button.setChecked(True);logs.addWidget(self.details_button)
        self.details=QPlainTextEdit();self.details.setObjectName('logArea');self.details.setReadOnly(True);self.details.setMaximumBlockCount(300);self.details.setMaximumHeight(72);self.details.setPlainText('Hazır. Kamerayı Başlat ile aç.');logs.addWidget(self.details)
        self.details_button.toggled.connect(self.details.setVisible)
        self.apply_theme()
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(250)
        self.mic_timer=QTimer(self);self.mic_timer.timeout.connect(self.refresh_mic);self.mic_timer.start(4000)
        self.refresh_mic()

    def toggle_theme(self):
        self.dark_mode=not self.dark_mode;self.apply_theme()

    def apply_theme(self):
        bg,card,button,fg,border,log=('#11141b','#1c202b','#242938','#e7ebf3','#2a3040','#0f1320') if self.dark_mode else ('#eef1f6','#ffffff','#f2f4f8','#1a2233','#dfe3ea','#fbfcfe')
        self.theme_button.setText('Açık Tema' if self.dark_mode else 'Koyu Tema')
        self.setStyleSheet(f'''QMainWindow,QDialog,QScrollArea,QWidget#centralPanel{{background:{bg};color:{fg};}}
            QWidget{{color:{fg};font-family:"Segoe UI","Noto Sans",sans-serif;font-size:13px;}}
            QLabel,QCheckBox{{background:transparent;}}
            QLabel#statusLabel{{font-size:16px;font-weight:700;}}
            QFrame#card{{background:{card};border:1px solid {border};border-radius:16px;}}
            QPushButton{{background:{button};border:1px solid {border};border-radius:21px;padding:7px 12px;min-height:26px;}}
            QPushButton:hover{{border-color:#7892ff;}} QPushButton:disabled{{color:#8b94a6;}}
            QPushButton:focus{{border:2px solid #7892ff;}}
            QPushButton#primary{{background:#5b79ff;color:white;font-weight:700;}}
            QPushButton#primary:disabled{{background:{button};color:#8b94a6;}}
            QLabel#preview{{background:#000000;color:#aeb7c8;border-radius:10px;}}
            QPlainTextEdit{{background:{log};border:1px solid {border};border-radius:10px;padding:8px;}}
            QCheckBox{{padding:8px 0;}}
            QProgressBar{{background:{button};border:none;min-height:14px;border-radius:6px;}}
            QProgressBar::chunk{{background:#28c880;border-radius:6px;}}''')

    def restart(self):
        self.stop();self.start()

    def start(self):
        if self.worker.state()!=QProcess.ProcessState.NotRunning:return
        for name in ['frame.jpg','state.json','stop']:(self.folder/name).unlink(missing_ok=True)
        self.resume();self.started=time.monotonic();self.last_frame=self.started;self.user_stop=False
        command,args=child_command('--camera-worker',str(self.folder),*(['--virtual'] if self.virtual.isChecked() else []))
        self.worker.start(command,args);self.start_button.setEnabled(False);self.stop_button.setEnabled(True);self.virtual.setEnabled(False)
        self.status.setText('Kinect’e bağlanılıyor…');self.details.appendPlainText('Kamera başlatılıyor…')

    def stop(self):
        self.user_stop=True
        if self.worker.state()!=QProcess.ProcessState.NotRunning:
            (self.folder/'stop').touch()
            if not self.worker.waitForFinished(1500):self.worker.kill();self.worker.waitForFinished(1500)
        self.status.setText('Durduruldu');self.start_button.setEnabled(True);self.stop_button.setEnabled(False);self.virtual.setEnabled(True)
        self.details.appendPlainText('Kamera durduruldu.')
        if not self.frozen:self.clear_frame()

    def clear_frame(self):
        self.pixmap=None;self.key=None;self.image.setPixmap(QPixmap());self.image.setText('Güncel görüntü yok. Kamerayı başlat.')

    def refresh(self):
        running=self.worker.state()!=QProcess.ProcessState.NotRunning
        state={}
        if running:
            try:state=json.loads((self.folder/'state.json').read_text(encoding='utf-8'))
            except (OSError,ValueError):pass
            if state.get('state')=='error':
                self.details.setPlainText(state.get('message','Kamera hatası'))
                message=state.get('message','Kamera hatası')
                self.stop();self.status.setText(message);return
            age=time.time()-state.get('captured',0)
            if state.get('state')=='running' and 0<=age<3:
                self.last_frame=time.monotonic();self.status.setText('Görüntü akıyor · '+('OBS Virtual Camera' if self.virtual.isChecked() else 'yerel önizleme'))
                if not self.frozen and state.get('sequence')!=self.key:
                    image=QPixmap(str(self.folder/'frame.jpg'))
                    if not image.isNull():self.pixmap=image;self.key=state['sequence']
            elif not self.frozen:self.clear_frame();self.status.setText('Görüntü bekleniyor…')
            if time.monotonic()-self.last_frame>12:
                self.stop();self.status.setText('Kinect’ten görüntü gelmedi. USB/güç ve kamera sürücüsünü denetle.')
        if self.pixmap is not None:
            self.image.setPixmap(self.pixmap.scaled(self.image.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

    def freeze_frame(self):
        self.frozen=False;self.refresh()
        if self.pixmap is None or self.worker.state()==QProcess.ProcessState.NotRunning:
            self.clear_frame();self.live_button.setEnabled(False)
            self.frame_status.setText('Test alınamadı; önce kamerayı başlat.');return
        self.frozen=True;self.live_button.setEnabled(True);self.frame_status.setText('Test karesi · '+time.strftime('%H:%M:%S'))

    def resume(self):
        self.frozen=False;self.key=None;self.live_button.setEnabled(False)
        self.clear_frame();self.frame_status.setText('Canlı önizleme · yaklaşık 2 güncelleme/sn')
        self.refresh()

    def finished(self,code,status):
        self.start_button.setEnabled(True);self.stop_button.setEnabled(False);self.virtual.setEnabled(True)
        if not self.user_stop:
            try:message=json.loads((self.folder/'state.json').read_text(encoding='utf-8')).get('message','Kamera akışı kapandı.')
            except (OSError,ValueError):message='Kamera akışı kapandı. İlk kurulum ve bağlantıyı denetle.'
            self.status.setText(message);self.details.setPlainText(message)
        if not self.frozen:self.clear_frame()

    def worker_error(self,error):
        if error==QProcess.ProcessError.FailedToStart:self.finished(1,QProcess.ExitStatus.CrashExit)

    def refresh_mic(self):
        try:
            muted=bool(microphone_endpoint().GetMute())
            self.mic_status.setText('Kinect mikrofonu · '+('sessizde' if muted else 'açık'));self.mute.setText('Sesi aç' if muted else 'Sessize al');self.mute.setEnabled(True)
        except Exception:
            self.mic_status.setText('Kinect mikrofonu bulunamadı');self.mute.setEnabled(False)

    def toggle_mic(self):
        try:
            endpoint=microphone_endpoint();endpoint.SetMute(not endpoint.GetMute(),None);self.refresh_mic()
        except Exception as exc:self.mic_status.setText(str(exc))

    def audio_test(self):
        if self.mic_dialog is not None and self.mic_dialog.isVisible():self.mic_dialog.raise_();return
        from audio import AudioTest
        self.mic_dialog=AudioTest(self);self.mic_dialog.show()

    def closeEvent(self,event):
        if self.mic_dialog is not None:self.mic_dialog.reject()
        self.timer.stop();self.mic_timer.stop();self.stop();self.temp.cleanup();event.accept()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--camera-worker');parser.add_argument('--virtual',action='store_true')
    parser.add_argument('--upload-firmware');parser.add_argument('--result');parser.add_argument('--self-test');parser.add_argument('--test-worker')
    args=parser.parse_args()
    if args.camera_worker:
        from camera import run
        return run(args.camera_worker,args.virtual)
    if args.upload_firmware:
        from firmware import upload
        try:message=upload(args.upload_firmware);code=0
        except Exception as exc:message=str(exc);code=1
        if args.result:atomic_write(Path(args.result),json.dumps({'message':message},ensure_ascii=False).encode())
        return code
    if args.test_worker:
        from selftest import test_worker
        return test_worker(args.test_worker)
    if args.self_test:
        from selftest import self_test
        return self_test(args.self_test)
    if sys.platform!='win32':
        raise SystemExit('Windows sürümünü Windows 10 1809+ x64 üzerinde çalıştırın.')
    if sys.getwindowsversion().build<17763:
        raise SystemExit('Windows 10 1809 veya daha yenisi gerekli.')
    app=QApplication(sys.argv);window=MainWindow();window.show();return app.exec()

if __name__=='__main__':raise SystemExit(main())
