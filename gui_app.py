# -*- coding: utf-8 -*-
"""
MehburAI - Modern Masaüstü Kullanıcı Arayüzü (GUI)
====================================================
Neon Cyan & Derin Siyah temalı CustomTkinter masaüstü arayüzü.

Özellikler:
  • Neon Cyan (#00F0FF) & Derin Siyah (#0A0A0E) estetik koyu tema
  • Canlı Ağ Durumu Göstergesi (🟢 Online / 🔴 Offline LED)
  • Çoklu Sekme Mimarisi:
      1. 💬 Sohbet (Chat & Zeka)
      2. 🧠 Hafıza Yönetimi (Öğrenilen Bilgiler & Arama)
      3. ⚙️ Ayarlar (Gemini API Anahtarı & Bağlantı Testi)
  • Donmayan Asenkron Thread Mimarisi (Sorular arka planda yanıtlanır)
  • Mesaj balonları, kaynak rozetleri ve dinamik sayaçlar
"""

import math
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from ai_engine import AIEngine, VisionAssistant
from auto_learner import IdleLearner
from config import (
    APP_VERSION,
    DATA_DIR,
    THEME_ACCENTS,
    THEME_BACKGROUNDS,
    Theme,
    derive_theme_colors,
    ensure_app_icon,
    get_api_key,
    get_learn_config,
    get_logo_path,
    get_security_config,
    get_theme_config,
    get_voice_config,
    reset_theme_config,
    update_learn_config,
    update_theme_config,
    has_security_password,
    is_valid_bot_token,
    load_config,
    remove_api_key,
    set_api_key,
    set_security_password,
    update_security_config,
    update_voice_config,
    verify_security_password,
)
from memory_engine import MemoryEngine
from network_manager import NetworkMonitor
from security_guard import (
    FileBackup,
    SecurityGuard,
    TelegramNotifier,
    trigger_intruder_alert,
)
from telegram_bot import TelegramControlBot
from updater import check_for_update
from background import SingleInstance, is_autostart_enabled, restart_app, set_autostart

try:
    from voice_engine import (
        Dictation,
        JarvisCall,
        SpeechToText,
        TextToSpeech,
        VoiceAssistant,
        missing_dependencies as voice_missing_deps,
        voice_dependencies_ok,
    )
except Exception:  # ses bağımlılıkları hiç kurulu değilse uygulama yine açılsın
    Dictation = None
    JarvisCall = None
    VoiceAssistant = None
    SpeechToText = TextToSpeech = None
    voice_dependencies_ok = lambda: False          # noqa: E731
    voice_missing_deps = lambda: ["voice_engine"]  # noqa: E731


