# -*- coding: utf-8 -*-
"""
MehburAI - 🛡️ Güvenlik Modu (Yetkisiz Erişim Alarmı)
=====================================================
Kullanıcının ayarlardan belirlediği korumalı yol(lar)ı arka planda izler.
Korunan bir klasör Dosya Gezgini'nde açıldığında, korunan bir program
çalıştırıldığında ya da korunan bir dosya/klasör SİLİNDİĞİNDE
`on_access(path, event)` geri çağrısını tetikler; arayüz de bir şifre ekranı
gösterir. (`event`: "access" veya "delete")

Korumalı yolların gizli bir yedeği tutulur; yetkisiz silme tespit edilirse
(yanlış şifre / ekran kapatıldı) dosya bu yedekten otomatik geri yüklenir.

Şifre yanlış girilir ya da ekran kapatılırsa:
  • Web kameradan bir kare çekilir,
  • Cihaz sahibinin Telegram'ına ("MehburAI (Telegram)" botu) gönderilir,
  • Kişiye "fotoğrafınız çekildi ve cihaz sahibine iletildi" uyarısı gösterilir.

Bu bir GİZLİ izleme aracı DEĞİLDİR: şifre ekranı ve uyarı açıkça görünür,
kişi fotoğrafının çekildiğini bilir. Yalnızca cihaz sahibinin kendi
bilgisayarında yetkisiz erişimi fark etmesi için tasarlanmıştır.
"""

import hashlib
import os
import shutil
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


