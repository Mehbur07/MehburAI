# -*- coding: utf-8 -*-
"""
MehburAI - Arka Plan / Otomatik Başlatma Yardımcıları
=====================================================
  • Windows açılışında otomatik başlatma (Başlangıç klasörü kısayolu)
  • Tek örnek (single instance) kilidi + ikinci açılışta mevcut pencereyi öne getirme
"""

import os
import socket
import subprocess
import sys
import threading
from typing import Callable, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SINGLETON_PORT = 50507          # localhost — sadece bu makinede
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ─────────────────────────────────────────────
# pythonw.exe yolu
# ─────────────────────────────────────────────

def pythonw_path() -> str:
    exe_dir = os.path.dirname(sys.executable)
    for name in ("pythonw.exe", "python.exe"):
        cand = os.path.join(exe_dir, name)
        if os.path.isfile(cand):
            return cand
    return sys.executable


# ─────────────────────────────────────────────
# Windows açılışında otomatik başlatma
# ─────────────────────────────────────────────

def _startup_lnk() -> str:
    startup = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup",
    )
    return os.path.join(startup, "MehburAI.lnk")


def is_autostart_enabled() -> bool:
    return os.path.isfile(_startup_lnk())


def set_autostart(enabled: bool) -> bool:
    """Başlangıç klasörüne MehburAI kısayolu ekler/kaldırır. Başarılıysa True."""
    lnk = _startup_lnk()
    if not enabled:
        try:
            if os.path.isfile(lnk):
                os.remove(lnk)
            return True
        except Exception:
            return False

    # Kısayolu oluştur — GÖRELİ argüman + WorkingDirectory (mutlak yol pencereyi kapatıyor)
    lnk_esc = lnk.replace("'", "''")
    proj_esc = BASE_DIR.replace("'", "''")
    pyw_esc = pythonw_path().replace("'", "''")
    ps = (
        "$W = New-Object -ComObject WScript.Shell;"
        f"$S = $W.CreateShortcut('{lnk_esc}');"
        f"$S.TargetPath = '{pyw_esc}';"
        "$S.Arguments = 'run_mehbur.py --tray';"
        f"$S.WorkingDirectory = '{proj_esc}';"
        "$S.Description = 'MehburAI - Guvenlik Modu (arka plan)';"
        "$S.Save()"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, timeout=15, creationflags=_NO_WINDOW,
        )
    except Exception:
        return False
    return os.path.isfile(lnk)


# ─────────────────────────────────────────────
# Tek örnek (single instance)
# ─────────────────────────────────────────────

class SingleInstance:
    """
    localhost soketiyle tek örnek kilidi.
    - `acquire()` ilk örnekte True döner ve "SHOW" dinleyicisini başlatır.
    - Zaten çalışıyorsa False döner ve mevcut pencereye "öne gel" sinyali gönderir.
    """

    def __init__(self, on_show: Optional[Callable[[], None]] = None):
        self._on_show = on_show
        self._sock: Optional[socket.socket] = None

    def set_on_show(self, fn: Callable[[], None]) -> None:
        self._on_show = fn

    def acquire(self) -> bool:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            srv.bind(("127.0.0.1", _SINGLETON_PORT))
        except OSError:
            srv.close()
            self._signal_show()
            return False
        srv.listen(3)
        self._sock = srv
        threading.Thread(target=self._listen, daemon=True, name="MehburAI-Singleton").start()
        return True

    def _listen(self) -> None:
        while self._sock is not None:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break
            try:
                data = conn.recv(32)
                if data.strip() == b"SHOW" and self._on_show:
                    self._on_show()
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def _signal_show() -> None:
        try:
            c = socket.create_connection(("127.0.0.1", _SINGLETON_PORT), timeout=2)
            c.sendall(b"SHOW")
            c.close()
        except Exception:
            pass

    def release(self) -> None:
        s, self._sock = self._sock, None
        if s is not None:
            try:
                s.close()
            except Exception:
                pass
