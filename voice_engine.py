# -*- coding: utf-8 -*-
"""
MehburAI - Sesli Sohbet Motoru (Voice Engine)
=============================================
İki bağımsız yetenek sağlar:

1. Yerel Sesli Asistan (yalnız bu bilgisayarda)
   • Mikrofonu sürekli dinler (Vosk — çevrimdışı Türkçe STT).
   • Yalnızca "Hey Mehbur" uyandırma sözcüğünü (yazım/duyum hatasına
     toleranslı — "hey melbur", "he mecbur" ...) duyunca "Emrinizdeyim
     efendim" der (edge-tts — doğal ses). Yalın "Mehbur" tek başına
     uyandırmaz — rastgele konuşmadaki benzer kelimelerle (mecbur, mahmut,
     mehmet ...) karışıp yanlış tetiklenmeyi azaltmak için.
   • Ardından komutu dinler, MehburAI zeka motoruna verir, yanıtı seslendirir.

2. STT yardımcıları (Telegram sesli mesajları için)
   • `SpeechToText.transcribe_file()` bir ses dosyasını (ogg/opus, mp3, wav…)
     yazıya çevirir.

Bağımlılıklar (opsiyonel — yoksa özellik sessizce devre dışı kalır):
   vosk, sounddevice, soundfile, edge-tts, numpy
İlk kullanımda ~35 MB Türkçe Vosk modeli `data/models/` altına indirilir.
"""

import asyncio
import difflib
import json
import os
import queue
import threading
import time
import zipfile
from io import BytesIO
from typing import Callable, List, Optional

from config import DATA_DIR, get_voice_config

# ── Opsiyonel bağımlılıklar ───────────────────
try:
    import numpy as np
except Exception:
    np = None

try:
    import sounddevice as sd
except Exception:
    sd = None

try:
    import soundfile as sf
except Exception:
    sf = None

try:
    import vosk
    vosk.SetLogLevel(-1)
except Exception:
    vosk = None

try:
    import edge_tts
except Exception:
    edge_tts = None

try:
    import requests
except Exception:
    requests = None


SAMPLE_RATE = 16000
# Yalnızca "Hey Mehbur" uyandırır — yalın "Mehbur" (rastgele konuşmada "mecbur",
# "mahmut", "mehmet" gibi kelimelerle çok kolay karışıyordu) artık TEK BAŞINA
# uyandırmaz; bu sayede "hiç söylemediğim halde arada açılıyor" sorunu azalır.
WAKE_WORDS = ("hey mehbur",)
WAKE_RESPONSE = "Emrinizdeyim efendim."


def voice_dependencies_ok() -> bool:
    return all(x is not None for x in (np, sd, sf, vosk, edge_tts))


def missing_dependencies() -> List[str]:
    names = {"numpy": np, "sounddevice": sd, "soundfile": sf,
             "vosk": vosk, "edge-tts": edge_tts}
    return [n for n, mod in names.items() if mod is None]


# ─────────────────────────────────────────────
# Konuşma → Yazı (Vosk, çevrimdışı Türkçe)
# ─────────────────────────────────────────────

