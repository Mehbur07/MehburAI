@echo off
chcp 65001 >nul
title MehburAI - Otomatik Kurulum ve Baslatici
color 0B

echo.
echo  =============================================================
echo     [*] MEHBUR AI - OTOMATIK KURULUM VE BASLATICI [*]
echo  =============================================================
echo.
echo  [1/4] Python kontrol ediliyor...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [HATA] Bilgisayarinizda Python kurulu degil veya PATH'e eklenmemis!
    echo  Lutfen https://www.python.org/downloads/ adresinden Python indirip kurun.
    echo  (Kurulum sirasinda "Add Python to PATH" kutucugunu isaretlemeyi unutmayin!)
    echo.
    pause
    exit /b 1
)
python --version
echo  [OK] Python mevcut.

echo.
echo  [2/4] Gerekli yapay zeka kutuphaneleri yukleniyor...
echo  (CustomTkinter, Google Generative AI, Pillow, Requests...)
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo  [UYARI] Pip yuklemesinde bazi uyarilar olustu, devam ediliyor...
) else (
    echo  [OK] Kutuphaneler basariyla hazirlandi.
)

echo.
echo  [3/4] Masaustune MehburAI kisayolu olusturuluyor...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$WshShell = New-Object -comObject WScript.Shell; $Desktop = [Environment]::GetFolderPath('Desktop'); $Shortcut = $WshShell.CreateShortcut(\"$Desktop\MehburAI.lnk\"); $Shortcut.TargetPath = 'python.exe'; $Shortcut.Arguments = '\"%~dp0run_mehbur.py\"'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Description = 'MehburAI - Hibrit Akilli Asistan'; $Shortcut.Save();"
echo  [OK] Masaustu kisayolu olusturuldu: MehburAI.lnk

echo.
echo  [4/4] MehburAI baslatiliyor...
echo  =============================================================
echo.

cd /d "%~dp0"
python run_mehbur.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [BILGI] Program kapandi veya bir hata olustu.
    pause
)
