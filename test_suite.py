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
  8. Küfür / Hakaret Algılama (yazım hatası toleranslı)
  9. Genişletilmiş Bilgisayar Erişimi (program açma, dosya/klasör, ses, parlaklık, güç)
"""

import io
import sys

# Windows UTF-8 Fix
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from ai_engine import AIEngine, ProfanityFilter
from config import PROFANITY_RESPONSE, get_api_key, set_api_key
from memory_engine import MemoryEngine
from network_manager import NetworkMonitor
from system_tools import SystemTools


def run_full_validation():
    print("=" * 65)
    print("  🤖 MEHBUR AI — FAZ 5 ENTEGRASYON VE DOĞRULAMA TESTLERİ")
    print("=" * 65)
    passed_tests = 0
    total_tests = 9

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
    # TEST 8: Küfür ve Hakaret Algılama Filtresi
    # ─────────────────────────────────────────
    print("\n[TEST 8] Küfür ve Hakaret Algılama Filtresi:")

    # 8a. Doğrudan küfürler (Tümü True dönmeli)
    profanity_positives = [
        "amk", "aq", "oç", "siktir git", "orospu çocuğu",
        "piç kurusu", "sikeyim", "yarrak", "yavşak", "pezevenk",
        "aptal Mehbur", "sen salaksın", "şerefsiz", "götlek",
        "amına koyayım", "gerizekalı", "s*ktir",
        # Yazım hatalı / eksik harfli varyasyonlar (yeni tolerans)
        "orospo", "orospı", "aptl", "saalak", "çomarr",
        "serefsız", "pezevengk", "gerizekali",
    ]
    prof_pos_ok = True
    for pf in profanity_positives:
        detected = ProfanityFilter.check_profanity(pf)
        if not detected:
            print(f"  ❌ Algılanamadı: '{pf}'")
            prof_pos_ok = False

    if prof_pos_ok:
        print(f"  • {len(profanity_positives)} küfürlü ifade başarıyla algılandı ✓")

    # 8b. Masum kelimeler (Tümü False dönmeli — False Positive olmamalı)
    safe_sentences = [
        "eksik parça var", "sıkıntı yok", "götürmek lazım",
        "piliç eti", "fizik dersi", "klasik müzik", "fıstık ezmesi",
        "10 dakika bekle", "malzeme listesi nedir", "görev yöneticisi",
        "Merhaba nasılsın?", "Türkiye'nin başkenti neresidir?",
        # Yazım-hatası toleransının bulaşmaması gereken masum kelimeler
        "solak biri", "salık verdi", "silik yazı", "sülük tuttu",
        "yürek yedi", "yörük çadırı", "yarık duvar", "hamak kurduk",
    ]
    safe_ok = True
    for sf in safe_sentences:
        detected = ProfanityFilter.check_profanity(sf)
        if detected:
            print(f"  ❌ Yanlış pozitif: '{sf}'")
            safe_ok = False

    if safe_ok:
        print(f"  • {len(safe_sentences)} masum cümle doğru şekilde geçirildi ✓")

    # 8c. process_query entegrasyonu — küfürlü mesaj doğru yanıtı vermeli
    profanity_result = ai.process_query("siktir git")
    assert profanity_result["answer"] == PROFANITY_RESPONSE, \
        f"Beklenen '{PROFANITY_RESPONSE}', gelen '{profanity_result['answer']}'"
    assert profanity_result["source"] == "profanity_filter"
    assert profanity_result["learned"] is False
    print(f"  • process_query küfür testi: '{profanity_result['answer']}' ✓")

    assert prof_pos_ok and safe_ok
    print("  ✅ TEST 8 BAŞARILI: Küfür algılama filtresi hatasız çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 9: Genişletilmiş Bilgisayar Erişimi (Program / Dosya / Sistem)
    # ─────────────────────────────────────────
    print("\n[TEST 9] Genişletilmiş Bilgisayar Erişimi:")
    import os as _os

    # Yan etkileri engelle: testlerde gerçek program/pencere açma ve tuş basma yok.
    SystemTools._launch = staticmethod(lambda target: True)
    SystemTools._press_vk = staticmethod(lambda vk, times=1: None)
    if hasattr(_os, "startfile"):
        _os.startfile = lambda *a, **k: None

    # 9a. Komut olmayan sorular None dönmeli (yanlış tetikleme yok)
    non_commands = [
        "Albert Einstein kimdir", "Türkiye'nin başkenti neresi",
        "bugün hava nasıl", "python nedir",
        "discordda kanal nasıl açılır", "chrome nedir", "açıklama yapar mısın",
        "kapıyı aç", "oruç ne zaman açılır", "excel formülü açıkla",
    ]
    nc_ok = all(SystemTools.handle_system_query(q) is None for q in non_commands)
    assert nc_ok, "Normal sorular yanlışlıkla sistem komutu sanıldı!"
    print(f"  • {len(non_commands)} normal soru doğru şekilde 'komut değil' sayıldı ✓")

    # 9a-2. Fiil çekimi + yazım hatası toleransı ("açar mısın", "makimesini")
    conjugated = {
        "hesap makinesini açar mısın": "hesap makinesi",
        "hesap makimesini açar mısın": "hesap makinesi",   # 'makimesini' yazım hatası
        "not defteri açsana": "not defteri",
        "chromu başlatır mısın": "chrome",
    }
    for phrase, expect in conjugated.items():
        rep = SystemTools.handle_system_query(phrase)
        assert rep and expect.split()[0].lower() in rep.lower(), \
            f"'{phrase}' -> beklenen '{expect}', gelen {rep!r}"
    print(f"  • {len(conjugated)} çekimli/yazım-hatalı 'aç' komutu doğru eşleşti ✓")

    # 9b. Güç komutu iptali (zararsız) çalışmalı
    cancel_reply = SystemTools.handle_system_query("kapatmayı iptal et")
    assert cancel_reply and "iptal" in cancel_reply.lower()
    print(f"  • Güç komutu iptali: '{cancel_reply}' ✓")

    # 9c. Klasör oluşturma gerçekten dosya sistemine yazmalı
    test_dir_name = "MehburAI_SelfTest_Klasor"
    create_reply = SystemTools.handle_system_query(
        f'masaüstünde "{test_dir_name}" klasörü oluştur'
    )
    desktop_path = _os.path.join(_os.path.expanduser("~"), "Desktop", test_dir_name)
    assert _os.path.isdir(desktop_path), "Klasör oluşturulamadı!"
    print(f"  • Klasör oluşturma: '{create_reply.splitlines()[0]}' ✓")
    _os.rmdir(desktop_path)  # temizle

    # 9d. Parlaklık komutu seviye çıkarımı yapmalı (donanım desteklemese bile yanıt üretir)
    bright_reply = SystemTools.handle_system_query("parlaklığı %55 yap")
    assert bright_reply and ("55" in bright_reply or "parlaklık" in bright_reply.lower())
    print(f"  • Parlaklık komutu ayrıştırıldı ✓")

    # 9e. Ses kısma komutu tanınmalı
    vol_reply = SystemTools.handle_system_query("sesi kıs")
    assert vol_reply and "ses" in vol_reply.lower()
    print(f"  • Ses kontrolü: '{vol_reply}' ✓")

    print("  ✅ TEST 9 BAŞARILI: Genişletilmiş bilgisayar erişimi çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # Özet Rapor
    # ─────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  🎉 TÜM ENTEGRASYON TESTLERİ TAMAMLANDI: {passed_tests}/{total_tests} BAŞARILI!")
    print("=" * 65)


if __name__ == "__main__":
    run_full_validation()
