import threading
import requests
import os
import time
import m3u8
import subprocess
import shutil
import logging
from urllib.parse import urljoin
from queue import Queue
import sys

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')


def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        # When packaged with PyInstaller
        return os.path.join(sys._MEIPASS, 'ffmpeg.exe')
    return os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')


class DownloadWorker(threading.Thread):
    def __init__(self, name, url, output_dir, progress_callback, done_callback, num_connections=8, max_retries=3):
        super().__init__()
        self.name = name
        self.url = url
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        self.num_connections = max(1, min(num_connections, 64))
        self.max_retries = max_retries

        self._pause_event = threading.Event()
        self._pause_event.set()
        self._cancelled = False

        self.segment_urls = []
        self.total_segments = 0
        self.downloaded_segments = 0
        self.downloaded_bytes = 0
        self.lock = threading.Lock()
        self.start_time = None
        self.segment_dir = None

    def run(self):
        try:
            playlist = m3u8.load(self.url)

            if playlist.is_variant and playlist.playlists:
                best = max(playlist.playlists, key=lambda p: p.stream_info.bandwidth)
                self.url = urljoin(self.url, best.uri)
                playlist = m3u8.load(self.url)

            self.segment_urls = [urljoin(self.url, seg.uri) for seg in playlist.segments]
            self.total_segments = len(self.segment_urls)

            if self.total_segments == 0:
                self._safe_done_callback(False, "No segments found.")
                return

            self.start_time = time.time()
            self.segment_dir = os.path.join(self.output_dir, f"{self.name}_segments")
            os.makedirs(self.segment_dir, exist_ok=True)

            q = Queue()
            for i, url in enumerate(self.segment_urls):
                q.put((i, url))

            threads = []
            for _ in range(self.num_connections):
                t = threading.Thread(target=self.worker, args=(q,))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            if self._cancelled:
                self._cleanup_temp()
                self._safe_done_callback(False, "Download cancelled.")
                return

            # Generate segments.txt
            list_path = os.path.join(self.segment_dir, "segments.txt")
            with open(list_path, "w") as f:
                for i in range(self.total_segments):
                    segment_path = os.path.join(self.segment_dir, f"{i:05}.ts").replace("\\", "/")
                    f.write(f"file '{segment_path}'\n")

            output_path = os.path.join(self.output_dir, f"{self.name}.mp4")
            ffmpeg_path = get_ffmpeg_path()

            if not os.path.exists(ffmpeg_path):
                self._safe_done_callback(False, f"FFmpeg not found at: {ffmpeg_path}")
                return

            ffmpeg_cmd = [
                ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
                "-i", list_path, "-c", "copy", output_path
            ]
            
            try:
                result = subprocess.run(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW  # 👈 Prevents console flashing
                )
            except FileNotFoundError:
                self._safe_done_callback(False, "FFmpeg not found. Please install it or ensure it's in the package.")
                return
            
            if result.returncode != 0:
                logging.error("FFmpeg error:\n%s", result.stderr)
                self._safe_done_callback(False, f"FFmpeg error:\n{result.stderr.strip()}")
                return

            self._cleanup_temp()
            self._safe_done_callback(True, "Download complete.")

        except Exception as e:
            logging.exception(f"[{self.name}] Unexpected error:")
            self._cleanup_temp()
            self._safe_done_callback(False, f"Error: {str(e)}")

    def worker(self, q):
        while not q.empty() and not self._cancelled:
            self._pause_event.wait()
            try:
                index, url = q.get_nowait()
            except Exception:
                break

            retries = 0
            while retries <= self.max_retries and not self._cancelled:
                self._pause_event.wait()
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        segment_path = os.path.join(self.segment_dir, f"{index:05}.ts")
                        with open(segment_path, "wb") as f:
                            f.write(response.content)

                        segment_size = len(response.content)

                        with self.lock:
                            self.downloaded_segments += 1
                            self.downloaded_bytes += segment_size

                            percent = (self.downloaded_segments / self.total_segments) * 100
                            elapsed = time.time() - self.start_time + 0.01
                            speed = self.downloaded_bytes / elapsed / (1024 * 1024)

                            estimated_total_mb = (
                                (self.downloaded_bytes / self.downloaded_segments * self.total_segments)
                                / (1024 * 1024)
                            )

                            self.progress_callback(
                                self.name,
                                percent,
                                self.downloaded_bytes / (1024 * 1024),
                                estimated_total_mb,
                                speed
                            )
                        break
                    else:
                        raise Exception(f"HTTP {response.status_code}")
                except Exception as e:
                    retries += 1
                    wait_time = 0.5 * retries
                    logging.warning(f"[{self.name}] Segment {index} retry {retries}: {e}")
                    time.sleep(wait_time)

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def cancel(self):
        self._cancelled = True
        self._pause_event.set()

    def _cleanup_temp(self):
        if self.segment_dir and os.path.exists(self.segment_dir):
            try:
                shutil.rmtree(self.segment_dir)
                logging.info(f"[{self.name}] Temp folder cleaned.")
            except Exception as e:
                logging.error(f"[{self.name}] Cleanup error: {e}")

    def _safe_done_callback(self, success, message):
        try:
            self.done_callback(self.name, success, message)
        except Exception as e:
            logging.error(f"[{self.name}] Done callback error: {e}") 
