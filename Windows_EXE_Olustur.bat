@echo off
setlocal
set "PYTHONUTF8=1"
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto python_path
py -3.12 -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if errorlevel 1 goto python_path
py -3.12 desktop\build_windows.py
if errorlevel 1 goto failed
goto done

:python_path
python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if errorlevel 1 goto missing_python
python desktop\build_windows.py
if errorlevel 1 goto failed
goto done

:missing_python
echo Python 3.12 bulunamadi. Once python.org uzerinden Python 3.12 kurun.
pause
exit /b 1

:failed
echo EXE olusturulamadi. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1

:done
echo Yeni EXE hazir. Surum bilgisi dist\SFP-Windows\SURUM.txt icindedir.
explorer "%~dp0dist\SFP-Windows"
exit /b 0
