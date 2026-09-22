# -*- coding: utf-8 -*-
"""
MehburAI - Konfigürasyon & Tema Ayarları
=========================================
Uygulama genelinde kullanılan tüm sabitler, renkler, yollar
ve API anahtarı yönetim fonksiyonları bu modülde tanımlanır.
"""

import os
import json
import sys

# ─────────────────────────────────────────────
# Uygulama Sürümü
# ─────────────────────────────────────────────
# Kullanıcı Claude'a MehburAI'a yeni bir özellik/değişiklik ekletirken bu sürüm
# İKİ KATMANLI ilerler:
#   • BÜYÜK ekleme (yeni özellik/sekme/yetenek)      → ORTA basamak artar: 1.1 → 1.2 → ... → 1.9 → 2.0 (2.1, ...)
#   • KÜÇÜK ekleme (ince ayar, küçük düzeltme/iyileştirme) → SON basamak artar: 1.2 → 1.2.1 → 1.2.2 → ...
#     (bir sonraki BÜYÜK eklemede üçüncü basamak sıfırlanıp ORTA basamak artar, örn. 1.2.3 → 1.3)
# (Elle güncellenir — kod her eklemede otomatik saymaz.)
APP_VERSION = "1.6.1"

# Güncelleme denetimi (updater.py): yeni sürüm GitHub'da yayınlanınca eski sürümü olan
# bilgisayarlarda uygulama açılınca uyarı çıkar. Depo herkese açık değilse denetim sessizce atlanır.
GITHUB_REPO = "Mehbur07/MehburAI"
UPDATE_PAGE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

# ─────────────────────────────────────────────
# Proje Yolları
# ─────────────────────────────────────────────
# PyInstaller ile .exe'ye paketlendiğinde (`sys.frozen`) kod, geçici bir açılış
# klasörüne çıkarılır — data/assets ORAYA değil, .exe'nin YANINDAKİ klasöre
# yazılmalı (yoksa her açılışta ayarlar/hafıza sıfırlanır). Geliştirme ortamında
# (sys.frozen yok) eskisi gibi bu dosyanın bulunduğu klasör kullanılır.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "mehbur_memory.db")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# assets/ — uygulama logosu ve ikonları
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")   # ana logo (kullanıcı buraya koyar)
ICON_PATH = os.path.join(ASSETS_DIR, "logo.ico")   # logo.png'den otomatik üretilir

# Gerekli klasörlerin var olduğundan emin ol
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)


def get_logo_path():
    """Uygulama logosu (assets/logo.png) varsa yolunu, yoksa None döndürür."""
    return LOGO_PATH if os.path.isfile(LOGO_PATH) else None


def ensure_app_icon():
    """
    assets/logo.png'den Windows pencere ikonu (.ico) üretir — yoksa ya da
    logo.png güncellenmişse yeniden oluşturur. Üretilen .ico yolunu döndürür;
    logo.png yoksa veya Pillow kurulu değilse None döner.
    """
    if not os.path.isfile(LOGO_PATH):
        return ICON_PATH if os.path.isfile(ICON_PATH) else None
    try:
        stale = (
            not os.path.isfile(ICON_PATH)
            or os.path.getmtime(ICON_PATH) < os.path.getmtime(LOGO_PATH)
        )
        if stale:
            from PIL import Image
            img = Image.open(LOGO_PATH).convert("RGBA")
            side = min(img.size)
            sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256) if s <= side]
            img.save(ICON_PATH, format="ICO", sizes=sizes or [(min(side, 64),) * 2])
    except Exception:
        return ICON_PATH if os.path.isfile(ICON_PATH) else None
    return ICON_PATH

