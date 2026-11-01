# Kinect Webcam

Xbox 360 Kinect kamerasını ve mikrofonunu Fedora KDE üzerinde tek panelden kullanmak için Python/PyQt6 uygulaması. Linux sürümü: **v15**. Windows 10 (1809+) / Windows 11 x64 sürümü için [Windows kurulum ve derleme rehberine](windows/WINDOWS.md) bakın.

## Neler yapar?

- OBS için V4L2 sanal kamera ve tarayıcılar için PipeWire kamera akışı.
- Kinect mikrofonunu sistem genelinde sessize alma / sesi açma.
- Ana ekranda canlı görüntü, **Test Al** ile tek kareyi sabitleme ve **Canlıya dön**.
- **Mikrofon Testi:** ses seviyesi, beş saniyelik geçici kayıt ve kaydı dinleme. Eski görüntü çıkışı testi aynı pencerede korunur.
- Gerektiğinde açılan teknik ayrıntılar; varsayılan görünümde log kapalıdır.
- Fedora x86_64 için yönetici onaylı ilk kurulum: eksik paketler, USB izinleri, firmware yükleyicisi ve sanal kamera ayarları.
- Firefox kamera izin sorunlarını denetleme ve kullanıcı onayıyla önceki yeniden başlatma çözümü.

Kamera testi Kinect'i ikinci kez açmaz; çalışan köprüden yaklaşık saniyede iki önizleme alır. Ana kamera akışı 30 kare/sn hedefler. Önizleme üretmeyen eski bir köprü çalışıyorsa akışı bir kez yeniden başlatın. “Görüntü çıkışını da test et” önceki çıkış testini korur.

Mikrofon yalnızca test düğmesine basınca dinlenir. Başka bir mikrofon otomatik seçilmez ve sessizdeki Kinect kendiliğinden açılmaz. Kayıt mono, 16 kHz, 16-bit ve beş saniyedir. Ses yalnızca yerel geçici dosyada tutulur; test penceresi kapanınca silinir. Kaydı dinlerken mikrofon testi durur. Test penceresini kapatmak kamera akışını durdurmaz; kamerayı Durdur düğmesiyle kapatın. Zorla kapatma/çökme durumunda geçici dosya normal kapanıştaki gibi silinemeyebilir.

## Tarayıcıda kullanım

**Chrome / Chromium / Edge / Brave:** uygulamada **OBS / Chromium** seçip Başlat’a basın. Ardından görüşme sitesinin kamera listesinde **Kinect360 Facecam** seçin. Bu yol V4L2 sanal kamerayı kullanır; `exclusive_caps=1` ile kamera yazıcısı başladıktan sonra görüntü yakalama aygıtı olarak görünür. Akışı başlatmadan açılmış kamera listesi için sekmeyi yenilemek gerekebilir.

**Firefox:** uygulamada Firefox seçip Başlat’a basın; sitede **Kinect Kamerasi** seçin. Bu yol doğrudan PipeWire kaynağıdır. Chromium kullanımı Firefox izinlerini sıfırlamaz veya Firefox’u kapatmaz.

Tarayıcının site/sistem kamera izinleri ayrıca geçerlidir; Flatpak paketlerinin kamera erişimi ayrıca gerekebilir. Tarayıcı ayarları, güvenlik bayrakları ve profil verileri otomatik değiştirilmez. Gerçek Google Meet ve Chromium donanım testi bu sürüm hazırlanırken yapılmamıştır.

