# download_worker.py
import m3u8, requests, os
from threading import Thread
from moviepy.video.io.VideoFileClip import VideoFileClip
import tempfile, time


class DownloadWorker(Thread):
    def __init__(self, url, output_file, progress_callback, done_callback, name=""):
        super().__init__()
        self.url = url
        self.output_file = output_file
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        self.name = name

    def run(self):
        try:
            start_time = time.time()
            m3u8_obj = m3u8.load(self.url)
            segments = m3u8_obj.segments
            total = len(segments)

            if total == 0:
                raise Exception("No segments found.")

            downloaded = 0
            downloaded_bytes = 0
            segment_data = []

            for segment in segments:
                segment_url = segment.absolute_uri
                response = requests.get(segment_url, timeout=10)
                data = response.content

                downloaded_bytes += len(data)
                segment_data.append(data)
                downloaded += 1

                percent = (downloaded / total) * 100
                downloaded_mb = downloaded_bytes / (1024 * 1024)
                estimated_total_mb = (downloaded_bytes / downloaded) * total / (1024 * 1024)
                elapsed = max(1, time.time() - start_time)
                speed = downloaded_mb / elapsed

                self.progress_callback(self.name, percent, downloaded_mb, estimated_total_mb, speed)

            # Save to .ts
            ts_path = tempfile.mktemp(suffix=".ts")
            with open(ts_path, 'wb') as f:
                for chunk in segment_data:
                    f.write(chunk)

            # Convert to .mp4
            clip = VideoFileClip(ts_path)
            clip.write_videofile(self.output_file, codec='libx264')
            clip.close()
            os.remove(ts_path)

            self.done_callback(self.name, True, "Downloaded successfully.")
        except Exception as e:
            self.done_callback(self.name, False, str(e))
