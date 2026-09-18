@echo off
chcp 65001 >nul
title MehburAI - .exe Paketleyici
color 0B

echo.
echo  =============================================================
echo     [*] MEHBUR AI - .EXE PAKETLEYICI (PyInstaller) [*]
echo  =============================================================
echo.

cd /d "%~dp0"

echo  [1/3] PyInstaller kontrol ediliyor / kuruluyor...
python -m pip install --quiet pyinstaller
if %ERRORLEVEL% NEQ 0 (
    echo  [HATA] PyInstaller kurulamadi.
    pause
    exit /b 1
)

echo.
echo  [2/3] MehburAI.exe derleniyor (dist\MehburAI\MehburAI.exe)...
python -m PyInstaller MehburAI.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo  [HATA] Derleme basarisiz oldu.
    pause
    exit /b 1
)

echo.
echo  [3/3] MehburAI.Setup.exe olusturuluyor (dist\MehburAI.Setup.exe)...
python -c "import shutil; shutil.make_archive('build/payload', 'zip', 'dist/MehburAI')"
if %ERRORLEVEL% NEQ 0 (
    echo  [HATA] Paket arsivi olusturulamadi.
    pause
    exit /b 1
)
python -m PyInstaller installer.py --noconfirm --onefile --windowed --name MehburAI.Setup ^
    --icon "%CD%\assets\logo.ico" --add-data "%CD%\build\payload.zip;." --add-data "%CD%\assets\logo.ico;." ^
    --distpath dist --workpath build\setup --specpath build
if %ERRORLEVEL% NEQ 0 (
    echo  [HATA] Setup derlenemedi.
    pause
    exit /b 1
)

echo.
echo  =============================================================
echo   [OK] Kurulum dosyasi: dist\MehburAI.Setup.exe
echo   Calistirinca %%APPDATA%%\MehburAI altina kurar ve baslatir.
echo  =============================================================
pause
