@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Educational Audio Video Studio 1.19

set PYEXE=
where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 -c "import sys" >nul 2>nul
  if not errorlevel 1 set PYEXE=py -3.11
)
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYEXE="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE (
  where python >nul 2>nul
  if not errorlevel 1 set PYEXE=python
)
if not defined PYEXE (
  echo [ERROR] Khong tim thay Python 3.11 / 3.12.
  echo Cai Python tu https://www.python.org/downloads/windows/
  echo Nho bat Add Python to PATH va Tcl/Tk.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Tao moi truong Python rieng trong thu muc app...
  %PYEXE% -m venv .venv
  if errorlevel 1 goto failed
)

echo [2/3] Kiem tra/cai thu vien...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto failed

echo [3/3] Khoi dong ung dung...
".venv\Scripts\python.exe" educational_video_studio.py
if errorlevel 1 (
  echo.
  echo Ung dung ket thuc voi loi. Hay xem README_VI.md.
  pause
)
exit /b 0

:failed
echo.
echo Khong the cai Python dependencies. Kiem tra ket noi Internet va thu lai.
pause
exit /b 1
