# Linux · Kinect Webcam v16

**[AppImage dosyasını indir](https://github.com/yasx01/kinect-webcam/releases/download/linux-v16-preview/KinectWebcam-v16-x86_64.AppImage)** · [Sürüm notları](../SURUM_v16.md)

## İndir ve aç

Hedef: **Fedora KDE x86_64**. AppImage ince pakettir; sistemin Python/PyQt6, libfreenect, FFmpeg ve PipeWire/GStreamer bileşenlerini kullanır. İlk kurulum Fedora içindir. Diğer dağıtımlarda otomatik kurulum desteklenmez; AppImage biçimi tüm dağıtımlarda çalışma garantisi değildir.

1. AppImage dosyasını indir.
2. Sağ tık → Özellikler → İzinler bölümünde program olarak çalıştırma iznini aç.
3. Dosyayı açıp **İlk Kurulum / Denetle** yönergelerini izle. Eksik paketler için internet ve yönetici onayı gerekebilir. Kurulumdan sonra Kinect'i çıkarıp takman veya yeniden başlatman gerekebilir.

Terminal kullanmak istersen, dosyanın bulunduğu klasörde:

```bash
chmod +x KinectWebcam-v16-x86_64.AppImage
./KinectWebcam-v16-x86_64.AppImage
```

İlk komut çalıştırma izni verir; ikinci komut uygulamayı açar. FUSE erişimi olmayan bir ortamda `./KinectWebcam-v16-x86_64.AppImage --appimage-extract-and-run` seçeneği kullanılabilir.

## Tarayıcı ve OBS

- **Firefox:** uygulamada Firefox modunu başlat, sitede **Kinect Kamerasi** seç. Görüntü doğrudan PipeWire'a aktarılır.
- **Chrome / Chromium / Edge / Brave:** **OBS / Chromium** modunu başlat, sitede **Kinect360 Facecam** seç. V4L2 sanal kamera kullanılır.
- **OBS isteğe bağlıdır.** İki tarayıcı yolu da OBS uygulaması olmadan çalışacak şekilde hazırlanmıştır. OBS ile kayıt/yayın yapmak istersen OBS'yi ayrıca kurabilirsin.

Akışı başlattıktan sonra görüşme sekmesini yenilemek gerekebilir. Site ve sistem kamera/mikrofon izinleri geçerlidir. Flatpak kamera erişimi ve Secure Boot nedeniyle çekirdek modülü yüklenmesi ayrıca ayar gerektirebilir.

## Mikrofon hazırlığı

Uygulamada mikrofon bağlı görünüyorsa tekrar firmware seçmen gerekmez. **Mikrofon Testi** ile beş saniyelik geçici kayıt alıp dinleyebilirsin. Sistem genelindeki sessize alma diğer uygulamaları da etkiler.

Mikrofon hazır değilse **İlk Kurulum / Denetle → Mikrofon için firmware seç…** düğmesiyle kendi kullanım hakkına sahip olduğun yerel UACFirmware dosyasını seç. Dosya SHA-256 ile doğrulanır; sistem kurulumu ancak yönetici onayından sonra yapılır. Uygulama firmware veya SDK indirmez. USB/güç yeniden bağlandığında firmware tekrar yüklenmelidir; seçilmiş dosyayla kurulum yapılınca udev kuralı bunu otomatik yürütür.

Firmware seçmezsen kamera kurulumu devam eder. Mikrofon hazırlığı isteğe bağlı olarak gösterilir; mikrofonun hazır olduğu iddia edilmez. Firmware seçilmeden yapılan kamera kurulumu, mevcut mikrofon yükleme kuralını değiştirmez.

## Kaynaktan derleme

Projenin kök klasöründe:

```bash
bash tools/fetch-build-tools.sh
bash packaging/build-appimage-v16.sh
```

İlk komut sabit sürümlü AppImage araçlarını sadece `build-tools/` içine indirir. İkinci komut açık kaynak yükleyicisini derler ve `dist/KinectWebcam-v16-x86_64.AppImage` üretir. Derleme firmware gerektirmez ve pakete firmware eklemez. Sistem kurulumu yapmaz; C derleyicisi, pkg-config ve libusb geliştirme dosyalarının bulunması gerekir.

```bash
bash tools/run-tests.sh
```

119 otomatik test, Python/Bash sözdizimi denetimleri ve paket içindeki arayüzün offscreen açılışı kontrol edildi. Gerçek Kinect, temiz Fedora kurulumu ve görüşme uygulaması testi yapılmadı. [Paket doğrulama notları](../SURUM_v16.md)
