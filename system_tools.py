# -*- coding: utf-8 -*-
"""
MehburAI - Bilgisayar & Sistem Araçları (System Tools)
======================================================
MehburAI'nin kullanıcının bilgisayarına erişmesini, sistem bilgilerini
okumasını ve masaüstü uygulamalarını açmasını sağlayan modül.

Yetenekler:
  • Sistem Durumu (RAM, Disk, İşletim Sistemi, Tarih & Saat)
  • Masaüstü Programlarını Açma (Not Defteri, Hesap Makinesi, Tarayıcı vb.)
  • Bilgisayar komutlarını ve sorularını anlama & yanıtlama
"""

import os
import platform
import shutil
import subprocess
import time
from datetime import datetime
from typing import Optional

from memory_engine import clean_text


class SystemTools:
    """Bilgisayar donanım ve işletim sistemi kontrol yöneticisi."""

    @staticmethod
    def get_system_summary() -> str:
        """Bilgisayarın donanım ve durum özetini çıkarır."""
        os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
        arch = platform.architecture()[0]
        processor = platform.processor() or "Bilinmiyor"
        hostname = platform.node()

        # Disk Alanı (C:\ sürücüsü)
        try:
            total, used, free = shutil.disk_usage("C:\\")
            total_gb = total // (2**30)
            used_gb = used // (2**30)
            free_gb = free // (2**30)
            disk_info = f"{total_gb} GB Toplam | {free_gb} GB Boş (%{(free/total)*100:.0f} boş)"
        except Exception:
            disk_info = "Alınamadı"

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        summary = (
            f"💻 **Bilgisayar Sistem Durumu**\n\n"
            f"• **Cihaz Adı:** `{hostname}`\n"
            f"• **İşletim Sistemi:** `{os_info}` ({arch})\n"
            f"• **İşlemci Mimarisi:** `{processor}`\n"
            f"• **C: Diski Durumu:** `{disk_info}`\n"
            f"• **Sistem Zamanı:** `{now_str}`"
        )
        return summary

    @staticmethod
    def get_current_time_date() -> str:
        """Güncel tarih ve saati Türkçe olarak döndürür."""
        now = datetime.now()
        gunler = {
            0: "Pazartesi", 1: "Salı", 2: "Çarşamba",
            3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"
        }
        gun_adi = gunler.get(now.weekday(), "")
        saat_str = now.strftime("%H:%M")
        tarih_str = now.strftime("%d.%m.%Y")

        return f"🕒 Şu an saat **{saat_str}**, tarih **{tarih_str} ({gun_adi})**."

    @staticmethod
    def open_app(app_name: str) -> str:
        """Kullanıcının istediği masaüstü uygulamasını başlatır."""
        app_lower = app_name.lower()

        try:
            if "not defteri" in app_lower or "notepad" in app_lower:
                subprocess.Popen(["notepad.exe"])
                return "📝 Not Defteri başarıyla açıldı!"

            elif "hesap makinesi" in app_lower or "calc" in app_lower:
                subprocess.Popen(["calc.exe"])
                return "🔢 Hesap Makinesi başarıyla açıldı!"

            elif "dosya" in app_lower or "explorer" in app_lower:
                subprocess.Popen(["explorer.exe"])
                return "📁 Dosya Gezgini açıldı!"

            elif "tarayıcı" in app_lower or "tarayici" in app_lower or "chrome" in app_lower or "edge" in app_lower:
                os.system("start https://www.google.com")
                return "🌐 İnternet tarayıcınız açıldı!"

            elif "görev yöneticisi" in app_lower or "taskmgr" in app_lower:
                subprocess.Popen(["taskmgr.exe"])
                return "📊 Görev Yöneticisi açıldı!"

            else:
                return f"⚠️ '{app_name}' uygulaması doğrudan tanınamadı. Not Defteri, Hesap Makinesi, Dosya Gezgini veya Tarayıcı açmayı deneyebilirsiniz."

        except Exception as e:
            return f"Uygulama açılırken hata oluştu: {e}"

    @classmethod
    def handle_system_query(cls, query: str) -> Optional[str]:
        """
        Kullanıcı girdisinin bilgisayar/sistem komutu olup olmadığını kontrol eder.
        Eğer bir sistem isteğiyse yanıt üretir, değilse None döner.
        """
        cleaned = clean_text(query)

        # 1. Saat / Tarih soruları
        if any(w in cleaned for w in ["saat kaç", "saat kac", "tarih ne", "tarih nedir", "bugün günlerden ne", "bugun ayin kaci"]):
            return cls.get_current_time_date()

        # 2. Sistem / Bilgisayar Durumu
        if any(w in cleaned for w in [
            "sistem bilgisi", "bilgisayarımın durumu", "bilgisayarimin durumu",
            "bilgisayar özellikleri", "bilgisayar ozellikleri", "sistem durumu",
            "disk alanı", "disk alani", "bilgisayar hakkında bilgi"
        ]):
            return cls.get_system_summary()

        # 3. Uygulama Açma Komutları
        if "aç" in cleaned or "ac" in cleaned or "başlat" in cleaned or "calistir" in cleaned or "çalıştır" in cleaned:
            if any(app in cleaned for app in [
                "not defteri", "notepad", "hesap makinesi", "hesap makinasi",
                "calc", "dosya gezgini", "explorer", "tarayıcı", "tarayici",
                "tarayıcıyı", "tarayiciyi", "görev yöneticisi"
            ]):
                return cls.open_app(cleaned)

        return None
