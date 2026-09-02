# -*- coding: utf-8 -*-
"""
MehburAI - 🛡️ Güvenlik Modu (Yetkisiz Erişim Alarmı)
=====================================================
Kullanıcının ayarlardan belirlediği korumalı yol(lar)ı arka planda izler.
Korunan bir klasör Dosya Gezgini'nde açıldığında veya korunan bir program
çalıştırıldığında `on_access(path)` geri çağrısını tetikler; arayüz de bir
şifre ekranı gösterir.

Şifre yanlış girilir ya da ekran kapatılırsa:
  • Web kameradan bir kare çekilir,
  • Cihaz sahibinin Telegram'ına ("MehburAI (Telegram)" botu) gönderilir,
  • Kişiye "fotoğrafınız çekildi ve cihaz sahibine iletildi" uyarısı gösterilir.

Bu bir GİZLİ izleme aracı DEĞİLDİR: şifre ekranı ve uyarı açıkça görünür,
kişi fotoğrafının çekildiğini bilir. Yalnızca cihaz sahibinin kendi
bilgisayarında yetkisiz erişimi fark etmesi için tasarlanmıştır.
"""

import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Callable, List, Optional

import requests

from config import DATA_DIR, get_security_config

# Windows'ta arka plan PowerShell çağrılarının konsol penceresi açmasını engeller
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _run_ps(script: str, timeout: float = 8.0) -> str:
    """PowerShell betiğini GÖRÜNMEZ pencerede çalıştırır, stdout döndürür."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
            creationflags=_NO_WINDOW,
        )
        return out.stdout or ""
    except Exception:
        return ""


# ─────────────────────────────────────────────
# Telegram Bildirimi
# ─────────────────────────────────────────────

class TelegramNotifier:
    """"MehburAI (Telegram)" botu üzerinden cihaz sahibine bildirim gönderir."""

    API = "https://api.telegram.org"

    @classmethod
    def _creds(cls):
        cfg = get_security_config()
        return cfg.get("telegram_bot_token", "").strip(), cfg.get("telegram_chat_id", "").strip()

    @classmethod
    def is_configured(cls) -> bool:
        token, chat_id = cls._creds()
        return bool(token and chat_id)

    @classmethod
    def send_message(cls, text: str) -> bool:
        token, chat_id = cls._creds()
        if not token or not chat_id:
            return False
        try:
            r = requests.post(
                f"{cls.API}/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": text},
                timeout=15,
            )
            return r.ok
        except requests.RequestException:
            return False

    @classmethod
    def send_photo(cls, photo_path: str, caption: str = "") -> bool:
        token, chat_id = cls._creds()
        if not token or not chat_id or not os.path.isfile(photo_path):
            return False
        try:
            with open(photo_path, "rb") as f:
                r = requests.post(
                    f"{cls.API}/bot{token}/sendPhoto",
                    data={"chat_id": chat_id, "caption": caption[:1024]},
                    files={"photo": f},
                    timeout=30,
                )
            return r.ok
        except (requests.RequestException, OSError):
            return False

    @classmethod
    def test(cls) -> tuple:
        """Ayarlardaki 'Telegram Testi' butonu için. (başarı, mesaj)"""
        token, chat_id = cls._creds()
        if not token or not chat_id:
            return False, "Bot token veya chat ID girilmemiş."
        ok = cls.send_message("✅ MehburAI Güvenlik Modu — Telegram bağlantısı çalışıyor.")
        return (ok, "Test mesajı gönderildi." if ok else "Gönderilemedi (token/chat ID hatalı olabilir).")

    @classmethod
    def detect_chat_id(cls, token: str = "") -> tuple:
        """
        Bota yazılan son mesajdan chat ID'yi otomatik bulur.
        Kullanıcının önceden bota bir mesaj ('merhaba' / /start) atması gerekir.
        Returns: (chat_id|None, açıklama)
        """
        token = (token or cls._creds()[0]).strip()
        if not token:
            return None, "Önce Bot Token gir."
        try:
            r = requests.get(f"{cls.API}/bot{token}/getUpdates", timeout=15)
            data = r.json()
        except (requests.RequestException, ValueError):
            return None, "Telegram'a bağlanılamadı."
        if not data.get("ok"):
            return None, "Bot Token geçersiz görünüyor."
        for upd in reversed(data.get("result", [])):
            msg = upd.get("message") or upd.get("edited_message") or upd.get("channel_post")
            chat = (msg or {}).get("chat") or {}
            if chat.get("id") is not None:
                who = chat.get("username") or chat.get("first_name") or chat.get("title") or chat["id"]
                return str(chat["id"]), f"Chat ID bulundu ({who})."
        return None, "Bota henüz mesaj yazmamışsın. Telegram'da @MehburAI_bot'a bir 'merhaba' yaz, sonra tekrar dene."


# ─────────────────────────────────────────────
# Web Kamera Yakalama
# ─────────────────────────────────────────────

class CameraCapture:
    """Web kameradan tek kare yakalar. OpenCV varsa onu kullanır."""

    @staticmethod
    def snapshot(save_dir: Optional[str] = None) -> Optional[str]:
        save_dir = save_dir or os.path.join(DATA_DIR, "security_snapshots")
        os.makedirs(save_dir, exist_ok=True)
        fname = f"guvenlik_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        path = os.path.join(save_dir, fname)

        try:
            import cv2  # type: ignore
        except Exception:
            return None

        cam = None
        try:
            for index in (0, 1, 2):
                cam = cv2.VideoCapture(index, getattr(cv2, "CAP_DSHOW", 0))
                if cam is not None and cam.isOpened():
                    break
                if cam is not None:
                    cam.release()
                    cam = None
            if cam is None or not cam.isOpened():
                return None

            # İlk kareler genellikle karanlık olur — birkaç kare ısındır
            frame = None
            for _ in range(8):
                ok, frame = cam.read()
                time.sleep(0.06)
            if frame is None:
                ok, frame = cam.read()
                if not ok:
                    return None

            cv2.imwrite(path, frame)
            return path if os.path.isfile(path) else None
        except Exception:
            return None
        finally:
            if cam is not None:
                try:
                    cam.release()
                except Exception:
                    pass


# ─────────────────────────────────────────────
# Korumalı Yol İzleyici
# ─────────────────────────────────────────────

class SecurityGuard:
    """
    Arka planda korumalı yolların açılıp açılmadığını izler.
    Erişim tespit edilince `on_access(path)` çağrılır (arayüz şifre ekranı gösterir).
    """

    POLL_INTERVAL = 2.0          # saniye
    DEBOUNCE = 8.0               # ekran kapandıktan sonra kısa süre tekrar sormaz (sn)

    def __init__(self, on_access: Callable[[str], None]):
        self._on_access = on_access
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        # Kenar (edge) tespiti: yalnızca "kapalı → açık" geçişinde şifre sorulur.
        self._active = set()        # şu an açık/çalışan korumalı hedefler
        self._pending = set()       # şifre ekranı açık olanlar
        self._cooldown = {}         # path -> ts (kısa debounce)
        self._primed = False        # ilk tarama mevcut durumu sessizce kaydeder

    # ── yaşam döngüsü ──────────────────────────
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        with self._lock:
            self._primed = False    # zaten açık olan programlar için sorma
            self._active.clear()
        self._thread = threading.Thread(target=self._loop, name="MehburAI-SecurityGuard", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    # ── doğrulama sonrası ─────────────────────
    def mark_passed(self, path: str) -> None:
        p = self._norm(path)
        with self._lock:
            self._pending.discard(p)
            self._active.add(p)     # hâlâ açık — kapanıp tekrar açılmadıkça sorma
            self._cooldown[p] = time.time() + self.DEBOUNCE

    def mark_resolved(self, path: str) -> None:
        """Ekran kapandı (doğru/yanlış fark etmez) — hedef hâlâ açıksa yeniden sorma."""
        p = self._norm(path)
        with self._lock:
            self._pending.discard(p)
            self._active.add(p)
            self._cooldown[p] = time.time() + self.DEBOUNCE

    # ── iç mekanizma ──────────────────────────
    @staticmethod
    def _norm(p: str) -> str:
        return os.path.normcase(os.path.normpath(p.strip().strip('"')))

    def _watch_list(self) -> List[str]:
        cfg = get_security_config()
        if not cfg.get("security_enabled"):
            return []
        return [self._norm(p) for p in cfg.get("security_watch_paths", []) if str(p).strip()]

    # Tek PowerShell çağrısıyla hem açık Explorer klasörlerini hem çalışan
    # süreç yollarını alır (E| ve P| ön ekleriyle) — poll başına 1 süreç.
    _SCAN_SCRIPT = (
        "$ErrorActionPreference='SilentlyContinue';"
        "(New-Object -ComObject Shell.Application).Windows() | "
        "ForEach-Object { try { 'E|' + $_.Document.Folder.Self.Path } catch {} };"
        "Get-Process | Where-Object { $_.Path } | ForEach-Object { 'P|' + $_.Path }"
    )

    @classmethod
    def _scan(cls) -> tuple:
        """(açık_explorer_klasörleri, çalışan_exe_yolları)"""
        explorer, exes = [], []
        for line in _run_ps(cls._SCAN_SCRIPT, timeout=6).splitlines():
            line = line.strip()
            if line.startswith("E|") and line[2:]:
                explorer.append(line[2:])
            elif line.startswith("P|") and line[2:]:
                exes.append(line[2:])
        return explorer, exes

    @staticmethod
    def _open_explorer_paths() -> List[str]:
        return SecurityGuard._scan()[0]

    @staticmethod
    def _running_exe_paths() -> List[str]:
        return SecurityGuard._scan()[1]

    @staticmethod
    def list_running_apps() -> List[tuple]:
        """
        Şu an penceresi açık olan kullanıcı programlarını (ad, tam yol) listeler.
        Ayarlardaki "Çalışan programdan seç" için kullanılır.
        """
        ps = (
            "$ErrorActionPreference='SilentlyContinue';"
            "Get-Process | Where-Object { $_.Path -and $_.MainWindowTitle } | "
            "Sort-Object Name -Unique | ForEach-Object { $_.Name + '|' + $_.Path }"
        )
        win_dir = os.environ.get("SystemRoot", r"C:\Windows").lower()
        apps, seen = [], set()
        for line in _run_ps(ps, timeout=8).splitlines():
            if "|" not in line:
                continue
            name, path = line.split("|", 1)
            name, path = name.strip(), path.strip()
            low = path.lower()
            if not path or low in seen or low.startswith(win_dir):
                continue
            if name.lower() in ("python", "pythonw"):
                continue
            seen.add(low)
            apps.append((name, path))
        return sorted(apps, key=lambda a: a[0].lower())

    def _loop(self) -> None:
        while self._running:
            try:
                self._check_once()
            except Exception:
                pass
            waited = 0.0
            while waited < self.POLL_INTERVAL and self._running:
                time.sleep(0.25)
                waited += 0.25

    def _check_once(self) -> None:
        watch = self._watch_list()
        if not watch:
            with self._lock:
                self._active.clear()
            return

        raw_explorer, raw_exes = self._scan()
        explorer = [self._norm(p) for p in raw_explorer]
        exes = set(self._norm(p) for p in raw_exes)

        # Şu an açık/çalışan korumalı hedefler
        now_active = set()
        for target in watch:
            is_open = target in exes or any(
                op == target or op.startswith(target + os.sep) for op in explorer
            )
            if is_open:
                now_active.add(target)

        with self._lock:
            # İlk tarama: yalnızca mevcut durumu kaydet, şifre sorma
            if not self._primed:
                self._active = now_active
                self._primed = True
                return

            now = time.time()
            newly_opened = now_active - self._active - self._pending
            to_fire = [
                t for t in newly_opened if now >= self._cooldown.get(t, 0)
            ]
            # Açık kalanları + ekranı açık olanları "aktif" say
            self._active = now_active | self._pending
            for t in to_fire:
                self._pending.add(t)

        for target in to_fire:
            try:
                self._on_access(target)
            except Exception:
                with self._lock:
                    self._pending.discard(target)


# ─────────────────────────────────────────────
# Şifre yanlış → alarm akışı (arayüzden çağrılır)
# ─────────────────────────────────────────────

def trigger_intruder_alert(reason: str = "Yanlış şifre") -> dict:
    """
    Web kameradan fotoğraf çeker ve Telegram'a gönderir.
    Arayüz bunu bir arka plan thread'inde çağırmalıdır (ağ + kamera bloklayabilir).

    Returns: {"photo": path|None, "telegram": bool, "detail": str}
    """
    when = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    host = os.environ.get("COMPUTERNAME", "bilinmeyen-cihaz")
    user = os.environ.get("USERNAME", "?")

    photo = CameraCapture.snapshot()
    caption = (
        f"🛡️ MehburAI Güvenlik Uyarısı\n"
        f"Sebep: {reason}\n"
        f"Cihaz: {host} / kullanıcı: {user}\n"
        f"Zaman: {when}"
    )

    tg_ok = False
    if TelegramNotifier.is_configured():
        if photo:
            tg_ok = TelegramNotifier.send_photo(photo, caption)
        if not tg_ok:
            tg_ok = TelegramNotifier.send_message(
                caption + ("\n(Kameradan görüntü alınamadı.)" if not photo else "")
            )

    detail = []
    detail.append("fotoğraf çekildi" if photo else "kamera alınamadı")
    detail.append("Telegram'a gönderildi" if tg_ok else "Telegram gönderilemedi")
    return {"photo": photo, "telegram": tg_ok, "detail": ", ".join(detail)}


# ─────────────────────────────────────────────
# Bağımsız Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import io
    import sys

    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("MehburAI Güvenlik Modu — hızlı test")
    print("Telegram yapılandırılmış mı:", TelegramNotifier.is_configured())
    print("Açık Explorer klasörleri:", SecurityGuard._open_explorer_paths())
    print("Kamera testi (data/security_snapshots/):", CameraCapture.snapshot())
