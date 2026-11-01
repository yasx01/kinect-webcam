# Kinect Webcam v16 — indirilebilir Linux AppImage

## Kullanıcı için değişiklikler

- Fedora KDE x86_64 için AppImage, GitHub Releases üzerinden doğrudan indirilebilir.
- Microsoft UACFirmware, SDK/MSI veya Windows sürücüsü pakete eklenmez.
- İlk kurulum ekranında kullanıcı yerel UACFirmware dosyasını seçebilir. Dosya SHA-256 ile doğrulanır ve ancak yönetici onayıyla kurulur.
- Firmware seçilmeden kamera kurulumu yapılabilir; mikrofon hazırlığı isteğe bağlı gösterilir. Var olan mikrofon otomatik yükleme kuralı bu durumda korunur.
- OBS uygulaması zorunlu paketlerden çıkarılmıştır. Firefox doğrudan PipeWire, Chromium V4L2 sanal kamera yolunu kullanır.
- v15 ve Windows sürümü korunmuştur. Sistem geneline kurulum veya sudo işlemi bu geliştirme sırasında yapılmamıştır.

## Doğrulama

119 otomatik test, Python ve Bash sözdizimi denetimleri geçti. Yeni paketten çıkarılan AppRun offscreen açıldı. Paket içindeki Python dosyalarının kaynakla aynı olduğu, yükleyici manifestinin doğrulandığı ve firmware olmadan hazırlık denetiminin çalıştığı kontrol edildi. Bilinen firmware bayt dizisi de dahil olmak üzere paket içeriği tarandı; firmware/SDK bulunmadı.

REA, AppImage'dan çıkarılan dosyalardan oluşturulmuş ZIP envanterlerini statik olarak inceledi. Bu, AppImage bootloader'ının tersine mühendisliği veya gerçek kamera davranışının gözlenmesi değildir. v16 envanteri 23 kayıt içerir; seçili görünümde AppRun ve açık kaynak kinect_upload_fw bulunur, UACFirmware bulunmaz.

- v15 envanter özeti: ev_b166511e108a0d3ea0a35790aa157c135bf6ca5fe10214f55efd6927013e3355
- v16 envanter özeti: ev_06ce91e3bb52d19b0e588c9a7977e1e992619e5dec24c3b8d9ad08e58b70133c
- v16 seçili üyeler: ev_f72664ddaeecdf7d74fc97eda986e8308c16b45fb46f92ebb3be28e28386427f

Gerçek Kinect, temiz Fedora kurulumu, USB çıkarıp takma veya gerçek görüşme uygulaması testi yapılmadı. İlk kurulum Fedora x86_64 içindir; tüm Linux dağıtımlarında çalışma garantisi verilmez. Bu ince AppImage sistem bağımlılıkları kullanır; ilk hazırlık internet ve yönetici onayı gerektirebilir.

## Çıktı

KinectWebcam-v16-x86_64.AppImage
SHA-256: 272e25abb1a67aba54034690ba8bc38d636c51c92bed6be3215c15cc27662bc3

[Linux indirmesi](https://github.com/yasx01/kinect-webcam/releases/tag/linux-v16-preview) · [Kurulum rehberi](docs/LINUX.md)
