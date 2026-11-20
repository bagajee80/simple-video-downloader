param([string]$Compiler = 'ISCC.exe')

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    py -3 -m venv .venv-release
    if ($LASTEXITCODE) { throw 'Virtual environment setup failed.' }
    $python = '.\.venv-release\Scripts\python.exe'
    & $python -m pip install 'pyinstaller==6.22.3'
    if ($LASTEXITCODE) { throw 'PyInstaller installation failed.' }
    & $python -m PyInstaller --noconfirm --onedir --windowed --exclude-module yt_dlp --name SimpleVideoDownloader simple_video_downloader.py
    if ($LASTEXITCODE) { throw 'Application build failed.' }
    $payload = (Resolve-Path 'dist/SimpleVideoDownloader').Path
    & $Compiler "/DPayload=$payload" setup.iss
    if ($LASTEXITCODE) { throw 'Installer build failed.' }
} finally {
    Pop-Location
}
