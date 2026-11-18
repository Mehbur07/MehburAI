@echo off
cd /d "%~dp0"
copy /y hooks\pre-commit .git\hooks\pre-commit >nul
echo Hassas bilgi kancasi (pre-commit) kuruldu.
pause
