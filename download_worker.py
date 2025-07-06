import m3u8
import requests
import os
import time
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


class DownloadWorker(threading.Thread):
    def __init__(self, name, url, output_dir, progress_callback, done_callback):
        super().__init__()
        self.name = name
        self.url = url
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self.done_callback = done_callback

        self._pause_event = threading.Event()
        self._pause_event.set()  # Start in unpaused state
        self._cancelled = threading.Event()

        self.segment_data = []

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def cancel(self):
        self._cancelled.set()

    def _wait_if_paused(self):
        self._pause_event.wait()

    def run(self):
        try:
            m3u8_obj = m3u8.load(self.url)
            segments = m3u8_obj.segments
            total = len(segments)

            if total == 0:
                raise Exception("No segments found.")

            self.segment_data = [None] * total
            downloaded = 0
            downloaded_bytes = 0
            start_time = time.time()

            session = requests.Session()

            def download_segment(i, segment_url):
                if self._cancelled.is_set():
                    return None
                self._wait_if_paused()
                response = session.get(segment_url, timeout=10)
                response.raise_for_status()
                return i, response.content

            with ThreadPoolExecutor(max_workers=16) as executor:
                futures = {
                    executor.submit(download_segment, i, seg.absolute_uri): i
                    for i, seg in enumerate(segments)
                }

                for future in as_completed(futures):
                    if self._cancelled.is_set():
                        raise Exception("Download cancelled by user.")

                    result = future.result()
                    if result is None:
                        continue
                    i, data = result
                    self.segment_data[i] = data
                    downloaded += 1
                    downloaded_bytes += len(data)

                    percent = (downloaded / total) * 100
                    downloaded_mb = downloaded_bytes / (1024 * 1024)
                    estimated_total_mb = (downloaded_bytes / downloaded) * total / (1024 * 1024)
                    elapsed = time.time() - start_time
                    speed = downloaded_bytes / elapsed / (1024 * 1024)

                    self.progress_callback(self.name, percent, downloaded_mb, estimated_total_mb, speed)

            ts_file = os.path.join(self.output_dir, f"{self.name}.ts")
            with open(ts_file, 'wb') as f:
                for chunk in self.segment_data:
                    f.write(chunk)

            mp4_file = os.path.join(self.output_dir, f"{self.name}.mp4")

            self.convert_to_mp4(ts_file, mp4_file)

            os.remove(ts_file)  # delete temporary .ts file

            self.done_callback(self.name, True, mp4_file)
        except Exception as e:
            self.done_callback(self.name, False, str(e))

    def convert_to_mp4(self, input_path, output_path):
        try:
            subprocess.run(
                ['ffmpeg', '-y', '-i', input_path, '-c', 'copy', output_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            raise Exception(f"Conversion failed: {e}")
