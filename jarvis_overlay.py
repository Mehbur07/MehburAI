# -*- coding: utf-8 -*-
"""
MehburAI - JARVIS Sesli Asistan Ekranı (Overlay)
================================================
Sesli sohbet açıkken "Mehbur" / "Hey Mehbur" denince açılan tam ekran,
Iron Man tarzı dönen nokta küresi. Ana pencere sistem tepsisinde gizli
olsa bile görünür. ESC ya da tıklama ile kapanır; etkileşim bitince
kendiliğinden kaybolur.

Durum → renk:
  • boşta / hazır / yanıt .. neon cyan    (#00F0FF)
  • komut dinlerken ........ koyu sarı    (#E0A500)
  • işlemde / düşünürken ... neon cyan    (daha hızlı nabız)
  • hata .................. neon kırmızı  (#FF2A4D)

Yalnız tkinter kullanır (ekstra bağımlılık yok). Tüm genel metotlar ANA
(GUI) thread'inden çağrılmalıdır.
"""

import math
import tkinter as tk

_BG = "#04040A"

COLORS = {
    "idle": "#00F0FF",     # neon cyan
    "listen": "#E0A500",   # koyu sarı
    "think": "#00F0FF",    # neon cyan (hızlı nabız)
    "error": "#FF2A4D",    # neon kırmızı
}


def _rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _blend(c1: str, c2: str, t: float) -> str:
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    r1, g1, b1 = _rgb(c1)
    r2, g2, b2 = _rgb(c2)
    return f"#{int(r1 + (r2 - r1) * t):02x}{int(g1 + (g2 - g1) * t):02x}{int(b1 + (b2 - b1) * t):02x}"


