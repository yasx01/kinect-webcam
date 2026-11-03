# Kinect Webcam Windows v0.2.0

Windows 10 1809+ / Windows 11 x64 hedeflenir.

- Eski Linux paneli referans alınarak koyu tema, oval düğmeler ve kontrol/görüntü/günlük kartları düzenlendi.
- İlk pencere 760 × 720, minimum 720 × 640; açık/koyu tema ve Yeniden Başlat düğmesi eklendi.
- Kare Al / Test Et, Canlıya dön, mikrofon sessize alma ve beş saniyelik ses testi korunur.
- Türkçe hata mesajlarının bozulmasının nedeni giderildi: kamera ve firmware alt işlemlerinden gelen UTF-8 JSON artık açıkça UTF-8 olarak okunur. Font: Segoe UI, Noto Sans yedekli. Türkçe harfler kaldırılmadı.
- UTF-8 düzeltmesi kamera hatası, işlem kapanışı ve firmware sonucu için Windows ANSI kodlaması taklit edilerek sınanır. Paket başlangıç testi de Türkçe mesajı denetler.

19 kaynak testi geçti. Windows exe GitHub Actions Windows ortamında derlenir. Kamera sürücüsü/libusbK ve OBS Virtual Camera gereksinimleri değişmedi. Uygulama sürücüleri otomatik değiştirmez; firmware/SDK pakete dahil değildir.

Gerçek Kinect, fiziksel Windows 10 ve gerçek OBS görüşmesi bu değişiklik için test edilmedi.

Windows derleme kaydı: https://github.com/yasx01/kinect-webcam/actions/runs/41637852981
Kaynak commit: 3e473fd40eb5b26b523947a749bab950b0774cd3.

Windows runner üzerinde 19 test geçti. Paketlenmiş exe de başlatıldı: native kitaplık/yükleyici açılışı, arayüz başlangıcı, yapay kamera alt işlemi, kayıt başlatmadan mikrofon penceresi ve UTF-8 Türkçe mesaj denetimleri geçti. Bu kontroller fiziksel Kinect testi değildir.

İndirilen ZIP ve içindeki PE/AMD64 exe doğrulandı. EXE SHA-256: `45d9528872a86b17adffadfac13a4a95ae168fafdefc540ba20b2b8f4df470c2`. ZIP SHA-256: `57f69042465e4987347c53066151af48c596f1dfce559898715d9902de4f5887`.
