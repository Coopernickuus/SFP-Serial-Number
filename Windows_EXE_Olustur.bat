@echo off
setlocal
set "PYTHONUTF8=1"
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto python_path
py -3 -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>nul
if errorlevel 1 goto python_path
py -3 desktop\build_windows.py
if errorlevel 1 goto failed
goto done

:python_path
python -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>nul
if errorlevel 1 goto python3_path
python desktop\build_windows.py
if errorlevel 1 goto failed
goto done

:python3_path
python3 -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>nul
if errorlevel 1 goto missing_python
python3 desktop\build_windows.py
if errorlevel 1 goto failed
goto done

:missing_python
echo Python bulunamadi. Python 3.11-3.15 kurun ve bu dosyayi tekrar acin.
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
