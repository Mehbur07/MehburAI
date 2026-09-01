# -*- coding: utf-8 -*-
"""
MehburAI - Konfigürasyon & Tema Ayarları
=========================================
Uygulama genelinde kullanılan tüm sabitler, renkler, yollar
ve API anahtarı yönetim fonksiyonları bu modülde tanımlanır.
"""

import os
import json

# ─────────────────────────────────────────────
# Proje Yolları
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "mehbur_memory.db")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# data/ klasörünün var olduğundan emin ol
os.makedirs(DATA_DIR, exist_ok=True)

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
# Ağ Kontrolü Ayarları
# ─────────────────────────────────────────────
class NetworkConfig:
    """İnternet bağlantı kontrolü konfigürasyonu."""

    # Cloudflare DNS adresi (hızlı, güvenilir, küresel)
    CHECK_HOST = "1.1.1.1"
    CHECK_PORT = 53           # DNS portu
    CHECK_TIMEOUT = 2.0       # Saniye cinsinden zaman aşımı
    CHECK_INTERVAL = 5.0      # Periyodik kontrol aralığı (saniye)


# ─────────────────────────────────────────────
# Gemini API Ayarları
# ─────────────────────────────────────────────
class GeminiConfig:
    """Google Gemini API konfigürasyonu."""

    MODEL_NAME = "gemini-2.0-flash"
    MAX_OUTPUT_TOKENS = 2048
    TEMPERATURE = 0.7

    # Sistem promptu (MehburAI Kişiliği)
    SYSTEM_PROMPT = (
        "Sen MehburAI adında Türkçe konuşan akıllı bir yapay zeka asistanısın. "
        "Soruları doğru, öz ve anlaşılır şekilde yanıtlarsın. "
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
# API Anahtarı Yönetimi
# ─────────────────────────────────────────────

def load_config() -> dict:
    """Kayıtlı konfigürasyonu dosyadan yükler."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_config(config: dict) -> None:
    """Konfigürasyonu dosyaya kaydeder."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[HATA] Konfigürasyon kaydedilemedi: {e}")


def get_api_key() -> str | None:
    """Kayıtlı Gemini API anahtarını getirir."""
    config = load_config()
    return config.get("gemini_api_key")


def set_api_key(api_key: str) -> None:
    """Gemini API anahtarını kaydeder."""
    config = load_config()
    config["gemini_api_key"] = api_key
    save_config(config)


def remove_api_key() -> None:
    """Kayıtlı Gemini API anahtarını siler."""
    config = load_config()
    config.pop("gemini_api_key", None)
    save_config(config)
