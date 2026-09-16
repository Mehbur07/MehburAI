# -*- mode: python ; coding: utf-8 -*-

import os

# vosk yükler kendi native DLL'lerini (libvosk.dll vb.) çalışma zamanında
# cffi.dlopen() ile elle açıyor; PyInstaller'ın statik analizi bunu göremez,
# bu yüzden vosk paket klasöründeki DLL'leri elle binaries'e eklemek gerekiyor
# (aksi halde derlenmiş .exe'de "Eksik kütüphane: vosk" hatası çıkar).
vosk_binaries = []
try:
    import vosk
    vosk_dir = os.path.dirname(vosk.__file__)
    for fname in ('libvosk.dll', 'libgcc_s_seh-1.dll', 'libstdc++-6.dll', 'libwinpthread-1.dll'):
        fpath = os.path.join(vosk_dir, fname)
        if os.path.exists(fpath):
            vosk_binaries.append((fpath, 'vosk'))
except Exception:
    pass

a = Analysis(
    ['run_mehbur.py'],
    pathex=[],
    binaries=vosk_binaries,
    datas=[('assets', 'assets')],
    hiddenimports=['vosk.vosk_cffi'],
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
