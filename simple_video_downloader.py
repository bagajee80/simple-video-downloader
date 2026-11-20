"""Simple Video Downloader for Windows."""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import parse_qs, urlsplit


EXAMPLE_URL = "https://youtu.be/KhqcxSvTyz4"
QUALITIES = {"720p": 720, "1080p": 1080, "최고화질": None}
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
PROGRESS = re.compile(r"^SVD_PROGRESS\s*([0-9.]+)%")


def normalize_url(value):
    url = urlsplit(value.strip())
    if url.scheme != "https" or url.netloc.lower() not in {
        "youtu.be", "youtube.com", "www.youtube.com", "m.youtube.com",
    }:
        raise ValueError("HTTPS YouTube 영상 주소를 입력하세요.")
    parts = url.path.strip("/").split("/")
    video_id = ""
    if url.netloc.lower() == "youtu.be" and len(parts) == 1:
        video_id = parts[0]
    elif url.path == "/watch":
        video_id = parse_qs(url.query).get("v", [""])[0]
    elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed"}:
        video_id = parts[1]
    if not VIDEO_ID.fullmatch(video_id):
        raise ValueError("YouTube 영상 한 개의 주소를 입력하세요.")
    return f"https://www.youtube.com/watch?v={video_id}"


def tool_path(name):
    base = Path(sys.executable if getattr(sys, "frozen", False) else __file__).parent
    tools = base / "tools"
    for folder in (base, tools, *sorted(tools.glob("ffmpeg-*-essentials_build/bin"), reverse=True)):
        candidate = folder / f"{name}.exe"
        if candidate.is_file():
            return str(candidate)
    return shutil.which(f"{name}.exe")


def download_args(url, quality, ffmpeg, node, extension="mp4"):
    if extension == "mp3":
        format_args = ["--format", "ba/b", "--extract-audio", "--audio-format", "mp3"]
    else:
        height = QUALITIES[quality]
        limit = f"[height<={height}]" if height else ""
        format_args = ["--format", f"bv*{limit}+ba/b{limit}", "--format-sort", "res",
                       "--merge-output-format", "mp4", "--remux-video", "mp4"]
    return [
        "--ignore-config", "--no-playlist", "--no-colors",
        "--newline", "--progress", "--progress-delta", "0.2",
        "--progress-template", "download:SVD_PROGRESS%(progress._percent_str)s",
        "--progress-template", "postprocess:SVD_PROCESS",
        "--ffmpeg-location", str(Path(ffmpeg).parent),
        "--js-runtimes", f"node:{node}",
        *format_args,
        "--windows-filenames", "-o", "%(title).90s [%(id)s].%(ext)s",
        "--", url,
    ]


def worker(log_path, args):
    # Wait until the GUI has assigned this process to the Windows job.
    ready = Path(log_path).with_name("start")
    deadline = time.monotonic() + 15
    while not ready.exists():
        if time.monotonic() >= deadline:
            raise SystemExit(1)
        time.sleep(0.025)
    # PyInstaller's windowed bootloader may leave stdout and stderr unset.
    with open(log_path, "w", encoding="utf-8", buffering=1) as log:
        external_yt_dlp = tool_path("yt-dlp") if getattr(sys, "frozen", False) else None
        if external_yt_dlp:
            # Keep the same progress protocol with the official standalone backend.
            environment = dict(os.environ, PYTHONIOENCODING="utf-8")
            exit_code = subprocess.call(
                [external_yt_dlp, *args], stdout=log, stderr=log, env=environment,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            raise SystemExit(exit_code)
        sys.stdout = sys.stderr = log
        try:
            import yt_dlp
            yt_dlp.main(args)
        finally:
            log.flush()


class WindowsJob:
    def __init__(self, pid):
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": (wintypes.HANDLE, (ctypes.c_void_p, wintypes.LPCWSTR)),
            "OpenProcess": (wintypes.HANDLE, (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)),
            "AssignProcessToJobObject": (wintypes.BOOL, (wintypes.HANDLE, wintypes.HANDLE)),
            "TerminateJobObject": (wintypes.BOOL, (wintypes.HANDLE, wintypes.UINT)),
            "CloseHandle": (wintypes.BOOL, (wintypes.HANDLE,)),
        }
        for name, (result, arguments) in signatures.items():
            function = getattr(self.api, name)
            function.restype = result
            function.argtypes = arguments
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            # PROCESS_SET_QUOTA and PROCESS_TERMINATE are required for assignment.
            process = self.api.OpenProcess(0x0100 | 0x0001, False, pid)
            if not process:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not self.api.AssignProcessToJobObject(self.handle, process):
                    raise ctypes.WinError(ctypes.get_last_error())
            finally:
                self.api.CloseHandle(process)
        except OSError:
            self.close()
            raise

    def terminate(self):
        if not self.api.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        self.api.CloseHandle(self.handle)


