@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title Discord Channel Backup - 啟動中

echo.
echo  ============================================
echo    Discord 頻道備份工具
echo    Discord Channel Backup
echo  ============================================
echo.
echo  資料夾: %CD%
echo.

set "LOG=%~dp0launch.log"
echo ==== %DATE% %TIME% ==== > "%LOG%"

REM ---- 尋找 Python（避免 Windows Store 假 python）----
set "PY="
set "PY_ARGS="

if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PY=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PY=%LocalAppData%\Programs\Python\Python311\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PY=%LocalAppData%\Programs\Python\Python310\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Launcher\py.exe" (
  set "PY=%LocalAppData%\Programs\Python\Launcher\py.exe"
  set "PY_ARGS=-3"
)
if not defined PY if exist "C:\Program Files\Python313\python.exe" set "PY=C:\Program Files\Python313\python.exe"
if not defined PY if exist "C:\Program Files\Python312\python.exe" set "PY=C:\Program Files\Python312\python.exe"

if not defined PY (
  where py >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%I in ('where py') do (
      set "PY=%%I"
      set "PY_ARGS=-3"
      goto :have_py
    )
  )
)

if not defined PY (
  for /f "delims=" %%I in ('where python 2^>nul') do (
    echo %%I | findstr /I "WindowsApps" >nul
    if errorlevel 1 (
      set "PY=%%I"
      goto :have_py
    )
  )
)

:have_py
if not defined PY (
  echo [錯誤] 找不到 Python。
  echo.
  echo 請先安裝 Python 3.10 或更新版本：
  echo   https://www.python.org/downloads/
  echo 安裝時請勾選：Add python.exe to PATH
  echo.
  echo 詳細說明請看：使用說明_下載後請看.md
  echo.
  pause
  exit /b 1
)

echo [1/3] Python: %PY% %PY_ARGS%
echo Using: %PY% %PY_ARGS%>> "%LOG%"
"%PY%" %PY_ARGS% --version
if errorlevel 1 (
  echo [錯誤] Python 無法執行
  pause
  exit /b 1
)
echo.

if not exist "%~dp0requirements.txt" (
  echo [錯誤] 找不到 requirements.txt
  echo 請確認你是解壓縮「整個專案資料夾」後再執行本 bat。
  echo 不要只解出單一檔案。
  pause
  exit /b 1
)
if not exist "%~dp0gui.py" (
  echo [錯誤] 找不到 gui.py
  echo 請完整下載並解壓縮專案 ZIP。
  pause
  exit /b 1
)

if not exist "%~dp0.venv\Scripts\python.exe" (
  echo [2/3] 第一次使用：建立虛擬環境 .venv ...
  echo （約 10～60 秒，請稍候）
  "%PY%" %PY_ARGS% -m venv "%~dp0.venv"
  if errorlevel 1 (
    echo [錯誤] 建立 venv 失敗。請確認 Python 安裝完整。
    type "%LOG%"
    pause
    exit /b 1
  )
  echo       虛擬環境完成。
) else (
  echo [2/3] 虛擬環境已存在。
)

set "VPY=%~dp0.venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo [錯誤] 找不到 %VPY%
  pause
  exit /b 1
)

echo [2/3] 檢查 / 安裝套件...
"%VPY%" -c "import customtkinter,discord,aiohttp,tqdm" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo       正在安裝依賴（第一次可能要 1～3 分鐘，請勿關閉）...
  "%VPY%" -m pip install -U pip >> "%LOG%" 2>&1
  "%VPY%" -m pip install -r "%~dp0requirements.txt" >> "%LOG%" 2>&1
  if errorlevel 1 (
    echo [錯誤] 套件安裝失敗。請看 launch.log
    echo 常見原因：沒有網路、公司防火牆、Python 版本太舊
    type "%LOG%"
    pause
    exit /b 1
  )
  "%VPY%" -c "import customtkinter,discord,aiohttp,tqdm" >> "%LOG%" 2>&1
  if errorlevel 1 (
    echo [錯誤] 安裝後仍無法 import，請看 launch.log
    pause
    exit /b 1
  )
)
echo       套件 OK。
echo.

echo [3/3] 啟動圖形介面...
echo 若沒有跳出視窗，請不要關閉此黑窗，把錯誤訊息截圖。
echo.
"%VPY%" -u "%~dp0gui.py"
set "EC=%ERRORLEVEL%"
echo Exit %EC%>> "%LOG%"

if not "%EC%"=="0" (
  echo.
  echo [錯誤] 程式結束代碼: %EC%
  echo 紀錄: %LOG%
  pause
  exit /b %EC%
)

echo.
echo 程式已關閉。
pause
exit /b 0
