# -*- coding: utf-8 -*-
"""
MehburAI - Telegram Uzaktan Kontrol (Remote Control Bot)
=======================================================
Cihaz sahibi, "MehburAI (Telegram)" botuna yazarak MehburAI'a uzaktan erişir:
soru sorabilir, program açtırabilir, ekran görüntüsü / kamera karesi isteyebilir,
güvenlik modunu yönetebilir — kısaca GUI'deki sohbet kutusunun yaptığı her şeyi
Telegram üzerinden yapabilir.

Güvenlik:
  • Yalnızca ayarlardaki `telegram_chat_id` (cihaz sahibi) komut verebilir.
    Başka bir sohbetten mesaj gelirse yalnızca kısa bir "bu bot özeldir" yanıtı
    döner (aynı kişiye 10 dk'da bir kez) ve komut asla işlenmez.
  • Bot yalnızca "Ayarlar > 🛡️ Güvenlik Modu > 🤖 Telegram'dan uzaktan kontrol"
    anahtarı açıkken çalışır.
  • Uzun anket (long-polling) kullanır — dinlenen bir port / web sunucusu açmaz.
  • Başlarken bota daha önce yazılmış birikmiş mesajları atlar (offset drenajı),
    böylece kapalıyken yollanan eski komutlar çalışmaz.
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Callable, List, Optional

import requests

from config import DATA_DIR, get_security_config, get_voice_config
from security_guard import CameraCapture
from system_tools import SystemTools


def _chunks(text: str, size: int = 3900) -> List[str]:
    """Telegram mesaj sınırı (4096) için metni parçalara böler."""
    text = text or ""
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


_FILE_Q_FILLERS = {"şu", "su", "bu", "o", "bir", "bana", "lütfen", "lutfen", "hemen", "the"}


def _human_size(path: str) -> str:
    try:
        n = os.path.getsize(path)
    except OSError:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _file_send_query(text: str) -> str:
    """'şu dosyayı gönder', 'ödev.docx yolla', 'rapor dosyasını yolla' → arama terimi.
    Yalnızca AÇIKÇA dosya gönderme isteği ise değer döner; değilse boş."""
    import re
    low = text.lower()
    has_verb = any(v in low for v in ("gönder", "gonder", "yolla", "yollar",
                                      "at bana", "atar mısın", "paylaş", "paylas", "ilet"))
    has_file_word = "dosya" in low or "belge" in low
    m_ext = re.search(r'\b([A-Za-zÇĞİÖŞÜçğıöşü0-9_\-]+\.[A-Za-z0-9]{1,5})\b', text)
    if not has_verb or not (has_file_word or m_ext):
        return ""
    m = re.search(r'"([^"]+)"|\'([^\']+)\'', text)
    if m:
        return (m.group(1) or m.group(2)).strip()
    if m_ext:
        return m_ext.group(1).strip()
    m = re.search(r'([A-Za-zÇĞİÖŞÜçğıöşü0-9_\-]{2,40})\s+(?:dosya|belge)', low)
    if m and m.group(1) not in _FILE_Q_FILLERS:
        return m.group(1).strip()
    return ""


HELP_TEXT = (
    "🤖 *MehburAI Uzaktan Kontrol*\n"
    "Bana normal bir mesaj yaz — GUI'deki sohbet kutusu gibi yanıtlarım "
    "(soru sor, \"not defteri aç\", \"sesi kıs\", \"bilgisayarı kapat\" ...).\n"
    "🎤 Sesli mesaj da gönderebilirsin — yazıya çevirip yanıtlarım.\n\n"
    "Özel komutlar:\n"
    "• /ekran — ekran görüntüsü gönder\n"
    "• /foto — web kameradan bir kare gönder\n"
    "• /dosya <isim> — bilgisayardan (Masaüstü…, AppData) dosya/klasör ara-gönder;\n"
    "     birden çok eşleşirse hangisini istediğini butonla sorar\n"
    "• /durum — güvenlik modu durumu\n"
    "• /guvenlik ac | /guvenlik kapat — güvenlik modunu aç/kapat\n"
    "• /aramabaslat — 🎙️ sesli görüşmeyi başlat: yazsan da sessen de yanıtı ayrıca "
    "sesli mesaj olarak da alırsın (Telegram Bot API gerçek arama/çağrı başlatamaz — "
    "bu, sesli mesaj alışverişiyle çağrı hissi veren bir moddur)\n"
    "• /aramabitir — sesli görüşmeyi bitir\n"
    "• /yardim — bu mesaj"
)

# Telegram'ın "/" menüsünde (komut listesi) görünen komutlar — bot açılırken setMyCommands ile kaydedilir
BOT_COMMANDS = [
    ("aramabaslat", "🎙️ Sesli görüşmeyi başlat"),
    ("aramabitir", "📴 Sesli görüşmeyi bitir"),
    ("ekran", "🖥️ Ekran görüntüsü gönder"),
    ("foto", "📷 Kameradan fotoğraf gönder"),
    ("dosya", "📁 Dosya ara ve gönder"),
    ("durum", "🛡️ Güvenlik modu durumu"),
    ("guvenlik", "🔒 Güvenlik modunu aç/kapat"),
    ("yardim", "❓ Komut listesi"),
]


class TelegramControlBot:
    """"MehburAI (Telegram)" botuna gelen mesajları dinleyip MehburAI'a yönlendirir."""

    API = "https://api.telegram.org"
    POLL_TIMEOUT = 50            # getUpdates long-poll süresi (sn)
    CAPTURE_DIR = os.path.join(DATA_DIR, "remote_captures")

    def __init__(
        self,
        query_handler: Callable[[str], str],
        security_status: Optional[Callable[[], str]] = None,
        security_toggle: Optional[Callable[[bool], str]] = None,
    ):
        # query_handler(text) -> yanıt metni, veya (metin, 🎨 görsel_yolu) tuple'ı
        # (AIEngine.process_query sarmalayıcısı — görsel üretim/düzenleme sonucunu taşır)
        self._query_handler = query_handler
        self._security_status = security_status
        self._security_toggle = security_toggle
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._offset: Optional[int] = None
        self._session = requests.Session()
        self._rejected: dict = {}       # yetkisiz chat_id -> son ret zamanı (spam engeli)
        self._pending_choices: dict = {}  # seçim_id -> (ts, [yol, ...]) — "hangisini?" için
        self._call_mode: bool = False   # 🎙️ /arama açıkken yanıtlar ayrıca sesli mesaj olarak da gider

    # ── kimlik bilgileri ──────────────────────
    def _creds(self):
        cfg = get_security_config()
        chat_id = (cfg.get("telegram_chat_id", "") or "").strip()
        return (cfg.get("telegram_bot_token", "").strip(), chat_id)

    def _is_owner(self, chat_id) -> bool:
        """Verilen chat ID ayarlardaki cihaz sahibi ID'sine mi ait?"""
        cid = str(chat_id or "").strip()
        owner = (get_security_config().get("telegram_chat_id", "") or "").strip()
        return bool(cid and owner and cid == owner)

    def is_configured(self) -> bool:
        token, chat_id = self._creds()
        return bool(token and chat_id)

    # ── yaşam döngüsü ─────────────────────────
    def start(self) -> bool:
        if not self.is_configured():
            return False
        # Önceki döngü hâlâ canlıysa (kapanıyor olabilir) ikinci thread açma — bayrağı geri aç
        if self._thread is not None and self._thread.is_alive():
            self._running = True
            return True
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="MehburAI-TelegramBot", daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    # ── ana döngü ─────────────────────────────
    def _register_commands(self) -> bool:
        """Komut listesini (Telegram'daki '/' menüsü) günceller — /aramabaslat dahil."""
        token, _ = self._creds()
        if not token:
            return False
        try:
            r = self._session.post(
                f"{self.API}/bot{token}/setMyCommands",
                json={"commands": [{"command": c, "description": d} for c, d in BOT_COMMANDS]},
                timeout=15,
            )
            return r.ok
        except requests.RequestException:
            return False

    def _loop(self) -> None:
        self._drain_backlog()
        self._register_commands()
        self._send("🤖 MehburAI uzaktan kontrol aktif. Komutlar için /yardim yaz.")
        while self._running:
            token, chat_id = self._creds()
            if not token or not chat_id:
                time.sleep(3)
                continue
            try:
                r = self._session.get(
                    f"{self.API}/bot{token}/getUpdates",
                    params={"timeout": self.POLL_TIMEOUT,
                            "offset": self._offset,
                            "allowed_updates": '["message","callback_query"]'},
                    timeout=self.POLL_TIMEOUT + 15,
                )
                status = r.status_code
                data = r.json()
            except (requests.RequestException, ValueError):
                time.sleep(3)
                continue

            if status in (401, 404):
                # Geçersiz / iptal edilmiş token — boşuna dövme, uzun bekle
                time.sleep(30)
                continue
            if not data.get("ok"):
                time.sleep(3)
                continue

            for upd in data.get("result", []):
                self._offset = upd["update_id"] + 1
                if not self._running:
                    break
                try:
                    self._handle_update(upd)
                except Exception:
                    pass

    def _drain_backlog(self) -> None:
        """Bot kapalıyken birikmiş eski mesajları atla (offset'i sona çek)."""
        token, _ = self._creds()
        if not token:
            return
        try:
            r = self._session.get(
                f"{self.API}/bot{token}/getUpdates",
                params={"timeout": 0, "offset": -1}, timeout=20,
            )
            result = r.json().get("result", [])
            if result:
                self._offset = result[-1]["update_id"] + 1
        except (requests.RequestException, ValueError):
            pass

    # ── gelen mesaj ──────────────────────────
    def _handle_update(self, upd: dict) -> None:
        cq = upd.get("callback_query")
        if cq:
            self._handle_callback(cq)
            return
        msg = upd.get("message") or upd.get("edited_message")
        if not msg:
            return
        chat = msg.get("chat") or {}
        cid = str(chat.get("id") or "")
        # Yetkisiz: yalnızca cihaz sahibinin chat ID'si komut verebilir (ayarlardaki ID)
        if not self._is_owner(cid):
            self._reject_stranger(cid)
            return

        # 🎤 Sesli mesaj / ses dosyası → yazıya çevir
        media = msg.get("voice") or msg.get("audio") or msg.get("video_note")
        if media:
            self._handle_voice(media)
            return

        text = (msg.get("text") or "").strip()
        if not text:
            self._send("Metin ya da sesli mesaj gönder. Komutlar için /yardim.")
            return
        self._dispatch(text)

    def _handle_voice(self, media: dict) -> None:
        cfg = get_voice_config()
        if not cfg.get("telegram_voice_enabled", True):
            self._send("🎤 Sesli mesaj işleme kapalı (Ayarlar → Sesli Sohbet).")
            return
        try:
            from voice_engine import SpeechToText
        except Exception:
            self._send("🎤 Ses tanıma bileşeni yüklü değil.")
            return

        self._chat_action("typing")
        path = self._download_file(media.get("file_id", ""), suffix=".oga")
        if not path:
            self._send("⚠️ Sesli mesaj indirilemedi.")
            return
        try:
            transcript = SpeechToText.transcribe_file(path)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

        if not transcript:
            self._send("🎤 Sesli mesajı anlayamadım, tekrar dener misin?")
            return
        self._send(f"🎤 Anladığım: «{transcript}»")
        self._dispatch(transcript)

    def _download_file(self, file_id: str, suffix: str = "") -> Optional[str]:
        """Telegram'daki bir dosyayı yerel diske indirir; yolu döndürür."""
        token, _ = self._creds()
        if not token or not file_id:
            return None
        try:
            r = self._session.get(f"{self.API}/bot{token}/getFile",
                                   params={"file_id": file_id}, timeout=20)
            fp = r.json().get("result", {}).get("file_path")
            if not fp:
                return None
            data = self._session.get(f"{self.API}/file/bot{token}/{fp}", timeout=60).content
            os.makedirs(self.CAPTURE_DIR, exist_ok=True)
            local = os.path.join(self.CAPTURE_DIR,
                                 f"tg_{int(time.time()*1000)}{suffix or os.path.splitext(fp)[1]}")
            with open(local, "wb") as f:
                f.write(data)
            return local
        except (requests.RequestException, ValueError, OSError):
            return None

    def _dispatch(self, text: str) -> None:
        # Yalnızca "/" ile başlayanlar özel komut; gerisi doğrudan zeka motoruna gider
        if text.startswith("/"):
            parts = text[1:].strip().split(None, 1)
            cmd = parts[0].lower() if parts else ""
            rest = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ("start", "yardim", "yardım", "help", "komutlar"):
                self._send(HELP_TEXT)
                return
            if cmd in ("ekran", "ss", "screenshot"):
                self._send_screenshot()
                return
            if cmd in ("foto", "fotograf", "fotoğraf", "selfie", "kamera"):
                self._send_camera()
                return
            if cmd in ("durum",):
                self._send(self._security_status() if self._security_status
                           else "Durum bilgisi mevcut değil.")
                return
            if cmd in ("guvenlik", "güvenlik"):
                if rest:
                    self._toggle_security(rest.lower())
                else:
                    self._send("Kullanım: /guvenlik ac  •  /guvenlik kapat  (durum için /durum)")
                return
            if cmd in ("dosya", "dosyagonder", "gonder", "gönder"):
                if rest:
                    self._send_file_search(rest)
                else:
                    self._send("Kullanım: /dosya <aranacak isim>  (örn. /dosya ödev)")
                return
            if cmd in ("aramabaslat", "aramabaşlat", "arama", "ara", "sesliarama", "call"):
                self._start_call()
                return
            if cmd in ("aramabitir", "aramakapat", "aramayibitir", "endcall"):
                self._end_call()
                return
            self._send(f"Bilinmeyen komut: /{cmd}\n/yardim ile komut listesini gör.")
            return

        # "şu dosyayı gönder / X dosyasını yolla" gibi doğal ifadeler
        fq = _file_send_query(text)
        if fq:
            self._send_file_search(fq)
            return

        # Düz metin → MehburAI zeka motoru (sistem araçları dahil)
        self._chat_action("typing")
        image_path = None
        try:
            answer = self._query_handler(text)
            if isinstance(answer, tuple):   # (metin, 🎨 üretilen/düzenlenen görsel yolu)
                answer, image_path = answer
        except Exception as e:
            answer = f"⚠️ İşlenemedi: {e}"

        if image_path and os.path.isfile(image_path):
            self._send_photo(image_path, caption=(answer or "")[:1024])
            if self._call_mode:
                self._send_voice_reply(answer or "")
        else:
            self._reply(answer or "(boş yanıt)")

    # ── 🎙️ Sesli görüşme modu ─────────────────
    # Not: Telegram Bot API'sinde bir botun gerçek bir sesli/görüntülü ARAMA
    # başlatması (telefonu çaldırması) mümkün değil — bu API'nin sunmadığı bir
    # yetenek. Bunun yerine "/arama" açıkken her yanıt METİN + ayrıca SESLİ
    # MESAJ olarak da gönderilir; böylece karşılıklı sesli mesajlaşmayla
    # gerçek zamanlı bir görüşmeye en yakın deneyim sağlanır.

    def _start_call(self) -> None:
        self._call_mode = True
        self._send(
            "🎙️ *Sesli görüşme modu açık.*\n"
            "Yazdığın ya da sesli gönderdiğin her mesaja artık ayrıca sesli "
            "yanıt da vereceğim. Bitirmek için /aramabitir yaz."
        )
        self._send_voice_reply("Sesli görüşme modu açık efendim, sizi dinliyorum.")

    def _end_call(self) -> None:
        was_on = self._call_mode
        self._call_mode = False
        self._send("📴 Sesli görüşme modu kapatıldı." if was_on else "Sesli görüşme modu zaten kapalıydı.")

    def _reply(self, answer: str) -> None:
        """AI yanıtını gönderir; '/arama' açıksa ayrıca sesli mesaj olarak da yollar."""
        self._send(answer)
        if self._call_mode:
            self._send_voice_reply(answer)

    def _send_voice_reply(self, text: str) -> None:
        """Metni seslendirip sesli mesaj olarak gönderir (yalnızca çağrı modunda)."""
        try:
            from voice_engine import TextToSpeech, _speakable
        except Exception:
            return
        if not TextToSpeech.is_available():
            return
        spoken = _speakable(text)
        if not spoken:
            return
        os.makedirs(self.CAPTURE_DIR, exist_ok=True)
        path = os.path.join(self.CAPTURE_DIR, f"tg_voice_{int(time.time()*1000)}.mp3")
        try:
            if not TextToSpeech.synth_to_file(spoken, path):
                return
            self._send_voice_note(path)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    def _send_voice_note(self, path: str) -> bool:
        """Bir ses dosyasını Telegram'a sesli mesaj (sendVoice) olarak gönderir;
        istemci reddederse normal ses dosyası (sendAudio) olarak yollar."""
        token, chat_id = self._creds()
        if not (token and chat_id and path and os.path.isfile(path)):
            return False
        self._chat_action("record_voice")
        try:
            with open(path, "rb") as f:
                r = self._session.post(
                    f"{self.API}/bot{token}/sendVoice",
                    data={"chat_id": chat_id},
                    files={"voice": f}, timeout=60,
                )
            if r.ok:
                return True
        except (requests.RequestException, OSError):
            pass
        try:
            with open(path, "rb") as f:
                r = self._session.post(
                    f"{self.API}/bot{token}/sendAudio",
                    data={"chat_id": chat_id, "title": "MehburAI"},
                    files={"audio": f}, timeout=60,
                )
            return r.ok
        except (requests.RequestException, OSError):
            return False

    def _toggle_security(self, arg: str) -> None:
        if not self._security_toggle:
            self._send("Güvenlik modu bu sürümde uzaktan değiştirilemiyor.")
            return
        want = arg in ("ac", "aç", "aktif", "on", "1", "true", "baslat", "başlat")
        off = arg in ("kapat", "kapa", "durdur", "off", "0", "false")
        if not want and not off:
            self._send("Kullanım: /guvenlik ac  •  /guvenlik kapat")
            return
        self._send(self._security_toggle(want))

    # ── giden mesaj / medya ──────────────────
    def _send(self, text: str) -> None:
        """Cihaz sahibine (ayarlardaki chat_id) mesaj gönderir."""
        _, owner = self._creds()
        self._send_to(owner, text)

    def _send_to(self, chat_id: str, text: str) -> None:
        token = self._creds()[0]
        if not token or not chat_id or not text:
            return
        for chunk in _chunks(text):
            try:
                self._session.post(
                    f"{self.API}/bot{token}/sendMessage",
                    data={"chat_id": chat_id, "text": chunk},
                    timeout=20,
                )
            except requests.RequestException:
                pass

    def _reject_stranger(self, chat_id: str) -> None:
        """Yetkisiz sohbete kısa bir ret mesajı gönderir (aynı kişiye 10 dk'da bir kez —
        botun spam aracına dönüşmemesi için)."""
        if not chat_id:
            return
        now = time.time()
        if now - self._rejected.get(chat_id, 0) < 600:
            return
        self._rejected[chat_id] = now
        if len(self._rejected) > 300:   # sözlük şişmesin
            self._rejected = {k: v for k, v in self._rejected.items() if now - v < 600}
        self._send_to(chat_id, "⛔ Bu bot özeldir. Yalnızca sahibi kullanabilir.")

    def _chat_action(self, action: str = "typing") -> None:
        token, chat_id = self._creds()
        if not token or not chat_id:
            return
        try:
            self._session.post(
                f"{self.API}/bot{token}/sendChatAction",
                data={"chat_id": chat_id, "action": action}, timeout=10,
            )
        except requests.RequestException:
            pass

    def _send_photo(self, path: str, caption: str = "", cleanup: bool = False) -> None:
        token, chat_id = self._creds()
        if not (token and chat_id and path and os.path.isfile(path)):
            self._send("⚠️ Gönderilecek görüntü oluşturulamadı.")
            return
        self._chat_action("upload_photo")
        try:
            with open(path, "rb") as f:
                self._session.post(
                    f"{self.API}/bot{token}/sendPhoto",
                    data={"chat_id": chat_id, "caption": caption[:1024]},
                    files={"photo": f}, timeout=60,
                )
        except (requests.RequestException, OSError):
            self._send("⚠️ Fotoğraf gönderilemedi.")
        finally:
            if cleanup:
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _send_screenshot(self) -> None:
        path = SystemTools.save_screenshot(dest_dir=self.CAPTURE_DIR)
        if not path:
            self._send("⚠️ Ekran görüntüsü alınamadı (Pillow kütüphanesi gerekli olabilir).")
            return
        stamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self._send_photo(path, f"🖥️ Ekran görüntüsü — {stamp}", cleanup=True)

    def _send_camera(self) -> None:
        self._send("📸 Kamera karesi alınıyor...")
        path = CameraCapture.snapshot()
        if not path:
            self._send("⚠️ Web kamerasından görüntü alınamadı (kamera yok / OpenCV kurulu değil).")
            return
        stamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        self._send_photo(path, f"📷 Kamera — {stamp}")

    def _send_document(self, path: str, caption: str = "") -> bool:
        token, chat_id = self._creds()
        if not (token and chat_id and path and os.path.isfile(path)):
            return False
        if os.path.getsize(path) > 48 * 1024 * 1024:   # Bot API sınırı ~50 MB
            self._send(f"⚠️ '{os.path.basename(path)}' çok büyük (>48 MB), gönderilemiyor.")
            return False
        self._chat_action("upload_document")
        try:
            with open(path, "rb") as f:
                r = self._session.post(
                    f"{self.API}/bot{token}/sendDocument",
                    data={"chat_id": chat_id, "caption": caption[:1024]},
                    files={"document": (os.path.basename(path), f)}, timeout=180,
                )
            return r.ok
        except (requests.RequestException, OSError):
            return False

    def _send_file_search(self, term: str) -> None:
        term = term.strip().strip('"\'').strip()
        if len(term) < 2:
            self._send("Kullanım: /dosya <aranacak isim>  (en az 2 harf)")
            return
        self._send(f"🔍 '{term}' aranıyor (Masaüstü, Belgeler, İndirilenler, Resimler, "
                   "Video, Müzik, AppData)...")
        self._chat_action("upload_document")
        try:
            matches = SystemTools.locate_files(term, limit=12, files_only=False,
                                               include_appdata=True)
        except Exception as e:
            self._send(f"⚠️ Arama hatası: {e}")
            return
        if not matches:
            self._send(f"🔍 '{term}' ile eşleşen dosya/klasör bulunamadı.")
            return
        if len(matches) == 1:
            self._deliver_path(matches[0])
            return
        # Tek bir TAM ad eşleşmesi varsa doğrudan gönder
        exact = [p for p in matches if os.path.basename(p).lower() == term.lower()]
        if len(exact) == 1:
            self._deliver_path(exact[0])
            return
        self._offer_choices(term, matches)

    def _offer_choices(self, term: str, matches: list) -> None:
        """Birden çok eşleşme → 'hangisini istersin?' butonları."""
        now = time.time()
        # eski seçimleri temizle (1 saat)
        self._pending_choices = {k: v for k, v in self._pending_choices.items()
                                 if now - v[0] < 3600}
        choice_id = f"{int(now * 1000) % 1000000}"
        self._pending_choices[choice_id] = (now, list(matches))

        def _tag(p):
            return "📁" if os.path.isdir(p) else "📄"

        lines, buttons = [], []
        for i, p in enumerate(matches):
            root = os.path.dirname(p)
            if len(root) > 46:
                root = "…" + root[-45:]
            lines.append(f"{i + 1}. {_tag(p)} {os.path.basename(p)}\n     {root}")
            label = f"{i + 1}. {_tag(p)} {os.path.basename(p)}"
            buttons.append([{"text": label[:60], "callback_data": f"f|{choice_id}|{i}"}])
        buttons.append([{"text": "✖️ Vazgeç", "callback_data": f"f|{choice_id}|x"}])

        self._send_with_keyboard(
            f"🔍 '{term}' için {len(matches)} eşleşme — hangisini istersin?\n\n"
            + "\n".join(lines),
            {"inline_keyboard": buttons},
        )

    def _handle_callback(self, cq: dict) -> None:
        cq_id = cq.get("id", "")
        frm = str((cq.get("from") or {}).get("id") or "")
        token = self._creds()[0]
        if not self._is_owner(frm):
            if token and cq_id:
                try:
                    self._session.post(f"{self.API}/bot{token}/answerCallbackQuery",
                                       data={"callback_query_id": cq_id,
                                             "text": "⛔ Yetkisiz"}, timeout=10)
                except requests.RequestException:
                    pass
            return

        data = cq.get("data", "")
        msg = cq.get("message") or {}
        mid = msg.get("message_id")
        chat_id = str((msg.get("chat") or {}).get("id") or "")

        def _answer(text=""):
            if token and cq_id:
                try:
                    self._session.post(f"{self.API}/bot{token}/answerCallbackQuery",
                                       data={"callback_query_id": cq_id, "text": text[:180]},
                                       timeout=10)
                except requests.RequestException:
                    pass

        def _strip_keyboard(new_text=None):
            if not (token and chat_id and mid):
                return
            try:
                if new_text is not None:
                    self._session.post(f"{self.API}/bot{token}/editMessageText",
                                       data={"chat_id": chat_id, "message_id": mid,
                                             "text": new_text}, timeout=10)
                else:
                    self._session.post(f"{self.API}/bot{token}/editMessageReplyMarkup",
                                       data={"chat_id": chat_id, "message_id": mid,
                                             "reply_markup": json.dumps({"inline_keyboard": []})},
                                       timeout=10)
            except requests.RequestException:
                pass

        parts = data.split("|")
        if len(parts) != 3 or parts[0] != "f":
            _answer()
            return
        _, choice_id, idx = parts
        entry = self._pending_choices.get(choice_id)
        if idx == "x":
            _answer("İptal edildi")
            _strip_keyboard("✖️ Vazgeçildi.")
            self._pending_choices.pop(choice_id, None)
            return
        if not entry:
            _answer("Bu seçim listesi artık geçerli değil — /dosya ile tekrar ara.")
            _strip_keyboard()
            return
        try:
            path = entry[1][int(idx)]
        except (ValueError, IndexError):
            _answer("Geçersiz seçim.")
            return
        self._pending_choices.pop(choice_id, None)
        _answer("Gönderiliyor…")
        _strip_keyboard(f"📎 Seçildi: {os.path.basename(path)}")
        self._deliver_path(path)

    def _send_with_keyboard(self, text: str, reply_markup: dict) -> None:
        token, chat_id = self._creds()
        if not token or not chat_id:
            return
        try:
            self._session.post(
                f"{self.API}/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": text[:4000],
                      "reply_markup": json.dumps(reply_markup)},
                timeout=20,
            )
        except requests.RequestException:
            pass

    def _deliver_path(self, path: str) -> None:
        """Tek bir eşleşmeyi gönderir: dosyaysa doğrudan, klasörse .zip yapıp."""
        if os.path.isdir(path):
            self._send(f"📁 '{os.path.basename(path)}' bir klasör — sıkıştırılıyor...")
            self._chat_action("upload_document")
            zpath, msg = SystemTools.zip_folder(path)
            if not zpath:
                self._send(f"⚠️ {msg}")
                return
            self._send(f"📦 Gönderiliyor: {os.path.basename(path)}.zip  "
                       f"({_human_size(zpath)}, {msg})")
            ok = self._send_document(zpath, "")
            try:
                os.remove(zpath)
            except OSError:
                pass
            if not ok:
                self._send("⚠️ Arşiv gönderilemedi (48 MB sınırını aşıyor olabilir).")
            return
        if os.path.isfile(path):
            self._send(f"📎 Gönderiliyor: {os.path.basename(path)}  ({_human_size(path)})")
            if not self._send_document(path, os.path.dirname(path)):
                self._send("⚠️ Dosya gönderilemedi (çok büyük olabilir ya da erişilemedi).")
            return
        self._send("⚠️ Yol artık mevcut değil.")


# ─────────────────────────────────────────────
# Bağımsız Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import io
    import sys

    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("MehburAI Telegram Uzaktan Kontrol — hızlı test")
    bot = TelegramControlBot(
        query_handler=lambda t: f"(test yankı) {t}",
        security_status=lambda: "🟢 test durumu",
        security_toggle=lambda w: f"güvenlik {'açıldı' if w else 'kapandı'} (test)",
    )
    print("Telegram yapılandırılmış mı:", bot.is_configured())
    if bot.is_configured():
        print("Dinleme başlatılıyor (Ctrl+C ile çık)...")
        bot.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            bot.stop()