def _foreground_exe_path() -> Optional[str]:
    """Şu an odakta (foreground) olan pencerenin çalıştırılabilir dosya yolu — hızlı, ctypes."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return None
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not h:
            return None
        try:
            buf = ctypes.create_unicode_buffer(4096)
            size = wintypes.DWORD(4096)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return buf.value
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        return None
    return None


def close_target(path: str) -> bool:
    """
    Yetkisiz erişimde açılan hedefi kapatır:
      • program → o süreci (yol veya isim eşleşmesi) sonlandırır
      • klasör  → o yolu gösteren Dosya Gezgini penceresini kapatır
    """
    p = path.strip().strip('"')
    if not p:
        return False
    p_esc = p.replace("'", "''")
    base = os.path.basename(p)
    is_prog = p.lower().endswith((".exe", ".com", ".bat", ".lnk")) or (
        not os.path.isdir(p) and "." in base
    )
    try:
        if is_prog:
            stem = os.path.splitext(base)[0].replace("'", "''")
            _run_ps(
                "$ErrorActionPreference='SilentlyContinue';"
                f"Get-Process | Where-Object {{ $_.Path -eq '{p_esc}' -or "
                f"$_.ProcessName -eq '{stem}' }} | Stop-Process -Force",
                timeout=10,
            )
        else:
            _run_ps(
                "$ErrorActionPreference='SilentlyContinue';"
                "(New-Object -ComObject Shell.Application).Windows() | "
                f"Where-Object {{ try {{ $_.Document.Folder.Self.Path -eq '{p_esc}' }} "
                "catch { $false } } | ForEach-Object { $_.Quit() }",
                timeout=10,
            )
        return True
    except Exception:
        return False


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
# Korumalı Dosya Yedeği (yetkisiz silmeye karşı geri yükleme)
# ─────────────────────────────────────────────

class FileBackup:
    """
    Korumalı dosya/klasörlerin gizli bir kopyasını `data/security_backups/`
    altında tutar. Yetkisiz silme tespit edilince orijinal yol bu kopyadan
    geri yüklenir. (Şifre doğru girilirse yedek `discard()` ile atılır.)
    """

    DIR = os.path.join(DATA_DIR, "security_backups")

    # Yedek boyut sınırları — bunları aşan yollar için silme yine tespit edilir
    # (fotoğraf + Telegram + kapatma) ama otomatik geri yükleme yapılmaz.
    MAX_BYTES = 200 * 1024 * 1024     # 200 MB
    MAX_FILES = 4000

    @classmethod
    def _slot(cls, path: str) -> str:
        norm = os.path.normcase(os.path.abspath(path.strip().strip('"')))
        tag = hashlib.sha1(norm.encode("utf-8", "replace")).hexdigest()[:16]
        base = os.path.basename(path.rstrip("\\/")) or "kok"
        return os.path.join(cls.DIR, f"{tag}__{base}")

    @classmethod
    def has(cls, path: str) -> bool:
        slot = cls._slot(path)
        return os.path.isfile(slot) or os.path.isdir(slot)

    @classmethod
    def _too_big(cls, path: str) -> bool:
        """Klasör yedeklenemeyecek kadar büyük mü? (hızlı, erken çıkışlı tarama)"""
        total, count = 0, 0
        try:
            for root, _dirs, files in os.walk(path):
                for name in files:
                    count += 1
                    if count > cls.MAX_FILES:
                        return True
                    try:
                        total += os.path.getsize(os.path.join(root, name))
                    except OSError:
                        pass
                    if total > cls.MAX_BYTES:
                        return True
        except Exception:
            return True
        return False

    @classmethod
    def sync(cls, path: str) -> None:
        """Yol hâlâ varsa ve sınırların altındaysa gizli yedeği tazeler."""
        try:
            slot = cls._slot(path)
            if os.path.isdir(path):
                if cls._too_big(path):
                    # Çok büyük — eski yedeği (varsa) at, geri yükleme devre dışı
                    if os.path.isdir(slot):
                        shutil.rmtree(slot, ignore_errors=True)
                    return
                os.makedirs(cls.DIR, exist_ok=True)
                if os.path.isdir(slot):
                    shutil.rmtree(slot, ignore_errors=True)
                elif os.path.isfile(slot):
                    os.remove(slot)
                shutil.copytree(path, slot)
            elif os.path.isfile(path):
                try:
                    if os.path.getsize(path) > cls.MAX_BYTES:
                        return
                except OSError:
                    return
                os.makedirs(cls.DIR, exist_ok=True)
                if os.path.isdir(slot):
                    shutil.rmtree(slot, ignore_errors=True)
                shutil.copy2(path, slot)
        except Exception:
            pass

    @classmethod
    def restore(cls, path: str) -> bool:
        """Silinen korumalı yolu yedekten eski yerine koyar."""
        try:
            slot = cls._slot(path)
            if os.path.exists(path):
                return True
            if os.path.isdir(slot):
                shutil.copytree(slot, path)
                return True
            if os.path.isfile(slot):
                parent = os.path.dirname(path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                shutil.copy2(slot, path)
                return True
        except Exception:
            pass
        return False

    @classmethod
    def discard(cls, path: str) -> None:
        """Yedeği sil (silme işlemi yetkiyle onaylandı)."""
        try:
            slot = cls._slot(path)
            if os.path.isdir(slot):
                shutil.rmtree(slot, ignore_errors=True)
            elif os.path.isfile(slot):
                os.remove(slot)
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

    POLL_INTERVAL = 1.5          # saniye
    DEBOUNCE = 8.0               # ekran kapandıktan sonra kısa süre tekrar sormaz (sn)

    BACKUP_EVERY = 30.0         # korumalı yol yedeği en fazla bu sıklıkla tazelenir (sn)

    def __init__(self, on_access: Callable[..., None]):
        # on_access(path) veya on_access(path, event) — event: "access" | "delete"
        self._on_access = on_access
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        # Kenar (edge) tespiti
        self._run_prev = set()      # geçen taramada çalışan/açık korumalı hedefler
        self._fg_prev = None        # geçen taramada odakta olan korumalı hedef
        self._passed = set()        # şifresi doğru girilmiş hedefler (gerçekten kapanınca temizlenir)
        self._pending = set()       # şifre ekranı açık olanlar
        self._cooldown = {}         # path -> ts (kısa debounce)
        self._primed = False        # ilk tarama mevcut durumu sessizce kaydeder
        # Silme (delete) tespiti
        self._exists_prev = {}      # path -> geçen taramada var mıydı
        self._del_fired = set()     # silme ekranı tetiklenmiş hedefler (yol geri gelince temizlenir)
        self._backup_at = {}        # path -> son yedekleme ts

    @staticmethod
    def _reappears(target: str, tries: int = 3, gap: float = 0.4) -> bool:
        """Kısa aralıklarla tekrar bakar; yol geri gelirse True (yanlış alarm)."""
        for _ in range(tries):
            time.sleep(gap)
            if os.path.exists(target):
                return True
        return False

    def _notify(self, path: str, event: str) -> None:
        """on_access geri çağrısını hem tek hem çift argümanlı imzayla dener."""
        try:
            self._on_access(path, event)
        except TypeError:
            self._on_access(path)

    # ── yaşam döngüsü ──────────────────────────
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        with self._lock:
            self._primed = False
            self._run_prev.clear()
            self._fg_prev = None
            self._passed.clear()
            self._exists_prev.clear()
            self._del_fired.clear()
        self._thread = threading.Thread(target=self._loop, name="MehburAI-SecurityGuard", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    # ── doğrulama sonrası ─────────────────────
    def mark_passed(self, path: str) -> None:
        """Şifre doğru girildi — hedef gerçekten kapanana kadar tekrar sorma."""
        p = self._norm(path)
        with self._lock:
            self._pending.discard(p)
            self._passed.add(p)
            self._cooldown[p] = time.time() + self.DEBOUNCE

    def mark_resolved(self, path: str) -> None:
        """Ekran kapandı (yanlış şifre / iptal). Kısa debounce; 'passed' sayılmaz."""
        p = self._norm(path)
        with self._lock:
            self._pending.discard(p)
            self._cooldown[p] = time.time() + self.DEBOUNCE

    # ── iç mekanizma ──────────────────────────
    @staticmethod
    def _norm(p: str) -> str:
        return os.path.normcase(os.path.normpath(p.strip().strip('"')))

    @staticmethod
    def _base(p: str) -> str:
        return os.path.basename(p).lower()

    @classmethod
    def _is_program(cls, target: str) -> bool:
        return target.lower().endswith((".exe", ".com", ".bat", ".lnk")) or (
            not os.path.isdir(target) and "." in os.path.basename(target)
        )

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

    WAKE_GAP = 40.0   # iki poll arası bu kadar saniye geçtiyse = uyku/hazırda bekletme

    def _loop(self) -> None:
        last = time.monotonic()
        while self._running:
            gap = time.monotonic() - last
            last = time.monotonic()
            if gap > self.WAKE_GAP:
                # Bilgisayar uyudu ve yeni uyandı → o an açık olan her şey için
                # şifre sormamak adına durumu sıfırla, bir tur bekle, sonra devam et.
                with self._lock:
                    self._primed = False
                    self._run_prev.clear()
                    self._fg_prev = None
                    self._exists_prev.clear()
                    self._del_fired.clear()
                time.sleep(2.0)
                continue
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
                self._run_prev.clear()
                self._fg_prev = None
                self._passed.clear()
                self._exists_prev.clear()
                self._del_fired.clear()
            return

        # ── Korumalı yol SİLME tespiti (Explorer taramasından bağımsız) ──
        del_to_fire = []
        to_backup = []
        with self._lock:
            now = time.time()
            watch_set = set(watch)
            for target in list(self._exists_prev):
                if target not in watch_set:
                    self._exists_prev.pop(target, None)
                    self._del_fired.discard(target)
                    self._backup_at.pop(target, None)

            for target in watch:
                exists = os.path.exists(target)
                had = self._exists_prev.get(target, exists)
                self._exists_prev[target] = exists

                if exists:
                    self._del_fired.discard(target)
                    # Gizli yedeği periyodik tazele (yalnızca doğrulama ekranı açık değilken).
                    # Priming turunda da alınır — mümkün olan en erken yedek.
                    if (target not in self._pending
                            and now - self._backup_at.get(target, 0) > self.BACKUP_EVERY):
                        self._backup_at[target] = now
                        to_backup.append(target)
                elif (had and self._primed and target not in self._del_fired
                        and now >= self._cooldown.get(target, 0)
                        and os.path.isdir(os.path.dirname(target) or target)):
                    # Vardı, artık yok (ama üst klasör duruyor) → silinmiş / taşınmış
                    # Üst klasör de yoksa: sürücü çıkarılmış olabilir, alarm verme.
                    self._del_fired.add(target)
                    self._cooldown[target] = now + self.DEBOUNCE
                    del_to_fire.append(target)

        # Yedekleme + geri çağrı kilit dışında (büyük klasörler UI'ı bloklamasın)
        for target in to_backup:
            FileBackup.sync(target)

        for target in del_to_fire:
            # Yanlış pozitifi ele: bazı editörler kaydederken dosyayı anlık siler/yeniden
            # oluşturur. Bildirmeden önce kısa aralıklarla birkaç kez doğrula.
            if self._reappears(target):
                with self._lock:
                    self._del_fired.discard(target)
                continue
            try:
                self._notify(target, "delete")
            except Exception:
                with self._lock:
                    self._del_fired.discard(target)

        raw_explorer, raw_exes = self._scan()
        explorer = [self._norm(p) for p in raw_explorer]
        exe_bases = set(self._base(p) for p in raw_exes)
        fg_path = _foreground_exe_path()
        fg_base = self._base(fg_path) if fg_path else ""

        # Şu an "açık" korumalı hedefler + odaktaki korumalı hedef
        run_now, fg_now = set(), None
        for target in watch:
            if self._is_program(target):
                if self._base(target) in exe_bases:
                    run_now.add(target)
                if fg_base and self._base(target) == fg_base:
                    fg_now = target
            else:  # klasör
                if any(op == target or op.startswith(target + os.sep) for op in explorer):
                    run_now.add(target)

        with self._lock:
            now = time.time()
            # Gerçekten kapanan hedefleri "passed" listesinden düş → tekrar açılırsa sorar
            for p in list(self._passed):
                if p not in run_now and p != fg_now:
                    self._passed.discard(p)

            if not self._primed:
                self._run_prev = set(run_now)
                self._fg_prev = fg_now
                self._passed |= run_now          # başlangıçta zaten açık olanlara güven
                self._primed = True
                return

            run_edge = run_now - self._run_prev              # yeni başlatıldı / açıldı
            fg_edge = ({fg_now} if fg_now and fg_now != self._fg_prev else set())  # odağa geldi
            candidates = (run_edge | fg_edge) - self._passed - self._pending
            to_fire = [t for t in candidates if now >= self._cooldown.get(t, 0)]

            self._run_prev = run_now | self._pending
            self._fg_prev = fg_now
            for t in to_fire:
                self._pending.add(t)

        for target in to_fire:
            try:
                self._notify(target, "access")
            except Exception:
                with self._lock:
                    self._pending.discard(target)


# ─────────────────────────────────────────────
# Şifre yanlış → alarm akışı (arayüzden çağrılır)
# ─────────────────────────────────────────────

def trigger_intruder_alert(reason: str = "Yanlış şifre", close_path: Optional[str] = None,
                           restore_path: Optional[str] = None) -> dict:
    """
    Yetkisiz erişim akışı (arayüz bunu bir arka plan thread'inde çağırmalı):
      1. `close_path` verilmişse açılan hedefi kapatır (program sonlandır / klasör penceresi kapat)
      2. `restore_path` verilmişse silinen korumalı yolu gizli yedekten geri yükler
      3. Web kameradan fotoğraf çeker
      4. Cihaz sahibinin Telegram'ına gönderir

    Returns: {"photo": path|None, "telegram": bool, "closed": bool, "restored": bool, "detail": str}
    """
    closed = False
    if close_path:
        closed = close_target(close_path)

    restored = False
    if restore_path:
        restored = FileBackup.restore(restore_path)

    when = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    host = os.environ.get("COMPUTERNAME", "bilinmeyen-cihaz")
    user = os.environ.get("USERNAME", "?")

    photo = CameraCapture.snapshot()
    _hit = close_path or restore_path
    caption = (
        f"🛡️ MehburAI Güvenlik Uyarısı\n"
        f"Sebep: {reason}\n"
        + (f"Hedef: {os.path.basename(_hit.rstrip(chr(92)+chr(47)))}\n" if _hit else "")
        + (f"Geri yükleme: {'başarılı' if restored else 'başarısız'}\n" if restore_path else "")
        + f"Cihaz: {host} / kullanıcı: {user}\n"
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
    if close_path:
        detail.append("hedef kapatıldı" if closed else "hedef kapatılamadı")
    if restore_path:
        detail.append("dosya geri yüklendi" if restored else "dosya geri yüklenemedi")
    detail.append("fotoğraf çekildi" if photo else "kamera alınamadı")
    detail.append("Telegram'a gönderildi" if tg_ok else "Telegram gönderilemedi")
    return {"photo": photo, "telegram": tg_ok, "closed": closed, "restored": restored,
            "detail": ", ".join(detail)}


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
