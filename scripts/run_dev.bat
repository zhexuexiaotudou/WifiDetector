@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0\.."
if not exist .venv\Scripts\python.exe (
  echo 请先运行 scripts\setup_windows.ps1
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