class SpeechToText:
    MODEL_NAME = "vosk-model-small-tr-0.3"
    MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
    MODEL_DIR = os.path.join(DATA_DIR, "models", MODEL_NAME)

    _model = None
    _lock = threading.Lock()

    @classmethod
    def model_present(cls) -> bool:
        if not os.path.isdir(cls.MODEL_DIR):
            return False
        # Vosk modelleri iki düzende gelebilir: klasik (am/final.mdl) veya
        # grafik-tabanlı küçük model (kökte final.mdl + HCLr.fst).
        return (os.path.isfile(os.path.join(cls.MODEL_DIR, "am", "final.mdl"))
                or os.path.isfile(os.path.join(cls.MODEL_DIR, "final.mdl")))

    @classmethod
    def ensure_model(cls, progress: Optional[Callable[[str], None]] = None) -> bool:
        """Model yoksa indirir + açar. Başarılıysa True."""
        if cls.model_present():
            return True
        if requests is None:
            return False
        try:
            if progress:
                progress("Türkçe ses modeli indiriliyor (~35 MB)...")
            os.makedirs(os.path.dirname(cls.MODEL_DIR), exist_ok=True)
            r = requests.get(cls.MODEL_URL, timeout=180)
            r.raise_for_status()
            if progress:
                progress("Ses modeli açılıyor...")
            with zipfile.ZipFile(BytesIO(r.content)) as z:
                z.extractall(os.path.dirname(cls.MODEL_DIR))
            return cls.model_present()
        except Exception:
            return False

    @classmethod
    def get_model(cls):
        if vosk is None:
            return None
        with cls._lock:
            if cls._model is None:
                if not cls.ensure_model():
                    return None
                cls._model = vosk.Model(cls.MODEL_DIR)
        return cls._model

    @classmethod
    def is_available(cls) -> bool:
        return vosk is not None and (cls.model_present() or requests is not None)

    @classmethod
    def transcribe_pcm16(cls, pcm_bytes: bytes) -> str:
        model = cls.get_model()
        if model is None:
            return ""
        rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
        rec.AcceptWaveform(pcm_bytes)
        try:
            return (json.loads(rec.FinalResult()).get("text") or "").strip()
        except (ValueError, AttributeError):
            return ""

    @classmethod
    def transcribe_file(cls, path: str) -> str:
        """ogg/opus, mp3, wav… bir ses dosyasını yazıya çevirir."""
        if sf is None or np is None:
            return ""
        try:
            data, sr = sf.read(path, dtype="int16", always_2d=True)
        except Exception:
            return ""
        data = data[:, 0]  # mono
        if sr != SAMPLE_RATE and len(data):
            idx = (np.arange(int(len(data) * SAMPLE_RATE / sr)) * sr / SAMPLE_RATE).astype(int)
            idx = idx[idx < len(data)]
            data = data[idx]
        return cls.transcribe_pcm16(data.astype("<i2").tobytes())


# ─────────────────────────────────────────────
# Yazı → Konuşma (edge-tts, doğal ses)
# ─────────────────────────────────────────────

class TextToSpeech:
    DEFAULT_VOICE = "tr-TR-EmelNeural"     # sıcak kadın ses (Grok "Ara" benzeri)
    _play_lock = threading.Lock()

    @classmethod
    def _voice(cls) -> str:
        v = (get_voice_config().get("voice_tts_voice") or "").strip()
        return v or cls.DEFAULT_VOICE

    @classmethod
    def synth_to_file(cls, text: str, path: str, voice: Optional[str] = None) -> bool:
        if edge_tts is None or not text.strip():
            return False

        async def _run():
            await edge_tts.Communicate(text, voice or cls._voice()).save(path)

        try:
            asyncio.run(_run())
            return os.path.isfile(path) and os.path.getsize(path) > 0
        except Exception:
            return False

    @classmethod
    def speak(cls, text: str, voice: Optional[str] = None, blocking: bool = True) -> None:
        """Metni seslendirir ve hoparlörden çalar."""
        if not text or not text.strip() or sd is None or sf is None:
            return
        tmp = os.path.join(DATA_DIR, "remote_captures",
                           f"tts_{int(time.time()*1000)}.mp3")
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        if not cls.synth_to_file(text, tmp, voice):
            return

        def _play():
            with cls._play_lock:
                try:
                    data, sr = sf.read(tmp, dtype="float32", always_2d=True)
                    sd.play(data, sr)
                    sd.wait()
                except Exception:
                    pass
                finally:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass

        if blocking:
            _play()
        else:
            threading.Thread(target=_play, daemon=True, name="MehburAI-TTS").start()

    @classmethod
    def is_available(cls) -> bool:
        return None not in (edge_tts, sd, sf)


# ─────────────────────────────────────────────
# Uyandırma sözcüğü eşleştirme (hataya toleranslı)
# ─────────────────────────────────────────────

def _norm(s: str) -> str:
    table = str.maketrans("çğıöşü", "cgiosu")
    return (s or "").lower().translate(table)


