import threading
import time
import os
import requests
import m3u8
from urllib.parse import urljoin

class DownloadWorker(threading.Thread):
    def __init__(self, name, url, output_dir, progress_callback, done_callback):
        super().__init__()
        self.name = name
        self.url = url
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._cancelled = False

    def run(self):
        try:
            playlist = m3u8.load(self.url)
            if not playlist.segments:
                raise Exception("No segments found.")

            total_segments = len(playlist.segments)
            file_path = os.path.join(self.output_dir, f"{self.name}.mp4")
            with open(file_path, 'wb') as f:
                for i, segment in enumerate(playlist.segments):
                    self._pause_event.wait()
                    if self._cancelled:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        return

                    segment_url = urljoin(self.url, segment.uri)
                    content = requests.get(segment_url, timeout=10).content
                    f.write(content)

                    percent = ((i + 1) / total_segments) * 100
                    downloaded_mb = f.tell() / (1024 * 1024)
                    total_mb = (total_segments * len(content)) / (1024 * 1024)
                    speed = 0
                    self.progress_callback(self.name, percent, downloaded_mb, total_mb, speed)
            self.done_callback(self.name, True, "Download completed.")
        except Exception as e:
            self.done_callback(self.name, False, str(e))

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def cancel(self):
        self._cancelled = True
        self.resume()
