# -*- coding: utf-8 -*-
"""
MehburAI - Evrensel API Anahtarı (Çoklu Sağlayıcı Desteği)
============================================================
Ayarlar'daki tek API anahtarı kutusu artık Google Gemini'ye özel değil: Google,
OpenAI ya da Anthropic (Claude) anahtarlarından hangisi yapıştırılırsa
yapıştırılsın, biçiminden hangi şirkete ait olduğu anlaşılır
(`detect_provider`) ve "🧪 API'yi Test Et" bunu kullanıcıya söyler
(`GeminiService.test_key` bu modülü kullanır).

Yalnızca METİN SOHBETİ çok sağlayıcılıdır (`GeminiService.generate_response`
buradaki servislere yönlendirir). Google'a özgü özellikler — Google Arama ile
tüm web araması, görsel oluşturma/düzenleme, kamera/görsel anlama, yalan haber
sınıflandırması, hafıza çevirisi — yalnızca GERÇEK bir Google anahtarıyla
çalışmaya devam eder; bunların Gemini dışı bir karşılığı yoktur (kullanıcının
kendi tercihi, bkz. proje notları).
"""

import time
from typing import Optional, Tuple

import requests

PROVIDER_NAMES = {
    "google": "Google Gemini",
    "openai": "OpenAI",
    "anthropic": "Anthropic (Claude)",
    "unknown": "bilinmeyen",
}

CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 60.0


def detect_provider(key: str) -> str:
    """Anahtarın biçiminden hangi şirkete ait olduğunu tahmin eder.
    Emin olunamayan (ör. eski test/sahte anahtarlar) biçimler 'unknown' döner —
    çağıran taraf bunu güvenli varsayılan olan Google akışına yönlendirir."""
    key = (key or "").strip()
    if not key:
        return "unknown"
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("AIzaSy") or key.startswith("AQ."):
        return "google"
    if key.startswith("sk-") and len(key) > 20:
        return "openai"
    return "unknown"


class OpenAIService:
    """OpenAI Chat Completions API (metin sohbeti)."""

    API_BASE = "https://api.openai.com/v1"
    MODELS = ["gpt-4o-mini", "gpt-4.1-mini", "gpt-3.5-turbo"]

    @classmethod
    def _messages(cls, question: str, context: Optional[str], system_prompt: str) -> list:
        text = question
        if context:
            text = (
                "Aşağıdaki güvenilir kaynak bilgisini dikkate alarak soruyu yanıtla:\n"
                f"KAYNAK BİLGİSİ: {context}\n\nSORU: {question}"
            )
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]

    @classmethod
    def generate_response(cls, api_key: str, question: str, context: Optional[str],
                          system_prompt: str) -> Optional[str]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        messages = cls._messages(question, context, system_prompt)
        for model in cls.MODELS:
            try:
                r = requests.post(
                    f"{cls.API_BASE}/chat/completions",
                    headers=headers,
                    json={"model": model, "messages": messages, "temperature": 0.7},
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                )
                if r.status_code != 200:
                    continue
                choices = r.json().get("choices") or []
                text = (choices[0].get("message", {}).get("content") or "").strip() if choices else ""
                if text:
                    return text
            except requests.RequestException:
                continue
        return None

    @classmethod
    def test_key(cls, api_key: str) -> Tuple[bool, str]:
        try:
            r = requests.get(f"{cls.API_BASE}/models", headers={"Authorization": f"Bearer {api_key}"},
                             timeout=(CONNECT_TIMEOUT, 15.0))
        except requests.RequestException as e:
            return False, f"Bu bir OpenAI anahtarı — bağlanılamadı ({type(e).__name__})."
        if r.status_code in (401, 403):
            return False, "Bu bir OpenAI anahtarı ama geçersiz ya da yetkisiz."
        if r.status_code == 429:
            return False, "Bu bir OpenAI anahtarı, geçerli ama istek/kota sınırına takıldı (HTTP 429)."
        if r.status_code != 200:
            return False, f"Bu bir OpenAI anahtarı — beklenmeyen yanıt: HTTP {r.status_code}"
        t0 = time.time()
        text = cls.generate_response(api_key, "Sadece 'tamam' yaz.", None, "Kısa yanıt ver.")
        if text:
            return True, f"🟩 Bu bir OpenAI anahtarı, geçerli ve yanıt veriyor ({time.time() - t0:.1f} sn)."
        return False, "Bu bir OpenAI anahtarı, geçerli ama hiçbir model yanıt üretmedi."


class AnthropicService:
    """Anthropic Messages API (metin sohbeti)."""

    API_BASE = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"
    MODELS = ["claude-3-5-haiku-20241022", "claude-3-haiku-20240307"]

    @classmethod
    def _headers(cls, api_key: str) -> dict:
        return {"x-api-key": api_key, "anthropic-version": cls.API_VERSION, "Content-Type": "application/json"}

    @classmethod
    def generate_response(cls, api_key: str, question: str, context: Optional[str],
                          system_prompt: str) -> Optional[str]:
        text = question
        if context:
            text = (
                "Aşağıdaki güvenilir kaynak bilgisini dikkate alarak soruyu yanıtla:\n"
                f"KAYNAK BİLGİSİ: {context}\n\nSORU: {question}"
            )
        for model in cls.MODELS:
            try:
                r = requests.post(
                    f"{cls.API_BASE}/messages",
                    headers=cls._headers(api_key),
                    json={"model": model, "max_tokens": 2048, "temperature": 0.7,
                          "system": system_prompt, "messages": [{"role": "user", "content": text}]},
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                )
                if r.status_code != 200:
                    continue
                blocks = r.json().get("content") or []
                out = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
                if out:
                    return out
            except requests.RequestException:
                continue
        return None

    @classmethod
    def test_key(cls, api_key: str) -> Tuple[bool, str]:
        t0 = time.time()
        try:
            r = requests.post(
                f"{cls.API_BASE}/messages", headers=cls._headers(api_key),
                json={"model": cls.MODELS[0], "max_tokens": 16,
                      "messages": [{"role": "user", "content": "Sadece 'tamam' yaz."}]},
                timeout=(CONNECT_TIMEOUT, 20.0),
            )
        except requests.RequestException as e:
            return False, f"Bu bir Anthropic (Claude) anahtarı — bağlanılamadı ({type(e).__name__})."
        if r.status_code in (401, 403):
            return False, "Bu bir Anthropic (Claude) anahtarı ama geçersiz ya da yetkisiz."
        if r.status_code == 429:
            return False, "Bu bir Anthropic (Claude) anahtarı, geçerli ama istek/kota sınırına takıldı (HTTP 429)."
        if r.status_code != 200:
            return False, f"Bu bir Anthropic (Claude) anahtarı — beklenmeyen yanıt: HTTP {r.status_code}"
        blocks = r.json().get("content") or []
        if any(b.get("text") for b in blocks if b.get("type") == "text"):
            return True, f"🟧 Bu bir Anthropic (Claude) anahtarı, geçerli ve yanıt veriyor ({time.time() - t0:.1f} sn)."
        return False, "Bu bir Anthropic (Claude) anahtarı, geçerli ama boş yanıt döndü."
