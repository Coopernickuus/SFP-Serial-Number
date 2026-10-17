# SFP Seri Numaraları

Sürüm **1.1.1**. Karekod içindeki `␝S` ile sonraki `␝` veya `]S` ile sonraki `]` arasını alır, baştaki alan tanımlayıcı `S` harfini çıkarır. Örneğin `]SHA20230241879]10D2023` → `HA20230241879`. Sabit seri uzunluğu kullanılmaz; Q1/10D ve sonraki alanlar alınmaz. [Okuyucu örnekleri ve güncelleme notları](OKUYUCU_NOTLARI.md).

Tarayıcı sürümü için Python 3.9 veya üzeri yeterlidir; ek paket ve internet bağlantısı gerektirmez. Mac masaüstü sürümü de mevcut Python 3 kurulumunu kullanır. Windows EXE Python'u içinde paketler; oluşturulduktan sonra kullanıcıya Python kurdurmaz.

## Arayüz ile kullanım

1. Mac'te **SFP Seri Numaraları.app** dosyasını açın. Uygulama kendi penceresinde açılır; Terminal gerekmez. `.app` dosyası `serial_number.py` ve `ui` klasörüyle aynı klasörde kalmalıdır. **Baslat.command** da bu uygulamayı açar. Windows'ta hazırlanmış EXE'yi açın; EXE henüz oluşturulmadıysa aşağıdaki Windows bölümünü izleyin.
2. Tarayıcı sürümünü kullanmak isterseniz bu klasörde `python3 serial_number.py` veya Windows'ta **Baslat.bat** çalıştırın; `http://127.0.0.1:8765` açılır. Yalnızca bu yöntemle açılan sunucu için terminal penceresini açık tutun. Aynı liste zaten açıksa mevcut sunucu kullanılır.
3. **Karekod okut** alanına tıklayıp okuyucuyla okutun. Okuyucunun okuma sonu Enter veya Tab tuşu gönderiyorsa kayıt otomatik eklenir; odak girişte kalır. Elle yapıştırırken Enter'a veya **Seri numarasını ekle** düğmesine basın. Birden fazla karekodu ayrı satırlarda yapıştırabilirsiniz.
4. Mevcut dosyalar için **Dosya seçin** ile `.xlsx`, `.csv`, `.tsv` veya `.txt` seçin. Excel'in tüm çalışma sayfaları ve hücreleri taranır. Başlıklar ve karekod içermeyen hücreler atlanır; bozuk karekodların konumu gösterilir. Formüller çalıştırılmaz ve formüllü hücreler okunmaz. Şifreli Excel ve eski `.xls` desteklenmez; Excel'den şifresiz `.xlsx` olarak kaydedin.
5. **Tümünü kopyala** ile Excel'e tek sütun yapıştırın. **TXT indir** veya **CSV indir** ile yalnızca seri numaralarını alın. CSV'de bir başlık satırı bulunur. Sadece rakamlardan oluşan veya sıfırla başlayan seri numaraları için CSV'yi Excel'in **Veri → Metin/CSV'den** menüsüyle açıp sütun türünü **Metin** seçin; Excel doğrudan açılan CSV değerlerini sayıya çevirebilir. TXT ham değerleri aynen korur.

Her başarılı kayıt `data/seri_numaralari.sqlite3` dosyasına anında yazılır. Uygulamayı kapatıp açınca liste korunur. Aynı seri ikinci kez eklenmez ve tekrar uyarısı gösterilir. Büyük/küçük harf ve baştaki sıfırlar korunur. Kayıt zamanı ve kaynak bilgisi arayüzde görüntülenir. 1.000 kayıttan sonra ekranda son 1.000 kayıt gösterilir; kopyalama ve indirme her zaman bütün listeyi içerir. Arama, ekranda yüklenen kayıtlar içinde çalışır.

