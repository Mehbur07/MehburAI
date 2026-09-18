# -*- coding: utf-8 -*-
"""MehburAI.Setup.exe — MehburAI'yi %APPDATA%\\MehburAI altına kurar."""

import os
import subprocess
import sys
import threading
import tkinter as tk
import zipfile
from tkinter import ttk

APP_NAME = "MehburAI"
EXE_NAME = "MehburAI.exe"
INSTALL_DIR = os.path.join(os.environ["APPDATA"], APP_NAME)
NO_WINDOW = 0x08000000
_SYS32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
POWERSHELL = os.path.join(_SYS32, "WindowsPowerShell", "v1.0", "powershell.exe")
TASKKILL = os.path.join(_SYS32, "taskkill.exe")


def payload_path() -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "payload.zip")


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


def install(on_progress) -> None:
    stop_running_app()
    os.makedirs(INSTALL_DIR, exist_ok=True)
    with zipfile.ZipFile(payload_path()) as zf:
        members = zf.infolist()
        total = len(members)
        for i, m in enumerate(members, 1):
            dest = os.path.join(INSTALL_DIR, m.filename)
            # Kullanıcı verisi (ayarlar, hafıza, modeller) asla ezilmez
            if m.filename.replace("\\", "/").startswith("data/") and os.path.exists(dest):
                continue
            zf.extract(m, INSTALL_DIR)
            on_progress(i / total)
    create_desktop_shortcut()


class SetupWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MehburAI Kurulum")
        self.geometry("420x170")
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
                               fg="#cfd8dc", bg="#0a0e14")
        self.status.pack()
        self.bar = ttk.Progressbar(self, length=340, maximum=1.0)
        self.bar.pack(pady=16)
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            install(lambda f: self.after(0, self.bar.configure, {"value": f}))
            self.after(0, self._done)
        except Exception as e:
            self.after(0, lambda: self.status.configure(text=f"Hata: {e}", fg="#ff5252"))

    def _done(self):
        self.status.configure(text="Kurulum tamamlandı — masaüstüne kısayol eklendi, MehburAI başlatılıyor…")
        exe = os.path.join(INSTALL_DIR, EXE_NAME)
        subprocess.Popen([exe], cwd=INSTALL_DIR, creationflags=NO_WINDOW)
        self.after(1500, self.destroy)


if __name__ == "__main__":
    SetupWindow().mainloop()