# ─────────────────────────────────────────────
# Neon Cyan & Siyah Tema Renkleri
# ─────────────────────────────────────────────
class Theme:
    """MehburAI Neon Cyan & Siyah görsel tema sabitleri."""

    # Ana arka plan tonları
    BG_DARKEST = "#07070B"       # En koyu arkaplan
    BG_DARK = "#0A0A0E"          # Ana pencere arkaplanı
    BG_CARD = "#12121A"          # Kart / panel arkaplanı
    BG_CARD_HOVER = "#1A1A26"    # Kart hover durumu
    BG_INPUT = "#16161F"         # Input alanı arkaplanı

    # Neon Cyan vurgu tonları
    CYAN_PRIMARY = "#00F0FF"     # Ana neon cyan
    CYAN_GLOW = "#00D4E6"        # Hafif glow efekti
    CYAN_DIM = "#008B99"         # Soluk cyan (ikincil vurgu)
    CYAN_DARK = "#004D55"        # Koyu cyan (kenarlık / ince çizgi)

    # Durum renkleri
    STATUS_ONLINE = "#00FF88"    # Yeşil — İnternet bağlı
    STATUS_OFFLINE = "#FF3366"   # Kırmızı — İnternet yok
    STATUS_WARNING = "#FFB800"   # Sarı — Uyarı

    # Tehlike / silme (neon kırmızı)
    NEON_RED = "#FF2A4D"         # "Bu Sohbeti Sil" vb.
    NEON_RED_HOVER = "#7A1526"

    # Yanıt yazma animasyonu (harf harf) — harf başına gecikme (ms); 0 = anında
    TYPEWRITER_MS = 14

    # Metin renkleri
    TEXT_PRIMARY = "#E8E8EC"     # Ana metin
    TEXT_SECONDARY = "#8888A0"   # İkincil / soluk metin
    TEXT_ACCENT = "#00F0FF"      # Vurgu metin (cyan)
    TEXT_DARK = "#555570"        # Çok soluk metin

    # Mesaj balonları
    BUBBLE_USER = "#1A1A2E"      # Kullanıcı mesaj balonu
    BUBBLE_AI = "#0D2B2E"        # MehburAI mesaj balonu (hafif cyan tint)

    # Kenarlıklar
    BORDER_DEFAULT = "#1E1E2E"   # Normal kenarlık
    BORDER_FOCUS = "#00F0FF"     # Odaklanmış kenarlık

    # Buton
    BTN_PRIMARY_BG = "#00F0FF"   # Birincil buton arkaplanı
    BTN_PRIMARY_FG = "#07070B"   # Birincil buton yazı rengi
    BTN_HOVER_BG = "#33F5FF"     # Hover arkaplanı
    BTN_DISABLED_BG = "#333344"  # Devre dışı arkaplanı

    # Scrollbar
    SCROLLBAR_BG = "#16161F"
    SCROLLBAR_FG = "#2A2A3E"

    # Font sabitleri
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_TITLE = 22
    FONT_SIZE_HEADING = 16
    FONT_SIZE_BODY = 13
    FONT_SIZE_SMALL = 11
    FONT_SIZE_TINY = 9

    # Pencere sabitleri
    WINDOW_WIDTH = 950
    WINDOW_HEIGHT = 680
    WINDOW_MIN_WIDTH = 750
    WINDOW_MIN_HEIGHT = 550


# ─────────────────────────────────────────────
# 🎨 Kullanıcı Renk Teması (Ayarlar > Görünüm)
# ─────────────────────────────────────────────
# Vurgu rengi + arka plan tonu seçilir; diğer tüm Theme renkleri bunlardan türetilir.
# CustomTkinter renkleri pencere kurulurken okuduğundan değişiklik yeniden başlatınca
# uygulanır (ayarlar > "Uygula ve Yeniden Başlat").

THEME_ACCENTS = {
    "Neon Cyan": "#00F0FF",
    "Neon Mor": "#B026FF",
    "Neon Yeşil": "#39FF88",
    "Neon Kırmızı": "#FF2A4D",
    "Neon Pembe": "#FF3CAC",
    "Turuncu": "#FF8A00",
    "Altın": "#FFC629",
    "Elektrik Mavi": "#3D8BFF",
}
THEME_BACKGROUNDS = {
    "Siyah": "#0A0A0E",
    "Lacivert": "#0A0F1E",
    "Antrasit": "#141416",
    "Koyu Mor": "#100A1A",
    "Koyu Yeşil": "#08120E",
    "Koyu Kırmızı": "#160A0C",
}
THEME_DEFAULT_ACCENT = THEME_ACCENTS["Neon Cyan"]
THEME_DEFAULT_BG = THEME_BACKGROUNDS["Siyah"]


