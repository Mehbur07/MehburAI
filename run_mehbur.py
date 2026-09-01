# -*- coding: utf-8 -*-
"""
MehburAI - Ana Başlatıcı
========================
Uygulamayı başlatan giriş noktası.
"""

import sys
import os
import io

# Windows konsol encoding sorununu coz
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Proje kök dizinini Python yoluna ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """MehburAI uygulamasını başlatır."""
    print()
    print("  +============================================+")
    print("  |          [*]  M E H B U R A I  [*]         |")
    print("  |    Cevrimici & Cevrimdisi Akilli Asistan    |")
    print("  +============================================+")
    print("  [Baslatma] Neon Cyan & Siyah Masaustu Arayuzu yukleniyor...")
    print()

    from gui_app import launch_gui
    launch_gui()


if __name__ == "__main__":
    main()
