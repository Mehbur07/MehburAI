# -*- coding: utf-8 -*-
"""
MehburAI - Hesap İstemcisi (Supabase Auth)
==========================================
Giriş / kayıt ekranının arkasındaki iş: e-posta + şifreyle Supabase Auth'a
(GoTrue REST API) bağlanır. Kendi sunucunu çalıştırmaya gerek yoktur.

Kurulum (bir kez):
  1. supabase.com'da proje aç  →  Project Settings > API
  2. "Project URL" ve "anon / publishable" anahtarı aşağıya yaz
     (anon anahtar tarayıcı/istemci içinde durmak için tasarlanmıştır, gizli değildir;
      ASLA "service_role" anahtarını buraya yazma).
  3. Authentication > Providers > Email: "Confirm email" açıksa kayıttan sonra kullanıcı
     e-postasındaki bağlantıyla hesabını doğrular; kapalıysa kayıt olunca direkt giriş yapılır.

İstersen aynı değerleri data/config.json içindeki `account_supabase_url` ve
`account_supabase_key` alanlarına da yazabilirsin (kaynak koddakilerin yerine geçer).
"""

import base64
import hashlib
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from config import clear_account_session, get_account_config, update_account_config

SUPABASE_URL = "https://hqwlsfvsmtdacutkadub.supabase.co"
SUPABASE_ANON_KEY = (  # "anon" role (public by design; never put service_role here)
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhxd2xzZnZzbXRkYWN1dGthZHViIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI2ODMwMTUsImV4cCI6MjEwODI1OTAxNX0.LWecWnx8AOMEJcpWT7-Z-XqJss6azGIr96F__XGROIo"
)

TIMEOUT = 10

NOT_CONFIGURED_MSG = ("Hesap sistemi ayarlanmamış (Supabase proje adresi ve anahtarı eksik). "
                      "account_client.py dosyasına yazılmalı.")
OFFLINE_MSG = "Sunucuya bağlanılamadı. İnternet bağlantını kontrol et."


def _settings() -> tuple:
    acc = get_account_config()
    url = (acc.get("account_supabase_url") or SUPABASE_URL).strip().rstrip("/")
    key = (acc.get("account_supabase_key") or SUPABASE_ANON_KEY).strip()
    return url, key


def is_configured() -> bool:
    url, key = _settings()
    return bool(url and key)


def _headers(key: str, bearer: str = "") -> dict:
    return {"apikey": key, "Authorization": f"Bearer {bearer or key}",
            "Content-Type": "application/json"}


# Supabase'in (İngilizce) hata iletilerini Türkçeleştirir
_ERRORS = (
    ("invalid login credentials", "E-posta ya da şifre yanlış."),
    ("email not confirmed", "E-postanı henüz doğrulamadın. Gelen kutundaki bağlantıya tıkla."),
    ("user already registered", "Bu e-posta ile zaten bir hesap var."),
    ("already been registered", "Bu e-posta ile zaten bir hesap var."),
    ("password should be at least", "Şifre çok kısa (en az 8 karakter olmalı)."),
    ("weak password", "Şifre çok zayıf; daha uzun ya da karmaşık bir şifre dene."),
    ("unable to validate email", "Geçerli bir e-posta adresi gir."),
    ("invalid email", "Geçerli bir e-posta adresi gir."),
    ("rate limit", "Çok fazla deneme yapıldı — biraz bekleyip tekrar dene."),
    ("signups not allowed", "Yeni kayıtlar şu an kapalı."),
)


