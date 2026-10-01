# -*- coding: utf-8 -*-
"""
MehburAI - Hesap İstemcisi (sunucuyu kendisi bulur)
===================================================
Giriş / kayıt ekranının arkasındaki iş: hesap sunucusunun adresini kullanıcıya
SORMADAN bulur. Sırayla dener:

  1. Daha önce çalışmış kayıtlı adres
  2. Bu bilgisayar (http://127.0.0.1:8765)
  3. DEFAULT_SERVER_URL  (internetten erişilen sunucu için — derlemeden önce BİR KEZ doldur)
  4. Yerel ağda (LAN) UDP yayınıyla sunucu arama (account_server.py yanıt verir)
  5. Kaynaktan (python run_mehbur.py) çalışıyorsa ve hiçbiri yoksa: bu bilgisayarda
     account_server.py'yi arka planda başlat (yalnızca 127.0.0.1'e açık)
"""

import json
import os
import socket
import sys
from typing import Optional

import requests

from config import get_account_config, update_account_config

# İnternetten erişilebilir (HTTPS önerilir) hesap sunucunuz varsa buraya yazın; örn.
# "https://hesap.ornek.com". Boş bırakılırsa yalnızca bu PC ve yerel ağ aranır.
DEFAULT_SERVER_URL = ""

LOCAL_URL = "http://127.0.0.1:8765"
DISCOVERY_PORT = 8766
DISCOVERY_MAGIC = b"MEHBURAI_DISCOVER"


def is_healthy(url: str, timeout: float = 1.5) -> bool:
    try:
        r = requests.get(url.rstrip("/") + "/api/health", timeout=timeout)
        return r.ok and r.json().get("service") == "MehburAI Hesap Sunucusu"
    except (requests.RequestException, ValueError):
        return False


def discover_lan(timeout: float = 1.5) -> Optional[str]:
    """Yerel ağa UDP yayını atıp hesap sunucusunun adresini bulur (yoksa None)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        for target in ("255.255.255.255", "127.0.0.1"):
            try:
                sock.sendto(DISCOVERY_MAGIC, (target, DISCOVERY_PORT))
            except OSError:
                pass
        while True:
            data, addr = sock.recvfrom(512)
            try:
                info = json.loads(data.decode("utf-8"))
            except ValueError:
                continue
            if info.get("service") == "mehburai-accounts" and info.get("port"):
                return f"http://{addr[0]}:{int(info['port'])}"
    except (OSError, ValueError):
        return None
    finally:
        sock.close()


def start_local_server() -> Optional[str]:
    """Kaynaktan çalışırken, yan yana duran account_server.py'yi bu PC'de başlatır."""
    if getattr(sys, "frozen", False):
        return None                     # exe'nin içinde sunucu yok (ayrı çalıştırılır)
    here = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isfile(os.path.join(here, "account_server.py")):
        return None
    try:
        import importlib
        srv = importlib.import_module("account_server")
        srv.start_background("127.0.0.1")
    except Exception:
        return None
    return LOCAL_URL if is_healthy(LOCAL_URL) else None


def find_server(allow_autostart: bool = True) -> Optional[str]:
    """Çalışan hesap sunucusunun adresini döndürür; bulursa kaydeder. Yoksa None."""
    saved = get_account_config()["account_server_url"].rstrip("/")
    candidates = [u for u in (saved, LOCAL_URL, DEFAULT_SERVER_URL.rstrip("/")) if u]
    seen = set()
    for url in candidates:
        if url in seen:
            continue
        seen.add(url)
        if is_healthy(url):
            return _remember(url, saved)
    url = discover_lan()
    if url and is_healthy(url):
        return _remember(url, saved)
    if allow_autostart:
        url = start_local_server()
        if url:
            return _remember(url, saved)
    return None


def _remember(url: str, saved: str) -> str:
    if url != saved:
        update_account_config(account_server_url=url)
    return url


NO_SERVER_MSG = ("Hesap sunucusuna ulaşılamadı. Sunucu (account_server.py) çalışan bir "
                 "bilgisayar aynı ağda açık olmalı.")


def authenticate(kind: str, email: str, password: str) -> dict:
    """kind: 'login' | 'register'. Sunucuyu bulup isteği yapar.

    'register' başarılı olursa aynı bilgilerle otomatik giriş de yapılır; dönüş her zaman
    {"ok", "message", "token"?, "email"?} biçimindedir.
    """
    base = find_server()
    if not base:
        return {"ok": False, "message": NO_SERVER_MSG, "no_server": True}

    def post(path: str) -> dict:
        try:
            r = requests.post(f"{base}/api/{path}", json={"email": email, "password": password},
                              timeout=10)
            return r.json()
        except requests.RequestException as e:
            return {"ok": False, "message": f"Sunucuya bağlanılamadı ({type(e).__name__}).",
                    "no_server": True}
        except ValueError:
            return {"ok": False, "message": "Sunucudan geçersiz yanıt geldi."}

    data = post(kind)
    if kind == "register" and data.get("ok"):
        data = post("login")
        if data.get("ok"):
            data["message"] = "Kayıt başarılı, giriş yapıldı."
    return data


def verify_session() -> Optional[bool]:
    """Kayıtlı oturum hâlâ geçerli mi? True/False; sunucuya ulaşılamazsa None (çevrimdışı)."""
    acc = get_account_config()
    base, token = acc["account_server_url"].rstrip("/"), acc["account_token"]
    if not (base and token):
        return None
    try:
        r = requests.get(f"{base}/api/me", params={"token": token}, timeout=4)
    except requests.RequestException:
        return None
    if r.status_code == 401:
        return False
    return True if r.ok else None
