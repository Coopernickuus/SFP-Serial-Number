# Karekod okuyucu — sürüm 1.1.0

Seri numarası, bir alan ayracının hemen ardından gelen **S** harfinden sonra başlar ve **bir sonraki alan ayracından hemen önce** biter. Sabit karakter sayısı kullanılmaz. Baştaki S alan tanımlayıcısı çıkarılır; serinin kendi S harfi veya baştaki sıfırları korunur.

İki gösterim aynı şekilde okunur:

```text
␝SHA20230240976␝Q1  →  HA20230240976
]SHA20230240976]Q1  →  HA20230240976
```

`Q1`, `10D2023`, ürün kodu ve diğer alanlar seri numarasına dahil edilmez. Gerçek GS, görünen ␝ ve daha önce desteklenen kaçış gösterimleri de çalışmaya devam eder.

Son gönderdiğiniz çıktıların önceki örneklerle karşılaştırması:

| Sıra | Alınacak seri numarası | Sonraki alan |
| --- | --- | --- |
| 1 | HA20230240976 | Q1 |
| 2 | MA18210960908 | Q1 |
| 3 | FR202936065 | Q1 |
| 4 | HA20230241879 | 10D2023 |
| 5 | 1000082001138 | 10D2309 |

## Okutma sonrası ilerleme

Uygulamanın karekod girişinde **Enter** veya **Tab** kaydı tamamlar ve odak giriş alanında kalır. Okuma sonundaki ek Tab ve gezinme tuşları kısa bir süre tüketilir. Uzun metin alanda satıra sarılır; alan yatay olarak genişlemez. Normal boş alandaki Tab ve Shift+Tab gezinmesi korunur.

Excel'de görülen hücre ilerlemesi uygulama koduyla değiştirilemez. Okuyucunun **okuma sonu / suffix** ayarında yalnızca **Enter** seçin; ilave Tab veya gezinme tuşu gönderen ayarları kontrol edin. Ayarın tam adı ve kontrol karakterlerinin nasıl gönderildiği cihaz modeline bağlıdır. Fiziksel okuyucunun gönderdiği tuş dizisi bu Mac'te ölçülmedi.

## Windows'a güncellemeyi aktarma

Eski EXE'nin yalnızca `ui` klasörünü değiştirmek yeterli değildir: seri numarasını ayıklayan Python kodu EXE'nin içindedir. Yeni kaynak paketini ayrı bir klasöre çıkarın. Windows'ta Python 3.12 kurulu ve internet bağlantısı açıkken **Windows_EXE_Olustur.bat** dosyasını çalıştırın.

Yeni paket `dist/SFP-Windows` klasörüne yazılır. EXE ile yanındaki `ui` klasörünü birlikte kullanın. `SURUM.txt` içinde **1.1.0** yazmalıdır. Çalışan eski uygulamayı kapattıktan sonra yeni EXE'yi açın. Önceki kayıtlar aynı kullanıcı kayıt klasöründe tutulur.
