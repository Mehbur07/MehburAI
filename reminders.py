# -*- coding: utf-8 -*-
"""
MehburAI - Hatırlatıcı & Alarm (Reminders)
==========================================
Sohbet kutusundan ve sesli komutla doğal Türkçe ile hatırlatıcı/alarm kurar:

    "20 dakika sonra hatırlat çamaşırı çıkar"
    "yarın 9'da beni uyandır"          (sesli komutta: "yarın dokuzda beni uyandır")
    "akşam 8'de ilaç içmemi hatırlat"
    "yarım saat sonra alarm kur"
    "hatırlatıcılarım"  /  "alarmı iptal et"  /  "tüm hatırlatıcıları sil"

Zamanı gelince `on_fire(kayıt)` geri çağrısı çalışır (GUI: pencere + sesli okuma +
Telegram). Kayıtlar `data/desktop_reminders.json` dosyasında kalıcıdır; uygulama
kapalıyken kaçan hatırlatıcılar bir sonraki açılışta "kaçırıldı" notuyla gösterilir.

(Telegram'ın `/hatirlat` komutu ayrı çalışır; kendi dosyasını kullanır.)
"""

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

from config import DATA_DIR
from memory_engine import turkish_lower

REMINDERS_PATH = os.path.join(DATA_DIR, "desktop_reminders.json")

# Uygulama kapalıyken kaçan hatırlatıcı bu süreden eskiyse sessizce atılır
MAX_MISSED_SECONDS = 24 * 3600
# Bu süreden fazla gecikmişse bildirime "kaçırıldı" notu eklenir
LATE_NOTE_SECONDS = 120


# ─────────────────────────────────────────────
# Doğal dil çözümleme
# ─────────────────────────────────────────────

