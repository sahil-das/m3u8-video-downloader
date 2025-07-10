import threading
import requests
import os
import time
import m3u8
import subprocess
import shutil
import sys
from urllib.parse import urljoin
from queue import Queue, Empty
from settings import load_settings

settings = load_settings()

class DownloadWorker(threading.Thread):
    def __init__(self, name, url, output_dir, progress_callback, done_callback, num_connections=8):
        super().__init__()
        self.name = name
        self.url = url
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        
        # ✅ Validate num_connections
        allowed_threads = [1, 2, 4, 8, 16, 32]
        self.num_connections = num_connections if num_connections in allowed_threads else 8

        self._pause = threading.Event()
        self._pause.set()
        self._cancel = False
        self.segment_dir = None
        self.timeout = settings.get("timeout", 10)
        self.max_retries = settings.get("max_retries", 3)
        self.daemon = True

    def pause(self):
        self._pause.clear()

    def resume(self):
        self._pause.set()

    def cancel(self):
        self._cancel = True
        self._pause.set()

    def run(self):
        try:
            if not os.access(self.output_dir, os.W_OK):
                self.done_callback(self.name, False, "Output folder not writable.")
                return

            playlist = m3u8.load(self.url)
            if playlist.is_variant and playlist.playlists:
                playlist = m3u8.load(urljoin(self.url, playlist.playlists[0].uri))

            segments = playlist.segments
            if not segments:
                self.done_callback(self.name, False, "No segments found.")
                return

            ext = os.path.splitext(segments[0].uri)[1]
            segment_ext = ext if ext.lower() in [".ts", ".aac", ".mp4"] else ".ts"
            self.segment_dir = os.path.join(self.output_dir, f"{self.name}_segments")
            os.makedirs(self.segment_dir, exist_ok=True)

            key = None
            iv = None
            if playlist.keys and playlist.keys[0]:
                key_uri = playlist.keys[0].uri
                if key_uri:
                    try:
                        key_url = urljoin(playlist.base_uri or self.url, key_uri)
                        key = requests.get(key_url, timeout=self.timeout).content
                        iv = playlist.keys[0].iv
                    except Exception as e:
                        self.done_callback(self.name, False, f"Failed to download AES key: {e}")
                        return

            queue = Queue()
            for i, seg in enumerate(segments):
                segment_url = seg.absolute_uri or urljoin(self.url, seg.uri)
                queue.put((i, segment_url))

            total = queue.qsize()
            self.downloaded = 0
            self.downloaded_bytes = 0
            start_time = time.time()
            threads = []

            try:
                from Crypto.Cipher import AES
            except ImportError:
                self.done_callback(self.name, False, "Missing dependency: pycryptodome. Install via 'pip install pycryptodome'")
                return

            def worker():
                while not queue.empty() and not self._cancel:
                    self._pause.wait()
                    if self._cancel:
                        break
                    try:
                        i, segment_url = queue.get_nowait()
                    except Empty:
                        continue

                    retry = 0
                    while retry <= self.max_retries:
                        if self._cancel:
                            break
                        self._pause.wait()
                        try:
                            r = requests.get(segment_url, timeout=self.timeout)
                            if r.status_code != 200:
                                raise Exception(f"HTTP {r.status_code}")
                            data = r.content
                            
                            if not data or len(data) < 128:  # arbitrary minimal threshold
                                raise Exception(f"Incomplete segment ({len(data)} bytes)")

                            if key:
                                try:
                                    if iv:
                                        iv_clean = iv[2:] if iv.lower().startswith("0x") else iv
                                        iv_bytes = bytes.fromhex(iv_clean)
                                    else:
                                        iv_bytes = i.to_bytes(16, byteorder='big')
                                    cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
                                    data = cipher.decrypt(data)
                                except Exception as e:
                                    self.done_callback(self.name, False, f"Decryption failed: {e}")
                                    return

                                cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
                                data = cipher.decrypt(data)

                            seg_path = os.path.join(self.segment_dir, f"{i:05d}{segment_ext}")
                            if os.path.exists(seg_path):
                                os.remove(seg_path)

                            with open(seg_path, "wb") as f:
                                f.write(data)

                            self.downloaded += 1
                            self.downloaded_bytes += len(data)
                            elapsed = time.time() - start_time + 0.1
                            speed = self.downloaded_bytes / 1024 / 1024 / elapsed
                            percent = (self.downloaded / total) * 100
                            estimated_size = ((self.downloaded_bytes / self.downloaded) * total / 1024 / 1024) if self.downloaded else 0

                            self.progress_callback(self.name, percent, self.downloaded_bytes / 1024 / 1024, estimated_size, speed)
                            break
                        except Exception as e:
                            retry += 1
                            time.sleep(0.5 * retry)

            for _ in range(self.num_connections):
                t = threading.Thread(target=worker)
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            if self._cancel:
                self._cleanup()
                self.done_callback(self.name, False, "Cancelled")
                return

            input_txt = os.path.join(self.segment_dir, "segments.txt")
            with open(input_txt, "w", encoding="utf-8") as f:
                for i in range(total):
                    path = os.path.join(self.segment_dir, f"{i:05d}{segment_ext}").replace("\\", "/")
                    safe_path = path.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            output_path = os.path.join(self.output_dir, f"{self.name}.mp4")
            ffmpeg = settings.get("ffmpeg_path", "ffmpeg")
            if not shutil.which(ffmpeg):
                self._cleanup()
                self.done_callback(self.name, False, f"FFmpeg not found: {ffmpeg}")
                return

            cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", input_txt, "-c", "copy", output_path]

            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)
            if result.returncode != 0:
                self._cleanup()
                err = result.stderr.decode().strip()
                self.done_callback(self.name, False, f"FFmpeg error:\n{err}")
                return

            self._cleanup()
            self.done_callback(self.name, True, f"Download complete: {output_path}")

        except Exception as e:
            self._cleanup()
            self.done_callback(self.name, False, f"Error: {str(e)}")

    def _cleanup(self):
        if self.segment_dir and os.path.exists(self.segment_dir):
            shutil.rmtree(self.segment_dir, ignore_errors=True)
