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
from PyQt6.QtGui import QPixmap, QDesktopServices
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
            value=json.loads((Path(self.result_temp.name)/'result.json').read_text())
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
        super().__init__();self.setWindowTitle('Kinect Webcam · Windows');self.resize(840,720);self.setMinimumSize(640,560)
        self.temp=tempfile.TemporaryDirectory(prefix='kinect-webcam-camera-')
        self.folder=Path(self.temp.name);self.frozen=False;self.pixmap=None;self.key=None;self.mic_dialog=None
        self.started=0;self.last_frame=0;self.user_stop=False
        self.worker=QProcess(self);self.worker.finished.connect(self.finished);self.worker.errorOccurred.connect(self.worker_error)
        content=QWidget();root=QVBoxLayout(content);root.setContentsMargins(24,20,24,20);root.setSpacing(12)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setWidget(content);self.setCentralWidget(scroll)
        header=QHBoxLayout();root.addLayout(header)
        title=QLabel('Kinect Webcam');title.setStyleSheet('font-size:25px;font-weight:700');header.addWidget(title,1)
        setup=QPushButton('İlk kurulum');setup.clicked.connect(lambda:Setup(self).exec());header.addWidget(setup)
        self.status=QLabel('Hazır · kamerayı başlat');self.status.setWordWrap(True);root.addWidget(self.status)
        self.virtual=QCheckBox('Tarayıcıya aktar · OBS Virtual Camera');self.virtual.setChecked(True);root.addWidget(self.virtual)
        controls=QHBoxLayout();root.addLayout(controls)
        self.start_button=QPushButton('Başlat');self.start_button.setObjectName('primary');self.start_button.clicked.connect(self.start);controls.addWidget(self.start_button)
        self.stop_button=QPushButton('Durdur');self.stop_button.setEnabled(False);self.stop_button.clicked.connect(self.stop);controls.addWidget(self.stop_button)
        self.test_button=QPushButton('Test Al');self.test_button.clicked.connect(self.freeze_frame);controls.addWidget(self.test_button)
        self.live_button=QPushButton('Canlıya dön');self.live_button.setEnabled(False);self.live_button.clicked.connect(self.resume);controls.addWidget(self.live_button)
        self.image=QLabel('Görüntü burada görünecek.');self.image.setAlignment(Qt.AlignmentFlag.AlignCenter);self.image.setMinimumHeight(220)
        self.image.setStyleSheet('background:#090d14;border-radius:12px;color:#aeb7c8;');root.addWidget(self.image,1)
        self.frame_status=QLabel('Canlı önizleme · yaklaşık 2 güncelleme/sn');root.addWidget(self.frame_status)
        mic=QHBoxLayout();root.addLayout(mic)
        self.mic_status=QLabel('Mikrofon kontrol ediliyor…');self.mic_status.setWordWrap(True);mic.addWidget(self.mic_status,1)
        self.mute=QPushButton('Sessize al');self.mute.clicked.connect(self.toggle_mic);mic.addWidget(self.mute)
        audio=QPushButton('Mikrofon testi');audio.clicked.connect(self.audio_test);mic.addWidget(audio)
        hint=QLabel('Görüşme sitesinde OBS Virtual Camera ve Kinect mikrofonunu seç.');hint.setWordWrap(True);root.addWidget(hint)
        self.details_button=QPushButton('Teknik ayrıntılar');self.details_button.setCheckable(True);root.addWidget(self.details_button)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(110);self.details.hide();root.addWidget(self.details)
        self.details_button.toggled.connect(self.details.setVisible)
        self.setStyleSheet('''QMainWindow,QWidget{background:#11151d;color:#e9edf5;font-family:"Segoe UI";font-size:13px;}
            QPushButton{background:#232a38;border:1px solid #303a4c;border-radius:12px;padding:10px 16px;min-height:22px;}
            QPushButton:hover{background:#303a4c;} QPushButton:disabled{color:#838da0;}
            QPushButton:focus{border:2px solid #7892ff;} QPushButton#primary{background:#5273ff;color:white;border:none;}
            QCheckBox{padding:8px 0;} QPlainTextEdit{border:1px solid #303a4c;border-radius:10px;}
            QProgressBar{background:#303a4c;border:none;min-height:14px;border-radius:6px;}
            QProgressBar::chunk{background:#28c880;border-radius:6px;}''')
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(250)
        self.mic_timer=QTimer(self);self.mic_timer.timeout.connect(self.refresh_mic);self.mic_timer.start(4000)
        self.refresh_mic()

    def start(self):
        if self.worker.state()!=QProcess.ProcessState.NotRunning:return
        for name in ['frame.jpg','state.json','stop']:(self.folder/name).unlink(missing_ok=True)
        self.resume();self.started=time.monotonic();self.last_frame=self.started;self.user_stop=False
        command,args=child_command('--camera-worker',str(self.folder),*(['--virtual'] if self.virtual.isChecked() else []))
        self.worker.start(command,args);self.start_button.setEnabled(False);self.stop_button.setEnabled(True);self.virtual.setEnabled(False)
        self.status.setText('Kinect’e bağlanılıyor…')

    def stop(self):
        self.user_stop=True
        if self.worker.state()!=QProcess.ProcessState.NotRunning:
            (self.folder/'stop').touch()
            if not self.worker.waitForFinished(1500):self.worker.kill();self.worker.waitForFinished(1500)
        self.status.setText('Durduruldu');self.start_button.setEnabled(True);self.stop_button.setEnabled(False);self.virtual.setEnabled(True)
        if not self.frozen:self.clear_frame()

    def clear_frame(self):
        self.pixmap=None;self.key=None;self.image.setPixmap(QPixmap());self.image.setText('Güncel görüntü yok. Kamerayı başlat.')

    def refresh(self):
        running=self.worker.state()!=QProcess.ProcessState.NotRunning
        state={}
        if running:
            try:state=json.loads((self.folder/'state.json').read_text())
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
            try:message=json.loads((self.folder/'state.json').read_text()).get('message','Kamera akışı kapandı.')
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
