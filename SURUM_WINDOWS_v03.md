# Kinect Webcam Windows v0.3.0

## Uygulama içinden Kinect sürücüsü

Kullanıcıların ayrıca Zadig indirmesi gerekmiyor. İlk kurulum ekranındaki **Kamera sürücüsünü hazırla** düğmesi, paket içindeki libwdi kütüphanesini ve Kinect'e özel küçük kurulum bileşenini kullanır. Uygulamada açık onay ve Windows yönetici onayı gerekir; normal açılışta sürücü değişmez.

- Kurulum yalnızca 045e:02ae/02bf Kinect kamerasını kabul eder. Başka USB aygıtı veya kullanıcı tarafından girilen VID/PID seçilemez.
- İsteğe bağlı **ses USB erişimini hazırla** adımı yalnızca firmware öncesi 045e:02ad içindir. Normal çalışan 045e:02bb USB mikrofon sürücüsü ve motor aygıtı değiştirilmez.
- Aynı türden birden fazla Kinect varsa otomatik seçim yapılmaz.
- Kamera uygulamada çalışırken sürücü kurulumu başlamaz. Sürücü güncellemesi sırasında kurulum yardımcısı zaman aşımıyla zorla kapatılmaz.
- Hata, yönetici onayını reddetme veya Windows imza ilkesi engeli başarı olarak gösterilmez. Güvenlik korumalarını kapatma önerilmez.
- OBS Studio / OBS Virtual Camera yolu korunur. Bu sürüm yalnızca ayrı Zadig indirme zorunluluğunu kaldırır.

## Bileşenler

libwdi v1.5.1, commit `9b23b82a2dd1cbffc16d46c212f92c6bf8c0c602` kaynaklardan derlenir. libusbK 3.1.0.0 resmi sürücü dağıtımı sabit SHA-256 ile doğrulanır ve libwdi içine gömülür. Uygulama ayrıca Zadig veya inf-wizard programını açmaz/kurmaz. Gerekli imzalı sürücü ve KMDF destek dosyaları kütüphanenin parçasıdır; Microsoft Kinect firmware/SDK/MSI içermez.

Lisanslar, libwdi kaynak arşivi ve derleme yaması, libusbK kaynak/lisansları ZIP içinde bulunur. Derleme tarifi: `windows/build-driver.sh`. Windows 10 1809+ / Windows 11 x64 hedefi korunur. Linux v18 değiştirilmez.

## Kontroller

26 kaynak testi, sürücü onayını iptal etme, yanlış kurulum adımını reddetme, paket eksikliği, Windows güvenlik ilkesi hatası ve yayın açıkken sürücü kurulmasını engelleme kontrolleri dahil geçti. Yerel testler gerçek sürücü kurmaz. Windows runner paket denetimi, gömülü sürücünün varlığını ve native yardımcının Kinect dışındaki aygıtları reddeden sabit kurallarını da sınar.

Gerçek Kinect üzerinde Windows sürücü değiştirme, fiziksel Windows 10, USB çıkarıp takma ve gerçek OBS görüşmesi sınanmadı. Paketlenmiş uygulamanın açılış testi bu donanım kontrollerinin yerini tutmaz. Windows imza/güvenlik ilkeleri bazı bilgisayarlarda sürücüyü reddedebilir; bu durumda işlem tamamlanmış gösterilmez.

Windows derleme/test kaydı: https://github.com/yasx01/kinect-webcam/actions/runs/41834794927
Kaynak commit: `3be19978ad3c6546bc0081cb77f77e9d62e6792e`.
Paketlenmiş exe açıldı ve native kütüphane/firmware yükleyicisi, gömülü sürücü yardımcısı, arayüz, Türkçe UTF-8 mesaj, yapay kamera gönderimi ve kayıt almadan mikrofon penceresi denetimleri geçti.

EXE SHA-256: `a53514126b648b9a0d8c76eb7cd58e44d16c5daef3d927c1945463bc27f3618e`.
ZIP SHA-256: `260e00c34f7b8d05ebb31fc7229f24ce87ac4bbe460225989c8aa7f2fd60b717`.
