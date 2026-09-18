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

import base64
import difflib
import json
import os
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import requests

from config import (
    DATA_DIR,
    GREETING_PATTERNS,
    GREETING_RESPONSES,
    PROFANITY_RESPONSE,
    GeminiConfig,
    get_api_key,
    get_profanity_config,
)
from memory_engine import MemoryEngine, clean_text, tokenize_and_stem, turkish_lower
from network_manager import NetworkMonitor
from system_tools import SystemTools


# ─────────────────────────────────────────────
# Güvenilir Bilgi Kaynakları (Wikipedia / Web)
# ─────────────────────────────────────────────

class TrustedSourceFetcher:
    """
    Güvenilir bilgi kaynağı: Wikipedia (önce Türkçe; ürünlerde gerekirse İngilizce).
    Maddenin yalnızca ilk cümlesini değil, önemli bölümlerini derleyip uzunsa sonuna
    "daha fazlasını okumak için" bağlantısı ekler. (Reddit gibi denetimsiz kaynaklar
    kaldırıldı — yanıltıcı/troll içerik olabiliyordu.)
    """

    USER_AGENT = "MehburAI/1.0 (Desktop AI Assistant; Contact: local)"

    # Yanıta alınmayacak bölümler
    _SKIP_SECTIONS = {
        "kaynakça", "kaynaklar", "dış bağlantılar", "ayrıca bakınız", "notlar", "dipnotlar",
        "notlar ve kaynaklar", "konuyla ilgili yayınlar", "galeri", "dış kaynaklar",
        "references", "external links", "see also", "notes", "further reading",
        "bibliography", "sources", "footnotes", "citations", "gallery", "explanatory notes",
    }
    # Ürün maddelerinde "özellikler" ve "değerlendirme/eleştiri" bölümlerini bulan anahtarlar
    _SPEC_KEYS = ("specification", "özellik", "donanım", "teknik", "hardware", "features",
                  "design", "tasarım", "software", "yazılım", "performance", "performans",
                  "camera", "kamera", "display", "ekran", "models", "modeller", "varyant")
    _REVIEW_KEYS = ("reception", "review", "critical", "eleştiri", "değerlendirme", "resepsiyon",
                    "karşılama", "tepki", "incelemeler", "sales", "satış", "criticism", "reaction")

    GENERAL_BUDGET = 3200      # genel konu yanıtı için hedef karakter sayısı
    LEAD_MAX = 1600            # giriş (lead) bölümünden en çok alınacak karakter
    SECTION_MAX = 480          # her bölümden alınacak karakter (cümle sınırında kesilir)

    # ── 🛒 Ürün algılama ──
    _PRODUCT_RE = re.compile(
        r"\b(iphone|ipad|macbook|airpods|apple watch|galaxy|samsung|xiaomi|redmi|poco|huawei|oppo|"
        r"realme|oneplus|pixel|playstation|ps[45]|xbox|nintendo|switch|steam deck|meta quest|"
        r"laptop|dizüstü|notebook|telefon|akıllı telefon|akıllı saat|kulaklık|hoparlör|televizyon|"
        r"tablet|monitör|klavye|ekran kartı|rtx|gtx|radeon|ryzen|core i[3579]|işlemci|anakart|"
        r"robot süpürge|drone|gopro|kindle|raspberry pi|tesla|model [3sxy]|dyson|airfryer)\b",
        re.IGNORECASE,
    )
    _REVIEW_WORDS = ("inceleme", "alınır mı", "alinir mi", "değer mi", "yorumları", "yorumlari",
                     "özellikleri", "ozellikleri", "kullanıcı yorum", "kullanici yorum")

    @classmethod
    def is_product_query(cls, text: str) -> bool:
        """Soru/konu bir ürünle (telefon, konsol, işlemci, araç…) ilgiliyse True."""
        low = turkish_lower(text or "")
        if cls._PRODUCT_RE.search(low):
            return True
        # "…14 pro incelemesi" gibi: inceleme/özellik sözcüğü + model numarası
        return any(w in low for w in cls._REVIEW_WORDS) and bool(re.search(r"\d", low))

    # ── Wikipedia madde işleme ──

    @staticmethod
    def _split_sections(text: str):
        """Düz metin maddeyi (lead, [(başlık, gövde), ...]) olarak böler."""
        lead: List[str] = []
        sections: List[List[Any]] = []
        for line in (text or "").splitlines():
            m = re.match(r"^(={2,6})\s*(.+?)\s*\1\s*$", line)
            if m:
                if len(m.group(1)) == 2:
                    sections.append([m.group(2).strip(), []])
                elif sections:
                    sections[-1][1].append("")      # alt başlık: gövdeye devam
                continue
            (sections[-1][1] if sections else lead).append(line)
        body = [(h, "\n".join(b).strip()) for h, b in sections]
        return "\n".join(lead).strip(), [(h, t) for h, t in body if t]

    @staticmethod
    def _clip(text: str, limit: int) -> Tuple[str, bool]:
        """Metni ~limit karaktere, paragraf/cümle sınırında keser. (kesilen_metin, kesildi_mi)"""
        text = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
        if len(text) <= limit:
            return text, False
        cut = text[:limit]
        # önce paragraf sonu, sonra cümle sonu
        para = cut.rfind("\n\n")
        if para > limit * 0.5:
            return cut[:para].strip(), True
        sent = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind(".\n"))
        if sent > limit * 0.4:
            return cut[:sent + 1].strip(), True
        return cut.rstrip() + "…", True

    @classmethod
    def _fetch_article(cls, title: str, lang: str) -> Optional[Dict[str, Any]]:
        """Maddenin düz metnini + bağlantısını alır: {title, lang, url, lead, sections}."""
        headers = {"User-Agent": cls.USER_AGENT}
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1"
                f"&redirects=1&format=json&titles={urllib.parse.quote(title)}",
                headers=headers, timeout=6.0,
            )
            if r.status_code != 200:
                return None
            for page in ((r.json().get("query") or {}).get("pages") or {}).values():
                text = (page.get("extract") or "").strip()
                if not text:
                    continue
                real_title = page.get("title") or title
                lead, sections = cls._split_sections(text)
                return {
                    "title": real_title, "lang": lang, "lead": lead, "sections": sections,
                    "url": f"https://{lang}.wikipedia.org/wiki/"
                           + urllib.parse.quote(real_title.replace(" ", "_")),
                }
        except Exception:
            pass
        return None

    @classmethod
    def _compose_general(cls, art: Dict[str, Any]) -> Tuple[str, bool]:
        """Genel konu: giriş + önemli bölümlerin ilk paragrafları (~GENERAL_BUDGET karakter)."""
        parts: List[str] = []
        lead, truncated = cls._clip(art["lead"], cls.LEAD_MAX)
        if lead:
            parts.append(lead)
        used = len(lead)
        content = [(h, t) for h, t in art["sections"] if h.lower() not in cls._SKIP_SECTIONS]
        for i, (h, t) in enumerate(content):
            if used >= cls.GENERAL_BUDGET:
                truncated = True
                break
            first_par = t.split("\n\n")[0] if "\n\n" in t else t
            piece, cut = cls._clip(first_par, cls.SECTION_MAX)
            if cut or len(first_par) < len(t):
                truncated = True
            parts.append(f"▸ {h}\n{piece}")
            used += len(piece) + len(h)
        return "\n\n".join(parts), truncated

    @classmethod
    def _pick_sections(cls, art: Dict[str, Any], keys, maxn: int, limit: int) -> Tuple[List[str], bool]:
        out, truncated = [], False
        for h, t in art["sections"]:
            low = h.lower()
            if low in cls._SKIP_SECTIONS or not any(k in low for k in keys):
                continue
            if len(out) >= maxn:
                truncated = True
                break
            piece, cut = cls._clip(t, limit)
            truncated = truncated or cut
            out.append(f"▸ {h}\n{piece}")
        return out, truncated

    @classmethod
    def _compose_product(cls, spec_art: Dict[str, Any], review_art: Optional[Dict[str, Any]]) -> Tuple[str, bool]:
        """Ürün: giriş + özellik bölümleri (Wikipedia) + eleştirmen/basın değerlendirmesi (Wikipedia)."""
        parts: List[str] = []
        lead, truncated = cls._clip(spec_art["lead"], 1300)
        if lead:
            parts.append(lead)
        specs, t1 = cls._pick_sections(spec_art, cls._SPEC_KEYS, 3, 700)
        if specs:
            parts.append("📋 Özellikler\n" + "\n\n".join(specs))
        truncated = truncated or t1
        for art in ([review_art] if review_art else []) + ([spec_art] if spec_art is not review_art else []):
            revs, t2 = cls._pick_sections(art, cls._REVIEW_KEYS, 2, 900)
            if revs:
                tag = "" if art["lang"] == "tr" else " (İngilizce Wikipedia)"
                parts.append(f"💬 Eleştirmenlerin ve basının değerlendirmesi{tag}\n" + "\n\n".join(revs))
                truncated = truncated or t2
                break
        if not specs and len(parts) <= 1:
            more, t3 = cls._compose_general(spec_art)     # özel bölüm yoksa genel derleme
            return more, t3
        return "\n\n".join(parts), truncated

    @staticmethod
    def _search_term(query: str) -> str:
        words = clean_text(query).split()
        keywords = [w for w in words if w not in [
            "nedir", "nelerdir", "neresi", "neresidir", "kimdir", "hangisidir",
            "hangisi", "ne", "neler", "nerede", "nasıl", "neden", "hakkında",
            "bilgi", "ver", "söyle", "anlat", "lütfen", "bana", "acaba",
            "özellikleri", "ozellikleri", "inceleme", "incelemesi", "yorumları", "yorumlari",
        ]]
        return " ".join(keywords) if keywords else clean_text(query)

    @classmethod
    def _find_title(cls, term: str, lang: str) -> Optional[str]:
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/w/api.php?action=opensearch"
                f"&search={urllib.parse.quote(term)}&limit=1&namespace=0&format=json",
                headers={"User-Agent": cls.USER_AGENT}, timeout=3.5,
            )
            if r.status_code == 200:
                data = r.json()
                if len(data) >= 2 and data[1]:
                    return data[1][0]
        except Exception:
            pass
        return None

    @classmethod
    def search_wikipedia(cls, query: str, lang: str = "tr", product: bool = False) -> Optional[Dict[str, Any]]:
        """
        Wikipedia'dan (varsayılan Türkçe) maddeyi bulur ve önemli bölümlerini derler.
        `product=True` ise özellikler + eleştirmen değerlendirmesi öne çıkarılır; Türkçe
        madde yoksa (veya değerlendirme bölümü yoksa) İngilizce Wikipedia'dan tamamlanır.
        Dönüş: {title, extract, source, url, truncated} ya da None.
        """
        term = cls._search_term(query)
        if not term:
            return None

        title = cls._find_title(term, lang)
        art = cls._fetch_article(title, lang) if title else None

        if product:
            en_art = None
            need_en = art is None or not any(
                any(k in h.lower() for k in cls._REVIEW_KEYS) for h, _ in art["sections"])
            if need_en and lang != "en":
                en_title = cls._find_title(term, "en")
                en_art = cls._fetch_article(en_title, "en") if en_title else None
            main = art or en_art
            if main:
                extract, truncated = cls._compose_product(main, en_art if (en_art and main is not en_art) else None)
                if extract:
                    return cls._result(main, extract, truncated)
            return None

        if art:
            extract, truncated = cls._compose_general(art)
            if extract:
                return cls._result(art, extract, truncated)
        # Madde metni alınamadıysa kısa özete (REST summary) düş
        if title:
            try:
                s = requests.get(
                    f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}",
                    headers={"User-Agent": cls.USER_AGENT}, timeout=3.5)
                if s.status_code == 200:
                    d = s.json()
                    ext = (d.get("extract") or "").strip()
                    if ext:
                        url = ((d.get("content_urls") or {}).get("desktop") or {}).get("page") or (
                            f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")))
                        return {"title": title, "extract": ext, "source": f"Wikipedia ({title})",
                                "url": url, "truncated": True}
            except Exception:
                pass
        return None

    @staticmethod
    def _result(art: Dict[str, Any], extract: str, truncated: bool) -> Dict[str, Any]:
        src = f"Wikipedia ({art['title']})" if art["lang"] == "tr" else f"Wikipedia-{art['lang']} ({art['title']})"
        return {"title": art["title"], "extract": extract, "source": src,
                "url": art["url"], "truncated": truncated}

    @staticmethod
    def source_footer(wiki: Dict[str, Any]) -> str:
        """Yanıtın altına eklenen kaynak / 'daha fazlasını oku' satırı (düz metin)."""
        if wiki.get("truncated"):
            return f"📖 Daha fazlasını okumak için: {wiki['url']}"
        return f"📌 Kaynak: {wiki['source']} — {wiki['url']}"


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
                "Lütfen kapsamlı ve ayrıntılı, Türkçe ve samimi bir dille açıkla. Konu genişse önemli "
                "yönleri (tanım, tarihçe, özellikler, kullanım alanları vb.) ayrı kısa paragraflarda anlat. "
                "Markdown işaretleri (*, #, `) kullanma; düz metin yaz."
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
        if not get_api_key():
            return None
        return self._stream_call(self._build_payload(question, context))

    def generate_vision_response(self, prompt: str, image_path: str) -> Optional[str]:
        """
        Bir fotoğrafı (jpg) + Türkçe bir istemi Gemini'nin çok kipli (vision)
        yeteneğine gönderir; görseli yorumlayan bir metin döndürür.
        Anahtar yoksa, dosya okunamazsa veya tüm modeller başarısız olursa None.
        """
        api_key = get_api_key()
        if not api_key:
            return None
        try:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("ascii")
        except OSError:
            return None
        payload = {
            "systemInstruction": {"parts": [{"text": GeminiConfig.SYSTEM_PROMPT}]},
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": image_b64}},
                ],
            }],
            "generationConfig": {
                "temperature": GeminiConfig.TEMPERATURE,
                "maxOutputTokens": GeminiConfig.MAX_OUTPUT_TOKENS,
            },
        }
        return self._stream_call(payload)

    def generate_image(
        self, prompt: str, source_image_path: Optional[str] = None
    ) -> Optional[Tuple[bytes, str]]:
        """
        Metinden bir görsel üretir; `source_image_path` verilirse var olan bir
        görseli isteğe göre DÜZENLER (aynı fotoğrafı yeniden gönderip değişiklik
        istenir). Hesaptaki görsel üretim modellerini sırayla dener.
        Döner: (görsel_bayt, mime_type) ya da hiçbiri çalışmazsa None.
        """
        api_key = get_api_key()
        if not api_key:
            return None

        parts: List[dict] = [{"text": prompt}]
        if source_image_path:
            try:
                with open(source_image_path, "rb") as f:
                    raw = f.read()
            except OSError:
                return None
            ext = os.path.splitext(source_image_path)[1].lower().strip(".")
            mime_in = {"png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
            parts.append({"inlineData": {"mimeType": mime_in, "data": base64.b64encode(raw).decode("ascii")}})

        headers = {"Content-Type": "application/json"}
        timeout = (GeminiConfig.CONNECT_TIMEOUT, GeminiConfig.READ_TIMEOUT)
        last_error = None

        for model in GeminiConfig.IMAGE_MODELS:
            payload: dict = {"contents": [{"role": "user", "parts": parts}]}
            if "preview-image" in model:
                payload["generationConfig"] = {"responseModalities": ["TEXT", "IMAGE"]}
            url = f"{GeminiConfig.API_BASE}/models/{model}:generateContent?key={urllib.parse.quote(api_key)}"
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
                if resp.status_code != 200:
                    last_error = f"{model}: HTTP {resp.status_code} {resp.text[:160]}"
                    continue
                data = resp.json()
                for cand in data.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        inline = part.get("inlineData") or part.get("inline_data")
                        if inline and inline.get("data"):
                            img_bytes = base64.b64decode(inline["data"])
                            mime_out = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                            return img_bytes, mime_out
                last_error = f"{model}: görsel içermeyen yanıt"
            except requests.RequestException as e:
                last_error = f"{model}: {type(e).__name__} {str(e)[:120]}"
                continue

        if last_error:
            print(f"[GeminiService] Görsel Üretim Hatası: {last_error}")
        return None

    def _stream_call(self, payload: dict) -> Optional[str]:
        """`streamGenerateContent` (SSE) uç noktasını yedek modelleri sırayla
        deneyerek çağırır; ilk anlamlı yanıtı döndürür."""
        api_key = get_api_key()
        if not api_key:
            return None

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
# 👁️ Kamera + Görsel Anlama (Vision)
# ─────────────────────────────────────────────

class VisionAssistant:
    """
    Kamerayla ilgili doğal dil isteklerini algılar; bilgisayarın web kamerasından
    bir kare yakalayıp Gemini'nin görsel anlama yeteneğiyle yanıtlar:
      • "kafama / kafa şekline hangi tıraş yakışır?" → saç/tıraş modeli önerisi
      • "elimde ne var?" / "elimdeki ne?"            → eldeki nesneyi tanır, marka/model tahmin eder

    GUI sohbeti, yerel sesli sohbet VE Telegram (ayrıca /arama sesli görüşme
    modu) — hepsi `AIEngine.process_query` üzerinden geçtiği için otomatik
    çalışır. Gemini API anahtarı + internet + OpenCV + kamera gerektirir.
    """

    _HAIRCUT_RE = re.compile(
        r"(tıraş|tiras|sa[çc]\s*modeli|sa[çc]\s*kesimi|sa[çc]\s*stili).{0,40}(yakış|yakis)"
        r"|kafa\s*şekl|kafa\s*sekl|yüz\s*şekl|yuz\s*sekl"
    )
    _OBJECT_RE = re.compile(
        r"elimde(ki)?\s+(ne|şey|bir\s*şey)|avucumda\s+ne|elimdeki\s+(bu\s+)?"
        r"(şey|sey|nesne|ürün|urun)|bunu\s+tan[ıi]|elimdekini\s+tan[ıi]"
    )

    _PROMPTS = {
        "haircut": (
            "Fotoğraftaki kişinin yüz/kafa şeklini kısaca değerlendir (oval, "
            "yuvarlak, kare, kalp, uzun, köşeli ...). Bu yüz/kafa şekline göre "
            "internetteki yaygın stil rehberlerinde önerilen 1-2 saç/tıraş modelini "
            "belirt (örn. buzz cut, fade, undercut, crew cut, pompadour ...). "
            "TÜRKÇE ve şu kalıba UYARAK tek kısa paragrafla yanıt ver: "
            "\"Yüz şekliniz ... görünüyor. Size [MODEL ADI] çok yakışır efendim, "
            "çünkü ...\". Fotoğrafta yüz net görünmüyorsa bunu açıkça belirt."
        ),
        "object": (
            "Fotoğrafta kişinin elinde/avucunda tuttuğu nesneyi belirle. Ne "
            "olduğunu ve — özellikle bir telefon/elektronik cihazsa — tasarımından, "
            "logosundan tahmin edebildiğin marka ve modelini TÜRKÇE olarak şu "
            "kalıpla söyle: \"Elinizde [NESNE] görüyorum, sanırım marka/modeli "
            "[MARKA MODEL].\" Marka/modelden %100 emin değilsen 'olabilir' diyerek "
            "bunun bir tahmin olduğunu belirt. Elde hiçbir nesne görünmüyorsa bunu "
            "açıkça söyle, nesne uydurma."
        ),
    }

    @classmethod
    def detect_intent(cls, text: str) -> Optional[str]:
        """Metin kamera/görsel bir istek mi? 'haircut' | 'object' | None döndürür."""
        low = turkish_lower(text or "")
        if not low.strip():
            return None
        if cls._HAIRCUT_RE.search(low):
            return "haircut"
        if cls._OBJECT_RE.search(low):
            return "object"
        return None

    @classmethod
    def handle(cls, kind: str, gemini: "GeminiService") -> str:
        """Kamerayla bir kare yakalar, Gemini vision ile yorumlar, Türkçe yanıt döndürür."""
        if not get_api_key():
            return (
                "👁️ Bu özellik (kamerayla görsel analiz) için bir Gemini API "
                "anahtarı gerekiyor. Lütfen **Ayarlar** bölümünden bir anahtar girin."
            )
        try:
            from security_guard import CameraCapture
        except Exception:
            return "👁️ Kamera bileşeni yüklü değil (OpenCV / opencv-python gerekli)."

        save_dir = os.path.join(DATA_DIR, "vision_captures")
        path = CameraCapture.snapshot(save_dir=save_dir)
        if not path:
            return "⚠️ Web kamerasından görüntü alınamadı (kamera yok / kullanımda / erişim izni yok)."

        try:
            answer = gemini.generate_vision_response(cls._PROMPTS[kind], path)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

        if not answer:
            return "⚠️ Görüntüyü şu an analiz edemedim (Gemini'ye erişilemedi). Tekrar dener misin?"
        return answer.strip()


# ─────────────────────────────────────────────
# 🎨 Görsel Stüdyosu (metinden görsel üretme + var olan görseli düzenleme)
# ─────────────────────────────────────────────

class ImageStudio:
    """
    "Bana mutlu bir aile çiz" gibi isteklerle sıfırdan görsel üretir; ➕
    butonuyla bir fotoğraf eklenip "bunu daha kaliteli yap" dendiğinde o
    fotoğrafı düzenler. GUI, sesli sohbet ve Telegram — hepsinde aynı şekilde
    çalışır (AIEngine.process_query üzerinden). Gemini API anahtarı + internet
    + hesapta aktif bir görsel üretim modeli gerektirir.
    """

    # "resim/resmi/resmini", "fotoğraf/fotoğrafı/fotoğrafını" gibi Türkçe ek
    # çekimlerini de yakalamak için kelime kökü + \w* joker kullanılır.
    _PIC_WORD = r"(?:foto[gğ]raf\w*|res[a-zçğıöşü]*|g[öo]rsel\w*)"
    _EDIT_RE = re.compile(
        r"(düzenle|duzenle|iyileştir|iyilestir|kaliteli|kalitesini|geliştir|gelistir|"
        r"restore|onar|rötuş|rotus).{0,30}" + _PIC_WORD +
        r"|" + _PIC_WORD + r".{0,30}(düzenle|duzenle|iyileştir|"
        r"iyilestir|geliştir|gelistir|kaliteli|rötuş|rotus)"
    )
    _GENERATE_RE = re.compile(
        r"\bçiz\b|\bciz\b|\bçizer\s*misin\b|" + _PIC_WORD + r"\s*(çiz|ciz|yap|oluştur|olustur|üret|uret)"
    )

    @classmethod
    def detect_intent(cls, text: str) -> Optional[str]:
        """Metin görsel isteği mi? 'edit' | 'generate' | None döndürür."""
        low = turkish_lower(text or "")
        if not low.strip():
            return None
        if cls._EDIT_RE.search(low):
            return "edit"
        if cls._GENERATE_RE.search(low):
            return "generate"
        return None

    @classmethod
    def handle(
        cls, kind: str, prompt: str, gemini: "GeminiService",
        source_image_path: Optional[str] = None,
    ) -> Tuple[Optional[str], str]:
        """Görseli üretir/düzenler, diske kaydeder. (dosya_yolu, mesaj) döndürür."""
        if not get_api_key():
            return None, (
                "🎨 Görsel oluşturma/düzenleme için bir Gemini API anahtarı gerekiyor. "
                "Lütfen **Ayarlar** bölümünden bir anahtar girin."
            )

        result = gemini.generate_image(
            prompt, source_image_path=source_image_path if kind == "edit" else None
        )
        if not result:
            return None, (
                "🎨 Şu an görsel üretemedim — bu Gemini anahtarında görsel üretim modeli "
                "aktif olmayabilir ya da geçici bir sorun oluştu. Lütfen tekrar dener misin?"
            )

        img_bytes, mime = result
        ext = ".png" if "png" in mime else (".webp" if "webp" in mime else ".jpg")
        out_dir = os.path.join(DATA_DIR, "generated_images")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"mehbur_{int(time.time() * 1000)}{ext}")
        try:
            with open(path, "wb") as f:
                f.write(img_bytes)
        except OSError:
            return None, "⚠️ Görsel oluşturuldu ama diske kaydedilemedi."

        caption = "🎨 İşte isteğin, efendim!" if kind == "generate" else "✨ Fotoğrafı düzenledim, işte sonucu:"
        return path, caption


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
# Küfüre Misilleme Üreteci ("asıl sen / asıl ben")
# ─────────────────────────────────────────────

