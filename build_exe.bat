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
echo  [3/3] Bilgisayara kuruluyor: %%LOCALAPPDATA%%\Programs\MehburAI ...
set "DEST=%LOCALAPPDATA%\Programs\MehburAI"
if exist "%DEST%" rmdir /s /q "%DEST%"
mkdir "%DEST%"
robocopy "dist\MehburAI" "%DEST%" /E /NFL /NDL /NJH /NJS >nul
if not exist "%DEST%\data" mkdir "%DEST%\data"
if exist "data\config.json" copy /y "data\config.json" "%DEST%\data\config.json" >nul
if exist "data\mehbur_memory.db" copy /y "data\mehbur_memory.db" "%DEST%\data\mehbur_memory.db" >nul

echo.
echo  =============================================================
echo   [OK] Kurulum tamamlandi: %DEST%\MehburAI.exe
echo   Masaustu kisayolunu bu dosyaya yonlendirmeyi unutma
echo   (ya da MehburAI.lnk'yi bu betiği calistiran Claude güncelledi).
echo  =============================================================
pause
