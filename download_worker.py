import threading
import requests
import os
import time
import m3u8  # You must install python-m3u8 via pip: pip install m3u8


class DownloadWorker(threading.Thread):
    def __init__(self, name, url, output_dir, progress_callback, done_callback):
        super().__init__()
        self.name = name
        self.url = url
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self.done_callback = done_callback

        self._pause_event = threading.Event()
        self._pause_event.set()  # Start unpaused

        self._cancelled = False
        self.segment_urls = []
        self.total_mb = 0

    def run(self):
        try:
            # Step 1: Parse M3U8
            playlist = m3u8.load(self.url)
            self.segment_urls = [seg.uri for seg in playlist.segments]

            total_segments = len(self.segment_urls)
            if total_segments == 0:
                self.done_callback(self.name, False, "No segments found")
                return

            # Estimate size (rough)
            self.total_mb = total_segments * 0.4  # Average segment ~400KB

            output_path = os.path.join(self.output_dir, f"{self.name}.mp4")
            downloaded_mb = 0
            start_time = time.time()

            with open(output_path, "wb") as f:
                for idx, segment_url in enumerate(self.segment_urls):
                    if self._cancelled:
                        break

                    self._pause_event.wait()  # Wait if paused

                    # Download segment
                    response = requests.get(segment_url, stream=True)
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if self._cancelled:
                            break
                        if chunk:
                            f.write(chunk)
                            downloaded_mb += len(chunk) / (1024 * 1024)

                    percent = ((idx + 1) / total_segments) * 100
                    elapsed = time.time() - start_time + 0.1
                    speed = downloaded_mb / elapsed
                    self.progress_callback(self.name, percent, downloaded_mb, self.total_mb, speed)

            # Handle cancellation
            if self._cancelled:
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except Exception as e:
                        print(f"[{self.name}] Error deleting temp file: {e}")
                self.done_callback(self.name, False, "Download Cancelled")
                return

            # Success
            self.done_callback(self.name, True, "Download Complete")

        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            self.done_callback(self.name, False, str(e))

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def cancel(self):
        self._cancelled = True
        self._pause_event.set()  # Unpause if paused to exit cleanly
