# -*- coding: utf-8 -*-
"""
MehburAI - Ağ Bağlantı Yöneticisi (Network Manager)
=====================================================
Cloudflare DNS (1.1.1.1) üzerinden hızlı ve periyodik
internet bağlantı durumu izleme mekanizması.

Özellikler:
  • Socket tabanlı ultra hızlı bağlantı kontrolü (~50ms)
  • Arka plan thread'i ile sürekli periyodik izleme
  • Durum değişikliğinde callback (geri çağırma) desteği
  • Thread-safe durum erişimi
"""

import queue
import socket
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from config import NetworkConfig


class NetworkMonitor:
    """
    İnternet bağlantı durumunu izleyen ve değişiklikleri
    callback fonksiyonları aracılığıyla bildiren sınıf.

    Kullanım:
        def durum_degisti(online: bool):
            print("Online" if online else "Offline")

        monitor = NetworkMonitor(on_status_change=durum_degisti)
        monitor.start()
        # ...
        monitor.stop()
    """

    def __init__(
        self,
        on_status_change: Optional[Callable[[bool], None]] = None,
        host: str = NetworkConfig.CHECK_HOST,
        port: int = NetworkConfig.CHECK_PORT,
        timeout: float = NetworkConfig.CHECK_TIMEOUT,
        interval: float = NetworkConfig.CHECK_INTERVAL,
    ):
        """
        NetworkMonitor başlatıcı.

        Args:
            on_status_change: Bağlantı durumu değiştiğinde çağrılacak fonksiyon.
                              Parametre olarak bool alır (True=online, False=offline).
            host: Kontrol edilecek hedef adres (varsayılan: Cloudflare 1.1.1.1).
            port: Kontrol edilecek hedef port (varsayılan: 53 DNS).
            timeout: Bağlantı zaman aşımı süresi (saniye).
            interval: Periyodik kontrol aralığı (saniye).
        """
        self._host = host
        self._port = port
        # Varsayılan hedefse Cloudflare + Google hedeflerinin hepsi, özel host/port verildiyse yalnızca o
        if (host, port) == (NetworkConfig.CHECK_HOST, NetworkConfig.CHECK_PORT):
            self._targets: List[Tuple[str, str, int]] = list(NetworkConfig.CHECK_TARGETS)
        else:
            self._targets = [("Özel hedef", host, port)]
        self.last_target: Optional[str] = None   # son başarılı kontrolün hedefi (ör. "Cloudflare DNS 1.1.1.1:53")
        self._timeout = timeout
        self._interval = interval
        self._on_status_change = on_status_change

        # Thread-safe durum yönetimi
        self._lock = threading.Lock()
        self._is_online: Optional[bool] = None  # Başlangıçta bilinmeyen
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

        # İlk kontrolü hemen yap
        self._is_online = self._check_connection()

    # ─────────────────────────────────────────
    # Genel API
    # ─────────────────────────────────────────

    @property
    def is_online(self) -> bool:
        """Mevcut internet bağlantı durumunu döndürür (thread-safe)."""
        with self._lock:
            return bool(self._is_online)

    @property
    def status_text(self) -> str:
        """Kullanıcı dostu durum metni döndürür."""
        return "🟢 Çevrimiçi" if self.is_online else "🔴 Çevrimdışı"

    def check_now(self) -> bool:
        """
        Anlık bağlantı kontrolü yapar ve durumu günceller.

        Returns:
            bool: True ise internet bağlı, False ise değil.
        """
        new_status = self._check_connection()
        self._update_status(new_status)
        return new_status

    def start(self) -> None:
        """Arka planda periyodik bağlantı izlemeyi başlatır."""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="MehburAI-NetworkMonitor",
            daemon=True,  # Ana uygulama kapanınca otomatik sonlanır
        )
        self._monitor_thread.start()

    def stop(self) -> None:
        """Periyodik bağlantı izlemeyi durdurur."""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=self._timeout + 1)
            self._monitor_thread = None

    # ─────────────────────────────────────────
    # Dahili Mekanizma
    # ─────────────────────────────────────────

    def _probe(self, host: str, port: int) -> Tuple[bool, int]:
        """Tek hedefe TCP bağlantısı dener. (başarılı_mı, gecikme_ms)"""
        t0 = time.time()
        try:
            with socket.create_connection((host, port), timeout=self._timeout):
                return True, int((time.time() - t0) * 1000)
        except OSError:
            return False, int((time.time() - t0) * 1000)

    def _probe_all(self, wait_for_all: bool) -> List[Dict]:
        """Tüm hedefleri PARALEL dener. `wait_for_all=False` ise ilk başarıda hemen döner."""
        results: "queue.Queue[Dict]" = queue.Queue()

        def worker(label: str, host: str, port: int) -> None:
            ok, ms = self._probe(host, port)
            results.put({"label": label, "host": host, "port": port, "ok": ok, "ms": ms})

        for label, host, port in self._targets:
            threading.Thread(target=worker, args=(label, host, port), daemon=True).start()

        collected: List[Dict] = []
        for _ in self._targets:
            try:
                r = results.get(timeout=self._timeout + 1.0)
            except queue.Empty:
                break
            collected.append(r)
            if r["ok"] and not wait_for_all:
                break
        order = {(h, p): i for i, (_, h, p) in enumerate(self._targets)}
        return sorted(collected, key=lambda r: order.get((r["host"], r["port"]), 99))

    def _check_connection(self) -> bool:
        """
        İnternet var mı? Cloudflare (1.1.1.1) ve Google (8.8.8.8) hedeflerine paralel
        TCP bağlantısı denenir; herhangi biri açılırsa çevrimiçi sayılır (~50 ms).
        HTTP isteği yapılmaz, yalnızca soket bağlantısı denenir.
        """
        for r in self._probe_all(wait_for_all=False):
            if r["ok"]:
                self.last_target = f"{r['label']} {r['host']}:{r['port']}"
                return True
        return False

    def diagnose(self) -> List[Dict]:
        """
        Ayarlar'daki 'Bağlantıyı Şimdi Test Et' için: tüm hedefleri dener, durumu günceller ve
        her hedef için {label, host, port, ok, ms} listesi döndürür.
        """
        results = self._probe_all(wait_for_all=True)
        online = any(r["ok"] for r in results)
        if online:
            best = next(r for r in results if r["ok"])
            self.last_target = f"{best['label']} {best['host']}:{best['port']}"
        self._update_status(online)
        return results

    def _update_status(self, new_status: bool) -> None:
        """
        Durumu günceller ve değişiklik varsa callback'i tetikler.

        Args:
            new_status: Yeni bağlantı durumu.
        """
        with self._lock:
            old_status = self._is_online
            self._is_online = new_status

        # Durum değiştiyse callback'i çağır
        if old_status != new_status and self._on_status_change:
            try:
                self._on_status_change(new_status)
            except Exception as e:
                print(f"[NetworkMonitor] Callback hatası: {e}")

    def _monitor_loop(self) -> None:
        """Arka plan thread'inde çalışan periyodik izleme döngüsü."""
        while self._running:
            new_status = self._check_connection()
            self._update_status(new_status)

            # Kesintiye uğrayabilir bekleme (hızlı stop için)
            wait_elapsed = 0.0
            while wait_elapsed < self._interval and self._running:
                time.sleep(0.5)
                wait_elapsed += 0.5

    # ─────────────────────────────────────────
    # Yaşam Döngüsü Yardımcıları
    # ─────────────────────────────────────────

    def __enter__(self):
        """Context manager desteği: `with NetworkMonitor() as nm:`"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager çıkışında monitörü durdurur."""
        self.stop()
        return False

    def __repr__(self) -> str:
        status = "online" if self.is_online else "offline"
        running = "running" if self._running else "stopped"
        return (
            f"<NetworkMonitor host={self._host}:{self._port} "
            f"status={status} monitor={running}>"
        )


# ─────────────────────────────────────────────
# Hızlı Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  MehburAI - Ağ Bağlantı Testi")
    print("=" * 50)

    def on_change(online: bool):
        emoji = "🟢" if online else "🔴"
        durum = "ÇEVRİMİÇİ" if online else "ÇEVRİMDIŞI"
        print(f"\n  {emoji} Bağlantı durumu değişti: {durum}")

    monitor = NetworkMonitor(on_status_change=on_change)
    print(f"\n  İlk kontrol: {monitor.status_text}")
    print(f"  Detay: {monitor}")

    print(f"\n  Periyodik izleme başlatılıyor ({NetworkConfig.CHECK_INTERVAL}s aralık)...")
    print("  Durdurmak için Ctrl+C basın.\n")

    monitor.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n  İzleme durduruluyor...")
        monitor.stop()
        print("  ✅ NetworkMonitor durduruldu.")
