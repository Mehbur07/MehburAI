# ⚡ MehburAI — Hibrit Çevrim İçi & Çevrim Dışı Masaüstü Yapay Zeka

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-00F0FF?style=for-the-badge&logo=python&logoColor=black" alt="Python Version" />
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-008B99?style=for-the-badge" alt="CustomTkinter" />
  <img src="https://img.shields.io/badge/AI-Google_Gemini-FF3366?style=for-the-badge&logo=google" alt="Gemini AI" />
  <img src="https://img.shields.io/badge/Theme-Neon_Cyan_%26_Black-07070B?style=for-the-badge" alt="Neon Theme" />
  <img src="https://img.shields.io/badge/License-MIT-00FF88?style=for-the-badge" alt="License" />
</p>

**MehburAI**, internet bağlantısını dinamik olarak algılayan, çevrim içiyken **Google Gemini API** ve güvenilir kaynaklar (**Wikipedia OpenSearch & REST v1**) üzerinden soruları yanıtlayıp otomatik olarak yerel hafızasına kaydeden, çevrim dışıyken ise **Türkçe Morfolojik Semantik Benzerlik Motoru** ile hafızasındaki bilgileri hatasız getiren modern bir masaüstü yapay zeka asistanıdır.

---

## 🌟 Temel Özellikler