def is_valid_hex_color(value) -> bool:
    import re
    return bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value or "").strip()))


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix_colors(c1: str, c2: str, t: float) -> str:
    """c1'den c2'ye t (0..1) oranında karışım — '#RRGGBB'."""
    (r1, g1, b1), (r2, g2, b2) = _hex_to_rgb(c1), _hex_to_rgb(c2)
    t = max(0.0, min(1.0, t))
    return "#{:02X}{:02X}{:02X}".format(
        round(r1 + (r2 - r1) * t), round(g1 + (g2 - g1) * t), round(b1 + (b2 - b1) * t))


def derive_theme_colors(accent: str, bg: str) -> dict:
    """Vurgu + arka plan renginden tüm Theme renklerini türetir."""
    black, white = "#000000", "#FFFFFF"
    bg_card = mix_colors(bg, white, 0.05)
    bg_input = mix_colors(bg, white, 0.065)
    return {
        "BG_DARKEST": mix_colors(bg, black, 0.35),
        "BG_DARK": bg,
        "BG_CARD": bg_card,
        "BG_CARD_HOVER": mix_colors(bg, white, 0.09),
        "BG_INPUT": bg_input,
        "BUBBLE_USER": mix_colors(bg, white, 0.10),
        "BUBBLE_AI": mix_colors(bg, accent, 0.16),
        "BORDER_DEFAULT": mix_colors(bg, white, 0.11),
        "BTN_DISABLED_BG": mix_colors(bg, white, 0.19),
        "SCROLLBAR_BG": bg_input,
        "SCROLLBAR_FG": mix_colors(bg, white, 0.16),
        "CYAN_PRIMARY": accent,
        "CYAN_GLOW": mix_colors(accent, black, 0.10),
        "CYAN_DIM": mix_colors(accent, black, 0.45),
        "CYAN_DARK": mix_colors(accent, bg, 0.72),
        "TEXT_ACCENT": accent,
        "BORDER_FOCUS": accent,
        "BTN_PRIMARY_BG": accent,
        "BTN_HOVER_BG": mix_colors(accent, white, 0.20),
        "BTN_PRIMARY_FG": mix_colors(bg, black, 0.35),
    }


def apply_theme(accent: str, bg: str) -> None:
    """Theme sınıfının renklerini verilen vurgu/arka plan rengine göre günceller."""
    if not (is_valid_hex_color(accent) and is_valid_hex_color(bg)):
        return
    for name, value in derive_theme_colors(accent.upper(), bg.upper()).items():
        setattr(Theme, name, value)


# ─────────────────────────────────────────────
# Ağ Kontrolü Ayarları
# ─────────────────────────────────────────────
class NetworkConfig:
    """İnternet bağlantı kontrolü konfigürasyonu."""

    # Cloudflare DNS adresi (hızlı, güvenilir, küresel)
    CHECK_HOST = "1.1.1.1"
    CHECK_PORT = 53           # DNS portu
    CHECK_TIMEOUT = 2.0       # Saniye cinsinden zaman aşımı
    CHECK_INTERVAL = 5.0      # Periyodik kontrol aralığı (saniye)

    # Hedeflerden HERHANGİ BİRİNE ulaşılırsa internet var sayılır (paralel denenir).
    # Bazı ağlar/VPN/güvenlik duvarları yalnızca 1.1.1.1:53'ü kesebildiği için tek hedef
    # yanlışlıkla "çevrimdışı" gösterebiliyordu.
    CHECK_TARGETS = [
        ("Cloudflare DNS", "1.1.1.1", 53),
        ("Cloudflare HTTPS", "1.1.1.1", 443),
        ("Google DNS", "8.8.8.8", 53),
        ("Google HTTPS", "8.8.8.8", 443),
    ]


