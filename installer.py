# -*- coding: utf-8 -*-
"""MehburAI.Setup.exe — MehburAI'yi %APPDATA%\\MehburAI altına kurar.

Çevrimiçi kurucu: küçük bir .exe'dir; çalışınca uygulamanın tüm dosyalarını
(`MehburAI-payload.zip`) GitHub Releases'ten indirip kurar. (Derlemeye bir
payload.zip gömülmüşse — çevrimdışı sürüm — indirmeden onu kullanır.)
"""

import os
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.request
import zipfile
from tkinter import ttk

APP_NAME = "MehburAI"
EXE_NAME = "MehburAI.exe"
INSTALL_DIR = os.path.join(os.environ["APPDATA"], APP_NAME)
NO_WINDOW = 0x08000000
_SYS32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
POWERSHELL = os.path.join(_SYS32, "WindowsPowerShell", "v1.0", "powershell.exe")
TASKKILL = os.path.join(_SYS32, "taskkill.exe")
GITHUB_REPO = "Mehbur07/MehburAI"   # config.GITHUB_REPO ile aynı olmalı (testte doğrulanır)
PAYLOAD_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/MehburAI-payload.zip"


def payload_path() -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "payload.zip")


def download_payload(dest: str, on_progress) -> None:
    """Uygulama paketini GitHub'dan `dest` dosyasına indirir. on_progress(indirilen_bayt, toplam_bayt)."""
    req = urllib.request.Request(PAYLOAD_URL, headers={"User-Agent": "MehburAI-Setup"})
    got = 0
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            on_progress(got, total)
    if total and got != total:
        raise IOError("İndirme yarım kaldı")
    if not zipfile.is_zipfile(dest):
        raise IOError("İndirilen dosya geçerli bir paket değil")


def stop_running_app() -> None:
    subprocess.run([TASKKILL, "/F", "/IM", EXE_NAME],
                   capture_output=True, creationflags=NO_WINDOW)


def create_desktop_shortcut() -> bool:
    """Masaüstüne (OneDrive'a yönlendirilmiş olsa bile gerçek Masaüstü klasörüne) MehburAI kısayolu koyar."""
    exe = os.path.join(INSTALL_DIR, EXE_NAME)
    icon = os.path.join(INSTALL_DIR, "assets", "logo.ico")
    q = lambda s: s.replace("'", "''")  # noqa: E731
    ps = (
        "$d=[Environment]::GetFolderPath('Desktop');"
        "$W=New-Object -ComObject WScript.Shell;"
        "$S=$W.CreateShortcut((Join-Path $d 'MehburAI.lnk'));"
        f"$S.TargetPath='{q(exe)}';"
        f"$S.WorkingDirectory='{q(INSTALL_DIR)}';"
        f"$S.IconLocation='{q(icon)}';"
        "$S.Description='MehburAI';"
        "$S.Save()"
    )
    try:
        subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", ps],
                       capture_output=True, timeout=30, creationflags=NO_WINDOW)
        return True
    except Exception:
        return False


def is_update() -> bool:
    return os.path.isfile(os.path.join(INSTALL_DIR, EXE_NAME))