- 🌐 **Sıfır Gecikmeli Ağ Algılama:** Cloudflare (`1.1.1.1`) DNS socket kontrolü ile gerçek zamanlı canlı bağlantı durumu (`🟢 Çevrimiçi` / `🔴 Çevrimdışı`).
- 🧠 **Öğrenen Kalıcı Bellek (SQLite):** Çevrim içiyken sorulan her soru ve cevabı hafızaya kaydeder (*"Eğer bu soru sorulursa bu cevabı ver"*).
- 🔍 **Türkçe Semantik Eşleme:** Soru farklı kelimeler veya eklerle sorulsa bile (Karakter N-Gram + Kök Jaccard + Token Kosinüs Benzerliği) hafızadaki doğru cevabı bulur.
- ⚡ **Neon Cyan & Siyah Masaüstü Arayüzü:** CustomTkinter ile donmayan asenkron arka plan thread mimarisi.
- 💻 **Gerçek Bilgisayar Erişimi:** Sadece sabit birkaç uygulama değil — *herhangi bir programı* adından bulup açar (Spotify, Word, Chrome, Ayarlar, Kamera…), klasör açar, dosya arar, klasör/dosya oluşturur, **ses / parlaklık** ayarlar, ekranı kilitler, uyku moduna alır, **ekran görüntüsü** alır ve (onaylı, iptal edilebilir) **kapatma / yeniden başlatma** komutlarını çalıştırır.
- 🤬 **Yazım Hatası Toleranslı Küfür Filtresi:** `orospo`, `aptl`, `çomarr` gibi bilerek/yanlışlıkla bozuk yazılmış hakaretleri de yakalar; `solak`, `yürek`, `sülük` gibi masum kelimelere bulaşmaz.
- 💬 **Sohbetler (her biri kendi geçmişi + ruh hali):** Sohbet sekmesinin solunda sohbet listesi, **➕ Yeni Sohbet** ve neon kırmızı **🗑 Bu Sohbeti Sil**. Her sohbet ayrı bir konuşma; mesajları ve "ruh hali" birbirinden bağımsız.
- 😤 **Sohbete Özel Üslup — Küfüre Misilleme:** Bir sohbette ilk kez küfür edilince MehburAI *"Sana böyle laflar yakışıyor mu?"* der. **"yakışıyor"** dersen *"O zaman bana da yakışıyor…"* deyip o sohbette sertleşir: artık küfre *"asıl sen / asıl ben"* ile karşılık verir (*"senin ben ananı s…"* → *"Asıl ben senin ananı sikeyim."*, *"oç'sun"* → *"Asıl sen oçsun."*, isim takmalarda Türkçe ünlü uyumlu ek) ve normal yanıtların sonuna sivri bir kuyruk ekler. **"yakışmıyor"** dersen sohbet normale döner. Sohbet listesinde ruh hali ikonlanır (⚠️ kızgın · 😠 kaba). Diğer sohbetler ve Telegram/sesli sohbet bundan etkilenmez.
- ⌨️ **Harf Harf Yazma Animasyonu:** MehburAI yanıtları tek seferde değil, daktilo efektiyle yazılır (`Theme.TYPEWRITER_MS` — `0` yaparsan anında).
- 🎨 **Uygulama Logosu:** `assets/logo.png` — pencere/görev çubuğu ikonu, üst bar logosu ve sistem tepsisi ikonu bu görseli kullanır (`logo.ico` çok boyutlu olarak otomatik üretilir). Hazır bir neon logo `assets/make_logo.py` ile üretilir; kendi görselini istersen doğrudan `assets/logo.png` üzerine yaz.
- 🛡️ **Güvenlik Modu (Yetkisiz Erişim Alarmı):** Ayarlardan korumalı klasör/program yolları, bir şifre ve Telegram bilgileri girilir. Korunan yol **kapalıyken açıldığında** _veya korunan bir dosya/klasör **silinmeye çalışıldığında**_ MehburAI tüm ekranı karartıp **şifre sorar**; şifre yanlış girilir ya da ekran kapatılırsa açılan program/klasör kapatılır (**silme girişiminde dosya gizli yedekten otomatik geri yüklenir**), web kameradan fotoğraf çekilip cihaz sahibine **Telegram'dan** (`MehburAI (Telegram)` botu) gönderilir ve kişiye *"fotoğrafınız çekildi, kameraya bakın gülümseyin :D"* yazılır. Tepside açık kalan (Telegram/WhatsApp gibi) programları da destekler; laptop uyku moduna geçip uyandığında birikmiş açılışlar için sormaz. Pencereyi kapatsan bile **sistem tepsisinde arka planda çalışır** ve istenirse **Windows açılışında otomatik başlar**. *(Gizli izleme değildir — şifre ekranı ve uyarı açıkça görünür.)*
- 🤖 **Telegram'dan Uzaktan Kontrol:** Ayarlardan `🤖 Telegram'dan uzaktan kontrol` anahtarı açılınca, `MehburAI (Telegram)` botuna yazarak MehburAI'a **uzaktan erişilir** — soru sor, *"not defteri aç"* / *"sesi kıs"* / *"bilgisayarı kapat"* gibi sistem komutları çalıştır, `/ekran` ile ekran görüntüsü, `/foto` ile web kamera karesi, `/aramabaslat` ile sesli görüşme modu, `/dosya <isim>` ile bilgisayardan (Masaüstü, Belgeler, İndirilenler… **ve AppData**) dosya/klasör ara-gönder — birden çok eşleşirse *"hangisini istersin?"* diye **butonla sorar**; klasörse `.zip` yapıp yollar, `/durum` ile güvenlik durumu al, `/guvenlik ac|kapat` ile güvenlik modunu yönet. **Sesli mesaj** da gönderebilirsin — çevrimdışı yazıya çevrilip yanıtlanır (yanlış duyulan kelimelere toleranslı). **Yalnızca cihaz sahibinin Chat ID'si** (Ayarlar'dan girilir, yalnızca yerel `data/config.json`'da durur — kodda/GitHub'da/.exe'de asla yer almaz) komut verebilir; başkasına yalnızca *"⛔ Bu bot özeldir"* yanıtı döner ve komut asla işlenmez. Uzun anket (long-polling) kullanır — dinlenen bir port açmaz, kapalıyken yollanan eski komutları çalıştırmaz.
- 🧠 **Boşta Otomatik Öğrenme:** MehburAI açıkken sen bir süre soru sormazsan arka planda Wikipedia'dan yeni konular öğrenip hafızaya yazar. **Ürünlerde** (telefon, konsol, işlemci…) özellikleri ve eleştirmen/basın değerlendirmesini yine Wikipedia madde bölümlerinden (gerekirse İngilizce maddeden) çeker — normal sorularda da ürün algılanırsa aynısı yapılır. Ayarlar > 🧠 Otomatik Öğrenme'den kapatılabilir.
- 🎨 **Renk Ayarı:** Ayarlar > 🎨 Görünüm'den vurgu rengi ve arka plan tonu (hazır renkler ya da özel renk) seçilir, önizlenir; 'Uygula' uygulamayı yeni renklerle yeniden başlatır.
- 🎤 **Bas-Konuş:** Sohbet kutusundaki mikrofon butonuna basıp konuş; konuşman yazıya çevrilip gönderilir (tekrar basınca durur). 'Hey Mehbur' uyandırma dinlemesi Ayarlar > Sesli Sohbet'ten ayrıca açılır.
- 📦 **Kurulum (`MehburAI.Setup.exe`):** `build_exe.bat` tek dosyalık Setup üretir. Herhangi bir Windows bilgisayarda çalıştırınca (Python gerekmez) `%APPDATA%\MehburAI` altına kurar, masaüstüne kısayol koyar. Türkçe ses modeli ve tüm kütüphaneler dahildir; **Gemini API anahtarı, Telegram bot token'ı ve Telegram ID'si pakete/kaynağa/GitHub'a ASLA girmez** — Ayarlar'dan kullanıcı girer. `scan_secrets.py` bunu her derlemede (kaynak, paket, .exe içi) ve her commit'te (`hooks/pre-commit`, kurmak için `install_hooks.bat`) otomatik doğrular.
- 🎙️ **Sesli Sohbet (yalnız bilgisayarda):** Ayarlardan `🎙️ Sesli Sohbet` açılınca — ya da sohbet kutusundaki 🎤 mikrofon butonuna tıklayınca — MehburAI bilgisayarın mikrofonunu dinler. Yalnızca **"Hey Mehbur"** dediğinde *"Emrinizdeyim efendim"* der (doğal Türkçe ses — Emel/Ahmet, `edge-tts`) ve komutunu bekler; yanıtı sesli verir. Yalın **"Mehbur"** artık TEK BAŞINA uyandırmaz — rastgele konuşmadaki benzer kelimelerle (mecbur, mahmut, mehmet…) karışıp yanlış tetiklenmeyi azaltmak için. Konuşma tanıma **tamamen çevrimdışı** (`vosk`, ~35 MB Türkçe model ilk açılışta iner), yanlış duyulan "Hey Mehbur" biçimlerini (hey melbur, he mecbur…) de anlar. Sohbet kutusundaki tüm yetenekler geçerli — *"Hey Mehbur bilgisayarı kapat"*, *"Hey Mehbur ekran görüntüsü al"* vb.
- 🟦 **JARVIS Ekranı:** Sesli sohbet açıkken uyandırma sözcüğü söylenince Iron Man tarzı **tam ekran dönen nokta küresi** açılır (ana pencere tepside gizli olsa bile). Boşta/yanıt: **neon cyan** • komut dinlerken: **koyu sarı** • hata: **neon kırmızı**. İş bitince kendiliğinden kaybolur, ESC ile kapanır. Ayarlardan kapatılabilir.
- 📞 **Telegram'da "/arama" — Sesli Görüşme Modu:** Bota `/arama` yazınca yanıtlar hem metin hem **sesli mesaj** olarak gelir — karşılıklı sesli mesajlaşmayla gerçek zamanlı bir görüşmeye en yakın deneyim. *(Not: Telegram Bot API bir botun telefonu gerçekten çaldırıp arama başlatmasına izin vermez — bu, o kısıtın içinde en yakın deneyimdir.)* `/aramabitir` ile kapatılır.
- 👁️ **Kamera + Görsel Anlama:** *"Kafama hangi tıraş yakışır?"* dediğinde web kameradan bir kare alır, Gemini'nin görsel anlama yeteneğiyle yüz/kafa şeklini değerlendirip bir saç/tıraş modeli önerir (*"Size buzz cut çok yakışır efendim..."*). *"Elimde ne var?"* dediğinde eldeki nesneyi tanımaya, mümkünse marka/modelini tahmin etmeye çalışır. GUI sohbeti, yerel sesli sohbet ve Telegram'da (▸/arama dahil) aynı şekilde çalışır. Gemini API anahtarı + internet + kamera + OpenCV gerektirir.
- 🎨 **Görsel Stüdyosu (oluşturma + düzenleme):** *"Bana mutlu bir aile çiz"* dediğinde sıfırdan bir görsel üretir; ➕ butonuyla bir fotoğraf ekleyip *"bunu daha kaliteli yap"* dediğinde o fotoğrafı düzenler. Üretilen görsel sohbet balonuna küçük bir önizleme olarak eklenir (tıklayınca büyük hali açılır); Telegram'da fotoğraf olarak gönderilir. Gemini hesabında bir görsel üretim modelinin aktif olması gerekir — yoksa nazikçe haber verir.
- ➕ **Dosya Ekleme:** Sohbet kutusundaki ➕ butonuyla bir metin dosyası (`.txt`, `.md`, `.csv`, `.json`, kod dosyaları…) ekleyip içeriği hakkında soru sorabilirsin — *"gta5hilekodları.txt'deki hileler ne işe yarar?"* MehburAI dosyayı okuyup Gemini ile yalnızca o içeriğe dayanarak yanıtlar (Gemini API anahtarı gerektirir).
- 🌐 **Wikipedia (güvenilir kaynak):** Yanıtlar maddenin yalnızca ilk cümlesi değil; girişi ve önemli bölümleri (~3 bin karakter) derlenir, madde daha uzunsa en alta *"📖 Daha fazlasını okumak için: <Wikipedia bağlantısı>"* eklenir (sohbette tıklanabilir). Gemini anahtarı yokken de bu derleme doğrudan gösterilir. Reddit gibi denetimsiz kaynaklar kaldırıldı — troll/yanıltıcı içerik riski nedeniyle yalnızca Wikipedia kullanılır.
- 😈 **Özel İsim Yanıtı:** *"Adın ne?"*, *"Kimsin?"* gibi sorulara *"Merhaba, ben MehburAI dünyayı ele geçireceğim"* şeklinde özel yanıt verir.
- 🔑 **Güvenli Ayarlar Paneli:** Gemini API anahtarınızı arayüz üzerinden kolayca ekleyebilir, güncelleyebilir veya silebilirsiniz.
- 🔢 **Sürüm Numarası:** Üst bardaki rozet MehburAI'nin sürümünü gösterir (`config.APP_VERSION`) — her yeni özellikte artar.

---

## 🚀 Hızlı Başlangıç (Tek Tıkla Otomatik Kurulum)

### 0. Yöntem: `MehburAI.exe` ile (Python kurulumu gerektirmez)
`build_exe.bat`'e çift tıkla — PyInstaller ile derler ve
`%LOCALAPPDATA%\Programs\MehburAI\MehburAI.exe` konumuna **doğrudan bilgisayara kurar**
(ayarlar/hafıza mevcutsa oraya kopyalanır, sıfırlanmaz). Sonra Masaüstü kısayolunu
(`MehburAI.lnk`) o `.exe`'ye yönlendir — artık Python kurulu olmasa da çift tıkla açılır.
Yeniden derlemek istersen aynı betiği tekrar çalıştırman yeterli.

### 1. Yöntem: `Setup_and_Run.bat` ile (Kaynaktan çalıştır — geliştirici modu)
Projeyi indirdikten sonra klasör içindeki **`Setup_and_Run.bat`** dosyasına çift tıklayın. 
* Otomatik olarak tüm kütüphaneleri kurar,
* Masaüstünüze `MehburAI` kısayolunu oluşturur,
* Yapay zekayı anında başlatır.

### 2. Yöntem: Manuel Terminal ile
```powershell
# 1. Projeyi klonlayın
git clone https://github.com/Mehbur07/MehburAI.git
cd MehburAI