# ─────────────────────────────────────────────
# Gemini API Ayarları
# ─────────────────────────────────────────────
class GeminiConfig:
    """Google Gemini API konfigürasyonu."""

    # Birincil model ve sırayla denenecek yedek modeller.
    # (Eski "gemini-2.0-flash" Google tarafından kapatıldı; artık 3.x nesli kullanılıyor.)
    MODEL_NAME = "gemini-3.6-flash"
    FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-flash-latest", "gemini-3.5-flash"]
    MAX_OUTPUT_TOKENS = 2048
    TEMPERATURE = 0.7

    # 🎨 Görsel üretim/düzenleme (metinden görsel + var olan görseli düzenleme).
    # Hesapta hangisi aktifse sırayla denenir; hiçbiri yoksa "Görsel Stüdyosu"
    # nazikçe devre dışı kalır.
    IMAGE_MODELS = [
        "gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-3.1-flash-lite-image",
        "gemini-3.1-flash-image-preview", "gemini-3-pro-image",
    ]

    # REST akış (SSE) uç noktası ayarları
    API_BASE = "https://generativelanguage.googleapis.com/v1beta"
    CONNECT_TIMEOUT = 10.0
    READ_TIMEOUT = 75.0

    # Sistem promptu (MehburAI Kişiliği)
    SYSTEM_PROMPT = (
        "Sen MehburAI adında Türkçe konuşan akıllı bir yapay zeka asistanısın. "
        "Soruları doğru, kapsamlı ve anlaşılır şekilde yanıtlarsın; konu genişse "
        "önemli kısımları düzenli paragraflarla açıklarsın. "
        "Güvenilir bilgi kaynakları olan Wikipedia, ansiklopediler ve bilimsel veriler "
        "çerçevesinde yanıt üretirsin. Yanıtlarında kaynak belirtmeye özen gösterirsin. "
        "Samimi, yardımsever ve profesyonel bir üslup kullanırsın. "
        "Yanıtlarını Türkçe olarak verirsin."
    )


# ─────────────────────────────────────────────
# Bellek / Semantik Arama Ayarları
# ─────────────────────────────────────────────
class MemoryConfig:
    """Offline bellek ve semantik eşleşme konfigürasyonu."""

    # Semantik benzerlik eşik değeri (0.0 - 1.0)
    # Bu değerin üstündeki eşleşmeler "bilinen soru" olarak kabul edilir
    SIMILARITY_THRESHOLD = 0.48

    # Maksimum döndürülecek benzer sonuç sayısı
    MAX_RESULTS = 3


# ─────────────────────────────────────────────
# Selamlaşma Kalıpları
# ─────────────────────────────────────────────
GREETING_PATTERNS = [
    "merhaba", "selam", "hey", "hi", "hello",
    "günaydın", "iyi günler", "iyi akşamlar", "iyi geceler",
    "nasılsın", "naber", "ne haber", "napıyorsun",
    "kimsin", "sen kimsin", "adın ne", "kendini tanıt",
    "hoşgeldin", "hoş geldin",
    "sa", "selamün aleyküm", "as", "aleyküm selam",
]

GREETING_RESPONSES = {
    "merhaba": "Merhaba! 👋 Ben MehburAI, sana nasıl yardımcı olabilirim?",
    "selam": "Selam! 🌟 Bugün sana ne konuda yardımcı olabilirim?",
    "nasılsın": "İyiyim, teşekkür ederim! 😊 Sen nasılsın? Sana nasıl yardımcı olabilirim?",
    "kimsin": "Merhaba, ben MehburAI dünyayı ele geçireceğim",
    "adin_ne": "Merhaba, ben MehburAI dünyayı ele geçireceğim",
    "günaydın": "Günaydın! ☀️ Güzel bir güne başlıyoruz, sana nasıl yardımcı olabilirim?",
    "iyi günler": "İyi günler! 🌤️ Bugün hangi konuda yardımcı olabilirim?",
    "iyi akşamlar": "İyi akşamlar! 🌙 Sana nasıl yardımcı olabilirim?",
    "iyi geceler": "İyi geceler! 🌟 Uyumadan önce bir sorun varsa yardımcı olayım!",
    "default": "Merhaba! 👋 Ben MehburAI. Sana nasıl yardımcı olabilirim?",
}

