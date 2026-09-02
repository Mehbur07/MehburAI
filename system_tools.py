# -*- coding: utf-8 -*-
"""
MehburAI - Bilgisayar & Sistem Araçları (System Tools)
======================================================
MehburAI'nin kullanıcının bilgisayarını gerçek anlamda kullanabilmesini sağlayan
modül. Sadece birkaç sabit uygulama değil; program açma, dosya/klasör işlemleri,
sistem kontrolü (ses, parlaklık, kilit, uyku, ekran görüntüsü) ve güç komutları.

Yetenekler:
  • Program Açma .......... Herhangi bir uygulamayı adından bulup açar
                            (Spotify, Word, Chrome, Ayarlar, Kamera, ...)
  • Dosya / Klasör ........ Bilinen klasörleri açar, dosya arar, klasör/dosya oluşturur
  • Sistem Kontrolü ....... Ses aç/kıs/sustur, parlaklık, ekranı kilitle, uyku,
                            ekran görüntüsü alma
  • Güç Komutları ......... Kapatma / yeniden başlatma (gecikmeli + iptal edilebilir)
  • Bilgi ................. Saat, tarih, sistem/donanım/disk durumu

Not: Tüm işlemler yalnızca yerel makinede, kullanıcının kendi oturumunda çalışır.
"""

import ctypes
import difflib
import glob
import os
import platform
import re
import shutil
import subprocess
import time
from datetime import datetime
from typing import Optional

from memory_engine import clean_text


# ─────────────────────────────────────────────
# Yardımcı Sabitler
# ─────────────────────────────────────────────

HOME = os.path.expanduser("~")

# Bilinen kullanıcı klasörleri (Türkçe takma adlar → gerçek yol)
KNOWN_FOLDERS = {
    "masaüstü": os.path.join(HOME, "Desktop"),
    "masaustu": os.path.join(HOME, "Desktop"),
    "indirilenler": os.path.join(HOME, "Downloads"),
    "indirilen": os.path.join(HOME, "Downloads"),
    "belgeler": os.path.join(HOME, "Documents"),
    "belgelerim": os.path.join(HOME, "Documents"),
    "dokümanlar": os.path.join(HOME, "Documents"),
    "resimler": os.path.join(HOME, "Pictures"),
    "resimlerim": os.path.join(HOME, "Pictures"),
    "fotoğraflar": os.path.join(HOME, "Pictures"),
    "müzik": os.path.join(HOME, "Music"),
    "müziklerim": os.path.join(HOME, "Music"),
    "videolar": os.path.join(HOME, "Videos"),
    "videolarım": os.path.join(HOME, "Videos"),
}

# Uygulama takma adları → çalıştırılabilir komut / URI
KNOWN_APPS = {
    "not defteri": "notepad", "notepad": "notepad", "notdefteri": "notepad",
    "hesap makinesi": "calc", "hesap makinası": "calc", "hesap makinesı": "calc",
    "calc": "calc", "hesap makinesi": "calc",
    "paint": "mspaint", "resim": "mspaint",
    "boya": "mspaint",
    "wordpad": "wordpad",
    "komut istemi": "cmd", "cmd": "cmd", "konsol": "cmd", "terminal": "wt",
    "powershell": "powershell",
    "kayıt defteri": "regedit", "regedit": "regedit",
    "görev yöneticisi": "taskmgr", "taskmgr": "taskmgr",
    "denetim masası": "control", "kontrol paneli": "control",
    "dosya gezgini": "explorer", "explorer": "explorer", "dosyalar": "explorer",
    "aygıt yöneticisi": "devmgmt.msc", "disk yönetimi": "diskmgmt.msc",
    "hizmetler": "services.msc",
    "ekran alıntısı": "snippingtool", "ekran alıntı": "snippingtool",
    "makas": "snippingtool", "snipping": "snippingtool",
    "ayarlar": "ms-settings:", "windows ayarları": "ms-settings:",
    "kamera": "microsoft.windows.camera:",
    "takvim": "outlookcal:", "posta": "outlookmail:", "mail": "outlookmail:",
    "harita": "bingmaps:", "haritalar": "bingmaps:",
    "mağaza": "ms-windows-store:", "microsoft store": "ms-windows-store:",
    "saat": "ms-clock:", "alarm": "ms-clock:",
    # Yaygın 3. parti uygulamalar (PATH / App Paths üzerinden)
    "chrome": "chrome", "google chrome": "chrome",
    "edge": "msedge", "microsoft edge": "msedge",
    "firefox": "firefox", "mozilla firefox": "firefox",
    "opera": "opera", "brave": "brave",
    "word": "winword", "microsoft word": "winword",
    "excel": "excel", "microsoft excel": "excel",
    "powerpoint": "powerpnt", "sunum": "powerpnt",
    "outlook": "outlook",
    "spotify": "spotify",
    "discord": "discord",
    "telegram": "telegram", "telegram desktop": "telegram",
    "whatsapp": "whatsapp",
    "steam": "steam",
    "epic games": "com.epicgames.launcher:",
    "vlc": "vlc", "vlc media player": "vlc",
    "obs": "obs64", "obs studio": "obs64",
    "zoom": "zoom",
    "vscode": "code", "visual studio code": "code", "vs code": "code",
    "photoshop": "photoshop",
}

