"""Opt-in, bounded local recording from an explicitly identified Kinect input."""
from pathlib import Path
import tempfile
import wave
import numpy as np
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices, QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar
from common import is_kinect, audio_level, write_clip, RATE, RECORD_BYTES


def mono_pcm16(data, fmt):
    if not data:return b''
    kind = fmt.sampleFormat().name
    dtype, scale, offset = {'UInt8':('u1',128,128), 'Int16':('<i2',32768,0),
                            'Int32':('<i4',2147483648,0), 'Float':('<f4',1,0)}[kind]
    values = np.frombuffer(data,dtype=dtype).reshape(-1,fmt.channelCount()).astype(np.float64)
    values = (values-offset).mean(axis=1)/scale
    return (np.clip(values,-1,32767/32768)*32768).astype('<i2').tobytes()


class AudioTest(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Mikrofon testi'); self.resize(430,310)
        self.temp = tempfile.TemporaryDirectory(prefix='kinect-webcam-audio-')
        self.path = Path(self.temp.name)/'test.wav'
        self.source = None; self.stream = None; self.samples = bytearray(); self.pending = b''; self.rate = RATE; self.format = None; self.target = RECORD_BYTES
        self.timeout = QTimer(self); self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.failed)
        self.player = QMediaPlayer(self); self.output = QAudioOutput(self)
        self.output.setVolume(0.6); self.player.setAudioOutput(self.output)
        self.player.errorOccurred.connect(lambda *_: self.status.setText('Kayıt çalınamadı; Windows ses çıkışını denetle.'))
        layout = QVBoxLayout(self)
        self.status = QLabel('Kinect mikrofonundan 5 saniyelik kayıt alıp dinleyebilirsin.');self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.meter = QProgressBar();self.meter.setRange(0,100);self.meter.setTextVisible(False);self.meter.setValue(0);layout.addWidget(self.meter)
        self.record = QPushButton('5 saniye kaydet');self.record.clicked.connect(self.start);layout.addWidget(self.record)
        self.play = QPushButton('Kaydı dinle');self.play.setEnabled(False);self.play.clicked.connect(self.listen);layout.addWidget(self.play)
        stop = QPushButton('Durdur');stop.clicked.connect(self.stop);layout.addWidget(stop)
        note = QLabel('Kayıt bu bilgisayarda geçici tutulur; pencere kapanınca silinir.');note.setWordWrap(True);layout.addWidget(note)
        close = QPushButton('Kapat');close.clicked.connect(self.reject);layout.addWidget(close)

    def start(self):
        self.stop()
        devices = [dev for dev in QMediaDevices.audioInputs() if is_kinect(dev.description())]
        if len(devices) != 1:
            self.status.setText('Tek bir Kinect mikrofonu bulunamadı. Başka mikrofon kullanılmadı.');return
        fmt = QAudioFormat();fmt.setSampleRate(RATE);fmt.setChannelCount(1);fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not devices[0].isFormatSupported(fmt):
            fmt = devices[0].preferredFormat()
        self.format = fmt; self.rate = fmt.sampleRate(); self.target = self.rate*2*5
        if self.rate <= 0 or fmt.channelCount() <= 0:
            self.status.setText('Kinect ses biçimi okunamadı.');return
        self.path.unlink(missing_ok=True);self.samples.clear();self.play.setEnabled(False)
        self.source = QAudioSource(devices[0], fmt, self)
        self.stream = self.source.start()
        if self.stream is None:
            self.failed();return
        self.stream.readyRead.connect(self.read)
        self.record.setEnabled(False);self.timeout.start(10000)
        self.status.setText('Kaydediliyor… 0 / 5 saniye')

    def read(self):
        if self.stream is None:return
        raw = self.pending + bytes(self.stream.readAll())
        size = self.format.bytesPerFrame()
        aligned = len(raw)//size*size
        self.pending = raw[aligned:]
        try:data = mono_pcm16(raw[:aligned], self.format)
        except (ValueError,KeyError):self.failed();return
        self.samples.extend(data[:self.target-len(self.samples)])
        self.meter.setValue(audio_level(data)[0])
        self.status.setText(f'Kaydediliyor… {len(self.samples)/(self.rate*2):.1f} / 5 saniye')
        if len(self.samples) == self.target:
            try:
                if self.rate == RATE:
                    write_clip(self.path, self.samples)
                else:
                    with wave.open(str(self.path),'wb') as output:
                        output.setnchannels(1);output.setsampwidth(2);output.setframerate(self.rate)
                        output.writeframes(self.samples)
            except (OSError,ValueError):
                self.failed();return
            self.stop()
            self.play.setEnabled(True);self.status.setText('Kayıt hazır. Kaydı dinle’ye bas.')

    def stop(self):
        self.timeout.stop()
        if self.stream is not None:
            self.stream.readyRead.disconnect(self.read);self.stream = None
        if self.source is not None:
            self.source.stop();self.source.deleteLater();self.source = None
        self.player.stop();self.player.setSource(QUrl())
        self.samples.clear();self.pending = b'';self.record.setEnabled(True);self.meter.setValue(0)
        self.status.setText('Ses testi durduruldu.')

    def failed(self):
        self.stop();self.play.setEnabled(False)
        self.status.setText('Beş saniyelik kayıt tamamlanamadı. Mikrofon iznini ve Kinect bağlantısını denetle.')

    def listen(self):
        if not self.path.is_file():return
        self.stop();self.player.setSource(QUrl.fromLocalFile(str(self.path)));self.player.play()
        self.status.setText('Geçici kayıt çalınıyor; mikrofon kaydı kapalı.')

    def reject(self):
        self.stop();self.temp.cleanup();super().reject()

    def closeEvent(self, event):
        self.reject();event.accept()
