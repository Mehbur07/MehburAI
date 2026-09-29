# -*- coding: utf-8 -*-
"""
MehburAI - Arayüz Çevirisi (Ayarlar > 🌐 Dil)
=============================================
Arayüz Türkçe yazılır; seçili dil Türkçe değilse ekrana konan her yazı `t()` ile
çevrilir. Çeviriler `assets/i18n/<dil>.json` içinde hazır gelir (internet gerekmez):
    {"strings": {"<Türkçe>": "<çeviri>"}, "templates": {"Sürüm: {}": "Version: {}"}}
Sözlükte olmayan yazı OLDUĞU GİBİ kalır — bu yüzden sohbet mesajları, kullanıcı verisi
vb. asla değişmez. Sözlükleri yenilemek için: `python assets/i18n/make_i18n.py`.

`install_hooks()` CustomTkinter bileşenlerinin `text`/`placeholder_text` değerlerini hem
oluşturulurken hem sonradan `configure` edilirken çevirir; `relocalize(root)` dil
değişince açık penceredeki her yazıyı yeniden başlatmadan yeni dile geçirir.
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple

from config import ASSETS_DIR, LANGUAGE_DEFAULT, get_response_language

BUNDLE_DIR = os.path.join(ASSETS_DIR, "i18n")

_lang: str = LANGUAGE_DEFAULT
_tables: Dict[str, Tuple[Dict[str, str], List[Tuple["re.Pattern", str]]]] = {}


def _compile_template(src: str) -> Optional["re.Pattern"]:
    parts = src.split("{}")
    if len(parts) < 2 or not re.search(r"[^\W\d_]", "".join(parts)):
        return None                       # yalnızca yer tutucu/emoji olan kalıp → çevrilecek bir şey yok
    return re.compile("^" + "(.*?)".join(re.escape(p) for p in parts) + "$", re.DOTALL)


def _load(lang: str):
    if lang in _tables:
        return _tables[lang]
    strings: Dict[str, str] = {}
    templates: List[Tuple["re.Pattern", str]] = []
    try:
        with open(os.path.join(BUNDLE_DIR, f"{lang}.json"), encoding="utf-8") as f:
            data = json.load(f)
        strings = {k: v for k, v in (data.get("strings") or {}).items() if isinstance(v, str) and v}
        for src, dst in (data.get("templates") or {}).items():
            rx = _compile_template(src)
            if rx and isinstance(dst, str) and dst.count("{}") == src.count("{}"):
                templates.append((rx, dst))
        templates.sort(key=lambda p: -len(p[0].pattern))       # en belirgin kalıp önce
    except (OSError, ValueError):
        pass
    _tables[lang] = (strings, templates)
    return _tables[lang]


def set_language(code: str) -> None:
    global _lang
    _lang = code or LANGUAGE_DEFAULT


def current_language() -> str:
    return _lang


def t(text, lang: Optional[str] = None):
    """Türkçe arayüz yazısını seçili dile çevirir; bilinmeyen yazıyı aynen döndürür."""
    lang = lang or _lang
    if lang == LANGUAGE_DEFAULT or not isinstance(text, str) or not text.strip():
        return text
    strings, templates = _load(lang)
    hit = strings.get(text)
    if hit is not None:
        return hit
    stripped = text.strip()
    if stripped != text and stripped in strings:
        return text.replace(stripped, strings[stripped])
    for rx, dst in templates:
        m = rx.match(text)
        if m:
            return _fill(dst, m.groups())
    return text


def _fill(dst: str, values) -> str:
    """'{}' yer tutucularını sırayla doldurur (değerdeki '{' / '}' karakterlerinden etkilenmez)."""
    pieces = dst.split("{}")
    out = pieces[0]
    for v, rest in zip(values, pieces[1:]):
        out += v + rest
    return out


# ── CustomTkinter kancaları ──

_TEXT_WIDGETS = ("CTkLabel", "CTkButton", "CTkSwitch", "CTkCheckBox", "CTkRadioButton")
_hooks_installed = False


def install_hooks() -> None:
    """CTk bileşenlerinin text/placeholder_text değerlerini otomatik çevirir (bir kez kurulur)."""
    global _hooks_installed
    if _hooks_installed:
        return
    import customtkinter as ctk

    def wrap(cls, keys):
        orig_init, orig_conf = cls.__init__, cls.configure

        def __init__(self, *args, **kwargs):
            for key in keys:
                if isinstance(kwargs.get(key), str):
                    setattr(self, f"_i18n_{key}", kwargs[key])
                    kwargs[key] = t(kwargs[key])
            orig_init(self, *args, **kwargs)

        def configure(self, require_redraw=False, **kwargs):
            for key in keys:
                if isinstance(kwargs.get(key), str):
                    setattr(self, f"_i18n_{key}", kwargs[key])
                    kwargs[key] = t(kwargs[key])
            return orig_conf(self, require_redraw=require_redraw, **kwargs)

        cls.__init__, cls.configure, cls.config = __init__, configure, configure

    for name in _TEXT_WIDGETS:
        wrap(getattr(ctk, name), ("text",))
    wrap(ctk.CTkEntry, ("placeholder_text",))
    _wrap_option_menu(ctk.CTkOptionMenu)
    _hooks_installed = True


def _wrap_option_menu(cls) -> None:
    """Açılır menü seçeneklerini ekranda çevirir ama koda (get(), set(), command) Türkçe
    asıl değeri verir — renk adı → renk kodu gibi eşleştirmeler bozulmasın."""
    orig_init, orig_conf, orig_set, orig_get = cls.__init__, cls.configure, cls.set, cls.get
    orig_pick = cls._dropdown_callback

    def shown_to_src(self, shown):
        srcs = getattr(self, "_i18n_values", None) or []
        for s in srcs:
            if t(s) == shown:
                return s
        return shown

    def _dropdown_callback(self, value):
        self._i18n_current = shown_to_src(self, value)
        return orig_pick(self, value)

    def __init__(self, *args, **kwargs):
        if isinstance(kwargs.get("values"), (list, tuple)):
            self._i18n_values = list(kwargs["values"])
            kwargs["values"] = [t(v) for v in self._i18n_values]
        cmd = kwargs.get("command")
        if callable(cmd):
            kwargs["command"] = lambda shown, _cmd=cmd, _self=self: _cmd(shown_to_src(_self, shown))
        orig_init(self, *args, **kwargs)

    def configure(self, require_redraw=False, **kwargs):
        if isinstance(kwargs.get("values"), (list, tuple)):
            self._i18n_values = list(kwargs["values"])
            kwargs["values"] = [t(v) for v in self._i18n_values]
        cmd = kwargs.get("command")
        if callable(cmd):
            kwargs["command"] = lambda shown, _cmd=cmd, _self=self: _cmd(shown_to_src(_self, shown))
        return orig_conf(self, require_redraw=require_redraw, **kwargs)

    def set(self, value):
        self._i18n_current = value
        return orig_set(self, t(value) if isinstance(value, str) else value)

    def get(self):
        shown = orig_get(self)
        current = getattr(self, "_i18n_current", None)
        # Dil değişmiş olsa bile (ekranda eski dildeki yazı) Türkçe asıl değeri döndür
        if isinstance(current, str) and shown in (current, t(current)):
            return current
        return shown_to_src(self, shown)

    cls.__init__, cls.configure, cls.config, cls.set, cls.get = __init__, configure, configure, set, get
    cls._dropdown_callback = _dropdown_callback


def relocalize(root) -> int:
    """Açık penceredeki tüm (kancadan geçmiş) yazıları yeni dile göre yeniden çevirir."""
    changed = 0
    stack = [root]
    while stack:
        w = stack.pop()
        for key in ("text", "placeholder_text"):
            src = getattr(w, f"_i18n_{key}", None)
            if isinstance(src, str):
                try:
                    w.configure(**{key: src})
                    changed += 1
                except Exception:
                    pass
        values = getattr(w, "_i18n_values", None)
        if values:
            try:
                current = getattr(w, "_i18n_current", None) or w.get()   # Türkçe asıl değer
                w.configure(values=values)
                w.set(current)
                changed += 1
            except Exception:
                pass
        try:
            stack.extend(w.winfo_children())
        except Exception:
            pass
    return changed


set_language(get_response_language())
