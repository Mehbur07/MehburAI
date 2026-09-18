# -*- mode: python ; coding: utf-8 -*-

import os

# vosk kendi native DLL'lerini (libvosk.dll + MinGW çalışma zamanı) çalışma
# zamanında cffi.dlopen() ile elle açıyor; PyInstaller'ın statik analizi bunu
# göremez. Bu yüzden vosk klasöründeki TÜM DLL'ler elle 'vosk' klasörüne eklenir
# (aksi halde başka bilgisayarda "Eksik kütüphane: vosk" hatası çıkar).
vosk_files = []
try:
    import vosk
    vosk_dir = os.path.dirname(vosk.__file__)
    for fname in os.listdir(vosk_dir):
        if fname.lower().endswith('.dll'):
            vosk_files.append((os.path.join(vosk_dir, fname), 'vosk'))
except Exception:
    pass

# Türkçe ses modeli (~35 MB) pakete girer — internetsiz ilk açılışta da sesli
# sohbet çalışsın. YALNIZCA data/models paketlenir: data/config.json (API anahtarı,
# bot token, Telegram ID), *.db (sohbet geçmişi), kamera kareleri ASLA girmez.
model_datas = []
for base in (os.path.abspath('.'), os.path.join(os.environ.get('APPDATA', ''), 'MehburAI')):
    mdir = os.path.join(base, 'data', 'models', 'vosk-model-small-tr-0.3')
    if os.path.isdir(mdir):
        model_datas.append((mdir, os.path.join('data', 'models', 'vosk-model-small-tr-0.3')))
        break

a = Analysis(
    ['run_mehbur.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')] + vosk_files + model_datas,
    hiddenimports=['vosk.vosk_cffi', 'srt', 'tqdm', 'edge_tts'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MehburAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/logo.ico'],
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MehburAI',
)
