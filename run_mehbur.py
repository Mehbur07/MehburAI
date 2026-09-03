# -*- coding: utf-8 -*-
"""
MehburAI - Ana Başlatıcı
========================
Uygulamayı başlatan giriş noktası.
"""

import sys
import os
import io

# pythonw.exe ile (konsolsuz) başlatıldığında sys.stdout / sys.stderr None olur.
# Aksi halde aşağıdaki satırlar ve modüllerdeki print() çağrıları çökertir.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Windows konsol encoding sorununu coz (yalnızca gerçek bir konsol varsa)
try:
    if getattr(sys.stdout, "buffer", None) is not None and sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

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


def _log_crash(exc: BaseException) -> None:
    """Beklenmeyen hatayı data/last_error.log dosyasına yazar (konsolsuz başlatmada bile görülsün)."""
    import traceback
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(base, "data")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "last_error.log"), "w", encoding="utf-8") as f:
            import datetime
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except BaseException as _exc:  # noqa: BLE001 — başlatma hatasını kaydet ve yeniden fırlat
        _log_crash(_exc)
        raise
