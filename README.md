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
- 💻 **Bilgisayar & Sistem Araçları:** Saat/tarih sorgulama, sistem/donanım/disk bilgisi alma, Not Defteri, Hesap Makinesi gibi uygulamaları doğrudan açma.
- 😈 **Özel İsim Yanıtı:** *"Adın ne?"*, *"Kimsin?"* gibi sorulara *"Merhaba, ben MehburAI dünyayı ele geçireceğim"* şeklinde özel yanıt verir.
- 🔑 **Güvenli Ayarlar Paneli:** Gemini API anahtarınızı arayüz üzerinden kolayca ekleyebilir, güncelleyebilir veya silebilirsiniz.

---

## 🚀 Hızlı Başlangıç (Tek Tıkla Otomatik Kurulum)

### 1. Yöntem: `Setup_and_Run.bat` ile (Tavsiye Edilen)
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
├── ai_engine.py          # Wikipedia + Gemini API + Karar Motoru
├── system_tools.py       # Bilgisayar donanım, saat & masaüstü araçları
├── gui_app.py            # CustomTkinter Neon Cyan & Siyah Masaüstü GUI
├── requirements.txt      # Bağımlılıklar
├── run_mehbur.py         # Ana başlatıcı
├── Setup_and_Run.bat     # Tek tıkla otomatik kurucu & başlatıcı
└── data/
    └── mehbur_memory.db  # Kalıcı SQLite bellek veritabanı
```

---

## 📄 Lisans
Bu proje **MIT** lisansı altında geliştirilmiştir.
Geliştirici: **[Mehbur07 (Mehmet Burak ŞAHİN)](https://mehbur07.com)**
