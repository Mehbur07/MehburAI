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

import os
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from ai_engine import AIEngine
from config import (
    Theme,
    get_api_key,
    get_security_config,
    has_security_password,
    load_config,
    remove_api_key,
    set_api_key,
    set_security_password,
    update_security_config,
    verify_security_password,
)
from memory_engine import MemoryEngine
from network_manager import NetworkMonitor
from security_guard import SecurityGuard, TelegramNotifier, trigger_intruder_alert


# CustomTkinter Genel Tema Ayarları
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MehburApp(ctk.CTk):
    """MehburAI Ana Masaüstü Penceresi."""

    def __init__(self):
        super().__init__()

        # Pencere Başlığı ve Boyutları
        self.title("MehburAI — Hibrit Akıllı Asistan")
        self.geometry(f"{Theme.WINDOW_WIDTH}x{Theme.WINDOW_HEIGHT}")
        self.minsize(Theme.WINDOW_MIN_WIDTH, Theme.WINDOW_MIN_HEIGHT)
        self.configure(fg_color=Theme.BG_DARK)

        # Çekirdek Servisler
        self.memory = MemoryEngine()
        self.network = NetworkMonitor(on_status_change=self._on_network_status_change)
        self.ai = AIEngine(memory_engine=self.memory, network_monitor=self.network)

        # Durum Değişkenleri
        self._is_processing = False
        self._security_dialogs = {}   # path -> Toplevel (aynı yol için tek ekran)
        self._security_queue = queue.Queue()   # guard thread -> UI thread köprüsü

        # 🛡️ Güvenlik Modu izleyicisi
        self.security_guard = SecurityGuard(on_access=self._security_queue.put)

        # UI Bileşenlerini İnşa Et
        self._build_ui()

        # Ağ İzleyiciyi Başlat
        self.network.start()

        # Güvenlik Modu etkinse izlemeyi başlat
        if get_security_config().get("security_enabled"):
            self.security_guard.start()

        # Güvenlik kuyruğunu düzenli aralıkla ana thread'de kontrol et
        self.after(700, self._poll_security_queue)

        # İlk Başlangıç Mesajı
        self._send_welcome_message()

        # Pencere Kapanış Olayı
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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

        # Varsayılan olarak Sohbet panelini göster
        self.switch_tab("chat")

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

        title_lbl = ctk.CTkLabel(
            logo_frame,
            text="⚡ MEHBUR AI",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=20, weight="bold"),
            text_color=Theme.CYAN_PRIMARY,
        )
        title_lbl.pack(side="left", padx=(0, 8))

        subtitle_lbl = ctk.CTkLabel(
            logo_frame,
            text="v1.0",
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
        """Sohbet mesajlaşma alanı ve giriş kutusu."""
        self.panel_chat.grid_rowconfigure(0, weight=1)
        self.panel_chat.grid_columnconfigure(0, weight=1)

        # Mesaj Geçmişi (Scrollable Frame)
        self.chat_history_box = ctk.CTkScrollableFrame(
            self.panel_chat,
            fg_color=Theme.BG_DARKEST,
            corner_radius=10,
            border_width=1,
            border_color=Theme.BORDER_DEFAULT,
        )
        self.chat_history_box.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 10))

        # Alt Giriş Paneli
        input_container = ctk.CTkFrame(self.panel_chat, fg_color="transparent")
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
        self.send_btn.grid(row=0, column=1, sticky="e")

        # Hızlı Yardım & Ayarlar Butonları
        quick_frame = ctk.CTkFrame(self.panel_chat, fg_color="transparent", height=30)
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
            text="🗑️ Sohbeti Temizle",
            font=ctk.CTkFont(size=11),
            fg_color=Theme.BG_CARD,
            text_color=Theme.TEXT_SECONDARY,
            hover_color=Theme.BG_CARD_HOVER,
            height=26,
            command=self._clear_chat_display,
        )
        btn_clear_chat.pack(side="right")

    def _insert_quick_query(self, text: str):
        """Hızlı örnek soruyu giriş kutusuna yazar."""
        self.query_entry.delete(0, "end")
        self.query_entry.insert(0, text)
        self.query_entry.focus()

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
            is_online=self.network.is_online
        )

    def _on_send_clicked(self):
        """Kullanıcı gönder butonuna bastığında tetiklenir."""
        query = self.query_entry.get().strip()
        if not query or self._is_processing:
            return

        # Giriş kutusunu temizle ve kilitle
        self.query_entry.delete(0, "end")
        self._set_processing(True)

        # Kullanıcı mesajını sohbet balonuna ekle
        self._add_message_bubble(role="user", message=query, is_online=self.network.is_online)

        # Düşünülüyor / Yükleniyor balonunu ekle
        self._add_loading_bubble()

        # Yanıt üretimini arka plan thread'inde çalıştır (UI donmasın)
        threading.Thread(
            target=self._process_query_async,
            args=(query,),
            daemon=True,
            name="MehburAI-QueryWorker"
        ).start()

    def _process_query_async(self, query: str):
        """Arka planda AI Engine ile soruyu işler."""
        try:
            result = self.ai.process_query(query)
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

        # Mesajı ekle
        self._add_message_bubble(
            role="mehbur",
            message=answer,
            source=source_label,
            is_online=is_online
        )

        # Sayaçları ve hafıza listesini güncelle
        self._update_badges()
        self._refresh_memory_list()

        # İşlem kilidini kaldır
        self._set_processing(False)

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

    def _add_message_bubble(self, role: str, message: str, source: Optional[str] = None, is_online: bool = True):
        """Sohbet alanına şık bir mesaj kutucuğu ekler."""
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

            msg_lbl = ctk.CTkLabel(
                bubble,
                text=message,
                font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13),
                text_color=Theme.TEXT_PRIMARY,
                wraplength=520,
                justify="left",
            )
            msg_lbl.pack(anchor="w", padx=12, pady=(2, 10))

        # Otomatik en aşağı kaydır
        self.after(50, lambda: self.chat_history_box._parent_canvas.yview_moveto(1.0))

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
        """Sohbet alanını temizler."""
        for widget in self.chat_history_box.winfo_children():
            widget.destroy()
        self._send_welcome_message()

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
        self.api_status_lbl.pack(anchor="w", padx=16, pady=(0, 14))

        # 2. 🛡️ Güvenlik Modu Kartı
        self._build_security_card(self.settings_scroll)

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
            text="🌐 Ağ & Bağlantı Kontrolü (Cloudflare 1.1.1.1)",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY,
        )
        net_title.pack(anchor="w", padx=16, pady=(14, 6))

        btn_test_net = ctk.CTkButton(
            net_card,
            text="🔄 Bağlantıyı Şimdi Test Et",
            font=ctk.CTkFont(size=12),
            fg_color=Theme.BG_CARD_HOVER,
            hover_color=Theme.CYAN_DARK,
            height=34,
            command=self._manual_network_check,
        )
        btn_test_net.pack(anchor="w", padx=16, pady=(0, 14))

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
                "Korunan bir klasör Dosya Gezgini'nde açıldığında veya korunan bir program "
                "çalıştırıldığında MehburAI şifre sorar. Şifre yanlış girilir ya da ekran "
                "kapatılırsa: web kameradan fotoğraf çekilir, Telegram'dan size gönderilir ve "
                "kişiye \"fotoğrafınız çekildi ve cihaz sahibine iletildi\" uyarısı gösterilir."
            ),
        ).pack(anchor="w", padx=16, pady=(0, 10))

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

        self.sec_tg_token = ctk.CTkEntry(
            card, placeholder_text="Bot Token (123456:ABC-DEF...)", show="•", height=36,
            fg_color=Theme.BG_INPUT, border_color=Theme.CYAN_DARK,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12), corner_radius=8,
        )
        self.sec_tg_token.pack(fill="x", padx=16, pady=(0, 6))
        if cfg.get("telegram_bot_token"):
            self.sec_tg_token.insert(0, cfg["telegram_bot_token"])

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
        else:
            self.security_guard.stop()
        self._refresh_security_status()

    def _save_security_paths(self):
        raw = self.sec_paths_box.get("1.0", "end")
        paths = [ln.strip().strip('"') for ln in raw.splitlines() if ln.strip()]
        update_security_config(security_watch_paths=paths)
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
        update_security_config(
            telegram_bot_token=self.sec_tg_token.get().strip(),
            telegram_chat_id=self.sec_tg_chat.get().strip(),
        )
        self.sec_status.configure(text="✅ Telegram bilgileri kaydedildi.", text_color=Theme.STATUS_ONLINE)
        self.after(1800, self._refresh_security_status)

    def _autodetect_chat_id(self):
        token = self.sec_tg_token.get().strip()
        if not token:
            self.sec_status.configure(text="⚠️ Önce Bot Token gir.", text_color=Theme.STATUS_WARNING)
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
                path = self._security_queue.get_nowait()
                self._show_security_challenge(path)
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

    def _show_security_challenge(self, path: str):
        if path in self._security_dialogs and self._security_dialogs[path].winfo_exists():
            self._security_dialogs[path].lift()
            return
        if not has_security_password():
            # Şifre yoksa doğrulama yapılamaz — izleyiciyi geri çevir
            self.security_guard.mark_resolved(path)
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("🔒 MehburAI Güvenlik Modu")
        dlg.geometry("460x300")
        dlg.resizable(False, False)
        dlg.configure(fg_color=Theme.BG_DARK)
        dlg.transient(self)
        dlg.attributes("-topmost", True)
        try:
            dlg.after(120, dlg.grab_set)
        except Exception:
            pass
        self._security_dialogs[path] = dlg
        state = {"alerted": False}

        ctk.CTkLabel(
            dlg, text="🔒 Bu konum korumalı", text_color=Theme.STATUS_OFFLINE,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=18, weight="bold"),
        ).pack(pady=(22, 4))
        ctk.CTkLabel(
            dlg, text=os.path.basename(path.rstrip("\\/")) or path, text_color=Theme.TEXT_SECONDARY,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
        ).pack(pady=(0, 12))

        entry = ctk.CTkEntry(
            dlg, placeholder_text="Güvenlik şifresini girin", show="•", width=320, height=40,
            fg_color=Theme.BG_INPUT, border_color=Theme.CYAN_DARK,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13),
        )
        entry.pack(pady=(0, 10))
        entry.after(250, entry.focus_force)

        info = ctk.CTkLabel(
            dlg, text="", justify="center", wraplength=400,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
        )
        info.pack(pady=(2, 8))

        def do_verify():
            if verify_security_password(entry.get()):
                self.security_guard.mark_passed(path)
                self._close_security_dialog(path)
            else:
                info.configure(
                    text="⚠️ Hatalı şifre. Fotoğrafınız çekildi ve cihaz sahibine iletildi.",
                    text_color=Theme.STATUS_OFFLINE,
                )
                if not state["alerted"]:
                    state["alerted"] = True
                    self._fire_intruder_alert("Yanlış şifre girildi")

        def on_x():
            info.configure(
                text="⚠️ Doğrulama yapılmadı. Fotoğrafınız çekildi ve cihaz sahibine iletildi.",
                text_color=Theme.STATUS_OFFLINE,
            )
            if not state["alerted"]:
                state["alerted"] = True
                self._fire_intruder_alert("Şifre ekranı kapatıldı")
            self.after(2500, lambda: self._close_security_dialog(path))

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
        self.security_guard.mark_resolved(path)

    def _ui_call(self, fn):
        """Arka plan thread'inden UI'ı güvenle günceller (pencere kapandıysa yut)."""
        try:
            if self.winfo_exists():
                self.after(0, fn)
        except Exception:
            pass

    def _fire_intruder_alert(self, reason: str):
        """Kamera + Telegram işini arka planda yapar (UI donmasın)."""
        def worker():
            result = trigger_intruder_alert(reason)

            def show():
                if hasattr(self, "sec_status") and self.sec_status.winfo_exists():
                    self.sec_status.configure(
                        text=f"🚨 Uyarı gönderildi: {result['detail']}",
                        text_color=Theme.STATUS_OFFLINE,
                    )
            self._ui_call(show)
        threading.Thread(target=worker, daemon=True, name="MehburAI-IntruderAlert").start()

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

    def _manual_network_check(self):
        """Manuel olarak ağ kontrolü yapar ve rozeti günceller."""
        is_online = self.network.check_now()
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

    def _on_close(self):
        """Pencere kapatıldığında servisleri güvenle sonlandırır."""
        self.network.stop()
        try:
            self.security_guard.stop()
        except Exception:
            pass
        self.destroy()


# ─────────────────────────────────────────────
# Başlatma
# ─────────────────────────────────────────────
def launch_gui():
    """Masaüstü uygulamasını başlatır."""
    app = MehburApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