Masaüstü penceresini kapatınca uygulamanın kendi başlattığı sunucu da kapanır. Önceden terminalden başlatılmış bir sunucu kullanılıyorsa onu terminalde **Ctrl+C** ile kapatın. Mac/tarayıcı kayıtlarını yedeklemek için uygulama kapalıyken `data` klasörünü kopyalayın. Windows masaüstü kayıtları `%LOCALAPPDATA%\SFP Seri Numaralari` klasöründedir. Başka Mac'e taşırken proje klasörünün tamamını kopyalayın; hedef bilgisayarda Python 3 bulunmalıdır.

Kayıt listesindeki **Listeyi sıfırla** düğmesiyle yeni bir listeye başlayabilirsiniz. Silinecek toplam kayıt sayısı gösterilir; onay verirseniz bütün seri kayıtları kalıcı olarak temizlenir. Arama filtresi açık olsa da tüm liste sıfırlanır. İptal ederseniz kayıtlar korunur. Liste boşken veya okutma/dosya aktarma devam ederken düğme kapalıdır.

## Okuyucu ayarı

Okuyucu klavye gibi yazan USB HID modunda çalışmalı; okuma sonu için **Enter** önerilir. Uygulama şunları tanır:

- Görünen `␝`, `␞`, `␄` karakterleri.
- Okuyucunun GS yerine gönderdiği `]` ayracı: `]Sseri]Q1` → `seri`.
- Gerçek ASCII GS, RS ve EOT kontrol karakterleri.
- Excel/metin gösterimleri: `_x001D_`, `\x1d`, `\u001d` (RS ve EOT karşılıkları da kabul edilir).
- Arayüz odaktayken **Ctrl+] → GS**, **Ctrl+Shift+6 → RS**, **Ctrl+D → EOT**. **Ctrl+M/J** kayıt gönderir.

GS'nin `]` olarak gelmesi desteklenir; bu okuyucu için ayırıcıyı yeniden ayarlamak gerekmez. Ayırıcılar tamamen kaybolursa program tahmin etmez; açıklamalı hata gösterir. Fiziksel okuyucuyla ilk denemeyi etiket üzerindeki seriyle karşılaştırın. Excel'de hücreler arasında aşırı ilerleme varsa cihazın okuma sonu (suffix) tuşlarını kontrol edin. Menü adları modele göre değişir.

## Arayüzsüz toplu işlem

```bash
python3 serial_number.py --input "SFP Seri Numaralar.xlsx" --output "outputs/seri_numaralari.txt"
python3 serial_number.py --input "SFP Seri Numaralar.xlsx" --output "outputs/seri_numaralari.csv"
```

Hem çıktı dosyası yazılır hem de ortak kalıcı listeye ekleme yapılır. Çıktı, seçilen kaynak dosyadan çıkarılan benzersiz serileri kaynak sırasıyla içerir; seriler daha önce veritabanına alınmış olsa da çıktıda bulunur. `--output` verilmezse `outputs/seri_numaralari.txt` kullanılır. Çıktı dosyası varsa üzerine yazılır; kaynak dosyaya ve veritabanına çıktı yazılmasına izin verilmez. Geçerli kayıtlar alınır, sorunlu kayıtlar terminale bildirilir; kısmi hata durumunda çıkış kodu 1, dosya/çalıştırma hatasında 2 olur.

Farklı bir liste için `--db "data/baska_liste.sqlite3"`, farklı port için `--port 8766`, tarayıcıyı otomatik açmamak için `--no-browser` kullanın. Arayüz yalnızca bu bilgisayardaki `127.0.0.1` adresinde çalışır.

Portu başka bir program veya farklı bir kayıt listesi kullanıyorsa açıklamalı uyarı gösterilir. Bu durumda `python3 serial_number.py --port 8766` ile farklı port seçebilirsiniz.

## Ekrandaki yazıları değiştirme

Başlık ve açıklamalar `ui/index.html`, işlem mesajları `ui/app.js`, görünüm `ui/style.css` içindedir. Kaydedip Mac uygulamasında **⌘ + R** ile yenileyin. Windows EXE'nin yanındaki `ui` klasörünü düzenleyip uygulamayı yeniden açın. Bu dosyalar için yeniden derleme gerekmez. Örnekli anlatım: [METINLERI_DUZENLEME.md](METINLERI_DUZENLEME.md).