def _error_message(resp: requests.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        body = {}
    raw = str(body.get("msg") or body.get("error_description") or body.get("message")
              or body.get("error") or "").strip()
    low = raw.lower()
    for needle, tr in _ERRORS:
        if needle in low:
            return tr
    if resp.status_code == 429:
        return "Çok fazla deneme yapıldı — biraz bekleyip tekrar dene."
    return raw or f"İşlem başarısız (HTTP {resp.status_code})."


def _session_result(data: dict, fallback_email: str) -> dict:
    user = data.get("user") or {}
    return {"ok": True, "token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "email": (user.get("email") or fallback_email or "").lower()}


def authenticate(kind: str, email: str, password: str) -> dict:
    """kind: 'login' | 'register'. Dönüş: {"ok", "message", "token"?, "refresh_token"?, "email"?}.

    Kayıt sonrası oturum açıldıysa (e-posta doğrulaması kapalı) token döner; doğrulama
    gerekiyorsa ok=True ama token yoktur ve message kullanıcıya ne yapacağını söyler.
    """
    url, key = _settings()
    if not (url and key):
        return {"ok": False, "message": NOT_CONFIGURED_MSG, "not_configured": True}
    email = (email or "").strip().lower()
    try:
        if kind == "register":
            r = requests.post(f"{url}/auth/v1/signup", headers=_headers(key),
                              json={"email": email, "password": password}, timeout=TIMEOUT)
            if not r.ok:
                return {"ok": False, "message": _error_message(r)}
            data = r.json()
            if data.get("access_token"):
                res = _session_result(data, email)
                res["message"] = "Kayıt başarılı, giriş yapıldı."
                return res
            return {"ok": True, "confirm_email": True,
                    "message": "Kayıt başarılı! E-postana bir doğrulama bağlantısı gönderdik — "
                               "tıkladıktan sonra giriş yap."}
        r = requests.post(f"{url}/auth/v1/token?grant_type=password", headers=_headers(key),
                          json={"email": email, "password": password}, timeout=TIMEOUT)
        if not r.ok:
            return {"ok": False, "message": _error_message(r)}
        res = _session_result(r.json(), email)
        res["message"] = "Giriş başarılı."
        return res
    except requests.RequestException:
        return {"ok": False, "message": OFFLINE_MSG, "offline": True}
    except ValueError:
        return {"ok": False, "message": "Sunucudan geçersiz yanıt geldi."}


def verify_session() -> Optional[bool]:
    """Kayıtlı oturum hâlâ geçerli mi? True/False; internet yoksa None (çevrimdışı → izin ver).

    Erişim anahtarı (1 saatlik) dolmuşsa yenileme anahtarıyla sessizce yenilenir.
    """
    acc = get_account_config()
    url, key = _settings()
    token, refresh = acc["account_token"], acc.get("account_refresh_token", "")
    if not (url and key and (token or refresh)):
        return None
    try:
        r = requests.get(f"{url}/auth/v1/user", headers=_headers(key, token), timeout=5)
        if r.ok:
            return True
        if r.status_code not in (401, 403):
            return None
        if not refresh:
            return False
        rr = requests.post(f"{url}/auth/v1/token?grant_type=refresh_token", headers=_headers(key),
                           json={"refresh_token": refresh}, timeout=5)
        if rr.ok and rr.json().get("access_token"):
            d = rr.json()
            update_account_config(account_token=d["access_token"],
                                  account_refresh_token=d.get("refresh_token", refresh))
            return True
        return False if rr.status_code in (400, 401, 403) else None
    except (requests.RequestException, ValueError):
        return None


def logout() -> None:
    """Oturumu sunucuda kapatır (en iyi çaba) ve yerel oturum bilgisini siler."""
    acc = get_account_config()
    url, key = _settings()
    token = acc["account_token"]
    clear_account_session()
    if url and key and token:
        try:
            requests.post(f"{url}/auth/v1/logout", headers=_headers(key, token), timeout=6)
        except requests.RequestException:
            pass


# ─────────────────────────────────────────────
# Google ile giriş (Supabase OAuth + PKCE, yerel geri dönüş adresi)
# ─────────────────────────────────────────────

# Geri dönüş (callback) için denenen yerel portlar. Hepsi Supabase > Authentication >
# URL Configuration > Redirect URLs listesine eklenmeli (ya da http://127.0.0.1:*/** ).
CALLBACK_PORTS = (53682, 53683, 53684, 61287)
GOOGLE_TIMEOUT = 180

_DONE_PAGE = ("<html><head><meta charset='utf-8'><title>MehburAI</title></head>"
              "<body style='font-family:sans-serif;background:#0A0A0E;color:#00F0FF;"
              "text-align:center;padding-top:15vh'><h2>{title}</h2><p style='color:#aaa'>{text}</p>"
              "</body></html>")


def _pkce_pair() -> tuple:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def _start_callback_server(result: dict):
    """İlk boş portta tek seferlik geri dönüş sunucusu açar. (sunucu, port) döndürür."""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urlparse(self.path)
            if u.path != "/callback":
                self.send_response(404); self.end_headers(); return
            q = parse_qs(u.query)
            if q.get("code"):
                result["code"] = q["code"][0]
                page = _DONE_PAGE.format(title="Giriş başarılı ✅", text="Bu sekmeyi kapatıp MehburAI'ye dönebilirsin.")
            else:
                result["error"] = (q.get("error_description") or q.get("error") or ["Giriş iptal edildi."])[0]
                page = _DONE_PAGE.format(title="Giriş tamamlanamadı", text="MehburAI'ye dönüp tekrar dene.")
            body = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    for port in CALLBACK_PORTS:
        try:
            srv = HTTPServer(("127.0.0.1", port), Handler)
            srv.timeout = 1
            return srv, port
        except OSError:
            continue
    return None, 0


def google_login(open_browser: Callable[[str], object] = webbrowser.open,
                 timeout: float = GOOGLE_TIMEOUT) -> dict:
    """Tarayıcıda Google ile girişi yürütür. Dönüş: authenticate() ile aynı biçim."""
    url, key = _settings()
    if not (url and key):
        return {"ok": False, "message": NOT_CONFIGURED_MSG, "not_configured": True}
    result: dict = {}
    srv, port = _start_callback_server(result)
    if srv is None:
        return {"ok": False, "message": "Yerel geri dönüş portu açılamadı (portlar dolu)."}
    verifier, challenge = _pkce_pair()
    auth_url = f"{url}/auth/v1/authorize?" + urlencode({
        "provider": "google",
        "redirect_to": f"http://127.0.0.1:{port}/callback",
        "code_challenge": challenge,
        "code_challenge_method": "s256",
    })
    try:
        open_browser(auth_url)
        deadline = time.time() + timeout
        while time.time() < deadline and not result:
            srv.handle_request()
    finally:
        srv.server_close()
    if result.get("error"):
        return {"ok": False, "message": _google_error(result["error"])}
    if not result.get("code"):
        return {"ok": False, "message": "Google girişi zaman aşımına uğradı. Tekrar dene."}
    try:
        r = requests.post(f"{url}/auth/v1/token?grant_type=pkce", headers=_headers(key),
                          json={"auth_code": result["code"], "code_verifier": verifier}, timeout=TIMEOUT)
        if not r.ok:
            return {"ok": False, "message": _error_message(r)}
        res = _session_result(r.json(), "")
        res["message"] = "Google ile giriş yapıldı."
        return res
    except requests.RequestException:
        return {"ok": False, "message": OFFLINE_MSG, "offline": True}
    except (ValueError, KeyError):
        return {"ok": False, "message": "Sunucudan geçersiz yanıt geldi."}


def _google_error(raw: str) -> str:
    low = raw.lower()
    if "provider is not enabled" in low or "unsupported provider" in low:
        return "Google girişi Supabase'te henüz açılmamış (Authentication > Sign In / Providers > Google)."
    if "access_denied" in low or "denied" in low:
        return "Google girişi iptal edildi."
    return raw
