# İsteğe bağlı Microsoft Runtime başvurusu

Bu klasör uygulama paketlerine dahil edilmez. Microsoft'un orijinal sürücüsünün yerine geçmez; resmi dosyanın kaynağını ve doğrulama bilgisini kaydeder.

- [Microsoft Kinect for Windows Runtime v1.8 resmi sayfası](https://www.microsoft.com/en-us/download/details.aspx?id=40277)
- [Orijinal Microsoft indirmesi](https://download.microsoft.com/download/e/c/5/ec50686b-82f4-4dbf-a922-980183b214e6/KinectRuntime-v1.8-Setup.exe)
- Sürüm: 1.8.0.595. Dosya boyutu: 116273144 bayt.
- SHA-256: `f4d4143fb0f0a8d276889c077bfc8af42bfe99c128cadab5e316bf015a9858e9`.

## Dosya neden burada bulunmuyor?

Resmi kurulum paketinin İngilizce lisansı incelendi. SCOPE OF LICENSE bölümünde başkalarının kopyalaması için yayımlamaya izin verilmediği belirtiliyor. BACKUP COPY bölümü kişisel yeniden kurulum için bir yedek kopyaya izin veriyor. Herkese açık bir GitHub dosya aynası bu kişisel yedekle aynı şey değildir. Bu yüzden depo orijinal ikili dosyayı barındırmaz; kaynak ve özet bilgisiyle resmi indirmeye yönlendirir.

Lisans ayrıca bu Runtime'ı Kinect for Windows sensörüyle sınırlar; Xbox 360 sensörü için kullanım hakkı tanımaz. Microsoft'un resmi gereksinimleri eski Windows sürümlerini listeler; Windows 10/11 uyumluluğu burada garanti edilmez.

## Kurulum seçimi

Kinect Webcam'in Windows sürümü libusbK/libfreenect kullanır; bu Microsoft Runtime kurulumu gerekli değildir. Microsoft sürücüsüne geçmek Kinect Webcam'in kameraya erişimini etkileyebilir. Bu başvuru, Microsoft Runtime isteyen farklı uygulamalar için isteğe bağlıdır. Dosya otomatik indirilmez veya çalıştırılmaz. Microsoft'un şartlarını ve kendi sensörünü kontrol ederek resmi yükleyiciyi kullanıcı kendisi çalıştırır.

PowerShell ile indirilen dosyayı doğrulamak için:

```powershell
Get-FileHash .\KinectRuntime-v1.8-Setup.exe -Algorithm SHA256
```

Komut dosyayı değiştirmez; çıkan özet yukarıdakiyle aynı olmalıdır. Mevcut Microsoft ikili dosyasını yeniden yayımlamaya ayrıca izin veren bir belge sağlanırsa dağıtım yeniden değerlendirilebilir.
