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

import socket
import threading
import time
from typing import Callable, Optional

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

    def _check_connection(self) -> bool:
        """
        Cloudflare DNS'e socket bağlantısı açarak internet durumunu kontrol eder.

        Bu yöntem HTTP isteği yapmaz, yalnızca TCP socket bağlantısı
        dener — bu da onu ultra hızlı (~50ms) yapar.

        Returns:
            bool: True ise bağlantı başarılı, False ise başarısız.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            result = sock.connect_ex((self._host, self._port))
            sock.close()
            return result == 0
        except (socket.error, OSError):
            return False

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
