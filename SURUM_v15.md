# Kinect Webcam v15 — Linux son sürüm

## Kullanım

- Ana ekranda canlı görüntü, Test Al ile tek kareyi sabitleme ve Canlıya dön.
- OBS / Chromium: akışı başlat, görüşme sitesinde Kinect360 Facecam seç.
- Firefox: PipeWire yolu korunur; Kinect Kamerasi seç.
- Mikrofon Testi: ses seviyesi, beş saniyelik kayıt ve yerel dinleme. Önceki çıkış testi aynı pencerede korunur.
- Teknik ayrıntılar varsayılan kapalıdır. Küçük ekranlarda içerik kaydırılabilir. Açık ve koyu tema vardır.

## Giderilen mantık hataları

- Başlat/durdur/mod değiştirme işlemleri üst üste çalışmaz; işlem sürerken pencere kapatılarak çalışan QThread yok edilemez.
- Eski PID kaydı tek başına çalışan kamera kabul edilmez. Kullanıcı ve köprü komutu doğrulanır; durdurma PID yeniden kullanımı yarışına karşı pidfd ile yapılır.
- Güncel görüntü gelmiyorsa akış bekleniyor denir; canlı panel eski kareyi güncelmiş gibi sunmaz. Bilerek sabitlenen kare Test karesi ve saat ile belirtilir.
- Bozuk ayar dosyası veya geçersiz mod uygulamayı çökertmez.
- Mikrofon süreci biterse dinleniyor durumu kalmaz. Eksik kayıt oynatılamaz, pencere kapanınca geçici kayıt temizlenir.
- FFmpeg/GStreamer kapanmayı geciktirirse köprü çıkışında sonlandırma tamamlanır.

## Doğrulama

112 otomatik test geçti. Python AST ve bash -n denetimleri başarılı. AppImage açılıp dosya listesi çıkarıldı, firmware ve yükleyici SHA-256 özetleri doğrulandı. Paketten çıkarılan GUI offscreen ortamda açıldı. Kaynak ve paket Python dosyaları eşleşiyor. Arşivdeki/eski sürümlerdeki 126 dosya ve Git deposundaki v14 dosyaları değişmedi.

Bu çalışmada gerçek Kinect, gerçek mikrofon kaydı, Chrome/Meet görüşmesi, USB çıkarıp takma veya temiz Fedora kurulumu denenmedi. Yapay test görüntüsü kullanılan önizleme gerçek kamera testi değildir. Kaynak doğrulaması tamamlanması her bilgisayarda sorunsuz çalışma garantisi değildir.

## Paket ve kaynak ayrımı

Yerel AppImage daha önce onaylanmış UACFirmware'i içerir. SDK/MSI ve Windows sürücüsü içermez. GitHub'a kaynak kod ve testler yüklenir; firmware, derlenmiş yükleyici, AppImage, build-tools ve dist yüklenmez. Microsoft firmware'i kaynak depoda dağıtılmaz. Windows çalışması ertelenmiştir.

AppImage: KinectWebcam-v15-x86_64.AppImage
SHA-256: edc5b68b7b60c2962084745c0b13536506edd30fa9552773bf71f54620673eba
