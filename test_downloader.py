import os
from pathlib import Path
import tempfile
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from simple_video_downloader import Downloader, EXAMPLE_URL, download_args, normalize_url, publish


class DownloadTests(unittest.TestCase):
    def test_url_normalization(self):
        expected = "https://www.youtube.com/watch?v=KhqcxSvTyz4"
        for url in (EXAMPLE_URL, expected + "&list=example",
                    "https://m.youtube.com/shorts/KhqcxSvTyz4"):
            with self.subTest(url=url):
                self.assertEqual(normalize_url(url), expected)
        for url in ("https://youtube.com.evil.test/watch?v=KhqcxSvTyz4",
                    "https://youtube.com/playlist?list=example",
                    "https://youtu.be/short"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_url(url)

    def test_quality_and_mp4(self):
        for quality, limit in (("720p", "[height<=720]"), ("1080p", "[height<=1080]"),
                               ("최고화질", "")):
            with self.subTest(quality=quality):
                args = download_args(EXAMPLE_URL, quality, r"C:\tools\ffmpeg.exe", r"C:\tools\node.exe")
                self.assertEqual(args[args.index("--format") + 1], f"bv*{limit}+ba/b{limit}")
                for flag in ("--merge-output-format", "--remux-video"):
                    self.assertEqual(args[args.index(flag) + 1], "mp4")

    @unittest.skipUnless(os.name == "nt", "Windows file semantics")
    def test_existing_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            existing = folder / "영상.mp4"
            existing.write_bytes(b"existing")
            incoming = folder / "incoming"
            incoming.mkdir()
            source = incoming / existing.name
            source.write_bytes(b"replacement")
            self.assertEqual(publish(source, folder).name, "영상 (1).mp4")
            self.assertEqual(existing.read_bytes(), b"existing")


@unittest.skipUnless(os.name == "nt", "Windows GUI and process control")
class GuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.temp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.destination = self.temp / "한글 저장 폴더"
        self.destination.mkdir()
        for name in ("ffmpeg.exe", "ffprobe.exe", "node.exe"):
            (self.temp / name).touch()
        (self.temp / "yt_dlp.py").write_text(
            "from pathlib import Path\n"
            "import os, time\n"
            "def main(args):\n"
            "    print('SVD_PROGRESS 32.0%', flush=True)\n"
            "    if os.environ.get('SVD_TEST_SLOW'):\n"
            "        Path('unfinished.part').write_bytes(b'partial')\n"
            "        time.sleep(20)\n"
            "    print('SVD_PROCESS', flush=True)\n"
            "    Path('test.mp4').write_bytes(b'fixture')\n",
            encoding="utf-8",
        )
        self.enterContext(patch.dict(os.environ, {"PYTHONPATH": str(self.temp)}))
        self.enterContext(patch("simple_video_downloader.tool_path",
                                side_effect=lambda name: str(self.temp / f"{name}.exe")))
        error_box = self.enterContext(patch("simple_video_downloader.messagebox.showerror"))
        self.addCleanup(error_box.assert_not_called)
        self.app = Downloader(self.root)
        self.app.folder.set(str(self.destination))
        self.addCleanup(self.stop_worker)

    def wait_for(self, predicate):
        deadline = time.monotonic() + 8
        while not predicate() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.02)
        self.assertTrue(predicate(), self.app.status.get())

    def stop_worker(self):
        if self.app.process is not None:
            self.app.cancel()
            self.wait_for(lambda: self.app.process is None)

    def test_success_and_open_folder(self):
        self.app.start()
        self.assertIsNotNone(self.app.process)
        self.wait_for(lambda: self.app.process is None)
        self.assertEqual(self.app.status.get(), "다운로드 완료")
        self.assertEqual(list(self.destination.iterdir()), [self.destination / "test.mp4"])
        with patch("simple_video_downloader.os.startfile") as open_path:
            self.app.open_button.invoke()
            open_path.assert_called_once_with(self.destination)

    def test_progress_and_cancel_remove_partial_files(self):
        with patch.dict(os.environ, {"SVD_TEST_SLOW": "1"}):
            self.app.start()
        self.assertIsNotNone(self.app.process)
        self.wait_for(lambda: float(self.app.progress["value"]) == 32)
        self.app.cancel_button.invoke()
        self.wait_for(lambda: self.app.process is None)
        self.assertEqual(self.app.status.get(), "다운로드를 취소했습니다.")
        self.assertEqual(list(self.destination.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