# 2. Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt

# 3. MehburAI'yi çalıştırın
python run_mehbur.py
```

---

## 📁 Proje Mimarisi

```
MehburAI/
├── config.py             # Neon Cyan tema sabitleri & ayar yöneticisi
├── network_manager.py    # Cloudflare 1.1.1.1 anlık ağ izleyici
├── memory_engine.py      # SQLite + Türkçe Morfolojik Semantik Bellek
├── ai_engine.py          # Wikipedia + Gemini REST (streamGenerateContent) + Karar Motoru + Küfür Filtresi
├── system_tools.py       # Program açma, dosya/klasör, ses/parlaklık, kilit/uyku, ekran görüntüsü, güç
├── security_guard.py     # 🛡️ Güvenlik Modu: korumalı yol izleme + silme koruması/yedek + kamera + Telegram alarmı
├── telegram_bot.py       # 🤖 Telegram'dan uzaktan kontrol (long-polling, sesli mesaj→yazı, dosya gönderme)
├── voice_engine.py       # 🎙️ Sesli sohbet: "Hey Mehbur" uyandırma sözcüğü + Vosk STT + edge-tts
├── jarvis_overlay.py     # 🟦 JARVIS tam ekran nokta küresi (tkinter Canvas animasyonu)
├── background.py         # 🛡️ Otomatik başlatma (Başlangıç kısayolu) + tek örnek kilidi
├── gui_app.py            # CustomTkinter Neon Cyan & Siyah Masaüstü GUI
├── assets/
│   ├── logo.png          # 🎨 Uygulama logosu (kendi görselinle değiştirebilirsin)
│   └── make_logo.py      # Hazır neon logo üreteci (PIL)
├── requirements.txt      # Bağımlılıklar
├── run_mehbur.py         # Ana başlatıcı
├── Setup_and_Run.bat     # Tek tıkla otomatik kurucu & başlatıcı (kaynaktan)
├── build_exe.bat         # 🖥️ .exe'ye paketler + %LOCALAPPDATA%'a kurar (PyInstaller)
├── MehburAI.spec         # PyInstaller derleme tarifi
└── data/
    └── mehbur_memory.db  # Kalıcı SQLite bellek veritabanı
```

---

## 📄 Lisans
Bu proje **MIT** lisansı altında geliştirilmiştir.
Geliştirici: **[Mehbur07 (Mehmet Burak ŞAHİN)](https://mehbur07.com)**
