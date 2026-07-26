@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
title Discord Channel Backup

echo.
echo  ============================================
echo    Discord Bot Media Downloader
echo  ============================================
echo.
echo  Folder: %CD%
echo.

set "LOG=%~dp0launch.log"
echo ==== %DATE% %TIME% ==== > "%LOG%"

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
      goto have_py
    )
  )
)

if not defined PY (
  for /f "delims=" %%I in ('where python 2^>nul') do (
    echo %%I | findstr /I "WindowsApps" >nul
    if errorlevel 1 (
      set "PY=%%I"
      goto have_py
    )
  )
)

:have_py
if not defined PY (
  echo [ERROR] Python not found.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  echo Check "Add python.exe to PATH" during setup.
  echo.
  pause
  exit /b 1
)

echo [1/3] Python: %PY% %PY_ARGS%
echo Using: %PY% %PY_ARGS%>> "%LOG%"
"%PY%" %PY_ARGS% --version
if errorlevel 1 (
  echo [ERROR] Python failed to run
  pause
  exit /b 1
)
echo.

if not exist "%~dp0requirements.txt" (
  echo [ERROR] requirements.txt missing. Extract the FULL project ZIP.
  pause
  exit /b 1
)
if not exist "%~dp0gui.py" (
  echo [ERROR] gui.py missing. Extract the FULL project ZIP.
  pause
  exit /b 1
)

if not exist "%~dp0.venv\Scripts\python.exe" (
  echo [2/3] First run: creating virtualenv .venv ...
  "%PY%" %PY_ARGS% -m venv "%~dp0.venv"
  if errorlevel 1 (
    echo [ERROR] venv failed.
    pause
    exit /b 1
  )
  echo       venv ready.
) else (
  echo [2/3] Virtualenv already exists.
)

set "VPY=%~dp0.venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo [ERROR] Missing %VPY%
  pause
  exit /b 1
)

echo [2/3] Checking packages...
"%VPY%" -c "import customtkinter,discord,aiohttp,tqdm" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo       Installing dependencies first time may take 1-3 min. Do not close.
  "%VPY%" -m pip install -U pip >> "%LOG%" 2>&1
  "%VPY%" -m pip install -r "%~dp0requirements.txt" >> "%LOG%" 2>&1
  if errorlevel 1 (
    echo [ERROR] pip install failed. See launch.log
    type "%LOG%"
    pause
    exit /b 1
  )
)
echo       Packages OK.
echo.

echo [3/3] Starting GUI...
"%VPY%" -u "%~dp0gui.py"
set "EC=%ERRORLEVEL%"
echo Exit %EC%>> "%LOG%"

if not "%EC%"=="0" (
  echo.
  echo [ERROR] Exit code: %EC%
  echo Log: %LOG%
  pause
  exit /b %EC%
)

echo.
echo Closed.
pause
exit /b 0