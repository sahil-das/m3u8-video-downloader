import threading
import subprocess
import os
import time


class DownloadWorker(threading.Thread):
    def __init__(self, task_queue, status_callback, progress_callback):
        super().__init__(daemon=True)
        self.queue = task_queue
        self.status_callback = status_callback
        self.progress_callback = progress_callback

    def run(self):
        while True:
            try:
                url, output = self.queue.get()
                self.status_callback(f"Starting: {output}")
                self.download_with_ffmpeg(url, output)
                self.status_callback(f"Completed: {output}")
                self.progress_callback(0)
                self.queue.task_done()
            except Exception as e:
                self.status_callback(f"Error: {e}")
                self.progress_callback(0)

    def download_with_ffmpeg(self, url, output, max_retries=3):
        retries = 0
        while retries < max_retries:
            try:
                command = [
                    "ffmpeg",
                    "-y",
                    "-i", url,
                    "-c", "copy",
                    "-bsf:a", "aac_adtstoasc",
                    output
                ]

                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )

                total_duration = None
                for line in process.stdout:
                    if "Duration:" in line:
                        total_duration = self.parse_duration(line)
                    if "time=" in line:
                        current_time = self.parse_time(line)
                        if total_duration and current_time:
                            percent = min(current_time / total_duration, 1.0)
                            self.progress_callback(percent)

                process.wait()
                if process.returncode == 0:
                    return
                else:
                    raise Exception("FFmpeg failed.")

            except Exception as e:
                retries += 1
                self.status_callback(f"Retry {retries}/{max_retries} - {output}")
                time.sleep(2)

        raise Exception("Download failed after retries.")

    def parse_duration(self, line):
        import re
        match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", line)
        if match:
            h, m, s = map(float, match.groups())
            return h * 3600 + m * 60 + s
        return None

    def parse_time(self, line):
        import re
        match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
        if match:
            h, m, s = map(float, match.groups())
            return h * 3600 + m * 60 + s
        return None
