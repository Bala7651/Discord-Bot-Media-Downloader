@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Pack release ZIP

set "OUT=%~dp0_release"
set "NAME=Discord-Bot-Media-Downloader"
set "ZIP=%~dp0Discord-Bot-Media-Downloader-portable.zip"

echo Creating clean folder (no .venv / .git)...
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%\%NAME%"

copy /Y "gui.py" "%OUT%\%NAME%\" >nul
copy /Y "backup.py" "%OUT%\%NAME%\" >nul
copy /Y "core.py" "%OUT%\%NAME%\" >nul
copy /Y "bot_store.py" "%OUT%\%NAME%\" >nul
copy /Y "settings_store.py" "%OUT%\%NAME%\" >nul
copy /Y "i18n.py" "%OUT%\%NAME%\" >nul
copy /Y "requirements.txt" "%OUT%\%NAME%\" >nul
copy /Y "run_gui.bat" "%OUT%\%NAME%\" >nul
copy /Y "pack_release.bat" "%OUT%\%NAME%\" >nul
copy /Y "README.md" "%OUT%\%NAME%\" >nul
copy /Y "LICENSE" "%OUT%\%NAME%\" >nul
copy /Y "SECURITY.md" "%OUT%\%NAME%\" >nul
copy /Y "CONTRIBUTING.md" "%OUT%\%NAME%\" >nul
copy /Y ".gitignore" "%OUT%\%NAME%\" >nul
if exist "????_?????.md" copy /Y "????_?????.md" "%OUT%\%NAME%\" >nul

echo Compressing...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%OUT%\%NAME%' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 (
  echo ERROR compress failed
  if /I "%~1"=="--no-pause" exit /b 1
  pause
  exit /b 1
)

rmdir /s /q "%OUT%"
echo.
echo DONE: %ZIP%
echo Unzip and run run_gui.bat
if /I "%~1"=="--no-pause" exit /b 0
pause
exit /b 0