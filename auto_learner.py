# -*- coding: utf-8 -*-
"""
MehburAI - Boşta Otomatik Öğrenme
=================================
MehburAI açıkken kullanıcı bir süredir soru sormuyorsa arka planda Wikipedia'dan
yeni bir konu çekip hafızaya (SQLite `knowledge_base`) kaydeder — çevrimdışıyken de
bu bilgilerle yanıt verebilsin diye.

  • Genel konu  → Wikipedia maddesinin önemli bölümleri
  • Ürün konusu → Wikipedia'dan özellikler + eleştirmen/basın değerlendirmesi (Reddit gibi denetimsiz kaynak yok)

Ayarlar > 🧠 Otomatik Öğrenme anahtarıyla kapatılabilir.
"""

import random
import threading
import time
from typing import Callable, Dict, Optional

from ai_engine import TrustedSourceFetcher
from config import get_learn_config

GENERAL_TOPICS = [
    "Yapay zeka", "Güneş Sistemi", "Kara delik", "Osmanlı İmparatorluğu", "İstanbul",
    "Mustafa Kemal Atatürk", "Fotosentez", "DNA", "İnternet", "Blockchain", "Kuantum mekaniği",
    "Mars", "Albert Einstein", "Nikola Tesla", "Python (programlama dili)", "Linux",
    "Elektrikli araç", "İklim değişikliği", "Uluslararası Uzay İstasyonu", "Ay", "Deprem",
    "Volkan", "Mitokondri", "Vitamin", "Satranç", "Futbol", "Nobel Ödülü", "Leonardo da Vinci",
    "Mimar Sinan", "Kapadokya", "Pamukkale", "Çernobil faciası", "Bilgisayar", "Mikroişlemci",
    "Wi-Fi", "Bluetooth", "5G", "Sanal gerçeklik", "Robot", "Evrim", "Yerçekimi", "Enerji",
    "Bulut bilişim", "Siber güvenlik", "Açık kaynak", "Video oyunu", "Sinema", "Müzik",
]

PRODUCT_TOPICS = [
    "iPhone 15", "Samsung Galaxy S24", "PlayStation 5", "Xbox Series X", "Nintendo Switch",
    "Steam Deck", "MacBook Air", "AirPods Pro", "Apple Watch", "Tesla Model 3", "Kindle",
    "GoPro", "Raspberry Pi", "GeForce RTX 4090", "Ryzen 7 7800X3D", "Meta Quest 3",
    "Google Pixel 8", "Xiaomi 14", "Sony WH-1000XM5", "Logitech G Pro",
]


class IdleLearner:
    """Kullanıcı boştayken periyodik olarak bir konu öğrenen arka plan iş parçacığı."""

    FIRST_DELAY = 90       # açılıştan ilk denemeye kadar (sn)
    INTERVAL = 300         # iki öğrenme arası (sn)
    IDLE_AFTER = 120       # kullanıcı bu kadar sn soru sormadıysa "boşta" say

    def __init__(
        self,
        memory,
        is_online: Callable[[], bool],
        idle_seconds: Callable[[], float],
        on_learned: Optional[Callable[[Dict], None]] = None,
    ):
        self._memory = memory
        self._is_online = is_online
        self._idle_seconds = idle_seconds
        self._on_learned = on_learned
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._tried: set = set()
        self.last_result: Optional[Dict] = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="MehburAI-IdleLearner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        if self._stop.wait(self.FIRST_DELAY):
            return
        while not self._stop.is_set():
            try:
                if (get_learn_config()["auto_learn_enabled"]
                        and self._is_online()
                        and self._idle_seconds() >= self.IDLE_AFTER):
                    self.learn_once()
            except Exception:
                pass
            if self._stop.wait(self.INTERVAL):
                return

    def _pick_topic(self) -> Optional[tuple]:
        """(konu, ürün_mü) — henüz denenmemiş rastgele bir konu; hepsi bittiyse listeyi sıfırla."""
        for _ in range(2):
            want_product = random.random() < 0.35
            pool = [t for t in (PRODUCT_TOPICS if want_product else GENERAL_TOPICS) if t not in self._tried]
            if not pool:
                pool = [t for t in (GENERAL_TOPICS if want_product else PRODUCT_TOPICS) if t not in self._tried]
                want_product = not want_product
            if pool:
                return random.choice(pool), want_product
            self._tried.clear()
        return None

    def learn_once(self, topic: Optional[str] = None) -> Optional[Dict]:
        """Bir konu öğrenip hafızaya yazar. Başarılıysa {"topic","source","product"} döner."""
        if topic:
            is_product = TrustedSourceFetcher.is_product_query(topic)
        else:
            picked = self._pick_topic()
            if picked is None:
                return None
            topic, is_product = picked
        self._tried.add(topic)

        wiki = TrustedSourceFetcher.search_wikipedia(topic, product=is_product)
        if not wiki:
            return None
        question = f"{topic} özellikleri ve incelemeleri" if is_product else f"{topic} nedir"
        answer = wiki["extract"] + "\n\n" + TrustedSourceFetcher.source_footer(wiki)
        sources = ["Wikipedia"]

        source_label = "otomatik öğrenme (" + " + ".join(sources) + ")"
        self._memory.save_knowledge(question=question, answer=answer, source=source_label)
        result = {"topic": topic, "source": source_label, "product": is_product, "time": time.time()}
        self.last_result = result
        if self._on_learned:
            try:
                self._on_learned(result)
            except Exception:
                pass
        return result
