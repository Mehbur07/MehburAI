# -*- coding: utf-8 -*-
"""
MehburAI - Hesap Sunucusu (Kayıt Ol / Giriş Yap)
==================================================
Bu betik MehburAI.exe'nin İÇİNE GİRMEZ — ayrı, elle çalıştırılan küçük bir
sunucudur. Amacı: MehburAI kullanıcılarının e-posta + şifreyle kayıt olup
giriş yapabilmesi (MehburAI > Ayarlar > 👤 Hesap). Sunucuyu SEN (bu betiği
çalıştıran kişi) kendi bilgisayarında barındırırsın; MehburAI'yi kullanan
herkes (bu bilgisayarda ya da ağdaki/İnternetteki başka bir bilgisayarda)
buradaki adrese bağlanarak hesap açar/giriş yapar.

Çalıştırmak için (hazır Python dışında hiçbir şey kurmaya gerek yok):
    python account_server.py
Varsayılan olarak 0.0.0.0:8765'i dinler; MEHBUR_ACCOUNT_HOST/PORT ortam
değişkenleriyle değiştirilebilir.

ÖNEMLİ GÜVENLİK NOTLARI (lütfen oku):
  • Bu sunucu düz HTTP konuşur. Yalnızca kendi ev ağında (LAN) kullanıyorsan
    sorun değildir. İNTERNETTEN erişilebilir yapacaksan (router'da port
    yönlendirme + Dinamik DNS, ya da Cloudflare Tunnel gibi bir araç), önüne
    MUTLAKA HTTPS sağlayan bir ters vekil (Caddy, Cloudflare Tunnel, nginx+
    certbot vb.) koy — yoksa e-posta/şifreler ağ üzerinde AÇIK METİN gider.
    Bu adımı MehburAI kuramaz/kuramadı — router/DNS/Cloudflare hesabı
    tarafında senin yapman gereken, elle atılacak adımlardır.
  • Şifreler ASLA düz metin saklanmaz: her biri rastgele bir "salt" ile
    birlikte `hashlib.scrypt` ile karıştırılıp öyle veritabanına yazılır.
  • Art arda başarısız giriş denemeleri e-posta başına geçici kilitlenir
    (kaba kuvvet saldırılarını yavaşlatmak için).
  • Bilgisayarın bu sunucuyu barındırırken sürekli açık/bağlı olmalı
    (BIOS'taki "elektrik kesintisinden sonra otomatik aç" ayarı bunun
    içindir — o ayar da yalnızca BIOS/UEFI ekranından elle açılabilir).
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "account_server_data")
DB_PATH = os.path.join(DATA_DIR, "accounts.db")

HOST = os.environ.get("MEHBUR_ACCOUNT_HOST", "0.0.0.0")
PORT = int(os.environ.get("MEHBUR_ACCOUNT_PORT", "8765"))

SESSION_DAYS = 30
MAX_FAILED_ATTEMPTS = 6
LOCKOUT_SECONDS = 300
MAX_BODY_BYTES = 8192

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_lock = threading.Lock()
_failed_attempts: dict = {}   # e-posta -> [başarısız deneme zaman damgaları]


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                salt BLOB NOT NULL,
                hash BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at REAL NOT NULL
            )
        """)
        conn.commit()


def _hash_password(password: str, salt: bytes = None):
    salt = salt or secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return salt, h


def _verify_password(password: str, salt: bytes, expected: bytes) -> bool:
    _, h = _hash_password(password, salt)
    return hmac.compare_digest(h, expected)


def _rate_limited(email: str) -> bool:
    with _lock:
        attempts = [t for t in _failed_attempts.get(email, []) if time.time() - t < LOCKOUT_SECONDS]
        _failed_attempts[email] = attempts
        return len(attempts) >= MAX_FAILED_ATTEMPTS


def _record_failure(email: str) -> None:
    with _lock:
        _failed_attempts.setdefault(email, []).append(time.time())


