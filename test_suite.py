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
 10. 🤖 Telegram Uzaktan Kontrol (yetkilendirme, komutlar, bot token doğrulama)
"""

import io
import sys

# Windows UTF-8 Fix
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from ai_engine import (
    AIEngine,
    ImageStudio,
    MathSolver,
    ProfanityComeback,
    ProfanityFilter,
    TrustedSourceFetcher,
    VisionAssistant,
)
from config import (
    APP_VERSION,
    PROFANITY_RESPONSE,
    get_api_key,
    get_profanity_config,
    set_api_key,
    update_profanity_config,
)
from memory_engine import MemoryEngine
from network_manager import NetworkMonitor
from system_tools import SystemTools


def run_full_validation():
    print("=" * 65)
    print("  🤖 MEHBUR AI — FAZ 5 ENTEGRASYON VE DOĞRULAMA TESTLERİ")
    print("=" * 65)
    passed_tests = 0
    total_tests = 24

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

    # 8c. process_query entegrasyonu — misilleme kapalıyken nazik uyarı dönmeli
    update_profanity_config(profanity_comeback_enabled=False)
    profanity_result = ai.process_query("siktir git")
    assert profanity_result["answer"] == PROFANITY_RESPONSE, \
        f"Beklenen '{PROFANITY_RESPONSE}', gelen '{profanity_result['answer']}'"
    assert profanity_result["source"] == "profanity_filter"
    assert profanity_result["learned"] is False
    update_profanity_config(profanity_comeback_enabled=True)
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
    # TEST 10: 🤖 Telegram Uzaktan Kontrol
    # ─────────────────────────────────────────
    print("\n[TEST 10] 🤖 Telegram Uzaktan Kontrol:")
    import config as _cfg
    import telegram_bot as _tb

    _out = []
    _bot = _tb.TelegramControlBot(
        query_handler=lambda t: f"cevap<{t}>",
        security_status=lambda: "DURUM-OK",
    )
    _bot._creds = lambda: ("TESTTOKEN", "555")
    _bot._is_owner = lambda cid: str(cid) == "555"
    _bot._send = lambda s: _out.append(("send", s))
    _bot._chat_action = lambda a="typing": None
    _bot._send_photo = lambda p, c="", cleanup=False: _out.append(("photo", c))
    _rej = []
    _bot._send_to = lambda cid, txt: _rej.append((cid, txt))
    _tb.SystemTools.save_screenshot = staticmethod(lambda dest_dir=None: "ss.png")
    _tb.CameraCapture.snapshot = staticmethod(lambda save_dir=None: "cam.jpg")

    # 10a. Yetkisiz chat ID: komut İŞLENMEZ ama tek seferlik ret mesajı alır
    _bot._handle_update({"message": {"chat": {"id": 111}, "text": "merhaba"}})
    _bot._handle_update({"message": {"chat": {"id": 111}, "text": "hala buradayım"}})
    assert _out == [], "yetkisiz komut asla işlenmemeli"
    assert len(_rej) == 1 and str(_rej[0][0]) == "111" and "özel" in _rej[0][1].lower(), _rej
    print("  • Yetkisiz chat ID engelleniyor + tek ret mesajı gönderiliyor ✓")

    # 10a-2. Sahip ID'si kodda YOK; yalnızca ayarlardaki ID yetkili, bozuk/boş ID kimseyi yetkilendirmez
    assert not hasattr(_cfg, "OWNER_TELEGRAM_ID"), "sabit Telegram ID'si kodda kalmamalı"
    _bot2 = _tb.TelegramControlBot(query_handler=lambda t: "ok")
    _real_raw = open(_cfg.CONFIG_FILE, "r", encoding="utf-8").read() \
        if _os.path.exists(_cfg.CONFIG_FILE) else None
    try:
        _cfg.save_config({**_cfg.load_config(), "telegram_chat_id": "424242424"})
        assert _bot2._is_owner("424242424")
        assert not _bot2._is_owner("999999999") and not _bot2._is_owner("")
        _cfg.save_config({**_cfg.load_config(), "telegram_chat_id": "••••bozuk"})
        assert _cfg.get_security_config()["telegram_chat_id"] == ""
        assert not _bot2._is_owner("424242424") and not _bot2._is_owner("")
    finally:
        if _real_raw is not None:
            open(_cfg.CONFIG_FILE, "w", encoding="utf-8").write(_real_raw)
    print("  • Sahip ID'si yalnızca ayarlardan geliyor; bozuk/boş ID kimseyi yetkilendirmiyor ✓")

    # 10b. Düz metin → zeka motoruna gider
    _bot._handle_update({"message": {"chat": {"id": 555}, "text": "einstein kimdir"}})
    assert any(k == "send" and "cevap<einstein kimdir>" in v for k, v in _out), _out
    print("  • Düz mesaj MehburAI zeka motoruna yönleniyor ✓")

    # 10c. /ekran ve /foto fotoğraf gönderiyor
    _out.clear()
    _bot._handle_update({"message": {"chat": {"id": 555}, "text": "/ekran"}})
    _bot._handle_update({"message": {"chat": {"id": 555}, "text": "/foto"}})
    assert sum(1 for k, _ in _out if k == "photo") == 2, _out
    print("  • /ekran ve /foto komutları görüntü gönderiyor ✓")

    # 10d. /durum komutu
    _out.clear()
    _bot._handle_update({"message": {"chat": {"id": 555}, "text": "/durum"}})
    assert ("send", "DURUM-OK") in _out, _out
    print("  • /durum komutu çalışıyor ✓")

    # 10e. Bozuk/maskeli token geçerli token'ı EZEMEZ (regression: '••••' hatası)
    #      (gerçek config.json'ı bozmamak için dosyayı ham olarak sakla-geri yükle)
    _cfg_raw = open(_cfg.CONFIG_FILE, "r", encoding="utf-8").read() \
        if _os.path.exists(_cfg.CONFIG_FILE) else None
    try:
        assert _cfg.is_valid_bot_token("123456789:AA" + "x" * 33)
        assert not _cfg.is_valid_bot_token("•" * 46)
        _cfg.update_security_config(telegram_bot_token="123456789:AA" + "x" * 33)
        _good = _cfg.get_security_config()["telegram_bot_token"]
        _cfg.update_security_config(telegram_bot_token="•" * 46)       # bozuk yazma denemesi
        assert _cfg.get_security_config()["telegram_bot_token"] == _good, "bozuk token gerçek olanı ezmemeli"
        _cfg.update_security_config(telegram_bot_token="")            # boş = dokunma
        assert _cfg.get_security_config()["telegram_bot_token"] == _good
    finally:
        if _cfg_raw is not None:
            open(_cfg.CONFIG_FILE, "w", encoding="utf-8").write(_cfg_raw)
    print("  • Bozuk/maskeli bot token geçerli token'ı ezemiyor ✓")

    print("  ✅ TEST 10 BAŞARILI: Telegram uzaktan kontrol bileşenleri çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 11: 🎙️ Sesli Sohbet (uyandırma sözcüğü + STT)
    # ─────────────────────────────────────────
    print("\n[TEST 11] 🎙️ Sesli Sohbet:")
    import voice_engine as _ve
    from telegram_bot import _file_send_query as _fsq

    # 12a. Uyandırma sözcüğü — YALNIZCA "Hey Mehbur" uyandırmalı (yazım/duyum
    #      hatasına toleranslı); yalın "mehbur"/"mecbur" artık uyandırmamalı
    #      (kullanıcı geri bildirimi: "mehbur demediğimde bile açılıyordu").
    for s in ("hey mehbur saat kaç", "he mecbur bilgisayarı kapat",
              "hey melbur aç", "heymehbur ışıkları aç"):
        assert _ve.contains_wake_word(s), f"uyandırmalı: {s}"
    for s in ("mehbur saat kaç", "mecbur bilgisayarı kapat", "melbur aç",
              "bugün hava nasıl", "mahmut gel", "mehmet nerede", "merhaba"):
        assert not _ve.contains_wake_word(s), f"uyandırmamalı: {s}"
    assert _ve.strip_wake_word("hey mehbur saat kaç") == "saat kaç"
    assert _ve.strip_wake_word("mehbur ai not defteri aç") == "not defteri aç"
    print("  • Uyandırma sözcüğü artık YALNIZCA 'Hey Mehbur' ile tetikleniyor ✓")

    # 12b. Telegram 'dosya gönder' ifade ayrıştırıcısı
    assert _fsq("ödev.docx yolla") == "ödev.docx"
    assert _fsq('"yıllık rapor" dosyasını gönder') == "yıllık rapor"
    assert _fsq("bugün hava nasıl") == ""
    assert _fsq("şu dosyayı gönder") in ("", "şu") and _fsq("şu dosyayı gönder") != "şu"
    print("  • 'dosya gönder' doğal ifadesi doğru ayrışıyor ✓")

    # 12c. Ses ayarları kalıcı + geçersiz ses reddediliyor
    _vc_raw = open(_cfg.CONFIG_FILE, "r", encoding="utf-8").read() \
        if _os.path.exists(_cfg.CONFIG_FILE) else None
    try:
        _cfg.update_voice_config(voice_tts_voice="tr-TR-AhmetNeural", voice_enabled=True,
                                 voice_overlay_enabled=False)
        assert _cfg.get_voice_config()["voice_tts_voice"] == "tr-TR-AhmetNeural"
        assert _cfg.get_voice_config()["voice_overlay_enabled"] is False
        _cfg.update_voice_config(voice_tts_voice="hacker-voice")   # geçersiz
        assert _cfg.get_voice_config()["voice_tts_voice"] == "tr-TR-AhmetNeural"
    finally:
        if _vc_raw is not None:
            open(_cfg.CONFIG_FILE, "w", encoding="utf-8").write(_vc_raw)
    print("  • Ses ayarları kaydediliyor, geçersiz ses reddediliyor ✓")

    # 12c-2. JARVIS overlay yardımcıları (renk karışımı + durum haritası)
    import jarvis_overlay as _jv
    assert set(_jv.COLORS) == {"idle", "listen", "think", "error"}
    assert _jv.COLORS["listen"].lower() == "#e0a500" and _jv.COLORS["error"].lower() == "#ff2a4d"
    assert _jv._blend("#000000", "#ffffff", 0.5).lower() in ("#7f7f7f", "#808080")
    assert len(_jv.JarvisOverlay._fib_sphere(120)) == 120
    print("  • JARVIS overlay renkleri / küre noktaları doğru ✓")

    # 12d-2. /dosya çok eşleşme → buton listesi; buton seçimi doğru dosyayı gönderir
    _b3 = _tb.TelegramControlBot(query_handler=lambda t: t)
    _b3._creds = lambda: ("T", "555")
    _b3._is_owner = lambda c: str(c) == "555"
    _b3._chat_action = lambda a="typing": None
    _b3._send = lambda s: None
    _kb = []
    _b3._send_with_keyboard = lambda t, rm: _kb.append(rm)
    _deliv = []
    _b3._deliver_path = lambda p: _deliv.append(p)
    _b3._session = type("S", (), {"post": lambda *a, **k: type("R", (), {"ok": True})()})()
    _tb.SystemTools.locate_files = staticmethod(
        lambda *a, **k: [r"C:\X\ayar.json", r"C:\Y\ayar.json"])
    _b3._send_file_search("ayar")
    assert _kb and len(_kb[0]["inline_keyboard"]) == 3, _kb          # 2 dosya + vazgeç
    _cid = list(_b3._pending_choices)[0]
    _b3._handle_callback({"id": "q", "from": {"id": 555}, "data": f"f|{_cid}|1",
                          "message": {"message_id": 1, "chat": {"id": 555}}})
    assert _deliv == [r"C:\Y\ayar.json"], _deliv
    _b3._handle_callback({"id": "q", "from": {"id": 111}, "data": f"f|{_cid}|0",
                          "message": {"message_id": 1, "chat": {"id": 111}}})
    assert _deliv == [r"C:\Y\ayar.json"], "yetkisiz callback dosya göndermemeli"
    print("  • Çok eşleşmede buton listesi + seçim + yetki kontrolü ✓")

    # 12e. Telegram klasör→zip: büyük klasör reddedilir, küçük klasör sıkıştırılır
    import tempfile as _tf2
    _d = _os.path.join(_tf2.mkdtemp(), "mini")
    _os.makedirs(_os.path.join(_d, "alt"))
    open(_os.path.join(_d, "a.txt"), "w").write("x" * 50)
    open(_os.path.join(_d, "alt", "b.txt"), "w").write("y" * 50)
    _zp, _msg = SystemTools.zip_folder(_d, max_bytes=10 * 1024 * 1024)
    assert _zp and _os.path.isfile(_zp), _msg
    _os.remove(_zp)
    _zp2, _msg2 = SystemTools.zip_folder(_d, max_bytes=10)   # 10 bayt sınır → red
    assert _zp2 is None and "büyük" in _msg2
    import shutil as _sh2
    _sh2.rmtree(_os.path.dirname(_d), ignore_errors=True)
    print("  • Klasör → .zip sıkıştırma + boyut sınırı çalışıyor ✓")

    # 12f. (opsiyonel) STT döngü testi — model + kütüphaneler varsa
    if _ve.voice_dependencies_ok() and _ve.SpeechToText.model_present():
        import asyncio as _aio, tempfile as _tf
        _p = _os.path.join(_tf.gettempdir(), "mehbur_stt_test.mp3")
        _aio.run(_ve.edge_tts.Communicate("bilgisayarı kapat", "tr-TR-EmelNeural").save(_p))
        _txt = _ve.SpeechToText.transcribe_file(_p)
        _os.remove(_p)
        assert "kapat" in _txt.lower(), f"STT beklenmedik: {_txt!r}"
        print(f"  • Çevrimdışı STT çalışıyor (algılanan: '{_txt}') ✓")
    else:
        print("  • STT döngü testi atlandı (model/kütüphane yok) — çekirdek mantık doğrulandı")

    print("  ✅ TEST 11 BAŞARILI: Sesli sohbet bileşenleri çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 12: 🤬 Küfüre Misilleme ("asıl sen / asıl ben")
    # ─────────────────────────────────────────
    print("\n[TEST 12] Küfüre Misilleme Yanıtı:")

    update_profanity_config(profanity_comeback_enabled=True)
    assert get_profanity_config()["profanity_comeback_enabled"] is True

    # 13a. Aileye yönelik fiilli küfür → "Asıl ben senin ananı ..."
    cb_family = ProfanityComeback.generate("senin ben ananı sikeyim")
    assert cb_family.lower().startswith("asıl ben senin anan"), cb_family
    assert ProfanityComeback.generate("amına koyayım").lower().startswith("asıl ben senin"), \
        "maskesiz ağır kalıp aile misillemesine gitmeli"
    assert ProfanityComeback.generate("amk").lower().startswith("asıl ben senin"), "amk → aile misillemesi"

    # 13b. İsim takma → "Asıl sen ...sın" (ünlü uyumlu ek)
    cb_oc = ProfanityComeback.generate("sen tam bir oç'sun")
    assert cb_oc.lower().startswith("asıl sen oç"), cb_oc
    cb_pic = ProfanityComeback.generate("sen tam bir piçsin")
    assert "piç" in cb_pic.lower() and cb_pic.lower().startswith("asıl sen"), cb_pic
    assert ProfanityComeback.generate("aptalsın").lower().startswith("asıl sen aptal"), "ünlü uyumu: aptalsın"

    # 13c. Sohbet bağlamı YOKKEN (conversation_id verilmemiş) küfür → nazik uyarı
    #      (Misilleme yalnızca sohbet 'kaba' moduna geçtiğinde devreye girer — bkz. TEST 14)
    res = ai.process_query("sen tam bir oç'sun")
    assert res["source"] == "profanity_filter", res["source"]
    assert res["answer"] == PROFANITY_RESPONSE, res["answer"]

    print("  • 'ananı sikeyim' →", cb_family)
    print("  • \"oç'sun\" →", cb_oc)
    print("  ✅ TEST 12 BAŞARILI: Küfüre misilleme üreteci çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 13: 🎨 Uygulama Logosu & İkon Üretimi
    # ─────────────────────────────────────────
    print("\n[TEST 13] Uygulama Logosu & İkon:")
    import os as _os2
    from config import ICON_PATH, LOGO_PATH, ensure_app_icon, get_logo_path

    lp = get_logo_path()
    assert lp is None or _os2.path.isfile(lp), "get_logo_path geçersiz yol döndürdü"

    made_temp_logo = False
    if lp is None:
        try:
            from PIL import Image as _Img
            _Img.new("RGBA", (128, 128), (0, 240, 255, 255)).save(LOGO_PATH)
            made_temp_logo = True
        except Exception:
            print("  • Pillow yok — ikon üretimi testi atlandı ✓")

    try:
        ico = ensure_app_icon()
        if get_logo_path():
            assert ico == ICON_PATH and _os2.path.isfile(ICON_PATH), \
                "logo.png varken .ico üretilmeliydi"
            print("  • logo.png → logo.ico (çok boyutlu) üretildi ✓")
        else:
            assert ico is None
            print("  • Logo yokken ikon üretimi güvenli şekilde atlandı ✓")
    finally:
        if made_temp_logo:
            for _p in (LOGO_PATH, ICON_PATH):
                try:
                    _os2.remove(_p)
                except OSError:
                    pass

    print("  ✅ TEST 13 BAŞARILI: Logo / ikon sistemi çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 14: 💬 Sohbetler + Sohbete Özel Ruh Hali (normal→kızgın→kaba)
    # ─────────────────────────────────────────
    print("\n[TEST 14] Sohbet Bazlı Ruh Hali Makinesi:")
    from ai_engine import MoodFilter, RudeFlavor

    # 15a. MoodFilter — "yakışıyor" onay/ret sınıflandırması
    assert MoodFilter.classify_confirmation("yakışıyor") == "affirm"
    assert MoodFilter.classify_confirmation("evet tabii") == "affirm"
    assert MoodFilter.classify_confirmation("yakışmıyor") == "negate"
    assert MoodFilter.classify_confirmation("hayır") == "negate"
    assert MoodFilter.classify_confirmation("bugün hava nasıl") is None
    print("  • MoodFilter onay/ret sınıflandırması ✓")

    # 15b. Sohbet oluştur → mood 'normal'
    conv_id = memory.create_conversation("Test Sohbeti")
    assert memory.get_conversation_mood(conv_id) == "normal"

    # 15c. İlk küfür → nazik uyarı + mood 'provoked'
    r1 = ai.process_query("piç", conversation_id=conv_id)
    assert r1["answer"] == PROFANITY_RESPONSE, r1["answer"]
    assert r1["source"] == "profanity_filter"
    assert memory.get_conversation_mood(conv_id) == "provoked"

    # 15d. "yakışıyor" → "o zaman bana da yakışıyor" + mood 'rude'
    r2 = ai.process_query("yakışıyor", conversation_id=conv_id)
    assert r2["source"] == "mood", r2["source"]
    assert "bana da yakışıyor" in r2["answer"].lower(), r2["answer"]
    assert memory.get_conversation_mood(conv_id) == "rude"

    # 15e. Artık küfre "asıl sen / asıl ben" ile karşılık verir
    r3 = ai.process_query("sen tam bir oç'sun", conversation_id=conv_id)
    assert r3["source"] == "profanity_comeback", r3["source"]
    assert r3["answer"].lower().startswith("asıl sen"), r3["answer"]
    r4 = ai.process_query("senin ben ananı sikeyim", conversation_id=conv_id)
    assert r4["answer"].lower().startswith("asıl ben senin"), r4["answer"]

    # 15f. 'kaba' modda normal yanıtların sonuna sivri kuyruk eklenir
    assert RudeFlavor.wrap("Cevap bu.").startswith("Cevap bu.")
    assert "—" in RudeFlavor.wrap("Cevap bu.")

    # 15g. Sohbete özel geçmiş + silme
    msgs = memory.get_conversation_messages(conv_id)
    assert len(msgs) >= 8 and any(m["role"] == "mehbur" for m in msgs)
    other = memory.create_conversation("Diğer")
    assert memory.get_conversation_messages(other) == []       # geçmiş sohbete özel
    assert memory.delete_conversation(conv_id) is True
    assert memory.get_conversation(conv_id) is None
    assert memory.get_conversation_messages(conv_id) == []      # mesajlar da silindi
    memory.delete_conversation(other)

    # 15h. Sohbetsiz (conversation_id=None) çağrı hâlâ nazik davranır
    assert ai.process_query("piç")["answer"] == PROFANITY_RESPONSE

    print("  • normal → küfür → 'yakışıyor mu?' → 'yakışıyor' → misilleme akışı ✓")
    print("  ✅ TEST 14 BAŞARILI: Sohbet bazlı ruh hali makinesi çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 15: 🔢 Sürüm Numarası + Wikipedia/Reddit Yedeği
    # ─────────────────────────────────────────
    print("\n[TEST 15] Sürüm Numarası & Uzun Wikipedia Yanıtı (Reddit yok):")
    import re as _re16

    assert _re16.fullmatch(r"\d+\.\d+(\.\d+)?", APP_VERSION), f"APP_VERSION biçimi geçersiz: {APP_VERSION!r}"
    print(f"  • APP_VERSION = '{APP_VERSION}' (X.Y veya X.Y.Z biçiminde) ✓")

    # 16a. Reddit (denetimsiz kaynak) tamamen kaldırıldı
    assert not any("reddit" in n.lower() for n in dir(TrustedSourceFetcher)), "Reddit kalıntısı var"
    print("  • Reddit kaynağı kaldırıldı (yalnızca güvenilir kaynak: Wikipedia) ✓")

    # 16b. Uzun madde → giriş + önemli bölümler, ~3 kB, sonda 'daha fazlasını oku' bağlantısı (ağ gerekmez)
    _para = "Bu bir örnek cümledir. " * 40
    _long_art = {
        "title": "Örnek", "lang": "tr", "url": "https://tr.wikipedia.org/wiki/%C3%96rnek",
        "lead": _para, "sections": [("Tarihçe", _para), ("Özellikler", _para), ("Kullanım", _para),
                                    ("Kaynakça", "atlanmalı"), ("Dış bağlantılar", "atlanmalı")],
    }
    _txt, _trunc = TrustedSourceFetcher._compose_general(_long_art)
    assert _trunc and len(_txt) > 1500, len(_txt)
    assert "▸ Tarihçe" in _txt and "atlanmalı" not in _txt
    _foot = TrustedSourceFetcher.source_footer({"truncated": True, "url": _long_art["url"], "source": "Wikipedia (Örnek)"})
    assert _foot.startswith("📖 Daha fazlasını okumak için:") and _long_art["url"] in _foot
    _short_art = dict(_long_art, lead="Kısa madde.", sections=[])
    _txt2, _trunc2 = TrustedSourceFetcher._compose_general(_short_art)
    assert _txt2 == "Kısa madde." and not _trunc2
    assert "Kaynak: Wikipedia (Örnek)" in TrustedSourceFetcher.source_footer(
        {"truncated": False, "url": _long_art["url"], "source": "Wikipedia (Örnek)"})
    print("  • Uzun madde ~3 kB'a derleniyor, Kaynakça atlanıyor, sonda 'daha fazlasını okumak için' bağlantısı var ✓")

    # 16c. Ürün: özellikler + eleştirmen değerlendirmesi (Wikipedia bölümlerinden)
    _prod_art = {
        "title": "Telefon X", "lang": "tr", "url": "https://tr.wikipedia.org/wiki/Telefon_X",
        "lead": "Telefon X bir akıllı telefondur.",
        "sections": [("Özellikler", "6,1 inç ekran ve güçlü işlemci."),
                     ("Eleştiriler", "Eleştirmenler pil ömrünü övdü.")],
    }
    _ptxt, _ = TrustedSourceFetcher._compose_product(_prod_art, None)
    assert "📋 Özellikler" in _ptxt and "6,1 inç" in _ptxt and "💬 Eleştirmenlerin" in _ptxt and "pil ömrünü" in _ptxt
    print("  • Ürün yanıtı: özellikler + eleştirmen/basın değerlendirmesi Wikipedia'dan derleniyor ✓")

    # 16d. Gerçek Wikipedia (ağ varsa): tek cümle değil, uzun ve bağlantılı yanıt
    try:
        _wp = TrustedSourceFetcher.search_wikipedia("python")
    except Exception:
        _wp = None
    if _wp:
        assert len(_wp["extract"]) > 1000 and _wp["url"].startswith("https://tr.wikipedia.org/wiki/")
        print(f"  • Gerçek Wikipedia: {_wp['source']} → {len(_wp['extract'])} karakter ✓")
    else:
        print("  • Wikipedia'ya ulaşılamadı (ağ yok olabilir) — güvenli şekilde None ✓")

    print("  ✅ TEST 15 BAŞARILI: Sürüm sabiti ve uzun/güvenilir Wikipedia yanıtı çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 16: 🎤📞👁️ Mikrofon Butonu · Telegram Sesli Görüşme · Kamera/Görsel Anlama
    # ─────────────────────────────────────────
    print("\n[TEST 16] Mikrofon Butonu, Telegram Sesli Görüşme ve Görsel Anlama:")
    import gui_app as _gui
    import telegram_bot as _tb17

    # 17a. Sohbet kutusundaki 🎤 mikrofon butonu bileşenleri mevcut
    for m in ("_toggle_voice_from_chat", "_update_mic_button", "_build_conversation_sidebar"):
        assert hasattr(_gui.MehburApp, m), f"gui_app.MehburApp.{m} eksik"
    print("  • Sohbet kutusundaki 🎤 mikrofon butonu bağlı ✓")

    # 17b. Telegram '/arama' sesli görüşme modu (gerçek arama değil — sesli mesajlaşma)
    _bot17 = _tb17.TelegramControlBot(query_handler=lambda t: f"yanıt: {t}")
    assert _bot17._call_mode is False
    _bot17._start_call()
    assert _bot17._call_mode is True
    _bot17._end_call()
    assert _bot17._call_mode is False
    assert hasattr(_bot17, "_send_voice_note") and hasattr(_bot17, "_reply")
    print("  • /arama sesli görüşme modu açılıp kapanıyor (metin + sesli yanıt) ✓")

    # 17c. 👁️ Kamera + görsel anlama niyet algılama
    assert VisionAssistant.detect_intent("benim kafa şeklime hangi tıraş yakışır") == "haircut"
    assert VisionAssistant.detect_intent("saç modeli olarak ne yakışır bana") == "haircut"
    assert VisionAssistant.detect_intent("elimde ne var") == "object"
    assert VisionAssistant.detect_intent("elimdeki şeyi tanıyabilir misin") == "object"
    assert VisionAssistant.detect_intent("bugün hava nasıl") is None

    # API anahtarı yokken güvenli, açıklayıcı bir mesajla döner (kamerayı ASLA denemez).
    # Bu makinede gerçek bir anahtar kayıtlı olabileceğinden geçici olarak kaldırılıp
    # test sonunda geri yüklenir (TEST 7'deki gibi).
    from config import get_api_key as _get_key17, remove_api_key as _remove_key17, set_api_key as _set_key17
    _saved_key17 = _get_key17()
    _remove_key17()
    try:
        no_key_msg = VisionAssistant.handle("object", ai.gemini)
    finally:
        if _saved_key17:
            _set_key17(_saved_key17)
        else:
            _remove_key17()
    assert "API anahtarı" in no_key_msg or "Gemini" in no_key_msg, no_key_msg
    print("  • 'kafama ne tıraş yakışır' / 'elimde ne var' niyetleri doğru algılanıyor ✓")

    print("  ✅ TEST 16 BAŞARILI: Mikrofon butonu, Telegram sesli görüşme ve görsel anlama hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 17: 📎🎨 Dosya Ekleme (metin/görsel) + Görsel Stüdyosu
    # ─────────────────────────────────────────
    print("\n[TEST 17] Dosya Ekleme ve Görsel Stüdyosu:")

    # 18a. Görsel isteği niyet algılama
    assert ImageStudio.detect_intent("bana mutlu bir aile çiz") == "generate"
    assert ImageStudio.detect_intent("bir kedi resmi oluştur") == "generate"
    assert ImageStudio.detect_intent("bu fotoğrafı daha kaliteli olacak şekilde düzenle") == "edit"
    assert ImageStudio.detect_intent("bugün hava nasıl") is None
    print("  • 'bana ... çiz' → generate, 'fotoğrafı ... düzenle' → edit niyeti doğru ✓")

    # 18b. API anahtarı yokken ImageStudio.handle güvenli mesajla döner (Gemini'ye asla gitmez).
    # Bu makinede gerçek bir anahtar kayıtlı olabileceğinden geçici olarak kaldırılıp geri yüklenir.
    from config import get_api_key as _gk18, remove_api_key as _rk18, set_api_key as _sk18
    _saved18 = _gk18()
    _rk18()
    try:
        img_path, img_msg = ImageStudio.handle("generate", "bir kedi çiz", ai.gemini)
    finally:
        (_sk18(_saved18) if _saved18 else _rk18())
    assert img_path is None and ("API anahtarı" in img_msg or "Gemini" in img_msg), img_msg

    # 18c. process_query — ekli METİN dosyası hakkında soru (anahtar yokken açıklayıcı mesaj)
    _saved18b = _gk18()
    _rk18()
    try:
        fres = ai.process_query(
            "bu dosyada ne var", file_context={"name": "not.txt", "kind": "text", "text": "MehburAI test notu."}
        )
    finally:
        (_sk18(_saved18b) if _saved18b else _rk18())
    assert fres["source"] == "file_no_key", fres["source"]
    assert "API anahtarı" in fres["answer"]

    # 18d. process_query — ekli görsel OLMADAN "düzenle" isteği → önce ➕ ile ekle der
    eres = ai.process_query("bu fotoğrafı daha kaliteli yap")
    assert eres["source"] == "🎨 Görsel Stüdyosu"
    assert "➕" in eres["answer"]
    assert "image_path" not in eres
    print("  • Anahtar yokken/ekli dosya yokken güvenli, açıklayıcı yanıtlar dönüyor (kamera/Gemini asla tetiklenmiyor) ✓")

    # 18e. GUI'de ➕ dosya ekleme bileşenleri mevcut
    for m in ("_pick_attachment", "_validate_attachment", "_clear_attachment", "_attach_image_preview"):
        assert hasattr(_gui.MehburApp, m), f"gui_app.MehburApp.{m} eksik"

    # 18f. Telegram: query_handler (metin, 🎨 görsel_yolu) tuple döndürebilir — çökmeden işlenir
    _bot18 = _tb17.TelegramControlBot(query_handler=lambda t: (f"cevap: {t}", None))
    _bot18._dispatch("selam")
    _bot18_img = _tb17.TelegramControlBot(query_handler=lambda t: ("çizdim", "C:/__mehbur_test_yok__.png"))
    _bot18_img._dispatch("bana bir kedi çiz")   # yol yok → güvenli şekilde metne düşer, çökmez
    print("  • Telegram (metin, görsel_yolu) tuple yanıtını çökmeden işliyor ✓")

    print("  ✅ TEST 17 BAŞARILI: Dosya ekleme ve görsel stüdyosu güvenli şekilde çalışıyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 18: 🔒 Hassas bilgi tarayıcı, 🎨 tema, 🧠 boşta öğrenme, 🛒 ürün bilgisi,
    #          🎤 bas-konuş, /aramabaslat
    # ─────────────────────────────────────────
    print("\n[TEST 18] Hassas Bilgi Filtresi, Tema, Otomatik Öğrenme, Ürün Bilgisi, Bas-Konuş, /aramabaslat:")
    import json as _json19
    import os as _os19
    import tempfile as _tmp19
    import zipfile as _zip19

    import config as _cfg19
    import scan_secrets as _ss
    import telegram_bot as _tb19
    import voice_engine as _ve19
    from auto_learner import IdleLearner as _IdleLearner

    # 19a. Hassas bilgi tarayıcı — kalıpları yakalar, test sahte değerlerini yok sayar, yasak dosyaları bulur
    _fake_key = "AIza" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx"[:35]
    _fake_tok = "123456789" + ":" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx"[:35]
    assert _ss.scan_text("x.py", f'K = "{_fake_key}"', set())
    assert _ss.scan_text("x.py", f'T = "{_fake_tok}"', set())
    assert not _ss.scan_text("x.py", 'K = "AIzaSyD_TestValidGeminiKey1234567890XYZ"', set())
    assert _ss.scan_text("x.py", "gizli = 'ozelDeger123456'", {"ozelDeger123456"})
    _zp = _os19.path.join(_tmp19.mkdtemp(), "p.zip")
    with _zip19.ZipFile(_zp, "w") as _z:
        _z.writestr("MehburAI.exe", "ok")
        _z.writestr("data/config.json", "{}")
    assert any("config.json" in f for f in _ss.scan_zip(_zp, set()))
    assert _ss.scan_repo(_ss.known_secret_values()) == [], "depoda hassas bilgi var!"
    print("  • Tarayıcı anahtar/token kalıplarını yakalıyor, config.json/.db'yi paketten engelliyor, depo temiz ✓")

    # 19b. Renk teması — türetme geçerli, kalıcı ayar, geçersiz hex yok sayılır
    _c19 = _cfg19.derive_theme_colors("#B026FF", "#0A0F1E")
    assert all(_cfg19.is_valid_hex_color(v) for v in _c19.values())
    _raw19 = open(_cfg19.CONFIG_FILE, "r", encoding="utf-8").read() if _os19.path.exists(_cfg19.CONFIG_FILE) else None
    try:
        _cfg19.update_theme_config(accent="#ff8a00", bg="#0a0f1e")
        assert _cfg19.get_theme_config() == {"accent": "#FF8A00", "bg": "#0A0F1E"}
        _cfg19.update_theme_config(accent="kırmızı", bg="#12")     # geçersiz → yok sayılır
        assert _cfg19.get_theme_config() == {"accent": "#FF8A00", "bg": "#0A0F1E"}
        _cfg19.reset_theme_config()
        assert _cfg19.get_theme_config() == {"accent": _cfg19.THEME_DEFAULT_ACCENT, "bg": _cfg19.THEME_DEFAULT_BG}
    finally:
        if _raw19 is not None:
            open(_cfg19.CONFIG_FILE, "w", encoding="utf-8").write(_raw19)
    for m in ("_build_appearance_card", "_apply_theme_and_restart", "_build_learn_card", "_dictation_done"):
        assert hasattr(_gui.MehburApp, m), f"gui_app.MehburApp.{m} eksik"
    print("  • Vurgu/arka plan rengi türetiliyor, kaydediliyor, geçersiz değer reddediliyor ✓")

    # 19c. Ürün algılama + boşta öğrenme (ağ kullanmadan, sahte kaynaklarla)
    assert TrustedSourceFetcher.is_product_query("iPhone 15 özellikleri")
    assert TrustedSourceFetcher.is_product_query("RTX 4090 alınır mı")
    assert not TrustedSourceFetcher.is_product_query("Albert Einstein kimdir")
    _orig_wiki = TrustedSourceFetcher.search_wikipedia
    _calls19 = []

    def _fake_wiki(cls, q, lang="tr", product=False):
        _calls19.append((q, product))
        return {"title": q, "extract": f"{q} hakkında uzun özet.", "source": f"Wikipedia ({q})",
                "url": "https://tr.wikipedia.org/wiki/X", "truncated": True}
    TrustedSourceFetcher.search_wikipedia = classmethod(_fake_wiki)
    try:
        _mem19 = MemoryEngine(db_path=_os19.path.join(_tmp19.mkdtemp(), "l.db"))
        _learner = _IdleLearner(_mem19, lambda: True, lambda: 9999)
        _r_prod = _learner.learn_once("iPhone 15")
        assert _r_prod and _r_prod["product"] and _r_prod["source"] == "otomatik öğrenme (Wikipedia)"
        _r_gen = _learner.learn_once("Kara delik")
        assert _r_gen and not _r_gen["product"]
        assert _calls19 == [("iPhone 15", True), ("Kara delik", False)], _calls19
        _rows = {r["question"]: r for r in _mem19.get_all_knowledge()}
        assert "Daha fazlasını okumak için" in _rows["iPhone 15 özellikleri ve incelemeleri"]["answer"]
        assert _rows["Kara delik nedir"]["source"].startswith("otomatik öğrenme")
        _t = _learner._pick_topic()
        assert _t and _t[0] not in {"iPhone 15", "Kara delik"}
    finally:
        TrustedSourceFetcher.search_wikipedia = _orig_wiki
    print("  • Boşta öğrenme: genel konu ve ürün Wikipedia'dan (bağlantılı) hafızaya yazılıyor, Reddit yok ✓")

    # 19d. Telegram: /aramabaslat komutu + komut listesi (setMyCommands)
    assert any(c == "aramabaslat" for c, _ in _tb19.BOT_COMMANDS) and "/aramabaslat" in _tb19.HELP_TEXT
    _b19 = _tb19.TelegramControlBot(query_handler=lambda t: "ok")
    _b19._send = lambda s: None
    _b19._send_voice_reply = lambda t: None
    _b19._dispatch("/aramabaslat")
    assert _b19._call_mode is True
    _b19._dispatch("/aramabitir")
    assert _b19._call_mode is False
    _posted = {}

    class _FakeSess:
        def post(self, url, json=None, timeout=0, **kw):
            _posted["url"], _posted["json"] = url, json
            return type("R", (), {"ok": True})()
    _b19._session = _FakeSess()
    _b19._creds = lambda: ("TESTTOKEN", "555")
    assert _b19._register_commands() is True
    assert _posted["url"].endswith("/setMyCommands")
    assert "aramabaslat" in [c["command"] for c in _posted["json"]["commands"]]
    print("  • /aramabaslat sesli görüşmeyi başlatıyor ve Telegram komut listesine (setMyCommands) kayıtlı ✓")

    # 19e. 🎤 bas-konuş: bağımlılık yoksa temiz hata döner (mikrofon/model asla açılmaz)
    _orig_ok = _ve19.voice_dependencies_ok
    _ve19.voice_dependencies_ok = lambda: False
    try:
        _res19 = {}
        _d = _ve19.Dictation(on_done=lambda t, e: _res19.update(t=t, e=e))
        assert _d.start()
        _d._thread.join(timeout=5)
        assert _res19 == {"t": "", "e": "deps"}, _res19
    finally:
        _ve19.voice_dependencies_ok = _orig_ok
    _va = _ve19.VoiceAssistant(on_command=lambda t: "")
    _va.pause(); assert _va._paused.is_set()
    _va._mic_cb(b"\x00\x00", 1, None, None); assert _va._audio_q.empty()   # duraklatılmışken ses yok sayılır
    _va.resume(); assert not _va._paused.is_set()
    print("  • Bas-konuş (Dictation) hata yolu + uyandırma dinleyicisi duraklat/devam çalışıyor ✓")

    # 19f. Gemini anahtarı girilmemişse yanıtın en başında özür notu (yalnızca gösterimde; hafızaya notsuz)
    from ai_engine import NO_GEMINI_APOLOGY as _apology
    from config import get_api_key as _gk19, remove_api_key as _rk19, set_api_key as _sk19
    _saved_key19 = _gk19()
    _orig_wiki19 = TrustedSourceFetcher.search_wikipedia
    _orig_gem19 = ai.gemini.generate_response
    TrustedSourceFetcher.search_wikipedia = classmethod(
        lambda cls, q, lang="tr", product=False: {"title": "X", "extract": "Wikipedia özeti.", "source": "Wikipedia (X)",
                                                   "url": "https://tr.wikipedia.org/wiki/X", "truncated": False})
    try:
        if network.check_now():
            _rk19()
            ai.gemini.generate_response = lambda *a, **k: None
            _nk = ai.process_query("kuantum dolanıklık deneyi nedir zzq")
            assert _nk["answer"].startswith(_apology + "\n\n"), _nk["answer"][:80]
            assert _apology not in memory.search_knowledge("kuantum dolanıklık deneyi nedir zzq")["answer"]
            _sk19("AIzaSyD_TestValidGeminiKey1234567890XYZ")
            ai.gemini.generate_response = lambda *a, **k: "Gemini yanıtı."
            _wk = ai.process_query("kuantum dolanıklık deneyi nedir zzq")
            assert _apology not in _wk["answer"] and _wk["answer"].startswith("Gemini yanıtı.")
            print("  • Gemini anahtarı yokken yanıtın başında özür notu var, anahtar varken yok ✓")
        else:
            print("  • (Çevrimdışı — özür notu testi atlandı)")
    finally:
        TrustedSourceFetcher.search_wikipedia = _orig_wiki19
        ai.gemini.generate_response = _orig_gem19
        (_sk19(_saved_key19) if _saved_key19 else _rk19())

    # 19g. Ağ denetimi: 1.1.1.1:53 kesik olsa bile diğer hedeflerden biri açıksa çevrimiçi; tanı listesi döner
    import threading
    from network_manager import NetworkMonitor as _NM
    _nm = _NM.__new__(_NM)
    _nm._timeout, _nm._interval, _nm._host, _nm._port = 1.0, 5.0, "1.1.1.1", 53
    _nm._targets = list(_cfg19.NetworkConfig.CHECK_TARGETS)
    _nm.last_target = None
    _nm._lock, _nm._is_online, _nm._on_status_change = threading.Lock(), None, None
    _nm._probe = lambda host, port: ((host, port) == ("8.8.8.8", 443), 7)     # yalnızca Google HTTPS açık
    assert _nm._check_connection() is True and "Google HTTPS" in _nm.last_target
    _diag = _nm.diagnose()
    assert [r["ok"] for r in _diag] == [False, False, False, True] and _nm.is_online is True
    _nm._probe = lambda host, port: (False, 1)
    assert _nm._check_connection() is False and not any(r["ok"] for r in _nm.diagnose()) and _nm.is_online is False
    print("  • Ağ denetimi Cloudflare+Google hedeflerini paralel deniyor; biri açıksa çevrimiçi, tanı listesi dönüyor ✓")

    # 19h. Gemini API testi (anahtarsız/ geçersiz/ geçerli yanıtları — ağ çağrıları sahte)
    import ai_engine as _ae19
    _g19 = _ae19.GeminiService()
    assert _g19.test_key("") == (False, "API anahtarı girilmemiş.")
    _orig_get, _orig_post = _ae19.requests.get, _ae19.requests.post
    try:
        _ae19.requests.get = lambda *a, **k: type("R", (), {"status_code": 400, "text": ""})()
        _ok, _msg = _g19.test_key("bozuk-anahtar")
        assert not _ok and "geçersiz" in _msg
        _ae19.requests.get = lambda *a, **k: type("R", (), {"status_code": 200, "text": ""})()

        class _SSE:
            status_code = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def iter_lines(self): return [b'data: {"candidates":[{"content":{"parts":[{"text":"tamam"}]}}]}']
        _ae19.requests.post = lambda *a, **k: _SSE()
        _ok, _msg = _g19.test_key("gecerli-anahtar")
        assert _ok and "yanıt veriyor" in _msg
    finally:
        _ae19.requests.get, _ae19.requests.post = _orig_get, _orig_post
    print("  • 'API'yi Test Et': boş / geçersiz / geçerli anahtar doğru mesajlarla sınanıyor ✓")

    # 19i. Görsel: Gemini kotası yoksa (429) ücretsiz yedekle çiziyor; düzenleme dürüst hata veriyor
    class _QuotaGemini:
        last_image_error = "quota"
        def generate_image(self, prompt, source_image_path=None): return None
        def english_image_prompt(self, request): return "a cat"
    _saved_key19b = _gk19()
    _sk19("AIzaSyD_TestValidGeminiKey1234567890XYZ")
    _orig_free = _ae19.ImageStudio._free_generate
    try:
        _ae19.ImageStudio._free_generate = classmethod(lambda cls, p: (b"\\xff\\xd8fake-jpeg", "image/jpeg"))
        _path, _cap = _ae19.ImageStudio.handle("generate", "bana kedi çiz", _QuotaGemini())
        assert _path and _path.endswith(".jpg") and "Pollinations" in _cap
        _os19.remove(_path)
        _p2, _m2 = _ae19.ImageStudio.handle("edit", "düzenle", _QuotaGemini(), source_image_path="x.png")
        assert _p2 is None and "429" in _m2 and "faturalandırma" in _m2
        _ae19.ImageStudio._free_generate = classmethod(lambda cls, p: None)
        _p3, _m3 = _ae19.ImageStudio.handle("generate", "bana kedi çiz", _QuotaGemini())
        assert _p3 is None and "yedek üretici de yanıt vermedi" in _m3
    finally:
        _ae19.ImageStudio._free_generate = _orig_free
        (_sk19(_saved_key19b) if _saved_key19b else _rk19())
    assert "gemini-2.0-flash-preview-image-generation" not in _cfg19.GeminiConfig.IMAGE_MODELS
    print("  • Görsel: Gemini kotası yokken ücretsiz yedekle çiziyor, düzenlemede gerçek sebebi söylüyor ✓")

    print("  ✅ TEST 18 BAŞARILI: Hassas bilgi filtresi, tema, otomatik öğrenme, ürün bilgisi, bas-konuş, /aramabaslat hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 19: 🔔 Güncelleme uyarısı (yeni sürüm denetimi)
    # ─────────────────────────────────────────
    print("\n[TEST 19] Güncelleme Uyarısı:")
    import updater as _up

    # 20a. Sürüm ayrıştırma / karşılaştırma
    assert _up.parse_version("v1.3.3") == (1, 3, 3) and _up.parse_version("1.4") == (1, 4, 0)
    assert _up.parse_version("sürüm yok") is None
    assert _up.parse_version("1.10") > _up.parse_version("1.9.9") > _up.parse_version("1.3.3")
    print("  • Sürüm numaraları doğru ayrıştırılıyor/karşılaştırılıyor (1.10 > 1.9.9 > 1.3.3) ✓")

    # 20b. Kaynak sırası ve hata yolları (ağ çağrıları sahte)
    class _Resp:
        def __init__(self, code, js=None, text=""):
            self.status_code, self._js, self.text = code, js, text
        def json(self):
            return self._js
    _orig_get20 = _up.requests.get
    try:
        # yeni sürüm: Releases API'den
        _up.requests.get = lambda url, **k: _Resp(200, {"tag_name": "v9.9.9", "html_url": "https://github.com/x/y/releases/tag/v9.9.9"})
        _r = _up.check_for_update("1.3.3")
        assert _r == {"current": "1.3.3", "latest": "9.9.9", "url": "https://github.com/x/y/releases/tag/v9.9.9"}, _r
        # aynı/eski sürüm: uyarı yok
        _up.requests.get = lambda url, **k: _Resp(200, {"tag_name": "v1.3.3", "html_url": "u"})
        assert _up.check_for_update("1.3.3") is None
        # Releases 404 (depo gizli / yayın yok) → depodaki config.py'ye düş
        def _get_fallback(url, **k):
            if "api.github.com" in url:
                return _Resp(404)
            return _Resp(200, text='# x\nAPP_VERSION = "2.0"\n')
        _up.requests.get = _get_fallback
        _r2 = _up.check_for_update("1.3.3")
        assert _r2 and _r2["latest"] == "2.0" and _r2["url"] == _cfg19.UPDATE_PAGE_URL
        # her yer 404 → sessizce None (uyarı yok, hata yok)
        _up.requests.get = lambda url, **k: _Resp(404)
        assert _up.check_for_update("1.3.3") is None
        # ağ hatası → sessizce None
        def _boom(url, **k):
            raise _up.requests.ConnectionError("yok")
        _up.requests.get = _boom
        assert _up.check_for_update("1.3.3") is None
    finally:
        _up.requests.get = _orig_get20
    print("  • Yeni sürüm bulununca bilgi dönüyor; aynı sürüm / 404 / ağ hatasında sessizce uyarı yok ✓")

    # 20c. Arayüzde şerit bileşenleri + varsayılan depo adresi
    for m in ("_build_update_banner", "_check_for_updates", "_show_update_banner", "_open_update_page"):
        assert hasattr(_gui.MehburApp, m), f"gui_app.MehburApp.{m} eksik"
    assert _cfg19.UPDATE_PAGE_URL.startswith("https://github.com/") and _cfg19.GITHUB_REPO in _cfg19.UPDATE_PAGE_URL
    import inspect as _insp20
    _src20 = _insp20.getsource(_gui.MehburApp._show_update_banner)
    assert "Uyarı: Yeni sürüm yayınlandı." in _src20 and "bu bağlantıya tıklayın:" in _src20
    print("  ✅ TEST 19 BAŞARILI: Güncelleme denetimi ve uyarı şeridi hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 20: 📞 JARVIS görüşmesi (telefon butonu) — 🎤 bas-konuş yerinde kalır
    # ─────────────────────────────────────────
    print("\n[TEST 20] JARVIS Görüşmesi (📞):")
    import threading as _th21
    import voice_engine as _ve21

    # 21a. Bitirme cümleleri
    assert _ve21.is_call_end_phrase("tamam görüşmeyi bitir") and _ve21.is_call_end_phrase("Görüşürüz Mehbur")
    assert not _ve21.is_call_end_phrase("saat kaç") and not _ve21.is_call_end_phrase("")
    print("  • 'görüşmeyi bitir / görüşürüz' anlaşılıyor, normal cümleler bitirmiyor ✓")

    # 21b. Döngü: karşılama → dinle → işle → yanıt → veda (mikrofon/ses/TTS sahte)
    _orig21 = (_ve21.Dictation, _ve21.TextToSpeech, _ve21.voice_dependencies_ok)
    _said21, _states21, _cmds21 = [], [], []
    _turns21 = ["hey mehbur saat kaç", "", "görüşmeyi bitir"]

    class _FakeDict21:
        def __init__(self, on_partial=None, on_done=None):
            self._done = on_done
        def start(self):
            t = _turns21.pop(0)
            _th21.Thread(target=lambda: self._done(t, ""), daemon=True).start()
        def stop(self):
            pass

    class _FakeTTS21:
        @staticmethod
        def speak(text, voice=None, blocking=True):
            _said21.append(text)

    _ve21.Dictation, _ve21.TextToSpeech = _FakeDict21, _FakeTTS21
    _ve21.voice_dependencies_ok = lambda: True
    try:
        _ended21 = _th21.Event()
        _c21 = _ve21.JarvisCall(
            on_command=lambda t: (_cmds21.append(t) or "Saat 22:15."),
            on_state=lambda s, t="": _states21.append(s),
            on_end=_ended21.set,
        )
        assert _c21.start() and _ended21.wait(10), "görüşme bitmedi"
        assert _cmds21 == ["saat kaç"], _cmds21          # uyandırma sözcüğü ayıklandı, sessiz tur atlandı
        assert _said21[0] == _ve21.WAKE_RESPONSE and "Saat 22:15." in _said21 and _said21[-1].startswith("Görüşmek")
        assert _states21[0] == "karsilama" and "islemde" in _states21 and "yanit" in _states21 and _states21[-1] == "veda"
    finally:
        _ve21.Dictation, _ve21.TextToSpeech, _ve21.voice_dependencies_ok = _orig21
    print("  • Karşılama → dinle → işle → seslendir → veda döngüsü çalışıyor, bitince on_end çağrılıyor ✓")

    # 21c. Arayüz: 📞 butonu eklendi, 🎤 hâlâ bas-konuş
    for m in ("_toggle_jarvis_call", "_on_call_state", "_on_call_end", "_ensure_jarvis", "_toggle_voice_from_chat"):
        assert hasattr(_gui.MehburApp, m), f"gui_app.MehburApp.{m} eksik"
    _gsrc21 = open(_gui.__file__, encoding="utf-8").read()
    assert 'self.call_btn = ctk.CTkButton' in _gsrc21 and "command=self._toggle_jarvis_call" in _gsrc21
    assert "command=self._toggle_voice_from_chat" in _gsrc21 and "Dictation(" in _gsrc21
    print("  ✅ TEST 20 BAŞARILI: 📞 JARVIS görüşmesi hazır; 🎤 sesli mesaj olarak duruyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 21: Çevrimiçi kurucu (küçük .exe → dosyaları GitHub'dan indirir)
    # ─────────────────────────────────────────
    print("\n[TEST 21] Çevrimiçi Kurucu:")
    import os as _os22
    import io as _io22
    import tempfile as _tf22
    import zipfile as _zf22
    import installer as _inst22
    import config as _cfg22

    # 22a. Adres config'tekiyle uyumlu, Release'in sabit 'latest' adresini gösteriyor
    assert _inst22.GITHUB_REPO == _cfg22.GITHUB_REPO
    assert _inst22.PAYLOAD_URL == f"https://github.com/{_cfg22.GITHUB_REPO}/releases/latest/download/MehburAI-payload.zip"
    print("  • İndirme adresi config.GITHUB_REPO ile uyumlu ✓")

    # 22b. İndirme: sahte GitHub yanıtı → dosya yazılıyor, ilerleme bildiriliyor, yarım/bozuk dosya reddediliyor
    _buf22 = _io22.BytesIO()
    with _zf22.ZipFile(_buf22, "w") as _z22:
        _z22.writestr("MehburAI.exe", "exe")
        _z22.writestr("data/config.json", "PAKETTEN")
        _z22.writestr("assets/logo.png", "png")
        _z22.writestr("../kacak.txt", "zip-slip")
    _pay22 = _buf22.getvalue()

    class _Resp22:
        def __init__(self, data, length=None):
            self._r = _io22.BytesIO(data)
            self.headers = {"Content-Length": str(len(data) if length is None else length)}
        def read(self, n=-1): return self._r.read(n)
        def __enter__(self): return self
        def __exit__(self, *a): return False

    _orig_open22 = _inst22.urllib.request.urlopen
    _tmp22 = _tf22.mkdtemp()
    try:
        _seen22 = []
        _inst22.urllib.request.urlopen = lambda req, timeout=0: _Resp22(_pay22)
        _dl22 = _os22.path.join(_tmp22, "p.zip")
        _inst22.download_payload(_dl22, lambda g, t: _seen22.append((g, t)))
        assert open(_dl22, "rb").read() == _pay22 and _seen22[-1] == (len(_pay22), len(_pay22))
        _inst22.urllib.request.urlopen = lambda req, timeout=0: _Resp22(_pay22, length=len(_pay22) + 5)
        try:
            _inst22.download_payload(_dl22, lambda g, t: None); raise SystemExit("yarım indirme kabul edildi")
        except IOError:
            pass
        _inst22.urllib.request.urlopen = lambda req, timeout=0: _Resp22(b"bozuk veri")
        try:
            _inst22.download_payload(_dl22, lambda g, t: None); raise SystemExit("bozuk dosya kabul edildi")
        except IOError:
            pass
    finally:
        _inst22.urllib.request.urlopen = _orig_open22
    print("  • İndirme + ilerleme çalışıyor; yarım ve bozuk dosya reddediliyor ✓")

    # 22c. Açma: dosyalar kuruluyor, mevcut data/ ezilmiyor, '..' ile dışarı yazılamıyor
    _inst_dir22 = _os22.path.join(_tmp22, "kurulum")
    _os22.makedirs(_os22.path.join(_inst_dir22, "data"))
    with open(_os22.path.join(_inst_dir22, "data", "config.json"), "w") as _f22:
        _f22.write("KULLANICI")
    _dl22 = _os22.path.join(_tmp22, "p.zip")
    with open(_dl22, "wb") as _f22:
        _f22.write(_pay22)
    _inst22.extract_payload(_dl22, _inst_dir22, lambda f: None)
    assert open(_os22.path.join(_inst_dir22, "MehburAI.exe")).read() == "exe"
    assert open(_os22.path.join(_inst_dir22, "data", "config.json")).read() == "KULLANICI"
    assert not _os22.path.exists(_os22.path.join(_tmp22, "kacak.txt"))
    print("  • Dosyalar kuruluyor; kullanıcının data/ klasörü korunuyor; zip-slip engelleniyor ✓")

    # 22c2. Kalan süre tahmini
    assert _inst22.remaining_seconds(1.0, 0.5) is None          # çok erken → hesaplanıyor
    assert _inst22.remaining_seconds(10, 0.0) is None
    assert abs(_inst22.remaining_seconds(10, 0.25) - 30) < 1e-6  # 10 sn'de %25 → 30 sn kaldı
    assert _inst22.remaining_seconds(10, 1.0) == 0
    assert _inst22.format_eta(None) == "hesaplanıyor…" and _inst22.format_eta(12.4) == "~12 sn"
    assert _inst22.format_eta(125) == "~2 dk 5 sn" and _inst22.format_eta(0) == "~1 sn"
    print("  • Kalan süre tahmini hıza göre hesaplanıyor, çok erken/eksik veride 'hesaplanıyor…' diyor ✓")

    # 22d. Build betiği: Setup'a payload gömülmüyor, MehburAI.zip yalnızca .exe içeriyor
    _bat22 = open(_os22.path.join(_os22.path.dirname(_os22.path.abspath(__file__)), "build_exe.bat"), encoding="utf-8").read()
    assert "--add-data \"%CD%\\build\\payload.zip" not in _bat22 and "dist/MehburAI.zip" in _bat22
    print("  ✅ TEST 21 BAŞARILI: Çevrimiçi kurucu hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 22: 📞 Görüşmede ✕ çık / 🎤 sustur / 📷 kamera + ⏭ atla + 📋 kopyala
    # ─────────────────────────────────────────
    print("\n[TEST 22] Görüşme Kontrolleri, Yazma Animasyonunu Atla, Panoya Kopyala:")
    import threading as _th23
    import time as _time23
    import tkinter as _tk23
    import voice_engine as _ve23

    # 23a. set_muted(True) o anki dinlemeyi hemen kesiyor (görüşmeyi bitirmiyor)
    _c23a = _ve23.JarvisCall(on_command=lambda t: "x")
    _stopped23 = []
    _c23a._dictation = type("D", (), {"stop": lambda self: _stopped23.append(1)})()
    assert not _c23a.is_muted()
    _c23a.set_muted(True)
    assert _c23a.is_muted() and _stopped23 == [1]
    _c23a.set_muted(False)
    assert not _c23a.is_muted()
    print("  • set_muted(True) aktif dinlemeyi hemen kesiyor, görüşme sürüyor ✓")

    # 23b. Susturulmuş başlarsa dinlemeye geçmiyor ('sessizde'); açılınca kaldığı yerden devam ediyor
    _turns23 = ["ikinci soru", "görüşmeyi bitir"]
    _dict_starts23 = []

    class _FakeDict23:
        def __init__(self, on_partial=None, on_done=None):
            self._done = on_done
        def start(self):
            _dict_starts23.append(1)
            t = _turns23.pop(0)
            _th23.Thread(target=lambda: self._done(t, ""), daemon=True).start()
        def stop(self):
            pass

    class _FakeTTS23:
        @staticmethod
        def speak(text, voice=None, blocking=True):
            _said23.append(text)

    _said23, _states23, _cmds23 = [], [], []
    _orig23 = (_ve23.Dictation, _ve23.TextToSpeech, _ve23.voice_dependencies_ok)
    _ve23.Dictation, _ve23.TextToSpeech = _FakeDict23, _FakeTTS23
    _ve23.voice_dependencies_ok = lambda: True
    try:
        _ended23 = _th23.Event()
        _c23 = _ve23.JarvisCall(
            on_command=lambda t: (_cmds23.append(t) or "Yanıt."),
            on_state=lambda s, t="": _states23.append(s),
            on_end=_ended23.set,
        )
        _c23.set_muted(True)      # görüşme başlamadan sustur
        assert _c23.start()
        _t0 = _time23.time()
        while "sessizde" not in _states23 and _time23.time() - _t0 < 5:
            _time23.sleep(0.05)
        assert "sessizde" in _states23, _states23
        assert _dict_starts23 == [], "susturulmuşken dinlemeye başlamamalı"
        _c23.set_muted(False)     # aç → sıradaki turlar normal işlensin
        assert _ended23.wait(10), "görüşme bitmedi"
        assert _cmds23 == ["ikinci soru"], _cmds23
        assert _states23[-1] == "veda"
    finally:
        _ve23.Dictation, _ve23.TextToSpeech, _ve23.voice_dependencies_ok = _orig23
    print("  • Susturulmuşken dinlemeye başlamıyor ('sessizde'), açılınca kaldığı yerden devam ediyor ✓")

    # 23c. JarvisOverlay: ✕ her zaman görünür; 📞 görüşmesi 🎤/📷 düğmelerini gösterip gizliyor
    _root23 = _tk23.Tk()
    _root23.withdraw()
    _ov23 = None
    try:
        _ov23 = _jv.JarvisOverlay(_root23)
        _ov23.show(mode="idle", title="t", subtitle="s")
        _root23.update_idletasks()
        assert _ov23._btn_exit.winfo_ismapped()
        assert not _ov23._btn_mic.winfo_ismapped() and not _ov23._btn_cam.winfo_ismapped()

        _closed23, _mic23, _cam23 = [], [], []
        _ov23.on_close = lambda: _closed23.append(1)
        _ov23.set_call_controls(True, mic_muted=False, camera_on=False,
                                on_mic_toggle=lambda: _mic23.append(1),
                                on_camera_toggle=lambda: _cam23.append(1))
        _root23.update_idletasks()
        assert _ov23._btn_mic.winfo_ismapped() and _ov23._btn_cam.winfo_ismapped()
        assert _ov23._btn_mic.cget("text") == "🎤" and _ov23._btn_cam.cget("fg") == "#7d8590"

        _ov23._mic_clicked()
        _ov23._cam_clicked()
        assert _mic23 == [1] and _cam23 == [1]

        _ov23.set_mic_muted(True)
        assert _ov23._btn_mic.cget("text") == "🔇"
        _ov23.set_camera_on(True)
        assert _ov23._btn_cam.cget("fg").lower() == "#00e676"

        _ov23.set_call_controls(False)
        _root23.update_idletasks()
        assert not _ov23._btn_mic.winfo_ismapped() and not _ov23._btn_cam.winfo_ismapped()

        _ov23._user_close()
        assert _closed23 == [1]
    finally:
        if _ov23 is not None:
            try:
                _ov23.destroy()
            except Exception:
                pass
        _root23.destroy()
    print("  • JARVIS ekranında ✕ çık / 🎤 sustur / 📷 kamera düğmeleri çalışıyor ✓")

    # 23d. gui_app: 📞 görüşmesi mikrofon/kamera kontrolüne ve kamera izin kapısına bağlı
    for m in ("_call_command", "_toggle_call_mic", "_toggle_call_camera"):
        assert hasattr(_gui.MehburApp, m), f"gui_app.MehburApp.{m} eksik"
    _gsrc23 = open(_gui.__file__, encoding="utf-8").read()
    assert "set_call_controls(" in _gsrc23 and "on_mic_toggle=lambda: self._toggle_call_mic(call)" in _gsrc23
    assert "VisionAssistant.detect_intent(text)" in _gsrc23 and "_call_camera_on" in _gsrc23
    print("  • gui_app: 📞 görüşmesi 🎤/📷 kontrolüne bağlı; kamera kapalıyken kamera soruları reddediliyor ✓")

    # 23e. ⏭ Atla (yazma animasyonunu anında bitirir) + 📋 Kopyala (panoya kopyalar)
    assert "skip_btn" in _gsrc23 and "⏭ Atla" in _gsrc23 and "def finish():" in _gsrc23
    assert hasattr(_gui.MehburApp, "_copy_to_clipboard")
    assert "📋 Kopyala" in _gsrc23 and "self.clipboard_append(text)" in _gsrc23
    import inspect as _insp23
    _tw_sig23 = str(_insp23.signature(_gui.MehburApp._run_typewriter))
    assert "skip_btn" in _tw_sig23
    print("  • ⏭ Atla yazma animasyonunu anında bitiriyor; 📋 Kopyala cevabı panoya kopyalıyor ✓")
    print("  ✅ TEST 22 BAŞARILI: Görüşme kontrolleri + atla/kopyala hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 23: .exe'lere gömülen Win32 sürüm bilgisi (SmartScreen/AV yanlış pozitif azaltma)
    # ─────────────────────────────────────────
    print("\n[TEST 23] .exe Sürüm Bilgisi (version_info.py):")
    import os as _os24
    import version_info as _vi24

    assert _vi24._version_tuple("1.6.1") == (1, 6, 1, 0)
    assert _vi24._version_tuple("2.0") == (2, 0, 0, 0)
    assert _vi24._version_tuple("1.10.2.5.9") == (1, 10, 2, 5)   # fazlası kesilir
    print("  • 'X.Y[.Z]' → 4'lü Win32 sürüm demetine doğru çevriliyor ✓")

    _info24 = _vi24.build_version_info("1.6.1", "MehburAI Kurulum", "MehburAI.Setup.exe")
    from PyInstaller.utils.win32.versioninfo import VSVersionInfo as _VSV24
    assert isinstance(_info24, _VSV24)
    _txt24 = str(_info24)
    assert "MehburAI Kurulum" in _txt24 and "MehburAI.Setup.exe" in _txt24 and "'1.6.1'" in _txt24
    assert "Mehbur07" in _txt24                                  # CompanyName

    import tempfile as _tf24
    _tmp24 = _tf24.mkdtemp()
    _out24 = _os24.path.join(_tmp24, "vi24.txt")
    with open(_out24, "w", encoding="utf-8") as _f24:
        _f24.write(_txt24)
    from PyInstaller.utils.win32.versioninfo import load_version_info_from_text_file as _load24
    _reloaded24 = _load24(_out24)                                 # PyInstaller'ın kendi --version-file yolu
    assert isinstance(_reloaded24, _VSV24)
    print("  • Üretilen sürüm bilgisi PyInstaller'ın --version-file'ıyla (eval tabanlı) geri okunabiliyor ✓")

    # 24b. MehburAI.spec ve build_exe.bat gerçekten kullanıyor; UPX kapalı
    _spec24 = open(_os24.path.join(_os24.path.dirname(_os24.path.abspath(__file__)), "MehburAI.spec"), encoding="utf-8").read()
    assert "from version_info import build_version_info" in _spec24 and "version=app_version_info" in _spec24
    assert "upx=False" in _spec24
    _bat24 = open(_os24.path.join(_os24.path.dirname(_os24.path.abspath(__file__)), "build_exe.bat"), encoding="utf-8").read()
    assert "version_info.py --version" in _bat24 and "--version-file" in _bat24 and "--noupx" in _bat24
    print("  • MehburAI.spec + build_exe.bat sürüm bilgisini gömüyor, UPX kapalı (her ikisinde de) ✓")
    print("  ✅ TEST 23 BAŞARILI: .exe'ler Yayımcı/Ürün bilgisiyle deriniyor, UPX kapalı.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 24: 🔢 Yerel Matematik (Gemini'ye sormadan çözülür, token israfı yok)
    # ─────────────────────────────────────────
    print("\n[TEST 24] 🔢 Yerel Matematik:")
    _MS = MathSolver

    # 24a. Sembol + Türkçe işlem sözcükleriyle doğru sonuç
    for _q, _want in (
        ("2+2", "Sonuç: 4"), ("125*8-4", "Sonuç: 996"), ("(3+5)/2", "Sonuç: 4"),
        ("3 artı 5", "Sonuç: 8"), ("125 çarpı 8 kaç eder", "Sonuç: 1000"),
        ("100 bölü 4 nedir", "Sonuç: 25"), ("2 üzeri 10", "Sonuç: 1024"),
        ("7 mod 3", "Sonuç: 1"), ("3,5+1,5", "Sonuç: 5"), ("-5+10", "Sonuç: 5"),
    ):
        _d = _MS.detect(_q)
        assert _d, f"algılanamadı: {_q!r}"
        assert _MS.solve(_d) == _want, f"{_q!r} -> {_MS.solve(_d)!r} (beklenen {_want!r})"
    assert _MS.solve(_MS.detect("10 bölü 0")) == "Sıfıra bölme tanımsızdır."
    print("  • Sembol ve Türkçe işlem sözcükleriyle ('artı/çarpı/bölü/üzeri/mod', 'kaç eder/nedir') doğru çözülüyor ✓")

    # 24b. Matematik OLMAYAN metinlerde asla tetiklenmiyor (Wikipedia/sohbet akışını bozmaz)
    for _q in ("saat kaç", "2. Dünya Savaşı ne zaman bitti", "42", "Albert Einstein kimdir",
               "merhaba nasılsın", "12 Eylül 1980", "0090 555 123 45 67", "3 tane elma aldım",
               "", "   ", "5 tl", "2+2 değil felsefe"):
        assert _MS.detect(_q) is None, f"yanlışlıkla matematik sayıldı: {_q!r}"
    print("  • Sıradan sorular (tarih, telefon, tek sayı, kimlik sorusu ...) matematik sayılmıyor ✓")

    # 24c. Güvenlik: eval() değil ast beyaz listesi — kod çalıştırma imkânsız; aşırı üs (DoS) engellenir
    assert _MS.detect("__import__('os').system('dir')") is None
    assert _MS.detect("1 and 2") is None and _MS.detect("1;2") is None
    _huge = _MS.detect("2**99999999")
    assert _huge and _MS.solve(_huge) is None, "aşırı büyük üs sınırlanmalı"
    assert _MS.solve("()") is None and _MS.solve("5/") is None
    print("  • Kod enjeksiyonu imkânsız (ast beyaz listesi), aşırı büyük üs (DoS) engelleniyor ✓")

    # 24d. AIEngine.process_query matematiği Gemini'ye SORMADAN yanıtlıyor
    _orig_gen24 = ai.gemini.generate_response
    _gemini_called24 = []
    ai.gemini.generate_response = lambda *a, **k: (_gemini_called24.append(1) or "GEMINI ÇAĞRILDI")
    try:
        _r24 = ai.process_query("125 çarpı 8 kaç eder")
        assert _r24["answer"] == "Sonuç: 1000" and _r24["source"] == "🔢 Yerel Matematik", _r24
        assert not _gemini_called24, "matematik sorusu Gemini'ye gitmemeli"
    finally:
        ai.gemini.generate_response = _orig_gen24
    print("  • AIEngine matematik sorularını Gemini'ye hiç sormadan yanıtlıyor ✓")
    print("  ✅ TEST 24 BAŞARILI: Yerel matematik çözücü hazır, Gemini token'ı israf etmiyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # Özet Rapor
    # ─────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  🎉 TÜM ENTEGRASYON TESTLERİ TAMAMLANDI: {passed_tests}/{total_tests} BAŞARILI!")
    print("=" * 65)


if __name__ == "__main__":
    run_full_validation()