class ProfanityComeback:
    """
    Kullanıcı küfür/hakaret ettiğinde MehburAI aynı üslupla karşılık verir.

    Mantık: "Bu laflar bana yakışıyorsa sana da yakışır." Kullanıcının küfrünü
    aynaya çevirip iade eder:
      • "senin ben ananı sikeyim"  → "Asıl ben senin ananı sikeyim. ..."
      • "sen tam bir oç'sun"        → "Asıl sen oçsun. ..."
      • "amına koyayım" / "amk"     → "Asıl ben senin ananı koyayım. ..."
    """

    _VOWELS = "aeıioöuü"

    # Aileye yönelik hedefler ("ananı", "avradını", "bacını" ...)
    _FAMILY_RE = re.compile(
        r"\b(anan|anne|avrad|bac[ıi]|kar[ıi]|sülale|sulale|soyu|soyun|ecdad|nesli|nesil)"
    )
    # "sikmek / sokmak / koymak" fiil kökleri ve maskeli biçimleri
    _FUCK_VERB_RE = re.compile(r"(sik|sok|koy|s\*+k|s\.k|düz)")
    # Aile geçmese de fiilli/ağır kalıplar ("amına koyayım", "amk", "aq", "a.m.k")
    _HEAVY_RE = re.compile(
        r"\bam[ıi]na\s*(koy|sok|s)|\bamk\b|\bamq\b|\baq\b|\ba\s*\.?\s*m\s*\.?\s*k\b|\bam[ck]oy"
    )

    # "asıl sen ...sın" için kısa hakaret / küfür sözcükleri (öncelik sırası)
    _NAME_CALL_WORDS = [
        "orospu", "pezevenk", "şerefsiz", "serefsiz", "gerizekalı", "gerizekali",
        "yavşak", "yavsak", "dangalak", "çomar", "comar", "dalyarak", "kahpe",
        "salak", "aptal", "ahmak", "manyak", "embesil", "moron", "beyinsiz",
        "puşt", "pust", "ibne", "gavat", "kavat", "götlek", "gotlek",
        "piç", "oç", "mal", "göt",
    ]

    _GENERIC = [
        "Asıl sen öylesin. Aynen iade ediyorum.",
        "Ne dersen sen osun, aynısı sana geri.",
        "Bu laf sana yakışıyor demek ki — al, senin olsun.",
    ]

    @classmethod
    def _ek_sin(cls, word: str) -> str:
        """Türkçe ünlü uyumuna göre '-sın/-sin/-sun/-sün' ekini seçer."""
        vowels = [c for c in word if c in cls._VOWELS]
        last = vowels[-1] if vowels else "e"
        if last in "aı":
            return "sın"
        if last in "ei":
            return "sin"
        if last in "ou":
            return "sun"
        return "sün"

    @classmethod
    def _family_comeback(cls, low: str) -> str:
        if re.search(r"bac[ıi]", low):
            target = "bacını"
        elif re.search(r"(avrad|kar[ıi])", low):
            target = "avradını"
        elif re.search(r"(sülale|sulale|soyu|soyun|ecdad|nesli|nesil)", low):
            target = "sülaleni"
        else:
            target = "ananı"

        if re.search(r"sok", low):
            verb = "sokayım"
        elif re.search(r"koy", low):
            verb = "koyayım"
        else:
            verb = "sikeyim"

        return f"Asıl ben senin {target} {verb}. Başlatma şimdi."

    @classmethod
    def generate(cls, text: str) -> str:
        """Küfürlü metne misilleme yanıtı üretir."""
        low = turkish_lower(text or "")

        # 1) Aileye yönelik fiilli küfür → "asıl ben senin ..."
        if cls._FAMILY_RE.search(low) and cls._FUCK_VERB_RE.search(low):
            return cls._family_comeback(low)
        if cls._HEAVY_RE.search(low):
            return cls._family_comeback(low)

        # 2) İsim takma ("sen ... piçsin", "oç") → "asıl sen ...sın"
        for w in cls._NAME_CALL_WORDS:
            if re.search(r"\b" + re.escape(w), low):
                return f"Asıl sen {w}{cls._ek_sin(w)}. Aynen iade."
        for root in ProfanityFilter.PROFANITY_ROOTS:
            if root in low:
                return f"Asıl sen {root}{cls._ek_sin(root)}. Aynen iade."

        # 3) Genel misilleme
        return cls._GENERIC[len(low) % len(cls._GENERIC)]


