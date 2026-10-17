@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 desktop\build_windows.py
) else (
  python desktop\build_windows.py
)
if errorlevel 1 (
  echo EXE olusturulamadi. Yukaridaki hata mesajini kontrol edin.
  pause
  exit /b 1
)
explorer dist\SFP-Windows
