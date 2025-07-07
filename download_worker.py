import threading
import requests
import os
import time
import m3u8
from urllib.parse import urljoin
from queue import Queue

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
        self.total_mb = 0
        self.segment_data = {}
        self.downloaded_bytes = 0
        self.lock = threading.Lock()
        self.start_time = None

    def run(self):
        try:
            playlist = m3u8.load(self.url)

            # Handle master playlist
            if playlist.is_variant:
                if playlist.playlists:
                    best = max(playlist.playlists, key=lambda p: p.stream_info.bandwidth)
                    self.url = urljoin(self.url, best.uri)
                    playlist = m3u8.load(self.url)

            self.segment_urls = [urljoin(self.url, seg.uri) for seg in playlist.segments]
            total_segments = len(self.segment_urls)

            if total_segments == 0:
                self.done_callback(self.name, False, "No segments found")
                return

            self.total_mb = total_segments * 0.4
            self.start_time = time.time()

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
                self.done_callback(self.name, False, "Download Cancelled")
                return

            # Ensure all segments are downloaded
            missing = [i for i in range(len(self.segment_urls)) if i not in self.segment_data]
            if missing:
                self.done_callback(self.name, False, f"Missing segments: {missing}")
                return

            output_path = os.path.join(self.output_dir, f"{self.name}.mp4")
            with open(output_path, "wb") as f:
                for i in range(len(self.segment_urls)):
                    f.write(self.segment_data[i])

            self.done_callback(self.name, True, "Download Complete")

        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            self.done_callback(self.name, False, str(e))

    def worker(self, q):
        while not q.empty() and not self._cancelled:
            self._pause_event.wait()
            try:
                index, url = q.get_nowait()
            except:
                break

            retries = 0
            while retries <= self.max_retries:
                self._pause_event.wait()
                try:
                    response = requests.get(url, timeout=10, stream=True)
                    content = response.content

                    with self.lock:
                        self.segment_data[index] = content
                        self.downloaded_bytes += len(content)

                        percent = (len(self.segment_data) / len(self.segment_urls)) * 100
                        elapsed = time.time() - self.start_time + 0.01
                        speed = self.downloaded_bytes / elapsed / (1024 * 1024)

                        self.progress_callback(
                            self.name,
                            percent,
                            self.downloaded_bytes / (1024 * 1024),
                            self.total_mb,
                            speed
                        )
                    break
                except Exception as e:
                    retries += 1
                    if retries > self.max_retries:
                        print(f"[{self.name}] Failed segment {index}: {e}")
                finally:
                    q.task_done()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def cancel(self):
        self._cancelled = True
        self._pause_event.set()
