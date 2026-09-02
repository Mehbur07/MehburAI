# -*- coding: utf-8 -*-
"""
MehburAI - Yapay Zeka Karar ve Üretim Motoru (AI Engine)
==========================================================
MehburAI'nin ana zeka modülü. Ağ durumuna göre dinamik olarak:
  1. Selamlaşma Filtresi: Basit selam ve sohbetleri anında yanıtlar.
  2. Çevrimiçi Mod (Online):
     - Wikipedia / Güvenilir kaynaklardan gerçek bilgi özeti çeker.
     - Google Gemini API ile akıcı ve doğru yanıt üretir.
     - Üretilen her yanıtı otomatik olarak `memory_engine` hafızasına kaydeder.
  3. Çevrimdışı Mod (Offline):
     - Hafızadaki öğrenilmiş bilgileri semantik benzerlikle arar.
     - Eşleşme varsa hafızadaki yanıtı sunar.
     - Eşleşme yoksa kullanıcıyı nazikçe bilgilendirir.
"""

import difflib
import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import requests

from config import (
    GREETING_PATTERNS,
    GREETING_RESPONSES,
    PROFANITY_RESPONSE,
    GeminiConfig,
    get_api_key,
)
from memory_engine import MemoryEngine, clean_text, tokenize_and_stem, turkish_lower
from network_manager import NetworkMonitor
from system_tools import SystemTools


# ─────────────────────────────────────────────
# Güvenilir Bilgi Kaynakları (Wikipedia / Web)
# ─────────────────────────────────────────────

class TrustedSourceFetcher:
    """Türkçe Wikipedia ve güvenilir kaynaklardan bilgi çekici."""

    USER_AGENT = "MehburAI/1.0 (Desktop AI Assistant; Contact: local)"

    @classmethod
    def search_wikipedia(cls, query: str) -> Optional[Dict[str, str]]:
        """
        Türkçe Wikipedia OpenSearch ve Summary API'sinden en doğru madde özetini çeker.
        """
        words = clean_text(query).split()
        keywords = [w for w in words if w not in [
            "nedir", "nelerdir", "neresi", "neresidir", "kimdir", "hangisidir",
            "hangisi", "ne", "neler", "nerede", "nasıl", "neden", "hakkında",
            "bilgi", "ver", "söyle", "anlat", "lütfen", "bana", "acaba"
        ]]
        search_term = " ".join(keywords) if keywords else clean_text(query)

        if not search_term:
            return None

        headers = {"User-Agent": cls.USER_AGENT}

        # 1. OpenSearch ile en uygun başlığı bul
        try:
            opensearch_url = (
                f"https://tr.wikipedia.org/w/api.php?action=opensearch"
                f"&search={urllib.parse.quote(search_term)}&limit=1&namespace=0&format=json"
            )
            resp = requests.get(opensearch_url, headers=headers, timeout=3.5)
            if resp.status_code == 200:
                data = resp.json()
                if len(data) >= 2 and data[1]:
                    title = data[1][0]
                    # 2. Summary REST API'den özet çek
                    summary_url = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                    s_resp = requests.get(summary_url, headers=headers, timeout=3.5)
                    if s_resp.status_code == 200:
                        s_data = s_resp.json()
                        extract = s_data.get("extract", "").strip()
                        if extract:
                            return {
                                "title": title,
                                "extract": extract,
                                "source": f"Wikipedia ({title})"
                            }
        except Exception:
            pass

        return None


# ─────────────────────────────────────────────
# Google Gemini API Servisi
# ─────────────────────────────────────────────