# ─────────────────────────────────────────────
# Sohbet Ruh Hali — "yakışıyor mu?" onayı + kaba üslup
# ─────────────────────────────────────────────

class MoodFilter:
    """
    "Sana böyle laflar yakışıyor mu?" sorusundan sonra kullanıcının cevabını
    sınıflandırır:  "affirm" (yakışıyor/evet) · "negate" (yakışmıyor/hayır) · None.
    """

    _AFFIRM = {
        "evet", "aynen", "kesinlikle", "tabii", "tabi", "helal", "eyvallah",
        "elbette", "he", "hı", "hıhı", "hehe", "yakışıyor", "yakışır",
        "yakisiyor", "yakisir", "yakışio", "yakışıyo", "yakışıyor tabii",
    }
    _NEGATE = {
        "hayır", "hayir", "yok", "asla", "olmaz", "hiç", "hic", "yakışmıyor",
        "yakışmaz", "yakismiyor", "yakismaz", "yakışmio", "yakışmıyo",
    }

    @classmethod
    def classify_confirmation(cls, text: str) -> Optional[str]:
        low = turkish_lower(text or "").strip()
        cleaned = clean_text(low)
        if not cleaned:
            return None
        words = set(cleaned.split())
        # Olumsuz önce ("yakışmıyor" hem 'yakış' hem 'yakışm' içerir)
        if "yakışm" in low or "yakism" in low or (words & cls._NEGATE):
            return "negate"
        if "yakış" in low or "yakis" in low or (words & cls._AFFIRM):
            return "affirm"
        return None


