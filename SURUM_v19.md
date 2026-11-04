# Kinect Webcam v19 — Fedora RPM ve Ubuntu DEB

- Fedora 44 x86_64 için RPM, Ubuntu 24.04/26.04 LTS amd64 için DEB. AppImage v18 ve Windows v0.3.0 ayrıca kullanılabilir.
- Uygulama menüsüne ve `/usr/bin/kinect-webcam` başlatıcısına kurulur. Bağımlılıklar dağıtım paket yöneticisi tarafından karşılanır; kullanıcı Python/pip paketi indirmek zorunda kalmaz.
- Ortak küçük ctypes bağlayıcısı dağıtımın libfreenect C kütüphanesini kullanır. Böylece Fedora'ya özel Python kamera paketine bağımlılık kalkar; her Python sürümü için ayrı Cython uzantısı gerekmez. Kare tamponu yeniden kullanılmadan kopyalanır.
- İlk kurulum Fedora'da dnf/akmods, Ubuntu'da apt/dkms kullanır. Fedora'ya özgü restorecon/RPM Fusion işlemleri Ubuntu'da çalıştırılmaz.
- Ubuntu Firefox Snap kamera izin kimliği desteklenir. Önizleme v18'deki gibi mevcut akışın kare kopyasını okur; ayrıca Kinect/sanal kamera açmaz.
- Paket kurulum/kaldırma betikleri çalışan Kinect akışını veya eski kinect-webcam.service dosyasını değiştirmez. Microsoft firmware/SDK paketlere eklenmez.

## Kontroller ve sınırlar

129 kaynak testi: Ubuntu paket tespiti, apt/dkms yolu, C kamera tamponunun kopyalanması ve Snap izin kimliği dahil. Fedora 44 ve Ubuntu 24.04 temiz konteynerlerinde paket kurulum/kaldırma, arayüz başlangıcı ve paket bütünlüğü denetlenir. Aynı DEB dosyası Ubuntu 26.04'te de kullanılır. Son çalışmanın sonuçları GitHub Actions kaydında ve sürümle yayımlanan doğrulama raporlarında bulunur.

Fiziksel Kinect, gerçek OBS/Firefox görüşmesi, Secure Boot imza/enrollment ve gerçek çekirdek modülü yüklemesi yeni paketlerle test edilmedi. Konteynerler tam Fedora KDE/Ubuntu masaüstü kurulumu değildir.

## Kullanım

[Dağıtıma özel indirme, kurulum ve kaldırma rehberi](docs/NATIVE_LINUX.md). Derleme tarifi `packaging/build-native-packages.py`; çıktı `dist/` klasörüne yazılır. Diğer sürümler/arşiv korunur.

Microsoft'un orijinal Runtime başvurusu uygulamadan ayrı `optional-drivers/microsoft-runtime/` klasöründedir. Lisans başkalarının kopyalaması için yayımlamayı yasakladığından bu klasör ikili dosya yerine resmi indirme adresi ve SHA-256 içerir. Orijinal dosya yerel uygulama deposunun dışındaki kişisel yedek klasöründe tutulur.

Başarılı derleme/denetim: https://github.com/yasx01/kinect-webcam/actions/runs/41841944490
Kaynak commit: `073a9621a4aa701e92890f1883f13e9b641b32c4`.

`kinect-webcam-19.0.0-1.fc44.x86_64.rpm` SHA-256: `46c42fd4992d373983286ffa36389bee53dbd162052d160756a32c584d5b579e`.

`kinect-webcam_19.0.0-1_amd64.deb` SHA-256: `964c7ac1e1a52c25d06aac89d370bbb45dc5c2b3a8200f0e0a181ac242d9b7d3`.