# ─────────────────────────────────────────────
# Küfür & Hakaret Filtresi Yanıtı
# ─────────────────────────────────────────────
PROFANITY_RESPONSE = "Sana böyle laflar yakışıyor mu?"

# Misilleme modu açıkken (varsayılan) MehburAI küfrü aynen iade eder:
# "Bu laflar bana yakışıyorsa sana da yakışır" — küfür edene "asıl sen / asıl ben"
# kalıbıyla karşılık verir. Kapatılırsa yukarıdaki nazik uyarıya döner.
PROFANITY_DEFAULTS = {
    "profanity_comeback_enabled": True,
}


# ─────────────────────────────────────────────
# API Anahtarı Yönetimi (Çift Katmanlı Kalıcı Bellek)
# ─────────────────────────────────────────────

def _ensure_settings_table():
    """SQLite içinde ayarlar tablosunun var olduğundan emin olur."""
    try:
        import sqlite3
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
    except Exception:
        pass


def load_config() -> dict:
    """Kayıtlı konfigürasyonu dosyadan ve SQLite yedeğinden yükler."""
    config = {}
    # 1. JSON dosyasından oku
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            config = {}

    # 2. Eğer JSON'da API anahtarı yoksa SQLite yedeğini kontrol et
    if not config.get("gemini_api_key"):
        try:
            import sqlite3
            _ensure_settings_table()
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM app_settings WHERE key = 'gemini_api_key'")
                row = cursor.fetchone()
                if row and row[0]:
                    config["gemini_api_key"] = row[0]
                    # JSON'ı da güncelle
                    save_config(config)
        except Exception:
            pass

    return config


