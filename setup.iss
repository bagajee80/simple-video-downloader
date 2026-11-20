#ifndef Payload
  #error Payload path required
#endif

[Setup]
AppId=SimpleVideoDownloader.Windows
AppName=Simple Video Downloader
AppVersion=1.0.0
DefaultDirName={localappdata}\Programs\Simple Video Downloader
DefaultGroupName=Simple Video Downloader
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
ArchiveExtraction=auto
OutputDir=release
OutputBaseFilename=SimpleVideoDownloader-Setup-x64
CreateUninstallRegKey=no

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕 화면에 바로가기 만들기"; Flags: unchecked

[Files]
Source: "{#Payload}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "https://github.com/GyanD/codexffmpeg/releases/download/8.1.2/ffmpeg-8.1.2-essentials_build.7z"; DestName: "ffmpeg.7z"; DestDir: "{app}\tools"; ExternalSize: 33876939; Hash: "e25b682664025d49034c981afb4bae36238a40f29a3cc1c713ad9a8b5b3528f6"; Flags: external download extractarchive recursesubdirs ignoreversion
Source: "https://github.com/yt-dlp/yt-dlp/releases/download/2026.10.26/yt-dlp.exe"; DestName: "yt-dlp.exe"; DestDir: "{app}\tools"; ExternalSize: 23575744; Hash: "f5389d3698ecde4ef06f4e6b1ce0294fe9ac1396228c8990b8d3416d6d177a7d"; Flags: external download ignoreversion
Source: "https://nodejs.org/dist/v24.19.0/win-x64/node.exe"; DestName: "node.exe"; DestDir: "{app}\tools"; ExternalSize: 92825416; Hash: "3602f2bb1a10f2cbab4c36886218a33c1ab3db87290e73b033c46c77147d0237"; Flags: external download ignoreversion

[Icons]
Name: "{group}\Simple Video Downloader"; Filename: "{app}\SimpleVideoDownloader.exe"; WorkingDir: "{app}"; Check: not WizardNoIcons
Name: "{group}\Simple Video Downloader 제거"; Filename: "{uninstallexe}"; WorkingDir: "{app}"; Check: not WizardNoIcons
Name: "{userdesktop}\Simple Video Downloader"; Filename: "{app}\SimpleVideoDownloader.exe"; WorkingDir: "{app}"; Tasks: desktopicon; Check: not WizardNoIcons

[Run]
Filename: "{app}\SimpleVideoDownloader.exe"; Description: "Simple Video Downloader 실행"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
