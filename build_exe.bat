@echo off
chcp 65001 >nul
title MehburAI - .exe ve Setup Paketleyici
color 0B

echo.
echo  =============================================================
echo     [*] MEHBUR AI - .EXE + SETUP PAKETLEYICI (PyInstaller) [*]
echo  =============================================================
echo.

cd /d "%~dp0"

echo  [1/6] PyInstaller kontrol ediliyor / kuruluyor...
python -m pip install --quiet pyinstaller
if %ERRORLEVEL% NEQ 0 (
    echo  [HATA] PyInstaller kurulamadi.
    pause
    exit /b 1
)

echo.
echo  [2/6] Kaynak kodda hassas bilgi taramasi (API anahtari / bot token / Telegram ID)...
python scan_secrets.py
if %ERRORLEVEL% NEQ 0 (
    echo  [DURDU] Kaynakta hassas bilgi var - derleme yapilmadi.
    pause
    exit /b 1
)

echo.
echo  [3/6] MehburAI.exe derleniyor (dist\MehburAI\MehburAI.exe)...
python -m PyInstaller MehburAI.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo  [HATA] Derleme basarisiz oldu.
    pause
    exit /b 1
)

echo.
echo  [4/6] Derlenmis paket taraniyor (dosyalar + .exe'nin ici)...
python scan_secrets.py --dist dist\MehburAI
if %ERRORLEVEL% NEQ 0 (
    echo  [DURDU] Pakette hassas bilgi var.
    pause
    exit /b 1
)
python scan_secrets.py --pyz build\MehburAI\PYZ-00.pyz
if %ERRORLEVEL% NEQ 0 (
    echo  [DURDU] .exe'nin icindeki kodda hassas bilgi var.
    pause
    exit /b 1
)

echo.
echo  [5/6] Kurulum arsivi (payload.zip) hazirlaniyor ve taraniyor...
python -c "import os,shutil; os.path.exists('build/payload.zip') and os.remove('build/payload.zip'); shutil.make_archive('build/payload', 'zip', 'dist/MehburAI')"
if %ERRORLEVEL% NEQ 0 (
    echo  [HATA] Paket arsivi olusturulamadi.
    pause
    exit /b 1
)
python scan_secrets.py --zip build\payload.zip
if %ERRORLEVEL% NEQ 0 (
    echo  [DURDU] Kurulum arsivinde hassas bilgi var.
    pause
    exit /b 1
)

echo.
echo  [6/6] MehburAI.Setup.exe olusturuluyor (dist\MehburAI.Setup.exe)...
python -m PyInstaller installer.py --noconfirm --onefile --windowed --name MehburAI.Setup ^
    --icon "%CD%\assets\logo.ico" --add-data "%CD%\assets\logo.ico;." ^
    --distpath dist --workpath build\setup --specpath build
if %ERRORLEVEL% NEQ 0 (
    echo  [HATA] Setup derlenemedi.
    pause
    exit /b 1
)

echo.
echo  [6b/6] GitHub Release dosyalari hazirlaniyor (dist\MehburAI.zip = yalnizca .exe, dist\MehburAI-payload.zip = uygulama dosyalari)...
python -c "import shutil,zipfile; z=zipfile.ZipFile('dist/MehburAI.zip','w',zipfile.ZIP_DEFLATED); z.write('dist/MehburAI.Setup.exe','MehburAI.Setup.exe'); z.close(); shutil.copyfile('build/payload.zip','dist/MehburAI-payload.zip')"
if %ERRORLEVEL% NEQ 0 (
    echo  [HATA] Release dosyalari hazirlanamadi.
    pause
    exit /b 1
)
python scan_secrets.py --zip dist\MehburAI.zip
if %ERRORLEVEL% NEQ 0 (
    echo  [DURDU] MehburAI.zip icinde hassas bilgi var.
    pause
    exit /b 1
)

echo.
echo  =============================================================
echo   [OK] Kurulum dosyasi: dist\MehburAI.Setup.exe  (kucuk, cevrimici kurucu)
echo   GitHub Release'e yuklenecekler: dist\MehburAI.zip ve dist\MehburAI-payload.zip
echo   Setup calisinca payload'i GitHub'dan indirip %%APPDATA%%\MehburAI
echo   altina kurar, masaustune kisayol koyar ve baslatir.
echo   Icinde API anahtari / bot token / Telegram ID YOKTUR.
echo  =============================================================
pause
