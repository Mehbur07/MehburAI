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

# .exe'ye paketlenmişse (PyInstaller) çalışma klasörü .exe'nin kendi yanı,
# geliştirme ortamında bu betiğin bulunduğu klasördür.
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
    else os.path.dirname(os.path.abspath(__file__))
_SINGLETON_PORT = 50507          # localhost — sadece bu makinede
# Windows bazı port aralıklarını kendine ayırabilir (Hyper-V/WSL/Docker; örn. 50411-50510).
# O aralıktaki port "erişim izni yok" (WinError 10013) verir — o zaman yedek portlar denenir.
_SINGLETON_PORTS = (_SINGLETON_PORT, 47831, 39517, 28731, 19853)
_SHOW_REPLY = b"OK"
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
    if getattr(sys, "frozen", False):
        target, args = sys.executable, "--tray"
    else:
        target, args = pythonw_path(), "run_mehbur.py --tray"
    lnk_esc = lnk.replace("'", "''")
    proj_esc = BASE_DIR.replace("'", "''")
    target_esc = target.replace("'", "''")
    ps = (
        "$W = New-Object -ComObject WScript.Shell;"
        f"$S = $W.CreateShortcut('{lnk_esc}');"
        f"$S.TargetPath = '{target_esc}';"
        f"$S.Arguments = '{args}';"
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
        """İlk örnekse (ya da kilit kurulamıyorsa) True; zaten çalışıyorsa False döner."""
        for port in _SINGLETON_PORTS:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            try:
                srv.bind(("127.0.0.1", port))
            except OSError as e:
                srv.close()
                if self._is_addr_in_use(e):
                    # Port dolu: gerçekten MehburAI mi? (eski sürüm yanıt vermez → ilk portta yine "çalışıyor" say)
                    if self._signal_show(port) or port == _SINGLETON_PORT:
                        return False
                # Erişim izni yok (rezerve port) ya da başka bir uygulamanın portu → sonraki porta geç
                continue
            srv.listen(3)
            self._sock = srv
            threading.Thread(target=self._listen, daemon=True, name="MehburAI-Singleton").start()
            return True
        # Hiçbir port kullanılamadı: uygulamanın açılmasını engelleme (kilitsiz başla)
        return True

    @staticmethod
    def _is_addr_in_use(e: OSError) -> bool:
        import errno
        return getattr(e, "winerror", None) == 10048 or e.errno in (errno.EADDRINUSE, 98, 48)

    def _listen(self) -> None:
        while self._sock is not None:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break
            try:
                data = conn.recv(32)
                if data.strip() == b"SHOW":
                    conn.sendall(_SHOW_REPLY)
                    if self._on_show:
                        self._on_show()
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    @staticmethod
    def _signal_show(port: int = _SINGLETON_PORT) -> bool:
        """Çalışan MehburAI'ye 'öne gel' der; yanıt verirse (gerçekten MehburAI ise) True."""
        try:
            c = socket.create_connection(("127.0.0.1", port), timeout=2)
            try:
                c.sendall(b"SHOW")
                return c.recv(8).strip() == _SHOW_REPLY
            finally:
                c.close()
        except Exception:
            return False

    def release(self) -> None:
        s, self._sock = self._sock, None
        if s is not None:
            try:
                s.close()
            except Exception:
                pass
