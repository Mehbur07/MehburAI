# -*- coding: utf-8 -*-
"""
MehburAI - Web Kamera Yakalama
===============================
🛡️ Güvenlik Modu (yetkisiz erişim alarmı) kaldırıldı (kullanıcı isteğiyle).
Bu modülde yalnızca `CameraCapture` kalıyor — hem `ai_engine.VisionAssistant`
("kafama ne yakışır" / "elimde ne var") hem de Telegram `/foto` komutu bunu
paylaşır, o yüzden silinmedi.
"""

import os
import time
from datetime import datetime
from typing import Optional

from config import DATA_DIR


class CameraCapture:
    """Web kameradan tek kare yakalar. OpenCV varsa onu kullanır."""

    @staticmethod
    def snapshot(save_dir: Optional[str] = None) -> Optional[str]:
        save_dir = save_dir or os.path.join(DATA_DIR, "camera_captures")
        os.makedirs(save_dir, exist_ok=True)
        fname = f"kamera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        path = os.path.join(save_dir, fname)

        try:
            import cv2  # type: ignore
        except Exception:
            return None

        cam = None
        try:
            for index in (0, 1, 2):
                cam = cv2.VideoCapture(index, getattr(cv2, "CAP_DSHOW", 0))
                if cam is not None and cam.isOpened():
                    break
                if cam is not None:
                    cam.release()
                    cam = None
            if cam is None or not cam.isOpened():
                return None

            # İlk kareler genellikle karanlık olur — birkaç kare ısındır
            frame = None
            for _ in range(8):
                ok, frame = cam.read()
                time.sleep(0.06)
            if frame is None:
                ok, frame = cam.read()
                if not ok:
                    return None

            cv2.imwrite(path, frame)
            return path if os.path.isfile(path) else None
        except Exception:
            return None
        finally:
            if cam is not None:
                try:
                    cam.release()
                except Exception:
                    pass


# ─────────────────────────────────────────────
# Bağımsız Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import io
    import sys

    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("Kamera testi (data/camera_captures/):", CameraCapture.snapshot())
