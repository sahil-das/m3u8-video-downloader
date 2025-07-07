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
            output_path = os.path.join(self.output_dir, f"{self.name}.mp4")
            total_segments = len(self.segment_urls)
            downloaded_mb = 0
            start_time = time.time()
    
            with open(output_path, "wb") as f:
                for idx, segment_url in enumerate(self.segment_urls):
                    if self._cancelled:
                        break
                    self._pause_event.wait()  # Pauses here if needed
    
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
    
            # If cancelled, delete temp file AFTER closing it
            if self._cancelled:
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except Exception as e:
                        print(f"[{self.name}] Error deleting file: {e}")
                self.done_callback(self.name, False, "Download Cancelled")
                return
    
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
        self.resume()
