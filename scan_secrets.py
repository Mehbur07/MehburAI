# -*- coding: utf-8 -*-
"""
MehburAI - Hassas Bilgi Tarayıcı
================================
Gemini API anahtarı, Telegram bot token'ı, Telegram ID'si gibi hassas bilgilerin
GitHub'a push'lanan koda ya da .exe/Setup paketine SIZMASINI engeller.
Bulursa çıkış kodu 1 ile biter (commit/derleme durur).

Nasıl arar:
  1. Genel kalıplar (AIza…, AQ.…, <sayı>:<token>, gh?_…, özel anahtar).
  2. Bu bilgisayardaki GERÇEK değerler (data/config.json + SQLite ayarları) — bunlar
     hiçbir dosyada aynen geçmemelidir.
  3. Pakette olmaması gereken dosyalar (config.json, *.db, kamera kareleri …).

Kullanım:
  python scan_secrets.py --staged         # git commit öncesi (pre-commit kancası)
  python scan_secrets.py                  # depodaki takip edilen/eklenecek tüm dosyalar
  python scan_secrets.py --dist DIR       # derlenmiş .exe klasörü
  python scan_secrets.py --pyz FILE.pyz   # .exe'nin içindeki derlenmiş Python kodu
  python scan_secrets.py --zip FILE.zip   # Setup'a gömülecek payload arşivi
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))

PATTERNS = {
    "Gemini API anahtarı (AIza…)": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "Gemini API anahtarı (AQ.…)": re.compile(r"\bAQ\.[A-Za-z0-9_\-]{30,}"),
    "Telegram bot token'ı": re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b"),
    "GitHub token'ı": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "Özel anahtar (PRIVATE KEY)": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
# Test verilerindeki sahte değerler (örn. "AIzaSyD_TestValidGeminiKey…") sayılmaz
ALLOW_SUBSTRINGS = ("Test", "TEST", "example", "EXAMPLE", "XXXX")

FORBIDDEN_PATH = re.compile(
    r"(^|/)(data/(config\.json|camera_captures|vision_captures|remote_captures|generated_images)"
    r"|[^/]*\.db(-wal|-shm|-journal)?|\.env(\..*)?|last_error\.log|selftest\.txt)(/|$)",
    re.IGNORECASE,
)

TEXT_EXT = {".py", ".md", ".txt", ".bat", ".spec", ".json", ".yml", ".yaml", ".cfg", ".ini",
            ".toml", ".html", ".js", ".css", ".sh", ".ps1", ".gitignore", ".gitkeep"}
SKIP_DIRS = {".git", "build", "dist", "__pycache__", "venv", ".venv", "node_modules"}
SECRET_KEYS = ("gemini_api_key", "telegram_bot_token", "telegram_chat_id")


def known_secret_values() -> set:
    """Bu bilgisayardaki gerçek hassas değerler (geliştirme + kurulu uygulama verisi)."""
    values = set()
    dirs = [os.path.join(ROOT, "data"),
            os.path.join(os.environ.get("APPDATA", ""), "MehburAI", "data")]
    for d in dirs:
        cfg = os.path.join(d, "config.json")
        if os.path.isfile(cfg):
            try:
                with open(cfg, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k in SECRET_KEYS:
                    v = str(data.get(k) or "").strip()
                    if len(v) >= 6:
                        values.add(v)
            except (OSError, ValueError):
                pass
        db = os.path.join(d, "mehbur_memory.db")
        if os.path.isfile(db):
            try:
                with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
                    for (v,) in conn.execute("SELECT value FROM app_settings WHERE key='gemini_api_key'"):
                        if v and len(v) >= 6:
                            values.add(v)
            except sqlite3.Error:
                pass
    return values


def _mask(s: str) -> str:
    return s[:4] + "…" + s[-2:] if len(s) > 8 else "…"


def scan_text(name: str, text: str, secrets: set) -> list:
    """Bir dosya içeriğini tarar; bulgu listesi döndürür (sırlar maskelenir)."""
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for label, rx in PATTERNS.items():
            for m in rx.finditer(line):
                if any(a in m.group(0) for a in ALLOW_SUBSTRINGS):
                    continue
                findings.append(f"{name}:{lineno}: {label} → {_mask(m.group(0))}")
        for sec in secrets:
            if sec in line:
                findings.append(f"{name}:{lineno}: bu bilgisayardaki gerçek gizli değer → {_mask(sec)}")
    return findings


def scan_bytes(name: str, data: bytes, secrets: set) -> list:
    findings = []
    for sec in secrets:
        for enc in ("utf-8", "utf-16-le"):
            if sec.encode(enc) in data:
                findings.append(f"{name}: gerçek gizli değer bulundu → {_mask(sec)}")
                break
    return findings


def _is_text_file(path: str) -> bool:
    base = os.path.basename(path).lower()
    return os.path.splitext(base)[1] in TEXT_EXT or base in {".gitignore", ".gitkeep", "pre-commit"}


def _git(*args) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def scan_staged(secrets: set) -> list:
    findings = []
    names = _git("diff", "--cached", "--name-only", "--diff-filter=ACM", "-z").decode("utf-8", "replace")
    for name in filter(None, names.split("\0")):
        if FORBIDDEN_PATH.search(name.replace("\\", "/")):
            findings.append(f"{name}: repoya girmemesi gereken kişisel/hassas dosya")
            continue
        if not _is_text_file(name):
            continue
        try:
            blob = _git("show", f":{name}").decode("utf-8", "replace")
        except subprocess.CalledProcessError:
            continue
        findings += scan_text(name, blob, secrets)
    return findings


def scan_repo(secrets: set) -> list:
    findings = []
    listed = _git("ls-files", "-z", "--cached", "--others", "--exclude-standard").decode("utf-8", "replace")
    for name in filter(None, listed.split("\0")):
        norm = name.replace("\\", "/")
        if FORBIDDEN_PATH.search(norm):
            findings.append(f"{name}: repoya girmemesi gereken kişisel/hassas dosya")
            continue
        path = os.path.join(ROOT, name)
        if _is_text_file(name) and os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                findings += scan_text(name, f.read(), secrets)
    return findings


def scan_dist(folder: str, secrets: set) -> list:
    findings = []
    for dirpath, dirnames, filenames in os.walk(folder):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, folder).replace("\\", "/")
            if FORBIDDEN_PATH.search(rel):
                findings.append(f"{rel}: pakette olmaması gereken kişisel/hassas dosya")
                continue
            try:
                if os.path.getsize(path) > 120 * 1024 * 1024:
                    continue
                with open(path, "rb") as f:
                    findings += scan_bytes(rel, f.read(), secrets)
            except OSError:
                pass
    return findings


def scan_zip(zip_path: str, secrets: set) -> list:
    findings = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if FORBIDDEN_PATH.search(info.filename.replace("\\", "/")):
                findings.append(f"{info.filename}: pakette olmaması gereken kişisel/hassas dosya")
                continue
            if info.file_size <= 120 * 1024 * 1024:
                findings += scan_bytes(info.filename, zf.read(info), secrets)
    return findings


def scan_pyz(pyz_path: str, secrets: set) -> list:
    """PyInstaller'ın sıkıştırılmış derlenmiş Python modüllerinin (PYZ) içindeki sabitleri tarar."""
    import marshal

    from PyInstaller.archive.readers import ZlibArchiveReader

    findings = []
    reader = ZlibArchiveReader(pyz_path)
    for name in reader.toc:
        try:
            blob = marshal.dumps(reader.extract(name))
        except Exception:
            continue
        for label, rx in PATTERNS.items():
            for m in rx.finditer(blob.decode("latin-1")):
                if not any(a in m.group(0) for a in ALLOW_SUBSTRINGS):
                    findings.append(f"PYZ:{name}: {label} → {_mask(m.group(0))}")
        findings += scan_bytes(f"PYZ:{name}", blob, secrets)
    return findings


def main(argv) -> int:
    secrets = known_secret_values()
    if "--staged" in argv:
        findings, what = scan_staged(secrets), "commit edilecek dosyalar"
    elif "--dist" in argv:
        folder = argv[argv.index("--dist") + 1]
        findings, what = scan_dist(folder, secrets), f"paket klasörü ({folder})"
    elif "--pyz" in argv:
        z = argv[argv.index("--pyz") + 1]
        findings, what = scan_pyz(z, secrets), f"derlenmiş kod arşivi ({z})"
    elif "--zip" in argv:
        z = argv[argv.index("--zip") + 1]
        findings, what = scan_zip(z, secrets), f"Setup arşivi ({z})"
    else:
        findings, what = scan_repo(secrets), "depo dosyaları"

    if findings:
        print(f"[HASSAS BİLGİ] {what} taranırken {len(findings)} sorun bulundu:")
        for f in findings:
            print("  ✖", f)
        print("Bu bilgiler GitHub'a / .exe'ye / Setup'a girmemeli. Kaldırıp tekrar dene.")
        return 1
    print(f"[TEMİZ] {what}: hassas bilgi bulunamadı ({len(secrets)} gerçek gizli değer kontrol edildi).")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
