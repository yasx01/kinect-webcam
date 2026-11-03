# Kinect Webcam Windows v0.2.0

Windows 10 1809+ / Windows 11 x64 hedeflenir.

- Eski Linux paneli referans alınarak koyu tema, oval düğmeler ve kontrol/görüntü/günlük kartları düzenlendi.
- İlk pencere 760 × 720, minimum 720 × 640; açık/koyu tema ve Yeniden Başlat düğmesi eklendi.
- Kare Al / Test Et, Canlıya dön, mikrofon sessize alma ve beş saniyelik ses testi korunur.
- Türkçe hata mesajlarının bozulmasının nedeni giderildi: kamera ve firmware alt işlemlerinden gelen UTF-8 JSON artık açıkça UTF-8 olarak okunur. Font: Segoe UI, Noto Sans yedekli. Türkçe harfler kaldırılmadı.
- UTF-8 düzeltmesi kamera hatası, işlem kapanışı ve firmware sonucu için Windows ANSI kodlaması taklit edilerek sınanır. Paket başlangıç testi de Türkçe mesajı denetler.

19 kaynak testi geçti. Windows exe GitHub Actions Windows ortamında derlenir. Kamera sürücüsü/libusbK ve OBS Virtual Camera gereksinimleri değişmedi. Uygulama sürücüleri otomatik değiştirmez; firmware/SDK pakete dahil değildir.

Gerçek Kinect, fiziksel Windows 10 ve gerçek OBS görüşmesi bu değişiklik için test edilmedi.
