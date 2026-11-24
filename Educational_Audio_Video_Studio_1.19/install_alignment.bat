@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo Installing optional faster-whisper alignment support...
if not exist ".venv\Scripts\python.exe" (
  echo Please run run_app.bat once first to create the virtual environment.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check "faster-whisper>=1.0,<2"
if errorlevel 1 (
  echo Installation failed. Check your internet connection and Python version.
) else (
  echo Alignment support installed. The small model downloads on first use.
)
pause