_HEY_TOKENS = ("hey", "he", "ey", "hei", "yey")
_MEHBUR_TARGETS = ("mehbur", "mehbura", "mehburai")


def _is_hey_token(word: str) -> bool:
    return _norm(word) in _HEY_TOKENS


def _is_mehbur_token(word: str) -> bool:
    w = _norm(word)
    if len(w) < 4:
        return False
    for tgt in _MEHBUR_TARGETS:
        if abs(len(w) - len(tgt)) <= 2 and w[0] == tgt[0]:
            if difflib.SequenceMatcher(None, w, tgt).ratio() >= 0.72:
                return True
    return False


def contains_wake_word(text: str) -> bool:
    """Yalnızca **'Hey Mehbur'** (ardışık iki kelime) uyandırır — yazım/duyum
    hatasına toleranslı ('hey melbur', 'he mecbur', 'heymehbur' ...), ama tek
    başına 'mehbur' / 'mecbur' artık uyandırmaz (rastgele konuşmadaki benzer
    kelimelerle karışıp yanlış tetiklenmeyi azaltmak için)."""
    t = _norm(text)
    if not t:
        return False
    words = t.replace(",", " ").replace(".", " ").split()

    for i in range(len(words) - 1):
        if _is_hey_token(words[i]) and _is_mehbur_token(words[i + 1]):
            return True

    # Bitişik yazılmış/duyulmuş biçim: "heymehbur"
    for w in words:
        if len(w) >= 8 and w.startswith(("hey", "he")):
            rest = w[3:] if w.startswith("hey") else w[2:]
            if _is_mehbur_token(rest):
                return True

    return False


def _is_wakeish_token(word: str) -> bool:
    w = _norm(word)
    if w in _HEY_TOKENS or w == "ai":
        return True
    if _is_mehbur_token(word):
        return True
    for tgt in ("mecbur", "melbur"):
        if abs(len(w) - len(tgt)) <= 2 and w[:1] == tgt[:1] \
                and difflib.SequenceMatcher(None, w, tgt).ratio() >= 0.7:
            return True
    return False


def strip_wake_word(text: str) -> str:
    """Komut metninden baştaki uyandırma sözcüğünü / 'hey' / 'ai' kalıntısını ayıklar."""
    words = text.split()
    while words and _is_wakeish_token(words[0]):
        words.pop(0)
    return " ".join(words).strip()


# ─────────────────────────────────────────────
# Yerel Sesli Asistan (her zaman dinler)
# ─────────────────────────────────────────────

