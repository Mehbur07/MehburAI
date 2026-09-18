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

# Proje kök dizinini Python yoluna ekle (yalnızca geliştirme ortamında gerekli;
# .exe'ye paketlenmişse PyInstaller modülleri zaten kendisi bulur)
if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _selftest() -> None:
    """`MehburAI.exe --selftest` — bağımlılıkları / ses modelini yükleyip data/selftest.txt'ye yazar."""
    import traceback
    lines = [f"frozen={getattr(sys, 'frozen', False)}", f"python={sys.version.split()[0]}"]

    def step(name, fn):
        try:
            lines.append(f"{name}: {fn()}")
        except BaseException:
            lines.append(f"{name}: HATA\n{traceback.format_exc()}")

    def _import(mod):
        __import__(mod)
        return "ok"

    for mod in ("numpy", "sounddevice", "soundfile", "vosk", "edge_tts", "customtkinter",
                "PIL", "cv2", "pystray", "requests"):
        step(f"import {mod}", lambda m=mod: _import(m))

    def _voice():
        import voice_engine as ve
        return f"eksik={ve.missing_dependencies()} model_var={ve.SpeechToText.model_present()}"

    def _model():
        import voice_engine as ve
        return "yüklendi" if ve.SpeechToText.get_model() is not None else "YÜKLENEMEDİ"

    def _mics():
        import sounddevice as sd
        return [d["name"] for d in sd.query_devices() if d["max_input_channels"] > 0][:6]

    step("voice_engine", _voice)
    step("vosk modeli", _model)
    step("mikrofonlar", _mics)
    from config import DATA_DIR
    with open(os.path.join(DATA_DIR, "selftest.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    """MehburAI uygulamasını başlatır."""
    if "--selftest" in sys.argv:
        _selftest()
        return
    print()
    print("  +============================================+")
    print("  |          [*]  M E H B U R A I  [*]         |")
    print("  |    Cevrimici & Cevrimdisi Akilli Asistan    |")
    print("  +============================================+")
    print("  [Baslatma] Neon Cyan & Siyah Masaustu Arayuzu yukleniyor...")
    print()

    # Tek örnek: zaten çalışıyorsa mevcut pencereyi öne getirip çık
    from background import SingleInstance
    singleton = SingleInstance()
    if not singleton.acquire():
        print("  MehburAI zaten çalışıyor — mevcut pencere öne getirildi.")
        return

    start_hidden = "--tray" in sys.argv
    from gui_app import launch_gui
    launch_gui(start_hidden=start_hidden, singleton=singleton)


def _log_crash(exc: BaseException) -> None:
    """Beklenmeyen hatayı data/last_error.log dosyasına yazar (konsolsuz başlatmada bile görülsün)."""
    import traceback
    try:
        # .exe'ye paketlenmişse (PyInstaller) günlük .exe'nin yanına, geliştirme
        # ortamında bu betiğin kendi klasörüne yazılır.
        base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
            else os.path.dirname(os.path.abspath(__file__))
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