def publish(source, directory):
    index = 0
    while True:
        suffix = f" ({index})" if index else ""
        destination = directory / f"{source.stem}{suffix}{source.suffix}"
        try:
            source.rename(destination)  # Windows rename fails if the target exists.
            return destination
        except FileExistsError:
            index += 1


class Downloader:
    def __init__(self, root):
        self.root = root
        self.process = self.job = self.temp = None
        self.cancelled = self.closing = False
        self.log_offset = 0
        self.errors = []
        self.completed_folder = None
        preferred = Path.home() / "Downloads"
        self.folder = tk.StringVar(value=str(preferred if preferred.is_dir() else Path.home()))
        self.url = tk.StringVar(value=EXAMPLE_URL)
        self.quality = tk.StringVar(value="1080p")
        self.format = tk.StringVar(value="mp4")
        self.status = tk.StringVar(value="다운로드할 영상 주소를 입력하세요.")

        root.title("Simple Video Downloader")
        root.geometry("660x400")
        root.minsize(540, 400)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.option_add("*Font", ("맑은 고딕", 10))
        panel = ttk.Frame(root, padding=24)
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(1, weight=1)
        ttk.Label(panel, text="Simple Video Downloader",
                  font=("Segoe UI", 19, "bold")).grid(row=0, columnspan=3, sticky="w")
        ttk.Label(panel, text="저작권자에게 다운로드 허용을 받은 영상에만 사용하세요.",
                  foreground="#705019").grid(row=1, columnspan=3, sticky="w", pady=(4, 18))
        ttk.Label(panel, text="YouTube URL").grid(row=2, column=0, sticky="w", padx=(0, 12))
        address = ttk.Entry(panel, textvariable=self.url)
        address.grid(row=2, column=1, columnspan=2, sticky="ew")
        ttk.Label(panel, text="저장 형식").grid(row=3, column=0, sticky="w", pady=(12, 0))
        formats = ttk.Frame(panel)
        formats.grid(row=3, column=1, sticky="w", pady=(12, 0))
        video = ttk.Radiobutton(formats, text="MP4 영상", variable=self.format, value="mp4",
                               command=self.update_format)
        video.pack(side="left", padx=(0, 16))
        audio = ttk.Radiobutton(formats, text="MP3 음원", variable=self.format, value="mp3",
                               command=self.update_format)
        audio.pack(side="left")
        ttk.Label(panel, text="화질").grid(row=4, column=0, sticky="w", pady=12)
        self.quality_control = ttk.Combobox(panel, textvariable=self.quality, values=list(QUALITIES),
                                            state="readonly", width=14)
        self.quality_control.grid(row=4, column=1, sticky="w")
        ttk.Label(panel, text="저장 폴더").grid(row=5, column=0, sticky="w")
        folder = ttk.Entry(panel, textvariable=self.folder)
        folder.grid(row=5, column=1, sticky="ew")
        browse = ttk.Button(panel, text="찾아보기", command=self.browse)
        browse.grid(row=5, column=2, padx=(8, 0))
        self.inputs = (address, video, audio, folder, browse)
        self.progress = ttk.Progressbar(panel, maximum=100)
        self.progress.grid(row=6, columnspan=3, sticky="ew", pady=(22, 5))
        ttk.Label(panel, textvariable=self.status).grid(row=7, columnspan=3, sticky="w")
        actions = ttk.Frame(panel)
        actions.grid(row=8, columnspan=3, sticky="ew", pady=(14, 0))
        self.start_button = ttk.Button(actions, text="MP4 다운로드", command=self.start)
        self.start_button.pack(side="left")
        self.cancel_button = ttk.Button(actions, text="취소", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        self.open_button = ttk.Button(actions, text="저장 폴더 열기", command=self.open_folder,
                                      state="disabled")
        self.open_button.pack(side="right")

    def browse(self):
        selection = filedialog.askdirectory(parent=self.root, initialdir=self.folder.get())
        if selection:
            self.folder.set(selection)

    def set_running(self, running):
        for control in (*self.inputs, self.start_button):
            control.state(["disabled"] if running else ["!disabled"])
        self.cancel_button.configure(state="normal" if running else "disabled")
        self.update_format()

    def update_format(self):
        extension = self.format.get()
        self.quality_control.configure(
            state="disabled" if self.process is not None or extension == "mp3" else "readonly")
        self.start_button.configure(text=f"{extension.upper()} 다운로드")

    def start(self):
        try:
            url = normalize_url(self.url.get())
            self.directory = Path(self.folder.get().strip()).expanduser().resolve()
            if not self.folder.get().strip() or not self.directory.is_dir():
                raise ValueError("기존 저장 폴더를 선택하세요.")
            ffmpeg = tool_path("ffmpeg")
            node = tool_path("node")
            if not ffmpeg or not Path(ffmpeg).with_name("ffprobe.exe").is_file():
                raise ValueError("같은 폴더에 있는 ffmpeg.exe와 ffprobe.exe가 필요합니다. README를 확인하세요.")
            if not node:
                raise ValueError("Node.js가 필요합니다. README를 확인하세요.")
            if getattr(sys, "frozen", False) and not tool_path("yt-dlp"):
                # A standalone app built through build.bat can still bundle the module.
                from importlib.util import find_spec
                if find_spec("yt_dlp") is None:
                    raise ValueError("yt-dlp.exe가 필요합니다. 설치 프로그램을 다시 실행하세요.")
            self.temp = Path(tempfile.mkdtemp(prefix=".svd-", dir=self.directory))
            self.log = self.temp / "download.log"
            command = [sys.executable]
            if not getattr(sys, "frozen", False):
                command.append(str(Path(__file__).resolve()))
            command += ["--worker", str(self.log)]
            self.extension = self.format.get()
            command += download_args(url, self.quality.get(), ffmpeg, node, self.extension)
            self.process = subprocess.Popen(command, cwd=self.temp,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
            self.job = WindowsJob(self.process.pid)
            (self.temp / "start").touch()
        except (OSError, ValueError) as error:
            if self.process is not None:
                self.process.kill()
                self.process.wait()
                self.process = None
            self.cleanup()
            messagebox.showerror("시작할 수 없음", str(error), parent=self.root)
            return
        self.cancelled = False
        self.errors = []
        self.log_offset = 0
        self.set_running(True)
        self.open_button.configure(state="disabled")
        self.progress.configure(value=0)
        self.status.set("영상 정보를 가져오는 중…")
        self.root.after(100, self.poll)

    def update_progress(self):
        if not self.log.exists():
            return
        with self.log.open("rb") as stream:
            stream.seek(self.log_offset)
            lines = stream.read().splitlines(keepends=True)
        for raw in lines:
            if not raw.endswith(b"\n"):
                break
            self.log_offset += len(raw)
            line = raw.decode("utf-8", errors="replace").strip()
            match = PROGRESS.match(line)
            if match and not self.cancelled:
                percent = float(match[1])
                self.progress.configure(value=percent)
                self.status.set(f"다운로드 중 · 현재 영상 또는 음원 {percent:.1f}%")
            elif line.startswith("SVD_PROCESS") and not self.cancelled:
                self.status.set(f"{self.extension.upper()} 처리 중…")
            elif line.startswith(("ERROR:", "Traceback")):
                self.errors.append(line)

    def poll(self):
        exit_code = self.process.poll()
        self.update_progress()
        if exit_code is None:
            self.root.after(100, self.poll)
            return
        try:
            if self.cancelled:
                self.progress.configure(value=0)
                self.status.set("다운로드를 취소했습니다.")
            else:
                files = list(self.temp.glob(f"*.{self.extension}"))
                if exit_code or len(files) != 1 or not files[0].stat().st_size:
                    detail = f"{self.extension.upper()} 파일을 만들지 못했습니다. 종료 코드 {exit_code}"
                    raise OSError(self.errors[-1] if self.errors else detail)
                saved = publish(files[0], self.directory)
                self.completed_folder = saved.parent
                self.open_button.configure(state="normal")
                self.progress.configure(value=100)
                self.status.set("다운로드 완료")
        except OSError as error:
            self.status.set("다운로드 실패")
            messagebox.showerror("다운로드 실패", str(error), parent=self.root)
        finally:
            self.process = None
            self.cleanup()
            self.set_running(False)
        if self.closing:
            self.root.destroy()

    def cleanup(self):
        if self.job is not None:
            self.job.close()
            self.job = None
        if self.temp is not None:
            shutil.rmtree(self.temp, ignore_errors=True)
            self.temp = None

    def cancel(self):
        if self.cancelled:
            return
        try:
            if self.process.poll() is None:
                self.job.terminate()
        except OSError as error:
            self.closing = False
            messagebox.showerror("취소 실패", str(error), parent=self.root)
            return
        self.cancelled = True
        self.cancel_button.configure(state="disabled")
        self.status.set("취소 중…")

    def close(self):
        if self.process is None:
            self.root.destroy()
        else:
            self.closing = True
            self.cancel()

    def open_folder(self):
        try:
            os.startfile(self.completed_folder)
        except OSError as error:
            messagebox.showerror("폴더 열기 실패", str(error), parent=self.root)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--worker"]:
        worker(sys.argv[2], sys.argv[3:])
    else:
        root = tk.Tk()
        Downloader(root)
        root.mainloop()