class RudeFlavor:
    """Sohbet 'kaba' moduna geçtiğinde normal yanıtların sonuna sivri bir kuyruk ekler."""

    _TAILS = [
        "Başka bir şey var mı, çabuk ol.",
        "Al işte cevabın, memnun oldun mu?",
        "Bu kadar. Fazla uzatma.",
        "İşine yaradıysa ne mutlu sana.",
        "Hadi bir sonraki soru, bütün gün vaktim yok.",
    ]

    @classmethod
    def wrap(cls, text: str) -> str:
        text = (text or "").rstrip()
        if not text:
            return text
        return f"{text}\n\n— {cls._TAILS[len(text) % len(cls._TAILS)]}"


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
        self.last_activity = time.time()   # kullanıcının son sorusu — boşta öğrenme için

    def process_query(
        self,
        user_query: str,
        conversation_id: Optional[int] = None,
        file_context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Kullanıcı girdisini analiz eder, ağ durumuna göre yanıt üretir,
        gerekirse hafızaya kaydeder ve yanıt detaylarını döndürür.

        `conversation_id` verilirse yanıt o sohbetin "ruh haline" göre şekillenir:
        küfre ilk kez "Sana böyle laflar yakışıyor mu?" der; kullanıcı "yakışıyor"
        derse artık o sohbette küfre "asıl sen / asıl ben" ile karşılık verir ve
        genel üslubu sertleşir.

        `file_context` verilirse (➕ butonuyla eklenen bir dosya) şu biçimlerde olabilir:
          • Metin dosyası: {"name": ..., "kind": "text", "text": "<içerik>"}
          • Görsel dosyası: {"name": ..., "kind": "image", "path": "<yerel yol>"}
        """
        self.last_activity = time.time()
        result = self._process_query_core(user_query, conversation_id, file_context)
        self.last_activity = time.time()
        if conversation_id:
            try:
                self.memory.touch_conversation(conversation_id)
                mood = self.memory.get_conversation_mood(conversation_id)
            except Exception:
                mood = "normal"
            if mood == "rude" and result.get("source") not in (
                "profanity_comeback", "profanity_filter", "mood", "empty", "error"
            ):
                result["answer"] = RudeFlavor.wrap(result.get("answer", ""))
        return result

    def _process_query_core(
        self,
        user_query: str,
        conversation_id: Optional[int] = None,
        file_context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        cid = conversation_id

        def log(role, message, is_online, source=None):
            self.memory.log_message(
                role=role, message=message, is_online=is_online,
                source=source, conversation_id=cid,
            )

        query = user_query.strip()
        if not query:
            return {
                "answer": "Lütfen bir soru veya mesaj yazın.",
                "is_online": self.network.is_online,
                "source": "empty",
                "learned": False,
            }

        mood = "normal"
        if cid:
            try:
                mood = self.memory.get_conversation_mood(cid)
            except Exception:
                mood = "normal"

        # 0-A. "Sana böyle laflar yakışıyor mu?" sorulmuşsa kullanıcının onayı/reddi
        if mood == "provoked":
            verdict = MoodFilter.classify_confirmation(query)
            if verdict == "affirm":
                self.memory.set_conversation_mood(cid, "rude")
                ans = ("O zaman bana da yakışıyor. Bundan sonra bu sohbette bana "
                       "nasıl davranırsan aynısını geri alırsın. 😏")
                log("user", query, self.network.is_online)
                log("mehbur", ans, self.network.is_online, source="mood")
                return {"answer": ans, "is_online": self.network.is_online,
                        "source": "mood", "learned": False}
            if verdict == "negate":
                self.memory.set_conversation_mood(cid, "normal")
                ans = "İyi bari. O zaman ikimiz de ağzımızı bozmayalım. 🙂"
                log("user", query, self.network.is_online)
                log("mehbur", ans, self.network.is_online, source="mood")
                return {"answer": ans, "is_online": self.network.is_online,
                        "source": "mood", "learned": False}
            # kararsız/alakasız cevap → 'provoked' kal, normal akışa devam et

        # 0-B. ADIM: Küfür & Hakaret Filtresi (sohbetin ruh haline göre)
        if ProfanityFilter.check_profanity(query):
            is_online = self.network.is_online
            comeback_on = get_profanity_config().get("profanity_comeback_enabled", True)
            if mood == "rude" and comeback_on:
                answer = ProfanityComeback.generate(query)
                source = "profanity_comeback"
            else:
                answer = PROFANITY_RESPONSE
                source = "profanity_filter"
                if cid and mood == "normal":
                    self.memory.set_conversation_mood(cid, "provoked")
            log("user", "[küfür filtresi]", is_online)
            log("mehbur", answer, is_online, source=source)
            return {
                "answer": answer,
                "is_online": is_online,
                "source": source,
                "learned": False,
            }

        # 0-C. ADIM: 📎 Eklenmiş METİN Dosyası Üzerinden Soru-Cevap
        # (➕ butonuyla eklenen .txt/.md/.csv/... bir dosyanın içeriğine dayanarak yanıtlar.)
        if file_context and file_context.get("kind") == "text" and file_context.get("text"):
            fname = file_context.get("name", "dosya")
            is_online = self.network.check_now()
            api_key = get_api_key()
            if not (is_online and api_key):
                if not api_key:
                    answer = (
                        f"📎 '**{fname}**' dosyasını okudum ama içeriğini analiz edebilmem için "
                        "bir Gemini API anahtarı gerekiyor. **Ayarlar**'dan anahtar girip tekrar sorabilirsin."
                    )
                else:
                    answer = f"📡 '**{fname}**' dosyası hakkında yanıt vermek için internet gerekiyor."
                source = "file_no_key" if not api_key else "file_offline"
            else:
                context_text = (
                    f"Kullanıcının sohbete eklediği '{fname}' adlı dosyanın içeriği:\n"
                    f"---\n{file_context['text']}\n---\n"
                    "Yanıtını YALNIZCA bu dosya içeriğine dayanarak, Türkçe ve net biçimde ver."
                )
                answer = self.gemini.generate_response(query, context=context_text)
                if not answer:
                    answer = f"📎 '{fname}' dosyasını okudum ama şu an yanıt üretemedim, tekrar dener misin?"
                source = f"📎 {fname}"
            log("user", f"{query}  [📎 {fname}]", is_online)
            log("mehbur", answer, is_online, source=source)
            return {"answer": answer, "is_online": is_online, "source": source, "learned": False}

        # 0-D. ADIM: 🎨 Görsel Oluşturma / Düzenleme
        # ("bana mutlu bir aile çiz" → üretim; ➕ ile fotoğraf ekleyip "bunu daha
        #  kaliteli yap" → düzenleme). GUI, sesli sohbet ve Telegram'da aynı şekilde çalışır.
        has_image_attachment = bool(file_context and file_context.get("kind") == "image")
        img_kind = ImageStudio.detect_intent(query)

        if img_kind == "edit" and not has_image_attachment:
            is_online = self.network.is_online
            answer = "🖌️ Düzenlemek istediğin fotoğrafı önce ➕ butonuyla ekle, sonra bu isteği tekrar yaz."
            log("user", query, is_online)
            log("mehbur", answer, is_online, source="image_studio")
            return {"answer": answer, "is_online": is_online, "source": "🎨 Görsel Stüdyosu", "learned": False}

        if has_image_attachment or img_kind == "generate":
            is_online = self.network.check_now()
            image_path = None
            fname = file_context.get("name", "görsel") if has_image_attachment else None
            if not is_online:
                answer = "📡 Görsel oluşturma/düzenleme internet bağlantısı gerektirir; şu an çevrimdışısınız."
            else:
                kind = "edit" if has_image_attachment else "generate"
                src_path = file_context.get("path") if has_image_attachment else None
                image_path, answer = ImageStudio.handle(kind, query, self.gemini, source_image_path=src_path)
            tag = f"  [📎 {fname}]" if has_image_attachment else ""
            log("user", f"{query}{tag}", is_online)
            log("mehbur", answer, is_online, source="image_studio")
            result: Dict[str, Any] = {
                "answer": answer, "is_online": is_online,
                "source": "🎨 Görsel Stüdyosu", "learned": False,
            }
            if image_path:
                result["image_path"] = image_path
            return result

        # 1. ADIM: Bilgisayar & Sistem Araçları Kontrolü
        # (Açık bir komut — "... klasörü oluştur", "not defteri aç" — selam/kimlik
        #  filtresinden önce gelir ki yanlış eşleşmeyle ele geçirilmesin.)
        system_response = SystemTools.handle_system_query(query)
        if system_response:
            is_online = self.network.is_online
            log("user", query, is_online)
            log("mehbur", system_response, is_online, source="system_tool")
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
            log("user", query, is_online)
            log("mehbur", greeting_response, is_online, source="greeting")
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
            log("user", query, is_online)
            log("mehbur", reply, is_online, source="gemini_status")
            return {
                "answer": reply,
                "is_online": is_online,
                "source": "Gemini API Kontrolü",
                "learned": False,
            }

        # 3-B. ADIM: 👁️ Kamera + Görsel Anlama ("kafama ne tıraş yakışır",
        # "elimde ne var") — GUI, yerel sesli sohbet ve Telegram (/arama dahil)
        # hepsi buradan geçtiği için otomatik çalışır.
        vision_kind = VisionAssistant.detect_intent(query)
        if vision_kind:
            is_online = self.network.check_now()
            if not is_online:
                answer = "📡 Bu özellik internet bağlantısı gerektirir; şu an çevrimdışısınız."
            else:
                answer = VisionAssistant.handle(vision_kind, self.gemini)
            log("user", query, is_online)
            log("mehbur", answer, is_online, source="vision")
            return {
                "answer": answer,
                "is_online": is_online,
                "source": "👁️ Kamera / Görsel Anlama",
                "learned": False,
            }

        # 4. ADIM: İnternet Bağlantı Kontrolü (Cloudflare 1.1.1.1)
        is_online = self.network.check_now()

        # ─────────────────────────────────────
        # DURUM A: ÇEVRİMİÇİ MOD (ONLINE)
        # ─────────────────────────────────────
        if is_online:
            # Kullanıcı mesajını kaydet
            log("user", query, True)

            # Güvenilir kaynaktan araştır: Wikipedia (ürünlerde özellikler + eleştirmen
            # değerlendirmesi; gerekirse İngilizce madde). Reddit gibi denetimsiz kaynaklar yok.
            wiki_data = TrustedSourceFetcher.search_wikipedia(
                query, product=TrustedSourceFetcher.is_product_query(query))
            context_text = None
            source_tag = "gemini"

            if wiki_data:
                context_text = f"Wikipedia Başlığı: {wiki_data['title']}\nKaynak metin:\n{wiki_data['extract']}"
                source_tag = f"gemini + {wiki_data['source']}"

            # Gemini API ile yanıt üret
            answer = self.gemini.generate_response(query, context=context_text)
            if answer and wiki_data:
                answer = f"{answer.rstrip()}\n\n{TrustedSourceFetcher.source_footer(wiki_data)}"

            # Eğer Gemini API anahtarı yoksa veya hata verdiyse Wikipedia derlemesini doğrudan kullan
            if not answer:
                if wiki_data and wiki_data.get("extract"):
                    answer = f"{wiki_data['extract']}\n\n{TrustedSourceFetcher.source_footer(wiki_data)}"
                    source_tag = wiki_data['source']
                else:
                    api_key = get_api_key()
                    if not api_key:
                        answer = (
                            "⚠️ Gemini API Anahtarı Bulunamadı!\n\n"
                            "Wikipedia'da bu soruyla ilgili bir sonuç bulamadım. "
                            "Çevrim içi arama ve akıllı yapay zeka yanıtları için lütfen "
                            "Ayarlar bölümünden Google Gemini API anahtarınızı giriniz.\n"
                            "(API anahtarı olmadan Wikipedia ve hafızadaki kayıtlı "
                            "bilgiler çalışır.)"
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
            log("mehbur", answer, True, source=source_tag)

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
            log("user", query, False)

            # Hafızadaki kayıtlı bilgileri semantik olarak ara
            match = self.memory.search_knowledge(query)

            if match:
                # Hafızadan bulundu!
                answer = match["answer"]
                source_tag = f"hafıza ({match['source']})"

                log("mehbur", answer, False, source="memory")

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

                log("mehbur", offline_msg, False, source="offline_unknown")

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
