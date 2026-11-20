# Simple Video Downloader

Windows 10/11 x64용 한국어 YouTube 다운로드 도구입니다. **저작권자에게 다운로드를 허용받은 영상에만 사용하세요.**

## 설치

GitHub 저장소의 **Releases**에서 `SimpleVideoDownloader-Setup-x64.exe`를 내려받아 실행합니다. 설치 중 FFmpeg, yt-dlp, Node.js를 각 프로젝트의 배포 서버에서 내려받으므로 인터넷 연결이 필요합니다. 설치 후 시작 메뉴에서 **Simple Video Downloader**를 실행합니다. 삭제는 같은 메뉴의 **Simple Video Downloader 제거**를 사용합니다.

## 사용

YouTube 주소, 화질, 저장 폴더를 선택하고 **MP4 다운로드**를 누릅니다. 720p와 1080p는 해상도 상한입니다. **최고화질**은 해상도 상한을 두지 않습니다. 진행 중 **취소**, 완료 후 **저장 폴더 열기**를 사용할 수 있습니다.

## 개발 및 빌드

Python 3.11 이상이 필요합니다. 소스 실행 환경에서는 ffmpeg.exe와 ffprobe.exe를 같은 폴더에 놓고, node.exe와 함께 Windows PATH 또는 프로그램 옆 `tools` 폴더에서 찾을 수 있게 합니다.

```bat
py -3 -m pip install -r requirements.txt
py -3 simple_video_downloader.py
py -3 -m unittest -v
```

`build.bat`은 PyInstaller로 실행 파일을 만듭니다. 공개 배포용 설치 프로그램은 [Inno Setup 7](https://jrsoftware.org/inno-setup/downloads)을 설치한 뒤 `build-release.ps1`을 실행해 빌드합니다. `ISCC.exe`가 PATH에 없으면 `-Compiler` 인수로 절대 경로를 지정합니다. 결과는 `release\SimpleVideoDownloader-Setup-x64.exe`입니다.

공개 배포용 설치 프로그램은 [FFmpeg Windows 빌드](https://github.com/GyanD/codexffmpeg/releases/tag/8.1.2), [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.10.26), [Node.js](https://nodejs.org/dist/v24.19.0/)를 직접 내려받고 설치 전에 SHA-256을 검사합니다. 각 구성요소에는 해당 프로젝트의 라이선스가 적용됩니다.
