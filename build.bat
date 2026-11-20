@echo off
setlocal
cd /d "%~dp0" || exit /b 1

if defined SVD_PYTHON goto custom_python
where py >nul 2>&1
if errorlevel 1 goto normal_python
py -3 -c "import sys, tkinter; raise SystemExit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 goto normal_python
py -3 -m venv .venv-build
goto check_venv

:normal_python
set "SVD_PYTHON=python"
:custom_python
"%SVD_PYTHON%" -c "import sys, tkinter; raise SystemExit(sys.version_info < (3, 11))"
if errorlevel 1 goto no_python
"%SVD_PYTHON%" -m venv .venv-build

:check_venv
if errorlevel 1 goto failed
".venv-build\Scripts\python.exe" -m pip install --upgrade -r requirements.txt pyinstaller
if errorlevel 1 goto failed
".venv-build\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name SimpleVideoDownloader --collect-all yt_dlp --collect-all yt_dlp_ejs simple_video_downloader.py
if errorlevel 1 goto failed
echo Built: "%CD%\dist\SimpleVideoDownloader\SimpleVideoDownloader.exe"
exit /b 0

:no_python
echo Python 3.11 or newer with tkinter is required. Set SVD_PYTHON to its full path if needed.
:failed
echo Build failed. See the messages above.
exit /b 1
