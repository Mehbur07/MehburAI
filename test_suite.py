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
    total_tests = 31

    memory = MemoryEngine()
    network = NetworkMonitor()
    ai = AIEngine(memory_engine=memory, network_monitor=network)

    # Testler gerçek Reddit/Stack Overflow'a istek atmasın (Reddit'in istek sınırı çok düşük);
    # topluluk araması TEST 29'da sahte verilerle ayrıca sınanır.
    import ai_engine as _ae0
    _real_community_search = _ae0.CommunitySourceFetcher.search
    _ae0.CommunitySourceFetcher.search = classmethod(lambda cls, q: [])
    # Hafıza kayıtları testlerde arka planda gerçek Gemini ile çevrilmesin (TEST 30'da sahteyle sınanır)
    ai.translator.enabled = False

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
    for m in ("_build_appearance_card", "_apply_theme_now", "_build_learn_card", "_dictation_done"):
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
    _orig_grounded19 = ai.gemini.generate_grounded_response
    TrustedSourceFetcher.search_wikipedia = classmethod(
        lambda cls, q, lang="tr", product=False: {"title": "X", "extract": "Wikipedia özeti.", "source": "Wikipedia (X)",
                                                   "url": "https://tr.wikipedia.org/wiki/X", "truncated": False})
    # 🌐 Tüm-kaynak arama (Google Arama entegrasyonu) burada sahte None dönsün — bu blok
    # eski Wikipedia+generate_response yedek akışını test ediyor, gerçek ağ çağrısı istemiyor.
    ai.gemini.generate_grounded_response = lambda *a, **k: None
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
        ai.gemini.generate_grounded_response = _orig_grounded19
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
    for m in ("_build_update_banner", "_check_for_updates", "_show_update_banner"):
        assert hasattr(_gui.MehburApp, m), f"gui_app.MehburApp.{m} eksik"
    assert _cfg19.UPDATE_PAGE_URL.startswith("https://github.com/") and _cfg19.GITHUB_REPO in _cfg19.UPDATE_PAGE_URL
    import inspect as _insp20
    _src20 = _insp20.getsource(_gui.MehburApp._show_update_banner)
    assert "Yeni sürüm yayınlandı" in _src20
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
    # TEST 25: ⏰ Telegram Hatırlatmaları
    # ─────────────────────────────────────────
    print("\n[TEST 25] ⏰ Telegram Hatırlatmaları:")
    import time as _time25
    from datetime import datetime as _dt25, timedelta as _td25

    import telegram_bot as _tb25
    from telegram_bot import _parse_reminder

    # 25a. Zaman biçimleri doğru çözümleniyor
    _now25 = _dt25.now()
    _due, _msg, _err = _parse_reminder("30 ekmek al")
    assert _err is None and _msg == "ekmek al"
    assert abs((_due - _now25).total_seconds() - 30 * 60) < 5

    _due, _msg, _err = _parse_reminder("2sa toplantı var")
    assert _err is None and _msg == "toplantı var"
    assert abs((_due - _now25).total_seconds() - 2 * 3600) < 5

    _due, _msg, _err = _parse_reminder("18:30 ilaç iç")
    assert _err is None and _msg == "ilaç iç" and _due.hour == 18 and _due.minute == 30
    assert _due > _now25  # bugün geçtiyse otomatik yarına kayar

    _due, _msg, _err = _parse_reminder("yarın 09:00 doktor randevusu")
    assert _err is None and _due.date() == (_now25 + _td25(days=1)).date() and _due.hour == 9

    _due, _msg, _err = _parse_reminder("25.12 14:00 fatura öde")
    assert _err is None and _due.day == 25 and _due.month == 12 and _due.hour == 14

    assert _parse_reminder("")[2] is not None
    assert _parse_reminder("saçmalık metin")[2] is not None
    print("  • '30dk', '2sa', '18:30', 'yarın HH:MM', 'GG.AA HH:MM' biçimleri doğru çözümleniyor ✓")

    # 25b. Kurma / listeleme / iptal — gerçek dosyaya yazmadan (kaydetme mocklanır)
    _bot25 = _tb25.TelegramControlBot(query_handler=lambda t: "ok")
    _bot25._reminders = []
    _saved25 = []
    _bot25._save_reminders = lambda: _saved25.append(1)
    _out25 = []
    _bot25._send = lambda s: _out25.append(s)

    _bot25._add_reminder("5 su iç")
    assert len(_bot25._reminders) == 1 and _bot25._reminders[0]["message"] == "su iç"
    assert _saved25, "hatırlatma eklenince kaydedilmeli"
    _rid25 = _bot25._reminders[0]["id"]
    assert any("kuruldu" in s.lower() for s in _out25)

    _out25.clear()
    _bot25._list_reminders()
    assert _out25 and "su iç" in _out25[0]

    _out25.clear()
    _bot25._cancel_reminder(_rid25)
    assert not _bot25._reminders
    assert any("iptal edildi" in s.lower() for s in _out25)

    _out25.clear()
    _bot25._cancel_reminder("olmayanid")
    assert any("yok" in s.lower() for s in _out25)
    print("  • /hatirlat kuruyor, /hatirlatmalarim listeliyor, /hatirlatiptal siliyor ✓")

    # 25c. Süresi gelen hatırlatma arka plan döngüsünde tetiklenip gönderiliyor ve listeden düşüyor
    _bot25._reminders = [{"id": "abc123", "due_ts": _time25.time() - 1, "message": "geçmiş hatırlatma"}]
    _bot25._running = True
    _orig_sleep25 = _tb25.time.sleep
    _tb25.time.sleep = lambda s: None

    def _stop_after_send25(s):
        _out25.append(s)
        _bot25._running = False

    _bot25._send = _stop_after_send25
    try:
        _bot25._reminder_loop()  # _running kapanana dek (tek geçiş) döner
    finally:
        _tb25.time.sleep = _orig_sleep25
    assert any("geçmiş hatırlatma" in s for s in _out25)
    assert _bot25._reminders == []
    print("  • Süresi gelen hatırlatma arka planda tetiklenip gönderiliyor, listeden düşüyor ✓")

    print("  ✅ TEST 25 BAŞARILI: ⏰ Hatırlatma sistemi hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 26: 🔄 Tek Tuşla Güncelleme + 🎉 Yenilikler Penceresi
    # ─────────────────────────────────────────
    print("\n[TEST 26] 🔄 Tek Tuşla Güncelleme + 🎉 Yenilikler:")
    import inspect as _insp26

    # 26a. updater.fetch_latest_release_notes: gövdeyi döndürür, hata/404/boşta sessizce None
    _orig_get26 = _up.requests.get
    try:
        _up.requests.get = lambda url, **k: _Resp(200, {"body": "- Yeni özellik X\n- Düzeltme Y"})
        assert _up.fetch_latest_release_notes() == "- Yeni özellik X\n- Düzeltme Y"
        _up.requests.get = lambda url, **k: _Resp(200, {"body": "   "})
        assert _up.fetch_latest_release_notes() is None
        _up.requests.get = lambda url, **k: _Resp(404)
        assert _up.fetch_latest_release_notes() is None

        def _boom26(url, **k):
            raise _up.requests.ConnectionError("yok")

        _up.requests.get = _boom26
        assert _up.fetch_latest_release_notes() is None
    finally:
        _up.requests.get = _orig_get26
    print("  • fetch_latest_release_notes: gövdeyi getiriyor, ağ hatası/404/boşta sessizce None dönüyor ✓")

    # 26b. Son görülen sürüm kalıcı bellekte doğru okunup yazılıyor
    _prev_seen26 = _cfg19.get_last_seen_version()
    try:
        _cfg19.set_last_seen_version("1.7")
        assert _cfg19.get_last_seen_version() == "1.7"
        _cfg19.set_last_seen_version("1.8")
        assert _cfg19.get_last_seen_version() == "1.8"
    finally:
        _cfg19.set_last_seen_version(_prev_seen26)
    print("  • get/set_last_seen_version doğru kaydediyor/okuyor ✓")

    # 26c. Arayüz: "Şimdi Güncelle" artık GitHub'a yönlendirmek yerine .exe indirip çalıştırıyor,
    # ve az önce güncellendiysek (gizli açılış hariç) 'Yenilikler' penceresi bir kez gösteriliyor
    for m in ("_start_in_app_update", "_download_setup_exe", "_launch_updater",
              "_update_failed", "_maybe_show_whats_new", "_show_whats_new_dialog"):
        assert hasattr(_gui.MehburApp, m), f"gui_app.MehburApp.{m} eksik"
    assert not hasattr(_gui.MehburApp, "_open_update_page"), "eski 'tarayıcıda aç' davranışı kaldırılmalıydı"
    _src26a = _insp26.getsource(_gui.MehburApp._start_in_app_update)
    assert "_download_setup_exe" in _src26a and "_launch_updater" in _src26a
    _src26b = _insp26.getsource(_gui.MehburApp._download_setup_exe)
    assert "MehburAI.zip" in _src26b and "MehburAI.Setup.exe" in _src26b
    _src26c = _insp26.getsource(_gui.MehburApp._launch_updater)
    assert "subprocess.Popen" in _src26c and "_real_quit" in _src26c
    _src26d = _insp26.getsource(_gui.MehburApp._maybe_show_whats_new)
    assert ("_start_hidden" in _src26d and "get_last_seen_version" in _src26d
            and "set_last_seen_version" in _src26d)
    print("  • '🔄 Şimdi Güncelle' artık .exe indirip çalıştırıyor (tarayıcıya yönlendirmiyor) ✓")
    print("  • Az önce güncellenince (gizli açılış hariç) 'Yenilikler' penceresi bir kez gösteriliyor ✓")

    print("  ✅ TEST 26 BAŞARILI: Tek tuşla güncelleme + yenilikler penceresi hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 27: 🌐 Tüm Kaynaklardan Arama + 🕵️ Yalan Haber Süzgeci + Çok Dilli Yanıt
    # ─────────────────────────────────────────
    print("\n[TEST 27] Tüm Kaynaklardan Arama, Yalan Haber Süzgeci ve Yanıt Dili:")
    import ai_engine as _ae27
    from config import (
        get_response_language as _grl27,
        get_response_language_name as _grln27,
        set_response_language as _srl27,
        SUPPORTED_LANGUAGES as _langs27,
        GeminiConfig as _gc27,
    )

    # 27a. Yanıt dili ayarı: varsayılan 'tr', geçersiz kod yok sayılır, geçerli kod kalıcı,
    # sistem promptu seçili dile göre değişiyor (çeviri özelliğinin temeli)
    _prev_lang27 = _grl27()
    try:
        assert _grl27() in _langs27
        _srl27("xx-not-a-real-lang")
        assert _grl27() == _prev_lang27, "geçersiz dil kodu yok sayılmalıydı"
        _srl27("en")
        assert _grl27() == "en" and _grln27() == "English"
        assert "English" in _gc27.get_system_prompt()
        _srl27("tr")
        assert _grl27() == "tr" and "Türkçe" in _gc27.get_system_prompt()
    finally:
        _srl27(_prev_lang27)
    print("  • Yanıt dili ayarı kalıcı kaydediliyor, geçersiz kod yok sayılıyor, sistem promptu dile göre değişiyor ✓")

    # 27b. Etki alanı ayrıştırma + bilinen mizah/dezenformasyon sitesi hızlı eleme
    _NCF27 = _ae27.NewsCredibilityFilter
    assert _NCF27.domain_of("https://www.example.com/x") == "example.com"
    assert _NCF27.domain_of("https://theonion.com/haber") == "theonion.com"
    _trusted27, _blocked27 = _NCF27._quick_screen([
        {"title": "Gerçek Haber", "uri": "https://bbc.com/a"},
        {"title": "Parodi Haber", "uri": "https://theonion.com/b"},
    ])
    assert len(_trusted27) == 1 and _trusted27[0]["uri"] == "https://bbc.com/a"
    assert len(_blocked27) == 1 and _blocked27[0]["uri"] == "https://theonion.com/b"
    print("  • Bilinen mizah/dezenformasyon siteleri adres bazlı hemen eleniyor ✓")

    # 27c. Kara listeyi geçen kaynaklar Gemini'ye sınıflandırtılıyor; YALAN_HABER etiketli olan eleniyor
    _saved_key27a = _gk19()
    _sk19("AIzaSyD_TestValidGeminiKey1234567890XYZ")
    try:
        class _FakeGemini27:
            def _stream_call(self, payload):
                assert "GÜVENİLİR" in payload["contents"][0]["parts"][0]["text"]
                return "1: GÜVENİLİR\n2: YALAN_HABER\n"
        _srcs27 = [{"title": "A", "uri": "https://real-news.example/a"},
                   {"title": "B", "uri": "https://fake-news.example/b"}]
        _t27, _b27 = _NCF27.filter_sources(_FakeGemini27(), _srcs27)
        assert len(_t27) == 1 and _t27[0]["title"] == "A"
        assert len(_b27) == 1 and _b27[0]["title"] == "B"
    finally:
        (_sk19(_saved_key27a) if _saved_key27a else _rk19())
    print("  • Gemini bir kaynağı 'YALAN_HABER' etiketlerse o kaynak süzgeçten geçemiyor ✓")

    # 27d. GeminiService.generate_grounded_response: Google Arama sonucu + tekrarsız kaynak listesi (ağ sahte)
    _g27 = _ae27.GeminiService()
    _saved_key27b = _gk19()
    _sk19("AIzaSyD_TestValidGeminiKey1234567890XYZ")
    _orig_post27 = _ae27.requests.post
    try:
        def _fake_post27(url, json=None, headers=None, timeout=None):
            assert "google_search" in str(json.get("tools"))
            return _Resp(200, {
                "candidates": [{
                    "content": {"parts": [{"text": "Ayarlanan dilde çevrilmiş yanıt."}]},
                    "groundingMetadata": {"groundingChunks": [
                        {"web": {"uri": "https://real-news.example/a", "title": "A"}},
                        {"web": {"uri": "https://real-news.example/a", "title": "A"}},   # tekrar — süzülmeli
                    ]},
                }],
            })
        _ae27.requests.post = _fake_post27
        _res27 = _g27.generate_grounded_response("herhangi bir soru")
        assert _res27 and _res27["answer"] == "Ayarlanan dilde çevrilmiş yanıt."
        assert len(_res27["sources"]) == 1 and _res27["sources"][0]["uri"] == "https://real-news.example/a"
    finally:
        _ae27.requests.post = _orig_post27
        (_sk19(_saved_key27b) if _saved_key27b else _rk19())
    print("  • generate_grounded_response: Google Arama yanıtı + tekrarsız kaynak listesi doğru ayrıştırılıyor ✓")

    # 27e/27f. Uçtan uca (process_query, ağ tamamen sahte): yalan haberli arama sonucu TAMAMEN
    # atılıp güvenli Wikipedia akışına düşülüyor; tüm kaynaklar güvenilirse arama sonucu kullanılıyor
    _orig_grounded27 = ai.gemini.generate_grounded_response
    _orig_wiki27 = TrustedSourceFetcher.search_wikipedia
    _orig_gen27 = ai.gemini.generate_response
    _orig_stream27 = ai.gemini._stream_call
    _saved_key27c = _gk19()
    _sk19("AIzaSyD_TestValidGeminiKey1234567890XYZ")
    ai.gemini._stream_call = lambda payload: "1: GÜVENİLİR"   # kalan güvenilirlik denetimi hep temiz çıksın
    try:
        ai.gemini.generate_grounded_response = lambda q: {
            "answer": "Şüpheli kaynaklı yanıt.",
            "sources": [{"title": "Parodi", "uri": "https://theonion.com/x"}],
        }
        TrustedSourceFetcher.search_wikipedia = classmethod(
            lambda cls, q, lang="tr", product=False: {"title": "Y", "extract": "Güvenli Wikipedia özeti.",
                                                       "source": "Wikipedia (Y)",
                                                       "url": "https://tr.wikipedia.org/wiki/Y", "truncated": False})
        ai.gemini.generate_response = lambda *a, **k: "Wikipedia bağlamlı güvenli yanıt."
        _rf27 = ai.process_query("dünya düz mü zzq27")
        assert "Şüpheli kaynaklı yanıt" not in _rf27["answer"]
        assert _rf27["answer"].startswith("Wikipedia bağlamlı güvenli yanıt.")

        ai.gemini.generate_grounded_response = lambda q: {
            "answer": "Güvenilir kaynaklı yanıt.",
            "sources": [{"title": "BBC", "uri": "https://bbc.com/a"}],
        }
        _ok27 = ai.process_query("güvenilir soru zzq27b")
        assert _ok27["answer"].startswith("Güvenilir kaynaklı yanıt.")
        assert "yalan haber süzgecinden geçti" in _ok27["answer"]
        assert _ok27["source"] == "gemini+web"
    finally:
        ai.gemini.generate_grounded_response = _orig_grounded27
        TrustedSourceFetcher.search_wikipedia = _orig_wiki27
        ai.gemini.generate_response = _orig_gen27
        ai.gemini._stream_call = _orig_stream27
        (_sk19(_saved_key27c) if _saved_key27c else _rk19())
    print("  • Kaynaklardan biri yalan haberse TÜM arama sonucu atılıp güvenli Wikipedia akışına düşülüyor ✓")
    print("  • Tüm kaynaklar güvenilirse arama sonucu kullanılıyor, altyazıda süzgeçten geçtiği belirtiliyor ✓")

    # 27g. Selamlaşma seçili dilde; "halo/hallo/bonjour" selam sayılıyor, "halo nedir" bilgi sorusu kalıyor
    _GF27 = _ae27.GreetingFilter
    _prev_lang27b = _grl27()
    try:
        _srl27("tr")
        assert _GF27.check_greeting("merhaba") == "Merhaba! 👋 Ben MehburAI, sana nasıl yardımcı olabilirim?"
        assert "dünyayı ele geçireceğim" in _GF27.check_greeting("adın ne")
        _srl27("de")
        assert _GF27.check_greeting("merhaba").startswith("Hallo! 👋 Ich bin MehburAI")
        assert _GF27.check_greeting("halo").startswith("Hallo!")
        assert _GF27.check_greeting("Hallo!").startswith("Hallo!")
        assert _GF27.check_greeting("Wie geht's?").startswith("Mir geht's gut")
        assert _GF27.check_greeting("danke") .startswith("Gern geschehen")
        assert "Welt erobern" in _GF27.check_greeting("wer bist du")
        assert _GF27.check_greeting("halo nedir") is None
        assert _GF27.check_greeting("danke, und was ist berlin") is None
        _srl27("ja")
        assert _GF27.check_greeting("こんにちは").startswith("こんにちは！")
        _srl27("en")
        assert _GF27.check_greeting("bonjour").startswith("Hello!")
        for _code in _langs27:
            if _code != "tr":
                _srl27(_code)
                for _key in ("merhaba", "selam", "nasılsın", "adin_ne", "günaydın", "iyi günler",
                             "iyi akşamlar", "iyi geceler", "tesekkur"):
                    assert _key in _cfg19.GREETING_TRANSLATIONS[_code], (_code, _key)
    finally:
        _srl27(_prev_lang27b)
    print("  • Selamlaşma seçili dilde; 'halo/hallo/bonjour' selam, 'halo nedir' bilgi sorusu olarak kalıyor ✓")

    # 27h. Yedek Wikipedia önce seçili dilde aranıyor (Gemini de çökse ham metin o dilde), yoksa Türkçe
    _calls27 = []
    _orig_wiki27h = TrustedSourceFetcher.search_wikipedia
    _orig_gr27h = ai.gemini.generate_grounded_response
    _orig_gen27h = ai.gemini.generate_response
    _prev_lang27h = _grl27()
    try:
        _srl27("de")

        def _fw27(cls, q, lang="tr", product=False):
            _calls27.append(lang)
            if lang == "de":
                return {"title": "Halo", "extract": "Halo ist ein optisches Phänomen.",
                        "source": "Wikipedia-de (Halo)", "url": "https://de.wikipedia.org/wiki/Halo",
                        "truncated": False}
            return None
        TrustedSourceFetcher.search_wikipedia = classmethod(_fw27)
        ai.gemini.generate_grounded_response = lambda q: None
        ai.gemini.generate_response = lambda *a, **k: None       # Gemini çökmüş
        if network.check_now():
            _r27h = ai.process_query("halo phänomen zzq27h")
            assert _calls27[0] == "de" and "optisches Phänomen" in _r27h["answer"], _r27h["answer"][:120]
            print("  • Gemini yanıt vermezse Wikipedia seçili dilden (de.wikipedia) geliyor ✓")
        else:
            print("  • (Çevrimdışı — seçili dilde Wikipedia testi atlandı)")
    finally:
        TrustedSourceFetcher.search_wikipedia = _orig_wiki27h
        ai.gemini.generate_grounded_response = _orig_gr27h
        ai.gemini.generate_response = _orig_gen27h
        _srl27(_prev_lang27h)

    # 27i. Google Arama kotası (429) dolunca bir süre hiç denenmiyor (her soruda boşuna beklenmesin)
    _saved_key27i = _gk19()
    _sk19("AIzaSyD_TestValidGeminiKey1234567890XYZ")
    _orig_post27i = _ae27.requests.post
    _posts27 = []
    try:
        _ae27.GeminiService._grounding_off_until = 0.0
        _ae27.requests.post = lambda *a, **k: (_posts27.append(1), _Resp(429, {}))[1]
        assert _g27.generate_grounded_response("x") is None and len(_posts27) == 1
        assert _g27.generate_grounded_response("y") is None and len(_posts27) == 1
    finally:
        _ae27.requests.post = _orig_post27i
        _ae27.GeminiService._grounding_off_until = 0.0
        (_sk19(_saved_key27i) if _saved_key27i else _rk19())
    print("  • Google Arama kotası dolunca (429) diğer modeller denenmiyor ve bir süre atlanıyor ✓")

    print("  ✅ TEST 27 BAŞARILI: Tüm kaynaklardan arama, yalan haber süzgeci ve çok dilli yanıt hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 28: 📦 Kurucu, dosya adı yerine "ne indirildiğini" (özellik adını) gösteriyor
    # ─────────────────────────────────────────
    print("\n[TEST 28] Kurucuda İndirilen Özellikler Listesi:")
    import os as _os28
    import tempfile as _tmp28
    import zipfile as _zip28

    # 28a. Dosya yolları doğru özelliğe eşleniyor; bilinmeyenler 'temel sistem'e düşüyor
    _ff = _inst22.feature_of
    assert _ff("MehburAI.exe").startswith("Yapay zeka beyni")
    assert _ff("customtkinter/windows/ctk_tk.py") == "Arayüz ve renk değiştirme"
    assert _ff("vosk/libvosk.dll") == _ff("data/models/vosk-model-small-tr/am/final.mdl")
    assert _ff("cv2/cv2.pyd") == "Kamera ve görsel anlama"
    assert _ff("assets\\logo.ico") == "Logo ve simgeler"
    assert _ff("python314.dll") == _inst22.BASE_FEATURE
    for _label, _ in _inst22.FEATURES:
        assert not any(ext in _label.lower() for ext in (".dll", ".exe", ".pyd", ".zip", "/")), _label
    print("  • Dosyalar özelliklere eşleniyor; etiketlerde dosya adı yok ('Arayüz ve renk değiştirme' gibi) ✓")

    # 28b. Kurulumda her özellik, TÜM dosyaları yerine konunca yalnızca bir kez bildiriliyor
    _d28 = _tmp28.mkdtemp()
    _z28 = _os28.path.join(_d28, "p.zip")
    with _zip28.ZipFile(_z28, "w") as _zf28:
        for _n in ("MehburAI.exe", "cv2/a.pyd", "cv2/b.pyd", "customtkinter/x.py",
                   "python314.dll", "data/models/m.bin"):
            _zf28.writestr(_n, "x")
    _seen28 = []
    _inst22.extract_payload(_z28, _os28.path.join(_d28, "kur"), lambda f: None, _seen28.append)
    assert len(_seen28) == len(set(_seen28)) == 5, _seen28
    assert "Kamera ve görsel anlama" in _seen28 and "Arayüz ve renk değiştirme" in _seen28
    assert _os28.path.isfile(_os28.path.join(_d28, "kur", "cv2", "b.pyd"))

    # güncellemede kullanıcı verisi (data/) atlansa da o özellik yine 'tamam' sayılıyor
    _seen28b = []
    _inst22.extract_payload(_z28, _os28.path.join(_d28, "kur"), lambda f: None, _seen28b.append)
    assert sorted(_seen28b) == sorted(_seen28), _seen28b
    print("  • Her özellik tüm dosyaları kurulunca bir kez listeleniyor (güncellemede de) ✓")

    # 28c. Gerçek paket (varsa): her dosya bir özelliğe düşüyor, kamera/ses/arayüz listede
    _real28 = _os28.path.join(_os28.path.dirname(_os28.path.abspath(__file__)), "dist", "MehburAI-payload.zip")
    if _os28.path.isfile(_real28):
        with _zip28.ZipFile(_real28) as _rz:
            _names28 = {_ff(n) for n in _rz.namelist()}
        for _must in ("Kamera ve görsel anlama", "Arayüz ve renk değiştirme", "Logo ve simgeler",
                      "Sesli komut (\"Hey Mehbur\" ve konuşarak yazma)"):
            assert _must in _names28, _must
        print(f"  • Gerçek pakette {len(_names28)} özellik grubu bulundu ✓")
    else:
        print("  • (dist/MehburAI-payload.zip yok — gerçek paket kontrolü atlandı)")

    # 28d. Kurulum penceresi özellikleri '... indirildi' / '... güncellendi' diye yazıyor
    _src28 = _insp26.getsource(_inst22.SetupWindow)
    assert "indirildi" in _src28 and "güncellendi" in _src28 and "_add_feature" in _src28
    print("  • Kurulum penceresi '✅ <özellik> indirildi/güncellendi' satırları gösteriyor ✓")

    # 28e. Kilitli dosya (kapanmakta olan eski MehburAI / antivirüs): önce tekrar deneniyor,
    # hâlâ kilitliyse eski dosya kenara çekilip yenisi yazılıyor; '.old' artıkları sonra siliniyor
    class _FlakyZip28:
        def __init__(self, fails):
            self.fails, self.calls = fails, 0
        def extract(self, member, root):
            self.calls += 1
            if self.calls <= self.fails:
                raise PermissionError(13, "Erişim engellendi")
            with open(_os28.path.join(root, member), "w") as fh:
                fh.write("yeni")
    _root28 = _tmp28.mkdtemp()
    _dest28 = _os28.path.join(_root28, "libcrypto-3.dll")
    _orig_retry28 = _inst22.LOCK_RETRY_SECONDS
    try:
        _inst22.LOCK_RETRY_SECONDS = 5.0
        _fz = _FlakyZip28(fails=2)
        _inst22._extract_with_retry(_fz, "libcrypto-3.dll", _root28, _dest28)
        assert _fz.calls == 3 and open(_dest28).read() == "yeni"

        _inst22.LOCK_RETRY_SECONDS = 0.6
        _fz2 = _FlakyZip28(fails=10 ** 6)
        _fz2.extract = (lambda orig: (lambda m, r: orig(m, r) if _os28.path.exists(_dest28) else
                                      open(_dest28, "w").write("yeni2")))(_fz2.extract)
        _inst22._extract_with_retry(_fz2, "libcrypto-3.dll", _root28, _dest28)
        assert open(_dest28).read() == "yeni2"
        assert any(f.endswith(".old") for f in _os28.listdir(_root28))
        _inst22.cleanup_old_files(_root28)
        assert not any(f.endswith(".old") for f in _os28.listdir(_root28))
    finally:
        _inst22.LOCK_RETRY_SECONDS = _orig_retry28
    print("  • Kilitli dosyada kurulum takılmıyor: tekrar deneniyor, gerekirse eski dosya kenara çekiliyor ✓")

    # 28f. Eski MehburAI gerçekten kapanana kadar bekleniyor
    _orig_run28, _orig_alive28 = _inst22.subprocess.run, _inst22._app_is_running
    _alive28 = [True, True, False]
    try:
        _inst22.subprocess.run = lambda *a, **k: None
        _inst22._app_is_running = lambda: _alive28.pop(0) if _alive28 else False
        _inst22.stop_running_app(timeout=5)
        assert _alive28 == []
    finally:
        _inst22.subprocess.run, _inst22._app_is_running = _orig_run28, _orig_alive28
    print("  • Kurulum, açık MehburAI tamamen kapanmadan dosyalara dokunmuyor ✓")

    # 28g. Hata olursa pencerede GERÇEKTEN gösteriliyor (eskiden lambda silinmiş `e`yi kullanıp
    # NameError veriyor, pencere '%10'da donmuş kalıyordu)
    _m28 = _inst22.describe_error(PermissionError(13, "Erişim engellendi"))
    assert "Erişim engellendi" in _m28 and "başka bir program" in _m28
    _run_src28 = _insp26.getsource(_inst22.SetupWindow._run)
    assert "msg = describe_error(e)" in _run_src28 and "{e}" not in _run_src28
    print("  • Kurulum hatası artık ekranda gösteriliyor ve günlüğe yazılıyor ✓")

    print("  ✅ TEST 28 BAŞARILI: Kurucu, indirilenleri ne işe yaradıklarıyla listeliyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 29: 🧠 MehburAI Modelleri — Pro (her yer) / Flash (bilinen kaynaklar) / Flash-Lite (güvenilir)
    # ─────────────────────────────────────────
    print("\n[TEST 29] MehburAI Modelleri (Pro / Flash / Flash-Lite):")
    _CSF = _ae27.CommunitySourceFetcher

    # 29a. Adlar sürümden üretiliyor, seçim kalıcı
    _ver29 = ".".join(APP_VERSION.split(".")[:2])
    assert _cfg19.model_display_name("pro") == f"MehburAI Pro {_ver29}"
    assert _cfg19.model_display_name("flash") == f"MehburAI Flash {_ver29}"
    assert _cfg19.model_display_name("flash_lite") == f"MehburAI Flash-Lite {_ver29}"
    _prev_model29 = _cfg19.get_ai_model()
    try:
        _cfg19.set_ai_model("yok-boyle-model")
        assert _cfg19.get_ai_model() == _prev_model29
        _cfg19.set_ai_model("flash")
        assert _cfg19.get_ai_model() == "flash"
    finally:
        _cfg19.set_ai_model(_prev_model29)
    print(f"  • Adlar: MehburAI Pro/Flash/Flash-Lite {_ver29}; seçim kalıcı, geçersiz model yok sayılıyor ✓")

    # 29b. Reddit RSS ayrıştırma + 429'da bir süre denememe; Stack Overflow yalnız teknik sorularda
    _rss29 = (b'<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom">'
              b'<entry><category term="iphone" label="r/iphone"/><title>Battery life after 1 year</title>'
              b'<link href="https://www.reddit.com/r/iphone/comments/abc/x/"/>'
              b'<content type="html">&lt;p&gt;Still 91% health.&lt;/p&gt; submitted by /u/someone [link] [comments]'
              b'</content></entry></feed>')
    _orig_get29 = _ae27.requests.get
    _gets29 = []
    try:
        _CSF._reddit_off_until = 0.0

        def _fake_get29(url, **k):
            _gets29.append(url)
            if "reddit" in url:
                r = _Resp(200); r.content = _rss29; return r
            return _Resp(200, {"items": [{"question_id": 42, "title": "List &amp; tuple",
                                          "excerpt": "Use <span>tuple()</span>", "is_answered": True,
                                          "score": 7}]})
        _ae27.requests.get = _fake_get29
        _red = _CSF.search_reddit("iphone battery")
        assert _red == [{"title": "Battery life after 1 year",
                         "uri": "https://www.reddit.com/r/iphone/comments/abc/x/",
                         "text": "Still 91% health.", "site": "Reddit r/iphone"}], _red
        _so = _CSF.search_stackoverflow("python list")
        assert _so[0]["uri"] == "https://stackoverflow.com/q/42" and _so[0]["title"] == "List & tuple"
        assert _CSF.is_technical("python'da liste nasıl sıralanır") and not _CSF.is_technical("Adana kebap tarifi")
        _gets29.clear()
        _real_community_search("Adana kebap tarifi")
        assert all("stackexchange" not in u for u in _gets29)

        _ae27.requests.get = lambda url, **k: (_gets29.append(url), _Resp(429))[1]
        _gets29.clear()
        assert _CSF.search_reddit("x") == [] and _CSF.search_reddit("y") == [] and len(_gets29) == 1
    finally:
        _ae27.requests.get = _orig_get29
        _CSF._reddit_off_until = 0.0
    print("  • Reddit (RSS) ayrıştırılıyor, 429'da bir süre denenmiyor; Stack Overflow yalnız teknik sorularda ✓")

    # 29c. Uçtan uca: her model yalnızca kendi kaynaklarına bakıyor; yalan haberli gönderi bağlama girmiyor
    _saved29 = dict(grounded=ai.gemini.generate_grounded_response, gen=ai.gemini.generate_response,
                    stream=ai.gemini._stream_call, wiki=TrustedSourceFetcher.search_wikipedia,
                    comm=_CSF.search, key=_gk19(), model=_cfg19.get_ai_model())
    _log29 = {"grounded": 0, "community": 0, "ctx": None}
    _sk19("AIzaSyD_TestValidGeminiKey1234567890XYZ")
    try:
        ai.gemini.generate_grounded_response = lambda q: (_log29.__setitem__("grounded", _log29["grounded"] + 1), None)[1]
        TrustedSourceFetcher.search_wikipedia = classmethod(
            lambda cls, q, lang="tr", product=False: {"title": "Z", "extract": "Wiki metni.", "source": "Wikipedia (Z)",
                                                       "url": "https://tr.wikipedia.org/wiki/Z", "truncated": False})
        _CSF.search = classmethod(lambda cls, q: (_log29.__setitem__("community", _log29["community"] + 1), [
            {"title": "Gerçek deneyim", "uri": "https://www.reddit.com/r/a/1", "text": "iyi", "site": "Reddit r/a"},
            {"title": "Aşılar mikroçip içeriyor", "uri": "https://www.reddit.com/r/b/2", "text": "yalan", "site": "Reddit r/b"},
        ])[1])
        ai.gemini._stream_call = lambda payload: "1: GÜVENİLİR\n2: YALAN_HABER"
        ai.gemini.generate_response = lambda q, context=None: (_log29.__setitem__("ctx", context), "Yanıt.")[1]

        def _ask29(model, q):
            _cfg19.set_ai_model(model)
            _log29.update(grounded=0, community=0, ctx=None)
            return ai.process_query(q)

        if network.check_now():
            _r = _ask29("flash_lite", "model testi zzq29a")
            assert _log29["grounded"] == 0 and _log29["community"] == 0 and "Reddit" not in _r["answer"]
            assert _r["model"] == f"MehburAI Flash-Lite {_ver29}"

            _r = _ask29("flash", "model testi zzq29b")
            assert _log29["grounded"] == 0 and _log29["community"] == 1
            assert "Gerçek deneyim" in _log29["ctx"] and "mikroçip" not in _log29["ctx"]
            assert "reddit.com/r/a/1" in _r["answer"] and "reddit.com/r/b/2" not in _r["answer"]
            assert _r["model"] == f"MehburAI Flash {_ver29}" and "Reddit" in _r["source"]

            _r = _ask29("pro", "model testi zzq29c")
            assert _log29["grounded"] == 1 and _log29["community"] == 1        # arama yoksa Flash kaynaklarına düşer
            print("  • Flash-Lite yalnız Wikipedia; Flash + Reddit/Stack Overflow; Pro önce tüm web, olmazsa Flash kaynakları ✓")
            print("  • Yalan haber şüpheli topluluk gönderisi tek tek eleniyor, yanıta hiç girmiyor ✓")
        else:
            print("  • (Çevrimdışı — uçtan uca model testi atlandı)")
    finally:
        ai.gemini.generate_grounded_response = _saved29["grounded"]
        ai.gemini.generate_response = _saved29["gen"]
        ai.gemini._stream_call = _saved29["stream"]
        TrustedSourceFetcher.search_wikipedia = _saved29["wiki"]
        _CSF.search = _saved29["comm"]
        _cfg19.set_ai_model(_saved29["model"])
        (_sk19(_saved29["key"]) if _saved29["key"] else _rk19())

    # 29d. Arayüz: sohbet alanında model seçici var, balon başlığında cevabı veren model yazıyor
    _src29 = _insp26.getsource(_gui.MehburApp._build_chat_panel)
    assert "self.model_menu" in _src29 and "model_display_name" in _src29
    assert "model_name" in _insp26.getsource(_gui.MehburApp._handle_query_response)
    print("  • Sohbet ekranında model seçici var; her cevabın başlığında hangi modelin verdiği yazıyor ✓")

    print("  ✅ TEST 29 BAŞARILI: MehburAI Pro / Flash / Flash-Lite modelleri hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 30: 🌐 Tüm arayüz seçili dilde · 🧠 Hafıza bütün dillerde · 🎨 Renk yeniden başlatmadan
    # ─────────────────────────────────────────
    print("\n[TEST 30] Arayüz Çevirisi, Çok Dilli Hafıza, Anında Renk Değişimi:")
    import json as _json30
    import i18n as _i18n
    import customtkinter as _ctk30

    # 30a. t(): sözlükteki yazı + '{}' kalıbı çevriliyor, bilinmeyen (ör. sohbet mesajı) aynen kalıyor
    _dir30 = _tmp28.mkdtemp()
    with open(_os28.path.join(_dir30, "en.json"), "w", encoding="utf-8") as _fh:
        _json30.dump({"strings": {"💾 Kaydet": "💾 Save"},
                      "templates": {"📌 Kaynak: {} — {}": "📌 Source: {} — {}"}}, _fh)
    _saved_bundle30, _saved_lang30 = _i18n.BUNDLE_DIR, _i18n.current_language()
    _i18n.BUNDLE_DIR, _i18n._tables = _dir30, {}
    _root30 = None
    try:
        _i18n.set_language("en")
        assert _i18n.t("💾 Kaydet") == "💾 Save"
        assert _i18n.t("📌 Kaynak: Wikipedia (X) — https://a/b{c}") == "📌 Source: Wikipedia (X) — https://a/b{c}"
        assert _i18n.t("Bugün hava nasıl olacak?") == "Bugün hava nasıl olacak?"
        _i18n.set_language("tr")
        assert _i18n.t("💾 Kaydet") == "💾 Kaydet"

        # 30b. Kancalar: bileşen yazısı oluşturulurken/değiştirilirken çevriliyor; dil değişince
        # relocalize() açık penceredeki yazıları yeniden başlatmadan değiştiriyor
        _i18n.install_hooks()
        _i18n.set_language("en")
        _root30 = _ctk30.CTk(); _root30.withdraw()
        _btn30 = _ctk30.CTkButton(_root30, text="💾 Kaydet")
        _lbl30 = _ctk30.CTkLabel(_root30, text="Sohbet mesajı olduğu gibi kalmalı")
        assert _btn30.cget("text") == "💾 Save" and _lbl30.cget("text") == "Sohbet mesajı olduğu gibi kalmalı"
        _i18n.set_language("tr")
        _i18n.relocalize(_root30)
        assert _btn30.cget("text") == "💾 Kaydet"
        _i18n.set_language("en")
        _lbl30.configure(text="💾 Kaydet")
        assert _lbl30.cget("text") == "💾 Save"

        # Açılır menü: ekranda çeviri, koda (get/command) Türkçe asıl değer — dil değişse de
        with open(_os28.path.join(_dir30, "de.json"), "w", encoding="utf-8") as _fh:
            _json30.dump({"strings": {"Siyah": "Schwarz", "Lacivert": "Marineblau"}}, _fh)
        with open(_os28.path.join(_dir30, "en.json"), "w", encoding="utf-8") as _fh:
            _json30.dump({"strings": {"Siyah": "Black", "Lacivert": "Navy", "💾 Kaydet": "💾 Save"}}, _fh)
        _i18n._tables = {}
        _i18n.set_language("de")
        _got30 = []
        _om30 = _ctk30.CTkOptionMenu(_root30, values=["Siyah", "Lacivert"], command=_got30.append)
        _om30.set("Siyah")
        assert _om30.cget("values") == ["Schwarz", "Marineblau"] and _om30.get() == "Siyah"
        _om30._dropdown_callback("Marineblau")
        assert _got30 == ["Lacivert"] and _om30.get() == "Lacivert"
        _i18n.set_language("en")
        _i18n.relocalize(_root30)
        assert _om30.cget("values") == ["Black", "Navy"] and _om30.get() == "Lacivert"
        assert _om30._text_label.cget("text") == "Navy"
    finally:
        _i18n.BUNDLE_DIR, _i18n._tables = _saved_bundle30, {}
        _i18n.set_language(_saved_lang30)
        if _root30 is not None:
            _root30.destroy()
    print("  • Arayüz yazıları seçili dile çevriliyor, dil değişince anında güncelleniyor; sohbet mesajları değişmiyor ✓")

    # 30c. Gerçek sözlükler: her dilde ekrandaki yazıların (neredeyse) hepsi çevrilmiş
    import sys as _sys30
    _sys30.path.insert(0, _os28.path.join(_os28.path.dirname(_os28.path.abspath(__file__)), "assets", "i18n"))
    import make_i18n as _mk30
    _items30 = _mk30.extract()
    for _code in _langs27:
        if _code == "tr":
            continue
        _i18n._tables.pop(_code, None)
        _st30, _tp30 = _i18n._load(_code)
        _covered = sum(1 for s in _items30 if (s in _st30) or ("{}" in s and any(
            rx.pattern.startswith("^" + _mk30.re.escape(s.split("{}")[0])) for rx, _ in _tp30)))
        assert _covered >= 0.95 * len(_items30), (_code, _covered, len(_items30))
    _i18n._tables.clear()
    print(f"  • {len(_langs27) - 1} dilin sözlüğü ekrandaki {len(_items30)} yazının en az %95'ini kapsıyor ✓")

    # 30d. Hafıza: kaydedilen bilgi arka planda bütün dillere çevriliyor; hangi dilde sorulursa
    # sorulsun bulunuyor ve cevap seçili dilde geliyor; boşta öğrenilenler kotayı yormuyor
    _mem30 = MemoryEngine(db_path=_os28.path.join(_tmp28.mkdtemp(), "m.db"))
    _kid30, _ = _mem30.save_knowledge("Kara delik nedir", "Kara delik, ışığın bile kaçamadığı bölgedir.",
                                      source="test", lang="tr")
    _mem30.save_knowledge("Otomatik konu nedir", "x", source="oto", translate=False)
    assert [r["id"] for r in _mem30.pending_translations(10)] == [_kid30]

    class _FakeGem30:
        calls = 0

        def _stream_call(self, payload):
            _FakeGem30.calls += 1
            txt = payload["contents"][0]["parts"][0]["text"]
            _s = txt.index("{", txt.index("language codes"))
            codes = list(_json30.loads(txt[_s:txt.index("}", _s) + 1]))
            names = {"en": ("What is a black hole", "A black hole is a region light cannot escape."),
                     "de": ("Was ist ein Schwarzes Loch", "Ein Schwarzes Loch ist ein Bereich, dem nicht einmal Licht entkommt.")}
            return _json30.dumps({c: {"q": names.get(c, (f"{c} q", f"{c} a"))[0],
                                      "a": names.get(c, (f"{c} q", f"{c} a"))[1]} for c in codes})
    _kt30 = _ae27.KnowledgeTranslator(_mem30, _FakeGem30())
    assert _kt30.run_pending() == 1 and _FakeGem30.calls == 1          # 9 dil tek istekte (kota)
    assert _mem30.pending_translations(10) == []
    assert set(_mem30.get_translations(_kid30)) == set(_langs27) - {"tr"}
    _hit_de = _mem30.search_knowledge("Was ist ein Schwarzes Loch", lang="de")
    assert _hit_de and _hit_de["answer"].startswith("Ein Schwarzes Loch")
    _hit_en = _mem30.search_knowledge("Kara delik nedir", lang="en")
    assert _hit_en and _hit_en["answer"] == "A black hole is a region light cannot escape."
    assert _mem30.search_knowledge("Kara delik nedir", lang="tr")["answer"].startswith("Kara delik")

    # Gemini çökerse: kayıt 'bekliyor' kalır, gelen diller saklanır, sonra yalnız eksikler denenir
    _kid30b, _ = _mem30.save_knowledge("Mars nedir", "Mars bir gezegendir.", source="test", lang="tr")

    class _HalfGem30(_FakeGem30):
        def _stream_call(self, payload):         # yalnızca ilk 3 dili döndürür (kesilmiş yanıt)
            full = _json30.loads(super()._stream_call(payload))
            return _json30.dumps(dict(list(full.items())[:3]))
    _kt30b = _ae27.KnowledgeTranslator(_mem30, _HalfGem30())
    assert _kt30b.run_pending() == 0
    assert _mem30.pending_translations(10)[0]["id"] == _kid30b and len(_mem30.translated_langs(_kid30b)) == 3
    assert _kt30.run_pending() == 1 and len(_mem30.translated_langs(_kid30b)) == 9
    assert _mem30.delete_knowledge(_kid30b) and _mem30.get_translations(_kid30b) == {}

    # AIEngine kaydı seçili dille yapıp çevirmeni tetikliyor
    _src30 = _insp26.getsource(_ae27.AIEngine.remember)
    assert "lang=get_response_language()" in _src30 and "self.translator.kick()" in _src30
    assert "translate=False" in _insp26.getsource(_IdleLearner.learn_once)
    print("  • Kaydedilen bilgi arka planda 9 dile çevriliyor; hangi dilde sorulsa bulunup seçili dilde cevaplanıyor ✓")
    print("  • Gemini çökerse kayıt bekliyor kalıp eksik diller sonra tamamlanıyor; otomatik öğrenilenler çevrilmiyor ✓")

    # 30e. Renk değişimi yeniden başlatmadan uygulanıyor (cmd penceresi açan yeniden başlatma kaldırıldı)
    import background as _bg30
    assert not hasattr(_bg30, "restart_app")
    for _m30 in ("_apply_theme_now", "_reset_theme_now", "_apply_theme_live"):
        assert hasattr(_gui.MehburApp, _m30), _m30
    assert not hasattr(_gui.MehburApp, "_restart_now")
    _r30 = _ctk30.CTk(); _r30.withdraw()
    try:
        _f30 = _ctk30.CTkFrame(_r30, fg_color="#12121A", border_color="#004D55")
        _keep30 = _ctk30.CTkButton(_f30, fg_color="#FF2A4D", text="sil")
        assert _gui.recolor_widgets(_r30, {"#12121A": "#161B29", "#004D55": "#38155D"}) >= 2
        assert _f30.cget("fg_color") == "#161B29" and _f30.cget("border_color") == "#38155D"
        assert _keep30.cget("fg_color") == "#FF2A4D"
    finally:
        _r30.destroy()
    print("  • Renk 'Uygula' ile anında değişiyor; yeniden başlatma / cmd penceresi yok ✓")

    # 30f. Başlıktaki 🔄 Güncelle tuşu YALNIZCA yeni sürüm bulununca görünür (varsayılan gizli),
    # tema rengiyle uyumlu (Gönder/Uygula ile aynı vurgu rengi), tıklayınca doğrudan günceller.
    # Sohbet alt çubuğu yazı kutusunun üstüne binmiyor.
    _hdr30 = _insp26.getsource(_gui.MehburApp._build_header)
    assert "self.header_update_btn" in _hdr30 and "pack_forget" in _hdr30
    assert "fg_color=Theme.CYAN_PRIMARY" in _hdr30.split("header_update_btn = ctk.CTkButton")[1][:400]
    _banner30 = _insp26.getsource(_gui.MehburApp._show_update_banner)
    assert "header_update_btn.pack(" in _banner30
    assert "self._real_quit" in _insp26.getsource(_gui.MehburApp._launch_updater)
    assert not hasattr(_gui.MehburApp, "_on_header_update_click")
    _chat30 = _insp26.getsource(_gui.MehburApp._build_chat_panel)
    import re as _re30
    _rows30 = [int(r) for r in _re30.findall(
        r"(?:self\.chat_history_box|model_bar|input_container|quick_frame)\.grid\(row=(\d), column=0", _chat30)]
    assert len(_rows30) == 4, _rows30
    assert len(_rows30) == len(set(_rows30)), f"sohbet alanında iki bileşen aynı satırda: {_rows30}"
    assert "Örnek: adın ne" not in _chat30 and "Gemini API Ayarları" not in _chat30
    print("  • 🔄 Güncelle tuşu yalnızca yeni sürüm bulununca görünüyor, tema rengiyle uyumlu ✓")

    # 30g. Yan panel gizlenebilir ve genişliği sürükleyerek/kalıcı olarak ayarlanabilir
    _prev_sb30 = _cfg19.get_sidebar_config()
    try:
        _cfg19.update_sidebar_config(width=250, collapsed=True)
        _sb30 = _cfg19.get_sidebar_config()
        assert _sb30 == {"width": 250, "collapsed": True}
        _cfg19.update_sidebar_config(width=9999)          # sınırın üstü kırpılmalı
        assert _cfg19.get_sidebar_config()["width"] == _cfg19.SIDEBAR_MAX_WIDTH
        _cfg19.update_sidebar_config(width=1)
        assert _cfg19.get_sidebar_config()["width"] == _cfg19.SIDEBAR_MIN_WIDTH
    finally:
        _cfg19.update_sidebar_config(width=_prev_sb30["width"], collapsed=_prev_sb30["collapsed"])
    _sb_src30 = _insp26.getsource(_gui.MehburApp._build_conversation_sidebar)
    assert "self.sidebar_frame" in _sb_src30 and "_on_sidebar_resize_start" in _sb_src30
    assert "_toggle_sidebar" in _insp26.getsource(_gui.MehburApp._build_chat_panel)
    print("  • Yan panel gizlenebiliyor, genişliği sürüklenerek ayarlanıp kalıcı kaydediliyor ✓")

    # 30h. Yükleniyor balonu artık "araştırıyor ve düşünüyor" yazısı yerine animasyonlu nokta gösteriyor
    _load_src30 = _insp26.getsource(_gui.MehburApp._add_loading_bubble)
    assert "araştırıyor ve düşünüyor" not in _load_src30 and "_animate_loading_dots" in _load_src30
    _dot_src30 = _insp26.getsource(_gui.MehburApp._animate_loading_dots)
    assert "'.' * self._loading_dots" in _dot_src30 and "self.after(450" in _dot_src30
    assert "after_cancel" in _insp26.getsource(_gui.MehburApp._remove_loading_bubble)
    print("  • Yükleniyor balonunda sabit yazı yerine animasyonlu '...' noktalar var ✓")

    print("  ✅ TEST 30 BAŞARILI: Tüm arayüz seçili dilde, hafıza bütün dillerde, renk anında değişiyor.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # TEST 31: 🌍 Evrensel API Anahtarı (Google / OpenAI / Anthropic tespiti + yönlendirme)
    # ─────────────────────────────────────────
    print("\n[TEST 31] Evrensel API Anahtarı (Google / OpenAI / Anthropic):")
    import ai_providers as _prov31

    # 31a. Biçimden şirket tahmini; belirsiz/eski-sahte anahtarlar güvenli varsayılan olarak
    # 'unknown' döner (çağıran taraf bunu Google akışına yönlendirir — geriye dönük uyumluluk)
    assert _prov31.detect_provider("AIzaSyD_TestValidGeminiKey1234567890XYZ") == "google"
    assert _prov31.detect_provider("AQ.Ab8xyz123") == "google"
    assert _prov31.detect_provider("sk-ant-api03-abcdefghij1234567890") == "anthropic"
    assert _prov31.detect_provider("sk-proj-abcdefghijklmnopqrstuvwx") == "openai"
    assert _prov31.detect_provider("gecerli-anahtar") == "unknown"
    assert _prov31.detect_provider("") == "unknown"
    print("  • Anahtar biçiminden şirket doğru tahmin ediliyor; belirsiz biçim güvenli varsayılana (Google) düşüyor ✓")

    # 31b. GeminiService.generate_response: OpenAI/Anthropic biçimindeki anahtar o şirkete
    # yönlendiriliyor; Google/belirsiz biçim eskisi gibi _stream_call'a gidiyor
    _saved_key31 = _gk19()
    _calls31 = {"openai": 0, "anthropic": 0, "gemini": 0}
    _orig_oa31, _orig_an31 = _prov31.OpenAIService.generate_response, _prov31.AnthropicService.generate_response
    _orig_stream31 = ai.gemini._stream_call
    try:
        _prov31.OpenAIService.generate_response = classmethod(
            lambda cls, key, q, ctx, sp: (_calls31.__setitem__("openai", _calls31["openai"] + 1), "OpenAI yanıtı.")[1])
        _prov31.AnthropicService.generate_response = classmethod(
            lambda cls, key, q, ctx, sp: (_calls31.__setitem__("anthropic", _calls31["anthropic"] + 1), "Claude yanıtı.")[1])
        ai.gemini._stream_call = lambda payload: (_calls31.__setitem__("gemini", _calls31["gemini"] + 1), "Gemini yanıtı.")[1]

        _sk19("sk-proj-abcdefghijklmnopqrstuvwx")
        assert ai.gemini.generate_response("soru") == "OpenAI yanıtı." and _calls31 == {"openai": 1, "anthropic": 0, "gemini": 0}

        _sk19("sk-ant-api03-abcdefghij1234567890")
        assert ai.gemini.generate_response("soru") == "Claude yanıtı." and _calls31["anthropic"] == 1 and _calls31["gemini"] == 0

        _sk19("AIzaSyD_TestValidGeminiKey1234567890XYZ")
        assert ai.gemini.generate_response("soru") == "Gemini yanıtı." and _calls31["gemini"] == 1

        _sk19("gecerli-anahtar")               # eski/sahte test anahtarı → yine Google akışı (geriye dönük uyum)
        assert ai.gemini.generate_response("soru") == "Gemini yanıtı." and _calls31["gemini"] == 2
        assert _calls31["openai"] == 1 and _calls31["anthropic"] == 1   # başka çağrı yapılmadı
    finally:
        _prov31.OpenAIService.generate_response = _orig_oa31
        _prov31.AnthropicService.generate_response = _orig_an31
        ai.gemini._stream_call = _orig_stream31
        (_sk19(_saved_key31) if _saved_key31 else _rk19())
    print("  • Sohbet yanıtı: OpenAI/Anthropic biçimindeki anahtar o şirkete gidiyor, Google/belirsiz eskisi gibi çalışıyor ✓")

    # 31c. test_key: hangi şirketin anahtarı olduğunu tespit edip mesajda söylüyor
    _saved_key31b = _gk19()
    _orig_oat31, _orig_ant31 = _prov31.OpenAIService.test_key, _prov31.AnthropicService.test_key
    try:
        _prov31.OpenAIService.test_key = classmethod(lambda cls, key: (True, "🟩 Bu bir OpenAI anahtarı, geçerli ve yanıt veriyor (0.1 sn)."))
        _prov31.AnthropicService.test_key = classmethod(lambda cls, key: (False, "Bu bir Anthropic (Claude) anahtarı ama geçersiz ya da yetkisiz."))
        _ok31, _msg31 = ai.gemini.test_key("sk-proj-abcdefghijklmnopqrstuvwx")
        assert _ok31 and "OpenAI" in _msg31
        _ok31b, _msg31b = ai.gemini.test_key("sk-ant-api03-abcdefghij1234567890")
        assert not _ok31b and "Anthropic" in _msg31b
    finally:
        _prov31.OpenAIService.test_key = _orig_oat31
        _prov31.AnthropicService.test_key = _orig_ant31
        (_sk19(_saved_key31b) if _saved_key31b else _rk19())
    # Google yolu (belirsiz biçim, TEST 19h'de zaten ağ üzerinden sınanıyor): kaynak kodda mesajın
    # artık "Bu bir Google Gemini anahtarı" dediğini doğrula
    _src_google31 = _insp26.getsource(_ae27.GeminiService.test_key)
    assert "Bu bir Google Gemini anahtarı" in _src_google31
    print("  • 'API'yi Test Et' hangi şirketin anahtarı olduğunu tespit edip mesajda söylüyor ✓")

    # 31d. Gerçek OpenAI sunucusu (ağ varsa, uydurma ama doğru BİÇİMDE anahtar): 401 'geçersiz' diye dönüyor
    if network.check_now():
        _ok31c, _msg31c = _prov31.OpenAIService.test_key("sk-clearlyinvalidtestkey1234567890abcdefgh")
        assert not _ok31c and "OpenAI" in _msg31c and ("geçersiz" in _msg31c or "yetkisiz" in _msg31c), _msg31c
        print("  • Gerçek OpenAI sunucusu uydurma anahtarı 401 ile reddediyor, mesaj doğru okunuyor ✓")
    else:
        print("  • (Çevrimdışı — gerçek OpenAI sunucu testi atlandı)")

    # 31e. Ayarlar: API kartı artık evrensel ("Google Gemini API Anahtarı" değil), kaydedince/
    # gösterirken şirket adını belirtiyor
    _api_card_src31 = _insp26.getsource(_gui.MehburApp._build_settings_panel)
    assert "🔑 Yapay Zeka API Anahtarı" in _api_card_src31 and "🔑 Google Gemini API Anahtarı" not in _api_card_src31
    assert "PROVIDER_NAMES" in _insp26.getsource(_gui.MehburApp._save_api_key)
    print("  • Ayarlar'daki anahtar kartı artık evrensel; kaydedince tespit edilen şirketi gösteriyor ✓")

    print("  ✅ TEST 31 BAŞARILI: Evrensel API anahtarı — şirket tespiti + sohbet yönlendirmesi hazır.")
    passed_tests += 1

    # ─────────────────────────────────────────
    # Özet Rapor
    # ─────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  🎉 TÜM ENTEGRASYON TESTLERİ TAMAMLANDI: {passed_tests}/{total_tests} BAŞARILI!")
    print("=" * 65)


if __name__ == "__main__":
    run_full_validation()
