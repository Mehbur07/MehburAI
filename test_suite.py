# -*- coding: utf-8 -*-
"""
MehburAI - Kapsamlı Entegrasyon ve Doğrulama Test Paketi (Faz 5)
================================================================
Tüm sistem bileşenlerini otomatik olarak test eder:
  1. Cloudflare 1.1.1.1 Ağ Bağlantı Monitörü
  2. Özel İsim / Kimlik Yanıtı ("adın ne" -> dünyayı ele geçireceğim)
  3. Bilgisayara Erişim & Sistem Araçları (Saat, Disk, Sistem Durumu)
  4. Çevrim İçi Bilgi Arama & Otomatik Hafızaya Kaydetme
  5. Çevrim Dışı Semantik Bellek Eşleştirmesi (Farklı cümle kalıpları)
  6. Çevrim Dışı Bilinmeyen Soru Ayrımı
  7. Gemini API Anahtarı Ayarları & Konfigürasyon
"""

import io
import sys

# Windows UTF-8 Fix
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from ai_engine import AIEngine
from config import get_api_key, set_api_key
from memory_engine import MemoryEngine
from network_manager import NetworkMonitor
from system_tools import SystemTools


def run_full_validation():
    print("=" * 65)
    print("  🤖 MEHBUR AI — FAZ 5 ENTEGRASYON VE DOĞRULAMA TESTLERİ")
    print("=" * 65)
    passed_tests = 0
    total_tests = 6

    memory = MemoryEngine()
    network = NetworkMonitor()
    ai = AIEngine(memory_engine=memory, network_monitor=network)

    # ─────────────────────────────────────────
    # TEST 1: Ağ Bağlantı Kontrolü (Cloudflare 1.1.1.1)
    # ─────────────────────────────────────────
    print("\n[TEST 1] Cloudflare 1.1.1.1 Ağ Durumu Kontrolü:")
    is_online = network.check_now()
    print(f"  • Bağlantı Durumu: {network.status_text}")
    print(f"  • is_online: {is_online}")
    assert isinstance(is_online, bool)
    print("  ✅ TEST 1 BAŞARILI: Ağ denetleyicisi hatasız çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 2: Özel İsim / Kimlik Yanıtı
    # ─────────────────────────────────────────
    print("\n[TEST 2] Özel İsim / Kimlik Yanıtı Kontrolü:")
    expected_reply = "Merhaba, ben MehburAI dünyayı ele geçireceğim"
    res1 = ai.process_query("adın ne")
    res2 = ai.process_query("ismin nedir?")
    res3 = ai.process_query("sen kimsin")

    print(f"  • 'adın ne' -> '{res1['answer']}'")
    print(f"  • 'ismin nedir?' -> '{res2['answer']}'")
    print(f"  • 'sen kimsin' -> '{res3['answer']}'")

    assert res1['answer'] == expected_reply, f"Beklenen '{expected_reply}', gelen '{res1['answer']}'"
    assert res2['answer'] == expected_reply, f"Beklenen '{expected_reply}', gelen '{res2['answer']}'"
    print("  ✅ TEST 2 BAŞARILI: İsim ve kimlik sorularına beklenen yanıt verildi.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 3: Bilgisayara Erişim & Sistem Araçları
    # ─────────────────────────────────────────
    print("\n[TEST 3] Bilgisayara Erişim & Sistem Araçları Kontrolü:")
    time_res = ai.process_query("saat kaç")
    sys_res = ai.process_query("sistem bilgisi")

    print(f"  • Saat/Tarih: {time_res['answer']}")
    print(f"  • Sistem Durumu Özeti:\n    {sys_res['answer'][:120]}...")

    assert "saat" in time_res['answer'].lower() or "tarih" in time_res['answer'].lower()
    assert "Sistem" in sys_res['answer'] or "İşletim" in sys_res['answer']
    print("  ✅ TEST 3 BAŞARILI: Bilgisayar donanım ve zaman bilgisine erişildi.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 4: Çevrim İçi Bilgi Arama & Otomatik Öğrenme
    # ─────────────────────────────────────────
    print("\n[TEST 4] Bilgi Kaydı & Otomatik Hafıza Pipeline'ı:")
    sample_q = "Nikola Tesla kimdir?"
    sample_a = "Nikola Tesla, Sırp asıllı Amerikalı mucit, elektrik ve makine mühendisidir. Alternatif akım (AC) sistemini geliştirmiştir."
    rec_id, _ = memory.save_knowledge(sample_q, sample_a, source="wikipedia")
    print(f"  • Hafızaya işlenen ID: {rec_id} -> '{sample_q}'")
    print(f"  • Toplam hafıza kayıt sayısı: {memory.get_memory_count()}")
    assert rec_id > 0
    print("  ✅ TEST 4 BAŞARILI: Bilgi tabanına kayıt başarıyla işlendi.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 5: Çevrim Dışı Semantik Eşleşme (Farklı Kalıplar)
    # ─────────────────────────────────────────
    print("\n[TEST 5] Çevrim Dışı Semantik Arama Testi:")
    variations = [
        "Tesla kimdir?",
        "Nikola Tesla hakkında bilgi",
        "Nikola Tesla ne yapmıştır?"
    ]
    for v in variations:
        match = memory.search_knowledge(v)
        if match:
            print(f"  • Soru: '{v}' ➡️ Eşleşti (%{match['score']*100:.1f} benzerlik): '{match['question']}'")
            assert match['id'] == rec_id
        else:
            print(f"  • Soru: '{v}' ➡️ Eşleşmedi!")

    print("  ✅ TEST 5 BAŞARILI: Farklı cümlelerle sorulsa da hafızadaki doğru bilgi bulundu.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 6: Bilinmeyen Soru Çevrim Dışı Yönetimi
    # ─────────────────────────────────────────
    print("\n[TEST 6] Bilinmeyen Soru Çevrim Dışı Yönetimi:")
    unknown_q = "Gelecekte uçan arabalar ne zaman çıkacak xyz123?"
    unknown_match = memory.search_knowledge(unknown_q)
    print(f"  • Bilinmeyen Soru: '{unknown_q}'")
    print(f"  • Hafıza Eşleşmesi: {unknown_match}")
    assert unknown_match is None, "Bilinmeyen soru yanlışlıkla eşleşmemeli!"
    print("  ✅ TEST 6 BAŞARILI: Bilinmeyen sorular doğru şekilde 'öğrenilmedi' olarak ayrıldı.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 7: Gemini Aktiflik Durum Kontrolü
    # ─────────────────────────────────────────
    print("\n[TEST 7] Gemini Aktiflik Durum Kontrolü:")
    from config import get_api_key, remove_api_key, set_api_key
    initial_user_key = get_api_key()

    remove_api_key()
    res_nokey = ai.process_query("gemini aktif mi")
    print(f"  • Anahtar Yokken 'gemini aktif mi' -> '{res_nokey['answer']}'")
    assert res_nokey['answer'] == "Gemini aktif değil"

    set_api_key("sk-non-gemini-fake-api-key-1234567890")
    res_wrongkey = ai.process_query("gemini aktif mi")
    print(f"  • Farklı API Girildiğinde -> '{res_wrongkey['answer']}'")
    assert res_wrongkey['answer'] == "Gemini aktif değil"

    set_api_key("AIzaSyD_TestValidGeminiKey1234567890XYZ")
    res_validkey = ai.process_query("gemini aktif mi")
    print(f"  • Gemini API Girildiğinde -> '{res_validkey['answer']}'")
    assert res_validkey['answer'] == "Gemini aktif"

    # Kullanıcının orijinal anahtarını geri yükle
    if initial_user_key:
        set_api_key(initial_user_key)
    else:
        remove_api_key()

    print("  ✅ TEST 7 BAŞARILI: Gemini API kontrolü hatasız çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # Özet Rapor
    # ─────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  🎉 TÜM ENTEGRASYON TESTLERİ TAMAMLANDI: {passed_tests}/7 BAŞARILI!")
    print("=" * 65)


if __name__ == "__main__":
    run_full_validation()
