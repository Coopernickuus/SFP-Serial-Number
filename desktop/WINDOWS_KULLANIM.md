# Windows uygulaması

1. İndirdiğiniz ZIP dosyasını bir klasöre çıkarın.
2. **SFP Seri Numaralari.exe** dosyasına çift tıklayın.
3. Uygulama kendi penceresinde açılır. Python veya Terminal açmanız gerekmez.
4. Pencereyi kapatınca uygulama kapanır. Kayıt listeniz korunur.

Arayüz için Microsoft Edge WebView2 Runtime gerekir. Bilgisayarda yoksa Microsoft'un resmi sayfasından kurun: https://developer.microsoft.com/microsoft-edge/webview2/

Kayıtlar `%LOCALAPPDATA%\SFP Seri Numaralari\seri_numaralari.sqlite3` dosyasında saklanır. Yedeklemek için uygulama kapalıyken bu dosyayı kopyalayın. Mac'teki kayıtlar Windows'a kendiliğinden taşınmaz; aktarım için çıktı dosyalarınızı ayrıca alın.

Metinleri değiştirmek için EXE'nin yanındaki `ui/index.html` dosyasını bir metin düzenleyicide açın. Sonra uygulamayı kapatıp yeniden açın. Detaylar **METINLERI_DUZENLEME.md** dosyasındadır.

Uygulama henüz dijital olarak imzalanmamıştır. Hata ayrıntıları aynı kayıt klasöründeki `masaustu.log` dosyasına yazılır.