_ONES = {"sıfır": 0, "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5,
         "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9}
_TENS = {"on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50,
         "altmış": 60, "yetmiş": 70, "seksen": 80, "doksan": 90}
_NUM_WORDS = set(_ONES) | set(_TENS) | {"yüz"}
_SUFFIXES = ("da", "de", "ta", "te", "ya", "ye", "a", "e")

# Sayı sözcüğünün saat anlamı taşıdığı bağlam (bir önceki sözcük)
_CLOCK_CONTEXT = {"saat", "sabah", "akşam", "öğle", "öğlen", "gece", "yarın", "bugün",
                  "öğleden", "sonra", "ertesi", "gün"}
_UNIT_WORDS = {"saat", "sa", "dakika", "dk", "dakka", "saniye", "sn", "gün"}

_TRIGGER = re.compile(r"hatırlat|uyandır|\balarm\w*\b.*\b(kur|ayarla)\w*|\b(kur|ayarla)\w*\b.*\balarm")
_LIST_RE = re.compile(
    r"(hatırlatıcılarım|hatırlatmalarım|alarmlarım|hatırlatıcılarımı|alarmlarımı|"
    r"(hatırlatıcı|hatırlatma|alarm)\w*\s+(göster|listele|neler|var\s*mı)|"
    r"bekleyen\s+(hatırlat|alarm))"
)
_CANCEL_RE = re.compile(r"(hatırlatıcı|hatırlatma|alarm)\w*\s+.*?(iptal|sil|kaldır|temizle)"
                        r"|(iptal|sil|kaldır|temizle)\w*\s+.*?(hatırlatıcı|hatırlatma|alarm)")

_NOISE = {"mısın", "misin", "mısınız", "musun", "lütfen", "bana", "beni", "diye",
          "kur", "kurar", "ayarla", "ayarlar", "ayarlarmısın", "alarm", "ve"}


def _words_to_int(words: List[str]) -> Optional[int]:
    total = 0
    for w in words:
        if w in _ONES or w in _TENS:
            total += _ONES.get(w, 0) + _TENS.get(w, 0)
        elif w == "yüz":
            total = (total or 1) * 100
        else:
            return None
    return total


def _split_suffixed_number(tok: str) -> Optional[Tuple[str, str]]:
    """'dokuzda' -> ('dokuz', 'da'); sayı sözcüğü + ek değilse None."""
    for w in sorted(_NUM_WORDS, key=len, reverse=True):
        if tok.startswith(w) and tok[len(w):] in _SUFFIXES:
            return w, tok[len(w):]
    return None


def _normalize(text: str) -> str:
    """Küçük harf; 9'da → '9 da'; sayı sözcükleri (yirmi, dokuzda…) sayıya çevrilir."""
    low = turkish_lower(text)
    low = re.sub(r"(\d)\s*['’]\s*(da|de|ta|te|ya|ye|a|e)\b", r"\1 \2", low)
    low = re.sub(r"\bbuçu[kğ](da|de|ta|te|a|e)\b", r"buçuk \1", low)
    low = re.sub(r"[^\w\s:.]", " ", low)
    toks = low.split()
    out: List[str] = []
    i = 0
    while i < len(toks):
        # ardışık sayı sözcüklerini topla (son sözcük ek almış olabilir)
        j, run, suffix = i, [], ""
        while j < len(toks):
            if toks[j] in _NUM_WORDS:
                run.append(toks[j])
                j += 1
                continue
            sp = _split_suffixed_number(toks[j])
            if sp:
                run.append(sp[0])
                suffix = sp[1]
                j += 1
            break
        prev = out[-1] if out else ""
        nxt = toks[j] if j < len(toks) else ""
        if run and (nxt in _UNIT_WORDS or prev in _CLOCK_CONTEXT or nxt == "buçuk"):
            val = _words_to_int(run)
            if val is not None:
                out.append(str(val))
                if suffix:
                    out.append(suffix)
                i = j
                continue
        out.append(toks[i])
        i += 1
    text2 = " ".join(out)
    # "yarım saat" / "1 buçuk saat" → dakika
    text2 = re.sub(r"\byarım\s+saat\b", "30 dakika", text2)
    text2 = re.sub(r"\b(\d+)\s+buçuk\s+saat\b",
                   lambda m: f"{int(m.group(1)) * 60 + 30} dakika", text2)
    return text2


_UNIT_MIN = {"saat": 60, "sa": 60, "dakika": 1, "dk": 1, "dakka": 1,
             "saniye": 1 / 60, "sn": 1 / 60, "gün": 1440}
_REL_RE = re.compile(
    r"((?:\d+\s*(?:saat|sa|dakika|dk|dakka|saniye|sn|gün)\b\s*(?:ve\s+)?)+)\s*(?:sonra|içinde)\b"
)
_DATE_RE = re.compile(r"\b(yarın|bugün|öbür\s+gün|ertesi\s+gün)\b")
_PERIOD_RE = re.compile(r"\b(sabah|öğleden\s+sonra|öğle|öğlen|akşam|gece)\b")
_CLOCK_RE = re.compile(
    r"(?:\b(saat)\s+)?\b(\d{1,2})(?:[:.](\d{2}))?(?:\s+(buçuk))?(?:\s+(da|de|ta|te|ya|ye|a|e)\b)?"
)


def parse_natural(text: str, now: Optional[datetime] = None):
    """Doğal Türkçe hatırlatıcı isteğini çözümler.

    Dönüş: None → bu bir hatırlatıcı isteği değil;
           (due, mesaj, None) → başarı;  (None, None, hata) → anlaşılamadı.
    """
    now = now or datetime.now()
    low = _normalize(text)
    if not _TRIGGER.search(low):
        return None

    due: Optional[datetime] = None
    rest = low

    m = _REL_RE.search(low)
    if m:
        minutes = sum(int(n) * _UNIT_MIN[u]
                      for n, u in re.findall(r"(\d+)\s*(saat|sa|dakika|dk|dakka|saniye|sn|gün)", m.group(1)))
        if minutes <= 0:
            return None, None, "Süreyi anlayamadım."
        due = now + timedelta(minutes=minutes)
        rest = low[:m.start()] + " " + low[m.end():]
    else:
        date_m = _DATE_RE.search(low)
        period_m = _PERIOD_RE.search(low)
        clock = None
        for cm in _CLOCK_RE.finditer(low):
            saat, hh, mm, bucuk, suf = cm.groups()
            if not (saat or mm or suf):
                continue            # çıplak sayı — saat olduğundan emin değiliz
            clock = cm
            break
        if clock is None:
            return None, None, ("Zamanı anlayamadım. Örnek: \"20 dakika sonra hatırlat\" "
                                "ya da \"yarın 9'da beni uyandır\".")
        _, hh, mm, bucuk, _ = clock.groups()
        hh = int(hh)
        mm = int(mm) if mm else (30 if bucuk else 0)
        period = re.sub(r"\s+", " ", period_m.group(1)) if period_m else ""
        if period in ("akşam", "öğleden sonra", "gece") and 1 <= hh < 12:
            if not (period == "gece" and hh < 6):
                hh += 12
        elif period in ("öğle", "öğlen") and 1 <= hh <= 5:
            hh += 12
        if hh > 23 or mm > 59:
            return None, None, "Geçersiz saat."
        due = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        day = re.sub(r"\s+", " ", date_m.group(1)) if date_m else ""
        if day == "yarın":
            due += timedelta(days=1)
        elif day in ("öbür gün", "ertesi gün"):
            due += timedelta(days=2)
        elif due <= now:
            if day == "bugün":
                return None, None, "Bu saat bugün için geçmiş durumda."
            due += timedelta(days=1)
        spans = [clock.span()]
        if date_m:
            spans.append(date_m.span())
        if period_m:
            spans.append(period_m.span())
        chars = list(low)
        for a, b in spans:
            for k in range(a, b):
                chars[k] = " "
        rest = "".join(chars)

    words = [w for w in rest.split()
             if not re.match(r"hatırlat|uyandır", w) and w not in _NOISE]
    msg = " ".join(words).strip(" ,.-:")
    if not msg:
        msg = "Uyanma zamanı!" if re.search(r"uyandır|alarm", low) else "Hatırlatma zamanı!"
    return due, msg, None


def _when_text(due: datetime, now: Optional[datetime] = None) -> str:
    now = now or datetime.now()
    delta = int((due - now).total_seconds())
    clock = due.strftime("%H:%M")
    if delta < 3600:
        mins = max(1, round(delta / 60))
        return f"{mins} dakika sonra ({clock})"
    if due.date() == now.date():
        return f"bugün {clock}"
    if due.date() == (now + timedelta(days=1)).date():
        return f"yarın {clock}"
    return due.strftime("%d.%m.%Y %H:%M")


# ─────────────────────────────────────────────
# Kalıcı depo + zamanlayıcı
# ─────────────────────────────────────────────

class ReminderService:
    """Kalıcı hatırlatıcı listesi + zamanı gelince `on_fire` çağıran arka plan döngüsü."""

    def __init__(self, path: str = REMINDERS_PATH,
                 on_fire: Optional[Callable[[Dict], None]] = None,
                 check_seconds: float = 5.0):
        self.path = path
        self.on_fire = on_fire
        self.check_seconds = check_seconds
        self._items: List[Dict] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._load()

    # ── depo ──
    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._items = [r for r in data if isinstance(r, dict) and "due_ts" in r]
        except (OSError, ValueError):
            self._items = []

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._items, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def add(self, due: datetime, message: str) -> Dict:
        entry = {"id": uuid.uuid4().hex[:6], "due_ts": due.timestamp(),
                 "message": message, "created_ts": time.time()}
        with self._lock:
            self._items.append(entry)
            self._items.sort(key=lambda r: r["due_ts"])
            self._save()
        return entry

    def list(self) -> List[Dict]:
        with self._lock:
            return sorted(self._items, key=lambda r: r["due_ts"])

    def cancel_next(self) -> Optional[Dict]:
        with self._lock:
            if not self._items:
                return None
            nxt = min(self._items, key=lambda r: r["due_ts"])
            self._items.remove(nxt)
            self._save()
            return nxt

    def cancel_all(self) -> int:
        with self._lock:
            n = len(self._items)
            self._items = []
            self._save()
            return n

    # ── zamanlayıcı ──
    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="MehburAI-DesktopReminders",
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def pop_due(self, now: Optional[float] = None) -> List[Dict]:
        """Zamanı gelmiş kayıtları listeden çıkarıp döndürür (çok eskiler atılır)."""
        now = time.time() if now is None else now
        with self._lock:
            due = [r for r in self._items if r["due_ts"] <= now]
            if not due:
                return []
            self._items = [r for r in self._items if r["due_ts"] > now]
            self._save()
        fired = []
        for r in due:
            late = now - r["due_ts"]
            if late > MAX_MISSED_SECONDS:
                continue
            fired.append({**r, "late_seconds": late})
        return fired

    def _loop(self) -> None:
        while not self._stop.is_set():
            for r in self.pop_due():
                if self.on_fire:
                    try:
                        self.on_fire(r)
                    except Exception:
                        pass
            self._stop.wait(self.check_seconds)

    # ── sohbet / ses komutu ──
    def handle_query(self, text: str) -> Optional[str]:
        """Hatırlatıcı ile ilgili bir istekse yanıt metni, değilse None döner."""
        low = _normalize(text)
        if not re.search(r"hatırlat|alarm|uyandır", low):
            return None

        # listele (önce — "alarmlarım" iptal/kurma ile karışmasın)
        if _LIST_RE.search(low) and not _CANCEL_RE.search(low):
            return self._list_text()

        if _CANCEL_RE.search(low):
            if re.search(r"\b(tüm|bütün|hepsi\w*)\b|hatırlatıcılar|hatırlatmalar|alarmlar", low):
                n = self.cancel_all()
                return f"🗑️ {n} hatırlatıcı iptal edildi." if n else "⏰ Bekleyen hatırlatıcı yok."
            c = self.cancel_next()
            if not c:
                return "⏰ İptal edilecek bekleyen hatırlatıcı yok."
            return f"🗑️ En yakın hatırlatıcı iptal edildi: «{c['message']}»"

        parsed = parse_natural(text)
        if parsed is None:
            return None
        due, msg, err = parsed
        if err:
            return f"⚠️ {err}"
        self.add(due, msg)
        return f"⏰ Tamam, {_when_text(due)} hatırlatacağım: «{msg}»"

    def _list_text(self) -> str:
        items = self.list()
        if not items:
            return "⏰ Bekleyen hatırlatıcı yok."
        lines = ["⏰ Bekleyen hatırlatıcılar:"]
        for r in items:
            when = datetime.fromtimestamp(r["due_ts"]).strftime("%d.%m.%Y %H:%M")
            lines.append(f"• {when} — {r['message']}")
        lines.append("\nİptal için: \"alarmı iptal et\" (en yakın) ya da \"tüm hatırlatıcıları sil\".")
        return "\n".join(lines)


_service: Optional[ReminderService] = None
_service_lock = threading.Lock()


def get_reminder_service() -> ReminderService:
    """Uygulama genelinde tek ReminderService örneği."""
    global _service
    with _service_lock:
        if _service is None:
            _service = ReminderService()
        return _service
