import threading
import requests
import time
import os

class DownloadWorker(threading.Thread):
    def __init__(self, name, url, output_dir, progress_callback, done_callback):
        super().__init__()
        self.name = name
        self.url = url
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        self._pause_event.set()

    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=10)
            total = int(response.headers.get('content-length', 0))
            if total == 0:
                raise Exception("Empty or invalid content")

            downloaded = 0
            start_time = time.time()
            temp_path = os.path.join(self.output_dir, f"{self.name}.temp")
            final_path = os.path.join(self.output_dir, f"{self.name}.mp4")

            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._cancel_event.is_set():
                        f.close()
                        os.remove(temp_path)
                        self.done_callback(self.name, False, "Cancelled")
                        return

                    self._pause_event.wait()

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        elapsed = time.time() - start_time
                        speed = (downloaded / 1024 / 1024) / elapsed if elapsed > 0 else 0
                        percent = (downloaded / total) * 100
                        self.progress_callback(self.name, percent, downloaded / 1024 / 1024, total / 1024 / 1024, speed)

            os.rename(temp_path, final_path)
            self.done_callback(self.name, True, "Download completed")
        except Exception as e:
            self.done_callback(self.name, False, f"Failed: {str(e)}")

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def cancel(self):
        self._cancel_event.set()
        self._pause_event.set()
