@echo off
title MehburAI - Hibrit Akilli Asistan
cd /d "%~dp0"
python run_mehbur.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bir hata olustu. Cikmak icin bir tusa basin...
    pause >nul
)