class VoiceAssistant:
    """
    Mikrofonu sürekli dinler; uyandırma sözcüğünü duyunca komut alır ve
    `on_command(text) -> yanıt` çağrısının sonucunu seslendirir.
    Yalnızca bu bilgisayarda çalışır (Telegram'la ilgisi yoktur).
    """

    SILENCE_RMS = 320          # bu değerin altı "sessizlik"
    END_SILENCE = 1.1          # komut sonu için gereken sessizlik (sn)
    MAX_COMMAND = 12.0         # en fazla komut süresi (sn)

    def __init__(self, on_command: Callable[[str], str],
                 on_state: Optional[Callable[..., None]] = None):
        self._on_command = on_command
        # on_state(state, text="") — state: dinliyor | uyandi | komut_dinliyor |
        #   islemde | yanit | model_yok | mikrofon_hatasi | kapali
        self._on_state = on_state or (lambda *a, **k: None)
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._audio_q: "queue.Queue[bytes]" = queue.Queue()
        self._muted = threading.Event()   # TTS konuşurken mikrofonu yok say
        self._paused = threading.Event()  # 🎤 bas-konuş yazdırma sırasında yok say

    def pause(self) -> None:
        self._paused.set()
        self._drain_queue()

    def resume(self) -> None:
        self._drain_queue()
        self._paused.clear()

    # ── yaşam döngüsü ──
    def start(self) -> bool:
        if self._running:
            return True
        if not voice_dependencies_ok():
            return False
        self._running = True
        self._thread = threading.Thread(target=self._run, name="MehburAI-Voice", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    # ── mikrofon geri çağrısı ──
    def _mic_cb(self, indata, frames, time_info, status):  # noqa: ARG002
        if not self._muted.is_set() and not self._paused.is_set():
            self._audio_q.put(bytes(indata))

    # ── ana döngü ──
    def _run(self) -> None:
        model = SpeechToText.get_model()
        if model is None:
            self._on_state("model_yok")
            self._running = False
            return

        rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
        self._on_state("dinliyor")
        try:
            with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000,
                                   dtype="int16", channels=1, callback=self._mic_cb):
                while self._running:
                    try:
                        chunk = self._audio_q.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    if rec.AcceptWaveform(chunk):
                        text = json.loads(rec.Result()).get("text", "")
                    else:
                        text = json.loads(rec.PartialResult()).get("partial", "")
                    if text and contains_wake_word(text):
                        rec.Reset()
                        self._handle_wake(text)
                        self._drain_queue()
        except Exception:
            self._on_state("mikrofon_hatasi")
        finally:
            self._running = False
            self._on_state("kapali")

    def _drain_queue(self) -> None:
        try:
            while True:
                self._audio_q.get_nowait()
        except queue.Empty:
            pass

    # ── uyandırma sonrası ──
    def _handle_wake(self, wake_text: str) -> None:
        self._on_state("uyandi")
        self._speak(WAKE_RESPONSE)

        # Uyandırma sözcüğüyle aynı cümlede komut da verilmiş olabilir
        inline = strip_wake_word(wake_text)
        command = inline or self._listen_for_command()
        if not command:
            # Yanlış tetiklenme / sessizlik — sessizce dinlemeye dön (rahatsız etme)
            self._on_state("dinliyor")
            return

        self._on_state("islemde", command)
        try:
            reply = self._on_command(command) or ""
        except Exception:
            reply = "Bir hata oluştu efendim."
        spoken = _speakable(reply)
        self._on_state("yanit", spoken)
        self._speak(spoken)
        self._on_state("dinliyor")

    def _listen_for_command(self) -> str:
        """Uyandırmadan sonra sessizliğe kadar konuşmayı kaydeder ve yazıya çevirir."""
        self._on_state("komut_dinliyor")
        model = SpeechToText.get_model()
        rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
        self._drain_queue()
        started = time.time()
        last_voice = time.time()
        heard_any = False
        pcm = bytearray()

        while self._running and time.time() - started < self.MAX_COMMAND:
            try:
                chunk = self._audio_q.get(timeout=0.4)
            except queue.Empty:
                if heard_any and time.time() - last_voice > self.END_SILENCE:
                    break
                continue
            pcm += chunk
            if np is not None:
                samples = np.frombuffer(chunk, dtype="<i2")
                rms = float(np.sqrt(np.mean(samples.astype("float32") ** 2))) if len(samples) else 0.0
            else:
                rms = self.SILENCE_RMS + 1
            if rms > self.SILENCE_RMS:
                heard_any = True
                last_voice = time.time()
            elif heard_any and time.time() - last_voice > self.END_SILENCE:
                break

        rec.AcceptWaveform(bytes(pcm))
        text = (json.loads(rec.FinalResult()).get("text") or "").strip()
        return strip_wake_word(text)

    # ── seslendirme (mikrofonu bu sırada sustur) ──
    def _speak(self, text: str) -> None:
        if not text:
            return
        self._muted.set()
        try:
            TextToSpeech.speak(text, blocking=True)
        finally:
            time.sleep(0.15)
            self._drain_queue()
            self._muted.clear()


# ─────────────────────────────────────────────
# 🎤 Bas-Konuş Yazdırma (sohbet kutusundaki mikrofon butonu)
# ─────────────────────────────────────────────

