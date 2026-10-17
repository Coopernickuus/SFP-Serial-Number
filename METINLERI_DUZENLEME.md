# Ekrandaki yazıları değiştirme

Arayüz dosyaları `ui` klasöründedir. Bir kod/metin düzenleyiciyle açın; Word veya zengin metin biçimi kullanmayın. Dosyaları UTF-8 olarak kaydedin.

| Değiştirmek istediğiniz bölüm | Dosya |
| --- | --- |
| Başlıklar, açıklamalar, düğme adları ve giriş alanı örneği | `ui/index.html` |
| Kayıt, hata, tekrar ve sıfırlama mesajları | `ui/app.js` |
| Renkler, yazı boyutları, boşluklar ve yerleşim | `ui/style.css` |
| Dosya okuma ve doğrulama hataları | `serial_number.py` — Windows EXE için yeniden derleme gerekir |

Örneğin `ui/index.html` içinde:

```html
<h1>Okutun. Seri numarası kaydedilsin.</h1>
```

satırını şöyle değiştirebilirsiniz:

```html
<h1>SFP seri numarası toplama ekranı</h1>
```

HTML'de `>` ve `<` arasındaki görünen metinleri düzenleyin. `id="scan"`, `id="reset"` gibi kimlikleri, `src` ve `href` bağlantılarını koruyun; düğmeler bu kimliklerle çalışır. `<`, `>` ve `&` karakterlerini metin olarak yazmak için sırasıyla `&lt;`, `&gt;` ve `&amp;` kullanın.

JavaScript mesajlarında yalnızca tırnak içindeki metni değiştirin. `${report.deleted}` gibi değişkenleri ve çevresindeki tırnak/backtick işaretlerini koruyun.

Kaydettikten sonra:

- Mac uygulamasında **⌘ + R** veya **SFP → Arayüzü yenile** menüsünü kullanın.
- Tarayıcıda sayfayı yenileyin.
- Windows EXE'yi kapatıp yeniden açın.

Windows dağıtımında EXE'nin yanında bulunan `ui` klasörü, paket içindeki varsayılan arayüzün yerine kullanılır. Bu üç dosyadaki metin ve görünüm değişiklikleri için EXE'yi yeniden üretmeniz gerekmez. Python kodunu değiştirdiğinizde yeniden EXE oluşturun.