class JarvisOverlay:
    N_DOTS = 250
    FPS_MS = 33

    def __init__(self, master):
        self.master = master
        self.top = None
        self.canvas = None
        self._items = []
        self._pts = self._fib_sphere(self.N_DOTS)
        self._ang = 0.0
        self._tilt = 0.0
        self._t = 0.0
        self._mode = "idle"
        self._anim = None
        self._hide_after = None
        self._alpha = 0.0
        self._target_alpha = 0.0
        self.visible = False
        self.on_close = None   # kullanıcı ESC/tıkla/✕ ile kapatınca çağrılır (opsiyonel)

        # 📞 görüşme kontrolleri (yalnız JarvisCall sürerken görünür)
        self._on_mic_toggle = None
        self._on_camera_toggle = None
        self._mic_muted = False
        self._camera_on = False

    # ── küre noktaları (Fibonacci) ──
    @staticmethod
    def _fib_sphere(n: int):
        pts = []
        ga = math.pi * (3.0 - math.sqrt(5.0))
        for i in range(n):
            y = 1 - (i / (n - 1)) * 2 if n > 1 else 0.0
            r = math.sqrt(max(0.0, 1 - y * y))
            th = ga * i
            pts.append((math.cos(th) * r, y, math.sin(th) * r))
        return pts

    # ── pencere kurulumu ──
    def _build(self):
        self.top = tk.Toplevel(self.master)
        self.top.title("MehburAI")
        try:
            self.top.overrideredirect(True)
        except tk.TclError:
            pass
        self.top.configure(bg=_BG)
        for attr in (("-topmost", True), ("-alpha", 0.0)):
            try:
                self.top.attributes(*attr)
            except tk.TclError:
                pass

        sw = self.top.winfo_screenwidth()
        sh = self.top.winfo_screenheight()
        self.top.geometry(f"{sw}x{sh}+0+0")
        self._cx, self._cy = sw // 2, int(sh * 0.43)
        self._R = min(sw, sh) * 0.19

        self.canvas = tk.Canvas(self.top, bg=_BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        self._items = [self.canvas.create_oval(0, 0, 0, 0, fill=_BG, outline="")
                       for _ in range(self.N_DOTS)]

        self._wm = self.canvas.create_text(
            self._cx, int(sh * 0.10), text="M E H B U R   A I",
            fill="#2C6E77", font=("Segoe UI", 20, "bold"))
        self._title = self.canvas.create_text(
            self._cx, int(sh * 0.68), text="", fill="#E8E8EC",
            font=("Segoe UI", 26, "bold"))
        self._sub = self.canvas.create_text(
            self._cx, int(sh * 0.75), text="", fill="#00F0FF",
            width=int(sw * 0.62), font=("Segoe UI", 15), justify="center")
        self.canvas.create_text(
            self._cx, sh - 24, text="kapatmak için ESC ya da tıkla",
            fill="#33333F", font=("Segoe UI", 11))

        self.top.bind("<Escape>", lambda e: self._user_close())
        self.canvas.bind("<Button-1>", lambda e: self._user_close())

        # ── Kontrol düğmeleri (chip'ler) — alt orta, hint yazısının üzerinde ──
        btn_rely = 0.90
        self._btn_exit = tk.Label(
            self.top, text="✕  Kapat", bg="#2a0810", fg="#FF6B7A",
            font=("Segoe UI", 12, "bold"), padx=18, pady=8, cursor="hand2", bd=0)
        self._btn_exit.place(relx=0.5, rely=btn_rely, anchor="center")
        self._btn_exit.bind("<Button-1>", lambda e: self._user_close())

        self._btn_mic = tk.Label(
            self.top, text="🎤", bg="#0a1620", fg="#00F0FF",
            font=("Segoe UI", 16), padx=16, pady=6, cursor="hand2", bd=0)
        self._btn_mic.bind("<Button-1>", lambda e: self._mic_clicked())
        self._btn_cam = tk.Label(
            self.top, text="📷", bg="#0a1620", fg="#7d8590",
            font=("Segoe UI", 16), padx=16, pady=6, cursor="hand2", bd=0)
        self._btn_cam.bind("<Button-1>", lambda e: self._cam_clicked())
        self._btn_mic_rely = self._btn_cam_rely = btn_rely
        self._controls_visible = False
        self._refresh_controls()

    # ── genel API (ANA thread) ──
    def show(self, mode: str = "idle", title: str = "", subtitle: str = ""):
        if self.top is None:
            self._build()
        self._mode = mode if mode in COLORS else "idle"
        self._set_texts(title, subtitle)
        self.visible = True
        self._target_alpha = 0.95
        self._cancel_hide()
        try:
            self.top.deiconify()
            self.top.lift()
            self.top.attributes("-topmost", True)
        except tk.TclError:
            pass
        if self._anim is None:
            self._tick()

    def set_state(self, mode=None, title=None, subtitle=None):
        if mode and mode in COLORS:
            self._mode = mode
        self._set_texts(title, subtitle)

    def hide(self, delay_ms: int = 0):
        if self.top is None:
            self.visible = False
            return
        if delay_ms > 0:
            self._cancel_hide()
            self._hide_after = self.top.after(delay_ms, lambda: self.hide(0))
            return
        self._cancel_hide()
        self._target_alpha = 0.0
        self.visible = False

    def _user_close(self):
        """ESC / tıklama / ✕ ile kapatma — 📞 görüşmesi sürüyorsa on_close onu da bitirir
        (görüşme dinlemeyi/seslendirmeyi hemen keser, yanıt vermeye devam etmez)."""
        self.hide()
        if self.on_close is not None:
            try:
                self.on_close()
            except Exception:
                pass

    def _mic_clicked(self):
        if self._on_mic_toggle is not None:
            try:
                self._on_mic_toggle()
            except Exception:
                pass

    def _cam_clicked(self):
        if self._on_camera_toggle is not None:
            try:
                self._on_camera_toggle()
            except Exception:
                pass

    def set_mic_muted(self, muted: bool):
        """🎤/🔇 — 📞 görüşmesinde kendi sesimizi açıp kapatma düğmesinin görünümünü günceller."""
        self._mic_muted = bool(muted)
        if self.top is None:
            return
        if self._mic_muted:
            self._btn_mic.configure(text="🔇", fg="#FF6B7A", bg="#2a0810")
        else:
            self._btn_mic.configure(text="🎤", fg="#00F0FF", bg="#0a1620")

    def set_camera_on(self, on: bool):
        """📷 — kamera sorularının (saç/elimdeki nesne) yanıtlanıp yanıtlanmayacağını gösterir."""
        self._camera_on = bool(on)
        if self.top is None:
            return
        if self._camera_on:
            self._btn_cam.configure(text="📷", fg="#00E676", bg="#08220f")
        else:
            self._btn_cam.configure(text="📷", fg="#7d8590", bg="#0a1620")

    def set_call_controls(self, enabled: bool, mic_muted: bool = False, camera_on: bool = False,
                           on_mic_toggle=None, on_camera_toggle=None):
        """📞 JarvisCall sürerken 🎤/📷 düğmelerini gösterir; görüşme bitince gizler.
        on_mic_toggle()/on_camera_toggle() — düğmeye tıklanınca çağrılır (durumu GUI yönetir,
        yeni durumu set_mic_muted/set_camera_on ile bu overlay'e geri bildirir)."""
        if self.top is None:
            self._build()
        self._on_mic_toggle = on_mic_toggle
        self._on_camera_toggle = on_camera_toggle
        self._controls_visible = bool(enabled)
        self._refresh_controls()
        self.set_mic_muted(mic_muted)
        self.set_camera_on(camera_on)

    def _refresh_controls(self):
        if self._controls_visible:
            self._btn_mic.place(relx=0.40, rely=self._btn_mic_rely, anchor="center")
            self._btn_cam.place(relx=0.60, rely=self._btn_cam_rely, anchor="center")
        else:
            self._btn_mic.place_forget()
            self._btn_cam.place_forget()

    def destroy(self):
        self._cancel_hide()
        if self.top is not None:
            if self._anim is not None:
                try:
                    self.top.after_cancel(self._anim)
                except Exception:
                    pass
            try:
                self.top.destroy()
            except Exception:
                pass
        self._anim = None
        self.top = None

    # ── iç ──
    def _cancel_hide(self):
        if self._hide_after is not None and self.top is not None:
            try:
                self.top.after_cancel(self._hide_after)
            except Exception:
                pass
        self._hide_after = None

    def _set_texts(self, title, subtitle):
        if self.top is None:
            return
        if title is not None:
            self.canvas.itemconfigure(self._title, text=title)
        if subtitle is not None:
            s = subtitle if len(subtitle) <= 240 else subtitle[:237] + "…"
            self.canvas.itemconfigure(self._sub, text=s)

    def _tick(self):
        if self.top is None:
            self._anim = None
            return

        # fade in / out
        if abs(self._alpha - self._target_alpha) > 0.01:
            self._alpha += (self._target_alpha - self._alpha) * 0.18
        else:
            self._alpha = self._target_alpha
        try:
            self.top.attributes("-alpha", max(0.0, min(0.95, self._alpha)))
        except tk.TclError:
            pass
        if self._target_alpha == 0.0 and self._alpha <= 0.01:
            try:
                self.top.withdraw()
            except tk.TclError:
                pass
            self._anim = None
            return

        base = COLORS.get(self._mode, COLORS["idle"])
        self._t += 0.12
        speed = {"think": 0.055, "listen": 0.030}.get(self._mode, 0.018)
        self._ang += speed
        self._tilt = 0.28 * math.sin(self._t * 0.28)
        pulse = 0.78 + 0.22 * math.sin(self._t * (2.6 if self._mode == "think" else 1.4))

        ca, sa = math.cos(self._ang), math.sin(self._ang)
        ct, st = math.cos(self._tilt), math.sin(self._tilt)
        cx, cy, R = self._cx, self._cy, self._R
        persp = 2.6
        coords = self.canvas.coords
        itemcfg = self.canvas.itemconfigure

        for item, (x, y, z) in zip(self._items, self._pts):
            xr = x * ca + z * sa
            zr = -x * sa + z * ca
            yr = y * ct - zr * st
            zr = y * st + zr * ct
            f = persp / (persp - zr)
            sx = cx + xr * R * f
            sy = cy + yr * R * f
            depth = (zr + 1.0) * 0.5
            rad = (0.6 + 2.9 * depth) * f * pulse
            coords(item, sx - rad, sy - rad, sx + rad, sy + rad)
            itemcfg(item, fill=_blend(_BG, base, 0.12 + 0.88 * depth))

        self._anim = self.top.after(self.FPS_MS, self._tick)


# ─────────────────────────────────────────────
# Bağımsız Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("300x120")
    root.title("JARVIS Overlay testi")
    ov = JarvisOverlay(root)

    seq = [
        ("idle", "Emrinizdeyim efendim", ""),
        ("listen", "Dinliyorum...", ""),
        ("think", "Düşünüyorum...", "bilgisayarı kapat"),
        ("idle", "", "Bilgisayar 45 saniye içinde kapanacak."),
        ("error", "Bir hata oluştu", "Mikrofona erişilemedi"),
    ]

    def step(i=0):
        m, t, s = seq[i % len(seq)]
        ov.show(m, t, s)
        root.after(2600, lambda: step(i + 1))

    tk.Button(root, text="Kapat", command=lambda: (ov.destroy(), root.destroy())).pack(pady=30)
    root.after(500, step)
    root.mainloop()
