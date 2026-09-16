# -*- coding: utf-8 -*-
"""
MehburAI - Logo Üreteci
=======================
Neon cyan devre / sinir-ağı beyin + insan kafası profili, koyu yuvarlak rozet
ve "MehburAI / YAPAY ZEKA ASİSTANI" yazısıyla uygulama logosu üretir.

Çalıştır:  python assets/make_logo.py
Çıktı:     assets/logo.png  (1024x1024, RGBA)

Not: Kendi hazır logon varsa bu dosyayı çalıştırmana gerek yok — doğrudan
     assets/logo.png olarak kaydet, uygulama onu kullanır.
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "logo.png")

SS = 2                      # süper-örnekleme (yumuşak kenar)
SIZE = 1024
S = SIZE * SS

CYAN = (0, 240, 255, 255)
CYAN_SOFT = (120, 245, 255, 255)
CYAN_DIM = (0, 150, 170, 255)
BG_OUTER = (7, 8, 12, 255)
BG_INNER = (12, 26, 33, 255)


def _font(names, size):
    for n in names:
        for path in (n, os.path.join("C:\\Windows\\Fonts", n)):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _glow(layer, radius, passes=1):
    g = layer
    for _ in range(passes):
        g = g.filter(ImageFilter.GaussianBlur(radius))
    return g


def _radial_bg(draw_size):
    """Merkezi açık, kenarı koyu dairesel arka plan."""
    bg = Image.new("RGBA", (draw_size, draw_size), (0, 0, 0, 0))
    d = ImageDraw.Draw(bg)
    cx = cy = draw_size / 2
    R = draw_size / 2
    steps = 260
    for i in range(steps, 0, -1):
        t = i / steps
        r = R * t
        col = tuple(
            int(BG_INNER[k] + (BG_OUTER[k] - BG_INNER[k]) * (t ** 1.4))
            for k in range(3)
        ) + (255,)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return bg


def _circuit_traces(draw_size, seed=7):
    """Arka planda soluk devre yolları."""
    rnd = random.Random(seed)
    lay = Image.new("RGBA", (draw_size, draw_size), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx = cy = draw_size / 2
    R = draw_size * 0.46
    w = max(2, draw_size // 500)
    for _ in range(46):
        ang = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(R * 0.30, R * 0.95)
        x, y = cx + math.cos(ang) * r0, cy + math.sin(ang) * r0
        pts = [(x, y)]
        segs = rnd.randint(2, 5)
        horiz = rnd.random() < 0.5
        for _s in range(segs):
            step = rnd.uniform(draw_size * 0.03, draw_size * 0.11)
            if horiz:
                x += step * rnd.choice((-1, 1))
            else:
                y += step * rnd.choice((-1, 1))
            if math.hypot(x - cx, y - cy) > R:
                break
            pts.append((x, y))
            horiz = not horiz
        if len(pts) >= 2:
            d.line(pts, fill=(0, 120, 140, 90), width=w, joint="curve")
            ex, ey = pts[-1]
            rr = w * 1.8
            d.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], fill=(0, 140, 165, 110))
    return lay


# ── İnsan kafası profili (sağa bakar) — normalize 0..1000 kutu ────────────────
# Ön çizgi: alından burun-dudak-çeneye; arka çizgi: tepe -> ense.
_FACE_FRONT = [
    (487, 92), (556, 96), (626, 126), (679, 178), (708, 246),
    (721, 330), (722, 404), (708, 446),               # alın -> kaş
    (745, 468), (773, 506), (785, 536),               # burun sırtı -> uç
    (761, 556), (726, 562),                           # burun altı
    (732, 582), (722, 602), (732, 624),               # dudaklar
    (726, 674), (706, 724), (658, 760),               # çene
    (612, 792), (614, 900),                           # çene altı -> boyun ön
]
_HEAD_BACK = [
    (487, 92), (405, 108), (338, 168), (300, 268),
    (286, 384), (296, 500), (330, 596), (388, 664),
    (428, 700), (450, 786), (450, 900),               # ense -> boyun arka
]


def _map(points, box, off):
    ox, oy = off
    sx = sy = box / 1000.0
    return [(ox + x * sx, oy + y * sy) for (x, y) in points]


def _neural_net(draw_size, box, off, seed=3):
    """Kafanın içinde düğüm + bağlantı ağı (beyin = sinir ağı)."""
    rnd = random.Random(seed)
    ox, oy = off
    sc = box / 1000.0

    # Kafa iç bölgesi içinde kalan düğümler
    region = [
        (470, 210), (560, 200), (405, 300), (520, 300), (620, 285),
        (360, 400), (470, 400), (585, 395), (680, 380),
        (380, 500), (500, 495), (610, 490), (330, 590), (455, 585), (560, 585),
        (430, 300), (545, 470), (615, 585),
    ]
    nodes = [(ox + x * sc, oy + y * sc) for (x, y) in region]
    core = (ox + 545 * sc, oy + 470 * sc)   # parlak çekirdek (kulak hizası)

    edges = Image.new("RGBA", (draw_size, draw_size), (0, 0, 0, 0))
    ed = ImageDraw.Draw(edges)
    lw = max(2, draw_size // 430)

    # En yakın komşulara bağla
    for i, a in enumerate(nodes):
        d2 = sorted(
            range(len(nodes)),
            key=lambda j: (nodes[j][0] - a[0]) ** 2 + (nodes[j][1] - a[1]) ** 2,
        )
        for j in d2[1:4]:
            if j > i or rnd.random() < 0.35:
                ed.line([a, nodes[j]], fill=(0, 200, 225, 150), width=lw)
    # Çekirdekten ışınlar
    for a in nodes:
        if rnd.random() < 0.5:
            ed.line([core, a], fill=(70, 225, 245, 120), width=lw)

    dots = Image.new("RGBA", (draw_size, draw_size), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for (x, y) in nodes:
        r = rnd.uniform(draw_size * 0.006, draw_size * 0.011)
        dd.ellipse([x - r, y - r, x + r, y + r], fill=CYAN_SOFT)
    # Çekirdek halkaları
    for rr, al in ((0.055, 90), (0.040, 140), (0.025, 220), (0.012, 255)):
        R = draw_size * rr
        dd.ellipse([core[0] - R, core[1] - R, core[0] + R, core[1] + R],
                   fill=(180, 250, 255, al))
    return edges, dots, core


def build():
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Rozet maskesi (dış daire)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([S * 0.02, S * 0.02, S * 0.98, S * 0.98], fill=255)

    base.alpha_composite(_radial_bg(S))
    base.alpha_composite(_circuit_traces(S))

    # Kafa yerleşimi
    box = S * 0.60
    off = (S * 0.205, S * 0.145)

    # Sinir ağı (glow + net)
    edges, dots, core = _neural_net(S, box, off)
    base.alpha_composite(_glow(edges, S * 0.010, 2))
    base.alpha_composite(edges)
    base.alpha_composite(_glow(dots, S * 0.012, 2))
    base.alpha_composite(dots)

    # Kafa profili çizgileri (glow + net)
    prof = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    pd = ImageDraw.Draw(prof)
    lw = max(3, int(S * 0.010))
    front = _map(_FACE_FRONT, box, off)
    back = _map(_HEAD_BACK, box, off)
    pd.line(front, fill=CYAN, width=lw, joint="curve")
    pd.line(back, fill=CYAN, width=lw, joint="curve")
    for pts in (front, back):
        for (x, y) in pts:
            pd.ellipse([x - lw / 2, y - lw / 2, x + lw / 2, y + lw / 2], fill=CYAN)

    base.alpha_composite(_glow(prof, S * 0.014, 2))
    base.alpha_composite(prof)

    # Çekirdek parlaması (en üстte)
    cg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    R = S * 0.045
    ImageDraw.Draw(cg).ellipse([core[0] - R, core[1] - R, core[0] + R, core[1] + R],
                               fill=(210, 252, 255, 255))
    base.alpha_composite(_glow(cg, S * 0.03, 2))
    base.alpha_composite(cg)

    # Yazılar
    txt = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    f_name = _font(["bahnschrift.ttf", "Montserrat-Bold.ttf", "segoeuib.ttf", "arialbd.ttf"],
                   int(S * 0.100))
    f_sub = _font(["bahnschrift.ttf", "segoeui.ttf", "arial.ttf"], int(S * 0.032))

    name = "MehburAI"
    bb = td.textbbox((0, 0), name, font=f_name)
    td.text(((S - (bb[2] - bb[0])) / 2 - bb[0], S * 0.700), name, font=f_name, fill=CYAN_SOFT)

    # Alt yazı — hafif harf aralıklı, ortalanmış
    sub = "YAPAY ZEKA ASİSTANI"
    track = int(S * 0.009)
    widths = [td.textlength(ch, font=f_sub) for ch in sub]
    total = sum(widths) + track * (len(sub) - 1)
    x = (S - total) / 2
    y = S * 0.822
    for ch, w in zip(sub, widths):
        td.text((x, y), ch, font=f_sub, fill=CYAN_DIM)
        x += w + track

    base.alpha_composite(_glow(txt, S * 0.010, 2))
    base.alpha_composite(txt)

    # Dış neon halka
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse(
        [S * 0.035, S * 0.035, S * 0.965, S * 0.965],
        outline=CYAN, width=max(3, int(S * 0.006)),
    )
    base.alpha_composite(_glow(ring, S * 0.012, 2))
    base.alpha_composite(ring)

    # Rozet dışını kırp
    base.putalpha(Image.composite(base.getchannel("A"), Image.new("L", (S, S), 0), mask))

    out = base.resize((SIZE, SIZE), Image.LANCZOS)
    out.save(OUT)
    print(f"[OK] {OUT} ({out.size[0]}x{out.size[1]})")


if __name__ == "__main__":
    build()