# Windows Ayarlar alt sayfaları
SETTINGS_PAGES = {
    "wifi ayarları": "ms-settings:network-wifi",
    "wi-fi ayarları": "ms-settings:network-wifi",
    "ağ ayarları": "ms-settings:network-status",
    "bluetooth ayarları": "ms-settings:bluetooth",
    "ses ayarları": "ms-settings:sound",
    "ekran ayarları": "ms-settings:display",
    "gece ışığı": "ms-settings:nightlight",
    "güç ayarları": "ms-settings:powersleep",
    "pil ayarları": "ms-settings:batterysaver",
    "güncelleme ayarları": "ms-settings:windowsupdate",
    "windows güncelleme": "ms-settings:windowsupdate",
    "uygulamalar ayarları": "ms-settings:appsfeatures",
    "gizlilik ayarları": "ms-settings:privacy",
    "kişiselleştirme": "ms-settings:personalization",
    "arka plan ayarları": "ms-settings:personalization-background",
    "tema ayarları": "ms-settings:themes",
    "dil ayarları": "ms-settings:regionlanguage",
    "tarih saat ayarları": "ms-settings:dateandtime",
    "depolama ayarları": "ms-settings:storagesense",
    "bluetooth": "ms-settings:bluetooth",
}

# Sanal tuş kodları (ses kontrolü için)
_VK_VOLUME_MUTE = 0xAD
_VK_VOLUME_DOWN = 0xAE
_VK_VOLUME_UP = 0xAF

# "Aç / başlat / çalıştır" fiilinin Türkçe çekimleri (soru kalıpları dahil).
# Sadece bu tokenlar "açma niyeti" sayılır — 'açıklama', 'açlık' gibi kelimeler tetiklemez.
OPEN_VERB_TOKENS = {
    "aç", "ac", "açar", "acar", "açsana", "açsan", "açver", "açıver", "açarmısın",
    "açabilir", "açabilirmisin", "açabilirmisiniz", "açarmisin", "acsana",
    "başlat", "baslat", "başlatır", "baslatir", "başlatsana", "başlatabilir",
    "başlatabilirmisin", "çalıştır", "calistir", "çalistir", "çalıştırır",
    "çalıştırsana", "çalıştırabilir", "çalıştırabilirmisin", "run", "open", "getir",
}

# Hedef adını yalnız bırakmak için atılacak dolgu kelimeleri
_OPEN_FILLERS = {
    "bana", "bir", "birini", "lütfen", "lutfen", "rica", "ederim", "misin", "mısın",
    "musun", "müsün", "mi", "mı", "mu", "mü", "yeni", "hemen", "acaba", "şu", "bu",
    "artık", "hadi", "haydi", "bakalım", "programını", "programi", "programı",
    "program", "uygulamasını", "uygulamayı", "uygulama", "uygulamasi", "uygulamasını",
    "aç", "ac", "açar", "başlat", "baslat", "çalıştır", "calistir",
}