# Kurulum penceresinde dosya adı yerine "ne işe yaradığı" gösterilir. Her dosya yolunun
# başına göre bir özelliğe eşlenir (ilk eşleşen kazanır); eşleşmeyenler "temel sistem".
BASE_FEATURE = "Temel sistem dosyaları (uygulamanın çalışması için)"
FEATURES = [
    ("Yapay zeka beyni (sohbet, internetten araştırma, yalan haber süzgeci)",
     ("mehburai.exe",)),
    ("Sesli komut (\"Hey Mehbur\" ve konuşarak yazma)", ("vosk/", "data/models/")),
    ("Mikrofon ve ses çalma", ("_sounddevice_data/", "_soundfile_data/")),
    ("Kamera ve görsel anlama", ("cv2/",)),
    ("Resim çizme, fotoğraf düzenleme ve ekran görüntüsü", ("pil/",)),
    ("Arayüz ve renk değiştirme", ("customtkinter/", "_tkinter", "tcl", "_tcl_data/", "_tk_data/",
                                   "libtommath")),
    ("Logo ve simgeler", ("assets/",)),
    ("Ses ve görüntü işleme hesaplamaları", ("numpy",)),
    ("Hafıza (öğrenilen bilgiler ve sohbet geçmişi)", ("sqlite3.dll", "_sqlite3")),
    ("Güvenli internet bağlantısı", ("cryptography", "libssl", "libcrypto", "_ssl", "certifi/", "_hashlib")),
    ("İnternet ve Telegram bağlantısı", ("aiohttp", "yarl", "multidict", "frozenlist", "propcache",
                                         "charset_normalizer", "aiosignal", "_socket", "_asyncio",
                                         "_overlapped", "select.pyd")),
    ("Bilgisayar kontrolü (sistem bilgisi, program açma)", ("psutil", "_wmi")),
]


def feature_of(path: str) -> str:
    p = path.replace("\\", "/").lower()
    for label, prefixes in FEATURES:
        if p.startswith(prefixes):
            return label
    return BASE_FEATURE


class FeatureTracker:
    """Bir özelliğin TÜM dosyaları kurulunca (yalnızca bir kez) o özelliğin adını döndürür."""

    def __init__(self, names):
        self._left = {}
        for n in names:
            f = feature_of(n)
            self._left[f] = self._left.get(f, 0) + 1

    def mark(self, name: str):
        f = feature_of(name)
        if f not in self._left:
            return None
        self._left[f] -= 1
        if self._left[f] == 0:
            del self._left[f]
            return f
        return None


def extract_payload(zip_path: str, install_dir: str, on_progress, on_feature=None) -> None:
    """Paketi install_dir'e açar; kullanıcı verisi (data/) varsa ezilmez.
    on_feature(özellik_adı): bir özelliğin dosyalarının hepsi yerine konunca çağrılır."""
    root = os.path.abspath(install_dir)
    with zipfile.ZipFile(zip_path) as zf:
        members = zf.infolist()
        total = len(members)
        tracker = FeatureTracker(m.filename for m in members)
        for i, m in enumerate(members, 1):
            dest = os.path.abspath(os.path.join(root, m.filename))
            safe = dest.startswith(root + os.sep)          # zip-slip koruması
            # Kullanıcı verisi (ayarlar, hafıza, modeller) asla ezilmez
            keep_user_data = m.filename.replace("\\", "/").startswith("data/") and os.path.exists(dest)
            if safe and not keep_user_data:
                zf.extract(m, root)
            done = tracker.mark(m.filename)
            if done and on_feature:
                on_feature(done)
            on_progress(i / total)


EXTRACT_ALLOWANCE = 5    # sn — indirme bittikten sonra dosyaları açmanın kabaca süresi (ilk tahmin için)


def remaining_seconds(elapsed: float, fraction: float, min_elapsed: float = 1.5):
    """Şimdiye kadarki hıza göre kalan süre (sn); yeterli veri yoksa None."""
    if fraction <= 0 or elapsed < min_elapsed:
        return None
    return max(0.0, elapsed * (1 - fraction) / fraction)


def format_eta(seconds) -> str:
    if seconds is None:
        return "hesaplanıyor…"
    s = max(1, int(round(seconds)))
    if s < 60:
        return f"~{s} sn"
    return f"~{s // 60} dk {s % 60} sn"


