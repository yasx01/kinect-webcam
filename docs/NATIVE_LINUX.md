# Fedora ve Ubuntu için yerel paketler

Kinect Webcam v19, sistem paket yöneticisiyle kurulabilir. Hedefler: **Fedora 44 x86_64**, **Ubuntu 24.04 LTS ve 26.04 LTS amd64**. Bunlar AppImage yerine normal uygulama menüsüne kurulur. Bağımlılıkları dnf/apt çözer; kullanıcıya pip kurulumu gerekmez.

## İndir ve kur

- [Fedora 44 RPM](https://github.com/yasx01/kinect-webcam/releases/download/linux-v19-native-preview/kinect-webcam-19.0.0-1.fc44.x86_64.rpm)
- [Ubuntu 24.04/26.04 DEB](https://github.com/yasx01/kinect-webcam/releases/download/linux-v19-native-preview/kinect-webcam_19.0.0-1_amd64.deb)

İndirdiğin dosyanın bulunduğu klasörde, **kendi dağıtımına ait tek komutu** çalıştır:

Fedora:

```bash
sudo dnf install ./kinect-webcam-19.0.0-1.fc44.x86_64.rpm
```

Ubuntu:

```bash
sudo apt install ./kinect-webcam_19.0.0-1_amd64.deb
```

Komut yerel uygulama paketini ve eksik sistem bağımlılıklarını kurar; yönetici onayı ister. Ubuntu'da Universe deposu açık olmalıdır. Kurulumdan sonra uygulama menüsünden **Kinect Webcam** açılabilir veya `kinect-webcam` komutu kullanılabilir.

## İlk hazırlık

Uygulamada **İlk Kurulum / Denetle** bölümünü aç. Paket kurulum betikleri çalışan Kinect akışını durdurmaz, çekirdek modülünü zorla yüklemez ve firmware indirmez. İlk kurulum, USB/sanal kamera durumunu doğrular ve gerekiyorsa yapılacak değişiklikleri ayrı onayla tamamlar. Kamera izinleri için Kinect'i yeniden takmak veya bilgisayarı yeniden başlatmak gerekebilir.

Fedora'da V4L2 sanal kamera gerekiyorsa ilk kurulum RPM Fusion Free deposunu ve akmod paketini sunar. Ubuntu'da dağıtımın v4l2loopback-dkms paketi kullanılır; çalışan çekirdeğin başlıkları ve Secure Boot modül imzası ayrıca gerekebilir. Modül yüklemesi başarısızsa tamamlanmış gösterilmez. Fedora 44'ün standart depolarıyla kontrol paneli kurulabilir; RPM Fusion yalnızca sanal kamera hazırlığında gerekebilir.

Microsoft Kinect mikrofon firmware'i paketlere dahil değildir. Mikrofon sistemde zaten görünüyorsa tekrar hazırlık gerekmez; aksi halde ilk kurulumdan kendi yerel dosyanı seçebilirsin. Windows için Microsoft sürücüsü Linux'ta kullanılmaz.

## Kullanım

Çalışan Kinect köprüsü otomatik algılanır. Önizleme ve Kare Al / Test Et yalnızca hazır kareyi okur; ikinci kamera okuyucusu açmaz. Önizlemeyi kapatmak görüşme yayınını durdurmaz.

Firefox için PipeWire modu; Chromium/Chrome/Edge/Brave ve OBS için V4L2 modu seçilir. Linux'ta OBS uygulaması zorunlu değildir. Ubuntu'nun varsayılan Firefox Snap kurulumu için `snap.firefox` izin kimliği kullanılır. Snap/sistem kamera izinleri, görüşme sitesi izinleri ve masaüstünün portal hizmeti yine geçerlidir. Birden fazla farklı Firefox kurulumu varsa izin denetimi varsayılan Snap kurulumunu önceliklendirir.

## Kaldırma ve güncelleme

Fedora'da `sudo dnf remove kinect-webcam`, Ubuntu'da `sudo apt remove kinect-webcam` uygulamayı kaldırır. Kullanıcı tarafından ayrıca sağlanan firmware gibi kişisel kurulum verileri otomatik silinmez. DEB/RPM dosyası bir güncelleme deposu oluşturmaz; yeni sürüm çıktığında yeni dosyayı aynı kurulum komutuyla yükleyebilirsin.

## Derleme ve doğrulama

İlgili dağıtımda C derleyicisi, pkg-config, libusb geliştirme dosyaları ve RPM için rpmbuild / DEB için dpkg-deb gerekir:

```bash
python3 packaging/build-native-packages.py rpm
python3 packaging/build-native-packages.py deb
```

Yalnızca kendi ortamına uygun komutu çalıştır. Bu komutlar dosya oluşturur; sisteme paket kurmaz. Ubuntu paketi Ubuntu 24.04'te derlenir ve aynı dosya Ubuntu 26.04'te tekrar sınanır.

GitHub Actions temiz dağıtım konteynerlerinde bağımlılık çözümü, kurulum, dosya bütünlüğü, sistem libfreenect kütüphanesinin yüklenmesi, arayüzün offscreen açılması, kaynak testleri ve kaldırmayı denetler. Konteynerler tam masaüstü/Kinect ortamı değildir; gerçek görüşme, fiziksel Kinect ve çekirdek modülü yükleme bu kontrollerle doğrulanmış sayılmaz.