def _clear_failures(email: str) -> None:
    with _lock:
        _failed_attempts.pop(email, None)


def register(email: str, password: str):
    email = (email or "").strip().lower()
    password = password or ""
    if not EMAIL_RE.match(email):
        return False, "Geçerli bir e-posta adresi gir."
    if len(password) < 8:
        return False, "Şifre en az 8 karakter olmalı."
    salt, h = _hash_password(password)
    try:
        with _db() as conn:
            conn.execute("INSERT INTO users (email, salt, hash) VALUES (?, ?, ?)", (email, salt, h))
            conn.commit()
    except sqlite3.IntegrityError:
        return False, "Bu e-posta ile zaten bir hesap var."
    return True, "Kayıt başarılı."


def login(email: str, password: str):
    email = (email or "").strip().lower()
    password = password or ""
    if _rate_limited(email):
        return False, "Çok fazla başarısız deneme — birkaç dakika sonra tekrar dene.", None
    with _db() as conn:
        row = conn.execute("SELECT salt, hash FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not _verify_password(password, row["salt"], row["hash"]):
        _record_failure(email)
        return False, "E-posta ya da şifre yanlış.", None
    _clear_failures(email)
    token = secrets.token_urlsafe(32)
    with _db() as conn:
        conn.execute("INSERT INTO sessions (token, email, expires_at) VALUES (?, ?, ?)",
                     (token, email, time.time() + SESSION_DAYS * 86400))
        conn.commit()
    return True, "Giriş başarılı.", token


def whoami(token: str):
    if not token:
        return None
    with _db() as conn:
        row = conn.execute(
            "SELECT email FROM sessions WHERE token = ? AND expires_at > ?", (token, time.time())
        ).fetchone()
    return row["email"] if row else None


def logout(token: str) -> None:
    with _db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


class Handler(BaseHTTPRequestHandler):
    server_version = "MehburAccountServer/1.0"

    def _send_json(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return {}
        if length <= 0 or length > MAX_BODY_BYTES:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def do_POST(self):
        data = self._read_json()
        if self.path == "/api/register":
            ok, msg = register(data.get("email", ""), data.get("password", ""))
            self._send_json(200 if ok else 400, {"ok": ok, "message": msg})
        elif self.path == "/api/login":
            ok, msg, token = login(data.get("email", ""), data.get("password", ""))
            resp = {"ok": ok, "message": msg}
            if token:
                resp["token"] = token
                resp["email"] = (data.get("email") or "").strip().lower()
            self._send_json(200 if ok else 401, resp)
        elif self.path == "/api/logout":
            logout(data.get("token", ""))
            self._send_json(200, {"ok": True})
        else:
            self._send_json(404, {"ok": False, "message": "Bilinmeyen uç nokta."})

    def do_GET(self):
        if self.path.startswith("/api/me"):
            token = (parse_qs(urlparse(self.path).query).get("token") or [""])[0]
            email = whoami(token)
            if email:
                self._send_json(200, {"ok": True, "email": email})
            else:
                self._send_json(401, {"ok": False, "message": "Oturum geçersiz ya da süresi dolmuş."})
        elif self.path in ("/", "/api/health"):
            self._send_json(200, {"ok": True, "service": "MehburAI Hesap Sunucusu"})
        else:
            self._send_json(404, {"ok": False, "message": "Bilinmeyen uç nokta."})

    def log_message(self, fmt, *args):
        pass  # konsolu kirletmesin


def main():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"MehburAI Hesap Sunucusu {HOST}:{PORT} adresinde dinliyor (Ctrl+C ile durdur).")
    print(f"Veritabanı: {DB_PATH}")
    print("Bu bilgisayarın LAN adresi (ipconfig ile bak) + bu port, aynı ağdaki MehburAI'lerin "
          "Ayarlar > 👤 Hesap > Sunucu adresine gireceği adrestir, örn: http://192.168.1.5:8765")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDurduruldu.")
        sys.exit(0)


if __name__ == "__main__":
    main()
