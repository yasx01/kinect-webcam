# Kinect Webcam v18

## Yayını kesmeyen önizleme

- Uygulama açılırken çalışan OBS/Chromium veya Firefox köprüsü tanınır; önceki kayıtlı modun farklı olması görüntüyü gizlemez.
- Ana panel ve kamera/mikrofon test penceresi yalnızca çalışan köprünün güncel kare kopyasını okur. Fiziksel Kinect veya sanal kamera aygıtı ikinci bir okuyucu olarak açılmaz.
- Kare Al / Test Et yalnızca mevcut görüntüyü sabitler. Test penceresindeki kamera başlat/durdur/yeniden başlat kontrolleri ve FFmpeg ile ayrı V4L2 okuyan eski çıkış testi kaldırıldı.
- Önizleme açık düğmesiyle panel kapatılabilir; panelin zamanlayıcısı durur ve kare belleği temizlenir. OBS/Firefox yayını korunur. Panel/test penceresini kapatmak da yayını durdurmaz.
- Eski bir köprü kare kopyası sağlamıyorsa test onu yeniden başlatmaz veya cihazı açmaya çalışmaz; durumu açıklar.
- Elle yayın modunu değiştirmek hâlâ çalışan görüşmeyi kesebilir; ayrı onay gerekir. Firefox izin kontrolü, diğer köprü durdurulmadan önce yeni köprü başlatmaya çalışmaz. Önizleme için mod değiştirmek gerekmez.

## Daha küçük pencere

Ana pencere 700 × 620, minimum 640 × 540. Günlük başlangıçta kapalıdır. Kamera/mikrofon test penceresi 700 × 520; dar pencerede içerik kaydırılarak erişilebilir. Türkçe metinler ve önceki görsel düzen korunur.

## Kontroller

121 otomatik kontrol: yayın sırasında kare alma, önizlemeyi kapatma/açma, test penceresini kapatma, çalışan köprünün otomatik seçilmesi, kare yokken yeniden başlatmama, mod değişikliğini iptal etme ve dar pencere yerleşimi dahil. Python/Bash sözdizimi ve paket içeriği ayrıca doğrulandı.

Bu bilgisayardaki çalışan v17 Kinect köprüsü üzerinde pasif kontrol yapıldı: v18 arayüzü hazır kareyi okudu; kare testi, paneli kapatma ve pencereyi kapatma sonrasında aynı köprü kare üretmeye devam etti. Köprüye başlat/durdur komutu gönderilmedi ve ikinci kamera süreci açılmadı. OBS/Firefox tarafında gerçek görüşme testi ve temiz Fedora kurulumu yapılmadı.

v17, arşiv ve eski belgeler korunur. Microsoft firmware/SDK pakete eklenmez. Windows v0.2.0 bu Linux düzeltmesinden etkilenmez.

Derleme: `bash packaging/build-appimage-v18.sh`. Çıktı: `dist/KinectWebcam-v18-x86_64.AppImage`.

AppImage SHA-256: `2e148c2c50afea09b1aca46be3e922c37726634502f075056fbbae1516da152c`. Paket içeriği kaynaklarla karşılaştırıldı, açık kaynak yükleyici özeti doğrulandı ve paketlenen arayüz offscreen açıldı.