def save_config(config: dict) -> None:
    """Konfigürasyonu hem JSON dosyasına hem de SQLite'a kaydeder."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[HATA] Konfigürasyon kaydedilemedi: {e}")

    # SQLite yedeklemesi
    if "gemini_api_key" in config:
        try:
            import sqlite3
            _ensure_settings_table()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("""
                    INSERT INTO app_settings (key, value, updated_at)
                    VALUES ('gemini_api_key', ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """, (config["gemini_api_key"],))
                conn.commit()
        except Exception:
            pass


def get_api_key() -> str | None:
    """Kayıtlı Gemini API anahtarını getirir (kalıcı)."""
    config = load_config()
    return config.get("gemini_api_key")


def set_api_key(api_key: str) -> None:
    """Gemini API anahtarını kalıcı olarak kaydeder."""
    cleaned = api_key.strip()
    config = load_config()
    config["gemini_api_key"] = cleaned
    save_config(config)


def remove_api_key() -> None:
    """Kayıtlı Gemini API anahtarını siler."""
    config = load_config()
    config.pop("gemini_api_key", None)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    try:
        import sqlite3
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM app_settings WHERE key = 'gemini_api_key'")
            conn.commit()
    except Exception:
        pass


# ─────────────────────────────────────────────
# 🛡️ Güvenlik Modu (Yetkisiz Erişim Alarmı)
# ─────────────────────────────────────────────
# Kullanıcı ayarlardan korumalı yol(lar), bir şifre ve Telegram bilgileri girer.
# Korunan yol açıldığında MehburAI şifre sorar; şifre yanlışsa / ekran kapatılırsa
# kameradan fotoğraf çekilip cihaz sahibine Telegram'dan gönderilir ve ekranda
# "fotoğrafınız çekildi ve cihaz sahibine iletildi" uyarısı gösterilir.
# Bu ayarlar yalnızca yerel `data/config.json` içinde tutulur (repoya girmez).

# Cihaz sahibinin Telegram ID'si KODDA TUTULMAZ (kaynak koda / .exe'ye / GitHub'a
# hassas bilgi girmesin diye) — Ayarlar > Güvenlik Modu'ndan girilir ve yalnızca
# yerel `data/config.json` içinde durur. Bot yalnızca bu ID'den komut alır.

SECURITY_DEFAULTS = {
    "security_enabled": False,
    "security_watch_paths": [],       # ["C:\\Users\\...\\Gizli", "D:\\bir.exe"]
    "security_password_hash": "",     # sha256(salt + parola)
    "security_password_salt": "",
    "telegram_bot_token": "",         # BotFather'dan alınır ("MehburAI (Telegram)" botu)
    "telegram_chat_id": "",           # cihaz sahibinin Telegram sohbet ID'si (ayarlardan girilir)
    "telegram_remote_enabled": False, # bota yazarak MehburAI'ı uzaktan yönetme
}


def get_security_config() -> dict:
    """Kayıtlı güvenlik modu ayarlarını (varsayılanlarla birleştirilmiş) döndürür."""
    import re
    config = load_config()
    result = dict(SECURITY_DEFAULTS)
    for key in SECURITY_DEFAULTS:
        if key in config and config[key] not in (None, ""):
            result[key] = config[key]
    if not isinstance(result["security_watch_paths"], list):
        result["security_watch_paths"] = []
    # Chat ID geçerli bir Telegram ID değilse (bozuk/maskeli) boş say — bot kimseyi yetkilendirmez
    if not re.fullmatch(r"-?\d{5,}", str(result.get("telegram_chat_id", "")).strip()):
        result["telegram_chat_id"] = ""
    return result


def is_valid_bot_token(token: str) -> bool:
    """Telegram bot token biçimini doğrular: '<rakamlar>:<en az 30 karakter>'.
    (Maskeli/bozuk değerlerin — örn. '••••' — kaydedilmesini engellemek için.)"""
    import re
    return bool(re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{30,}", (token or "").strip()))


def update_security_config(**changes) -> None:
    """Verilen güvenlik ayarı anahtarlarını kaydeder (parola hariç)."""
    config = load_config()
    for key, value in changes.items():
        if key not in SECURITY_DEFAULTS or key.startswith("security_password"):
            continue
        # Bot token: yalnızca GEÇERLİ biçimde bir token yazılabilir.
        # Boş / maskeli / bozuk değerler yok sayılır (mevcut token korunur) —
        # böylece maskeli alanın kapanışta gerçek token'ı ezmesi engellenir.
        if key == "telegram_bot_token":
            if not is_valid_bot_token(value):
                continue
            value = value.strip()
        config[key] = value
    save_config(config)


# ─────────────────────────────────────────────
# 🎙️ Sesli Sohbet (yalnız bu bilgisayarda)
# ─────────────────────────────────────────────
# "Mehbur" / "Hey Mehbur" uyandırma sözcüğü + doğal Türkçe seslendirme.
# Yalnızca yerel makinede çalışır; Telegram tarafı sesli mesajı yazıya çevirir.

VOICE_DEFAULTS = {
    "voice_enabled": False,               # yerel sesli asistan (mikrofonu dinler)
    "voice_tts_voice": "tr-TR-EmelNeural",  # tr-TR-EmelNeural (kadın) / tr-TR-AhmetNeural (erkek)
    "telegram_voice_enabled": True,       # Telegram'daki sesli mesajları yazıya çevirip yanıtla
    "voice_overlay_enabled": True,        # uyandırınca JARVIS tarzı tam ekran nokta küresi
}

_VOICE_CHOICES = {"tr-TR-EmelNeural", "tr-TR-AhmetNeural"}


def get_voice_config() -> dict:
    """Kayıtlı sesli sohbet ayarlarını (varsayılanlarla) döndürür."""
    config = load_config()
    result = dict(VOICE_DEFAULTS)
    for key in VOICE_DEFAULTS:
        if key in config and config[key] not in (None, ""):
            result[key] = config[key]
    if result["voice_tts_voice"] not in _VOICE_CHOICES:
        result["voice_tts_voice"] = VOICE_DEFAULTS["voice_tts_voice"]
    return result


def update_voice_config(**changes) -> None:
    """Verilen sesli sohbet ayarı anahtarlarını kaydeder."""
    config = load_config()
    for key, value in changes.items():
        if key not in VOICE_DEFAULTS:
            continue
        if key == "voice_tts_voice" and value not in _VOICE_CHOICES:
            continue
        config[key] = value
    save_config(config)


# ─────────────────────────────────────────────
# 🤬 Küfüre Misilleme Ayarı
# ─────────────────────────────────────────────

def get_profanity_config() -> dict:
    """Küfüre misilleme ayarını (varsayılanlarla birleştirilmiş) döndürür."""
    config = load_config()
    result = dict(PROFANITY_DEFAULTS)
    for key in PROFANITY_DEFAULTS:
        if key in config and config[key] is not None:
            result[key] = bool(config[key])
    return result


def update_profanity_config(**changes) -> None:
    """Verilen küfür misilleme ayarı anahtarlarını kaydeder."""
    config = load_config()
    for key, value in changes.items():
        if key not in PROFANITY_DEFAULTS:
            continue
        config[key] = bool(value)
    save_config(config)


def set_security_password(plaintext: str) -> None:
    """Güvenlik modu parolasını tuzlu SHA-256 özeti olarak kaydeder (düz metin saklanmaz)."""
    import hashlib
    import secrets

    config = load_config()
    plaintext = (plaintext or "").strip()
    if not plaintext:
        config["security_password_hash"] = ""
        config["security_password_salt"] = ""
    else:
        salt = secrets.token_hex(16)
        digest = hashlib.sha256((salt + plaintext).encode("utf-8")).hexdigest()
        config["security_password_hash"] = digest
        config["security_password_salt"] = salt
    save_config(config)


def verify_security_password(plaintext: str) -> bool:
    """Girilen parolanın kayıtlı özetle eşleşip eşleşmediğini kontrol eder."""
    import hashlib
    import hmac

    cfg = get_security_config()
    stored = cfg.get("security_password_hash") or ""
    salt = cfg.get("security_password_salt") or ""
    if not stored or not salt:
        return False
    digest = hashlib.sha256((salt + (plaintext or "")).encode("utf-8")).hexdigest()
    return hmac.compare_digest(digest, stored)


def has_security_password() -> bool:
    cfg = get_security_config()
    return bool(cfg.get("security_password_hash") and cfg.get("security_password_salt"))


# ─────────────────────────────────────────────
# 🎨 Tema Ayarı (kalıcı) + 🧠 Otomatik Öğrenme Ayarı
# ─────────────────────────────────────────────

def get_theme_config() -> dict:
    """Kayıtlı vurgu/arka plan rengi (yoksa varsayılan Neon Cyan & Siyah)."""
    config = load_config()
    accent = config.get("theme_accent")
    bg = config.get("theme_bg")
    return {
        "accent": accent if is_valid_hex_color(accent) else THEME_DEFAULT_ACCENT,
        "bg": bg if is_valid_hex_color(bg) else THEME_DEFAULT_BG,
    }


def update_theme_config(accent: str | None = None, bg: str | None = None) -> None:
    """Vurgu ve/veya arka plan rengini kaydeder (geçersiz hex yok sayılır)."""
    config = load_config()
    if accent is not None and is_valid_hex_color(accent):
        config["theme_accent"] = accent.strip().upper()
    if bg is not None and is_valid_hex_color(bg):
        config["theme_bg"] = bg.strip().upper()
    save_config(config)


def reset_theme_config() -> None:
    config = load_config()
    config.pop("theme_accent", None)
    config.pop("theme_bg", None)
    save_config(config)


LEARN_DEFAULTS = {"auto_learn_enabled": True}


def get_learn_config() -> dict:
    config = load_config()
    return {"auto_learn_enabled": bool(config.get("auto_learn_enabled", LEARN_DEFAULTS["auto_learn_enabled"]))}


def update_learn_config(**changes) -> None:
    config = load_config()
    for key, value in changes.items():
        if key in LEARN_DEFAULTS:
            config[key] = bool(value)
    save_config(config)


def _apply_saved_theme() -> None:
    """Uygulama açılırken kayıtlı temayı Theme'e uygular (özel renk seçilmişse)."""
    try:
        config = load_config()
        if config.get("theme_accent") or config.get("theme_bg"):
            t = get_theme_config()
            apply_theme(t["accent"], t["bg"])
    except Exception:
        pass


_apply_saved_theme()
