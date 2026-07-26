@echo off
setlocal
cd /d "%~dp0"
title Discord Channel Backup

echo ============================================
echo   Discord Channel Backup
echo ============================================
echo.

set "LOG=%~dp0launch.log"
echo ==== launch %DATE% %TIME% ==== > "%LOG%"

set "PY=%LocalAppData%\Programs\Python\Python313\python.exe"
if not exist "%PY%" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=%LocalAppData%\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=%LocalAppData%\Programs\Python\Launcher\py.exe"
if not exist "%PY%" (
  echo [ERROR] Python not found at expected path.
  echo Install Python 3.10+ from python.org
  echo. >> "%LOG%"
  echo Python missing >> "%LOG%"
  pause
  exit /b 1
)

echo Using: %PY%
echo Using: %PY% >> "%LOG%"
"%PY%" --version
if errorlevel 1 (
  echo [ERROR] Python failed to run
  pause
  exit /b 1
)
"%PY%" --version >> "%LOG%" 2>&1

if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv ...
  "%PY%" -m venv .venv
  if errorlevel 1 (
    echo [ERROR] venv create failed
    pause
    exit /b 1
  )
)

set "VPY=%~dp0.venv\Scripts\python.exe"
echo Venv: %VPY%
echo Venv: %VPY% >> "%LOG%"

echo Checking packages...
"%VPY%" -c "import customtkinter,discord,aiohttp,tqdm"
if errorlevel 1 (
  echo Installing packages, please wait...
  "%VPY%" -m pip install -U pip
  "%VPY%" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] pip install failed
    echo See %LOG%
    pause
    exit /b 1
  )
)

echo Starting GUI...
echo Starting GUI >> "%LOG%"
"%VPY%" -u "%~dp0gui.py"
set "EC=%ERRORLEVEL%"
echo Exit code %EC% >> "%LOG%"

if not "%EC%"=="0" (
  echo.
  echo [ERROR] Program exited with code %EC%
  echo Log: %LOG%
  pause
  exit /b %EC%
)

echo Done.
pause
exit /b 0