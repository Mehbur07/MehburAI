# -*- coding: utf-8 -*-
"""
MehburAI - Güncelleme Denetleyicisi
===================================
Uygulama açılınca GitHub'daki en yeni sürüm numarasını (herkese açık, kimlik
doğrulamasız) öğrenir; bu bilgisayardaki sürümden yeniyse arayüzde uyarı gösterilir.

Kaynaklar (sırayla):
  1. GitHub Releases: son yayının etiketi (örn. v1.4)  →  indirme sayfası o yayının adresi
  2. Depodaki config.py içindeki APP_VERSION satırı       →  indirme sayfası UPDATE_PAGE_URL

Ağ yoksa / depo herkese açık değilse / yanıt anlaşılmazsa sessizce None döner —
kullanıcıya hata gösterilmez.
"""

import re
from typing import Dict, Optional, Tuple

import requests

from config import APP_VERSION, GITHUB_REPO, UPDATE_PAGE_URL

_HEADERS = {"User-Agent": "MehburAI-update-check", "Accept": "application/vnd.github+json"}
_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(text: Optional[str]) -> Optional[Tuple[int, int, int]]:
    """'v1.3.3' / '1.4' → (1, 3, 3) / (1, 4, 0). Anlaşılmazsa None."""
    m = _VERSION_RE.search(text or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def _pretty(text: str) -> str:
    m = _VERSION_RE.search(text or "")
    return m.group(0) if m else (text or "").strip()


def _latest_from_release(timeout: float) -> Optional[Tuple[str, str]]:
    r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                     headers=_HEADERS, timeout=timeout)
    if r.status_code != 200:
        return None
    data = r.json()
    tag = data.get("tag_name") or data.get("name") or ""
    if parse_version(tag) is None:
        return None
    return _pretty(tag), data.get("html_url") or UPDATE_PAGE_URL


def _latest_from_source(timeout: float) -> Optional[Tuple[str, str]]:
    r = requests.get(f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/config.py",
                     headers=_HEADERS, timeout=timeout)
    if r.status_code != 200:
        return None
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', r.text, re.MULTILINE)
    if not m or parse_version(m.group(1)) is None:
        return None
    return m.group(1), UPDATE_PAGE_URL


def check_for_update(current: str = APP_VERSION, timeout: float = 6.0) -> Optional[Dict[str, str]]:
    """
    Yeni sürüm varsa {"current", "latest", "url"} döndürür; yoksa (ya da denetlenemezse) None.
    """
    cur = parse_version(current)
    if cur is None:
        return None
    for source in (_latest_from_release, _latest_from_source):
        try:
            found = source(timeout)
        except (requests.RequestException, ValueError):
            continue
        if not found:
            continue
        latest, url = found
        latest_v = parse_version(latest)
        if latest_v and latest_v > cur:
            return {"current": current, "latest": latest, "url": url}
        return None   # kaynak yanıt verdi ve yeni sürüm yok
    return None
