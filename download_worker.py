import threading
import m3u8
import requests
import os
import time


class DownloadWorker(threading.Thread):
    def __init__(self, name, url, output_dir, progress_callback=None, done_callback=None):
        super().__init__()
        self.name = name
        self.url = url
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self.done_callback = done_callback

        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()

    def pause(self):
        self._pause_event.set()

    def resume(self):
        self._pause_event.clear()

    def cancel(self):
        self._cancel_event.set()

    def run(self):
        try:
            playlist = m3u8.load(self.url)
            if not playlist.segments:
                self.done_callback(self.name, False, "No segments found.")
                return

            segments = playlist.segments
            total = len(segments)
            output_path = os.path.join(self.output_dir, f"{self.name}.mp4")
            downloaded_bytes = 0
            segment_files = []

            start_time = time.time()

            for i, segment in enumerate(segments):
                if self._cancel_event.is_set():
                    self.done_callback(self.name, False, "Cancelled")
                    return

                while self._pause_event.is_set():
                    time.sleep(0.2)

                uri = segment.uri
                if not uri.startswith("http"):
                    base_uri = playlist.base_uri or self.url.rsplit("/", 1)[0] + "/"
                    uri = base_uri + uri

                r = requests.get(uri, stream=True, timeout=10)
                r.raise_for_status()

                segment_file = os.path.join(self.output_dir, f"{self.name}_{i}.ts")
                with open(segment_file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self._cancel_event.is_set():
                            self.done_callback(self.name, False, "Cancelled")
                            return
                        if self._pause_event.is_set():
                            while self._pause_event.is_set():
                                time.sleep(0.2)
                        if chunk:
                            f.write(chunk)
                            downloaded_bytes += len(chunk)

                segment_files.append(segment_file)

                percent = ((i + 1) / total) * 100
                elapsed = time.time() - start_time
                speed = downloaded_bytes / 1024 / 1024 / elapsed if elapsed > 0 else 0
                mb_done = downloaded_bytes / 1024 / 1024
                mb_total = (playlist.media_sequence + total) * 0.15  # estimate if unknown
                if self.progress_callback:
                    self.progress_callback(self.name, percent, mb_done, mb_total, speed)

            # Combine .ts files into final .mp4
            with open(output_path, "wb") as out_file:
                for seg_file in segment_files:
                    with open(seg_file, "rb") as f:
                        out_file.write(f.read())
                    os.remove(seg_file)

            self.done_callback(self.name, True, "Download completed.")

        except Exception as e:
            self.done_callback(self.name, False, f"Error: {str(e)}")
