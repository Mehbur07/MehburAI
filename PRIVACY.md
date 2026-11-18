# MehburAI Gizlilik Politikası

**Son güncelleme:** 19 Kasım 2026

MehburAI, bilgisayarında çalışan bir masaüstü yapay zeka asistanıdır. Bu sayfa, uygulamanın hangi
verileri nerede sakladığını ve hangi durumlarda üçüncü taraf servislere veri gönderdiğini açıklar.

Kısaca: **Verilerin büyük bölümü senin bilgisayarında kalır. Geliştirici olarak sohbetlerini, hafızanı,
dosyalarını ya da kullanımını görmem, toplamam ve satmam.**

## 1. Hesap bilgileri

MehburAI'yi kullanmak için e-posta ve şifreyle kayıt olursun ya da Google ile giriş yaparsın.
Giriş işlemlerini [Supabase](https://supabase.com) yürütür.

- **E-posta adresin** Supabase'te hesabını tanımlamak için saklanır.
- **Şifren** düz metin olarak saklanmaz; Supabase tarafından tek yönlü şifrelenerek (hash) tutulur.
  Geliştirici olarak şifreni göremem.
- **Google ile giriş** yaparsan Google, Supabase'e e-posta adresini ve temel profil bilgini (ad) iletir.
  Google hesabının şifresi MehburAI'ye hiçbir zaman gelmez.
- **Oturum anahtarları** bilgisayarında, uygulamanın `data/config.json` dosyasında tutulur. Çıkış yapınca silinir.
- Hesap doğrulama ve şifre sıfırlama e-postaları, geliştiricinin ayarladığı e-posta servisi üzerinden gönderilir.

## 2. Bilgisayarında kalan veriler

Aşağıdakiler yalnızca uygulamanın `data/` klasöründe, senin bilgisayarında saklanır ve geliştiriciye gönderilmez:

- Sohbetlerin ve mesaj geçmişin, "hafıza" (öğrenilen soru-cevaplar)
- Hatırlatıcıların ve alarmların
- Ayarların (tema, dil, ses seçimi vb.) ve girdiğin API anahtarları (Gemini, OpenAI, Anthropic)
- Telegram bot bilgilerin, kamerayla ya da ekran görüntüsüyle aldığın görüntüler (kullanırsan)

Bu verileri silmek için uygulamayı kaldırıp `data/` klasörünü silmen yeterlidir.

## 3. Üçüncü taraf servislere giden veriler

MehburAI bazı özellikleri için dış servisleri kullanır. Bunlara **yalnızca ilgili özelliği kullandığında**
ve gerektiği kadar veri gider:

| Servis | Ne zaman | Gönderilen |
|---|---|---|
| Google Gemini | Çevrim içiyken sorular, eklediğin dosya/fotoğraf, "kamerama bak" gibi komutlarda kamera karesi | Sorun, ekli dosya içeriği ya da görüntü |
| OpenAI / Anthropic | Yalnızca kendi anahtarını girip seçersen | Sorun |
| Wikipedia, Reddit, Stack Exchange | Bilgi/ürün araması | Arama ifaden |
| Pollinations | Ücretsiz görsel üretimi | Görsel isteğin (metin) |
| Telegram | Telegram uzaktan kontrolünü açarsan | Senin botun üzerinden yazışmalar |
| Microsoft (Edge sesleri) | Sesli yanıt seslendirilirken | Seslendirilecek yanıt metni |
| GitHub | Güncelleme denetimi ve indirme | Sürüm sorgusu (IP adresin GitHub'a görünür) |
| Supabase / Google | Hesap işlemleri | Bkz. bölüm 1 |

Bu servislerin kendi gizlilik politikaları geçerlidir. Çevrim dışıyken uygulama bu servislere istek atmaz;
yalnızca yerel hafızanı kullanır.

## 4. Geliştirici ne toplar?

Hiçbir şey. Uygulamada kullanımını izleyen, analiz eden ya da geliştiriciye veri gönderen bir
analitik/telemetri bileşeni yoktur. Verilerini üçüncü kişilere satmam ya da reklam amacıyla paylaşmam.

## 5. Hesabını ve verilerini silme

- Yerel verilerini silmek için bölüm 2'ye bak.
- Hesabının (e-posta kaydının) Supabase'ten silinmesini istersen aşağıdaki iletişim yolundan yaz.

## 6. Çocuklar

MehburAI 13 yaşın altındaki çocuklara yönelik değildir ve bilerek onların verisini toplamaz.

## 7. Değişiklikler

Bu politika zaman zaman güncellenebilir. Güncel hâli her zaman bu sayfadadır; "Son güncelleme" tarihine bak.

## 8. İletişim

Sorular ve talepler için GitHub'da bir kayıt aç: <https://github.com/Mehbur07/MehburAI/issues>

Geliştirici: Mehbur07 (Mehmet Burak ŞAHİN)