class GeminiService:
    """
    Google Gemini API ile entegre yanıt üretici.

    Not: Eski `google-generativeai` Python paketi Google tarafından kullanımdan
    kaldırıldı ve `gemini-2.0-flash` modeli kapatıldı. Ayrıca yeni nesil modellerde
    klasik `:generateContent` uç noktası uzun süre yanıt vermeden askıda kalabiliyor.
    Bu yüzden burada doğrudan REST üzerinden `:streamGenerateContent` (SSE) çağrısı
    yapılır — hızlı, güvenilir ve ekstra bağımlılık gerektirmez (`requests` yeterli).
    """

    def _build_payload(self, question: str, context: Optional[str]) -> dict:
        text = question
        if context:
            text = (
                "Aşağıdaki güvenilir kaynak bilgisini dikkate alarak soruyu yanıtla:\n"
                f"KAYNAK BİLGİSİ: {context}\n\n"
                f"SORU: {question}\n\n"
                "Lütfen net, anlaşılır, Türkçe ve samimi bir dille açıkla."
            )
        return {
            "systemInstruction": {"parts": [{"text": GeminiConfig.SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {
                "temperature": GeminiConfig.TEMPERATURE,
                "maxOutputTokens": GeminiConfig.MAX_OUTPUT_TOKENS,
            },
        }

    @staticmethod
    def _parse_sse_stream(response: requests.Response) -> str:
        """SSE (`data: {...}`) satırlarını birleştirip tam metni döndürür."""
        parts: List[str] = []
        for raw in response.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            for cand in data.get("candidates", []):
                for part in cand.get("content", {}).get("parts", []):
                    if part.get("text"):
                        parts.append(part["text"])
        return "".join(parts).strip()

    def generate_response(self, question: str, context: Optional[str] = None) -> Optional[str]:
        """
        Gemini API'den soru ve (varsa) güvenilir kaynak bağlamıyla yanıt alır.
        Anahtar yoksa veya tüm modeller başarısız olursa None döner.
        """
        api_key = get_api_key()
        if not api_key:
            return None

        payload = self._build_payload(question, context)
        headers = {"Content-Type": "application/json"}
        timeout = (GeminiConfig.CONNECT_TIMEOUT, GeminiConfig.READ_TIMEOUT)

        last_error = None
        for model in GeminiConfig.FALLBACK_MODELS:
            url = (
                f"{GeminiConfig.API_BASE}/models/{model}:streamGenerateContent"
                f"?alt=sse&key={urllib.parse.quote(api_key)}"
            )
            try:
                with requests.post(
                    url, json=payload, headers=headers, timeout=timeout, stream=True
                ) as resp:
                    if resp.status_code != 200:
                        last_error = f"{model}: HTTP {resp.status_code} {resp.text[:160]}"
                        # 404 = model kapalı, 503 = yoğunluk → sıradaki modeli dene
                        continue
                    text = self._parse_sse_stream(resp)
                    if text:
                        return text
                    last_error = f"{model}: boş yanıt"
            except requests.RequestException as e:
                last_error = f"{model}: {type(e).__name__} {str(e)[:120]}"
                continue

        if last_error:
            print(f"[GeminiService] API Yanıt Hatası: {last_error}")
        return None

    def quick_check(self) -> Tuple[bool, str]:
        """API anahtarının canlı çalışıp çalışmadığını kısa bir istekle test eder."""
        api_key = get_api_key()
        if not api_key:
            return False, "API anahtarı girilmemiş."
        try:
            resp = requests.get(
                f"{GeminiConfig.API_BASE}/models?key={urllib.parse.quote(api_key)}",
                timeout=(GeminiConfig.CONNECT_TIMEOUT, 20.0),
            )
            if resp.status_code == 200:
                return True, "Gemini API anahtarı geçerli ve aktif."
            if resp.status_code in (401, 403):
                return False, "API anahtarı geçersiz veya yetkisiz."
            return False, f"Beklenmeyen durum: HTTP {resp.status_code}"
        except requests.RequestException as e:
            return False, f"Bağlantı hatası: {type(e).__name__}"


# ─────────────────────────────────────────────
# Selamlaşma ve Nezaket Filtresi
# ─────────────────────────────────────────────

class GreetingFilter:
    """Genel selamlaşma ve sohbet sorularını tespit edip yanıtlar."""

    @staticmethod
    def check_greeting(text: str) -> Optional[str]:
        """Eğer girdi bir selamlaşma veya kimlik sorusuysa yanıt döndürür."""
        cleaned = clean_text(text)
        if not cleaned:
            return None

        # 1. Adın ne / Kimsin varyasyonları kontrolü
        # (Kelime sınırıyla eşleşir; "ödevler adında klasör" gibi cümlelere bulaşmaz.)
        name_patterns = [
            "adın ne", "adin ne", "adın nedir", "adin nedir",
            "ismin ne", "ismin nedir", "senin adın ne", "senin adin ne",
            "senin ismin ne", "senin ismin nedir", "adını söyle", "adini soyle",
            "ismini söyle", "ismini soyle", "kimsin", "sen kimsin",
            "kendini tanıt", "kendini tanit", "adın neydi", "adin neydi",
            "adın ne senin", "ismin ne senin",
        ]
        for np in name_patterns:
            if re.search(rf"(?<!\w){re.escape(np)}(?!\w)", cleaned):
                return GREETING_RESPONSES["adin_ne"]
        # Tek kelimelik "adın" / "ismin" yalnızca tam eşleşmede kimlik sorusudur
        if cleaned in {"adın", "adin", "ismin", "adını", "ismini"}:
            return GREETING_RESPONSES["adin_ne"]
        # "adını/ismini ... söyle/söyler misin/verir misin/öğrenebilir miyim"
        if re.search(r"\b(ad[ıi]n[ıi]|ismini)\b", cleaned) and any(
            v in cleaned for v in ["söyle", "soyle", "söyler", "soyler", "verir",
                                   "öğrenebilir", "ogrenebilir", "öğrensem", "merak"]
        ):
            return GREETING_RESPONSES["adin_ne"]

        # 2. Hal hatır / Nasılsın kontrolü
        if any(w in cleaned for w in ["nasılsın", "nasilsin", "naber", "ne haber", "napıyorsun", "napiyorsun"]):
            return GREETING_RESPONSES["nasılsın"]

        # 3. Günaydın / İyi günler / Akşam / Gece
        if "günaydın" in cleaned or "gunaydin" in cleaned:
            return GREETING_RESPONSES["günaydın"]
        if "iyi akşamlar" in cleaned or "iyi aksamlar" in cleaned:
            return GREETING_RESPONSES["iyi akşamlar"]
        if "iyi geceler" in cleaned:
            return GREETING_RESPONSES["iyi geceler"]
        if "iyi günler" in cleaned or "iyi gunler" in cleaned:
            return GREETING_RESPONSES["iyi günler"]

        # 4. Selam / Merhaba kalıpları
        for pattern in GREETING_PATTERNS:
            if cleaned == pattern or cleaned.startswith(pattern + " ") or cleaned.endswith(" " + pattern):
                if "selam" in cleaned:
                    return GREETING_RESPONSES["selam"]
                return GREETING_RESPONSES["merhaba"]

        # 5. Teşekkür kontrolü
        if any(t in cleaned for t in ["teşekkür", "tesekkur", "sağol", "sagol", "eyvallah", "harikasın", "harikasin"]):
            return "Rica ederim! 😊 Her zaman yardıma hazırım. Başka bir sorun var mı?"

        return None


# ─────────────────────────────────────────────
# Küfür & Hakaret Algılama Filtresi
# ─────────────────────────────────────────────

class ProfanityFilter:
    """Türkçe küfür, hakaret ve argo ifadeleri tespit eder."""

    # Kısaltmalar ve sembollü maskelemeler (tam kelime eşleşmesi)
    EXACT_ACRONYMS = {
        "amk", "aq", "amq", "oc", "oç", "sg", "sie", "mk", "mq",
        "o.ç", "o.c", "a.m.k", "a.q", "s.g",
    }

    # Kök bazlı küfür/hakaretler (startswith ile kontrol edilir)
    PROFANITY_ROOTS = [
        "orospu", "yavşak", "yavsak", "pezevenk", "pezeveng",
        "şerefsiz", "serefsiz", "haysiyetsiz", "karaktersiz", "namussuz",
        "salak", "aptal", "gerizekal", "embesil", "moron", "dangalak",
        "beyinsiz", "kahpe", "kancık", "kancik", "gavat", "kavat",
        "fahişe", "fahise", "taşşak", "tassak", "daşşak", "dassak",
        "taşak", "tasak", "dalyarak", "götlek", "gotlek", "götveren",
        "gotveren", "puşt", "pust", "ibne", "amcık", "amcik",
        "amcığ", "amcig", "yarrak", "yarak", "ahmak", "çomar", "comar",
    ]

    # Tam kelime eşleşmesi gereken kısa küfürler
    EXACT_WORDS = {
        "sik", "siki", "sike", "sikim", "sikti", "siktim", "siktin",
        "siktiğimin", "siktigimin", "siker", "sikerim", "sikersin",
        "sikerler", "sikeyim", "sikem", "sikik", "sikiş", "sikis",
        "sikişmek", "sikismek", "siktir", "siktirgit",
        "sokarım", "sokarim", "sokayım", "sokayim",
        "piç", "pic", "piçler", "picler", "piçin", "picin",
        "piçi", "pici", "piçsin", "picsin", "piçlik", "piclik",
        "göt", "got", "götü", "gotu", "göte", "gote", "götün", "gotun",
        "götüne", "gotune", "götünü", "gotunu", "götten", "gotten",
        "amına", "amina", "amınakoyayım", "aminakoyayim",
        "amınakoyim", "aminakoyim", "amkoyim",
        "mal", "malsın", "malsin", "manyak", "manyaksın",
    }

    # İki kelimeli küfür kalıpları (regex)
    PHRASE_PATTERNS = [
        r"\borospu\s+[çc]ocu[gğ]u\b",
        r"\bam[ıi]na\s+koy(ay[ıi]m|im|dum|du[gğ]um)\b",
        r"\bam[ıi]na\s+sok(ay[ıi]m|im|tum|tu[gğ]um)\b",
        r"\bsiktir\s+git\b",
        r"\byar[ra]ak\s+kafal[ıi]\b",
        r"\bg[öo]t\s+kafal[ıi]\b",
        r"\bg[öo]t\s+deli[gğ]i\b",
        r"\bg[öo]t\s+lalesi\b",
        r"\bit\s+o[gğ]lu\s+it\b",
        r"\bd[öo]l\s+israf[ıi]\b",
        # Maskelenmiş ve boşluklu kısaltmalar
        r"\ba\s*\.?\s*m\s*\.?\s*k\b",
        r"\ba\s*\.?\s*q\b",
        r"\bo\s*\.?\s*[çc]\b",
        r"\bs\s*\.?\s*g\b",
        r"\bs\s*[*#@x]+\s*k\b",
        r"\bs\s*[*#@x]+\s*kt[ıi]r\b",
        r"\bam\s*[*#@x]+\s*k\b",
    ]

    # False-positive koruması: masum kelimeler
    SAFE_WORDS = {
        "eksik", "eksikler", "eksiklik", "sıkıntı", "sıkıntılı", "sıkıntıları",
        "sıkıcı", "sık", "sıklaşmak", "sıkışık", "sıkı", "sıkıştırmak", "sıkma",
        "klasik", "fizik", "müzik", "vesika", "tasdik", "fıstık", "meksika",
        "kesik", "kemik", "patik", "çeltik", "piknik", "çekiç", "piliç",
        "kerpiç", "meriç", "götür", "götürmek", "götürdü", "götürün", "götürü",
        "göster", "göstermek", "görev", "gölge", "gövde", "gözlem", "göz", "gözlük",
        "malatya", "maliyet", "malzeme", "malum", "malik", "mallar",
        "çocuk", "toprak", "bayrak", "kayak", "tarak", "durak",
        "bakkal", "salata", "salatalık", "makarna", "nokta", "doktor",
        "faktör", "sektör", "sokak", "asker", "baskı", "maske",
        "aşırı", "şeker", "dakika", "tabak", "yasak",
    }

    # Türkçe sesli harfler (yazım hatası toleransı için)
    _VOWELS = set("aeıioöuü")

    @classmethod
    def _skeleton(cls, word: str) -> str:
        """Kelimenin sesli harflerini atıp ünsüz iskeletini döndürür."""
        return "".join(ch for ch in word if ch not in cls._VOWELS)

    @staticmethod
    def _collapse_repeats(word: str) -> str:
        """Ardışık tekrar eden harfleri teke indirir ('saalak' → 'salak')."""
        return re.sub(r"(.)\1+", r"\1", word)

    @classmethod
    def _is_typo_of_profanity(cls, word: str) -> bool:
        """
        Yazım hatalı / eksik harfli küfürleri yakalar; masum kelimelere
        bulaşmamak için dar ve temkinli kurallar kullanır.
        Örn: 'orospo'→'orospu', 'aptl'→'aptal', 'saalak'→'salak', 'çomarr'→'çomar'.
        """
        if len(word) < 4 or word in cls.SAFE_WORDS:
            return False

        w_skel = cls._skeleton(word)
        w_collapsed = cls._collapse_repeats(word)

        for root in cls.PROFANITY_ROOTS:
            if len(root) < 5 or word[0] != root[0] or abs(len(word) - len(root)) > 2:
                continue

            r_skel = cls._skeleton(root)

            # 1) Uzun ve ayırt edici kök + ilk 3 harf aynı + yüksek benzerlik
            #    ("orospo"≈"orospu", "serefsız"≈"serefsiz")
            if len(root) >= 6 and word[:3] == root[:3]:
                if difflib.SequenceMatcher(None, word, root).ratio() >= 0.80:
                    return True

            # 2) Eksik sesli harf: kelime kökten kısa ama ünsüz iskeleti aynı
            #    ("aptl"→"aptal", "yavsk"→"yavşak" değil ama "yavsak" kökü var)
            if len(word) < len(root) and w_skel == r_skel:
                return True

            # 3) Tekrar eden harf hatası: tekrarları silince köke/iskelete oturuyor
            #    ("saalak"→"salak", "çomarr"→"çomar", "aptaal"→"aptal")
            #    Yalnızca gerçekten tekrar silindiyse çalışır (masum kelime kalkanı).
            if w_collapsed != word and (
                w_collapsed == root or cls._skeleton(w_collapsed) == r_skel
            ):
                return True

        return False

    @classmethod
    def check_profanity(cls, text: str) -> bool:
        """Verilen metinde küfür veya hakaret varsa True döndürür."""
        if not text or not text.strip():
            return False

        lower_text = turkish_lower(text)

        # 1. Çok kelimeli regex kalıp kontrolü
        for pattern in cls.PHRASE_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                return True

        # 2. Leetspeak normalizasyonu
        leet_map = {"@": "a", "0": "o", "1": "i", "3": "e", "4": "a", "$": "s", "!": "i"}
        norm_text = lower_text
        for k, v in leet_map.items():
            norm_text = norm_text.replace(k, v)

        # Karakter tekrarlarını sadeleştir (örn. "siiiik" → "sik")
        collapsed_text = re.sub(r"(.)\1{2,}", r"\1", norm_text)

        # 3. Kelime bazlı kontrol
        cleaned_orig = clean_text(lower_text)
        cleaned_collapsed = clean_text(collapsed_text)
        all_words = set(cleaned_orig.split() + cleaned_collapsed.split())

        for word in all_words:
            # Güvenli kelime ise atla
            if word in cls.SAFE_WORDS:
                continue

            # Tam eşleşme (kısaltma veya kısa küfür)
            if word in cls.EXACT_WORDS or word in cls.EXACT_ACRONYMS:
                return True

            # Kök eşleşmesi (uzun küfür/hakaret kökleri)
            for root in cls.PROFANITY_ROOTS:
                if word.startswith(root):
                    return True

            # "sik..." ile başlayan fiil çekimleri ("sıkıntı" vb. SAFE_WORDS'te elendi)
            if re.match(r"^(sik|skt|s!k|s1k)[a-zçğıöşü]*", word) and word not in cls.SAFE_WORDS:
                return True

            # Yazım hatalı / eksik harfli küfürler ("orospo", "aptl", "yavsk" ...)
            if cls._is_typo_of_profanity(word):
                return True

        return False


# ─────────────────────────────────────────────
# Gemini API Durum Kontrolcüsü
# ─────────────────────────────────────────────

class GeminiStatusChecker:
    """Gemini API durumunu ve anahtar geçerliliğini kontrol eder."""

    @staticmethod
    def is_gemini_query(text: str) -> bool:
        """Kullanıcının Gemini durumunu sorup sormadığını anlar."""
        cleaned = clean_text(text)
        gemini_triggers = [
            "gemini aktif mi", "gemini aktifmi", "gemini api aktif mi",
            "gemini apisi aktif mi", "gemini apisi aktifmi", "gemini açık mı",
            "gemini acik mi", "gemini çalışıyor mu", "gemini calisiyor mu",
            "gemini durumu", "gemini api durumu", "gemini bağlı mı", "gemini bagli mi",
            "gemini aktif", "gemini calisiyormu", "gemini açıkmı", "gemini acikmi"
        ]
        return any(tr in cleaned for tr in gemini_triggers)

    @staticmethod
    def get_status_reply() -> str:
        """
        API anahtarını inceler:
        - Google Gemini Studio (AIzaSy...), Vertex AI / Cloud (AQ....) veya geçerli Google anahtarı ise -> 'Gemini aktif'
        - Eğer boşsa veya başka bir sağlayıcıya aitse (OpenAI: sk-, Groq: gsk_, vb.) -> 'Gemini aktif değil'
        """
        key = get_api_key()
        if not key or not isinstance(key, str) or not key.strip():
            return "Gemini aktif değil"

        cleaned_key = key.strip()

        # Başka yapay zeka sağlayıcılarına ait prefixler
        other_providers_prefixes = ["sk-", "gsk_", "sk-ant-", "hf_", "co-", "pplx-"]
        if any(cleaned_key.startswith(p) for p in other_providers_prefixes):
            return "Gemini aktif değil"

        # Google Gemini API formatları: AIzaSy..., AQ...., ya29.... veya 20+ karakter uzunluğunda geçerli token
        if (
            cleaned_key.startswith("AIza") or
            cleaned_key.startswith("AQ.") or
            cleaned_key.startswith("AQ_") or
            cleaned_key.startswith("ya29") or
            (len(cleaned_key) >= 20 and not any(cleaned_key.startswith(p) for p in other_providers_prefixes))
        ):
            return "Gemini aktif"
        else:
            return "Gemini aktif değil"


# ─────────────────────────────────────────────
# Ana Yapay Zeka Karar Motoru (AIEngine)
# ─────────────────────────────────────────────

class AIEngine:
    """
    MehburAI Ana Zeka Motoru.
    Ağ durumunu, belleği, Gemini'yi ve güvenilir kaynakları koordine eder.
    """

    def __init__(
        self,
        memory_engine: Optional[MemoryEngine] = None,
        network_monitor: Optional[NetworkMonitor] = None,
    ):
        self.memory = memory_engine or MemoryEngine()
        self.network = network_monitor or NetworkMonitor()
        self.gemini = GeminiService()

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Kullanıcı girdisini analiz eder, ağ durumuna göre yanıt üretir,
        gerekirse hafızaya kaydeder ve yanıt detaylarını döndürür.
        """
        query = user_query.strip()
        if not query:
            return {
                "answer": "Lütfen bir soru veya mesaj yazın.",
                "is_online": self.network.is_online,
                "source": "empty",
                "learned": False,
            }

        # 0. ADIM: Küfür & Hakaret Filtresi
        if ProfanityFilter.check_profanity(query):
            is_online = self.network.is_online
            self.memory.log_message(role="user", message="[küfür filtresi]", is_online=is_online)
            self.memory.log_message(role="mehbur", message=PROFANITY_RESPONSE, is_online=is_online, source="profanity_filter")
            return {
                "answer": PROFANITY_RESPONSE,
                "is_online": is_online,
                "source": "profanity_filter",
                "learned": False,
            }

        # 1. ADIM: Bilgisayar & Sistem Araçları Kontrolü
        # (Açık bir komut — "... klasörü oluştur", "not defteri aç" — selam/kimlik
        #  filtresinden önce gelir ki yanlış eşleşmeyle ele geçirilmesin.)
        system_response = SystemTools.handle_system_query(query)
        if system_response:
            is_online = self.network.is_online
            self.memory.log_message(role="user", message=query, is_online=is_online)
            self.memory.log_message(role="mehbur", message=system_response, is_online=is_online, source="system_tool")
            return {
                "answer": system_response,
                "is_online": is_online,
                "source": "💻 Bilgisayar Sistemi",
                "learned": False,
            }

        # 2. ADIM: Selamlaşma / Kimlik Kontrolü
        greeting_response = GreetingFilter.check_greeting(query)
        if greeting_response:
            is_online = self.network.is_online
            self.memory.log_message(role="user", message=query, is_online=is_online)
            self.memory.log_message(role="mehbur", message=greeting_response, is_online=is_online, source="greeting")
            return {
                "answer": greeting_response,
                "is_online": is_online,
                "source": "greeting",
                "learned": False,
            }

        # 3. ADIM: Gemini Aktiflik / API Durumu Kontrolü
        if GeminiStatusChecker.is_gemini_query(query):
            is_online = self.network.is_online
            reply = GeminiStatusChecker.get_status_reply()
            self.memory.log_message(role="user", message=query, is_online=is_online)
            self.memory.log_message(role="mehbur", message=reply, is_online=is_online, source="gemini_status")
            return {
                "answer": reply,
                "is_online": is_online,
                "source": "Gemini API Kontrolü",
                "learned": False,
            }

        # 4. ADIM: İnternet Bağlantı Kontrolü (Cloudflare 1.1.1.1)
        is_online = self.network.check_now()

        # ─────────────────────────────────────
        # DURUM A: ÇEVRİMİÇİ MOD (ONLINE)
        # ─────────────────────────────────────
        if is_online:
            # Kullanıcı mesajını kaydet
            self.memory.log_message(role="user", message=query, is_online=True)

            # Güvenilir kaynaktan araştır (Wikipedia)
            wiki_data = TrustedSourceFetcher.search_wikipedia(query)
            context_text = None
            source_tag = "gemini"

            if wiki_data:
                context_text = f"Wikipedia Başlığı: {wiki_data['title']}\nÖzet: {wiki_data['extract']}"
                source_tag = f"gemini + {wiki_data['source']}"

            # Gemini API ile yanıt üret
            answer = self.gemini.generate_response(query, context=context_text)

            # Eğer Gemini API anahtarı yoksa veya hata verdiyse Wikipedia özetini doğrudan kullan
            if not answer:
                if wiki_data and wiki_data.get("extract"):
                    answer = (
                        f"{wiki_data['extract']}\n\n"
                        f"📌 *Kaynak: {wiki_data['source']}*"
                    )
                    source_tag = wiki_data['source']
                else:
                    api_key = get_api_key()
                    if not api_key:
                        answer = (
                            "⚠️ **Gemini API Anahtarı Bulunamadı!**\n\n"
                            "Çevrim içi arama ve akıllı yapay zeka yanıtları için lütfen "
                            "**Ayarlar** bölümünden Google Gemini API anahtarınızı giriniz.\n"
                            "*(API anahtarı olmadan yalnızca hafızadaki kayıtlı bilgiler ve temel kaynaklar çalışır.)*"
                        )
                        source_tag = "system_no_key"
                    else:
                        answer = (
                            "Bu soruyla ilgili güvenilir bir bilgi kaynağına ulaşılamadı. "
                            "Lütfen soruyu farklı kelimelerle sormayı deneyin."
                        )
                        source_tag = "unknown"

            # Otomatik Öğrenme: Geçerli yanıtları hemen hafızaya kaydet ("Eğer bu soru sorulursa bu cevabı ver")
            learned = False
            if source_tag not in ["system_no_key", "unknown", "empty"]:
                self.memory.save_knowledge(question=query, answer=answer, source=source_tag)
                learned = True

            # Sohbet kaydını yap
            self.memory.log_message(role="mehbur", message=answer, is_online=True, source=source_tag)

            return {
                "answer": answer,
                "is_online": True,
                "source": source_tag,
                "learned": learned,
            }

        # ─────────────────────────────────────
        # DURUM B: ÇEVRİMDAŞI MOD (OFFLINE)
        # ─────────────────────────────────────
        else:
            self.memory.log_message(role="user", message=query, is_online=False)

            # Hafızadaki kayıtlı bilgileri semantik olarak ara
            match = self.memory.search_knowledge(query)

            if match:
                # Hafızadan bulundu!
                answer = match["answer"]
                source_tag = f"hafıza ({match['source']})"

                self.memory.log_message(role="mehbur", message=answer, is_online=False, source="memory")

                return {
                    "answer": answer,
                    "is_online": False,
                    "source": source_tag,
                    "learned": False,
                    "score": match["score"],
                    "matched_question": match["question"],
                }
            else:
                # Hafızada henüz yok!
                offline_msg = (
                    "📡 **Şu anda çevrimdışısınız.**\n\n"
                    "Bu sorunun cevabı henüz yerel hafızamda kayıtlı değil. "
                    "İnternete bağlandığınızda bu soruyu tekrar sorarsanız, "
                    "güvenilir kaynaklardan araştırıp yanıtlayacak ve gelecekte çevrimdışı "
                    "kullanabilmeniz için hafızama otomatik olarak kaydedeceğim! 💡"
                )

                self.memory.log_message(role="mehbur", message=offline_msg, is_online=False, source="offline_unknown")

                return {
                    "answer": offline_msg,
                    "is_online": False,
                    "source": "offline_unknown",
                    "learned": False,
                }


# ─────────────────────────────────────────────
# Bağımsız Test Modülü
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import io
    import sys

    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  MehburAI - Yapay Zeka Karar Motoru (AI Engine) Testi")
    print("=" * 60)

    ai = AIEngine()

    print(f"\n[Ağ Durumu]: {ai.network.status_text}")
    print(f"[Gemini API Durumu]: {'Anahtar Kayıtlı' if get_api_key() else 'Anahtar Yok (Wikipedia / Yedek Mod Aktif)'}")

    test_prompts = [
        "Merhaba MehburAI, nasılsın?",
        "Türkiye'nin başkenti neresidir?",
        "Albert Einstein kimdir?",
        "Teşekkür ederim harikasın",
    ]

    for p in test_prompts:
        print(f"\n💬 Kullanıcı: {p}")
        result = ai.process_query(p)
        print(f"🤖 MehburAI ({result['source']} | Online: {result['is_online']} | Öğrenildi: {result['learned']}):")
        print(f"   {result['answer']}")

    print("\n" + "=" * 60)
    print(f"  Toplam Hafıza Kaydı Sayısı: {ai.memory.get_memory_count()}")
    print("  ✅ AI Engine testi başarıyla tamamlandı!")
    print("=" * 60)
