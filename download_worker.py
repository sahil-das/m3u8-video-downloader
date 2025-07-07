import threading
import requests
import os
import time
import m3u8
from urllib.parse import urljoin, urlparse
from queue import Queue
import subprocess
import tempfile

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
        self.total_size = 0
        self.downloaded_bytes = 0
        self.lock = threading.Lock()
        self.temp_dir = tempfile.mkdtemp()
        self.start_time = None

    def run(self):
        try:
            playlist = m3u8.load(self.url)

            # Handle master playlist by selecting highest quality
            if playlist.is_variant:
                playlist = m3u8.load(urljoin(self.url, playlist.playlists[0].uri))

            self.segment_urls = [urljoin(self.url, seg.uri) for seg in playlist.segments]
            if not self.segment_urls:
                self.done_callback(self.name, False, "No segments found")
                return

            self.start_time = time.time()
            q = Queue()
            for i, url in enumerate(self.segment_urls):
                q.put((i, url))

            threads = []
            for _ in range(self.num_connections):
                t = threading.Thread(target=self.download_worker, args=(q,))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            if self._cancelled:
                self.done_callback(self.name, False, "Download Cancelled")
                return

            ts_list_path = os.path.join(self.temp_dir, "segments.txt")
            with open(ts_list_path, "w") as f:
                for i in range(len(self.segment_urls)):
                    f.write(f"file '{os.path.join(self.temp_dir, f'{i}.ts')}'\n")

            output_path = os.path.join(self.output_dir, f"{self.name}.mp4")
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", ts_list_path,
                "-c", "copy", output_path
            ]
            subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.done_callback(self.name, True, "Download Complete")

        except Exception as e:
            self.done_callback(self.name, False, str(e))

    def download_worker(self, q):
        while not q.empty() and not self._cancelled:
            self._pause_event.wait()
            try:
                index, url = q.get_nowait()
            except:
                break

            retries = 0
            while retries <= self.max_retries:
                try:
                    response = requests.get(url, timeout=10, stream=True)
                    ts_path = os.path.join(self.temp_dir, f"{index}.ts")
                    with open(ts_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if self._cancelled:
                                return
                            self._pause_event.wait()
                            if chunk:
                                f.write(chunk)
                                with self.lock:
                                    self.downloaded_bytes += len(chunk)
                                    percent = (index + 1) / len(self.segment_urls) * 100
                                    speed = self.downloaded_bytes / (time.time() - self.start_time + 0.01) / (1024 * 1024)
                                    self.progress_callback(
                                        self.name,
                                        percent,
                                        self.downloaded_bytes / (1024 * 1024),
                                        len(self.segment_urls) * 0.4,
                                        speed
                                    )
                    break
                except Exception as e:
                    retries += 1
                    if retries > self.max_retries:
                        print(f"[{self.name}] Failed to download segment {index}: {e}")

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def cancel(self):
        self._cancelled = True
        self._pause_event.set()
