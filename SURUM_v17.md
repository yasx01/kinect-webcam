# Kinect Webcam v17

Referans alınan eski arayüze yakın koyu renkler, yuvarlak düğmeler ve ayrı kontrol/görüntü/günlük kartları kullanılır. İlk açılış 760 × 720; minimum 720 × 640. Daha önce kaydedilmiş açık/koyu tema tercihi korunur; yeni kullanıcı için koyu tema seçilir.

- Kare Al / Test Et ana kontrol satırında; canlıya dön görüntü kartındadır.
- Mikrofon Testi mikrofon kartına taşındı. Günlük açılışta görünür, düğmesiyle gizlenebilir.
- Kamera köprüleri, izin kontrolleri ve ilk kurulum davranışı v16 ile aynı; OBS Linux tarayıcı çıkışı için zorunlu değildir.
- Microsoft firmware/SDK pakete eklenmez. Yerel firmware seçimi isteğe bağlıdır.
- v16, önceki sürümler ve original-files arşivi korunur.

120 otomatik test, Python/Bash sözdizimi denetimi ve küçük pencere yerleşim testi geçti. Önizlemeler kamera/mikrofon açılmadan oluşturuldu. Gerçek Kinect ve temiz Fedora KDE kurulumu bu değişiklik için test edilmedi.

Derleme: `bash packaging/build-appimage-v17.sh`. Çıktı: `dist/KinectWebcam-v17-x86_64.AppImage`.