class Dictation:
    """
    Mikrofonu BİR KEZ dinleyip konuşmayı yazıya çevirir (uyandırma sözcüğü gerekmez).
      on_partial(text) — konuşurken anlık metin
      on_done(text, error) — bitince nihai metin (boş olabilir); mikrofon/model hatasında
                             error dolu ("mic" | "model" | "deps")
    Konuşma bitince (Vosk uç-nokta tespiti), 8 sn hiç konuşulmazsa, 20 sn dolarsa
    ya da `stop()` çağrılırsa (o ana kadar duyulanla) biter.
    """

    NO_SPEECH_TIMEOUT = 8.0
    MAX_SECONDS = 20.0

    def __init__(self, on_partial: Optional[Callable[[str], None]] = None,
                 on_done: Optional[Callable[[str, str], None]] = None):
        self._on_partial = on_partial or (lambda t: None)
        self._on_done = on_done or (lambda t, e: None)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if self.is_running():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="MehburAI-Dictation", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        text, error = "", ""
        try:
            if not voice_dependencies_ok():
                error = "deps"
                return
            model = SpeechToText.get_model()
            if model is None:
                error = "model"
                return
            rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
            q: "queue.Queue[bytes]" = queue.Queue()

            def cb(indata, frames, time_info, status):  # noqa: ARG001
                q.put(bytes(indata))

            started = time.time()
            heard = False
            last_partial = ""
            try:
                with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000,
                                       dtype="int16", channels=1, callback=cb):
                    while not self._stop.is_set():
                        if time.time() - started > self.MAX_SECONDS:
                            break
                        if not heard and time.time() - started > self.NO_SPEECH_TIMEOUT:
                            break
                        try:
                            chunk = q.get(timeout=0.3)
                        except queue.Empty:
                            continue
                        if rec.AcceptWaveform(chunk):
                            t = (json.loads(rec.Result()).get("text") or "").strip()
                            if t:
                                text = t
                                break
                        else:
                            p = (json.loads(rec.PartialResult()).get("partial") or "").strip()
                            if p:
                                heard = True
                                if p != last_partial:
                                    last_partial = p
                                    self._on_partial(p)
            except Exception:
                error = "mic"
                return
            if not text:
                text = (json.loads(rec.FinalResult()).get("text") or "").strip() or last_partial
        except Exception:
            error = error or "mic"
        finally:
            self._on_done(text, error)


# ─────────────────────────────────────────────
# 📞 JARVIS Görüşmesi (sohbet kutusundaki telefon butonu)
# ─────────────────────────────────────────────

CALL_END_PHRASES = ("görüşmeyi bitir", "görüşmeyi kapat", "aramayı bitir", "aramayı kapat",
                    "görüşürüz", "hoşça kal", "hoşçakal", "kapat jarvis", "jarvis kapat",
                    "tamam bu kadar", "bu kadar yeter")


def is_call_end_phrase(text: str) -> bool:
    t = _norm(text)
    return any(_norm(p) in t for p in CALL_END_PHRASES)