# Program adı olarak kabul edilmeyecek genel kelimeler ("kapıyı aç" vb.)
_NOT_APP_WORDS = {
    "kapak", "cevap", "konu", "video", "kapı", "kapıyı", "pencere", "pencereyi",
    "gözünü", "gözlerini", "gözlerimi", "ağzını", "yol", "yolu", "defter",
    "sayfa", "sayfayı", "dosya", "dosyayı", "hesabı", "hesabımı", "kutuyu",
    "çekmeceyi", "musluğu", "ışığı", "radyoyu",
}


class SystemTools:
    """Bilgisayar donanım ve işletim sistemi kontrol yöneticisi."""

    # ─────────────────────────────────────────
    # BİLGİ: Saat / Tarih / Sistem Durumu
    # ─────────────────────────────────────────

    @staticmethod
    def get_system_summary() -> str:
        """Bilgisayarın donanım ve durum özetini çıkarır."""
        os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
        arch = platform.architecture()[0]
        processor = platform.processor() or "Bilinmiyor"
        hostname = platform.node()

        try:
            total, used, free = shutil.disk_usage("C:\\")
            total_gb = total // (2 ** 30)
            free_gb = free // (2 ** 30)
            disk_info = f"{total_gb} GB Toplam | {free_gb} GB Boş (%{(free / total) * 100:.0f} boş)"
        except Exception:
            disk_info = "Alınamadı"

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        return (
            f"💻 **Bilgisayar Sistem Durumu**\n\n"
            f"• **Cihaz Adı:** `{hostname}`\n"
            f"• **İşletim Sistemi:** `{os_info}` ({arch})\n"
            f"• **İşlemci Mimarisi:** `{processor}`\n"
            f"• **C: Diski Durumu:** `{disk_info}`\n"
            f"• **Sistem Zamanı:** `{now_str}`"
        )

    @staticmethod
    def get_current_time_date() -> str:
        """Güncel tarih ve saati Türkçe olarak döndürür."""
        now = datetime.now()
        gunler = {
            0: "Pazartesi", 1: "Salı", 2: "Çarşamba",
            3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar",
        }
        gun_adi = gunler.get(now.weekday(), "")
        return (
            f"🕒 Şu an saat **{now.strftime('%H:%M')}**, "
            f"tarih **{now.strftime('%d.%m.%Y')} ({gun_adi})**."
        )

    # ─────────────────────────────────────────
    # PROGRAM AÇMA (herhangi bir uygulama)
    # ─────────────────────────────────────────

    @staticmethod
    def _launch(target: str) -> bool:
        """Bir komutu / URI'yi / .lnk yolunu başlatmayı dener. Başarılıysa True."""
        # URI şeması (ms-settings:, microsoft.windows.camera: ...)
        if target.endswith(":") or "://" in target or target.startswith("ms-"):
            try:
                os.startfile(target)  # type: ignore[attr-defined]
                return True
            except Exception:
                try:
                    subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
                    return True
                except Exception:
                    return False

        # Doğrudan çalıştırılabilir dosya yolu
        if os.path.isfile(target):
            try:
                os.startfile(target)  # type: ignore[attr-defined]
                return True
            except Exception:
                return False

        # PATH veya "App Paths" üzerinden ("start" kabuğu her ikisini de çözer)
        try:
            subprocess.Popen(f'start "" "{target}"', shell=True)
            return True
        except Exception:
            pass

        # Son çare: doğrudan Popen
        try:
            subprocess.Popen([target])
            return True
        except Exception:
            return False

    @classmethod
    def _find_start_menu_shortcut(cls, name: str) -> Optional[str]:
        """Başlat Menüsü .lnk kısayollarında isme göre arama yapar."""
        roots = [
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        ]
        name_l = name.lower().strip()
        best = None
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for path in glob.glob(os.path.join(root, "**", "*.lnk"), recursive=True):
                stem = os.path.splitext(os.path.basename(path))[0].lower()
                if stem == name_l:
                    return path
                if best is None and name_l in stem:
                    best = path
        return best

    @classmethod
    def open_program(cls, raw_name: str) -> str:
        """Kullanıcının istediği uygulamayı adından bulup açar."""
        name = raw_name.strip().strip("'\"").strip()
        if not name:
            return "⚠️ Hangi programı açayım? Lütfen bir uygulama adı belirt."

        key = clean_text(name)

        # 1. Ayarlar alt sayfaları
        for phrase, uri in SETTINGS_PAGES.items():
            if phrase in key:
                if cls._launch(uri):
                    return f"⚙️ **{phrase.title()}** açıldı."

        # 2. Bilinen uygulama takma adları
        for alias, cmd in KNOWN_APPS.items():
            if alias in key:
                if cls._launch(cmd):
                    return f"🚀 **{alias.title()}** açılıyor..."

        # 3. Başlat Menüsü kısayolu araması
        shortcut = cls._find_start_menu_shortcut(name)
        if shortcut:
            if cls._launch(shortcut):
                found = os.path.splitext(os.path.basename(shortcut))[0]
                return f"🚀 **{found}** açılıyor..."

        # 4. Ham deneme (kullanıcı doğrudan exe adı yazmış olabilir)
        candidate = name.split()[-1]
        if cls._launch(name) or cls._launch(candidate):
            return f"🚀 **{name}** başlatılmaya çalışılıyor..."

        return (
            f"⚠️ '{name}' adlı programı bulamadım. "
            f"Adını tam yazmayı dene (örn. 'spotify', 'word', 'chrome') "
            f"ya da 'ayarlar', 'kamera', 'hesap makinesi' gibi bir uygulama söyle."
        )

    # ─────────────────────────────────────────
    # DOSYA / KLASÖR İŞLEMLERİ
    # ─────────────────────────────────────────

    @classmethod
    def open_folder(cls, key: str) -> Optional[str]:
        """Bilinen bir klasörü ya da verilen tam yolu Dosya Gezgini'nde açar."""
        # Tam yol verilmişse
        path_match = None
        for token in key.replace("\\", "/").split():
            if ":" in token or token.startswith("/"):
                path_match = token.replace("/", "\\")
                break
        if path_match and os.path.isdir(path_match):
            os.startfile(path_match)  # type: ignore[attr-defined]
            return f"📁 `{path_match}` klasörü açıldı."

        for alias, folder in KNOWN_FOLDERS.items():
            if alias in key:
                if os.path.isdir(folder):
                    os.startfile(folder)  # type: ignore[attr-defined]
                    return f"📁 **{alias.title()}** klasörü açıldı."
                return f"⚠️ **{alias.title()}** klasörü bulunamadı ({folder})."
        return None

    @classmethod
    def _resolve_base_dir(cls, key: str) -> str:
        """Metinde geçen hedef klasörü (masaüstü, indirilenler...) çözer, yoksa Masaüstü."""
        for alias, folder in KNOWN_FOLDERS.items():
            if alias in key and os.path.isdir(folder):
                return folder
        return KNOWN_FOLDERS["masaüstü"]

    # Dosya/klasör adı çıkarımında atılacak konum + dolgu kelimeleri
    _CREATE_NOISE = {
        "masaüstünde", "masaüstüne", "masaüstü", "masaustunde", "masaustu", "desktop",
        "indirilenlerde", "indirilenler", "indirilenlere", "downloads",
        "belgelerde", "belgeler", "belgelere", "documents", "dokümanlar", "dokumanlar",
        "resimlerde", "resimler", "resimlere", "müzikte", "müzik", "videolarda", "videolar",
        "yeni", "bir", "adında", "adinda", "isimli", "adlı", "adli", "klasör", "klasor",
        "klasörü", "klasoru", "klasörünü", "klasorunu", "dizin", "dizini", "dosya",
        "dosyası", "dosyasını", "belge", "oluştur", "olustur", "yap", "aç", "ac", "lütfen",
        "lutfen", "içine", "içinde", "içinede",
    }

    @classmethod
    def create_item(cls, key: str, original: str) -> Optional[str]:
        """'masaüstünde rapor klasörü oluştur' / 'belgelerde notlar.txt oluştur' gibi istekler."""
        base = cls._resolve_base_dir(key)

        word = r"[A-Za-zÇĞİÖŞÜçğıöşü0-9_\-]+"
        name = None

        # 1. Tırnak içindeki ad
        m = re.search(r'"([^"]+)"|\'([^\']+)\'', original)
        if m:
            name = m.group(1) or m.group(2)

        is_folder = any(w in key for w in ["klasör", "klasor", "dizin", "folder"])
        is_file = (not is_folder) and any(
            w in key for w in ["dosya", "dosyası", "belge", ".txt", ".md"]
        )

        # 2. Uzantılı dosya adı (rapor.txt)
        if not name:
            m3 = re.search(rf'({word}\.[A-Za-z0-9]{{1,5}})\b', original)
            if m3:
                name = m3.group(1)
                is_file, is_folder = True, False

        # 3. "X adında / isimli / adlı ..."
        if not name:
            m2 = re.search(rf'({word}(?:\s+{word})?)\s+(?:adında|adinda|isimli|adlı|adli)', original)
            if m2:
                name = m2.group(1)

        # 4. "... <konum> <ad> klasör/dosya ..."
        if not name:
            m4 = re.search(
                rf'({word}(?:\s+{word}){{0,2}})\s+'
                rf'(?:klasör|klasor|klasörü|klasoru|klasörünü|dizin|dosya|dosyası|dosyasını)',
                original,
            )
            if m4:
                name = m4.group(1)

        # Gürültü (konum/dolgu) kelimelerini at
        if name:
            toks = [t for t in re.split(r"\s+", name.strip()) if t.lower() not in cls._CREATE_NOISE]
            name = " ".join(toks).strip().strip(".").strip()

        if not name:
            return ("⚠️ Oluşturulacak dosya/klasör adını anlayamadım. "
                    "Örn: masaüstünde \"Projeler\" klasörü oluştur")

        target = os.path.join(base, name)

        try:
            if is_folder or (not is_file):
                os.makedirs(target, exist_ok=True)
                return f"📁 **{name}** klasörü oluşturuldu:\n`{target}`"
            else:
                if not os.path.exists(target):
                    open(target, "w", encoding="utf-8").close()
                return f"📄 **{name}** dosyası oluşturuldu:\n`{target}`"
        except Exception as e:
            return f"⚠️ Oluşturulamadı: {e}"

    @classmethod
    def search_files(cls, key: str, original: str) -> Optional[str]:
        """Kullanıcı profilindeki yaygın klasörlerde dosya adına göre arama yapar."""
        import re
        m = re.search(r'"([^"]+)"|\'([^\']+)\'', original)
        term = (m.group(1) or m.group(2)) if m else None
        if not term:
            m2 = re.search(
                r'([A-Za-zÇĞİÖŞÜçğıöşü0-9_\-\.]{2,40})\s+(?:dosya|dosyası|dosyasını|belge)',
                original,
            )
            if m2:
                term = m2.group(1)
        if not term:
            return ("⚠️ Ne aramamı istediğini yazamadım. "
                    "Örn: masaüstünde \"ödev\" dosyasını bul")

        term = term.strip().lower()
        search_dirs = [
            KNOWN_FOLDERS["masaüstü"], KNOWN_FOLDERS["belgeler"],
            KNOWN_FOLDERS["indirilenler"], KNOWN_FOLDERS["resimler"],
        ]
        # Metinde belirli bir klasör geçiyorsa yalnızca orada ara
        for alias, folder in KNOWN_FOLDERS.items():
            if alias in key and os.path.isdir(folder):
                search_dirs = [folder]
                break

        hits = []
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            for path in glob.glob(os.path.join(d, "**", "*"), recursive=True):
                if term in os.path.basename(path).lower():
                    hits.append(path)
                if len(hits) >= 15:
                    break
            if len(hits) >= 15:
                break

        if not hits:
            return f"🔍 '{term}' ile eşleşen bir dosya/klasör bulamadım."

        listed = "\n".join(f"• `{h}`" for h in hits[:10])
        extra = f"\n… ve {len(hits) - 10} tane daha" if len(hits) > 10 else ""
        return f"🔍 '{term}' için **{len(hits)}** sonuç:\n{listed}{extra}"

    # ─────────────────────────────────────────
    # SİSTEM KONTROLÜ (ses, parlaklık, kilit, uyku, ekran görüntüsü)
    # ─────────────────────────────────────────

    @staticmethod
    def _press_vk(vk: int, times: int = 1) -> None:
        for _ in range(times):
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
            time.sleep(0.01)

    @classmethod
    def control_volume(cls, key: str) -> Optional[str]:
        try:
            if any(w in key for w in ["sustur", "sesi kapat", "ses kapat", "mute", "sessize"]):
                cls._press_vk(_VK_VOLUME_MUTE)
                return "🔇 Ses susturuldu (tekrar açmak için 'sesi aç' de)."
            if any(w in key for w in ["sesi aç", "ses aç", "sesi yükselt", "ses yükselt",
                                      "sesi artır", "ses artır", "sesi arttır"]):
                cls._press_vk(_VK_VOLUME_UP, 5)
                return "🔊 Ses yükseltildi."
            if any(w in key for w in ["sesi kıs", "ses kıs", "sesi azalt", "ses azalt",
                                      "sesi düşür", "ses düşür", "sesi alçalt"]):
                cls._press_vk(_VK_VOLUME_DOWN, 5)
                return "🔉 Ses kısıldı."
        except Exception as e:
            return f"⚠️ Ses kontrolü başarısız: {e}"
        return None

    @classmethod
    def control_brightness(cls, key: str) -> Optional[str]:
        if "parlakl" not in key and "brightness" not in key:
            return None
        import re
        level = None
        m = re.search(r"%?\s*(\d{1,3})\s*%?", key)
        if m:
            level = max(0, min(100, int(m.group(1))))
        elif any(w in key for w in ["artır", "arttır", "yükselt", "aç"]):
            level = 90
        elif any(w in key for w in ["azalt", "düşür", "kıs"]):
            level = 30
        if level is None:
            return "⚠️ Parlaklığı kaça ayarlayayım? Örn: parlaklığı %60 yap"
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                 f".WmiSetBrightness(1,{level})"],
                capture_output=True, timeout=10,
            )
            return f"☀️ Ekran parlaklığı %{level} olarak ayarlandı."
        except Exception as e:
            return f"⚠️ Parlaklık ayarlanamadı (dizüstü değilse desteklenmez): {e}"

    @classmethod
    def lock_or_sleep(cls, key: str) -> Optional[str]:
        try:
            if any(w in key for w in ["ekranı kilitle", "bilgisayarı kilitle", "kilitle"]):
                ctypes.windll.user32.LockWorkStation()
                return "🔒 Ekran kilitlendi."
            if any(w in key for w in ["uyku moduna al", "uyku moduna geç", "uykuya al",
                                      "bilgisayarı uyut", "uyut"]):
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
                return "😴 Bilgisayar uyku moduna alınıyor..."
            if any(w in key for w in ["ekranı kapat", "monitörü kapat"]):
                subprocess.Popen(
                    'powershell -NoProfile -Command "(Add-Type -MemberDefinition '
                    "'[DllImport(\\\"user32.dll\\\")]public static extern int "
                    "SendMessage(int hWnd,int hMsg,int wParam,int lParam);' -Name a -Pass)"
                    '::SendMessage(-1,0x0112,0xF170,2)"',
                    shell=True,
                )
                return "🌑 Ekran kapatıldı (hareket ettirince açılır)."
        except Exception as e:
            return f"⚠️ İşlem başarısız: {e}"
        return None

    @staticmethod
    def take_screenshot() -> str:
        try:
            from PIL import ImageGrab
        except Exception:
            return "⚠️ Ekran görüntüsü için Pillow kütüphanesi gerekli (pip install Pillow)."
        try:
            img = ImageGrab.grab()
            fname = f"MehburAI_ekran_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = os.path.join(KNOWN_FOLDERS["masaüstü"], fname)
            img.save(path)
            return f"📸 Ekran görüntüsü kaydedildi:\n`{path}`"
        except Exception as e:
            return f"⚠️ Ekran görüntüsü alınamadı: {e}"

    # ─────────────────────────────────────────
    # GÜÇ KOMUTLARI (gecikmeli + iptal edilebilir)
    # ─────────────────────────────────────────

    _SHUTDOWN_DELAY = 45  # saniye

    @classmethod
    def power_command(cls, key: str) -> Optional[str]:
        try:
            if any(w in key for w in ["iptal et", "vazgeç", "kapatmayı iptal",
                                      "yeniden başlatmayı iptal", "shutdown iptal"]):
                subprocess.run(["shutdown", "/a"], capture_output=True)
                return "✅ Planlanmış kapatma/yeniden başlatma iptal edildi."

            if any(w in key for w in ["yeniden başlat", "yeniden baslat", "restart", "reboot"]):
                subprocess.run(["shutdown", "/r", "/t", str(cls._SHUTDOWN_DELAY)], capture_output=True)
                return (f"🔄 Bilgisayar **{cls._SHUTDOWN_DELAY} saniye** içinde yeniden başlatılacak.\n"
                        f"Vazgeçmek için **'iptal et'** yaz.")

            if any(w in key for w in ["bilgisayarı kapat", "bilgisayari kapat", "sistemi kapat",
                                      "pc'yi kapat", "shutdown", "kapat bilgisayarı"]):
                subprocess.run(["shutdown", "/s", "/t", str(cls._SHUTDOWN_DELAY)], capture_output=True)
                return (f"⚠️ Bilgisayar **{cls._SHUTDOWN_DELAY} saniye** içinde kapanacak.\n"
                        f"Vazgeçmek için hemen **'iptal et'** yaz.")

            if any(w in key for w in ["oturumu kapat", "çıkış yap", "logout", "oturum kapat"]):
                subprocess.run(["shutdown", "/l"], capture_output=True)
                return "👋 Oturum kapatılıyor..."
        except Exception as e:
            return f"⚠️ Güç komutu başarısız: {e}"
        return None

    # ─────────────────────────────────────────
    # ANA YÖNLENDİRİCİ
    # ─────────────────────────────────────────

    @classmethod
    def handle_system_query(cls, query: str) -> Optional[str]:
        """
        Kullanıcı girdisinin bir bilgisayar/sistem komutu olup olmadığını kontrol eder.
        Sistem isteğiyse yanıt üretir; değilse None döner (AIEngine online/offline moda geçer).
        """
        cleaned = clean_text(query)

        # 1. Saat / Tarih
        if any(w in cleaned for w in ["saat kaç", "saat kac", "saat kacta", "tarih ne",
                                      "tarih nedir", "bugün günlerden ne", "gunlerden ne",
                                      "bugün ayın kaçı", "bugun ayin kaci", "hangi gün",
                                      "günün tarihi"]):
            return cls.get_current_time_date()

        # 2. Sistem / Donanım Durumu
        if any(w in cleaned for w in ["sistem bilgisi", "sistem durumu", "bilgisayar durumu",
                                      "bilgisayarımın durumu", "bilgisayarimin durumu",
                                      "bilgisayar özellikleri", "bilgisayar ozellikleri",
                                      "donanım bilgisi", "donanim bilgisi", "disk alanı",
                                      "disk alani", "disk durumu", "bilgisayar hakkında bilgi",
                                      "işletim sistemi ne", "ram durumu"]):
            return cls.get_system_summary()

        # 3. Güç komutları (en spesifik → önce)
        if any(w in cleaned for w in ["kapat", "yeniden başlat", "yeniden baslat", "restart",
                                      "reboot", "shutdown", "oturumu kapat", "çıkış yap",
                                      "iptal et", "vazgeç"]):
            power = cls.power_command(cleaned)
            if power:
                return power

        # 4. Ekran görüntüsü
        if any(w in cleaned for w in ["ekran görüntüsü", "ekran goruntusu", "screenshot",
                                      "ekranın fotoğrafı", "ekran resmi", "ss al"]):
            return cls.take_screenshot()

        # 5. Sistem kontrolü: ses
        if "ses" in cleaned or "sustur" in cleaned or "mute" in cleaned:
            vol = cls.control_volume(cleaned)
            if vol:
                return vol

        # 6. Sistem kontrolü: parlaklık
        bright = cls.control_brightness(cleaned)
        if bright:
            return bright

        # 7. Sistem kontrolü: kilit / uyku / ekranı kapat
        if any(w in cleaned for w in ["kilitle", "uyku", "uyut", "ekranı kapat", "monitörü kapat"]):
            ls = cls.lock_or_sleep(cleaned)
            if ls:
                return ls

        # 8. Dosya/klasör oluşturma
        if (any(w in cleaned for w in ["oluştur", "olustur", "yeni klasör", "yeni dosya",
                                       "klasör aç", "klasor ac"])
                and any(w in cleaned for w in ["klasör", "klasor", "dosya", "dizin",
                                               ".txt", ".md", "belge"])):
            created = cls.create_item(cleaned, query)
            if created:
                return created

        # 9. Dosya arama
        if (any(w in cleaned for w in ["bul", "ara", "arıyorum", "nerede"])
                and any(w in cleaned for w in ["dosya", "dosyası", "dosyasını", "belge", "klasör"])):
            found = cls.search_files(cleaned, query)
            if found:
                return found

        # 10. Klasör açma
        if any(w in cleaned for w in ["klasörünü aç", "klasörü aç", "klasoru ac", "klasor ac",
                                      "dizinini aç", "aç masaüstü", "masaüstünü aç",
                                      "indirilenleri aç", "belgeleri aç", "resimleri aç"]) or \
           (("aç" in cleaned or "ac " in cleaned or "göster" in cleaned)
                and any(a in cleaned for a in KNOWN_FOLDERS)):
            folder = cls.open_folder(cleaned)
            if folder:
                return folder

        # 11. Program açma  ("... aç", "... açar mısın", "başlatır mısın" vb.)
        tokens = cleaned.split()
        has_open_verb = any(t in OPEN_VERB_TOKENS for t in tokens)
        explicit_open = any(p in cleaned for p in [
            "programını aç", "programı aç", "uygulamasını aç", "uygulamayı aç",
            "programını açar", "uygulamasını açar", "programını başlat",
        ])
        settings_hit = any(phrase in cleaned for phrase in SETTINGS_PAGES)
        app_hit = any(alias in cleaned for alias in KNOWN_APPS)

        if has_open_verb or explicit_open:
            if settings_hit:
                return cls.open_program(cleaned)
            if app_hit:
                return cls.open_program(cleaned)

            # Fiil + dolgu kelimelerini atıp hedef program adını izole et
            target = " ".join(
                t for t in tokens
                if t not in OPEN_VERB_TOKENS and t not in _OPEN_FILLERS
            ).strip()

            if has_open_verb or explicit_open:
                # Yazım hatası toleranslı eşleşme ("hesap makimesini" -> "hesap makinesi")
                fuzzy = cls._fuzzy_app(target)
                if fuzzy:
                    return cls.open_program(fuzzy)
                # Bilinmeyen ama açıkça istenmiş bir uygulama adı
                if target and len(target) >= 2 and target not in _NOT_APP_WORDS \
                        and not any(w in _NOT_APP_WORDS for w in target.split()):
                    return cls.open_program(target)

        return None

    @staticmethod
    def _fuzzy_app(target: str) -> Optional[str]:
        """Verilen hedefi KNOWN_APPS takma adlarıyla yazım hatası toleranslı eşleştirir."""
        target = target.strip()
        if len(target) < 3:
            return None
        aliases = list(KNOWN_APPS.keys())
        close = difflib.get_close_matches(target, aliases, n=1, cutoff=0.72)
        if close:
            return close[0]
        best, best_ratio = None, 0.0
        for alias in aliases:
            ratio = difflib.SequenceMatcher(None, target, alias).ratio()
            if ratio > best_ratio:
                best, best_ratio = alias, ratio
        return best if best_ratio >= 0.72 else None

    # Geriye dönük uyumluluk (eski kod `open_app` çağırıyor olabilir)
    @classmethod
    def open_app(cls, app_name: str) -> str:
        return cls.open_program(app_name)


# ─────────────────────────────────────────────
# Bağımsız Test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import io
    import sys

    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("=" * 60)
    print("  MehburAI - Bilgisayar & Sistem Araçları Testi")
    print("=" * 60)

    tests = [
        "saat kaç",
        "sistem bilgisi",
        "not defteri aç",
        "parlaklığı %50 yap",
        "masaüstünü aç",
        'masaüstünde "MehburTest" klasörü oluştur',
        "sesi kıs",
    ]
    for t in tests:
        print(f"\n💬 {t}")
        print(f"   → {SystemTools.handle_system_query(t)}")