# CustomTkinter Genel Tema Ayarları
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MehburApp(ctk.CTk):
    """MehburAI Ana Masaüstü Penceresi."""

    def __init__(self, start_hidden: bool = False, singleton=None):
        super().__init__()

        # Pencere Başlığı ve Boyutları
        self.title("MehburAI — Hibrit Akıllı Asistan")
        self.geometry(f"{Theme.WINDOW_WIDTH}x{Theme.WINDOW_HEIGHT}")
        self.minsize(Theme.WINDOW_MIN_WIDTH, Theme.WINDOW_MIN_HEIGHT)
        self.configure(fg_color=Theme.BG_DARK)
        self._apply_window_icon()

        # Çekirdek Servisler
        self.memory = MemoryEngine()
        self.active_conv_id = self.memory.ensure_conversation()
        self._type_after_id = None
        self.attached_file_path: Optional[str] = None
        self.attached_file_kind: Optional[str] = None   # 'text' | 'image'
        self._chat_images: list = []   # CTkImage referanslarını canlı tutar (GC engeli)
        self.network = NetworkMonitor(on_status_change=self._on_network_status_change)
        self.ai = AIEngine(memory_engine=self.memory, network_monitor=self.network)

        # Durum Değişkenleri
        self._is_processing = False
        self._security_dialogs = {}   # path -> Toplevel (aynı yol için tek ekran)
        self._security_backdrops = {}  # path -> tam ekran perde Toplevel
        self._security_queue = queue.Queue()   # guard thread -> UI thread köprüsü
        self._tray = None
        self._tray_notified = False
        self._quitting = False

        # 🛡️ Güvenlik Modu izleyicisi
        self.security_guard = SecurityGuard(
            on_access=lambda path, event="access": self._security_queue.put((path, event))
        )

        # 🤖 Telegram'dan uzaktan kontrol (bota yazarak MehburAI'ı yönetme)
        self._ai_lock = threading.Lock()
        self.telegram_bot = TelegramControlBot(
            query_handler=self._telegram_query,
            security_status=self._security_status_text,
            security_toggle=self._remote_toggle_security,
        )

        # 🎙️ Sesli Sohbet (yalnız bu bilgisayarda — uyandırma sözcüğü + doğal ses)
        self.voice_assistant = (
            VoiceAssistant(
                on_command=self._voice_command,
                on_state=lambda s, t="": self._ui_call(lambda: self._on_voice_state(s, t)),
            )
            if VoiceAssistant is not None else None
        )
        self._voice_state = "kapalı"
        self.jarvis = None   # JARVIS overlay — ilk uyandırmada oluşturulur
        self._dictation = None      # 🎤 bas-konuş yazdırma oturumu
        self._dictating = False
        self._call = None           # 📞 JARVIS görüşmesi (JarvisCall) — yoksa None
        self._call_camera_on = False   # 📷 görüşme sırasında kamera sorularına izin var mı

        # Tek örnek kilidi — ikinci açılış mevcut pencereyi öne getirir
        self._singleton = singleton or SingleInstance()
        self._singleton.set_on_show(lambda: self.after(0, self._restore_window))
        if singleton is None:
            self._singleton.acquire()

        # UI Bileşenlerini İnşa Et
        self._build_ui()

        # Ağ İzleyiciyi Başlat
        self.network.start()

        # 🧠 Boşta otomatik öğrenme (Wikipedia; ürünlerde özellikler + eleştirmen değerlendirmesi)
        self.learner = IdleLearner(
            memory=self.memory,
            is_online=lambda: self.network.is_online,
            idle_seconds=lambda: time.time() - self.ai.last_activity,
            on_learned=lambda r: self._ui_call(lambda: self._on_auto_learned(r)),
        )
        self.learner.start()

        # Güvenlik Modu etkinse izlemeyi başlat + tepsi ikonunu hazırla
        if get_security_config().get("security_enabled"):
            self.security_guard.start()
            self._setup_tray()

        # Telegram'dan uzaktan kontrol etkinse bot dinlemesini başlat
        if get_security_config().get("telegram_remote_enabled"):
            if self.telegram_bot.start():
                self._setup_tray()

        # Sesli sohbet etkinse mikrofon dinlemesini başlat
        if get_voice_config().get("voice_enabled") and self.voice_assistant is not None:
            self.after(1500, self._start_voice_async)
        self._update_mic_button()

        # Güvenlik kuyruğunu düzenli aralıkla ana thread'de kontrol et
        self.after(700, self._poll_security_queue)

        # Yeni sürüm var mı? (pencere çizildikten sonra arka planda, sessizce)
        self.after(4000, self._check_for_updates)

        # Sohbet listesi + aktif sohbetin geçmişi
        self._refresh_conversation_list()
        self._load_active_conversation()

        # Pencere Kapanış Olayı
        # Bazı Windows kurulumlarında kısayoldan açılışın hemen ardından, pencere
        # ilk çizilirken art arda SAHTE WM_DELETE_WINDOW mesajları gelebiliyor.
        # Çözüm: ilk ~18 sn tüm kapatma isteklerini yut; sonrasında X tuşu
        # uygulamayı KAPATMAZ, sadece sistem tepsisine gizler. Tamamen çıkış
        # yalnızca tepsi menüsünden veya "Çıkış" düğmesinden yapılır.
        self._close_armed = False
        self.protocol("WM_DELETE_WINDOW", self._on_close_request)
        self.after(18000, self._arm_close)
        # Tepsi ikonunu her zaman hazırla (kapatınca geri dönüş + Çıkış için)
        self.after(1500, self._setup_tray)

        # --tray ile (Windows açılışında) başlatıldıysa gizli aç
        if start_hidden and get_security_config().get("security_enabled"):
            self.after(200, self.withdraw)

    # ─────────────────────────────────────────
    # Arayüz İskeleti (UI Layout)
    # ─────────────────────────────────────────

    def _build_ui(self):
        """Tüm arayüz bileşenlerini oluşturur ve yerleştirir."""
        # Ana Grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Üst Başlık & Durum Çubuğu (Header Bar)
        self._build_header()

        # 2. Ana Panel Konteyneri
        self.main_container = ctk.CTkFrame(self, fg_color=Theme.BG_DARK, corner_radius=0)
        self.main_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 16))
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # 3 Paneli Oluştur
        self.panel_chat = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.panel_memory = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.panel_settings = ctk.CTkFrame(self.main_container, fg_color="transparent")

        self.panels = {
            "chat": self.panel_chat,
            "memory": self.panel_memory,
            "settings": self.panel_settings,
        }

        # Panel İçeriklerini İnşa Et
        self._build_chat_panel()
        self._build_memory_panel()
        self._build_settings_panel()

        # Güncelleme uyarı şeridi (yeni sürüm varsa görünür)
        self._build_update_banner()

        # Varsayılan olarak Sohbet panelini göster
        self.switch_tab("chat")

    # ─────────────────────────────────────────
    # 🔔 Güncelleme Uyarısı
    # ─────────────────────────────────────────

    def _build_update_banner(self):
        """Pencerenin altındaki uyarı şeridi — yeni sürüm bulunana kadar gizli."""
        self._update_url = ""
        self.update_banner = ctk.CTkFrame(
            self, fg_color=Theme.BG_CARD, corner_radius=10,
            border_width=1, border_color=Theme.STATUS_WARNING,
        )
        self.update_banner.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.update_banner.grid_columnconfigure(0, weight=1)

        self.update_msg_lbl = ctk.CTkLabel(
            self.update_banner, text="", justify="left", anchor="w", wraplength=760,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            text_color=Theme.STATUS_WARNING,
        )
        self.update_msg_lbl.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))

        self.update_link_lbl = ctk.CTkLabel(
            self.update_banner, text="", cursor="hand2", anchor="w",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, underline=True),
            text_color=Theme.CYAN_PRIMARY,
        )
        self.update_link_lbl.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 2))
        self.update_link_lbl.bind("<Button-1>", lambda e: self._open_update_page())

        self.update_ver_lbl = ctk.CTkLabel(
            self.update_banner, text="", anchor="w",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11), text_color=Theme.TEXT_SECONDARY,
        )
        self.update_ver_lbl.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 10))

        ctk.CTkButton(
            self.update_banner, text="✕", width=30, height=30, fg_color="transparent",
            hover_color=Theme.BG_CARD_HOVER, text_color=Theme.TEXT_SECONDARY,
            command=self.update_banner.grid_remove,
        ).grid(row=0, column=1, rowspan=2, padx=(0, 10), pady=8, sticky="ne")

        self.update_banner.grid_remove()

    def _open_update_page(self):
        if self._update_url.startswith("https://"):
            webbrowser.open(self._update_url)

    def _check_for_updates(self):
        """Açılışta (ve açık kaldıkça 6 saatte bir) yeni sürümü arka planda denetler."""
        def work():
            try:
                info = check_for_update()
            except Exception:
                info = None
            self._ui_call(lambda: self._show_update_banner(info))
        threading.Thread(target=work, daemon=True, name="MehburAI-UpdateCheck").start()
        if not self._quitting:
            self.after(6 * 3600 * 1000, self._check_for_updates)

    def _show_update_banner(self, info):
        if not info or not self.update_banner.winfo_exists():
            return
        self._update_url = info["url"]
        self.update_msg_lbl.configure(
            text="Uyarı: Yeni sürüm yayınlandı. Eğer yeni sürümü yüklemek istiyorsanız "
                 "bu bağlantıya tıklayın:")
        self.update_link_lbl.configure(text=info["url"])
        self.update_ver_lbl.configure(text=f"Sizdeki sürüm: {info['current']}  •  Yeni sürüm: {info['latest']}")
        self.update_banner.grid()

    def _apply_window_icon(self):
        """Pencere / görev çubuğu ikonunu assets/logo.png'den uygular (varsa)."""
        try:
            ico = ensure_app_icon()
            if ico:
                self.iconbitmap(ico)
        except Exception:
            pass
        try:
            logo = get_logo_path()
            if logo:
                from PIL import Image, ImageTk
                self._win_icon_img = ImageTk.PhotoImage(Image.open(logo).convert("RGBA"))
                self.iconphoto(True, self._win_icon_img)
        except Exception:
            pass

    def _build_header(self):
        """Üst kısımdaki Neon logo, sekmeler ve durum rozetleri."""
        self.header_frame = ctk.CTkFrame(
            self,
            fg_color=Theme.BG_CARD,
            corner_radius=0,
            border_width=1,
            border_color=Theme.CYAN_DARK,
            height=70,
        )
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(1, weight=1)

        # Sol: Logo & İsim
        logo_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=(20, 10), pady=12, sticky="w")

        _logo_path = get_logo_path()
        if _logo_path:
            try:
                from PIL import Image
                self._header_logo_img = ctk.CTkImage(
                    Image.open(_logo_path), size=(38, 38)
                )
                ctk.CTkLabel(logo_frame, image=self._header_logo_img, text="").pack(
                    side="left", padx=(0, 10)
                )
            except Exception:
                pass

        title_lbl = ctk.CTkLabel(
            logo_frame,
            text="⚡ MEHBUR AI",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=20, weight="bold"),
            text_color=Theme.CYAN_PRIMARY,
        )
        title_lbl.pack(side="left", padx=(0, 8))

        subtitle_lbl = ctk.CTkLabel(
            logo_frame,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY,
        )
        subtitle_lbl.pack(side="left", pady=(4, 0))

        # Orta: Belirgin Sekme Butonları (Navbar)
        nav_frame = ctk.CTkFrame(self.header_frame, fg_color=Theme.BG_DARKEST, corner_radius=10)
        nav_frame.grid(row=0, column=1, padx=10, pady=12)

        self.btn_nav_chat = ctk.CTkButton(
            nav_frame,
            text="💬 Sohbet",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            fg_color=Theme.CYAN_PRIMARY,
            text_color=Theme.BG_DARKEST,
            hover_color=Theme.CYAN_GLOW,
            width=110,
            height=36,
            corner_radius=8,
            command=lambda: self.switch_tab("chat"),
        )
        self.btn_nav_chat.pack(side="left", padx=4, pady=4)

        self.btn_nav_memory = ctk.CTkButton(
            nav_frame,
            text="🧠 Hafıza",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            fg_color="transparent",
            text_color=Theme.TEXT_PRIMARY,
            hover_color=Theme.BG_CARD_HOVER,
            width=110,
            height=36,
            corner_radius=8,
            command=lambda: self.switch_tab("memory"),
        )
        self.btn_nav_memory.pack(side="left", padx=4, pady=4)

        self.btn_nav_settings = ctk.CTkButton(
            nav_frame,
            text="⚙️ Ayarlar",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            fg_color="transparent",
            text_color=Theme.TEXT_PRIMARY,
            hover_color=Theme.BG_CARD_HOVER,
            width=110,
            height=36,
            corner_radius=8,
            command=lambda: self.switch_tab("settings"),
        )
        self.btn_nav_settings.pack(side="left", padx=4, pady=4)

        # Sağ: Durum Rozetleri
        badge_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        badge_frame.grid(row=0, column=2, padx=20, pady=12, sticky="e")

        # Hafıza Sayacı Rozeti
        self.memory_badge = ctk.CTkLabel(
            badge_frame,
            text=f"🧠 {self.memory.get_memory_count()} Bilgi",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text_color=Theme.CYAN_PRIMARY,
            fg_color=Theme.BG_DARKEST,
            corner_radius=10,
            padx=10,
            pady=5,
        )
        self.memory_badge.pack(side="left", padx=6)

        # Canlı Ağ Durumu Rozeti
        self.network_badge = ctk.CTkLabel(
            badge_frame,
            text=self._get_network_badge_text(),
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text_color=Theme.STATUS_ONLINE if self.network.is_online else Theme.STATUS_OFFLINE,
            fg_color=Theme.BG_DARKEST,
            corner_radius=10,
            padx=10,
            pady=5,
        )
        self.network_badge.pack(side="left")

    def switch_tab(self, tab_name: str):
        """Aktif sekmeyi değiştirir ve buton renklerini günceller."""
        # Tüm panelleri gizle
        for name, panel in self.panels.items():
            panel.grid_forget()

        # Seçilen paneli göster
        if tab_name in self.panels:
            self.panels[tab_name].grid(row=0, column=0, sticky="nsew")

        # Buton stillerini güncelle
        nav_buttons = {
            "chat": self.btn_nav_chat,
            "memory": self.btn_nav_memory,
            "settings": self.btn_nav_settings,
        }
        for name, btn in nav_buttons.items():
            if name == tab_name:
                btn.configure(
                    fg_color=Theme.CYAN_PRIMARY,
                    text_color=Theme.BG_DARKEST,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=Theme.TEXT_PRIMARY,
                )

        if tab_name == "memory":
            self._refresh_memory_list()
        elif tab_name == "settings":
            self._reload_settings_view()

    def _reload_settings_view(self):
        """Ayarlar sekmesine geçildiğinde kayıtlı anahtarı ve durumu yeniler."""
        current_key = get_api_key() or ""
        if hasattr(self, "api_key_entry") and self.api_key_entry:
            self.api_key_entry.delete(0, "end")
            if current_key:
                self.api_key_entry.insert(0, current_key)
        if hasattr(self, "api_status_lbl") and self.api_status_lbl:
            if current_key:
                self.api_status_lbl.configure(
                    text="✅ API Anahtarı Kayıtlı",
                    text_color=Theme.STATUS_ONLINE
                )
            else:
                self.api_status_lbl.configure(
                    text="⚠️ API Anahtarı Henüz Girilmedi",
                    text_color=Theme.STATUS_WARNING
                )
        if hasattr(self, "sec_status"):
            self._refresh_security_status()

    # ─────────────────────────────────────────
    # SEKME 1: SOHBET PANELİ (CHAT PANEL)
    # ─────────────────────────────────────────

    def _build_chat_panel(self):
        """Sol: Sohbetler kenar çubuğu · Sağ: mesajlaşma alanı ve giriş kutusu."""
        self.panel_chat.grid_rowconfigure(0, weight=1)
        self.panel_chat.grid_columnconfigure(0, weight=0, minsize=196)
        self.panel_chat.grid_columnconfigure(1, weight=1)

        # ── SOL: Sohbetler kenar çubuğu ──
        self._build_conversation_sidebar()

        # ── SAĞ: Sohbet alanı ──
        chat_area = ctk.CTkFrame(self.panel_chat, fg_color="transparent")
        chat_area.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        chat_area.grid_rowconfigure(0, weight=1)
        chat_area.grid_columnconfigure(0, weight=1)

        # Mesaj Geçmişi (Scrollable Frame)
        self.chat_history_box = ctk.CTkScrollableFrame(
            chat_area,
            fg_color=Theme.BG_DARKEST,
            corner_radius=10,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
        )
        self.chat_history_box.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 10))

        # Alt Giriş Paneli
        input_container = ctk.CTkFrame(chat_area, fg_color="transparent")
        input_container.grid(row=1, column=0, sticky="ew", padx=4, pady=0)
        input_container.grid_columnconfigure(0, weight=1)

        # Metin Giriş Kutusu
        self.query_entry = ctk.CTkEntry(
            input_container,
            placeholder_text="MehburAI'ye bir soru sorun veya mesaj yazın... (Örn: Albert Einstein kimdir?)",
            placeholder_text_color=Theme.TEXT_DARK,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13),
            fg_color=Theme.BG_INPUT,
            border_color=Theme.CYAN_DARK,
            border_width=1,
            text_color=Theme.TEXT_PRIMARY,
            height=48,
            corner_radius=10,
        )
        self.query_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.query_entry.bind("<Return>", lambda event: self._on_send_clicked())

        # ➕ Dosya Ekle Butonu — bir .txt/.md/.csv/... dosyasını seçip sohbete katar
        self.attach_btn = ctk.CTkButton(
            input_container,
            text="➕",
            font=ctk.CTkFont(size=17),
            fg_color=Theme.BG_CARD,
            text_color=Theme.CYAN_PRIMARY,
            hover_color=Theme.BG_CARD_HOVER,
            border_width=2,
            border_color=Theme.CYAN_DARK,
            width=48,
            height=48,
            corner_radius=10,
            command=self._pick_attachment,
        )
        self.attach_btn.grid(row=0, column=1, sticky="e", padx=(0, 10))

        # 🎤 Mikrofon Butonu — sesli sohbete geç (Ayarlar'daki anahtarla senkron)
        self.mic_btn = ctk.CTkButton(
            input_container,
            text="🎤",
            font=ctk.CTkFont(size=17),
            fg_color=Theme.BG_CARD,
            text_color=Theme.TEXT_DARK,
            hover_color=Theme.BG_CARD_HOVER,
            border_width=2,
            border_color=Theme.TEXT_DARK,
            width=48,
            height=48,
            corner_radius=10,
            command=self._toggle_voice_from_chat,
        )
        self.mic_btn.grid(row=0, column=2, sticky="e", padx=(0, 10))

        # 📞 JARVIS Butonu — tam ekran JARVIS açılır, eller serbest sesli görüşme başlar
        self.call_btn = ctk.CTkButton(
            input_container,
            text="📞",
            font=ctk.CTkFont(size=17),
            fg_color=Theme.BG_CARD,
            text_color=Theme.CYAN_PRIMARY,
            hover_color=Theme.BG_CARD_HOVER,
            border_width=2,
            border_color=Theme.CYAN_DARK,
            width=48,
            height=48,
            corner_radius=10,
            command=self._toggle_jarvis_call,
        )
        self.call_btn.grid(row=0, column=3, sticky="e", padx=(0, 10))

        # Gönder Butonu (Neon Cyan)
        self.send_btn = ctk.CTkButton(
            input_container,
            text="Gönder ⚡",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            fg_color=Theme.CYAN_PRIMARY,
            text_color=Theme.BG_DARKEST,
            hover_color=Theme.CYAN_GLOW,
            width=110,
            height=48,
            corner_radius=10,
            command=self._on_send_clicked,
        )
        self.send_btn.grid(row=0, column=4, sticky="e")

        # 📎 Eklenen dosya rozeti — dosya seçilince görünür, tıklayınca kaldırılır
        self.attachment_lbl = ctk.CTkLabel(
            input_container,
            text="",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text_color=Theme.CYAN_PRIMARY,
            fg_color=Theme.BG_CARD,
            corner_radius=6,
            anchor="w",
            cursor="hand2",
            height=24,
        )
        self.attachment_lbl.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        self.attachment_lbl.bind("<Button-1>", lambda e: self._clear_attachment())
        self.attachment_lbl.grid_remove()

        # Hızlı Yardım & Ayarlar Butonları
        quick_frame = ctk.CTkFrame(chat_area, fg_color="transparent", height=30)
        quick_frame.grid(row=2, column=0, sticky="ew", padx=4, pady=(6, 0))

        btn_sample1 = ctk.CTkButton(
            quick_frame,
            text="💡 Örnek: adın ne?",
            font=ctk.CTkFont(size=11),
            fg_color=Theme.BG_CARD,
            text_color=Theme.TEXT_SECONDARY,
            hover_color=Theme.BG_CARD_HOVER,
            height=26,
            command=lambda: self._insert_quick_query("adın ne"),
        )
        btn_sample1.pack(side="left", padx=(0, 6))

        btn_sample2 = ctk.CTkButton(
            quick_frame,
            text="🌍 Örnek: Albert Einstein kimdir?",
            font=ctk.CTkFont(size=11),
            fg_color=Theme.BG_CARD,
            text_color=Theme.TEXT_SECONDARY,
            hover_color=Theme.BG_CARD_HOVER,
            height=26,
            command=lambda: self._insert_quick_query("Albert Einstein kimdir?"),
        )
        btn_sample2.pack(side="left", padx=6)

        btn_goto_settings = ctk.CTkButton(
            quick_frame,
            text="⚙️ Gemini API Ayarları",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=Theme.BG_CARD,
            text_color=Theme.CYAN_PRIMARY,
            hover_color=Theme.BG_CARD_HOVER,
            height=26,
            command=lambda: self.switch_tab("settings"),
        )
        btn_goto_settings.pack(side="left", padx=6)

        btn_clear_chat = ctk.CTkButton(
            quick_frame,
            text="🧹 Mesajları Temizle",
            font=ctk.CTkFont(size=11),
            fg_color=Theme.BG_CARD,
            text_color=Theme.TEXT_SECONDARY,
            hover_color=Theme.BG_CARD_HOVER,
            height=26,
            command=self._clear_chat_display,
        )
        btn_clear_chat.pack(side="right")

        btn_quit = ctk.CTkButton(
            quick_frame,
            text="⏻ Çıkış",
            font=ctk.CTkFont(size=11),
            fg_color=Theme.BG_CARD,
            text_color="#FF8888",
            hover_color="#44111E",
            height=26,
            command=self._confirm_quit,
        )
        btn_quit.pack(side="right", padx=(0, 6))

    # ─────────────────────────────────────────
    # Sohbetler Kenar Çubuğu (Conversation Sidebar)
    # ─────────────────────────────────────────

    def _build_conversation_sidebar(self):
        """Sol tarafta sohbet listesi + 'Yeni Sohbet' ve neon kırmızı 'Bu Sohbeti Sil'."""
        side = ctk.CTkFrame(
            self.panel_chat,
            fg_color=Theme.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
        )
        side.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        side.grid_rowconfigure(2, weight=1)
        side.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            side,
            text="💬 Sohbetler",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.TEXT_SECONDARY,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        ctk.CTkButton(
            side,
            text="➕  Yeni Sohbet",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            fg_color=Theme.CYAN_PRIMARY,
            text_color=Theme.BG_DARKEST,
            hover_color=Theme.CYAN_GLOW,
            height=32,
            corner_radius=8,
            command=self._new_conversation,
        ).grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))

        self.conv_list_box = ctk.CTkScrollableFrame(side, fg_color="transparent")
        self.conv_list_box.grid(row=2, column=0, sticky="nsew", padx=4, pady=2)
        self.conv_list_box.grid_columnconfigure(0, weight=1)

        self.btn_delete_conv = ctk.CTkButton(
            side,
            text="🗑  Bu Sohbeti Sil",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            fg_color="transparent",
            border_width=1,
            border_color=Theme.NEON_RED,
            text_color=Theme.NEON_RED,
            hover_color=Theme.NEON_RED_HOVER,
            height=30,
            corner_radius=8,
            command=self._delete_active_conversation,
        )
        self.btn_delete_conv.grid(row=3, column=0, sticky="ew", padx=8, pady=(6, 10))

    def _refresh_conversation_list(self):
        """Sohbet listesini yeniden çizer; aktif olan vurgulanır, ruh hali ikonlanır."""
        if not hasattr(self, "conv_list_box"):
            return
        for w in self.conv_list_box.winfo_children():
            w.destroy()

        mood_icon = {"normal": "", "provoked": "  ⚠️", "rude": "  😠"}
        for conv in self.memory.list_conversations():
            cid = conv["id"]
            active = (cid == self.active_conv_id)
            title = (conv.get("title") or "Yeni Sohbet").strip()[:20]
            label = f"{title}{mood_icon.get(conv.get('mood', 'normal'), '')}"
            ctk.CTkButton(
                self.conv_list_box,
                text=label,
                anchor="w",
                font=ctk.CTkFont(
                    family=Theme.FONT_FAMILY, size=12,
                    weight="bold" if active else "normal",
                ),
                fg_color=Theme.CYAN_DARK if active else "transparent",
                text_color=Theme.CYAN_PRIMARY if active else Theme.TEXT_SECONDARY,
                hover_color=Theme.BG_CARD_HOVER,
                height=30,
                corner_radius=6,
                command=lambda c=cid: self._select_conversation(c),
            ).grid(sticky="ew", pady=2, padx=2)

    def _new_conversation(self):
        """Yeni boş bir sohbet açar ve ona geçer."""
        if self._is_processing:
            return
        self.active_conv_id = self.memory.create_conversation()
        self._refresh_conversation_list()
        self._load_active_conversation()
        self.switch_tab("chat")
        self.query_entry.focus()

    def _select_conversation(self, conv_id: int):
        """Listeden bir sohbete geçer, geçmişini yükler."""
        if self._is_processing or conv_id == self.active_conv_id:
            return
        self.active_conv_id = conv_id
        self._refresh_conversation_list()
        self._load_active_conversation()

    def _delete_active_conversation(self):
        """Aktif sohbeti ve tüm mesajlarını kalıcı olarak siler (onaylı)."""
        if self._is_processing:
            return
        if not messagebox.askyesno(
            "Sohbeti Sil",
            "Bu sohbet ve içindeki tüm mesajlar kalıcı olarak silinsin mi?",
            icon="warning",
            parent=self,
        ):
            return
        self.memory.delete_conversation(self.active_conv_id)
        self.active_conv_id = self.memory.ensure_conversation()
        self._refresh_conversation_list()
        self._load_active_conversation()

    def _load_active_conversation(self):
        """Aktif sohbetin mesaj geçmişini sohbet alanına yükler (animasyonsuz)."""
        self._cancel_typewriter()
        for widget in self.chat_history_box.winfo_children():
            widget.destroy()

        messages = self.memory.get_conversation_messages(self.active_conv_id)
        if not messages:
            self._send_welcome_message()
            return

        for m in messages:
            role = m["role"]
            text = m["message"]
            if role == "user" and text == "[küfür filtresi]":
                text = "🚫 (küfürlü mesaj)"
            self._add_message_bubble(
                role=role,
                message=text,
                source=(m.get("source") if role == "mehbur" else None),
                is_online=bool(m.get("is_online", 1)),
                animate=False,
            )
        self.after(60, lambda: self.chat_history_box._parent_canvas.yview_moveto(1.0))

    def _insert_quick_query(self, text: str):
        """Hızlı örnek soruyu giriş kutusuna yazar."""
        self.query_entry.delete(0, "end")
        self.query_entry.insert(0, text)
        self.query_entry.focus()

    # ─────────────────────────────────────────
    # ➕ Dosya Ekleme — bir metin dosyasını (içeriği hakkında soru sor) veya bir
    #    fotoğrafı (🎨 "bunu daha kaliteli yap" gibi düzenleme istekleri için) katar
    # ─────────────────────────────────────────

    _ATTACH_MAX_BYTES = 5 * 1024 * 1024      # 5 MB üstü dosya kabul edilmez
    _ATTACH_MAX_CHARS = 40_000               # Gemini'ye gönderilen metin içeriği bu kadarla sınırlı
    _IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

    @staticmethod
    def _human_file_size(num_bytes: int) -> str:
        n = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    def _validate_attachment(self, path: str):
        """Dosyanın türünü belirler; okunabilir bir metin/fotoğraf dosyası mı kontrol eder.
        Döner: (ok, hata_mesajı, tür) — tür: 'text' | 'image'."""
        try:
            size = os.path.getsize(path)
        except OSError:
            return False, "Dosya okunamadı.", None
        if size > self._ATTACH_MAX_BYTES:
            return False, f"Dosya çok büyük ({self._human_file_size(size)}). 5 MB'tan küçük bir dosya seç.", None

        if os.path.splitext(path)[1].lower() in self._IMAGE_EXTS:
            return True, "", "image"

        try:
            with open(path, "rb") as f:
                sample = f.read(4096)
            sample.decode("utf-8")
        except UnicodeDecodeError:
            return False, (
                "Bu dosyayı metin olarak okuyamıyorum. Lütfen .txt, .md, .csv, .json, .log "
                "gibi bir metin dosyası ya da .jpg/.png gibi bir fotoğraf seç."
            ), None
        except OSError:
            return False, "Dosya okunamadı.", None
        return True, "", "text"

    def _pick_attachment(self):
        """Dosya seçme penceresini açar; seçilen metin/fotoğraf dosyasını sohbete ekler."""
        path = filedialog.askopenfilename(
            parent=self,
            title="MehburAI'ye Dosya Ekle",
            filetypes=[
                ("Metin, kod ve fotoğraflar", "*.txt *.md *.csv *.log *.json *.ini *.py *.js "
                                                "*.ts *.xml *.yaml *.yml *.cfg *.jpg *.jpeg *.png *.webp *.bmp"),
                ("Tüm dosyalar", "*.*"),
            ],
        )
        if not path:
            return
        ok, err, kind = self._validate_attachment(path)
        if not ok:
            messagebox.showwarning("Dosya Eklenemedi", err, parent=self)
            return
        self.attached_file_path = path
        self.attached_file_kind = kind
        name = os.path.basename(path)
        size = self._human_file_size(os.path.getsize(path))
        hint = "bir soru sor" if kind == "text" else "\"bunu daha kaliteli yap\" gibi bir istek yaz"
        icon = "📎" if kind == "text" else "🖼️"
        self.attachment_lbl.configure(
            text=f"{icon} {name} ({size}) — {hint}, göndermeden önce kaldırmak için tıkla ✕"
        )
        self.attachment_lbl.grid()
        self.query_entry.focus()

    def _clear_attachment(self):
        """Eklenmiş dosyayı kaldırır."""
        self.attached_file_path = None
        self.attached_file_kind = None
        self.attachment_lbl.configure(text="")
        self.attachment_lbl.grid_remove()

    def _send_welcome_message(self):
        """Uygulama açılışında karşılama mesajını ekler."""
        welcome_text = (
            "Merhaba! Ben **MehburAI** 🤖⚡\n\n"
            "• **Çevrim İçi İken:** Güvenilir kaynakları ve Gemini yapay zekasını kullanarak "
            "sorularınızı yanıtlar ve cevabı otomatik olarak yerel hafızama kaydederim.\n"
            "• **Çevrim Dışı İken:** İnternetiniz olmasa bile daha önce öğrendiğim bilgileri "
            "semantik arama ile hatırlar ve size sunarım!"
        )
        self._add_message_bubble(
            role="mehbur",
            message=welcome_text,
            source="Sistem",
            is_online=self.network.is_online,
            animate=False,
        )

    def _on_send_clicked(self):
        """Kullanıcı gönder butonuna bastığında tetiklenir."""
        query = self.query_entry.get().strip()
        if not query or self._is_processing:
            return

        # ➕ Ekli dosya varsa AI Engine'e geçilecek bağlamı hazırla (metin/görsel)
        file_context = None
        attach_note = ""
        if self.attached_file_path and self.attached_file_kind:
            name = os.path.basename(self.attached_file_path)
            if self.attached_file_kind == "text":
                try:
                    with open(self.attached_file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read(self._ATTACH_MAX_CHARS + 1)
                    truncated = len(content) > self._ATTACH_MAX_CHARS
                    file_context = {"name": name, "kind": "text", "text": content[:self._ATTACH_MAX_CHARS]}
                    attach_note = f"\n\n📎 *{name}*" + (" (kısmi — dosya çok büyük)" if truncated else "")
                except OSError:
                    file_context = None
            else:  # 'image'
                file_context = {"name": name, "kind": "image", "path": self.attached_file_path}
                attach_note = f"\n\n🖼️ *{name}*"
            self._clear_attachment()

        # Giriş kutusunu temizle ve kilitle
        self.query_entry.delete(0, "end")
        self._set_processing(True)

        # Kullanıcı mesajını sohbet balonuna ekle (ekli dosya notuyla)
        self._add_message_bubble(
            role="user", message=query + attach_note,
            is_online=self.network.is_online, animate=False,
        )

        # İlk kullanıcı mesajından sohbet başlığını türet
        try:
            conv = self.memory.get_conversation(self.active_conv_id)
            if conv and (conv.get("title") or "Yeni Sohbet") == "Yeni Sohbet":
                title = query.strip().splitlines()[0][:28]
                self.memory.rename_conversation(self.active_conv_id, title or "Yeni Sohbet")
                self._refresh_conversation_list()
        except Exception:
            pass

        # Düşünülüyor / Yükleniyor balonunu ekle
        self._add_loading_bubble()

        conv_id = self.active_conv_id
        # Yanıt üretimini arka plan thread'inde çalıştır (UI donmasın)
        threading.Thread(
            target=self._process_query_async,
            args=(query, conv_id, file_context),
            daemon=True,
            name="MehburAI-QueryWorker"
        ).start()

    def _process_query_async(self, query: str, conv_id: Optional[int] = None, file_context: Optional[dict] = None):
        """Arka planda AI Engine ile soruyu işler."""
        try:
            with self._ai_lock:
                result = self.ai.process_query(query, conversation_id=conv_id, file_context=file_context)
        except Exception as e:
            result = {
                "answer": f"Bir hata oluştu: {e}",
                "is_online": self.network.is_online,
                "source": "error",
                "learned": False,
            }

        # Sonucu ana UI thread'inde göster
        self.after(0, self._handle_query_response, result)

    def _handle_query_response(self, result: dict):
        """Arka plandan gelen yanıtı UI'a aktarır."""
        self._remove_loading_bubble()

        answer = result.get("answer", "")
        source = result.get("source", "")
        is_online = result.get("is_online", True)
        learned = result.get("learned", False)
        score = result.get("score")

        source_label = source
        if learned:
            source_label = f"{source} (💡 Hafızaya Kaydedildi)"
        elif score:
            source_label = f"{source} (%{score*100:.0f} Benzerlik)"

        def _after_typing():
            self._update_badges()
            self._refresh_memory_list()
            self._refresh_conversation_list()   # ruh hali ikonu değişmiş olabilir
            self._set_processing(False)

        # Mesajı harf harf yazma animasyonuyla ekle (🎨 üretilen/düzenlenen görsel varsa altına eklenir)
        self._add_message_bubble(
            role="mehbur",
            message=answer,
            source=source_label,
            is_online=is_online,
            animate=True,
            on_done=_after_typing,
            image_path=result.get("image_path"),
        )

    def _set_processing(self, processing: bool):
        """Soru işlenirken UI butonlarını yönetir."""
        self._is_processing = processing
        if processing:
            self.send_btn.configure(text="Düşünüyor...", state="disabled", fg_color=Theme.BTN_DISABLED_BG)
        else:
            self.send_btn.configure(text="Gönder ⚡", state="normal", fg_color=Theme.CYAN_PRIMARY)
            self.query_entry.focus()

    # ─────────────────────────────────────────
    # Mesaj Balonları (Chat Bubbles)
    # ─────────────────────────────────────────

    def _add_message_bubble(self, role: str, message: str, source: Optional[str] = None,
                            is_online: bool = True, animate: bool = True, on_done=None,
                            image_path: Optional[str] = None):
        """Sohbet alanına şık bir mesaj kutucuğu ekler.

        MehburAI mesajları `animate=True` iken harf harf yazılır; yazım bitince
        `on_done` çağrılır. `image_path` verilirse (🎨 üretilen/düzenlenen görsel)
        balonun içine küçük bir önizleme olarak eklenir.
        """
        bubble_container = ctk.CTkFrame(self.chat_history_box, fg_color="transparent")
        bubble_container.pack(fill="x", padx=8, pady=6)

        if role == "user":
            # Kullanıcı Mesajı (Sağa hizalı)
            bubble = ctk.CTkFrame(
                bubble_container,
                fg_color=Theme.BUBBLE_USER,
                corner_radius=12,
                border_width=1,
                border_color=Theme.BORDER_DEFAULT,
            )
            bubble.pack(side="right", padx=(60, 0))

            header_lbl = ctk.CTkLabel(
                bubble,
                text="👤 Siz",
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
                text_color=Theme.TEXT_SECONDARY,
            )
            header_lbl.pack(anchor="e", padx=12, pady=(8, 2))

            msg_lbl = ctk.CTkLabel(
                bubble,
                text=message,
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13),
                text_color=Theme.TEXT_PRIMARY,
                wraplength=520,
                justify="left",
            )
            msg_lbl.pack(anchor="w", padx=12, pady=(0, 8))

        else:
            # MehburAI Mesajı (Sola hizalı)
            bubble = ctk.CTkFrame(
                bubble_container,
                fg_color=Theme.BUBBLE_AI,
                corner_radius=12,
                border_width=1,
                border_color=Theme.CYAN_DARK,
            )
            bubble.pack(side="left", padx=(0, 60))

            # Başlık ve Rozet
            header_box = ctk.CTkFrame(bubble, fg_color="transparent")
            header_box.pack(fill="x", padx=12, pady=(8, 2))

            name_lbl = ctk.CTkLabel(
                header_box,
                text="🤖 MehburAI",
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
                text_color=Theme.CYAN_PRIMARY,
            )
            name_lbl.pack(side="left")

            if source:
                badge_lbl = ctk.CTkLabel(
                    header_box,
                    text=f"• {source}",
                    font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
                    text_color=Theme.TEXT_SECONDARY,
                )
                badge_lbl.pack(side="left", padx=6)

            # ⏭ Atla — yazma animasyonu sürerken görünür; tıklayınca kalanı beklemeden
            # tam metni gösterir (aşağıda do_animate hesaplanınca eklenir)
            skip_btn = None

            if image_path and os.path.isfile(image_path):
                self._attach_image_preview(bubble, image_path)

            do_animate = bool(animate) and Theme.TYPEWRITER_MS > 0 and len(message) > 1
            if do_animate:
                skip_btn = ctk.CTkButton(
                    header_box,
                    text="⏭ Atla",
                    width=56,
                    height=20,
                    font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
                    fg_color="transparent",
                    text_color=Theme.TEXT_SECONDARY,
                    hover_color=Theme.BG_CARD_HOVER,
                    border_width=1,
                    border_color=Theme.TEXT_DARK,
                    corner_radius=6,
                )
                skip_btn.pack(side="right")
            msg_lbl = ctk.CTkLabel(
                bubble,
                text="" if do_animate else message,
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13),
                text_color=Theme.TEXT_PRIMARY,
                wraplength=520,
                justify="left",
            )
            msg_lbl.pack(anchor="w", padx=12, pady=(2, 10))

            url_m = re.search(r"https?://[^\s]+", message)
            if url_m:
                url = url_m.group(0).rstrip(".,);")
                link_lbl = ctk.CTkLabel(
                    bubble, text="🔗 Maddeyi tarayıcıda aç", cursor="hand2",
                    font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, underline=True),
                    text_color=Theme.CYAN_PRIMARY,
                )
                link_lbl.pack(anchor="w", padx=12, pady=(0, 10))
                link_lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

            # 📋 Panoya Kopyala — cevabın tam metnini kopyalar (tıklayınca kısa süre onay gösterir)
            copy_btn = ctk.CTkButton(
                bubble,
                text="📋 Kopyala",
                width=90,
                height=22,
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
                fg_color="transparent",
                text_color=Theme.TEXT_SECONDARY,
                hover_color=Theme.BG_CARD_HOVER,
                border_width=1,
                border_color=Theme.TEXT_DARK,
                corner_radius=6,
            )
            copy_btn.pack(anchor="w", padx=12, pady=(0, 10))
            copy_btn.configure(command=lambda b=copy_btn, m=message: self._copy_to_clipboard(m, b))

            if do_animate:
                self._run_typewriter(msg_lbl, message, on_done, skip_btn)
            elif on_done:
                self.after(0, on_done)

        # Otomatik en aşağı kaydır
        self.after(50, lambda: self.chat_history_box._parent_canvas.yview_moveto(1.0))

    def _attach_image_preview(self, bubble, image_path: str):
        """🎨 Üretilen/düzenlenen bir görseli mesaj balonunun içine küçük önizleme olarak ekler."""
        try:
            from PIL import Image
            img = Image.open(image_path)
            img.thumbnail((360, 360))
            ctk_img = ctk.CTkImage(img, size=img.size)
            lbl = ctk.CTkLabel(bubble, image=ctk_img, text="", cursor="hand2")
            lbl.pack(anchor="w", padx=12, pady=(2, 4))
            lbl.bind("<Button-1>", lambda e, p=image_path: self._open_image_external(p))
            self._chat_images.append(ctk_img)   # GC'ye kurban gitmesin
        except Exception:
            pass

    def _open_image_external(self, path: str):
        """Görsele tıklanınca varsayılan resim görüntüleyicide açar."""
        try:
            os.startfile(path)  # noqa: S606 — yalnızca MehburAI'nin kendi ürettiği yerel dosya
        except Exception:
            pass

    def _copy_to_clipboard(self, text: str, btn):
        """📋 Kopyala — cevabı panoya kopyalar, butonda 1.5 sn '✅ Kopyalandı' gösterir."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()   # bazı Windows sürümlerinde pano güncellemesi için gerekli
        except Exception:
            return
        if not btn.winfo_exists():
            return
        btn.configure(text="✅ Kopyalandı", text_color=Theme.STATUS_ONLINE, border_color=Theme.STATUS_ONLINE)
        self.after(1500, lambda: btn.winfo_exists() and btn.configure(
            text="📋 Kopyala", text_color=Theme.TEXT_SECONDARY, border_color=Theme.TEXT_DARK))

    def _cancel_typewriter(self):
        """Süren yazma animasyonunu durdurur."""
        if getattr(self, "_type_after_id", None):
            try:
                self.after_cancel(self._type_after_id)
            except Exception:
                pass
            self._type_after_id = None

    def _run_typewriter(self, label, full_text: str, on_done=None, skip_btn=None):
        """Etiket metnini harf harf yazar; süre uzunluktan bağımsız ~sabit kalır.
        `skip_btn` verilirse tıklanınca kalan animasyon anında tam metne atlar."""
        self._cancel_typewriter()
        step = max(1, math.ceil(len(full_text) / 110))   # uzun metinde büyük adım
        state = {"i": 0, "done": False}

        def finish():
            if state["done"]:
                return
            state["done"] = True
            self._cancel_typewriter()
            label.configure(text=full_text)
            if skip_btn is not None and skip_btn.winfo_exists():
                skip_btn.destroy()
            try:
                self.chat_history_box._parent_canvas.yview_moveto(1.0)
            except Exception:
                pass
            if on_done:
                on_done()

        if skip_btn is not None:
            skip_btn.configure(command=finish)

        def tick():
            i = state["i"]
            if i >= len(full_text):
                finish()
                return
            label.configure(text=full_text[:i])
            try:
                self.chat_history_box._parent_canvas.yview_moveto(1.0)
            except Exception:
                pass
            state["i"] = i + step
            self._type_after_id = self.after(Theme.TYPEWRITER_MS, tick)

        tick()

    def _add_loading_bubble(self):
        """Cevap beklenirken dönen yükleniyor balonu."""
        self._loading_frame = ctk.CTkFrame(self.chat_history_box, fg_color="transparent")
        self._loading_frame.pack(fill="x", padx=8, pady=4)

        bubble = ctk.CTkFrame(
            self._loading_frame,
            fg_color=Theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Theme.CYAN_DARK,
        )
        bubble.pack(side="left", padx=(0, 60))

        lbl = ctk.CTkLabel(
            bubble,
            text="🤖 MehburAI araştırıyor ve düşünüyor... ⚡",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, slant="italic"),
            text_color=Theme.CYAN_PRIMARY,
            padx=14,
            pady=10,
        )
        lbl.pack()
        self.after(50, lambda: self.chat_history_box._parent_canvas.yview_moveto(1.0))

    def _remove_loading_bubble(self):
        """Yükleniyor balonunu kaldırır."""
        if hasattr(self, "_loading_frame") and self._loading_frame:
            self._loading_frame.destroy()
            self._loading_frame = None

    def _clear_chat_display(self):
        """Aktif sohbetin mesajlarını temizler (sohbet ve başlığı kalır, ruh hali sıfırlanır)."""
        if self._is_processing:
            return
        try:
            self.memory.clear_conversation_messages(self.active_conv_id)
        except Exception:
            pass
        self._refresh_conversation_list()
        self._load_active_conversation()

    # ─────────────────────────────────────────
    # SEKME 2: HAFIZA YÖNETİMİ (MEMORY PANEL)
    # ─────────────────────────────────────────

    def _build_memory_panel(self):
        """Öğrenilen soru-cevapların listelendiği ve yönetildiği panel."""
        self.panel_memory.grid_rowconfigure(1, weight=1)
        self.panel_memory.grid_columnconfigure(0, weight=1)

        # Üst Arama & Kontrol Çubuğu
        top_bar = ctk.CTkFrame(self.panel_memory, fg_color=Theme.BG_CARD, corner_radius=8, height=45)
        top_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 8))
        top_bar.grid_columnconfigure(0, weight=1)

        self.memory_search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="🔍 Hafızadaki sorularda ara...",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            fg_color=Theme.BG_INPUT,
            border_color=Theme.CYAN_DARK,
            height=34,
            corner_radius=8,
        )
        self.memory_search_entry.grid(row=0, column=0, sticky="ew", padx=(8, 10), pady=6)
        self.memory_search_entry.bind("<KeyRelease>", lambda e: self._filter_memory_list())

        btn_refresh = ctk.CTkButton(
            top_bar,
            text="🔄 Yenile",
            font=ctk.CTkFont(size=12),
            fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK,
            width=80,
            height=34,
            command=self._refresh_memory_list,
        )
        btn_refresh.grid(row=0, column=1, padx=4, pady=6)

        btn_clear_all = ctk.CTkButton(
            top_bar,
            text="🗑️ Hafızayı Sıfırla",
            font=ctk.CTkFont(size=12),
            fg_color="#44111E",
            hover_color="#661122",
            text_color="#FFAAAA",
            width=130,
            height=34,
            command=self._confirm_clear_memory,
        )
        btn_clear_all.grid(row=0, column=2, padx=(4, 8), pady=6)

        # Hafıza Kartları Listesi (Scrollable)
        self.memory_list_box = ctk.CTkScrollableFrame(
            self.panel_memory,
            fg_color=Theme.BG_DARKEST,
            corner_radius=10,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
        )
        self.memory_list_box.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # Listeyi Doldur
        self._refresh_memory_list()

    def _refresh_memory_list(self):
        """Veritabanındaki tüm öğrenilen bilgileri arayüze kart olarak dizer."""
        for widget in self.memory_list_box.winfo_children():
            widget.destroy()

        records = self.memory.get_all_knowledge(limit=100)

        if not records:
            empty_lbl = ctk.CTkLabel(
                self.memory_list_box,
                text="🧠 Henüz hafızada kayıtlı bilgi bulunmuyor.\nÇevrim içiyken soru sordukça MehburAI bilgileri buraya kaydedecektir!",
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13),
                text_color=Theme.TEXT_SECONDARY,
                pady=40,
            )
            empty_lbl.pack()
            return

        for rec in records:
            self._create_memory_card(rec)

    def _filter_memory_list(self):
        """Arama çubuğuna göre hafıza listesini filtreler."""
        search_txt = self.memory_search_entry.get().strip().lower()
        for card in self.memory_list_box.winfo_children():
            if hasattr(card, "search_data"):
                if not search_txt or search_txt in card.search_data:
                    card.pack(fill="x", padx=6, pady=4)
                else:
                    card.pack_forget()

    def _create_memory_card(self, rec: dict):
        """Tek bir hafıza kartı oluşturur."""
        rec_id = rec["id"]
        question = rec["question"]
        answer = rec["answer"]
        source = rec.get("source", "Bilinmiyor")
        access_count = rec.get("access_count", 0)
        created_at = rec.get("created_at", "")

        card = ctk.CTkFrame(
            self.memory_list_box,
            fg_color=Theme.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
        )
        card.search_data = f"{question} {answer} {source}".lower()
        card.pack(fill="x", padx=6, pady=4)

        # Üst Satır: Soru ve Silme Butonu
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(10, 4))

        q_lbl = ctk.CTkLabel(
            header_frame,
            text=f"❓ {question}",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            text_color=Theme.CYAN_PRIMARY,
            anchor="w",
            wraplength=600,
            justify="left",
        )
        q_lbl.pack(side="left", fill="x", expand=True)

        btn_del = ctk.CTkButton(
            header_frame,
            text="✕ Sil",
            font=ctk.CTkFont(size=11),
            fg_color=Theme.BG_DARKEST,
            hover_color="#44111E",
            text_color="#FF6688",
            width=50,
            height=24,
            command=lambda rid=rec_id, c=card: self._delete_single_memory(rid, c),
        )
        btn_del.pack(side="right")

        # Orta: Yanıt Metni
        ans_lbl = ctk.CTkLabel(
            card,
            text=f"💡 {answer}",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.TEXT_PRIMARY,
            anchor="w",
            wraplength=680,
            justify="left",
        )
        ans_lbl.pack(anchor="w", padx=12, pady=(2, 8))

        # Alt: Meta Bilgiler
        meta_frame = ctk.CTkFrame(card, fg_color="transparent")
        meta_frame.pack(fill="x", padx=12, pady=(0, 8))

        meta_text = f"📌 Kaynak: {source}  •  👁️ Erişim: {access_count} kez  •  🕒 {created_at[:16]}"
        meta_lbl = ctk.CTkLabel(
            meta_frame,
            text=meta_text,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
            text_color=Theme.TEXT_DARK,
        )
        meta_lbl.pack(side="left")

    def _delete_single_memory(self, record_id: int, card_widget: ctk.CTkFrame):
        """Tek bir kaydı hafızadan siler."""
        if self.memory.delete_knowledge(record_id):
            card_widget.destroy()
            self._update_badges()

    def _confirm_clear_memory(self):
        """Tüm hafızayı silme işlemi."""
        self.memory.clear_all_knowledge()
        self._refresh_memory_list()
        self._update_badges()

    # ─────────────────────────────────────────
    # SEKME 3: AYARLAR (SETTINGS PANEL)
    # ─────────────────────────────────────────

    def _build_settings_panel(self):
        """Gemini API anahtarı, güvenlik modu ve uygulama ayarları paneli."""
        self.panel_settings.grid_columnconfigure(0, weight=1)
        self.panel_settings.grid_rowconfigure(0, weight=1)

        # Ayarlar uzun olduğundan kaydırılabilir bir konteynere yerleştirilir
        self.settings_scroll = ctk.CTkScrollableFrame(
            self.panel_settings, fg_color="transparent"
        )
        self.settings_scroll.grid(row=0, column=0, sticky="nsew")
        self.settings_scroll.grid_columnconfigure(0, weight=1)

        # 1. API Anahtarı Kartı
        api_card = ctk.CTkFrame(
            self.settings_scroll,
            fg_color=Theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Theme.CYAN_DARK,
        )
        api_card.pack(fill="x", padx=0, pady=(0, 12))

        api_title = ctk.CTkLabel(
            api_card,
            text="🔑 Google Gemini API Anahtarı",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=16, weight="bold"),
            text_color=Theme.CYAN_PRIMARY,
        )
        api_title.pack(anchor="w", padx=16, pady=(16, 4))

        api_desc = ctk.CTkLabel(
            api_card,
            text=(
                "MehburAI'nin çevrim içi modda en güncel yapay zeka gücüyle çalışabilmesi için "
                "Google Gemini API anahtarınızı giriniz.\n"
                "Ücretsiz anahtar: https://aistudio.google.com/apikey  (AIzaSy... veya AQ... ile başlar)\n"
                "(API anahtarı olmadan yalnızca Wikipedia özetleri ve kayıtlı hafıza çalışır.)"
            ),
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.TEXT_SECONDARY,
            justify="left",
        )
        api_desc.pack(anchor="w", padx=16, pady=(0, 12))

        # Giriş & Buton Satırı
        api_input_row = ctk.CTkFrame(api_card, fg_color="transparent")
        api_input_row.pack(fill="x", padx=16, pady=(0, 14))
        api_input_row.grid_columnconfigure(0, weight=1)

        current_key = get_api_key() or ""
        self.api_key_entry = ctk.CTkEntry(
            api_input_row,
            placeholder_text="AIzaSy... veya AQ... ile başlayan Gemini API anahtarınızı yapıştırın",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            fg_color=Theme.BG_INPUT,
            border_color=Theme.CYAN_DARK,
            show="•",
            height=40,
            corner_radius=8,
        )
        self.api_key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        if current_key:
            self.api_key_entry.insert(0, current_key)

        btn_save_key = ctk.CTkButton(
            api_input_row,
            text="💾 Kaydet",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=Theme.CYAN_PRIMARY,
            text_color=Theme.BG_DARKEST,
            hover_color=Theme.CYAN_GLOW,
            width=90,
            height=40,
            command=self._save_api_key,
        )
        btn_save_key.grid(row=0, column=1, padx=(0, 6))

        btn_del_key = ctk.CTkButton(
            api_input_row,
            text="✕ Sil",
            font=ctk.CTkFont(size=12),
            fg_color=Theme.BG_CARD_HOVER,
            hover_color="#44111E",
            text_color="#FF8888",
            width=70,
            height=40,
            command=self._remove_api_key,
        )
        btn_del_key.grid(row=0, column=2)

        # Durum Geri Bildirim Etiketi
        self.api_status_lbl = ctk.CTkLabel(
            api_card,
            text="✅ API Anahtarı Kayıtlı" if current_key else "⚠️ API Anahtarı Henüz Girilmedi",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.STATUS_ONLINE if current_key else Theme.STATUS_WARNING,
        )
        self.api_status_lbl.pack(anchor="w", padx=16, pady=(0, 8))

        # 🧪 API Testi — girilen (kaydedilmemiş olsa bile) anahtarı Google'a karşı sınar
        test_row = ctk.CTkFrame(api_card, fg_color="transparent")
        test_row.pack(fill="x", padx=16, pady=(0, 14))
        self.api_test_btn = ctk.CTkButton(
            test_row,
            text="🧪 API'yi Test Et",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK,
            text_color=Theme.CYAN_PRIMARY,
            border_width=1,
            border_color=Theme.CYAN_DARK,
            width=140,
            height=34,
            command=self._test_api_key,
        )
        self.api_test_btn.pack(side="left")
        self.api_test_lbl = ctk.CTkLabel(
            test_row,
            text="Anahtarın çalışıp çalışmadığını Gemini'ye kısa bir istek atarak dener.",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.TEXT_SECONDARY,
            justify="left",
            wraplength=560,
        )
        self.api_test_lbl.pack(side="left", padx=12)

        # 2. 🛡️ Güvenlik Modu Kartı
        self._build_security_card(self.settings_scroll)

        # 2b. 🎙️ Sesli Sohbet Kartı
        self._build_voice_card(self.settings_scroll)

        # 2c. 🎨 Görünüm (renk ayarı) + 2d. 🧠 Otomatik Öğrenme
        self._build_appearance_card(self.settings_scroll)
        self._build_learn_card(self.settings_scroll)

        # 3. Ağ Testi & Durum Kartı
        net_card = ctk.CTkFrame(
            self.settings_scroll,
            fg_color=Theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
        )
        net_card.pack(fill="x", padx=0, pady=(0, 12))

        net_title = ctk.CTkLabel(
            net_card,
            text="🌐 Ağ & Bağlantı Kontrolü (Cloudflare 1.1.1.1 + Google 8.8.8.8)",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
        )
        net_title.pack(anchor="w", padx=16, pady=(14, 6))

        self.net_test_btn = ctk.CTkButton(
            net_card,
            text="🔄 Bağlantıyı Şimdi Test Et",
            font=ctk.CTkFont(size=12),
            fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK,
            height=34,
            command=self._manual_network_check,
        )
        self.net_test_btn.pack(anchor="w", padx=16, pady=(0, 8))

        self.net_status_lbl = ctk.CTkLabel(
            net_card,
            text="Cloudflare ve Google sunucularına ulaşılıp ulaşılamadığını dener.",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.TEXT_SECONDARY,
            justify="left",
        )
        self.net_status_lbl.pack(anchor="w", padx=16, pady=(0, 14))

        # 4. Hakkında Kartı
        about_card = ctk.CTkFrame(
            self.settings_scroll,
            fg_color=Theme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
        )
        about_card.pack(fill="x", padx=0, pady=(0, 12))

        about_title = ctk.CTkLabel(
            about_card,
            text="ℹ️ MehburAI Hakkında",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
        )
        about_title.pack(anchor="w", padx=16, pady=(12, 4))

        about_text = (
            "MehburAI; internet bağlantısına göre otomatik uyum sağlayan hibrit bir yapay zeka sistemidir.\n"
            "• Çevrim İçi: Google Gemini + Türkçe Wikipedia Arama Motoru\n"
            "• Çevrim Dışı: SQLite + Türkçe Morfolojik Semantik Vektör Eşleşmesi\n"
            "• Tema: Neon Cyan & Siyah Cyberpunk Tasarımı"
        )
        about_lbl = ctk.CTkLabel(
            about_card,
            text=about_text,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.TEXT_SECONDARY,
            justify="left",
        )
        about_lbl.pack(anchor="w", padx=16, pady=(0, 14))

    # ─────────────────────────────────────────
    # 🎨 GÖRÜNÜM (RENK AYARI) KARTI
    # ─────────────────────────────────────────

    _CUSTOM_COLOR_LABEL = "Özel renk…"

    @staticmethod
    def _name_for_color(table: dict, value: str) -> str:
        for name, hexv in table.items():
            if hexv.upper() == str(value).upper():
                return name
        return MehburApp._CUSTOM_COLOR_LABEL

    def _build_appearance_card(self, parent):
        """Vurgu rengi + arka plan tonu seçimi; değişiklik yeniden başlatınca uygulanır."""
        self._theme_pending = dict(get_theme_config())

        card = ctk.CTkFrame(parent, fg_color=Theme.BG_CARD, corner_radius=12,
                            border_width=1, border_color=Theme.CYAN_DARK)
        card.pack(fill="x", padx=0, pady=(0, 12))

        ctk.CTkLabel(card, text="🎨 Görünüm (Renk Ayarı)",
                     font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=16, weight="bold"),
                     text_color=Theme.CYAN_PRIMARY).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(card, text="Arayüzün vurgu rengini ve arka plan tonunu istediğin gibi değiştir. "
                                "Önizlemeyi aşağıda gör; 'Uygula' dersen uygulama yeniden başlar.",
                     font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
                     text_color=Theme.TEXT_SECONDARY, justify="left",
                     wraplength=700).pack(anchor="w", padx=16, pady=(0, 10))

        accent_names = list(THEME_ACCENTS) + [self._CUSTOM_COLOR_LABEL]
        bg_names = list(THEME_BACKGROUNDS) + [self._CUSTOM_COLOR_LABEL]

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(row1, text="Vurgu rengi", width=110, anchor="w",
                     text_color=Theme.TEXT_PRIMARY).pack(side="left")
        self.theme_accent_menu = ctk.CTkOptionMenu(
            row1, values=accent_names, command=self._on_accent_choice, width=190,
            fg_color=Theme.BG_INPUT, button_color=Theme.CYAN_DARK,
            button_hover_color=Theme.CYAN_DIM)
        self.theme_accent_menu.set(self._name_for_color(THEME_ACCENTS, self._theme_pending["accent"]))
        self.theme_accent_menu.pack(side="left")

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(row2, text="Arka plan", width=110, anchor="w",
                     text_color=Theme.TEXT_PRIMARY).pack(side="left")
        self.theme_bg_menu = ctk.CTkOptionMenu(
            row2, values=bg_names, command=self._on_bg_choice, width=190,
            fg_color=Theme.BG_INPUT, button_color=Theme.CYAN_DARK,
            button_hover_color=Theme.CYAN_DIM)
        self.theme_bg_menu.set(self._name_for_color(THEME_BACKGROUNDS, self._theme_pending["bg"]))
        self.theme_bg_menu.pack(side="left")

        # Canlı önizleme: küçük bir sahte pencere
        self.theme_preview = ctk.CTkFrame(card, corner_radius=10, border_width=2, height=86)
        self.theme_preview.pack(fill="x", padx=16, pady=(0, 10))
        self.theme_preview.pack_propagate(False)
        self.theme_prev_bubble = ctk.CTkLabel(self.theme_preview, text="MehburAI: Merhaba efendim! 👋",
                                              corner_radius=8, anchor="w", padx=10, height=30)
        self.theme_prev_bubble.pack(anchor="w", padx=12, pady=(12, 4))
        self.theme_prev_btn = ctk.CTkLabel(self.theme_preview, text="Gönder ⚡", corner_radius=8,
                                           width=90, height=28,
                                           font=ctk.CTkFont(weight="bold"))
        self.theme_prev_btn.pack(anchor="w", padx=12)
        self._refresh_theme_preview()

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(btns, text="✅ Uygula ve Yeniden Başlat", height=36,
                      fg_color=Theme.CYAN_PRIMARY, text_color=Theme.BG_DARKEST,
                      hover_color=Theme.CYAN_GLOW,
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._apply_theme_and_restart).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text="↺ Varsayılan (Neon Cyan)", height=36,
                      fg_color=Theme.BG_CARD_HOVER, hover_color=Theme.CYAN_DARK,
                      command=self._reset_theme_and_restart).pack(side="left")

    def _refresh_theme_preview(self):
        c = derive_theme_colors(self._theme_pending["accent"], self._theme_pending["bg"])
        self.theme_preview.configure(fg_color=c["BG_DARK"], border_color=c["CYAN_DARK"])
        self.theme_prev_bubble.configure(fg_color=c["BUBBLE_AI"], text_color="#E8E8EC")
        self.theme_prev_btn.configure(fg_color=c["BTN_PRIMARY_BG"], text_color=c["BTN_PRIMARY_FG"])

    def _pick_custom_color(self, current: str) -> Optional[str]:
        from tkinter import colorchooser
        picked = colorchooser.askcolor(color=current, parent=self, title="Renk seç")
        return picked[1].upper() if picked and picked[1] else None

    def _on_accent_choice(self, name: str):
        if name == self._CUSTOM_COLOR_LABEL:
            color = self._pick_custom_color(self._theme_pending["accent"])
            if not color:
                self.theme_accent_menu.set(self._name_for_color(THEME_ACCENTS, self._theme_pending["accent"]))
                return
            self._theme_pending["accent"] = color
        else:
            self._theme_pending["accent"] = THEME_ACCENTS[name]
        self._refresh_theme_preview()

    def _on_bg_choice(self, name: str):
        if name == self._CUSTOM_COLOR_LABEL:
            color = self._pick_custom_color(self._theme_pending["bg"])
            if not color:
                self.theme_bg_menu.set(self._name_for_color(THEME_BACKGROUNDS, self._theme_pending["bg"]))
                return
            self._theme_pending["bg"] = color
        else:
            self._theme_pending["bg"] = THEME_BACKGROUNDS[name]
        self._refresh_theme_preview()

    def _restart_now(self, why: str):
        if not messagebox.askyesno("Yeniden başlat", f"{why}\n\nMehburAI şimdi yeniden başlatılsın mı?", parent=self):
            return
        if restart_app():
            self._real_quit()
        else:
            messagebox.showwarning("Yeniden başlat", "Otomatik yeniden başlatılamadı — "
                                   "lütfen uygulamayı kapatıp elle aç.", parent=self)

    def _apply_theme_and_restart(self):
        update_theme_config(accent=self._theme_pending["accent"], bg=self._theme_pending["bg"])
        self._restart_now("Renk ayarları kaydedildi.")

    def _reset_theme_and_restart(self):
        reset_theme_config()
        self._restart_now("Varsayılan renklere dönüldü.")

    # ─────────────────────────────────────────
    # 🧠 OTOMATİK ÖĞRENME KARTI
    # ─────────────────────────────────────────

    def _build_learn_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=Theme.BG_CARD, corner_radius=12,
                            border_width=1, border_color=Theme.CYAN_DARK)
        card.pack(fill="x", padx=0, pady=(0, 12))
        ctk.CTkLabel(card, text="🧠 Otomatik Öğrenme",
                     font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=16, weight="bold"),
                     text_color=Theme.CYAN_PRIMARY).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(card, text="MehburAI açıkken sen bir süre soru sormazsan arka planda Wikipedia'dan yeni "
                                "konular öğrenip hafızasına yazar (çevrimdışıyken de kullanır). Ürünlerde "
                                "özellikleri ve eleştirmen/basın değerlendirmelerini Wikipedia'dan çeker (Reddit gibi denetimsiz kaynak yok).",
                     font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
                     text_color=Theme.TEXT_SECONDARY, justify="left",
                     wraplength=700).pack(anchor="w", padx=16, pady=(0, 10))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 6))
        self.learn_switch = ctk.CTkSwitch(row, text="Boştayken otomatik öğren",
                                          progress_color=Theme.CYAN_PRIMARY,
                                          command=self._toggle_auto_learn)
        if get_learn_config()["auto_learn_enabled"]:
            self.learn_switch.select()
        self.learn_switch.pack(side="left")
        ctk.CTkButton(row, text="⚡ Şimdi bir konu öğren", width=170, height=32,
                      fg_color=Theme.BG_CARD_HOVER, hover_color=Theme.CYAN_DARK,
                      command=self._learn_now).pack(side="left", padx=14)

        self.learn_status = ctk.CTkLabel(card, text="Henüz bir şey öğrenmedi.",
                                         font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
                                         text_color=Theme.TEXT_SECONDARY)
        self.learn_status.pack(anchor="w", padx=16, pady=(0, 14))

    def _toggle_auto_learn(self):
        update_learn_config(auto_learn_enabled=bool(self.learn_switch.get()))

    def _learn_now(self):
        self.learn_status.configure(text="⏳ Öğreniyor…", text_color=Theme.STATUS_WARNING)

        def work():
            res = self.learner.learn_once()
            if res is None:
                self._ui_call(lambda: self.learn_status.configure(
                    text="⚠️ Şu an öğrenilemedi (internet/kaynak yok?)", text_color=Theme.STATUS_OFFLINE))
        threading.Thread(target=work, daemon=True, name="MehburAI-LearnNow").start()

    def _on_auto_learned(self, result: dict):
        if hasattr(self, "learn_status") and self.learn_status.winfo_exists():
            kind = "🛒 ürün" if result.get("product") else "📚 konu"
            self.learn_status.configure(
                text=f"✅ Son öğrenilen {kind}: {result['topic']}  —  {result['source']}",
                text_color=Theme.STATUS_ONLINE)
        try:
            self._refresh_memory_list()
        except Exception:
            pass

    # ─────────────────────────────────────────
    # 🎙️ SESLİ SOHBET KARTI
    # ─────────────────────────────────────────

    def _build_voice_card(self, parent):
        """Yerel sesli asistan (uyandırma sözcüğü) + Telegram sesli mesaj ayarları."""
        vcfg = get_voice_config()
        deps_ok = voice_dependencies_ok()

        card = ctk.CTkFrame(
            parent, fg_color=Theme.BG_CARD, corner_radius=12,
            border_width=1, border_color=Theme.CYAN_DARK,
        )
        card.pack(fill="x", padx=0, pady=(0, 12))

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            head, text="🎙️ Sesli Sohbet",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=16, weight="bold"),
            text_color=Theme.CYAN_PRIMARY,
        ).pack(side="left")
        self.voice_switch = ctk.CTkSwitch(
            head, text="Aktif", command=self._toggle_voice,
            progress_color=Theme.STATUS_ONLINE,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
        )
        self.voice_switch.pack(side="right")
        if vcfg.get("voice_enabled") and deps_ok:
            self.voice_switch.select()

        ctk.CTkLabel(
            card, justify="left", wraplength=820,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.TEXT_SECONDARY,
            text=(
                "Bu bilgisayarın mikrofonunu dinler. \"Mehbur\" veya \"Hey Mehbur\" "
                "dediğinde \"Emrinizdeyim efendim\" der ve ardından komutunu bekler "
                "(soru sor, \"not defteri aç\", \"bilgisayarı kapat\" ...). Yanlış "
                "duyulan kelimeleri de anlamaya çalışır. Tümüyle çevrimdışı tanıma; "
                "yanıt sesi çevrimiçi üretilir. İlk açılışta ~35 MB Türkçe ses modeli iner."
            ),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            row, text="Yanıt sesi:", font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.TEXT_PRIMARY,
        ).pack(side="left", padx=(0, 8))
        _cur_voice = ("Ahmet (erkek)" if vcfg.get("voice_tts_voice") == "tr-TR-AhmetNeural"
                      else "Emel (kadın)")
        self.voice_choice = ctk.CTkOptionMenu(
            row, values=["Emel (kadın)", "Ahmet (erkek)"], command=self._change_voice,
            width=150, font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            fg_color=Theme.BG_INPUT, button_color=Theme.CYAN_DARK,
        )
        self.voice_choice.set(_cur_voice)
        self.voice_choice.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row, text="🔊 Sesi Test Et", width=130, height=28,
            font=ctk.CTkFont(size=12), fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK, command=self._test_voice,
        ).pack(side="left")

        # — JARVIS tam ekran görseli —
        orow = ctk.CTkFrame(card, fg_color="transparent")
        orow.pack(fill="x", padx=16, pady=(2, 2))
        self.jarvis_switch = ctk.CTkSwitch(
            orow, text="🟦 JARVIS ekranı — uyandırınca tam ekran nokta küresi (Iron Man tarzı)",
            command=self._toggle_overlay, progress_color=Theme.STATUS_ONLINE,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
        )
        self.jarvis_switch.pack(side="left")
        if vcfg.get("voice_overlay_enabled", True):
            self.jarvis_switch.select()
        ctk.CTkButton(
            orow, text="👁️ Önizle", width=90, height=26,
            font=ctk.CTkFont(size=12), fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK, command=self._preview_jarvis,
        ).pack(side="left", padx=(10, 0))
        ctk.CTkLabel(
            card, text="Boşta/yanıt: neon cyan • komut dinlerken: koyu sarı • hata: neon kırmızı  "
                       "(ESC ile kapanır, iş bitince kendiliğinden kaybolur)",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11), text_color=Theme.TEXT_DARK,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self.tg_voice_switch = ctk.CTkSwitch(
            card, text="Telegram'daki sesli mesajları yazıya çevirip yanıtla",
            command=self._toggle_telegram_voice, progress_color=Theme.STATUS_ONLINE,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
        )
        self.tg_voice_switch.pack(anchor="w", padx=16, pady=(2, 8))
        if vcfg.get("telegram_voice_enabled", True):
            self.tg_voice_switch.select()

        _lbl, _col = self._VOICE_STATE_LABEL.get(
            "dinliyor" if (vcfg.get("voice_enabled") and deps_ok) else "kapali"
        )
        self.voice_status_lbl = ctk.CTkLabel(
            card, text=(_lbl if deps_ok else "⚠️ Ses kütüphaneleri kurulu değil: "
                        + ", ".join(voice_missing_deps())),
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text_color=(_col if deps_ok else Theme.STATUS_OFFLINE),
        )
        self.voice_status_lbl.pack(anchor="w", padx=16, pady=(0, 14))

    # ─────────────────────────────────────────
    # 🛡️ GÜVENLİK MODU KARTI
    # ─────────────────────────────────────────

    def _build_security_card(self, parent):
        """Yetkisiz erişim alarmı ayarları (korumalı yol, şifre, Telegram)."""
        cfg = get_security_config()

        card = ctk.CTkFrame(
            parent, fg_color=Theme.BG_CARD, corner_radius=12,
            border_width=1, border_color=Theme.STATUS_OFFLINE,
        )
        card.pack(fill="x", padx=0, pady=(0, 12))

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            head, text="🛡️ Güvenlik Modu (Yetkisiz Erişim Alarmı)",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=16, weight="bold"),
            text_color=Theme.STATUS_OFFLINE,
        ).pack(side="left")

        self.sec_enable_switch = ctk.CTkSwitch(
            head, text="Aktif", command=self._toggle_security,
            progress_color=Theme.STATUS_ONLINE,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
        )
        self.sec_enable_switch.pack(side="right")
        if cfg.get("security_enabled"):
            self.sec_enable_switch.select()

        ctk.CTkLabel(
            card, justify="left", wraplength=820,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.TEXT_SECONDARY,
            text=(
                "Korunan bir klasör Dosya Gezgini'nde açıldığında, korunan bir program "
                "çalıştırıldığında ya da korunan bir dosya/klasör silinmeye çalışıldığında "
                "MehburAI şifre sorar. Şifre yanlış girilir ya da ekran kapatılırsa: web "
                "kameradan fotoğraf çekilir, Telegram'dan size gönderilir ve kişiye "
                "\"fotoğrafınız çekildi ve cihaz sahibine iletildi\" uyarısı gösterilir. "
                "Silme girişiminde dosya gizli yedekten otomatik geri yüklenir."
            ),
        ).pack(anchor="w", padx=16, pady=(0, 10))

        # — Arka planda / açılışta çalışma —
        self.sec_autostart_switch = ctk.CTkSwitch(
            card, text="Windows açılışında otomatik başlat (arka planda çalışır)",
            command=self._toggle_autostart, progress_color=Theme.STATUS_ONLINE,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
        )
        self.sec_autostart_switch.pack(anchor="w", padx=16, pady=(0, 4))
        if is_autostart_enabled():
            self.sec_autostart_switch.select()
        ctk.CTkLabel(
            card, text="Pencereyi kapatsan bile güvenlik modu sistem tepsisinde çalışmaya devam eder.",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11), text_color=Theme.TEXT_DARK,
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # — Korumalı yollar —
        ctk.CTkLabel(
            card, text="📁 Korumalı yollar (her satıra bir tane — klasör veya .exe):",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(4, 4))

        self.sec_paths_box = ctk.CTkTextbox(
            card, height=70, fg_color=Theme.BG_INPUT, border_color=Theme.CYAN_DARK,
            border_width=1, font=ctk.CTkFont(family="Consolas", size=12), corner_radius=8,
        )
        self.sec_paths_box.pack(fill="x", padx=16, pady=(0, 6))
        self.sec_paths_box.insert("1.0", "\n".join(cfg.get("security_watch_paths", [])))
        # Odaktan çıkınca / her tuşta (gecikmeli) otomatik kaydet — buton unutulsa da kaybolmaz
        _inner = getattr(self.sec_paths_box, "_textbox", self.sec_paths_box)
        _inner.bind("<FocusOut>", self._save_security_paths, add=True)
        _inner.bind("<KeyRelease>", self._schedule_paths_save, add=True)

        paths_btns = ctk.CTkFrame(card, fg_color="transparent")
        paths_btns.pack(anchor="w", padx=16, pady=(0, 12))
        ctk.CTkButton(
            paths_btns, text="💾 Yolları Kaydet", height=30, width=140,
            font=ctk.CTkFont(size=12), fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK, command=self._save_security_paths,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            paths_btns, text="🖥️ Çalışan programdan seç", height=30, width=190,
            font=ctk.CTkFont(size=12), fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK, command=self._pick_running_app,
        ).pack(side="left")

        # — Şifre —
        pass_row = ctk.CTkFrame(card, fg_color="transparent")
        pass_row.pack(fill="x", padx=16, pady=(0, 4))
        pass_row.grid_columnconfigure(0, weight=1)
        self.sec_pass_entry = ctk.CTkEntry(
            pass_row, placeholder_text="🔒 Güvenlik şifresi belirle / değiştir",
            show="•", height=38, fg_color=Theme.BG_INPUT, border_color=Theme.CYAN_DARK,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12), corner_radius=8,
        )
        self.sec_pass_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            pass_row, text="🔒 Kaydet", width=90, height=38,
            font=ctk.CTkFont(size=12, weight="bold"), fg_color=Theme.CYAN_PRIMARY,
            text_color=Theme.BG_DARKEST, hover_color=Theme.CYAN_GLOW,
            command=self._save_security_password,
        ).grid(row=0, column=1)

        self.sec_pass_status = ctk.CTkLabel(
            card, font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text=("✅ Şifre tanımlı" if has_security_password() else "⚠️ Henüz şifre belirlenmedi"),
            text_color=(Theme.STATUS_ONLINE if has_security_password() else Theme.STATUS_WARNING),
        )
        self.sec_pass_status.pack(anchor="w", padx=16, pady=(0, 12))

        # — Telegram —
        ctk.CTkLabel(
            card, text="📨 Telegram Bildirimi — bot: \"MehburAI (Telegram)\"",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(4, 2))
        ctk.CTkLabel(
            card, justify="left", wraplength=820,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.TEXT_DARK,
            text=(
                "1) Telegram'da @BotFather → /newbot → ad: MehburAI (Telegram) → "
                "bir kullanıcı adı ver → TOKEN'ı kopyala\n"
                "2) Oluşturduğun bota Telegram'dan bir mesaj yaz (\"merhaba\")\n"
                "3) Chat ID'n için: @userinfobot'a yaz, verdiği numarayı aşağıya gir"
            ),
        ).pack(anchor="w", padx=16, pady=(0, 6))

        # Token'ı ASLA alana geri yazma (maskeli değer kaydedilip gerçek token'ı ezebiliyor).
        # Kayıtlıysa alanı boş bırak, placeholder ile durumu belirt; boş bırakılırsa değişmez.
        _tok_saved = is_valid_bot_token(cfg.get("telegram_bot_token", ""))
        self.sec_tg_token = ctk.CTkEntry(
            card,
            placeholder_text=("✅ Token kayıtlı — değiştirmek için yeni token yapıştır"
                              if _tok_saved else "Bot Token (123456:ABC-DEF...)"),
            show="•", height=36,
            fg_color=Theme.BG_INPUT, border_color=Theme.CYAN_DARK,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12), corner_radius=8,
        )
        self.sec_tg_token.pack(fill="x", padx=16, pady=(0, 6))

        chat_row = ctk.CTkFrame(card, fg_color="transparent")
        chat_row.pack(fill="x", padx=16, pady=(0, 8))
        chat_row.grid_columnconfigure(0, weight=1)
        self.sec_tg_chat = ctk.CTkEntry(
            chat_row, placeholder_text="Chat ID (örn. 123456789)", height=36,
            fg_color=Theme.BG_INPUT, border_color=Theme.CYAN_DARK,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12), corner_radius=8,
        )
        self.sec_tg_chat.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        if cfg.get("telegram_chat_id"):
            self.sec_tg_chat.insert(0, cfg["telegram_chat_id"])
        ctk.CTkButton(
            chat_row, text="🔎 Otomatik Bul", width=130, height=36,
            font=ctk.CTkFont(size=12), fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK, command=self._autodetect_chat_id,
        ).grid(row=0, column=1)

        tg_btns = ctk.CTkFrame(card, fg_color="transparent")
        tg_btns.pack(anchor="w", padx=16, pady=(0, 10))
        ctk.CTkButton(
            tg_btns, text="💾 Telegram Kaydet", width=150, height=32,
            font=ctk.CTkFont(size=12), fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK, command=self._save_telegram,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            tg_btns, text="📨 Test Gönder", width=120, height=32,
            font=ctk.CTkFont(size=12), fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK, command=self._test_telegram,
        ).pack(side="left")

        # — Telegram'dan uzaktan kontrol —
        self.sec_remote_switch = ctk.CTkSwitch(
            card,
            text="🤖 Telegram'dan uzaktan kontrol (bota yazarak MehburAI'ı yönet)",
            command=self._toggle_remote, progress_color=Theme.STATUS_ONLINE,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
        )
        self.sec_remote_switch.pack(anchor="w", padx=16, pady=(2, 2))
        if cfg.get("telegram_remote_enabled"):
            self.sec_remote_switch.select()
        ctk.CTkLabel(
            card, justify="left", wraplength=820,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11), text_color=Theme.TEXT_DARK,
            text=(
                "Açıkken yalnızca yukarıdaki Chat ID (cihaz sahibi) bota komut verebilir; "
                "diğer herkes yok sayılır. Bota normal mesaj yaz (soru sor, \"not defteri aç\", "
                "\"sesi kıs\"...) ya da /ekran, /foto, /durum, /guvenlik ac komutlarını kullan."
            ),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        self.sec_status = ctk.CTkLabel(
            card, text=self._security_status_text(),
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11, weight="bold"),
            text_color=Theme.TEXT_SECONDARY,
        )
        self.sec_status.pack(anchor="w", padx=16, pady=(0, 14))

    def _security_status_text(self) -> str:
        cfg = get_security_config()
        parts = []
        parts.append("🟢 İzleme açık" if self.security_guard.is_running() else "🔴 İzleme kapalı")
        parts.append(f"{len(cfg.get('security_watch_paths', []))} korumalı yol")
        parts.append("Telegram ✓" if TelegramNotifier.is_configured() else "Telegram ✗")
        parts.append("Şifre ✓" if has_security_password() else "Şifre ✗")
        parts.append("Uzaktan kontrol ✓" if self.telegram_bot.is_running() else "Uzaktan kontrol ✗")
        return "  •  ".join(parts)

    def _refresh_security_status(self):
        if hasattr(self, "sec_status"):
            self.sec_status.configure(text=self._security_status_text())
        if hasattr(self, "sec_pass_status"):
            ok = has_security_password()
            self.sec_pass_status.configure(
                text=("✅ Şifre tanımlı" if ok else "⚠️ Henüz şifre belirlenmedi"),
                text_color=(Theme.STATUS_ONLINE if ok else Theme.STATUS_WARNING),
            )

    def _toggle_security(self):
        enabled = bool(self.sec_enable_switch.get())
        if enabled and not has_security_password():
            self.sec_enable_switch.deselect()
            self.sec_status.configure(
                text="⚠️ Önce bir güvenlik şifresi belirleyin!", text_color=Theme.STATUS_WARNING
            )
            return
        update_security_config(security_enabled=enabled)
        if enabled:
            self.security_guard.start()
            self._setup_tray()
            # Güvenlik açılınca Windows açılışında otomatik başlatmayı da aç
            if not is_autostart_enabled() and set_autostart(True):
                if hasattr(self, "sec_autostart_switch"):
                    self.sec_autostart_switch.select()
        else:
            self.security_guard.stop()
        self._refresh_security_status()

    def _toggle_autostart(self):
        want = bool(self.sec_autostart_switch.get())
        ok = set_autostart(want)
        if not ok:
            (self.sec_autostart_switch.deselect if want else self.sec_autostart_switch.select)()
            self.sec_status.configure(
                text="⚠️ Otomatik başlatma ayarlanamadı.", text_color=Theme.STATUS_WARNING
            )
        else:
            self.sec_status.configure(
                text=("✅ Windows açılışında otomatik başlayacak." if want
                      else "Otomatik başlatma kapatıldı."),
                text_color=Theme.STATUS_ONLINE if want else Theme.TEXT_SECONDARY,
            )

    def _schedule_paths_save(self, *_a):
        if getattr(self, "_paths_save_job", None):
            try:
                self.after_cancel(self._paths_save_job)
            except Exception:
                pass
        self._paths_save_job = self.after(1200, self._save_security_paths)

    def _save_security_paths(self, *_a):
        self._paths_save_job = None
        raw = self.sec_paths_box.get("1.0", "end")
        paths = [ln.strip().strip('"') for ln in raw.splitlines() if ln.strip()]
        update_security_config(security_watch_paths=paths)
        if hasattr(self, "sec_status"):
            self.sec_status.configure(
                text=f"✅ {len(paths)} korumalı yol kaydedildi.", text_color=Theme.STATUS_ONLINE
            )
            self.after(1800, self._refresh_security_status)

    def _add_watch_path(self, path: str):
        cur = [ln.strip() for ln in self.sec_paths_box.get("1.0", "end").splitlines() if ln.strip()]
        if path not in cur:
            cur.append(path)
        self.sec_paths_box.delete("1.0", "end")
        self.sec_paths_box.insert("1.0", "\n".join(cur))
        self._save_security_paths()

    def _pick_running_app(self):
        """Açık programları listeleyip seçileni korumalı yollara ekler."""
        top = ctk.CTkToplevel(self)
        top.title("🖥️ Çalışan Programlar")
        top.geometry("620x440")
        top.configure(fg_color=Theme.BG_DARK)
        top.transient(self)
        top.attributes("-topmost", True)
        try:
            top.after(120, top.grab_set)
        except Exception:
            pass

        ctk.CTkLabel(
            top, text="Korumalı yollara eklemek için bir programa tıkla",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            text_color=Theme.CYAN_PRIMARY,
        ).pack(pady=(14, 8))

        listbox = ctk.CTkScrollableFrame(top, fg_color=Theme.BG_DARKEST)
        listbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        loading = ctk.CTkLabel(listbox, text="Programlar taranıyor...", text_color=Theme.TEXT_SECONDARY)
        loading.pack(pady=20)

        def fill(apps):
            if not listbox.winfo_exists():
                return
            try:
                loading.destroy()
            except Exception:
                pass
            if not apps:
                ctk.CTkLabel(
                    listbox, text="Penceresi açık program bulunamadı.\nProgramı açıp tekrar dene.",
                    text_color=Theme.TEXT_SECONDARY, justify="center",
                ).pack(pady=20)
                return
            for name, path in apps:
                def choose(p=path):
                    self._add_watch_path(p)
                    top.destroy()
                ctk.CTkButton(
                    listbox, text=f"  {name}\n  {path}", anchor="w", height=46,
                    font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
                    fg_color=Theme.BG_CARD, hover_color=Theme.CYAN_DARK,
                    text_color=Theme.TEXT_PRIMARY, command=choose,
                ).pack(fill="x", pady=3)

        # Tarama ana thread'de (kısa sürer, ~1-2 sn); pencere çizildikten sonra
        top.after(80, lambda: fill(SecurityGuard.list_running_apps()))

    def _save_security_password(self):
        pw = self.sec_pass_entry.get().strip()
        if len(pw) < 3:
            self.sec_pass_status.configure(
                text="⚠️ Şifre en az 3 karakter olmalı", text_color=Theme.STATUS_WARNING
            )
            return
        set_security_password(pw)
        self.sec_pass_entry.delete(0, "end")
        self._refresh_security_status()
        self.sec_pass_status.configure(text="✅ Şifre kaydedildi", text_color=Theme.STATUS_ONLINE)

    def _save_telegram(self):
        changes = {"telegram_chat_id": self.sec_tg_chat.get().strip()}

        raw_token = self.sec_tg_token.get().strip()
        # Boş alan = "token'a dokunma". Sadece alanda gerçek bir token varsa yaz.
        if raw_token and not all(ch == "•" for ch in raw_token):
            if is_valid_bot_token(raw_token):
                changes["telegram_bot_token"] = raw_token
                self.sec_tg_token.delete(0, "end")   # sırrı ekranda / bellekte tutma
                self.sec_tg_token.configure(
                    placeholder_text="✅ Token kayıtlı — değiştirmek için yeni token yapıştır"
                )
            else:
                self.sec_status.configure(
                    text="⚠️ Bot Token biçimi geçersiz (ör. 123456789:AA...). Token kaydedilmedi.",
                    text_color=Theme.STATUS_WARNING,
                )
                update_security_config(**changes)   # yine de Chat ID'yi kaydet
                return

        update_security_config(**changes)
        self.sec_status.configure(text="✅ Telegram bilgileri kaydedildi.", text_color=Theme.STATUS_ONLINE)
        # Uzaktan kontrol açık ama bot henüz çalışmıyorsa (bilgiler yeni girildi) başlat.
        # Zaten çalışıyorsa döngü yeni token/chat ID'yi bir sonraki turda kendiliğinden kullanır.
        if get_security_config().get("telegram_remote_enabled") and not self.telegram_bot.is_running():
            self.telegram_bot.start()
        self.after(1800, self._refresh_security_status)

    def _autodetect_chat_id(self):
        token = self.sec_tg_token.get().strip()
        if not token or all(ch == "•" for ch in token):
            token = get_security_config().get("telegram_bot_token", "").strip()
        if not is_valid_bot_token(token):
            self.sec_status.configure(text="⚠️ Önce geçerli bir Bot Token kaydet.",
                                      text_color=Theme.STATUS_WARNING)
            return
        self.sec_status.configure(
            text="🔎 Bota yazdığın mesaj aranıyor...", text_color=Theme.TEXT_SECONDARY
        )

        def worker():
            chat_id, msg = TelegramNotifier.detect_chat_id(token)

            def show():
                if chat_id and self.sec_tg_chat.winfo_exists():
                    self.sec_tg_chat.delete(0, "end")
                    self.sec_tg_chat.insert(0, chat_id)
                    self._save_telegram()
                if hasattr(self, "sec_status") and self.sec_status.winfo_exists():
                    self.sec_status.configure(
                        text=("✅ " if chat_id else "⚠️ ") + msg,
                        text_color=(Theme.STATUS_ONLINE if chat_id else Theme.STATUS_WARNING),
                    )
            self._ui_call(show)
        threading.Thread(target=worker, daemon=True, name="MehburAI-ChatIdDetect").start()

    def _test_telegram(self):
        self._save_telegram()
        self.sec_status.configure(text="📨 Test mesajı gönderiliyor...", text_color=Theme.TEXT_SECONDARY)

        def worker():
            ok, msg = TelegramNotifier.test()

            def show():
                if hasattr(self, "sec_status") and self.sec_status.winfo_exists():
                    self.sec_status.configure(
                        text=("✅ " if ok else "❌ ") + msg,
                        text_color=(Theme.STATUS_ONLINE if ok else Theme.STATUS_OFFLINE),
                    )
            self._ui_call(show)
        threading.Thread(target=worker, daemon=True, name="MehburAI-TelegramTest").start()

    # ── Erişim tespit edilince: şifre ekranı ──

    def _poll_security_queue(self):
        """Guard thread'inin bildirdiği erişimleri ana thread'de işler."""
        try:
            while True:
                item = self._security_queue.get_nowait()
                if isinstance(item, tuple):
                    path, event = item
                else:
                    path, event = item, "access"
                self._show_security_challenge(path, event)
        except queue.Empty:
            pass
        except Exception:
            pass
        finally:
            try:
                if self.winfo_exists():
                    self.after(700, self._poll_security_queue)
            except Exception:
                pass

    def _show_security_challenge(self, path: str, event: str = "access"):
        is_delete = (event == "delete")
        if path in self._security_dialogs and self._security_dialogs[path].winfo_exists():
            self._security_dialogs[path].lift()
            return
        if not has_security_password():
            self.security_guard.mark_resolved(path)
            return

        # 1) Tüm ekranı kaplayan koyu perde — açılan şey görünmesin / kullanılamasın
        backdrop = ctk.CTkToplevel(self)
        backdrop.configure(fg_color="#05050A")
        try:
            backdrop.overrideredirect(True)
        except Exception:
            pass
        try:
            sw, sh = backdrop.winfo_screenwidth(), backdrop.winfo_screenheight()
            backdrop.geometry(f"{sw}x{sh}+0+0")
        except Exception:
            pass
        backdrop.attributes("-topmost", True)
        try:
            backdrop.attributes("-alpha", 0.95)
        except Exception:
            pass
        ctk.CTkLabel(
            backdrop, text="🛡️  MehburAI Güvenlik Modu",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=26, weight="bold"),
            text_color=Theme.CYAN_DIM,
        ).place(relx=0.5, rely=0.12, anchor="center")
        backdrop.lift()

        # 2) Şifre ekranı (perdenin üstünde)
        dlg = ctk.CTkToplevel(self)
        dlg.title("🔒 MehburAI Güvenlik Modu")
        dlg.geometry("480x360")
        dlg.resizable(False, False)
        dlg.configure(fg_color=Theme.BG_DARK)
        dlg.transient(self)
        dlg.attributes("-topmost", True)
        try:
            dlg.after(150, dlg.grab_set)
        except Exception:
            pass
        self._security_dialogs[path] = dlg
        state = {"alerted": False}
        dlg.after(200, dlg.lift)
        dlg.after(450, dlg.lift)

        ctk.CTkLabel(
            dlg,
            text="🗑️ Bu korumalı dosya siliniyor" if is_delete else "🔒 Bu konum korumalı",
            text_color=Theme.STATUS_OFFLINE,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=18, weight="bold"),
        ).pack(pady=(20, 2))
        ctk.CTkLabel(
            dlg, text=os.path.basename(path.rstrip("\\/")) or path, text_color=Theme.TEXT_SECONDARY,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
        ).pack(pady=(0, 6))
        if is_delete:
            ctk.CTkLabel(
                dlg, justify="center", wraplength=420,
                text="Silme işlemi için güvenlik şifresi gerekli.\n"
                     "Şifre girilmezse dosya gizli yedekten geri yüklenecek.",
                text_color=Theme.TEXT_SECONDARY,
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            ).pack(pady=(0, 4))
        ctk.CTkLabel(
            dlg, justify="center", wraplength=420,
            text="📸 Bilgisayarın sahibine fotoğrafınız gönderilecek.\nKameraya bakın, gülümseyin :D",
            text_color=Theme.STATUS_WARNING,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
        ).pack(pady=(0, 10))

        entry = ctk.CTkEntry(
            dlg, placeholder_text="Güvenlik şifresini girin", show="•", width=320, height=40,
            fg_color=Theme.BG_INPUT, border_color=Theme.CYAN_DARK,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13),
        )
        entry.pack(pady=(0, 8))
        entry.after(250, entry.focus_force)

        info = ctk.CTkLabel(
            dlg, text="", justify="center", wraplength=420,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
        )
        info.pack(pady=(2, 6))

        def _deny(reason: str):
            if is_delete:
                info.configure(
                    text="⚠️ " + reason + " Fotoğrafınız çekildi, cihaz sahibine iletildi "
                         "ve dosya geri yükleniyor.",
                    text_color=Theme.STATUS_OFFLINE,
                )
            else:
                info.configure(
                    text="⚠️ " + reason + " Fotoğrafınız çekildi, cihaz sahibine iletildi "
                         "ve açtığınız şey kapatılıyor.",
                    text_color=Theme.STATUS_OFFLINE,
                )
            if not state["alerted"]:
                state["alerted"] = True
                if is_delete:
                    self._fire_intruder_alert(
                        "Korumalı dosya izinsiz silinmeye çalışıldı", restore_path=path
                    )
                else:
                    self._fire_intruder_alert(reason.rstrip("."), close_path=path)
            self.after(3000, lambda: self._close_security_dialog(path))

        def do_verify():
            if verify_security_password(entry.get()):
                if is_delete:
                    # Silme yetkiyle onaylandı — yedeği at, dosyanın silinmesine izin ver
                    FileBackup.discard(path)
                self.security_guard.mark_passed(path)
                self._close_security_dialog(path)
            else:
                _deny("Hatalı şifre.")

        def on_x():
            _deny("Doğrulama yapılmadı.")

        entry.bind("<Return>", lambda e: do_verify())
        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(pady=(4, 0))
        ctk.CTkButton(
            btns, text="Doğrula", width=140, height=38,
            font=ctk.CTkFont(size=13, weight="bold"), fg_color=Theme.CYAN_PRIMARY,
            text_color=Theme.BG_DARKEST, hover_color=Theme.CYAN_GLOW, command=do_verify,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btns, text="Kapat", width=100, height=38, font=ctk.CTkFont(size=13),
            fg_color=Theme.BG_CARD_HOVER, hover_color="#44111E", text_color="#FF8888",
            command=on_x,
        ).pack(side="left", padx=6)
        dlg.protocol("WM_DELETE_WINDOW", on_x)
        self._security_backdrops[path] = backdrop

    def _close_security_dialog(self, path: str):
        dlg = self._security_dialogs.pop(path, None)
        if dlg is not None:
            try:
                dlg.grab_release()
            except Exception:
                pass
            try:
                dlg.destroy()
            except Exception:
                pass
        backdrop = self._security_backdrops.pop(path, None)
        if backdrop is not None:
            try:
                backdrop.destroy()
            except Exception:
                pass
        self.security_guard.mark_resolved(path)

    def _ui_call(self, fn):
        """Arka plan thread'inden UI'ı güvenle günceller (pencere kapandıysa yut)."""
        try:
            if self.winfo_exists():
                self.after(0, fn)
        except Exception:
            pass

    def _fire_intruder_alert(self, reason: str, close_path: Optional[str] = None,
                             restore_path: Optional[str] = None):
        """Hedefi kapat / dosyayı geri yükle + kamera + Telegram işini arka planda yapar (UI donmasın)."""
        def worker():
            result = trigger_intruder_alert(reason, close_path=close_path, restore_path=restore_path)

            def show():
                if hasattr(self, "sec_status") and self.sec_status.winfo_exists():
                    self.sec_status.configure(
                        text=f"🚨 Uyarı gönderildi: {result['detail']}",
                        text_color=Theme.STATUS_OFFLINE,
                    )
            self._ui_call(show)
        threading.Thread(target=worker, daemon=True, name="MehburAI-IntruderAlert").start()

    # ── Telegram'dan uzaktan kontrol ──

    def _telegram_query(self, text: str):
        """Telegram botundan gelen mesajı MehburAI zeka motoruna verir, yanıtı döndürür.
        (Bot kendi thread'inde çağırır — GUI thread'ini bloklamaz.)
        🎨 Görsel üretildi/düzenlendiyse (metin, görsel_yolu) tuple'ı döner —
        bot bunu fotoğraf olarak gönderir."""
        with self._ai_lock:
            result = self.ai.process_query(text)
        answer = (result or {}).get("answer", "") or "(boş yanıt)"
        src = (result or {}).get("source", "")
        full = f"{answer}\n\n— {src}" if src else answer
        image_path = (result or {}).get("image_path")
        return (full, image_path) if image_path else full

    # ── 🎙️ Sesli Sohbet (yalnız bilgisayarda) ──

    def _voice_command(self, text: str) -> str:
        """Sesli asistandan gelen komutu zeka motoruna verir (sistem araçları dahil)."""
        with self._ai_lock:
            result = self.ai.process_query(text)
        return (result or {}).get("answer", "") or "Yanıt üretemedim efendim."

    _MIC_STATE_COLOR = {
        "dinliyor": Theme.STATUS_ONLINE,
        "uyandi": Theme.CYAN_PRIMARY,
        "komut_dinliyor": Theme.STATUS_WARNING,
        "islemde": Theme.STATUS_WARNING,
        "yanit": Theme.CYAN_PRIMARY,
        "model_indiriliyor": Theme.STATUS_WARNING,
        "model_yok": Theme.STATUS_OFFLINE,
        "mikrofon_hatasi": Theme.STATUS_OFFLINE,
        "kapali": Theme.TEXT_DARK,
        "kapalı": Theme.TEXT_DARK,
    }

    _VOICE_STATE_LABEL = {
        "dinliyor": ("🟢 Dinliyor — 'Hey Mehbur' de", Theme.STATUS_ONLINE),
        "uyandi": ("👂 Emrinizdeyim...", Theme.CYAN_PRIMARY),
        "komut_dinliyor": ("🎤 Komutu dinliyor...", Theme.STATUS_WARNING),
        "islemde": ("⚙️ İşleniyor...", Theme.STATUS_WARNING),
        "yanit": ("💬 Yanıtlıyor...", Theme.CYAN_PRIMARY),
        "model_indiriliyor": ("⬇️ Türkçe ses modeli indiriliyor (~35 MB)...", Theme.STATUS_WARNING),
        "model_yok": ("⚠️ Ses modeli yüklenemedi (internet?)", Theme.STATUS_OFFLINE),
        "mikrofon_hatasi": ("⚠️ Mikrofona erişilemedi", Theme.STATUS_OFFLINE),
        "kapali": ("🔴 Kapalı", Theme.TEXT_SECONDARY),
        "kapalı": ("🔴 Kapalı", Theme.TEXT_SECONDARY),
    }

    def _on_voice_state(self, state: str, text: str = ""):
        self._voice_state = state
        if hasattr(self, "voice_status_lbl") and self.voice_status_lbl.winfo_exists():
            txt, col = self._VOICE_STATE_LABEL.get(state, (f"• {state}", Theme.TEXT_SECONDARY))
            self.voice_status_lbl.configure(text=txt, text_color=col)
        self._update_mic_button(state)
        self._drive_jarvis(state, text)

    def _update_mic_button(self, state: Optional[str] = None):
        """Sohbet kutusundaki 🎤 butonunu sesli sohbet durumuna göre renklendirir."""
        if not hasattr(self, "mic_btn") or not self.mic_btn.winfo_exists():
            return
        if self._dictating:
            self.mic_btn.configure(text="⏺", text_color=Theme.NEON_RED, border_color=Theme.NEON_RED)
            return
        if state is None:
            active = bool(get_voice_config().get("voice_enabled")) and voice_dependencies_ok()
            state = "dinliyor" if active else "kapali"
        color = self._MIC_STATE_COLOR.get(state, Theme.TEXT_DARK)
        self.mic_btn.configure(text="🎤", text_color=color, border_color=color)

    _MIC_ERRORS = {
        "mic": "Mikrofona erişilemedi. Windows Ayarlar → Gizlilik ve güvenlik → Mikrofon bölümünden "
               "masaüstü uygulamalarının mikrofon kullanmasına izin verildiğini kontrol et.",
        "model": "Türkçe ses modeli yüklenemedi (ilk kullanımda internet gerekir).",
    }

    def _toggle_voice_from_chat(self):
        """Sohbet kutusundaki 🎤 butonu — bas-konuş: konuşmanı yazıya çevirip gönderir.
        Dinlerken tekrar basılırsa o ana kadar duyulan gönderilir."""
        if self._dictating and self._dictation is not None:
            self._dictation.stop()
            return
        if self._call is not None:      # 📞 görüşmesi mikrofonu kullanıyor
            return
        if Dictation is None or not voice_dependencies_ok():
            messagebox.showwarning(
                "Sesli Sohbet",
                "Eksik kütüphane: " + ", ".join(voice_missing_deps()),
                parent=self,
            )
            return
        if self._is_processing:
            return

        self._dictating = True
        if self.voice_assistant is not None:
            self.voice_assistant.pause()
        self.query_entry.delete(0, "end")
        self.query_entry.configure(placeholder_text="🎤 Dinliyorum... konuş (bitirmek için 🎤'e tekrar bas)")
        self._update_mic_button()

        self._dictation = Dictation(
            on_partial=lambda t: self._ui_call(lambda: self._dictation_partial(t)),
            on_done=lambda t, e: self._ui_call(lambda: self._dictation_done(t, e)),
        )
        self._dictation.start()

    def _dictation_partial(self, text: str):
        if self._dictating and self.query_entry.winfo_exists():
            self.query_entry.delete(0, "end")
            self.query_entry.insert(0, text)

    def _dictation_done(self, text: str, error: str):
        self._dictating = False
        self._dictation = None
        if self.voice_assistant is not None:
            self.voice_assistant.resume()
        if self.query_entry.winfo_exists():
            self.query_entry.configure(
                placeholder_text="MehburAI'ye bir soru sorun veya mesaj yazın... (Örn: Albert Einstein kimdir?)")
            self.query_entry.delete(0, "end")
        self._update_mic_button()
        if error:
            messagebox.showwarning("Sesli Sohbet", self._MIC_ERRORS.get(error, "Mikrofon başlatılamadı."),
                                   parent=self)
            return
        if not text:
            self.query_entry.configure(placeholder_text="🎤 Ses algılanamadı — tekrar dene")
            self.after(3500, lambda: self.query_entry.winfo_exists() and self.query_entry.configure(
                placeholder_text="MehburAI'ye bir soru sorun veya mesaj yazın... (Örn: Albert Einstein kimdir?)"))
            return
        self.query_entry.insert(0, text)
        self._on_send_clicked()

    # ── 📞 JARVIS Görüşmesi (telefon butonu) ──

    def _ensure_jarvis(self):
        if self.jarvis is None:
            try:
                from jarvis_overlay import JarvisOverlay
                self.jarvis = JarvisOverlay(self)
            except Exception:
                self.jarvis = None
        return self.jarvis

    def _toggle_jarvis_call(self):
        """📞 — JARVIS tam ekran açılır ve eller serbest görüşme başlar (uyandırma sözcüğü
        gerekmez). Görüşme sürerken tekrar basmak / ESC / ekrana tıklamak / "görüşmeyi bitir"
        demek onu bitirir."""
        if self._call is not None:
            self._call.stop()          # kapanış _on_call_end'de
            return
        if JarvisCall is None or not voice_dependencies_ok():
            messagebox.showwarning(
                "JARVIS Görüşmesi",
                "Eksik kütüphane: " + ", ".join(voice_missing_deps()),
                parent=self,
            )
            return
        if self._dictating or self._is_processing:
            return
        j = self._ensure_jarvis()
        if j is None:
            return

        if self.voice_assistant is not None:
            self.voice_assistant.pause()
        self._call_error = ""
        self._call_camera_on = False    # her görüşme kamerasız başlar (gizlilik) — 📷 ile açılır
        call = JarvisCall(
            on_command=self._call_command,
            on_state=lambda s, t="": self._ui_call(lambda: self._on_call_state(call, s, t)),
            on_end=lambda: self._ui_call(lambda: self._on_call_end(call)),
        )
        self._call = call
        j.on_close = call.stop
        self.call_btn.configure(text_color=Theme.NEON_RED, border_color=Theme.NEON_RED)
        j.show(mode="idle", title="Bağlanıyor…", subtitle="")
        j.set_call_controls(
            True, mic_muted=False, camera_on=False,
            on_mic_toggle=lambda: self._toggle_call_mic(call),
            on_camera_toggle=self._toggle_call_camera,
        )
        call.start()

    def _call_command(self, text: str) -> str:
        """📞 görüşmesindeki komutu işler; kamera soruları ('kafama ne yakışır', 'elimde ne
        var' ...) yalnızca JARVIS ekranındaki 📷 düğmesi açıkken yanıtlanır."""
        if not self._call_camera_on and VisionAssistant is not None and VisionAssistant.detect_intent(text):
            return ("📷 Kamera kapalı efendim. Bu soruyu yanıtlayabilmem için önce JARVIS "
                    "ekranındaki 📷 düğmesine basıp kamerayı açman gerekiyor.")
        return self._voice_command(text)

    def _toggle_call_mic(self, call):
        """🎤/🔇 — 📞 görüşmesinde kendi sesimizi açıp kapatır (görüşmeyi bitirmez)."""
        if call is not self._call:
            return
        muted = not call.is_muted()
        call.set_muted(muted)
        if self.jarvis is not None:
            self.jarvis.set_mic_muted(muted)

    def _toggle_call_camera(self):
        """📷 — 📞 görüşmesinde kamera sorularına izni açıp kapatır."""
        if self._call is None:
            return
        self._call_camera_on = not self._call_camera_on
        if self.jarvis is not None:
            self.jarvis.set_camera_on(self._call_camera_on)

    def _on_call_state(self, call, state: str, text: str = ""):
        j = self.jarvis
        if call is not self._call or j is None:
            return
        try:
            if state == "karsilama":
                j.show(mode="idle", title="Emrinizdeyim efendim", subtitle="")
            elif state == "dinliyor":
                j.show(mode="listen", title="Dinliyorum…", subtitle=None)   # önceki yanıt ekranda kalsın
            elif state == "duyuyor":
                j.set_state(subtitle=f"🎤 {text}")
            elif state == "sessizde":
                j.show(mode="idle", title="🔇 Mikrofon kapalı", subtitle="Açmak için 🎤 düğmesine bas")
            elif state == "islemde":
                j.show(mode="think", title="Düşünüyorum…", subtitle=text)
            elif state == "yanit":
                j.show(mode="idle", title="", subtitle=text)
            elif state == "veda":
                j.show(mode="idle", title="", subtitle=text)
            elif state == "hata":
                self._call_error = text or "mic"
                j.show(mode="error", title="Bir hata oluştu", subtitle="Mikrofona/ses modeline erişilemedi")
        except Exception:
            pass

    def _on_call_end(self, call):
        if call is not self._call:
            return
        self._call = None
        error = getattr(self, "_call_error", "")
        if self.jarvis is not None:
            self.jarvis.on_close = None
            self.jarvis.set_call_controls(False)
            self.jarvis.hide(delay_ms=0 if error else 1500)
        if self.voice_assistant is not None:
            self.voice_assistant.resume()
        if self.call_btn.winfo_exists():
            self.call_btn.configure(text_color=Theme.CYAN_PRIMARY, border_color=Theme.CYAN_DARK)
        if error:
            msg = self._MIC_ERRORS.get(error) or "Görüşme başlatılamadı."
            if error == "deps":
                msg = "Eksik kütüphane: " + ", ".join(voice_missing_deps())
            messagebox.showwarning("JARVIS Görüşmesi", msg, parent=self)

    def _drive_jarvis(self, state: str, text: str = ""):
        """Sesli asistan durumunu JARVIS tam ekran görseline aktarır."""
        if self._call is not None:      # 📞 görüşmesi ekranı kendisi yönetiyor
            return
        if not get_voice_config().get("voice_overlay_enabled", True):
            return
        if self.jarvis is None:
            try:
                from jarvis_overlay import JarvisOverlay
                self.jarvis = JarvisOverlay(self)
            except Exception:
                self.jarvis = None
                return
        j = self.jarvis
        try:
            if state == "uyandi":
                j.show(mode="idle", title="Emrinizdeyim efendim", subtitle="")
            elif state == "komut_dinliyor":
                j.show(mode="listen", title="Dinliyorum…", subtitle="")
            elif state == "islemde":
                j.show(mode="think", title="Düşünüyorum…", subtitle=text)
            elif state == "yanit":
                j.show(mode="idle", title="", subtitle=text)
                j.hide(delay_ms=8000)
            elif state == "mikrofon_hatasi":
                j.show(mode="error", title="Bir hata oluştu", subtitle="Mikrofona erişilemedi")
                j.hide(delay_ms=5000)
            elif state == "model_yok":
                if j.visible:
                    j.set_state(mode="error", title="Bir hata oluştu",
                                subtitle="Ses modeli yüklenemedi")
                    j.hide(delay_ms=5000)
            elif state == "dinliyor":
                if j.visible:
                    j.hide(delay_ms=2500)
            elif state == "kapali":
                j.hide()
        except Exception:
            pass

    def _preview_jarvis(self):
        """Ayarlardaki '👁️ Önizle' — JARVIS ekranını kısa bir demo ile gösterir."""
        if self.jarvis is None:
            try:
                from jarvis_overlay import JarvisOverlay
                self.jarvis = JarvisOverlay(self)
            except Exception:
                return
        seq = [
            (0, "idle", "Emrinizdeyim efendim", ""),
            (2600, "listen", "Dinliyorum…", ""),
            (5200, "think", "Düşünüyorum…", "saat kaç"),
            (7800, "idle", "", "Şu an saat 22:15."),
        ]
        for ms, m, t, s in seq:
            self.after(ms, lambda m=m, t=t, s=s: self.jarvis.show(m, t, s))
        self.after(12500, self.jarvis.hide)

    def _start_voice_async(self):
        """Modeli (gerekiyorsa) indirip sesli asistanı arka planda başlatır."""
        if self.voice_assistant is None:
            return
        self._on_voice_state("model_indiriliyor" if not SpeechToText.model_present() else "dinliyor")

        def worker():
            SpeechToText.ensure_model()
            ok = self.voice_assistant.start()
            if not ok:
                self._ui_call(lambda: self._on_voice_state("model_yok"))
        threading.Thread(target=worker, daemon=True, name="MehburAI-VoiceStart").start()

    def _toggle_voice(self):
        want = bool(self.voice_switch.get())
        if want and not voice_dependencies_ok():
            self.voice_switch.deselect()
            self._on_voice_state("kapali")
            self.voice_status_lbl.configure(
                text="⚠️ Eksik kütüphane: " + ", ".join(voice_missing_deps()),
                text_color=Theme.STATUS_OFFLINE,
            )
            return
        update_voice_config(voice_enabled=want)
        if want:
            self._setup_tray()
            self._start_voice_async()
        else:
            if self.voice_assistant is not None:
                self.voice_assistant.stop()
            self._on_voice_state("kapali")

    def _change_voice(self, choice: str):
        mapping = {"Emel (kadın)": "tr-TR-EmelNeural", "Ahmet (erkek)": "tr-TR-AhmetNeural"}
        update_voice_config(voice_tts_voice=mapping.get(choice, "tr-TR-EmelNeural"))

    def _test_voice(self):
        if TextToSpeech is None:
            return
        threading.Thread(
            target=lambda: TextToSpeech.speak("Emrinizdeyim efendim. Ben MehburAI."),
            daemon=True, name="MehburAI-VoiceTest",
        ).start()

    def _toggle_telegram_voice(self):
        update_voice_config(telegram_voice_enabled=bool(self.tg_voice_switch.get()))

    def _toggle_overlay(self):
        want = bool(self.jarvis_switch.get())
        update_voice_config(voice_overlay_enabled=want)
        if not want and self.jarvis is not None:
            self.jarvis.hide()

    def _remote_toggle_security(self, want: bool) -> str:
        """Bot '/guvenlik ac|kapat' komutu — güvenlik modunu uzaktan değiştirir."""
        if want and not has_security_password():
            return "⚠️ Önce MehburAI arayüzünden bir güvenlik şifresi belirlemelisin."
        if bool(get_security_config().get("security_enabled")) == want:
            return f"🛡️ Güvenlik modu zaten {'açık' if want else 'kapalı'}."
        self.after(0, lambda: self._apply_security_enabled(want))
        return f"🛡️ Güvenlik modu {'açılıyor' if want else 'kapatılıyor'}..."

    def _apply_security_enabled(self, want: bool):
        """Güvenlik modunu programatik olarak aç/kapat (GUI thread'inde çağrılmalı)."""
        update_security_config(security_enabled=want)
        if want:
            self.security_guard.start()
            self._setup_tray()
        else:
            self.security_guard.stop()
        if hasattr(self, "sec_enable_switch"):
            (self.sec_enable_switch.select if want else self.sec_enable_switch.deselect)()
        self._refresh_security_status()

    def _toggle_remote(self):
        """Ayarlardaki '🤖 Telegram'dan uzaktan kontrol' anahtarı."""
        want = bool(self.sec_remote_switch.get())
        if want and not self.telegram_bot.is_configured():
            self.sec_remote_switch.deselect()
            self.sec_status.configure(
                text="⚠️ Önce Telegram Bot Token + Chat ID kaydet.",
                text_color=Theme.STATUS_WARNING,
            )
            return
        update_security_config(telegram_remote_enabled=want)
        if want:
            started = self.telegram_bot.start()
            self._setup_tray()
            self.sec_status.configure(
                text=("✅ Telegram uzaktan kontrol açık — bota /yardim yaz." if started
                      else "⚠️ Bot başlatılamadı (Telegram bilgileri eksik)."),
                text_color=Theme.STATUS_ONLINE if started else Theme.STATUS_WARNING,
            )
        else:
            self.telegram_bot.stop()
            self.sec_status.configure(
                text="Telegram uzaktan kontrol kapatıldı.", text_color=Theme.TEXT_SECONDARY
            )
        self.after(1800, self._refresh_security_status)

    def _save_api_key(self):
        """API anahtarını kaydeder."""
        key = self.api_key_entry.get().strip()
        if key:
            set_api_key(key)
            self.api_status_lbl.configure(
                text="✅ API Anahtarı Başarıyla Kaydedildi!",
                text_color=Theme.STATUS_ONLINE
            )
        else:
            self.api_status_lbl.configure(
                text="⚠️ Lütfen geçerli bir anahtar girin!",
                text_color=Theme.STATUS_WARNING
            )

    def _remove_api_key(self):
        """API anahtarını siler."""
        remove_api_key()
        self.api_key_entry.delete(0, "end")
        self.api_status_lbl.configure(
            text="⚠️ API Anahtarı Silindi",
            text_color=Theme.STATUS_WARNING
        )

    def _test_api_key(self):
        """'API'yi Test Et' — kutudaki anahtarı (boşsa kayıtlıyı) arka planda sınar."""
        key = self.api_key_entry.get().strip() or (get_api_key() or "")
        if not key:
            self.api_test_lbl.configure(text="⚠️ Önce bir API anahtarı gir.", text_color=Theme.STATUS_WARNING)
            return
        self.api_test_btn.configure(state="disabled", text="⏳ Test ediliyor...")
        self.api_test_lbl.configure(text="Gemini'ye bağlanılıyor...", text_color=Theme.TEXT_SECONDARY)

        def work():
            try:
                ok, msg = self.ai.gemini.test_key(key)
            except Exception as e:
                ok, msg = False, f"Test sırasında hata: {type(e).__name__}"
            self._ui_call(lambda: self._show_api_test_result(ok, msg))
        threading.Thread(target=work, daemon=True, name="MehburAI-ApiTest").start()

    def _show_api_test_result(self, ok: bool, msg: str):
        if not self.api_test_btn.winfo_exists():
            return
        self.api_test_btn.configure(state="normal", text="🧪 API'yi Test Et")
        self.api_test_lbl.configure(
            text=("✅ " if ok else "❌ ") + msg,
            text_color=Theme.STATUS_ONLINE if ok else Theme.STATUS_OFFLINE,
        )

    def _manual_network_check(self):
        """'Bağlantıyı Şimdi Test Et' — Cloudflare/Google hedeflerini arka planda dener, sonucu gösterir."""
        self.net_test_btn.configure(state="disabled", text="⏳ Test ediliyor...")
        self.net_status_lbl.configure(text="Bağlantı deneniyor...", text_color=Theme.TEXT_SECONDARY)

        def work():
            try:
                results = self.network.diagnose()
            except Exception:
                results = []
            self._ui_call(lambda: self._show_network_result(results))
        threading.Thread(target=work, daemon=True, name="MehburAI-NetTest").start()

    def _show_network_result(self, results: list):
        if not self.net_test_btn.winfo_exists():
            return
        self.net_test_btn.configure(state="normal", text="🔄 Bağlantıyı Şimdi Test Et")
        online = any(r["ok"] for r in results)
        lines = [
            f"{'✓' if r['ok'] else '✗'} {r['label']} {r['host']}:{r['port']} — "
            + (f"{r['ms']} ms" if r["ok"] else "ulaşılamadı")
            for r in results
        ]
        head = ("🟢 İnternet bağlantısı var." if online else
                "🔴 Hiçbir hedefe ulaşılamadı — Wi-Fi/Ethernet, VPN veya güvenlik duvarını kontrol et.")
        self.net_status_lbl.configure(
            text=head + ("\n" + "\n".join(lines) if lines else ""),
            text_color=Theme.STATUS_ONLINE if online else Theme.STATUS_OFFLINE,
        )
        self._update_badges()

    # ─────────────────────────────────────────
    # Durum & Rozet Güncellemeleri
    # ─────────────────────────────────────────

    def _get_network_badge_text(self) -> str:
        """Ağ durum rozeti metni."""
        return "🟢 ÇEVRİMİÇİ" if self.network.is_online else "🔴 ÇEVRİMDIŞI"

    def _on_network_status_change(self, is_online: bool):
        """Ağ durumu değiştiğinde NetworkMonitor tarafından çağrılır."""
        self.after(0, self._update_badges)

    def _update_badges(self):
        """Tüm başlık rozetlerini günceller."""
        # Ağ rozeti
        is_online = self.network.is_online
        self.network_badge.configure(
            text=self._get_network_badge_text(),
            text_color=Theme.STATUS_ONLINE if is_online else Theme.STATUS_OFFLINE
        )

        # Hafıza rozeti
        count = self.memory.get_memory_count()
        self.memory_badge.configure(text=f"🧠 {count} Bilgi Hafızada")

    def report_callback_exception(self, exc, val, tb):
        """Arayüz geri çağrısındaki hataları data/last_error.log'a yazar (uygulama çökmesin)."""
        import traceback
        try:
            with open(os.path.join(DATA_DIR, "last_error.log"),
                      "a", encoding="utf-8") as f:
                import datetime
                f.write(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] callback exception:\n")
                traceback.print_exception(exc, val, tb, file=f)
        except Exception:
            pass

    # ── Sistem tepsisi (arka planda çalışma) ──

    def _setup_tray(self):
        """Güvenlik modu açıkken pencere kapatılsa bile uygulama tepside çalışmaya devam eder."""
        if self._tray is not None:
            return
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            self._tray = None
            return

        img = None
        try:
            _logo = get_logo_path()
            if _logo:
                img = Image.open(_logo).convert("RGBA")
        except Exception:
            img = None

        if img is None:
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([4, 4, 60, 60], fill=(0, 240, 255, 255))
            d.ellipse([20, 22, 30, 32], fill=(7, 7, 11, 255))
            d.ellipse([34, 22, 44, 32], fill=(7, 7, 11, 255))

        menu = pystray.Menu(
            pystray.MenuItem("MehburAI'yi Aç", lambda *_: self.after(0, self._restore_window), default=True),
            pystray.MenuItem(
                "🛡️ Güvenlik Modu",
                lambda *_: self.after(0, self._tray_toggle_security),
                checked=lambda _i: bool(get_security_config().get("security_enabled")),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Tamamen Çıkış", lambda *_: self.after(0, self._real_quit)),
        )
        self._tray = pystray.Icon("MehburAI", img, "MehburAI — Güvenlik Modu", menu)
        threading.Thread(target=self._tray.run, daemon=True, name="MehburAI-Tray").start()

    def _restore_window(self):
        try:
            self.deiconify()
            self.state("normal")
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _tray_toggle_security(self):
        cur = bool(get_security_config().get("security_enabled"))
        if not cur and not has_security_password():
            self._restore_window()
            self.switch_tab("settings")
            return
        update_security_config(security_enabled=not cur)
        if not cur:
            self.security_guard.start()
        else:
            self.security_guard.stop()
        if hasattr(self, "sec_enable_switch"):
            (self.sec_enable_switch.select if not cur else self.sec_enable_switch.deselect)()
        self._refresh_security_status()

    def _persist_all_settings(self):
        """Kapanmadan önce ayarların diske yazıldığından emin ol (yollar kaybolmasın)."""
        try:
            if hasattr(self, "sec_paths_box"):
                self._save_security_paths()
        except Exception:
            pass
        try:
            if hasattr(self, "sec_tg_token"):
                self._save_telegram()
        except Exception:
            pass

    def _real_quit(self):
        """Uygulamayı tamamen kapatır (tepsi dahil)."""
        self._quitting = True
        self._persist_all_settings()
        self.network.stop()
        try:
            self.learner.stop()
        except Exception:
            pass
        try:
            self.security_guard.stop()
        except Exception:
            pass
        try:
            self.telegram_bot.stop()
        except Exception:
            pass
        try:
            if self._call is not None:
                self._call.stop()
        except Exception:
            pass
        try:
            if self.voice_assistant is not None:
                self.voice_assistant.stop()
        except Exception:
            pass
        try:
            if self.jarvis is not None:
                self.jarvis.destroy()
        except Exception:
            pass
        try:
            self._singleton.release()
        except Exception:
            pass
        if self._tray is not None:
            try:
                self._tray.stop()
            except Exception:
                pass
        self.destroy()

    def _arm_close(self, *_a):
        self._close_armed = True

    def _on_close_request(self):
        """
        WM_DELETE_WINDOW: ilk ~18 sn'deki sahte kapatmaları yut, sonrasında
        uygulamayı KAPATMA — sadece tepsiye gizle.
        """
        if not self._close_armed or self._quitting:
            return
        self._hide_to_tray()

    def _confirm_quit(self):
        """'Çıkış' düğmesi — güvenlik modu açıksa uyar, değilse direkt kapat."""
        if get_security_config().get("security_enabled"):
            dlg = ctk.CTkToplevel(self)
            dlg.title("Çıkış")
            dlg.geometry("420x180")
            dlg.transient(self)
            dlg.attributes("-topmost", True)
            dlg.after(120, dlg.grab_set)
            ctk.CTkLabel(
                dlg, wraplength=380, justify="center",
                text="🛡️ Güvenlik modu açık. Tamamen çıkarsan yetkisiz erişim "
                     "koruması da durur.\n\nNe yapmak istersin?",
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            ).pack(padx=16, pady=(18, 12))
            row = ctk.CTkFrame(dlg, fg_color="transparent")
            row.pack()
            ctk.CTkButton(
                row, text="Tepsiye gizle", width=130, fg_color=Theme.CYAN_PRIMARY,
                text_color=Theme.BG_DARKEST,
                command=lambda: (dlg.destroy(), self._hide_to_tray()),
            ).pack(side="left", padx=6)
            ctk.CTkButton(
                row, text="Tamamen çık", width=130, fg_color="#44111E", text_color="#FF8888",
                command=lambda: (dlg.destroy(), self._real_quit()),
            ).pack(side="left", padx=6)
        else:
            self._real_quit()

    def _hide_to_tray(self):
        """Pencereyi sistem tepsisine gizler — uygulama (ve güvenlik modu) çalışmaya devam eder."""
        self._persist_all_settings()
        self._setup_tray()
        if self._tray is not None:
            self.withdraw()
            if not self._tray_notified:
                self._tray_notified = True
                msg = ("Güvenlik modu arka planda çalışıyor. "
                       if get_security_config().get("security_enabled")
                       else "MehburAI tepside çalışıyor. ")
                try:
                    self._tray.notify(msg + "Açmak için tepsi simgesine çift tıkla.", "MehburAI")
                except Exception:
                    pass
        else:
            # pystray yoksa: güvenlik açıksa gizle, değilse tamamen çık
            if get_security_config().get("security_enabled"):
                self.iconify()
            else:
                self._real_quit()

    # Geriye dönük uyum
    def _on_close(self):
        self._hide_to_tray()


# ─────────────────────────────────────────────
# Başlatma
# ─────────────────────────────────────────────
def launch_gui(start_hidden: bool = False, singleton=None):
    """Masaüstü uygulamasını başlatır."""
    app = MehburApp(start_hidden=start_hidden, singleton=singleton)
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
