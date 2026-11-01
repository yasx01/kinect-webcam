# Kinect Webcam — ilk Windows sürümü

Hedef: Windows 10 1809+ ve Windows 11, 64 bit. Linux v15 kaynakları değiştirilmedi.

Çıktılar: dist/KinectWebcam-Windows-x64.exe ve dist/KinectWebcam-Windows-x64.zip.
Kaynak/derleme commit'i: 4535c2ec861b4efc4fd58ca63e0acdc1134bf72d.
Windows derleme ve test kaydı: https://github.com/yasx01/kinect-webcam/actions/runs/41283398900
GitHub derleme çıktısı: KinectWebcam-Windows-x64 (artifact 13074536024).

## Özellikler

- libfreenect ile Kinect RGB kamerası; ana ekranda canlı önizleme, Test Al ve Canlıya dön.
- Kurulu OBS Virtual Camera üzerinden Chrome/Edge/Brave/Firefox'a görüntü çıkışı.
- Kinect mikrofonunu sistem genelinde sessize alma / sesi açma.
- Beş saniyelik yerel mikrofon kayıt ve dinleme testi; dört kanallı yerel ses biçimini mono PCM'e dönüştürme.
- İlk kurulum rehberi; sürücüleri otomatik değiştirmez. Kendi UACFirmware dosyasını seçerek USB ses hazırlığı yapma.

## Doğrulama ve sınırlar

Windows runner üzerinde 17 kaynak testi geçti. Paketlenen exe ayrıca başlatıldı; native DLL yükleme, firmware yükleyicisinin başlangıcı, GUI açılışı, ayrı kamera sürecinden yapay kare/sanal kamera gönderimi ve mikrofon test penceresinin kayıt başlatmadan açılması geçti. Rapor: dist/KinectWebcam-Windows-selftest.json.

İndirilen paketin SHA-256 özeti GitHub artifact özetiyle eşleşti. EXE başlığı PE/AMD64 olarak doğrulandı; EXE özeti Windows'ta üretilen manifest ile eşleşti.

Gerçek Kinect, gerçek OBS görüşmesi ve fiziksel Windows 10 bilgisayar testi yapılmadı. Test runner Windows Server 2022'dir; donanım uyumluluğu garantisi verilmez. İlk kullanımda libusbK kamera sürücüsü ve tarayıcı çıkışı için OBS hazırlanmalıdır. USB ses aygıtında normal Windows USB Audio sürücüsü korunmalıdır. Ayrıntılar: windows/WINDOWS.md.

ZIP lisans bildirimlerini ve kurulum rehberini içerir. Microsoft firmware'i, SDK/MSI veya Microsoft sürücüsü içermez. Kod GitHub'a commit edildi; exe git geçmişine değil GitHub Actions derleme çıktısına eklendi. Derleme çıktısı GitHub'ın saklama süresine tabidir.

EXE SHA-256: 93790bc3ac848e32cd34381fdccf7aa951fe6ab0e88249a0630b5a7920bcfa84