def install(on_status, on_progress, on_feature=None) -> None:
    """on_status(metin) durum yazısı; on_progress(0..1) çubuk; on_feature(ad) kurulan özellik."""
    bundled = payload_path()
    tmp = None
    try:
        if os.path.isfile(bundled):
            zip_path = bundled
        else:
            tmp = os.path.join(tempfile.gettempdir(), "MehburAI-payload.zip")
            on_status("İndiriliyor… (uygulama dosyaları GitHub'dan alınıyor)")
            t0 = time.monotonic()

            def dl(got, total):
                mb = got / 1048576
                if total:
                    # bağlantı ilk saniyelerde hızlandığı için 4 sn dolmadan tahmin verme
                    left = remaining_seconds(time.monotonic() - t0, got / total, min_elapsed=4.0)
                    if left is not None:
                        left += EXTRACT_ALLOWANCE      # indirme + dosyaları açma
                    on_status(f"İndiriliyor… {mb:.0f} / {total / 1048576:.0f} MB"
                              f"  •  tahmini kalan süre: {format_eta(left)}")
                else:
                    on_status(f"İndiriliyor… {mb:.0f} MB")
                on_progress(0.7 * got / total if total else 0.0)

            download_payload(tmp, dl)
            zip_path = tmp
        on_status("Kuruluyor…")
        stop_running_app()
        os.makedirs(INSTALL_DIR, exist_ok=True)
        base = 0.7 if tmp else 0.0
        t1 = time.monotonic()

        def ex(f):
            left = remaining_seconds(time.monotonic() - t1, f)
            on_status(f"Kuruluyor… %{f * 100:.0f}"
                      + (f"  •  tahmini kalan süre: {format_eta(left)}" if left is not None else ""))
            on_progress(base + (1 - base) * f)

        extract_payload(zip_path, INSTALL_DIR, ex, on_feature)
        create_desktop_shortcut()
    finally:
        if tmp and os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


class SetupWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MehburAI Kurulum")
        self.geometry("520x420")
        self.resizable(False, False)
        self.configure(bg="#0a0e14")
        icon = os.path.join(getattr(sys, "_MEIPASS", ""), "logo.ico")
        if os.path.isfile(icon):
            try:
                self.iconbitmap(icon)
            except Exception:
                pass
        tk.Label(self, text="MehburAI", font=("Segoe UI", 18, "bold"),
                 fg="#00e5ff", bg="#0a0e14").pack(pady=(18, 4))
        self.status = tk.Label(self, text=("Güncelleniyor… (ayarların ve verilerin korunur)" if is_update()
                                           else "Kuruluyor…"), font=("Segoe UI", 10),
                               fg="#cfd8dc", bg="#0a0e14", wraplength=410, justify="center")
        self.status.pack()
        self.bar = ttk.Progressbar(self, length=420, maximum=1.0)
        self.bar.pack(pady=(14, 8))

        self._verb = "güncellendi" if is_update() else "indirildi"
        self.features = tk.Text(self, height=12, width=62, font=("Segoe UI", 9), bg="#111823",
                                fg="#9be7a0", relief="flat", highlightthickness=0, wrap="word",
                                padx=8, pady=6, state="disabled")
        self.features.pack(padx=16, pady=(0, 12), fill="both", expand=True)
        threading.Thread(target=self._run, daemon=True).start()

    def _add_feature(self, name: str):
        self.features.configure(state="normal")
        self.features.insert("end", f"✅ {name} {self._verb}\n")
        self.features.see("end")
        self.features.configure(state="disabled")

    def _run(self):
        try:
            install(lambda t: self.after(0, lambda: self.status.configure(text=t)),
                    lambda f: self.after(0, lambda: self.bar.configure(value=f)),
                    lambda name: self.after(0, lambda: self._add_feature(name)))
            self.after(0, self._done)
        except Exception as e:
            self.after(0, lambda: self.status.configure(
                text=f"Hata: {e}" + chr(10) + "İnternet bağlantını kontrol edip kurucuyu tekrar çalıştır.",
                fg="#ff5252"))

    def _done(self):
        self.status.configure(text="Kurulum tamamlandı — masaüstüne kısayol eklendi, MehburAI başlatılıyor…")
        exe = os.path.join(INSTALL_DIR, EXE_NAME)
        subprocess.Popen([exe], cwd=INSTALL_DIR, creationflags=NO_WINDOW)
        self.after(4000, self.destroy)     # listenin okunabilmesi için biraz açık kalır


if __name__ == "__main__":
    SetupWindow().mainloop()