class JarvisCall:
    """
    Eller serbest sesli görüşme: "Emrinizdeyim efendim" der, sonra sırayla
    dinle → düşün (`on_command(text) -> yanıt`) → yanıtı seslendir döngüsüne girer.
    Uyandırma sözcüğü gerekmez. `stop()`, "görüşmeyi bitir / görüşürüz" denmesi ya da
    art arda 3 kez hiç konuşulmaması görüşmeyi bitirir.

    on_state(state, text="") — state: karsilama | dinliyor | duyuyor | islemde | yanit |
        veda | hata (text: "mic" | "model" | "deps")
    on_end() — görüşme bittiğinde (her durumda, bir kez) çağrılır.
    Mikrofon konuşma sırasında kapalıdır (Dictation her tur açıp kapatır) → kendini duymaz.
    """

    MAX_SILENT_TURNS = 3

    def __init__(self, on_command: Callable[[str], str],
                 on_state: Optional[Callable[..., None]] = None,
                 on_end: Optional[Callable[[], None]] = None):
        self._on_command = on_command
        self._on_state = on_state or (lambda *a, **k: None)
        self._on_end = on_end or (lambda: None)
        self._stop = threading.Event()
        self._dictation: Optional[Dictation] = None
        self._thread: Optional[threading.Thread] = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if self.is_running():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="MehburAI-Call", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        d = self._dictation
        if d is not None:
            d.stop()
        try:
            if sd is not None:
                sd.stop()       # konuşan yanıtı hemen kes
        except Exception:
            pass

    def _say(self, text: str) -> None:
        if text and not self._stop.is_set():
            TextToSpeech.speak(text, blocking=True)

    def _listen_turn(self) -> tuple:
        """Bir konuşma dinler → (metin, hata)."""
        done = threading.Event()
        box = {"text": "", "error": ""}

        def on_done(t, e):
            box["text"], box["error"] = t, e
            done.set()

        self._dictation = Dictation(on_partial=lambda t: self._on_state("duyuyor", t), on_done=on_done)
        self._dictation.start()
        while not done.wait(0.2):
            if self._stop.is_set():
                self._dictation.stop()
        self._dictation = None
        return box["text"], box["error"]

    def _run(self) -> None:
        try:
            if not voice_dependencies_ok():
                self._on_state("hata", "deps")
                return
            self._on_state("karsilama", WAKE_RESPONSE)
            self._say(WAKE_RESPONSE)
            silent = 0
            while not self._stop.is_set():
                self._on_state("dinliyor")
                text, error = self._listen_turn()
                if self._stop.is_set():
                    break
                if error:
                    self._on_state("hata", error)
                    return
                text = strip_wake_word(text)
                if not text:
                    silent += 1
                    if silent >= self.MAX_SILENT_TURNS:
                        self._on_state("veda", "Sesinizi duyamadım, görüşmeyi sonlandırıyorum efendim.")
                        self._say("Sesinizi duyamadım, görüşmeyi sonlandırıyorum efendim.")
                        return
                    continue
                silent = 0
                if is_call_end_phrase(text):
                    self._on_state("veda", "Görüşmek üzere efendim.")
                    self._say("Görüşmek üzere efendim.")
                    return
                self._on_state("islemde", text)
                try:
                    reply = self._on_command(text) or ""
                except Exception:
                    reply = "Bir hata oluştu efendim."
                spoken = _speakable(reply) or "Yanıt üretemedim efendim."
                self._on_state("yanit", spoken)
                self._say(spoken)
        except Exception:
            self._on_state("hata", "mic")
        finally:
            self._on_end()


def _speakable(text: str) -> str:
    """Markdown / emoji / bağlantı kalabalığını seslendirmeye uygun sadeleştirir."""
    import re
    t = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    t = re.sub(r"[*_#>|]", "", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"[📸📁📄🚀⚙️💻🕒🔒🛡️🤖⚡✅⚠️🔇🔊🔉😴🌑☀️👋🌟💡🔄]", "", t)
    t = re.sub(r"\n{2,}", ". ", t).replace("\n", " ")
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t[:600]


# ─────────────────────────────────────────────
# Bağımsız Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import io

    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("Bağımlılıklar tam mı:", voice_dependencies_ok(), "| eksik:", missing_dependencies())
    print("Uyandırma testi (yalnızca 'Hey Mehbur' uyandırmalı):")
    for s in ["hey mehbur saat kaç", "he mecbur bilgisayarı kapat",
              "hey melbur ışıkları aç", "mehbur saat kaç", "bugün hava nasıl",
              "mahmut gel", "mehmet nerede"]:
        print(f"  {s!r:40} -> {contains_wake_word(s)}  komut={strip_wake_word(s)!r}")

    if voice_dependencies_ok():
        print("\nModel indiriliyor / yükleniyor...")
        if SpeechToText.ensure_model(print):
            print("Model hazır. 'Emrinizdeyim efendim' seslendiriliyor...")
            TextToSpeech.speak(WAKE_RESPONSE)
            print("5 sn boyunca mikrofon dinleniyor, 'mehbur' de...")
            va = VoiceAssistant(on_command=lambda t: f"Şunu dediniz: {t}",
                                on_state=lambda s, txt="": print("  [durum]", s, txt))
            va.start()
            time.sleep(20)
            va.stop()