## Windows EXE oluşturma

Bu bilgisayarda Windows EXE henüz derlenmedi. İki yöntem hazırdır:

1. **Windows bilgisayarda:** Yeni kaynak paketini ayrı bir klasöre çıkarın. Derleme bilgisayarında Python 3.11–3.15 ve internet bağlantısı bulunmalı; mevcut Python 3.15 kurulumunuzu kullanabilirsiniz. **Windows_EXE_Olustur.bat** dosyasını açın; `py -3`, `python` veya `python3` ile yüklü Python bulunur ve kullanılan sürüm ekrana yazılır. Bağımlılıklar Python sürümü ve mimarisine özel `.build/windows-venv-py315-win-amd64` gibi bir ortama kurulur. Önceden 3.12 ile oluşturulmuş ortam yeniden kullanılmaz. Paket `dist/SFP-Windows` içinde oluşur; `SURUM.txt` dosyasında sürümü kontrol edin. Bu klasörün tamamını kullanıcıya verin; kullanıcı Python kurmadan EXE'yi açabilir. Microsoft Edge WebView2 Runtime gereklidir: [resmi indirme sayfası](https://developer.microsoft.com/microsoft-edge/webview2/).
2. **GitHub üzerinden:** Kaynakları, `desktop` klasörünü, `METINLERI_DUZENLEME.md` dosyasını ve gizli `.github/workflows/windows-exe.yml` dosyasını deponuza yükleyin. GitHub'da **Actions → Windows EXE oluştur → Run workflow** seçin. Başarılı çalışmanın **Artifacts** bölümündeki **SFP-Windows** paketini indirin. Akış Python 3.15 kullanır; EXE üretildikten sonra paket dosyalarını ve yerel sunucuyu geçici kayıtlarla kontrol eder. Gerçek Windows arayüzü ve fiziksel okuyucu ayrıca denenmelidir.

Oluşturucu Python 3.12 sürümüne sabitlenmez. Python 3.15 desteği bulunan [pythonnet 3.2.1](https://pypi.org/project/pythonnet/3.2.1/) ve [PyInstaller 6.22.3](https://pypi.org/project/pyinstaller/6.22.3/) kullanılır.

Windows paketi ve Mac `.app` birbirinden ayrıdır. Windows derlemesinde imzalama yapılmaz. Derleme araçları: [PyInstaller](https://pyinstaller.org/en/stable/) ve [pywebview](https://pywebview.flowrl.com/guide/freezing.html).

## Mac uygulamasını yeniden derleme

Swift pencere kodu `desktop/macos.swift` içindedir. Apple Command Line Tools yüklü bir Mac'te **Mac_Uygulama_Olustur.command** dosyasını açın. Mevcut Mac mimarisi için `SFP Seri Numaraları.app` oluşturulur. HTML/CSS/JavaScript metinlerini değiştirirken bu adım gerekmez.

`Baslat.command` kullanıldığında Terminal işlemi hemen biter. Pencerenin otomatik kapanması Terminal profilinin **Ayarlar → Profiller → Kabuk → Kabuk kapandığında** seçeneğine bağlıdır. Doğrudan `.app` dosyasını açmak Terminal'i hiç açmaz. [Apple açıklaması](https://support.apple.com/guide/terminal/change-profiles-shell-settings-trmlshll/mac)

## Doğrulama

```bash
python3 -m unittest discover -s tests -v
node --test tests/scanner_input.test.cjs
```

Testler eski ve yeni okuyucu çıktılarının aynı serileri verdiğini, farklı ayırıcıları, hatalı/çoklu alanları, dosyadan aktarmayı, kalıcı kayıtları, tekrarları, HTTP uçlarını, dışa aktarmayı ve Tab/Enter ile odak davranışını denetler. JavaScript testleri için Node.js gerekir; EXE'yi oluşturmak veya çalıştırmak için Node.js gerekmez. Fiziksel okuyucu doğrulaması ayrıca yapılmalıdır.
