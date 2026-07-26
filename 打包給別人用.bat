@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 打包 ZIP 給使用者下載

set "OUT=%~dp0_release"
set "NAME=Discord-Bot-Media-Downloader"
set "ZIP=%~dp0%NAME%-portable.zip"

echo 建立乾淨資料夾（不含 .venv / .git）...
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%\%NAME%"

for %%F in (
  gui.py
  backup.py
  core.py
  bot_store.py
  settings_store.py
  i18n.py
  requirements.txt
  run_gui.bat
  README.md
  LICENSE
  SECURITY.md
  CONTRIBUTING.md
  使用說明_下載後請看.md
  .gitignore
) do (
  if exist "%%F" copy /Y "%%F" "%OUT%\%NAME%\" >nul
)

echo.
echo 正在壓縮成：
echo   %ZIP%
echo.

powershell -NoProfile -Command "Compress-Archive -Path '%OUT%\%NAME%' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 (
  echo 壓縮失敗。
  pause
  exit /b 1
)

rmdir /s /q "%OUT%"
echo.
echo ============================================
echo  完成！請把這個 ZIP 給別人，或上傳到 GitHub Releases：
echo  %ZIP%
echo.
echo  別人解壓後雙擊 run_gui.bat 即可（需先裝 Python）。
echo ============================================
explorer /select,"%ZIP%"
pause
