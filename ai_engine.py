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

import re
import urllib.parse
from typing import Any, Dict, Optional, Tuple

import requests

from config import (
    GREETING_PATTERNS,
    GREETING_RESPONSES,
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
    """Google Gemini API ile entegre yanıt üretici."""

    def __init__(self):
        self._model = None
        self._configured_key = None

    def _ensure_model(self) -> bool:
        """API anahtarı varsa Gemini modelini hazırlar."""
        api_key = get_api_key()
        if not api_key:
            return False

        if self._model is None or self._configured_key != api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self._model = genai.GenerativeModel(
                    model_name=GeminiConfig.MODEL_NAME,
                    system_instruction=GeminiConfig.SYSTEM_PROMPT,
                )
                self._configured_key = api_key
            except Exception as e:
                print(f"[GeminiService] Başlatma hatası: {e}")
                self._model = None
                return False

        return self._model is not None

    def generate_response(self, question: str, context: Optional[str] = None) -> Optional[str]:
        """
        Gemini API'den soru ve güvenilir kaynak bağlamıyla yanıt alır.
        """
        if not self._ensure_model():
            return None

        prompt = question
        if context:
            prompt = (
                f"Aşağıdaki güvenilir kaynak bilgilerini dikkate alarak soruyu yanıtla:\n"
                f"KAYNAK BİLGİSİ: {context}\n\n"
                f"SORU: {question}\n\n"
                f"Lütfen net, anlaşılır, Türkçe ve samimi bir dille açıkla."
            )

        try:
            response = self._model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": GeminiConfig.MAX_OUTPUT_TOKENS,
                    "temperature": GeminiConfig.TEMPERATURE,
                }
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[GeminiService] API Yanıt Hatası: {e}")

        return None


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
        name_patterns = [
            "adın ne", "adin ne", "adın nedir", "adin nedir",
            "ismin ne", "ismin nedir", "senin adın ne", "senin adin ne",
            "senin ismin ne", "senin ismin nedir", "adını söyle", "adini soyle",
            "ismini söyle", "ismini soyle", "kimsin", "sen kimsin",
            "kendini tanıt", "kendini tanit", "adın neydi", "adin neydi",
            "adın ne senin", "ismin ne senin", "adın", "ismin"
        ]
        for np in name_patterns:
            if cleaned == np or np in cleaned:
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

        Returns:
            Dict[str, Any]:
                - 'answer': str (MehburAI'nin verdiği yanıt)
                - 'is_online': bool (İşlem anındaki bağlantı durumu)
                - 'source': str ('greeting', 'gemini+wikipedia', 'gemini', 'wikipedia', 'memory', 'offline_unknown')
                - 'learned': bool (Hafızaya yeni kaydedilip kaydedilmediği)
                - 'score': Optional[float] (Hafızadan geldiyse benzerlik skoru)
                - 'matched_question': Optional[str] (Hafızadan eşleşen soru)
        """
        query = user_query.strip()
        if not query:
            return {
                "answer": "Lütfen bir soru veya mesaj yazın.",
                "is_online": self.network.is_online,
                "source": "empty",
                "learned": False,
            }

        # 1. ADIM: Selamlaşma / Kimlik Kontrolü
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

        # 2. ADIM: Bilgisayar & Sistem Araçları Kontrolü
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

        # 3. ADIM: İnternet Bağlantı Kontrolü (Cloudflare 1.1.1.1)
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
