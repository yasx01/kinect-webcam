# Kinect Webcam — Windows

Hedef: **Windows 10 1809 ve sonrası / Windows 11, x64**. Xbox 360 Kinect v1 içindir; Kinect v2 ve ARM64 desteklenmez.

## İlk kullanım

1. Kinect'in kendi güç adaptörünü ve USB bağlantısını takın.
2. Uygulamada **İlk kurulum → Kamera sürücüsünü hazırla** düğmesine basın. Yapılacak değişikliği ve Windows yönetici onayını kabul edin. Gerekli sürücü kütüphanesi pakete dahildir; ayrıca Zadig indirmeniz gerekmez. İşlem yalnızca **Xbox NUI Camera** (045e:02ae/02bf) için libusbK hazırlar; birden fazla eşleşen Kinect varsa seçim yapmadan durur. Sürücü değişikliği Kinect SDK kullanan başka uygulamaları etkileyebilir.
3. [OBS Studio](https://obsproject.com/download) kurun; OBS Virtual Camera kayıtlı olmalıdır. Kinect Webcam'de Tarayıcıya aktar seçiliyse kamerayı Başlat ile açın. OBS'nin kendi Sanal Kamerayı Başlat işlemini aynı anda kullanmayın: tek kamera örneği paylaşılır.
4. Chrome, Edge, Brave veya Firefox'taki görüşme sitesinde **OBS Virtual Camera** ve Kinect mikrofonunu seçin. Tarayıcı site kamera/mikrofon izinleri korunur. İzinleri uygulama otomatik silmez.
5. Sadece görüntüyü denemek için Tarayıcıya aktar seçimini kaldırabilirsiniz; bu modda OBS gerekmez.

## Mikrofon

Windows ses aygıtlarında Kinect mikrofonu varsa sistem genelinde Sessize al / Sesi aç ve uygulama içi kayıt testi kullanılabilir. Başka veya varsayılan mikrofon otomatik seçilmez. Birden fazla Kinect ses kaynağı varsa uygulama seçim yapmadan uyarır.

Mikrofon görünmüyorsa İlk kurulum ekranında kendi kullanım hakkınıza sahip olduğunuz **UACFirmware** dosyasını seçebilirsiniz. Beklenen SHA-256 `efd1dd2fd2610f69d07af7aeff56b26551ac6ec4251159c50027769545b6f7a5` dışında dosya kabul edilmez. Ham ses aygıtı **045e:02ad** için gerekirse **İlk kurulum → Mikrofon görünmüyorsa: ses USB erişimini hazırla** düğmesini kullanın. Bu isteğe bağlı adım yalnızca firmware yükleme erişimini hazırlar; firmware yüklemek için yine yerel dosyanız gerekir. Firmware sonrası görünen **045e:02bb** aygıtında Windows USB Audio sürücüsünü koruyun; buna libusbK kurmak normal mikrofon erişimini engeller. Firmware her USB/güç kesintisinde tekrar gerekebilir. SDK/MSI veya firmware bu pakette dağıtılmaz; uygulama bunları internetten indirmez.

Ses testi yalnızca düğmeye bastığınızda kayıt yapar. Kayıt beş saniyeyle sınırlıdır ve test penceresi kapanınca silinir. Uygulama zorla kapatılırsa geçici dosya kalabilir. Kaydı dinlerken kayıt durdurulur. İnternete ses/görüntü gönderilmez; sanal kamerayı kullanan görüşme sitesi kendi bağlantısını yönetir.

## Derleme ve test

GitHub Actions `Windows executable` iş akışı, sabit libfreenect v0.7.5 commit'ini kaynaklarından derler. `BUILD_REDIST_PACKAGE=ON`: Microsoft firmware indirme/SDK adımı yoktur. PyInstaller, Python ve Qt'yi exe'ye dahil eder; kullanıcı Python kurmaz. Derleme ve kaynak testleri Windows runner üzerinde çalışır. Kinect ile sınırlı kurulum yardımcısı ve libwdi kaynaklardan derlenir. İmzalı libusbK 3.1.0.0 sürücü kaynakları resmi dağıtımdan sabit SHA-256 ile doğrulanır. Paketlenen exe ayrıca `--self-test <rapor.json>` ile başlatılır: native DLL yüklenmesi, GUI başlangıcı, yapay kamera akışı ve sanal kamera gönderim yolu sınanır. Yeni sürücü yardımcısının aygıt sınırları ve gömülü libusbK dosyalarının varlığı da kontrol edilir. Bu test gerçek sürücü kurulumu yapmaz ve Kinect/OBS donanımı gerektirmez; gerçek donanım testinin yerine geçmez.

Çıktı ZIP'i exe, kurulum açıklaması, lisanslar, SHA-256 ve test raporu içerir. Microsoft firmware'i/sürücüsü içermez. Kaynaklar ve derleme tarifi aynı GitHub deposundadır. İmzalanmamış ilk sürüm için Windows tanınmayan yayıncı uyarısı gösterebilir.

Yerel Windows derlemesi: Python 3.12 x64 ve MSYS2 UCRT64 derleme araçları gerekir. `bash windows/build-native.sh` ve ardından `bash windows/build-driver.sh` native dosyaları `windows/native` altında üretir. İkinci adım autotools, make, curl ve 7-Zip derleme araçlarını kullanır. Ayrı bir Python sanal ortamında `pip install -r windows/requirements.txt`, sonra `powershell -File windows/build.ps1` çalıştırın. Derleme scriptleri sürücü veya OBS kurulumu yapmaz. Son kullanıcı uygulamasındaki sürücü hazırlığı yalnızca ayrı onayla çalışır; uygulamayı normal açmak sürücü değiştirmez. Windows koruma/imza ilkeleri kurulumu reddederse başarı gösterilmez ve güvenlik ayarlarını kapatma önerilmez. Sürücü değiştirme fiziksel Windows/Kinect üzerinde ayrıca sınanmalıdır.

Kaynaklar: [OpenKinect](https://github.com/OpenKinect/libfreenect), [pyvirtualcam](https://github.com/letmaik/pyvirtualcam), [Qt Windows desteği](https://doc.qt.io/qt-6/windows.html).

Sürücü bileşenleri: [libwdi](https://github.com/pbatard/libwdi/tree/9b23b82a2dd1cbffc16d46c212f92c6bf8c0c602) (LGPLv3+), [libusbK 3.1.0.0](https://sourceforge.net/projects/libusbk/files/libusbK-release/3.1.0.0/) (bileşen lisanslarıyla). ZIP içindeki lisans klasörü libwdi kaynak arşivini, uygulanan derleme yamasını ve libusbK kaynak/lisanslarını içerir. Dinamik libwdi bağlantısının yeniden derleme tarifi `windows/build-driver.sh` dosyasındadır.
