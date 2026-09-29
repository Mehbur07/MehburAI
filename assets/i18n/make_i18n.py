# -*- coding: utf-8 -*-
"""
Arayüz çeviri sözlüklerini (assets/i18n/<dil>.json) üretir / günceller.

    python assets/i18n/make_i18n.py            # eksik çevirileri tamamla
    python assets/i18n/make_i18n.py --check    # yalnızca eksikleri say (ağ yok)

Kaynak kodda ekrana giden Türkçe yazıları (text=, placeholder_text=, pencere başlıkları,
mesaj kutuları, MehburAI'nin sabit cevapları) AST ile toplar; f-string'ler '{}' yer
tutuculu kalıba dönüşür. Eksikleri Gemini ile çevirir (geliştiricinin yerel anahtarı —
sözlükler depoya/pakete girer, anahtar girmez). Var olan çeviriler korunur.
"""

import ast
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from config import AI_MODELS, SUPPORTED_LANGUAGES, GeminiConfig, get_api_key  # noqa: E402

UI_FILES = ("gui_app.py", "jarvis_overlay.py")
REPLY_FILES = ("ai_engine.py", "system_tools.py")
UI_KWARGS = {"text", "placeholder_text", "values"}
POSITIONAL_TEXT_CALLS = {"showinfo", "showwarning", "showerror", "askyesno", "askokcancel",
                         "askyesnocancel", "askquestion", "title", "MenuItem", "t"}
REPLY_NAMES = {"answer", "reply", "msg", "offline_msg", "system_response"}


def template_of(node):
    """Sabit yazı → kendisi; f-string → '{}' yer tutuculu kalıp; toplama → birleşim."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = ""
        for v in node.values:
            out += v.value.replace("{}", "") if isinstance(v, ast.Constant) else "{}"
        return out
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = template_of(node.left), template_of(node.right)
        return a + b if a is not None and b is not None else None
    return None


def _collect(node, out: set):
    if isinstance(node, ast.IfExp):
        _collect(node.body, out)
        _collect(node.orelse, out)
        return
    if isinstance(node, (ast.Tuple, ast.List)):
        for e in node.elts:
            _collect(e, out)
        return
    s = template_of(node)
    if s and re.search(r"[^\W\d_]{2,}", s.replace("{}", "")):
        out.add(s)


def extract() -> set:
    found = set()
    for fn in UI_FILES:
        tree = ast.parse(open(os.path.join(ROOT, fn), encoding="utf-8").read())
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
            for kw in n.keywords:
                if kw.arg in UI_KWARGS:
                    _collect(kw.value, found)
            if name in POSITIONAL_TEXT_CALLS:
                for a in n.args[:2]:
                    _collect(a, found)
    for fn in REPLY_FILES:
        tree = ast.parse(open(os.path.join(ROOT, fn), encoding="utf-8").read())
        for n in ast.walk(tree):
            vals = []
            if isinstance(n, ast.Return) and n.value is not None:
                vals.append(n.value.elts[-1] if isinstance(n.value, ast.Tuple) and n.value.elts else n.value)
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in REPLY_NAMES
                                                for t in n.targets):
                vals.append(n.value)
            for v in vals:
                s = template_of(v)
                if s and " " in s and re.search(r"[^\W\d_]{2,}", s.replace("{}", "")):
                    found.add(s)
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and n.args
                    and (getattr(n.func, "attr", None) == "t" or getattr(n.func, "id", None) == "t")):
                _collect(n.args[0], found)
    for m in AI_MODELS.values():
        found.add(m["desc"])
    from ai_engine import NO_GEMINI_APOLOGY
    from config import PROFANITY_RESPONSE, THEME_ACCENTS, THEME_BACKGROUNDS
    found.update({NO_GEMINI_APOLOGY, PROFANITY_RESPONSE, "Özel renk…"})
    found.update(THEME_ACCENTS)            # açılır menüdeki renk adları
    found.update(THEME_BACKGROUNDS)
    return {s for s in found if s.strip()}


def split(items):
    strings = {s for s in items if "{}" not in s}
    return strings, items - strings


PROMPT = (
    "You translate the user interface of a Turkish desktop AI assistant called MehburAI into {lang}.\n"
    "Return ONLY a JSON object mapping every given Turkish string (exactly as given, as the key) to its "
    "{lang} translation. Rules: keep emojis, symbols, line breaks, markdown (**, `) and every '{{}}' "
    "placeholder exactly (same count, same order); keep the names MehburAI, Gemini, Telegram, Wikipedia, "
    "Reddit, JARVIS, Pro, Flash, Flash-Lite untranslated; keep it short like UI text; use the informal "
    "'you' where the source uses 'sen'.\n\nStrings (JSON list):\n{items}"
)


def translate_batch(items, lang_name, api_key):
    import requests
    payload = {"contents": [{"role": "user", "parts": [{"text": PROMPT.format(
        lang=lang_name, items=json.dumps(items, ensure_ascii=False))}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 16384,
                             "responseMimeType": "application/json"}}
    last = None
    for attempt in range(4):
        for model in GeminiConfig.FALLBACK_MODELS:
            try:
                r = requests.post(f"{GeminiConfig.API_BASE}/models/{model}:generateContent?key={api_key}",
                                  json=payload, timeout=(10, 180))
                if r.status_code != 200:
                    last = f"{model} HTTP {r.status_code}"
                    continue
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                data = json.loads(text[text.find("{"): text.rfind("}") + 1])
                return {k: v for k, v in data.items()
                        if k in items and isinstance(v, str) and v.count("{}") == k.count("{}")}
            except Exception as e:           # noqa: BLE001
                last = f"{model} {type(e).__name__}"
        time.sleep(5 * (attempt + 1))
    print(f"    ! çeviri başarısız: {last}")
    return {}


def main():
    check_only = "--check" in sys.argv
    items = extract()
    strings, templates = split(items)
    print(f"{len(strings)} yazı + {len(templates)} kalıp bulundu.")
    api_key = get_api_key()
    total_missing = 0
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--lang=")]
    for code, lang_name in SUPPORTED_LANGUAGES.items():
        if code == "tr" or (only and code not in only):
            continue
        path = os.path.join(HERE, f"{code}.json")
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        data.setdefault("strings", {})
        data.setdefault("templates", {})
        missing = [s for s in sorted(items)
                   if s not in (data["templates"] if "{}" in s else data["strings"])]
        total_missing += len(missing)
        print(f"  {code}: {len(missing)} eksik")
        if check_only or not missing:
            continue
        if not api_key:
            sys.exit("Gemini API anahtarı yok (Ayarlar'dan girilmeli).")
        for i in range(0, len(missing), 40):
            chunk = missing[i:i + 40]
            got = translate_batch(chunk, lang_name, api_key)
            for k, v in got.items():
                data["templates" if "{}" in k else "strings"][k] = v
            print(f"    {code}: {min(i + 40, len(missing))}/{len(missing)} ({len(got)} çevrildi)")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    return total_missing


if __name__ == "__main__":
    main()
