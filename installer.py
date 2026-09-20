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


def extract_payload(zip_path: str, install_dir: str, on_progress) -> None:
    """Paketi install_dir'e açar; kullanıcı verisi (data/) varsa ezilmez."""
    root = os.path.abspath(install_dir)
    with zipfile.ZipFile(zip_path) as zf:
        members = zf.infolist()
        total = len(members)
        for i, m in enumerate(members, 1):
            dest = os.path.abspath(os.path.join(root, m.filename))
            if not dest.startswith(root + os.sep):
                continue            # zip-slip koruması
            # Kullanıcı verisi (ayarlar, hafıza, modeller) asla ezilmez
            if m.filename.replace("\\", "/").startswith("data/") and os.path.exists(dest):
                continue
            zf.extract(m, root)
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


def install(on_status, on_progress) -> None:
    """on_status(metin) durum yazısı; on_progress(0..1) çubuk."""
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

        extract_payload(zip_path, INSTALL_DIR, ex)
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
        self.geometry("440x190")
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
        self.bar = ttk.Progressbar(self, length=340, maximum=1.0)
        self.bar.pack(pady=16)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            install(lambda t: self.after(0, lambda: self.status.configure(text=t)),
                    lambda f: self.after(0, lambda: self.bar.configure(value=f)))
            self.after(0, self._done)
        except Exception as e:
            self.after(0, lambda: self.status.configure(
                text=f"Hata: {e}" + chr(10) + "İnternet bağlantını kontrol edip kurucuyu tekrar çalıştır.",
                fg="#ff5252"))

    def _done(self):
        self.status.configure(text="Kurulum tamamlandı — masaüstüne kısayol eklendi, MehburAI başlatılıyor…")
        exe = os.path.join(INSTALL_DIR, EXE_NAME)
        subprocess.Popen([exe], cwd=INSTALL_DIR, creationflags=NO_WINDOW)
        self.after(1500, self.destroy)


if __name__ == "__main__":
    SetupWindow().mainloop()
