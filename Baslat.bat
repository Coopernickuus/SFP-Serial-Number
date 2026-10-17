@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 serial_number.py
) else (
  python serial_number.py
)
pause