Altyapı: [Chromium kamera belgeleri](https://www.chromium.org/developers/design-documents/video-capture/), [v4l2loopback exclusive_caps](https://github.com/v4l2loopback/v4l2loopback#options).

## Çalıştırma

Bu bir **ince AppImage** projesidir: sistemin Python, PyQt6, libfreenect, FFmpeg, GStreamer/PipeWire ve çekirdek sanal kamera bileşenlerini kullanır. İlk kurulum sistem dosyalarını değiştirmeden önce işlemleri gösterir ve yönetici onayı ister. İnternet gerekebilir. Secure Boot ve çekirdek modülü sorunları ayrıca ele alınmalıdır; temiz Fedora ve gerçek donanım testi tamamlanmadan evrensel uyumluluk sözü verilmez.

Sistem daha önce hazırlanmışsa kaynak panelini açmak için:

```bash
python3 -B v15/kinect-facecam-gui-v15.py
```

Bu komut paneli açar; sistem paketlerini kendiliğinden kurmaz. Kaynak checkout'unun ilk kurulum yükleri yerel derleme sırasında oluşturulur.

## Yerel AppImage derleme

Microsoft **UACFirmware**, SDK/MSI ve Windows sürücüleri bu herkese açık depoda bulunmaz. Kullanım hakkına sahip olduğunuz yerel firmware dosyasını ayrıca sağlamalısınız. Firmware indiren veya SDK çıkaran otomatik bir adım yoktur. Beklenen SHA-256: `efd1dd2fd2610f69d07af7aeff56b26551ac6ec4251159c50027769545b6f7a5`.

Derleme araçları: Bash, Python 3, C derleyicisi, pkg-config, libusb-1.0 geliştirme dosyaları, curl ve sha256sum. Fedora paket adları arasında `gcc`, `pkgconf-pkg-config`, `libusb1-devel` bulunur. Kurulum için sistem yöneticinizin onayını alın.

```bash
bash tools/fetch-build-tools.sh
KINECT_FIRMWARE_PATH=/usr/lib/firmware/kinect/UACFirmware bash packaging/build-appimage-v15.sh
```

İlk komut resmi AppImage araçlarını yalnızca `build-tools/` içine indirir, sabit SHA-256 özetlerini doğrular; sudo kullanmaz. İkinci komut açık kaynak yükleyicisini derler, belirtilen yerel firmware'i yerel pakete ekler ve `dist/KinectWebcam-v15-x86_64.AppImage` üretir. Hiçbiri sistem kurulumu yapmaz. Firmware'i içeren çıktıyı yayımlamadan önce ilgili dağıtım haklarını ayrıca değerlendirin. `build-tools/`, `dist/`, firmware ve üretilen yükler git tarafından dışlanır.

## Denetimler

```bash
bash tools/run-tests.sh
```

Komut her test dosyasını ayrı Python sürecinde çalıştırır. PyQt6, NumPy, python3-dbus, python3-gobject ve dbus-run-session gerekir. Kamera/ses testleri yapay veri kullanır; gerçek mikrofonu kaydetmez. Firefox izin entegrasyonu ayrı bir D-Bus oturumunda sahte izin deposuna bağlanır; gerçek Firefox kapanmaz veya ayarları değişmez.

v15 için 112 otomatik test vardır. Başlat/durdur işlemleri üst üste bindirilmez. PID kimliği kullanıcı ve köprü komutu üzerinden doğrulanır; durdurma pidfd ile yapılır. Eski veya canlılığı doğrulanamayan kare güncel görüntü gibi sunulmaz. Gerçek Kinect görüntü/ses, USB çıkarıp takma, görüşme uygulaması ve temiz Fedora kurulumu ayrıca elle doğrulanmalıdır. Firefox'un her kamera isteğinde yeniden izin sorması garanti edilmez; web sitesi, Firefox ve portal izinleri ayrı katmanlardır. Genel profil sıfırlaması veya tarayıcı önbelleği silme otomatik yapılmaz.

## Üçüncü taraf kaynaklar

`v15/vendor/kinect-audio-setup/kinect_upload_fw.c`, upstream kinect-audio-setup projesindendir; kaynak başlığındaki BSD koşulları ve `v15/licenses/` bildirimi korunmuştur. Köken bilgisi vendor dizinindedir. Microsoft firmware'i bu kodun lisansı kapsamında değildir. Projenin kendi kodu için henüz ayrı bir lisans seçilmemiştir; herkese açık görünmesi genel yeniden dağıtım izni anlamına gelmez.
