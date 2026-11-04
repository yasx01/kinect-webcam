<div align="center">
  <img src="v15/kinect-facecam-icon-v15.png" width="108" alt="Kinect Webcam simgesi">
  <h1>Kinect Webcam</h1>
  <p>Xbox 360 Kinect kameranı ve mikrofonunu bilgisayarında kullan.</p>
  <p>
    <img alt="Kinect v1" src="https://img.shields.io/badge/Kinect-Xbox_360-6E56CF?style=flat-square">
    <img alt="Windows 10 ve üzeri" src="https://img.shields.io/badge/Windows-10%2B-3578E5?style=flat-square">
    <img alt="Linux Fedora" src="https://img.shields.io/badge/Linux-Fedora-3C6EB4?style=flat-square">
  </p>
  <p><strong><a href="https://github.com/yasx01/kinect-webcam/releases/download/windows-v0.3.0/KinectWebcam-Windows-x64.zip">Windows paketini indir (.zip)</a></strong> · <a href="https://github.com/yasx01/kinect-webcam/releases/tag/windows-v0.3.0">Sürüm notları</a> · <strong><a href="https://github.com/yasx01/kinect-webcam/releases/download/linux-v18-preview/KinectWebcam-v18-x86_64.AppImage">Linux paketini indir (.AppImage)</a></strong> · <a href="docs/LINUX.md">Linux rehberi</a></p>
</div>

---

Kinect Webcam, kamera ve mikrofon kontrollerini tek bir panelde toplar. Görüntüyü uygulama içinde önizleyebilir, mikrofonunu test edebilir ve kamerayı görüşme uygulamalarına aktarabilirsin.

## İndir ve başla

| İşletim sistemi | Nereden başlamalı? |
| --- | --- |
| **Windows 10 (1809+) / 11** · 64 bit | [Windows paketini indir](https://github.com/yasx01/kinect-webcam/releases/download/windows-v0.3.0/KinectWebcam-Windows-x64.zip). Paket `.exe`, kurulum rehberi ve lisansları içerir. |
| **Linux · Fedora KDE** · 64 bit | [AppImage dosyasını indir](https://github.com/yasx01/kinect-webcam/releases/download/linux-v18-preview/KinectWebcam-v18-x86_64.AppImage). İlk kurulum Fedora KDE için hazırlanmıştır. [Linux rehberi](docs/LINUX.md) |

### Windows'ta ilk kullanım

1. İndirdiğin ZIP dosyasını **bir kez** çıkar ve içindeki `KinectWebcam-Windows-x64.exe` dosyasını aç.
2. Uygulamadaki **İlk kurulum → Kamera sürücüsünü hazırla** düğmesini kullan; ek sürücü programı indirmen gerekmez. Tarayıcıya görüntü aktarımı için OBS Studio / OBS Virtual Camera gerekir.
3. Kamerayı başlat; görüşme sitesinde **OBS Virtual Camera** ve Kinect mikrofonunu seç.

Mikrofon sistemde görünmüyorsa kendi kullanım hakkına sahip olduğun UACFirmware dosyasını seçmen gerekebilir. Sürücü hazırlığı yalnızca açık onayın ve Windows yönetici onayıyla yapılır. [Ayrıntılı Windows rehberi](windows/WINDOWS.md)

> **Windows önizleme sürümü:** Otomatik testler ve `.exe` başlangıç kontrolü geçti. Gerçek Kinect ile fiziksel Windows 10 bilgisayarda ve görüşme uygulamalarında henüz test edilmedi.

### Linux'ta ilk kullanım

1. AppImage dosyasını indir. Dosya özelliklerinden **program olarak çalıştırma izni** ver ve aç.
2. Fedora KDE'de **İlk Kurulum / Denetle** yönergelerini izle. Eksik sistem bileşenlerinin kurulması internet ve yönetici onayı gerektirebilir.
3. Firefox modunda **Kinect Kamerasi** seç. Chrome/Chromium için **OBS / Chromium** modunu başlatıp **Kinect360 Facecam** seç.

**Linux'ta OBS uygulaması zorunlu değil.** Mikrofon firmware'i pakete dahil değildir; sistemde zaten hazır değilse ilk kurulum ekranında kendi yerel dosyanı seçebilirsin. Kamera kurulumu firmware seçilmeden de yapılabilir. [Linux sürüm notları](SURUM_v18.md)

## Neler yapabilirsin?

- **Görüntüyü gör:** Çalışan yayını otomatik izle, **Kare Al / Test Et** ile kareyi sabitle. **Önizleme açık** düğmesi yalnızca paneli kapatır; yayın sürer.
- **Mikrofonu kontrol et:** Sessize al, sesi aç veya kısa bir kayıtla dene.
- **Görüşmeye katıl:** Görüntüyü sanal kamera üzerinden tarayıcıya veya OBS'ye aktar.
- **Kurulumu gözden geçir:** İşlemleri incele ve sistem değişikliklerini kullanıcı onayıyla yap.

Mikrofon testi yalnızca sen başlattığında kayıt alır; geçici kayıt normal kapanışta silinir. İşletim sisteminin ve görüşme sitesinin kamera/mikrofon izinleri geçerlidir.

## Geliştiriciler için

- [Linux kurulumu, derleme ve test](docs/LINUX.md)
- [Windows kurulumu ve derleme](windows/WINDOWS.md)
- [Linux v18 sürüm notları](SURUM_v18.md) · [Windows sürüm notları](SURUM_WINDOWS_v03.md)
- [Windows derleme ve test çıktısı](https://github.com/yasx01/kinect-webcam/actions/runs/41834794927)

Linux v18 için 121 otomatik test, Windows için 26 kaynak testi ve paket başlangıç denetimi çalıştırıldı. Bu kontroller gerçek donanım testinin yerini tutmaz.

## Lisans ve üçüncü taraflar

Açık kaynak bileşenlerin bildirimleri kaynak klasörlerinde ve Windows ZIP paketinde yer alır. Microsoft Kinect firmware'i ve SDK/MSI bu depoda veya Windows paketinde bulunmaz. Windows USB sürücü kurulumu için gerekli libwdi/libusbK bileşenleri pakete dahildir. Projenin kendi kodu için henüz ayrı bir lisans seçilmemiştir.
